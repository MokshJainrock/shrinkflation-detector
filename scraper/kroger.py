"""
Kroger price enrichment.

What this module does:
  - authenticates with Kroger OAuth2 API
  - searches for products matching our existing DB products
  - inserts ProductSnapshot rows carrying a real, API-sourced price
  - parses Kroger's item.size field for the product's size at time of query

What this module does NOT do:
  - create new Product rows (price enrichment only, never discovery)
  - create ShrinkflationFlags
  - copy size from the DB (uses Kroger's own reported item.size)
  - use fuzzy matching as primary identity logic
  - mark success when price is missing

Identity matching order:
  1. barcode (Product.barcode == Kroger item UPC)
  2. identity_key (normalized brand::name lookup)
  3. skip — no fallback to fuzzy matching

Schema fields used:
  ProductSnapshot.data_source      = "live_kroger"
  ProductSnapshot.observation_type = "real_observed"
  ProductSnapshot.size_unit_family = resolved via resolve_unit_family()
"""

from __future__ import annotations

import logging
import re
import time
from base64 import b64encode
from datetime import datetime, timezone
from typing import Optional

import requests

from config.settings import KROGER_TOKEN_URL, KROGER_SEARCH_URL
from db.models import (
    IngestionRun, Product, ProductSnapshot, get_session, resolve_unit_family,
)

logger = logging.getLogger(__name__)

# Default location for price queries — prices are location-specific on Kroger API
KROGER_LOCATION_ID = "01400513"  # Kroger On the Rhine, Cincinnati OH

# Categories to rotate through each tick
_KROGER_CATEGORIES = [
    "chips", "cereal", "juice", "cookies", "yogurt", "coffee",
    "pasta", "crackers", "bread", "ketchup", "ice cream",
    "peanut butter", "mayonnaise", "detergent", "candy",
]

DATA_SOURCE = "live_kroger"

# Module-level token cache — persists across calls within a process
_token_cache: dict = {"access_token": None, "expires_at": 0.0}


# ---------------------------------------------------------------------------
# Credentials (lazy read — safe for Streamlit Cloud where st.secrets is
# unavailable at import time)
# ---------------------------------------------------------------------------

def _get_kroger_credentials() -> tuple:
    """Read Kroger credentials at call time (not import time)."""
    try:
        import streamlit as st
        cid = st.secrets["KROGER_CLIENT_ID"]
        csec = st.secrets["KROGER_CLIENT_SECRET"]
        if cid and csec:
            return cid, csec
    except Exception:
        pass

    import os
    return os.getenv("KROGER_CLIENT_ID", ""), os.getenv("KROGER_CLIENT_SECRET", "")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def get_kroger_token() -> Optional[str]:
    """Get or refresh the Kroger OAuth2 access token. Returns None if not configured."""
    client_id, client_secret = _get_kroger_credentials()

    if not client_id or not client_secret:
        logger.warning(
            "[kroger] Credentials not configured — skipping. "
            f"CLIENT_ID present: {bool(client_id)}"
        )
        return None

    now = time.time()
    if _token_cache["access_token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["access_token"]

    credentials = b64encode(f"{client_id}:{client_secret}".encode()).decode()
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {credentials}",
    }
    data = {"grant_type": "client_credentials", "scope": "product.compact"}

    try:
        resp = requests.post(KROGER_TOKEN_URL, headers=headers, data=data, timeout=8)
        resp.raise_for_status()
        token_data = resp.json()
        _token_cache["access_token"] = token_data["access_token"]
        _token_cache["expires_at"] = now + token_data.get("expires_in", 1800)
        logger.info("[kroger] Token refreshed successfully")
        return _token_cache["access_token"]
    except requests.RequestException as e:
        logger.error(f"[kroger] Failed to obtain token: {e}")
        return None


# ---------------------------------------------------------------------------
# API search
# ---------------------------------------------------------------------------

def _search_kroger(query: str, token: str, limit: int = 10) -> list:
    """
    Search Kroger product catalog.
    Returns raw Kroger product dicts, or empty list on failure.
    """
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    params = {
        "filter.term": query,
        "filter.limit": limit,
        "filter.locationId": KROGER_LOCATION_ID,
    }
    try:
        resp = requests.get(KROGER_SEARCH_URL, headers=headers, params=params, timeout=8)
        resp.raise_for_status()
        return resp.json().get("data", [])
    except requests.RequestException as e:
        logger.warning(f"[kroger] Search failed for '{query}': {e}")
        return []


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _parse_kroger_size(size_str: Optional[str]) -> tuple:
    """
    Parse Kroger's item.size string (e.g. '14 FL OZ', '9.5 OZ', '1 GL').
    Returns (value, unit) or (None, None).
    """
    if not size_str:
        return None, None
    match = re.search(r"([\d.]+)\s*([a-zA-Z][a-zA-Z\s]*)", str(size_str).strip())
    if match:
        try:
            val = float(match.group(1))
            unit = match.group(2).strip().lower()
            if val > 0:
                return val, unit
        except ValueError:
            pass
    return None, None


def _extract_price_and_size(kroger_item: dict) -> tuple:
    """
    Extract price and size from a Kroger product response dict.

    Returns (price, size_value, size_unit, price_per_unit):
      - price: float from items[0].price.regular (or .promo), None if missing
      - size_value, size_unit: parsed from items[0].size, (None, None) if missing
      - price_per_unit: computed only when both price and size are available

    Does NOT fall back to any DB value or historical data.
    """
    items = kroger_item.get("items", [])
    if not items:
        return None, None, None, None

    item = items[0]
    price_info = item.get("price", {}) or {}

    price = price_info.get("regular")
    if not price:
        price = price_info.get("promo")
    if price:
        try:
            price = float(price)
        except (ValueError, TypeError):
            price = None

    size_value, size_unit = _parse_kroger_size(item.get("size"))

    price_per_unit = None
    if price and size_value and size_value > 0:
        price_per_unit = round(price / size_value, 4)

    return price, size_value, size_unit, price_per_unit


# ---------------------------------------------------------------------------
# Identity resolution (Kroger: match-only, never create)
# ---------------------------------------------------------------------------

def _normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _resolve_existing_product(session, barcode: Optional[str], brand: str, name: str) -> Optional[Product]:
    """
    Find an existing Product by barcode or identity_key.
    Kroger NEVER creates new products — returns None if not found.
    """
    # Step 1: barcode match
    if barcode:
        match = session.query(Product).filter(Product.barcode == barcode.strip()).first()
        if match:
            return match

    # Step 2: identity_key match (live products only)
    identity_key = f"{_normalize(brand)}::{_normalize(name)}"
    match = (
        session.query(Product)
        .filter(
            Product.identity_key == identity_key,
            Product.data_source.in_(["live_openfoodfacts", "live_kroger"]),
        )
        .first()
    )
    return match  # None if not found


# ---------------------------------------------------------------------------
# Main enrichment function
# ---------------------------------------------------------------------------

def scrape_kroger(max_categories: int = 3) -> tuple:
    """
    Enrich existing products with Kroger price data.

    For each category:
      - search Kroger catalog
      - match results to existing DB products (barcode → identity_key)
      - if price returned: insert ProductSnapshot(data_source="live_kroger")
      - if price not returned: log and skip

    Returns (matched_count, snapshots_created) for dashboard compatibility.
    """
    token = get_kroger_token()
    if not token:
        logger.info("[kroger] No credentials — skipping")
        return 0, 0

    session = get_session()
    total_matched = 0
    total_snapshots = 0
    total_price_missing = 0
    errors = 0

    run = IngestionRun(
        source="kroger",
        phase="track",  # Kroger is always price enrichment, never fill-phase discovery
        status="running",
    )
    session.add(run)
    session.commit()

    try:
        # Category rotation — cover different categories each tick
        now_utc = datetime.now(timezone.utc)
        minute_offset = (now_utc.hour * 60 + now_utc.minute) % len(_KROGER_CATEGORIES)
        categories_to_check = []
        for i in range(min(max_categories, len(_KROGER_CATEGORIES))):
            idx = (minute_offset + i) % len(_KROGER_CATEGORIES)
            categories_to_check.append(_KROGER_CATEGORIES[idx])

        logger.info(f"[kroger] Checking categories: {categories_to_check}")
        now = datetime.now(timezone.utc)

        for category in categories_to_check:
            kroger_results = _search_kroger(category, token)
            if not kroger_results:
                errors += 1
                continue

            for kr_item in kroger_results:
                kr_name = (kr_item.get("description") or "").strip()
                kr_brand = (kr_item.get("brand") or "").strip()

                if not kr_name:
                    continue

                # Extract UPC barcode from Kroger response
                kr_barcode = None
                items = kr_item.get("items", [])
                if items:
                    upc = items[0].get("upc", "")
                    if upc:
                        kr_barcode = upc.strip()

                # Strict identity resolution — no fuzzy matching
                product = _resolve_existing_product(session, kr_barcode, kr_brand, kr_name)
                if product is None:
                    # Product not in our panel — skip. Kroger never creates products.
                    continue

                total_matched += 1

                # Extract price and size from Kroger's response
                price, size_value, size_unit, price_per_unit = _extract_price_and_size(kr_item)

                # Price is required — without it, this snapshot is worthless
                if not price:
                    total_price_missing += 1
                    logger.debug(
                        f"[kroger] Price missing for '{kr_name}' — snapshot not created"
                    )
                    continue

                unit_family = resolve_unit_family(size_unit) if size_unit else "unknown"

                snapshot = ProductSnapshot(
                    product_id=product.id,
                    size_value=size_value,       # from Kroger's item.size (may be None)
                    size_unit=size_unit,
                    size_unit_family=unit_family,
                    price=price,                 # real Kroger retail price
                    price_per_unit=price_per_unit,
                    data_source=DATA_SOURCE,
                    observation_type="real_observed",
                    scraped_at=now,
                )
                session.add(snapshot)
                total_snapshots += 1

            session.commit()
            time.sleep(0.5)  # Kroger rate limit

        # Finalize run log
        run.finished_at = datetime.now(timezone.utc)
        run.products_added = 0  # Kroger never adds products
        run.snapshots_added = total_snapshots
        run.flags_added = 0
        run.errors_count = errors
        run.status = "complete"
        run.notes = (
            f"matched={total_matched};"
            f"price_missing={total_price_missing};"
            f"categories={len(categories_to_check)}"
        )
        session.commit()

    except Exception as e:
        logger.error(f"[kroger] Fatal error: {e}", exc_info=True)
        run.finished_at = datetime.now(timezone.utc)
        run.status = "failed"
        run.notes = f"error={str(e)[:200]}"
        session.commit()

    finally:
        session.close()

    logger.info(
        f"[kroger] matched={total_matched} | "
        f"snapshots={total_snapshots} | "
        f"price_missing={total_price_missing} | "
        f"errors={errors}"
    )
    return total_matched, total_snapshots


if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(level=_logging.INFO)
    matched, snaps = scrape_kroger()
    print(f"Done: {matched} matched, {snaps} snapshots")
