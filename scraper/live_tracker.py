"""
Live price tracker — fetches current product data from free public APIs
and checks for size/price changes since last check.

Called automatically by the dashboard on a schedule.
Uses Open Food Facts (free, no API key) for product size data.
"""

import time
import logging
import requests
import re
from datetime import datetime, timezone, timedelta

from db.models import Product, ProductSnapshot, ShrinkflationFlag, get_session, init_db

logger = logging.getLogger(__name__)

# ---- Open Food Facts API ----
OFF_SEARCH_URL = "https://world.openfoodfacts.org/api/v2/search"

# Required by OFF API — anonymous requests without User-Agent get 503
OFF_HEADERS = {
    "User-Agent": "ShrinkflationDetector/1.0 (https://github.com/MokshJainrock/shrinkflation-detector)"
}

# Categories + search terms to check for size changes
TRACKED_CATEGORIES = [
    "chips", "cereal", "ice-cream", "yogurt", "cookies",
    "crackers", "pasta", "candy", "bread", "coffee",
    "ketchup", "mayonnaise", "peanut-butter", "juice",
    "frozen-meals", "detergent", "soap",
]


def parse_quantity(quantity_str):
    """Parse '250 g' or '16 fl oz' → (value, unit)."""
    if not quantity_str:
        return None, None
    match = re.search(r"([\d.]+)\s*([a-zA-Z\s]+)", str(quantity_str))
    if match:
        try:
            return float(match.group(1)), match.group(2).strip().lower()
        except ValueError:
            return None, None
    return None, None


def fetch_live_products(category, page_size=50):
    """Fetch latest products from Open Food Facts for a category."""
    try:
        resp = requests.get(
            OFF_SEARCH_URL,
            params={
                "categories_tags_en": category,
                "fields": "product_name,brands,quantity,product_quantity,"
                          "product_quantity_unit,code,image_url,last_modified_t",
                "page_size": page_size,
                "sort_by": "last_modified_t",
                "json": 1,
            },
            headers=OFF_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("products", [])
    except Exception as e:
        logger.warning(f"Failed to fetch {category}: {e}")
        return []


def run_live_update(max_categories=5):
    """
    Fetch the latest product data from Open Food Facts and check for changes.
    Returns a dict with update stats.

    This is designed to be called periodically (e.g., once per day or on dashboard load).
    It only checks a subset of categories each time to stay within free API limits.
    """
    init_db()
    session = get_session()

    stats = {
        "new_products": 0,
        "new_snapshots": 0,
        "size_changes_detected": 0,
        "categories_checked": 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Rotate through categories — check different ones each run
    # Uses minute-of-day so each 60s tick scans different categories
    now_utc = datetime.now(timezone.utc)
    minute_offset = (now_utc.hour * 60 + now_utc.minute) % len(TRACKED_CATEGORIES)
    categories_to_check = []
    for i in range(max_categories):
        idx = (minute_offset + i) % len(TRACKED_CATEGORIES)
        categories_to_check.append(TRACKED_CATEGORIES[idx])

    for category in categories_to_check:
        products = fetch_live_products(category)
        stats["categories_checked"] += 1

        for raw in products:
            name = raw.get("product_name", "").strip()
            brand = raw.get("brands", "").strip()
            if not name or not brand:
                continue

            # Parse size
            size_value, size_unit = None, None
            if raw.get("product_quantity"):
                try:
                    size_value = float(raw["product_quantity"])
                    size_unit = raw.get("product_quantity_unit", "g")
                except (ValueError, TypeError):
                    size_value, size_unit = parse_quantity(raw.get("quantity"))
            else:
                size_value, size_unit = parse_quantity(raw.get("quantity"))

            if not size_value:
                continue

            # Find or create product
            existing = (
                session.query(Product)
                .filter_by(name=name, brand=brand, retailer="openfoodfacts")
                .first()
            )
            if not existing:
                existing = Product(
                    name=name,
                    brand=brand,
                    category=category.replace("-", " "),
                    barcode=raw.get("code"),
                    retailer="openfoodfacts",
                    image_url=raw.get("image_url"),
                )
                session.add(existing)
                session.flush()
                stats["new_products"] += 1

            # Get last snapshot to check for changes
            last_snap = (
                session.query(ProductSnapshot)
                .filter_by(product_id=existing.id)
                .order_by(ProductSnapshot.scraped_at.desc())
                .first()
            )

            # Only create new snapshot if it's been > 1 hour since last one
            if last_snap and last_snap.scraped_at:
                time_since = datetime.now(timezone.utc) - last_snap.scraped_at.replace(tzinfo=timezone.utc) \
                    if last_snap.scraped_at.tzinfo is None else datetime.now(timezone.utc) - last_snap.scraped_at
                if time_since < timedelta(hours=1):
                    continue

            # Create snapshot
            snapshot = ProductSnapshot(
                product_id=existing.id,
                size_value=size_value,
                size_unit=size_unit,
                price=None,
                price_per_unit=None,
            )
            session.add(snapshot)
            stats["new_snapshots"] += 1

            # Check for size change vs previous snapshot
            if last_snap and last_snap.size_value and size_value:
                old_size = last_snap.size_value
                new_size = size_value

                # Same unit check
                if last_snap.size_unit == size_unit and old_size != new_size:
                    size_change_pct = ((new_size - old_size) / old_size) * 100

                    # Shrinkflation: size decreased
                    if size_change_pct < -2:  # More than 2% decrease
                        real_increase = abs(size_change_pct)  # Without price data, use size decrease as proxy

                        if real_increase > 10:
                            severity = "HIGH"
                        elif real_increase > 5:
                            severity = "MEDIUM"
                        else:
                            severity = "LOW"

                        flag = ShrinkflationFlag(
                            product_id=existing.id,
                            old_size=old_size,
                            new_size=new_size,
                            old_price=None,
                            new_price=None,
                            real_price_increase_pct=round(real_increase, 2),
                            severity=severity,
                            detected_at=datetime.now(timezone.utc),
                            retailer="openfoodfacts",
                        )
                        session.add(flag)
                        stats["size_changes_detected"] += 1

        session.commit()
        time.sleep(1)  # Rate limit: 1 request per second

    session.close()
    return stats


if __name__ == "__main__":
    print("Running live tracker update...")
    result = run_live_update()
    print(f"Done: {result}")
