"""
Open Food Facts scraper — pulls product size/quantity data from the free API.
No API key required.
"""

import re
import time
import logging

import requests

from config.settings import OFF_BASE_URL, OFF_CATEGORIES
from db.models import Product, ProductSnapshot, get_session

logger = logging.getLogger(__name__)


def parse_quantity(quantity_str: str | None) -> tuple[float | None, str | None]:
    """Parse a quantity string like '250 g' or '1.5 L' into (value, unit)."""
    if not quantity_str:
        return None, None
    match = re.search(r"([\d.]+)\s*([a-zA-Z]+)", str(quantity_str))
    if match:
        try:
            return float(match.group(1)), match.group(2).lower()
        except ValueError:
            return None, None
    return None, None


def fetch_category(category: str, page: int = 1, page_size: int = 50, retries: int = 3) -> list[dict]:
    """Fetch products from Open Food Facts for a given category with retry logic."""
    params = {
        "categories_tags_en": category,
        "fields": "product_name,brands,quantity,product_quantity,product_quantity_unit,"
                  "categories,image_url,code",
        "page": page,
        "page_size": page_size,
        "json": 1,
    }

    for attempt in range(retries):
        try:
            resp = requests.get(OFF_BASE_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get("products", [])
        except requests.RequestException as e:
            wait = 2 ** attempt
            logger.warning(f"Attempt {attempt + 1}/{retries} failed for '{category}': {e}. Retrying in {wait}s...")
            time.sleep(wait)

    logger.error(f"All {retries} attempts failed for category '{category}'")
    return []


def scrape_openfoodfacts():
    """Main scraper — iterates through all categories and stores snapshots."""
    session = get_session()
    total_new = 0
    total_snapshots = 0

    print(f"Scraping Open Food Facts — {len(OFF_CATEGORIES)} categories")

    for category in OFF_CATEGORIES:
        print(f"  Scraping: {category}...")
        products = fetch_category(category)
        print(f"  Got {len(products)} products")

        for raw in products:
            name = raw.get("product_name", "").strip()
            brand = raw.get("brands", "").strip()
            if not name:
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

            # Upsert product (DB-agnostic)
            existing = (
                session.query(Product)
                .filter_by(name=name, brand=brand or "Unknown", retailer="openfoodfacts")
                .first()
            )
            if not existing:
                existing = Product(
                    name=name,
                    brand=brand or "Unknown",
                    category=category,
                    barcode=raw.get("code"),
                    retailer="openfoodfacts",
                    image_url=raw.get("image_url"),
                )
                session.add(existing)
                session.flush()
                total_new += 1

            # Create snapshot
            snapshot = ProductSnapshot(
                product_id=existing.id,
                size_value=size_value,
                size_unit=size_unit,
                price=None,  # OFF doesn't have prices
                price_per_unit=None,
            )
            session.add(snapshot)
            total_snapshots += 1

        session.commit()
        time.sleep(1)  # Rate limit

    session.close()
    print(f"\nOpen Food Facts scrape complete: {total_new} new products, {total_snapshots} snapshots")
    return total_new, total_snapshots


if __name__ == "__main__":
    scrape_openfoodfacts()
