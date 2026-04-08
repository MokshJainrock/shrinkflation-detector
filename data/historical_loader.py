"""
Historical shrinkflation case loader.

Loads documented cases from verified_cases.py into the database.
This module is the only place that creates rows with:
  - data_source = "documented_historical"
  - flag_source = "documented_historical"
  - observation_type = "documented_reference"

Design guarantees:
  - Idempotent: safe to call on every app startup.
  - Non-destructive: never drops tables or touches live scan data.
  - Version-aware: when HISTORICAL_DATA_VERSION changes, only
    documented_historical rows are deleted and re-loaded.
  - Evidence-traceable: every ShrinkflationFlag links back to the
    two ProductSnapshot rows that define the before/after state.

Snapshot timestamp convention:
  - "before" snapshot: datetime(year, 1, 1) — start of documented year
  - "after"  snapshot: datetime(year, 7, 1) — mid-year approximation
  Both carry observation_type="documented_reference" to signal that
  these are year-level approximations from published research, not
  real-time API observations.

Source quality tiers (informational — recorded in retailer field):
  Tier 1 (institutional): BLS, Consumer Reports, mouseprint.org, FTC
  Tier 2 (media):         CNN/NYT, WSJ/NPR, NPR, BBC, NYT, WSJ
  Tier 3 (community):     r/shrinkflation, Fooducate
  r/shrinkflation entries are real observations but lack institutional
  verification. They are loaded with the same schema but the source
  field makes the provenance auditable.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.exc import IntegrityError

from db.models import (
    Base, IngestionRun, Product, ProductSnapshot, ShrinkflationFlag,
    get_engine, get_session, init_db, resolve_unit_family,
)

logger = logging.getLogger(__name__)

# Bump this when verified_cases.py data changes materially.
# The loader will delete all documented_historical rows and re-insert.
# Live scan data (live_openfoodfacts, live_kroger) is never affected.
HISTORICAL_DATA_VERSION = 4

DATA_SOURCE = "documented_historical"
OBSERVATION_TYPE = "documented_reference"
FLAG_SOURCE = "documented_historical"


# ---------------------------------------------------------------------------
# Severity thresholds — applied only to documented historical cases
# where price data is real. These differ from settings.py thresholds
# to produce a meaningful distribution across the 531 documented cases.
# Distribution at time of writing:
#   HIGH   (>= 20% ppu increase): ~130 cases
#   MEDIUM (>=  8% ppu increase): ~210 cases
#   LOW    (>  0% ppu increase):  ~190 cases
#   NONE   (  0% — size shrank, price held): stable-price shrinkflation
# ---------------------------------------------------------------------------
_HIGH_THRESHOLD = 20.0    # price-per-unit increase >= 20%
_MEDIUM_THRESHOLD = 8.0   # price-per-unit increase >= 8%


def _compute_severity(ppu_increase_pct: float) -> str:
    if ppu_increase_pct >= _HIGH_THRESHOLD:
        return "HIGH"
    if ppu_increase_pct >= _MEDIUM_THRESHOLD:
        return "MEDIUM"
    return "LOW"


def _make_identity_key(brand: str, name: str) -> str:
    return f"{brand.strip().lower()}::{name.strip().lower()}"


def _make_dedupe_key(product_id: int, old_size: float, new_size: float) -> str:
    return f"{product_id}::{old_size}::{new_size}::documented_historical"


# ---------------------------------------------------------------------------
# Version tracking via IngestionRun
# ---------------------------------------------------------------------------

def _get_loaded_version(session) -> Optional[int]:
    """Return the HISTORICAL_DATA_VERSION from the most recent completed load."""
    run = (
        session.query(IngestionRun)
        .filter_by(source="historical_load", phase="fill", status="complete")
        .order_by(IngestionRun.finished_at.desc())
        .first()
    )
    if not run or not run.notes:
        return None
    # notes format: "version=N;..."
    for part in run.notes.split(";"):
        if part.startswith("version="):
            try:
                return int(part.split("=", 1)[1])
            except (ValueError, IndexError):
                pass
    return None


def _start_run(session) -> IngestionRun:
    run = IngestionRun(
        source="historical_load",
        phase="fill",
        status="running",
        notes=f"version={HISTORICAL_DATA_VERSION}",
    )
    session.add(run)
    session.commit()
    return run


def _finish_run(session, run: IngestionRun, stats: dict, error: str = None):
    run.finished_at = datetime.now(timezone.utc)
    run.products_added = stats.get("products_added", 0)
    run.snapshots_added = stats.get("snapshots_added", 0)
    run.flags_added = stats.get("flags_added", 0)
    run.errors_count = stats.get("errors", 0)
    run.status = "failed" if error else "complete"
    if error:
        run.notes = f"version={HISTORICAL_DATA_VERSION};error={error[:200]}"
    session.commit()


# ---------------------------------------------------------------------------
# Selective historical-data wipe (non-destructive to live data)
# ---------------------------------------------------------------------------

def _delete_historical_data(session) -> int:
    """
    Delete all rows with data_source="documented_historical".
    Returns the number of Product rows deleted (cascade deletes snapshots/flags).

    Live scan rows (live_openfoodfacts, live_kroger) are never touched.
    """
    # Delete flags first (no FK cascade in SQLite by default)
    hist_product_ids = [
        pid for (pid,) in
        session.query(Product.id).filter_by(data_source=DATA_SOURCE).all()
    ]
    if not hist_product_ids:
        return 0

    deleted_flags = (
        session.query(ShrinkflationFlag)
        .filter(ShrinkflationFlag.product_id.in_(hist_product_ids))
        .delete(synchronize_session=False)
    )
    deleted_snaps = (
        session.query(ProductSnapshot)
        .filter(ProductSnapshot.product_id.in_(hist_product_ids))
        .delete(synchronize_session=False)
    )
    deleted_products = (
        session.query(Product)
        .filter(Product.id.in_(hist_product_ids))
        .delete(synchronize_session=False)
    )
    session.commit()
    logger.info(
        f"[historical_loader] Cleared {deleted_products} products, "
        f"{deleted_snaps} snapshots, {deleted_flags} flags (documented_historical)"
    )
    return deleted_products


# ---------------------------------------------------------------------------
# Core loader
# ---------------------------------------------------------------------------

def load_historical_cases(force_reload: bool = False) -> dict:
    """
    Idempotent loader for documented shrinkflation cases.

    Behaviour:
    - If historical data is already loaded at the current HISTORICAL_DATA_VERSION:
      returns immediately (no-op).
    - If the version has changed (or force_reload=True):
      deletes all documented_historical rows, then re-inserts.
    - If the DB is empty:
      inserts from scratch.

    Returns a stats dict:
      {products_added, snapshots_added, flags_added,
       skipped_duplicates, errors, action}
    """
    from data.verified_cases import VERIFIED_CASES, STABLE_PRODUCTS

    init_db()
    session = get_session()
    stats = {
        "products_added": 0,
        "snapshots_added": 0,
        "flags_added": 0,
        "skipped_duplicates": 0,
        "errors": 0,
        "action": "no-op",
    }

    try:
        loaded_version = _get_loaded_version(session)
        already_loaded = (loaded_version == HISTORICAL_DATA_VERSION)

        if already_loaded and not force_reload:
            logger.info(
                f"[historical_loader] Historical data at version "
                f"{HISTORICAL_DATA_VERSION} already loaded — skipping."
            )
            session.close()
            stats["action"] = "skipped"
            return stats

        if loaded_version is not None and loaded_version != HISTORICAL_DATA_VERSION:
            logger.info(
                f"[historical_loader] Version change "
                f"({loaded_version} → {HISTORICAL_DATA_VERSION}) — "
                f"clearing documented_historical data."
            )
            _delete_historical_data(session)
            stats["action"] = "version-reload"
        elif force_reload:
            logger.info("[historical_loader] Force reload — clearing documented_historical data.")
            _delete_historical_data(session)
            stats["action"] = "force-reload"
        else:
            stats["action"] = "fresh-load"

        run = _start_run(session)
        error_msg = None

        try:
            _load_verified_cases(session, VERIFIED_CASES, stats)
            _load_stable_products(session, STABLE_PRODUCTS, stats)
        except Exception as e:
            error_msg = str(e)
            stats["errors"] += 1
            logger.error(f"[historical_loader] Load failed: {e}", exc_info=True)

        _finish_run(session, run, stats, error=error_msg)

        print(
            f"[historical_loader] Done — {stats['action']}: "
            f"{stats['products_added']} products, "
            f"{stats['snapshots_added']} snapshots, "
            f"{stats['flags_added']} flags, "
            f"{stats['skipped_duplicates']} skipped, "
            f"{stats['errors']} errors"
        )
        return stats

    finally:
        session.close()


# ---------------------------------------------------------------------------
# VERIFIED_CASES loader
# ---------------------------------------------------------------------------

def _load_verified_cases(session, cases: list, stats: dict):
    """Load shrinkflation cases. Each case produces: Product + 2 snapshots + 1 flag."""
    seen_products = set()  # (name_str, brand) — skip duplicate brand/name combos

    for case in cases:
        try:
            brand, name, category, old_size, new_size, unit, old_price, new_price, year, source = case
        except ValueError:
            logger.warning(f"[historical_loader] Malformed case tuple (skipping): {case}")
            stats["errors"] += 1
            continue

        product_name = f"{brand} {name}"
        key = (brand.strip(), product_name.strip())
        if key in seen_products:
            # Same brand+name appeared twice in VERIFIED_CASES — skip duplicate.
            stats["skipped_duplicates"] += 1
            continue
        seen_products.add(key)

        # Validate sizes
        if not old_size or not new_size or old_size <= 0 or new_size <= 0:
            logger.warning(f"[historical_loader] Invalid size for {product_name!r} — skipping")
            stats["errors"] += 1
            continue
        if new_size >= old_size:
            logger.warning(
                f"[historical_loader] {product_name!r}: new_size ({new_size}) >= old_size ({old_size}) "
                f"— not a size decrease, skipping flag (product still loaded)"
            )

        # Validate prices — historical loader requires both or neither
        has_prices = (
            old_price is not None and new_price is not None
            and old_price > 0 and new_price > 0
        )
        if not has_prices:
            logger.warning(
                f"[historical_loader] {product_name!r}: price data missing "
                f"(old={old_price}, new={new_price}) — product loaded, no flag created"
            )

        identity_key = _make_identity_key(brand, product_name)

        # --- Product ---
        product = _get_or_create_product(
            session, product_name, brand, category, unit, source, identity_key
        )
        if product is None:
            stats["errors"] += 1
            continue

        was_new_product = getattr(product, "_was_created", False)
        if was_new_product:
            stats["products_added"] += 1

        # --- Snapshots ---
        # Only create if the product was just inserted (idempotent: skip if already exist)
        old_snap_id, new_snap_id = None, None
        if was_new_product:
            old_snap_id, new_snap_id = _create_before_after_snapshots(
                session, product.id, old_size, new_size, unit, old_price, new_price, year, stats
            )

        # --- Flag ---
        if new_size < old_size and has_prices:
            old_ppu = old_price / old_size
            new_ppu = new_price / new_size
            ppu_increase = ((new_ppu - old_ppu) / old_ppu) * 100

            dedupe_key = _make_dedupe_key(product.id, old_size, new_size)
            flag_exists = (
                session.query(ShrinkflationFlag)
                .filter_by(dedupe_key=dedupe_key)
                .first()
            )
            if not flag_exists:
                flag = ShrinkflationFlag(
                    product_id=product.id,
                    flag_source=FLAG_SOURCE,
                    old_size=old_size,
                    new_size=new_size,
                    size_unit=unit,
                    old_price=old_price,
                    new_price=new_price,
                    has_price_evidence=True,
                    price_per_unit_increase_pct=round(ppu_increase, 2),
                    severity=_compute_severity(ppu_increase),
                    evidence_old_snapshot_id=old_snap_id,
                    evidence_new_snapshot_id=new_snap_id,
                    detected_at=datetime(year, 7, 1, tzinfo=timezone.utc),
                    dedupe_key=dedupe_key,
                )
                session.add(flag)
                try:
                    session.flush()
                    stats["flags_added"] += 1
                except IntegrityError:
                    session.rollback()
                    stats["skipped_duplicates"] += 1

    session.commit()


# ---------------------------------------------------------------------------
# STABLE_PRODUCTS loader
# ---------------------------------------------------------------------------

def _load_stable_products(session, stable_products: list, stats: dict):
    """
    Load stable (non-shrinking) baseline products.
    Each stable product gets ONE snapshot, NO flag.
    These serve as comparison controls in analysis queries.
    """
    seen_products: set = set()

    for item in stable_products:
        try:
            brand, name, category, size, unit, price = item
        except ValueError:
            logger.warning(f"[historical_loader] Malformed stable tuple (skipping): {item}")
            stats["errors"] += 1
            continue

        product_name = f"{brand} {name}"
        key = (brand.strip(), product_name.strip())
        if key in seen_products:
            stats["skipped_duplicates"] += 1
            continue
        seen_products.add(key)

        if not size or size <= 0:
            logger.warning(f"[historical_loader] Invalid size for stable {product_name!r} — skipping")
            stats["errors"] += 1
            continue

        identity_key = _make_identity_key(brand, product_name)
        product = _get_or_create_product(
            session, product_name, brand, category, unit, "documented-stable", identity_key
        )
        if product is None:
            stats["errors"] += 1
            continue

        was_new = getattr(product, "_was_created", False)
        if was_new:
            stats["products_added"] += 1
            ppu = round(price / size, 4) if (price and size > 0) else None
            snap = ProductSnapshot(
                product_id=product.id,
                size_value=size,
                size_unit=unit,
                size_unit_family=resolve_unit_family(unit),
                price=price if price and price > 0 else None,
                price_per_unit=ppu,
                data_source=DATA_SOURCE,
                observation_type=OBSERVATION_TYPE,
                scraped_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )
            session.add(snap)
            try:
                session.flush()
                stats["snapshots_added"] += 1
            except IntegrityError:
                session.rollback()

    session.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_product(
    session, name: str, brand: str, category: str,
    unit: str, source: str, identity_key: str
) -> Optional[Product]:
    """
    Return existing Product or create a new one.
    Sets ._was_created=True on the returned object if it was just inserted.
    Returns None on unrecoverable error.
    """
    existing = (
        session.query(Product)
        .filter_by(name=name, brand=brand, data_source=DATA_SOURCE)
        .first()
    )
    if existing:
        existing._was_created = False
        return existing

    product = Product(
        name=name,
        brand=brand,
        category=category,
        barcode=None,            # Never fabricate barcodes
        data_source=DATA_SOURCE,
        retailer=source,         # e.g. "BLS/Consumer Reports", "mouseprint.org"
        identity_key=identity_key,
        image_url=None,
    )
    session.add(product)
    try:
        session.flush()
        product._was_created = True
        return product
    except IntegrityError:
        session.rollback()
        # Race or duplicate — try to fetch the existing row
        existing = (
            session.query(Product)
            .filter_by(name=name, brand=brand, data_source=DATA_SOURCE)
            .first()
        )
        if existing:
            existing._was_created = False
            return existing
        logger.error(f"[historical_loader] Could not insert or find product {name!r}")
        return None


def _create_before_after_snapshots(
    session, product_id: int,
    old_size: float, new_size: float, unit: str,
    old_price: Optional[float], new_price: Optional[float],
    year: int, stats: dict
) -> tuple:
    """
    Create the before (Jan 1) and after (Jul 1) snapshots for a documented case.
    Returns (old_snapshot_id, new_snapshot_id) or (None, None) on failure.

    Timestamps are year-level approximations — observation_type="documented_reference"
    makes this explicit. The Jan 1 / Jul 1 convention is documented here and in
    the model docstring so future readers know these are not real observation times.
    """
    unit_family = resolve_unit_family(unit)

    old_ppu = round(old_price / old_size, 4) if (old_price and old_size > 0) else None
    new_ppu = round(new_price / new_size, 4) if (new_price and new_size > 0) else None

    old_snap = ProductSnapshot(
        product_id=product_id,
        size_value=old_size,
        size_unit=unit,
        size_unit_family=unit_family,
        price=old_price,
        price_per_unit=old_ppu,
        data_source=DATA_SOURCE,
        observation_type=OBSERVATION_TYPE,
        scraped_at=datetime(year, 1, 1, tzinfo=timezone.utc),
    )
    new_snap = ProductSnapshot(
        product_id=product_id,
        size_value=new_size,
        size_unit=unit,
        size_unit_family=unit_family,
        price=new_price,
        price_per_unit=new_ppu,
        data_source=DATA_SOURCE,
        observation_type=OBSERVATION_TYPE,
        scraped_at=datetime(year, 7, 1, tzinfo=timezone.utc),
    )
    session.add(old_snap)
    session.add(new_snap)
    try:
        session.flush()
        stats["snapshots_added"] += 2
        return old_snap.id, new_snap.id
    except IntegrityError:
        session.rollback()
        return None, None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    result = load_historical_cases(force_reload=force)
    print(result)
