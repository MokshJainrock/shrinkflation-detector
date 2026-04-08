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
  - use unconstrained fuzzy matching (token overlap requires brand match + ≥60% threshold)
  - mark success when price is missing

Identity matching order:
  1. barcode (Product.barcode == Kroger item UPC)
  2. identity_key (normalized brand::name lookup)
  3. token-overlap match (brand must match, ≥60% name-token overlap)
  4. skip — unmatched products are logged and ignored

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

# ---------------------------------------------------------------------------
# Text normalization for matching
# ---------------------------------------------------------------------------

# Words removed during normalization — these appear in Kroger product names
# but not in OFF names (or vice versa) and cause identity_key mismatches.
_FILLER_WORDS = frozenset([
    "pack", "pk", "ct", "count", "size", "original", "classic",
    "flavor", "flavored", "style", "variety", "bag", "box", "bottle",
    "can", "jar", "pouch", "container", "family", "value", "snack",
    "snacks", "item", "each", "ea", "approx", "about",
])

# Tokens that look like sizes — stripped during token matching to avoid
# "9.5 oz" in Kroger name conflicting with "10 oz" in OFF name.
_SIZE_PATTERN = re.compile(r"^\d+\.?\d*$")
_UNIT_TOKENS = frozenset([
    "oz", "fl", "lb", "lbs", "g", "kg", "ml", "l", "ct", "pk",
    "gal", "gl", "pt", "qt", "liter", "litre",
])


def normalize_text(s: str) -> str:
    """
    Normalize a product name or brand for matching.

    Pipeline:
      1. lowercase
      2. strip punctuation (keep alphanumeric + whitespace)
      3. remove filler/packaging words
      4. collapse whitespace
    """
    s = s.lower().strip()
    s = re.sub(r"[^\w\s]", "", s)          # remove punctuation
    tokens = s.split()
    tokens = [t for t in tokens if t not in _FILLER_WORDS]
    return " ".join(tokens).strip()


def _normalize_brand(brand: str) -> str:
    """Normalize brand only — lighter than full text normalization."""
    s = brand.lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _make_identity_key(brand: str, name: str) -> str:
    """Build identity key — must match live_tracker's format exactly."""
    # live_tracker uses its own _normalize which is: lower, strip punctuation,
    # collapse whitespace. We replicate that exact behavior here (no filler
    # removal) so identity_key lookups work across modules.
    b = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", brand.lower().strip())).strip()
    n = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", name.lower().strip())).strip()
    return f"{b}::{n}"


def _tokenize_for_matching(s: str) -> set[str]:
    """
    Tokenize a product name for overlap matching.

    Removes filler words, size numbers, and unit tokens so that
    "Kroger Classic Potato Chips 9.5 oz" → {"kroger", "potato", "chips"}
    """
    s = normalize_text(s)
    tokens = set()
    for t in s.split():
        if _SIZE_PATTERN.match(t):
            continue
        if t in _UNIT_TOKENS:
            continue
        if len(t) < 2:
            continue
        tokens.add(t)
    return tokens


def _resolve_existing_product(
    session, barcode: Optional[str], brand: str, name: str,
) -> Optional[Product]:
    """
    Find an existing Product using a 3-step matching pipeline.
    Kroger NEVER creates new products — returns None if not found.

    Steps:
      1. Barcode match (highest confidence)
      2. Exact identity_key match
      3. Token-overlap match: same brand + ≥60% name-token overlap

    Each step is strictly gated. False negatives are preferred over
    false positives.
    """
    # ── Step 1: barcode match ────────────────────────────────────────
    if barcode:
        match = session.query(Product).filter(
            Product.barcode == barcode.strip()
        ).first()
        if match:
            logger.debug(
                f"[kroger] MATCH barcode={barcode} → "
                f"product_id={match.id} name={match.name}"
            )
            return match

    # ── Step 2: exact identity_key match ─────────────────────────────
    identity_key = _make_identity_key(brand, name)
    match = (
        session.query(Product)
        .filter(
            Product.identity_key == identity_key,
            Product.data_source.in_(
                ["live_openfoodfacts", "live_kroger", "live_combined"]
            ),
        )
        .first()
    )
    if match:
        logger.debug(
            f"[kroger] MATCH identity_key='{identity_key}' → "
            f"product_id={match.id} name={match.name}"
        )
        return match

    # ── Step 3: token-overlap match (brand + name tokens) ────────────
    #
    # Load all live products whose normalized brand matches, then score
    # by name-token overlap. This catches cases where Kroger names are
    # slightly different from OFF names (e.g., "Lays Classic Potato
    # Chips 9.5 OZ" vs "Lay's Potato Chips").
    #
    # Guard-rails:
    #   - brand must match exactly (after normalization)
    #   - ≥60% of the DB product's name tokens must appear in the
    #     Kroger name tokens
    #   - if multiple products match, pick the one with highest overlap
    #     (ties broken by shortest name — more specific is safer)

    kr_brand_norm = _normalize_brand(brand)
    if not kr_brand_norm:
        logger.info(f"[kroger] UNMATCHED (no brand): {name}")
        return None

    kr_name_tokens = _tokenize_for_matching(name)
    if len(kr_name_tokens) < 2:
        # Too few tokens to match safely
        logger.info(f"[kroger] UNMATCHED (too few tokens): {brand} — {name}")
        return None

    # Query candidate products: same normalized brand, live sources only
    candidates = (
        session.query(Product)
        .filter(
            Product.data_source.in_(
                ["live_openfoodfacts", "live_kroger", "live_combined"]
            ),
        )
        .all()
    )

    best_match = None
    best_ratio = 0.0

    for candidate in candidates:
        # Brand must match
        cand_brand_norm = _normalize_brand(candidate.brand or "")
        if cand_brand_norm != kr_brand_norm:
            continue

        # Compute token overlap
        cand_name_tokens = _tokenize_for_matching(candidate.name or "")
        if not cand_name_tokens:
            continue

        overlap = kr_name_tokens & cand_name_tokens
        # Ratio = how much of the candidate's name is covered
        ratio = len(overlap) / len(cand_name_tokens)

        if ratio >= 0.6 and ratio > best_ratio:
            best_ratio = ratio
            best_match = candidate
        elif ratio == best_ratio and best_match is not None:
            # Tie-break: prefer shorter name (more specific)
            if len(candidate.name or "") < len(best_match.name or ""):
                best_match = candidate

    if best_match:
        logger.info(
            f"[kroger] MATCH token-overlap ({best_ratio:.0%}): "
            f"'{brand} — {name}' → "
            f"product_id={best_match.id} name='{best_match.name}'"
        )
        return best_match

    # ── Step 4: no match ─────────────────────────────────────────────
    logger.info(f"[kroger] UNMATCHED: {brand} — {name}")
    return None


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
