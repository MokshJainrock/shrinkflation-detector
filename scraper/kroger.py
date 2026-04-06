"""
Kroger API scraper — pulls price data for existing OFF products.

For accuracy, we only enrich products that have a barcode and can be looked up
via Kroger's exact product details endpoint. We intentionally skip fuzzy
name/category matching because it can attach the wrong price to a product.
"""

import time
import logging
from base64 import b64encode
from datetime import datetime, timezone

import requests

from config.settings import (
    KROGER_LOCATION_ID, KROGER_TOKEN_URL, KROGER_SEARCH_URL,
)
from db.models import Product, ProductSnapshot, get_session
from scraper.source_utils import ensure_utc, normalize_identifier

logger = logging.getLogger(__name__)

_token_cache: dict = {"access_token": None, "expires_at": 0}


def _get_kroger_credentials():
    """Read Kroger credentials FRESH every time (not at import time).
    This ensures st.secrets is available on Streamlit Cloud."""
    # Try Streamlit secrets first
    try:
        import streamlit as st
        cid = st.secrets["KROGER_CLIENT_ID"]
        csec = st.secrets["KROGER_CLIENT_SECRET"]
        if cid and csec:
            return cid, csec
    except Exception:
        pass

    # Fall back to env vars / config
    import os
    cid = os.getenv("KROGER_CLIENT_ID", "")
    csec = os.getenv("KROGER_CLIENT_SECRET", "")
    return cid, csec


def get_kroger_token() -> str | None:
    """Get or refresh Kroger OAuth2 access token."""
    client_id, client_secret = _get_kroger_credentials()

    if not client_id or not client_secret:
        logger.warning(
            "Kroger credentials not configured — skipping Kroger scraper. "
            f"CLIENT_ID present: {bool(client_id)}, "
            f"CLIENT_SECRET present: {bool(client_secret)}"
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
        return _token_cache["access_token"]
    except requests.RequestException as e:
        logger.error(f"Failed to get Kroger token: {e}")
        return None


def fetch_kroger_product_details(identifier: str, token: str) -> dict | None:
    """Fetch one Kroger product by exact UPC or productId."""
    if not identifier:
        return None

    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    params = {"filter.locationId": KROGER_LOCATION_ID}
    url = f"{KROGER_SEARCH_URL.rstrip('/')}/{identifier}"

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=8)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json().get("data")
    except requests.RequestException as e:
        logger.warning("Kroger product details failed for '%s': %s", identifier, e)
        return None


def _flatten_items(items) -> list[dict]:
    flattened = []
    for item in items or []:
        if isinstance(item, dict):
            flattened.append(item)
        elif isinstance(item, list):
            flattened.extend(subitem for subitem in item if isinstance(subitem, dict))
    return flattened


def is_exact_barcode_match(kroger_product: dict | None, barcode: str | None) -> bool:
    if not kroger_product or not barcode:
        return False

    expected = normalize_identifier(barcode)
    if not expected:
        return False

    observed = set()
    observed.update(normalize_identifier(kroger_product.get("upc")))
    observed.update(normalize_identifier(kroger_product.get("productId")))
    for item in _flatten_items(kroger_product.get("items")):
        observed.update(normalize_identifier(item.get("upc")))

    return bool(expected.intersection(observed))


def extract_price(kroger_product: dict, current_size_value: float | None) -> tuple[float | None, float | None]:
    """Extract a regular or promo price from Kroger product details."""
    price = None
    price_per_unit = None

    items = _flatten_items(kroger_product.get("items"))
    for item in items:
        price_info = item.get("price") or {}
        price = price_info.get("regular") or price_info.get("promo")
        if price:
            break

    if price and current_size_value and current_size_value > 0:
        try:
            price_per_unit = round(float(price) / float(current_size_value), 4)
        except (TypeError, ValueError, ZeroDivisionError):
            price_per_unit = None

    return price, price_per_unit


def _pick_products_for_this_tick(products: list[Product], max_products: int) -> list[Product]:
    if not products or max_products <= 0:
        return []
    if len(products) <= max_products:
        return products

    minute_bucket = int(time.time() // 60)
    start = minute_bucket % len(products)
    picked = []
    for index in range(max_products):
        picked.append(products[(start + index) % len(products)])
    return picked


def scrape_kroger(max_products=5):
    """Attach Kroger prices only when the UPC maps to an exact Kroger product."""
    token = get_kroger_token()
    if not token:
        print("Kroger: No valid credentials, skipping.")
        return 0, 0

    session = get_session()
    total_checked = 0
    total_snapshots = 0

    candidates = (
        session.query(Product)
        .filter(Product.retailer == "openfoodfacts", Product.barcode.isnot(None))
        .all()
    )
    candidates.sort(
        key=lambda product: ensure_utc(product.last_seen_at or product.created_at)
        or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    selected_products = _pick_products_for_this_tick(candidates, max_products)

    print(f"Scraping Kroger — checking {len(selected_products)} exact UPC matches this tick")

    for product in selected_products:
        total_checked += 1
        kroger_product = fetch_kroger_product_details(product.barcode, token)
        if not is_exact_barcode_match(kroger_product, product.barcode):
            continue

        latest_size_snapshot = (
            session.query(ProductSnapshot)
            .filter_by(product_id=product.id, snapshot_type="size")
            .order_by(ProductSnapshot.scraped_at.desc())
            .first()
        )
        current_size_value = latest_size_snapshot.size_value if latest_size_snapshot else None
        current_size_unit = latest_size_snapshot.size_unit if latest_size_snapshot else None
        price, price_per_unit = extract_price(kroger_product, current_size_value)
        if price is None:
            continue

        latest_price_snapshot = (
            session.query(ProductSnapshot)
            .filter_by(product_id=product.id, snapshot_type="price", source_name="kroger")
            .order_by(ProductSnapshot.scraped_at.desc())
            .first()
        )
        if (
            latest_price_snapshot is not None
            and latest_price_snapshot.price == price
            and latest_price_snapshot.price_per_unit == price_per_unit
            and latest_price_snapshot.size_value == current_size_value
            and latest_price_snapshot.size_unit == current_size_unit
        ):
            continue

        session.add(ProductSnapshot(
            product_id=product.id,
            size_value=current_size_value,
            size_unit=current_size_unit,
            price=price,
            price_per_unit=price_per_unit,
            snapshot_type="price",
            source_name="kroger",
        ))
        total_snapshots += 1
        time.sleep(0.25)

    session.commit()

    session.close()
    print(f"\nKroger scrape complete: {total_checked} checked, {total_snapshots} exact price snapshots")
    return total_checked, total_snapshots


if __name__ == "__main__":
    scrape_kroger()
