"""
Shrinkflation detector — flags products when a newer live size observation
shows a smaller package than the previous live size observation.
"""

from datetime import datetime, timezone, timedelta

from config.settings import (
    HIGH_SEVERITY_PCT,
    MEDIUM_SEVERITY_PCT,
    PRICE_MATCH_WINDOW_DAYS,
    SIZE_DECREASE_THRESHOLD_PCT,
)
from db.models import Product, ProductSnapshot, ShrinkflationFlag, get_session
from scraper.source_utils import ensure_utc


def compute_severity(real_increase_pct: float) -> str:
    if real_increase_pct > HIGH_SEVERITY_PCT:
        return "HIGH"
    elif real_increase_pct > MEDIUM_SEVERITY_PCT:
        return "MEDIUM"
    return "LOW"


def _get_latest_two_size_snapshots(session, product_id: int) -> list[ProductSnapshot]:
    return (
        session.query(ProductSnapshot)
        .filter(
            ProductSnapshot.product_id == product_id,
            ProductSnapshot.snapshot_type == "size",
            ProductSnapshot.size_value.isnot(None),
            ProductSnapshot.size_unit.isnot(None),
        )
        .order_by(ProductSnapshot.scraped_at.desc())
        .limit(2)
        .all()
    )


def _get_closest_price_snapshot(session, product_id: int, pivot: datetime) -> ProductSnapshot | None:
    pivot_utc = ensure_utc(pivot)
    if pivot_utc is None:
        return None

    window_start = pivot_utc - timedelta(days=PRICE_MATCH_WINDOW_DAYS)
    window_end = pivot_utc + timedelta(days=PRICE_MATCH_WINDOW_DAYS)
    candidates = (
        session.query(ProductSnapshot)
        .filter(
            ProductSnapshot.product_id == product_id,
            ProductSnapshot.snapshot_type == "price",
            ProductSnapshot.price.isnot(None),
            ProductSnapshot.scraped_at >= window_start,
            ProductSnapshot.scraped_at <= window_end,
        )
        .all()
    )
    if not candidates:
        return None
    return min(candidates, key=lambda snapshot: abs(ensure_utc(snapshot.scraped_at) - pivot_utc))


def run_detection():
    """Compare the two newest size snapshots for all live products."""
    session = get_session()
    products = session.query(Product).filter(Product.retailer == "openfoodfacts").all()
    flagged = 0
    skipped = 0

    print(f"Running shrinkflation detection on {len(products)} products...")

    for product in products:
        try:
            size_snapshots = _get_latest_two_size_snapshots(session, product.id)
            if len(size_snapshots) < 2:
                skipped += 1
                continue
            latest, old = size_snapshots[0], size_snapshots[1]

            if not latest.size_value or not old.size_value:
                skipped += 1
                continue
            if latest.size_value <= 0 or old.size_value <= 0:
                skipped += 1
                continue
            if latest.size_unit != old.size_unit:
                skipped += 1
                continue

            size_change_pct = ((old.size_value - latest.size_value) / old.size_value) * 100
            if size_change_pct < SIZE_DECREASE_THRESHOLD_PCT:
                continue

            existing = (
                session.query(ShrinkflationFlag)
                .filter_by(
                    product_id=product.id,
                    old_size=old.size_value,
                    new_size=latest.size_value,
                    size_unit=latest.size_unit,
                )
                .first()
            )
            if existing:
                continue

            old_price_snapshot = _get_closest_price_snapshot(session, product.id, old.scraped_at)
            new_price_snapshot = _get_closest_price_snapshot(session, product.id, latest.scraped_at)
            old_price = old_price_snapshot.price if old_price_snapshot else None
            new_price = new_price_snapshot.price if new_price_snapshot else None

            if old_price and new_price and old_price > 0 and new_price > 0:
                old_ppu = old_price / old.size_value
                new_ppu = new_price / latest.size_value
                if old_ppu <= 0:
                    real_increase_pct = size_change_pct
                    evidence_type = "size_only"
                else:
                    real_increase_pct = ((new_ppu - old_ppu) / old_ppu) * 100
                    evidence_type = "size_and_price"
            else:
                real_increase_pct = size_change_pct
                evidence_type = "size_only"

            severity = compute_severity(real_increase_pct)

            flag = ShrinkflationFlag(
                product_id=product.id,
                old_size=old.size_value,
                new_size=latest.size_value,
                old_price=old_price,
                new_price=new_price,
                real_price_increase_pct=round(real_increase_pct, 2),
                severity=severity,
                size_unit=latest.size_unit,
                evidence_type=evidence_type,
                detected_at=latest.scraped_at or datetime.now(timezone.utc),
                retailer=product.retailer,
            )
            session.add(flag)
            flagged += 1

        except Exception:
            skipped += 1
            continue

    session.commit()
    session.close()
    print(f"Detection complete: {flagged} new flags, {skipped} skipped (incomplete data)")
    return flagged


if __name__ == "__main__":
    run_detection()
