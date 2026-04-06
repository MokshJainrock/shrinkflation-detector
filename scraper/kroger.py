"""
Kroger API scraper — pulls price data and matches to existing products.
Requires free Kroger developer account: https://developer.kroger.com
"""

import time
import logging
from base64 import b64encode
from difflib import SequenceMatcher

import requests

from config.settings import (
    KROGER_TOKEN_URL, KROGER_SEARCH_URL, OFF_CATEGORIES,
)
from db.models import Product, ProductSnapshot, get_session

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


# Default Kroger store — needed for price data (prices are location-specific)
KROGER_LOCATION_ID = "01400513"  # Kroger On the Rhine, Cincinnati OH


def search_kroger_products(query: str, token: str, limit: int = 10) -> list[dict]:
    """Search Kroger product catalog with location for price data."""
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
        logger.warning(f"Kroger search failed for '{query}': {e}")
        return []


def match_product_name(kroger_name: str, db_products: list[Product]) -> Product | None:
    """Find best matching product from DB using fuzzy string matching."""
    best_match = None
    best_ratio = 0.0

    for product in db_products:
        ratio = SequenceMatcher(None, kroger_name.lower(), product.name.lower()).ratio()
        if ratio > best_ratio and ratio > 0.65:  # 0.65 threshold to avoid false matches
            best_ratio = ratio
            best_match = product

    return best_match


def extract_price(kroger_item: dict) -> tuple[float | None, float | None]:
    """Extract regular price and price_per_unit from Kroger product data."""
    price = None
    price_per_unit = None

    items = kroger_item.get("items", [])
    if items:
        item = items[0]
        price_info = item.get("price", {})
        price = price_info.get("regular")
        if not price:
            price = price_info.get("promo")

        size_info = item.get("size", "")
        if price and size_info:
            # Attempt to compute price per unit
            import re
            match = re.search(r"([\d.]+)", str(size_info))
            if match:
                try:
                    size_val = float(match.group(1))
                    if size_val > 0:
                        price_per_unit = round(price / size_val, 4)
                except (ValueError, ZeroDivisionError):
                    pass

    return price, price_per_unit


def scrape_kroger(max_categories=3):
    """Main Kroger scraper — searches for products and adds price snapshots.
    Only checks a few categories per tick to stay within time limits."""
    token = get_kroger_token()
    if not token:
        print("Kroger: No valid credentials, skipping.")
        return 0, 0

    session = get_session()
    total_matched = 0
    total_snapshots = 0

    # Rotate through categories each tick (like OFF scanner does)
    from datetime import datetime, timezone
    now_utc = datetime.now(timezone.utc)
    minute_offset = (now_utc.hour * 60 + now_utc.minute) % len(OFF_CATEGORIES)
    categories_to_check = []
    for i in range(min(max_categories, len(OFF_CATEGORIES))):
        idx = (minute_offset + i) % len(OFF_CATEGORIES)
        categories_to_check.append(OFF_CATEGORIES[idx])

    print(f"Scraping Kroger — {len(categories_to_check)} of {len(OFF_CATEGORIES)} categories this tick")

    for category in categories_to_check:
        print(f"  Searching Kroger for: {category}...")

        # Get existing products in this category from our DB
        db_products = (
            session.query(Product)
            .filter_by(category=category)
            .all()
        )

        kroger_results = search_kroger_products(category, token)
        print(f"  Got {len(kroger_results)} Kroger results")

        for kr_product in kroger_results:
            kr_name = kr_product.get("description", "")
            if not kr_name:
                continue

            # Try to match to existing product
            matched = match_product_name(kr_name, db_products)

            if matched:
                price, price_per_unit = extract_price(kr_product)
                if price:
                    snapshot = ProductSnapshot(
                        product_id=matched.id,
                        size_value=matched.snapshots[-1].size_value if matched.snapshots else None,
                        size_unit=matched.snapshots[-1].size_unit if matched.snapshots else None,
                        price=price,
                        price_per_unit=price_per_unit,
                    )
                    session.add(snapshot)
                    total_snapshots += 1
                    total_matched += 1

        session.commit()
        time.sleep(0.5)  # Rate limit

    session.close()
    print(f"\nKroger scrape complete: {total_matched} matched, {total_snapshots} price snapshots")
    return total_matched, total_snapshots


if __name__ == "__main__":
    scrape_kroger()
