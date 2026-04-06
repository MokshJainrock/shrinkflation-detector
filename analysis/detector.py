"""
Shrinkflation detector — compares latest snapshots vs 30 days ago,
flags products where size decreased but price stayed the same or increased.
"""

from datetime import datetime, timezone, timedelta

from sqlalchemy import func

from config.settings import SIZE_DECREASE_THRESHOLD_PCT, HIGH_SEVERITY_PCT, MEDIUM_SEVERITY_PCT, LOOKBACK_DAYS
from db.models import Product, ProductSnapshot, ShrinkflationFlag, get_session


def compute_severity(real_increase_pct: float) -> str:
    if real_increase_pct > HIGH_SEVERITY_PCT:
        return "HIGH"
    elif real_increase_pct > MEDIUM_SEVERITY_PCT:
        return "MEDIUM"
    return "LOW"


def run_detection():
    """Compare latest vs 30-day-old snapshots for all products."""
    session = get_session()
    now = datetime.now(timezone.utc)
    lookback = now - timedelta(days=LOOKBACK_DAYS)

    products = session.query(Product).all()
    flagged = 0
    skipped = 0

    print(f"Running shrinkflation detection on {len(products)} products...")

    for product in products:
        try:
            # Get latest snapshot
            latest = (
                session.query(ProductSnapshot)
                .filter(ProductSnapshot.product_id == product.id)
                .order_by(ProductSnapshot.scraped_at.desc())
                .first()
            )

            # Get oldest snapshot within lookback window
            old = (
                session.query(ProductSnapshot)
                .filter(
                    ProductSnapshot.product_id == product.id,
                    ProductSnapshot.scraped_at <= lookback,
                )
                .order_by(ProductSnapshot.scraped_at.desc())
                .first()
            )

            if not latest or not old:
                skipped += 1
                continue

            # Need size data for both
            if not latest.size_value or not old.size_value:
                skipped += 1
                continue
            if latest.size_value <= 0 or old.size_value <= 0:
                skipped += 1
                continue

            # Check if size decreased
            size_change_pct = ((old.size_value - latest.size_value) / old.size_value) * 100
            if size_change_pct < SIZE_DECREASE_THRESHOLD_PCT:
                continue  # Size didn't decrease enough

            # Compute real price increase
            old_price = old.price if old.price and old.price > 0 else None
            new_price = latest.price if latest.price and latest.price > 0 else None

            if old_price and new_price:
                old_ppu = old_price / old.size_value
                new_ppu = new_price / latest.size_value
                real_increase_pct = ((new_ppu - old_ppu) / old_ppu) * 100
            else:
                # No price data — still flag the size decrease, estimate from size alone
                real_increase_pct = size_change_pct  # Size shrink = hidden price increase

            severity = compute_severity(real_increase_pct)

            # Check for existing flag to avoid duplicates
            existing = (
                session.query(ShrinkflationFlag)
                .filter_by(product_id=product.id)
                .order_by(ShrinkflationFlag.detected_at.desc())
                .first()
            )
            if existing and existing.new_size == latest.size_value:
                continue  # Already flagged this size change

            flag = ShrinkflationFlag(
                product_id=product.id,
                old_size=old.size_value,
                new_size=latest.size_value,
                old_price=old_price,
                new_price=new_price,
                real_price_increase_pct=round(real_increase_pct, 2),
                severity=severity,
                retailer=product.retailer,
            )
            session.add(flag)
            flagged += 1

        except Exception as e:
            skipped += 1
            continue

    session.commit()
    session.close()
    print(f"Detection complete: {flagged} new flags, {skipped} skipped (incomplete data)")
    return flagged


if __name__ == "__main__":
    run_detection()
