"""
Open Food Facts live ingestion.

What this module does:
  - fetches product metadata (name, brand, size, barcode) from OFF API
  - resolves product identity: barcode first, identity_key fallback
  - inserts ProductSnapshot rows with real timestamps and source labels
  - enforces fill-phase → track-phase panel size control

What this module does NOT do:
  - create ShrinkflationFlags (detector only)
  - infer price impact from size alone
  - fall back to historical data when live data is missing
  - use fuzzy string matching as primary identity logic
  - fabricate prices, timestamps, or barcodes

Schema fields used:
  Product.data_source       = "live_openfoodfacts"
  ProductSnapshot.data_source     = "live_openfoodfacts"
  ProductSnapshot.observation_type = "real_observed"
  ProductSnapshot.size_unit_family = resolved via resolve_unit_family()
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests

from db.models import (
    IngestionRun, Product, ProductSnapshot, get_session, init_db, resolve_unit_family,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# OFF API mirrors: .net works from Streamlit Cloud; .org blocks cloud IPs
OFF_SEARCH_URLS = [
    "https://world.openfoodfacts.net/api/v2/search",
    "https://world.openfoodfacts.org/api/v2/search",
]

OFF_HEADERS = {
    "User-Agent": (
        "ShrinkflationDetector/1.0 "
        "(https://github.com/MokshJainrock/shrinkflation-detector; "
        "contact@shrinkflation.app)"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

OFF_FIELDS = (
    "product_name,brands,quantity,product_quantity,product_quantity_unit,"
    "categories_tags_en,image_url,code"
)

# Panel size targets for fill vs track phase control
PANEL_FILL_TARGET = 600   # below this: discover new products freely
PANEL_HARD_CAP = 800      # above this: stop creating new live products entirely

# Minimum time between snapshots for the same product (seconds)
# Set to match 30-min scan interval — prevents duplicate inserts per cycle
SNAPSHOT_MIN_INTERVAL_S = 1800  # 30 minutes

# Tracked categories for category-rotation scanning
TRACKED_CATEGORIES = [
    "chips", "cereal", "ice-cream", "yogurt", "cookies",
    "crackers", "pasta", "candy", "bread", "coffee",
    "ketchup", "mayonnaise", "peanut-butter", "juice",
    "frozen-meals", "detergent", "soap",
]

DATA_SOURCE = "live_openfoodfacts"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize(s: str) -> str:
    """Lowercase, remove punctuation, collapse whitespace."""
    s = s.lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _make_identity_key(brand: str, name: str) -> str:
    return f"{_normalize(brand)}::{_normalize(name)}"


def _parse_quantity(quantity_str: Optional[str]):
    """Parse '250 g' or '16 fl oz' → (value, unit). Returns (None, None) on failure."""
    if not quantity_str:
        return None, None
    match = re.search(r"([\d.]+)\s*([a-zA-Z][a-zA-Z\s]*)", str(quantity_str).strip())
    if match:
        try:
            val = float(match.group(1))
            unit = match.group(2).strip().lower()
            if val > 0:
                return val, unit
        except ValueError:
            pass
    return None, None


def _fetch_category(category: str, page_size: int = 50) -> list:
    """
    Fetch products from OFF for a given category.
    Tries .net mirror first, falls back to .org.
    Returns empty list on total failure — never raises.
    """
    params = {
        "categories_tags_en": category,
        "fields": OFF_FIELDS,
        "page_size": page_size,
        "sort_by": "last_modified_t",
        "json": 1,
    }
    for url in OFF_SEARCH_URLS:
        try:
            resp = requests.get(url, params=params, headers=OFF_HEADERS, timeout=8)
            resp.raise_for_status()
            products = resp.json().get("products", [])
            logger.debug(f"[OFF] {len(products)} products for '{category}' from {url.split('/')[2]}")
            return products
        except Exception as e:
            logger.warning(f"[OFF] {url.split('/')[2]} failed for '{category}': {e}")
            continue
    logger.error(f"[OFF] All mirrors failed for category '{category}'")
    return []


# ---------------------------------------------------------------------------
# Panel size + phase
# ---------------------------------------------------------------------------

def _get_live_panel_size(session) -> int:
    """Count products added by live ingestion (not historical)."""
    return (
        session.query(Product)
        .filter(Product.data_source.in_(["live_openfoodfacts", "live_kroger"]))
        .count()
    )


def _get_phase(panel_size: int) -> str:
    """
    Return "fill" or "track" based on current live panel size.

    fill  : panel_size < PANEL_FILL_TARGET  → create new products freely
    track : panel_size >= PANEL_FILL_TARGET → update existing only, no broad discovery
    """
    return "fill" if panel_size < PANEL_FILL_TARGET else "track"


# ---------------------------------------------------------------------------
# Identity resolution (STRICT)
# ---------------------------------------------------------------------------

def _match_by_barcode(session, barcode: str) -> Optional[Product]:
    """Find any Product with this barcode, regardless of data_source."""
    if not barcode:
        return None
    return (
        session.query(Product)
        .filter(Product.barcode == barcode.strip())
        .first()
    )


def _match_by_identity_key(session, brand: str, name: str) -> Optional[Product]:
    """
    Find a live Product by normalized brand::name.
    Only matches live products (not documented_historical).
    """
    key = _make_identity_key(brand, name)
    return (
        session.query(Product)
        .filter(
            Product.identity_key == key,
            Product.data_source == DATA_SOURCE,
        )
        .first()
    )


def _resolve_product(
    session,
    barcode: Optional[str],
    brand: str,
    name: str,
    category: str,
    image_url: Optional[str],
    phase: str,
) -> tuple:
    """
    Strict identity resolution.

    Returns (product, created: bool).
    created=True means a new Product row was inserted.

    Resolution order:
      1. barcode match (any data_source)
      2. identity_key match (live_openfoodfacts only)
      3. create new row — only allowed in "fill" phase

    In "track" phase: returns (None, False) if product not already known.
    """
    # Step 1: barcode
    if barcode:
        existing = _match_by_barcode(session, barcode)
        if existing:
            return existing, False

    # Step 2: identity key
    existing = _match_by_identity_key(session, brand, name)
    if existing:
        return existing, False

    # Step 3: create — only in fill phase
    if phase == "track":
        return None, False

    identity_key = _make_identity_key(brand, name)
    product = Product(
        name=name,
        brand=brand,
        category=category,
        barcode=barcode or None,
        data_source=DATA_SOURCE,
        retailer="openfoodfacts",
        identity_key=identity_key,
        image_url=image_url or None,
    )
    session.add(product)
    try:
        session.flush()
        return product, True
    except Exception as e:
        session.rollback()
        logger.warning(f"[live_tracker] Could not create product '{name}': {e}")
        return None, False


# ---------------------------------------------------------------------------
# Snapshot deduplication
# ---------------------------------------------------------------------------

def _should_insert_snapshot(
    session,
    product_id: int,
    size_value: float,
    size_unit: str,
    now: datetime,
) -> bool:
    """
    Return True if a new snapshot should be inserted.

    Inserts when:
      - No prior live snapshot exists for this product, OR
      - Last live snapshot was > SNAPSHOT_MIN_INTERVAL_S ago

    This means we record one snapshot per scan cycle per product.
    The detector compares snapshots across time — it needs
    regular observations even when nothing changed.
    """
    last = (
        session.query(ProductSnapshot)
        .filter(
            ProductSnapshot.product_id == product_id,
            ProductSnapshot.data_source == DATA_SOURCE,
        )
        .order_by(ProductSnapshot.scraped_at.desc())
        .first()
    )
    if not last:
        return True

    ts = last.scraped_at
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    elapsed = (now - ts).total_seconds()
    return elapsed >= SNAPSHOT_MIN_INTERVAL_S


# ---------------------------------------------------------------------------
# Main ingestion function
# ---------------------------------------------------------------------------

def run_live_update(max_categories: int = 5) -> dict:
    """
    Fetch products from OFF and insert clean snapshots.

    Returns a stats dict compatible with the dashboard's _run_live_scan().
    """
    init_db()
    session = get_session()

    stats = {
        "new_products": 0,
        "existing_updated": 0,
        "new_snapshots": 0,
        "categories_checked": 0,
        "phase": "fill",
        "panel_size": 0,
        "off_errors": 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    run = IngestionRun(
        source="openfoodfacts",
        phase="fill",  # updated at end
        status="running",
    )
    session.add(run)
    session.commit()

    try:
        panel_size = _get_live_panel_size(session)
        phase = _get_phase(panel_size)
        stats["panel_size"] = panel_size
        stats["phase"] = phase
        run.phase = phase

        # Category rotation: use minute-of-day so each run scans different categories
        now_utc = datetime.now(timezone.utc)
        minute_offset = (now_utc.hour * 60 + now_utc.minute) % len(TRACKED_CATEGORIES)
        categories_to_check = []
        for i in range(max_categories):
            idx = (minute_offset + i) % len(TRACKED_CATEGORIES)
            categories_to_check.append(TRACKED_CATEGORIES[idx])

        now = datetime.now(timezone.utc)

        for category in categories_to_check:
            raw_products = _fetch_category(category)
            stats["categories_checked"] += 1

            if not raw_products:
                stats["off_errors"] += 1
                time.sleep(1)
                continue

            for raw in raw_products:
                name = (raw.get("product_name") or "").strip()
                brand = (raw.get("brands") or "").strip().split(",")[0].strip()

                if not name or not brand:
                    continue

                # Parse size from OFF response
                size_value, size_unit = None, None
                if raw.get("product_quantity"):
                    try:
                        size_value = float(raw["product_quantity"])
                        size_unit = (raw.get("product_quantity_unit") or "g").lower()
                    except (ValueError, TypeError):
                        size_value, size_unit = _parse_quantity(raw.get("quantity"))
                else:
                    size_value, size_unit = _parse_quantity(raw.get("quantity"))

                # OFF product is useless without a parseable size
                if not size_value or size_value <= 0:
                    continue

                barcode = (raw.get("code") or "").strip() or None
                image_url = raw.get("image_url")
                full_name = name  # OFF's product_name is already the full name

                # Resolve product identity
                product, created = _resolve_product(
                    session, barcode, brand, full_name,
                    category.replace("-", " "), image_url, phase
                )
                if product is None:
                    continue  # track phase + unknown product → skip

                if created:
                    stats["new_products"] += 1
                    # Update panel size for phase tracking
                    panel_size += 1
                    if panel_size >= PANEL_FILL_TARGET:
                        phase = "track"
                        stats["phase"] = "track"
                else:
                    stats["existing_updated"] += 1

                # Snapshot deduplication
                if not _should_insert_snapshot(session, product.id, size_value, size_unit, now):
                    continue

                unit_family = resolve_unit_family(size_unit)
                snapshot = ProductSnapshot(
                    product_id=product.id,
                    size_value=size_value,
                    size_unit=size_unit,
                    size_unit_family=unit_family,
                    price=None,          # OFF does not provide prices
                    price_per_unit=None,
                    data_source=DATA_SOURCE,
                    observation_type="real_observed",
                    scraped_at=now,
                )
                session.add(snapshot)
                stats["new_snapshots"] += 1

            session.commit()
            time.sleep(1)  # OFF rate limit: 1 req/s

        # Finalize run log
        run.finished_at = datetime.now(timezone.utc)
        run.products_added = stats["new_products"]
        run.snapshots_added = stats["new_snapshots"]
        run.flags_added = 0
        run.errors_count = stats["off_errors"]
        run.status = "complete"
        run.notes = (
            f"phase={phase};"
            f"panel={panel_size};"
            f"categories={stats['categories_checked']}"
        )
        session.commit()

    except Exception as e:
        logger.error(f"[live_tracker] Fatal error: {e}", exc_info=True)
        run.finished_at = datetime.now(timezone.utc)
        run.status = "failed"
        run.notes = f"error={str(e)[:200]}"
        session.commit()
        stats["off_errors"] += 1

    finally:
        session.close()

    logger.info(
        f"[live_tracker] {stats['phase']} phase | "
        f"panel={stats['panel_size']} | "
        f"+{stats['new_products']} products | "
        f"+{stats['new_snapshots']} snapshots | "
        f"{stats['off_errors']} errors"
    )
    return stats


if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(level=_logging.INFO)
    result = run_live_update()
    print(result)
