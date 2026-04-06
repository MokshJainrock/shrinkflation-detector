"""
Open Food Facts ingestion utilities.

This module is the single source of truth for live product ingestion so that
the CLI, scheduler, and dashboard all apply the same validation and de-duping.
"""

import logging
import time
from datetime import datetime, timezone

import requests

from config.settings import OFF_BASE_URL, OFF_CATEGORIES
from db.models import Product, ProductSnapshot, get_session
from scraper.source_utils import ensure_utc, extract_off_product_payload

logger = logging.getLogger(__name__)

OFF_SEARCH_URLS = [
    "https://world.openfoodfacts.net/api/v2/search",
    OFF_BASE_URL,
]

OFF_HEADERS = {
    "User-Agent": "ShrinkflationDetector/1.0 (contact@shrinkflation.app)",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}


def select_rotating_categories(categories: list[str], max_categories: int | None = None) -> list[str]:
    if not categories:
        return []
    if max_categories is None or max_categories >= len(categories):
        return list(categories)

    now_utc = datetime.now(timezone.utc)
    minute_offset = (now_utc.hour * 60 + now_utc.minute) % len(categories)
    selected = []
    for index in range(max_categories):
        selected.append(categories[(minute_offset + index) % len(categories)])
    return selected


def fetch_category(category: str, page: int = 1, page_size: int = 50, retries: int = 3) -> list[dict]:
    """Fetch one category from Open Food Facts using the documented v2 search API."""
    params = {
        "categories_tags_en": category,
        "fields": (
            "product_name,brands,quantity,product_quantity,product_quantity_unit,"
            "image_url,code,last_modified_t"
        ),
        "page": page,
        "page_size": page_size,
        "sort_by": "last_modified_t",
        "json": 1,
    }

    for url in OFF_SEARCH_URLS:
        for attempt in range(retries):
            try:
                response = requests.get(url, params=params, headers=OFF_HEADERS, timeout=20)
                response.raise_for_status()
                return response.json().get("products", [])
            except requests.RequestException as exc:
                wait_seconds = 2 ** attempt
                logger.warning(
                    "OFF request failed for '%s' via %s (attempt %s/%s): %s",
                    category,
                    url,
                    attempt + 1,
                    retries,
                    exc,
                )
                time.sleep(wait_seconds)

    logger.error("Open Food Facts fetch failed for category '%s'", category)
    return []


def _find_existing_product(session, payload: dict) -> Product | None:
    product = (
        session.query(Product)
        .filter_by(source_key=payload["source_key"], retailer="openfoodfacts")
        .first()
    )
    if product:
        return product

    if payload.get("barcode"):
        product = (
            session.query(Product)
            .filter_by(barcode=payload["barcode"], retailer="openfoodfacts")
            .first()
        )
        if product:
            return product

    return (
        session.query(Product)
        .filter_by(name=payload["name"], brand=payload["brand"], retailer="openfoodfacts")
        .first()
    )


def upsert_live_product(session, payload: dict) -> dict:
    """Insert or update a live OFF product and create a size snapshot only on real size changes."""
    product = _find_existing_product(session, payload)
    created = False
    snapshot_created = False
    size_changed = False
    now_utc = datetime.now(timezone.utc)

    if product is None:
        product = Product(
            name=payload["name"],
            brand=payload["brand"],
            category=payload["category"],
            barcode=payload["barcode"],
            retailer="openfoodfacts",
            source_key=payload["source_key"],
            image_url=payload.get("image_url"),
            last_seen_at=now_utc,
            source_last_modified_at=payload.get("source_last_modified_at"),
        )
        session.add(product)
        session.flush()
        created = True
    else:
        product.name = payload["name"]
        product.brand = payload["brand"]
        product.category = payload["category"]
        product.barcode = payload["barcode"] or product.barcode
        product.image_url = payload.get("image_url") or product.image_url
        product.source_key = payload["source_key"]
        product.last_seen_at = now_utc
        if payload.get("source_last_modified_at"):
            stored_modified_at = ensure_utc(product.source_last_modified_at)
            incoming_modified_at = ensure_utc(payload["source_last_modified_at"])
            if (
                stored_modified_at is None
                or (incoming_modified_at and incoming_modified_at > stored_modified_at)
            ):
                product.source_last_modified_at = incoming_modified_at

    last_size_snapshot = (
        session.query(ProductSnapshot)
        .filter_by(product_id=product.id, snapshot_type="size")
        .order_by(ProductSnapshot.scraped_at.desc())
        .first()
    )

    if last_size_snapshot is None:
        snapshot_created = True
    else:
        size_changed = (
            abs((last_size_snapshot.size_value or 0) - payload["size_value"]) > 0.0001
            or last_size_snapshot.size_unit != payload["size_unit"]
        )
        snapshot_created = size_changed

    if snapshot_created:
        session.add(ProductSnapshot(
            product_id=product.id,
            size_value=payload["size_value"],
            size_unit=payload["size_unit"],
            price=None,
            price_per_unit=None,
            snapshot_type="size",
            source_name="openfoodfacts",
            source_updated_at=payload.get("source_last_modified_at"),
            scraped_at=now_utc,
        ))

    return {
        "new_product": created,
        "new_snapshot": snapshot_created,
        "size_changed": size_changed,
    }


def ingest_categories(categories: list[str], page_size: int = 50) -> dict:
    session = get_session()
    stats = {
        "new_products": 0,
        "new_snapshots": 0,
        "size_changes_observed": 0,
        "products_seen": 0,
        "categories_checked": 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        for category in categories:
            products = fetch_category(category, page_size=page_size)
            stats["categories_checked"] += 1

            for raw_product in products:
                payload = extract_off_product_payload(raw_product, category)
                if payload is None:
                    continue

                stats["products_seen"] += 1
                result = upsert_live_product(session, payload)
                stats["new_products"] += int(result["new_product"])
                stats["new_snapshots"] += int(result["new_snapshot"])
                stats["size_changes_observed"] += int(result["size_changed"])

            session.commit()
            time.sleep(1)
    finally:
        session.close()

    return stats


def scrape_openfoodfacts(max_categories: int | None = None):
    categories = select_rotating_categories(OFF_CATEGORIES, max_categories)
    stats = ingest_categories(categories)
    print(
        "\nOpen Food Facts scrape complete: "
        f"{stats['new_products']} new products, "
        f"{stats['new_snapshots']} new size snapshots"
    )
    return stats["new_products"], stats["new_snapshots"]


if __name__ == "__main__":
    scrape_openfoodfacts()
