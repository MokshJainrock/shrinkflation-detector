import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Try Streamlit secrets first (for Streamlit Cloud), fall back to env vars
def _get_secret(key, default=""):
    # Method 1: Streamlit secrets (st.secrets["KEY"])
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            # Try dict-style access first (most reliable on Streamlit Cloud)
            try:
                val = st.secrets[key]
                if val:
                    logger.info(f"Secret '{key}' loaded from Streamlit secrets")
                    return val
            except (KeyError, Exception):
                pass
            # Try .get() as fallback
            try:
                val = st.secrets.get(key)
                if val:
                    logger.info(f"Secret '{key}' loaded from Streamlit secrets (.get)")
                    return val
            except Exception:
                pass
    except Exception:
        pass

    # Method 2: Environment variable
    val = os.getenv(key, default)
    if val and val != default:
        logger.info(f"Secret '{key}' loaded from environment variable")
    return val

DATABASE_URL = _get_secret("DATABASE_URL", "sqlite:///shrinkflation.db")
KROGER_CLIENT_ID = _get_secret("KROGER_CLIENT_ID")
KROGER_CLIENT_SECRET = _get_secret("KROGER_CLIENT_SECRET")
OPENAI_API_KEY = _get_secret("OPENAI_API_KEY")

# Open Food Facts
# Primary: .net mirror (works from Streamlit Cloud; .org returns 503 there)
# live_tracker.py tries .net first and falls back to .org automatically.
OFF_BASE_URL = "https://world.openfoodfacts.net/api/v2/search"
OFF_CATEGORIES = [
    "chips", "cereal", "juice", "detergent", "cookies", "yogurt", "coffee",
    "pasta", "soap", "crackers", "bread", "mayo", "ketchup", "ice cream", "cheese",
]

# Kroger
KROGER_TOKEN_URL = "https://api.kroger.com/v1/connect/oauth2/token"
KROGER_SEARCH_URL = "https://api.kroger.com/v1/products"

# Detection thresholds
# These are used by analysis/detector.py for live detection.
# Values are intentionally higher than inflation-era defaults to produce
# a meaningful severity distribution across genuine detections.
SIZE_DECREASE_THRESHOLD_PCT = 2.0    # minimum % size decrease to consider
HIGH_SEVERITY_PPU_PCT = 20.0         # price-per-unit increase >= 20% → HIGH
MEDIUM_SEVERITY_PPU_PCT = 8.0        # price-per-unit increase >= 8%  → MEDIUM
LOOKBACK_DAYS = 90                   # how far back to search for old observation

# Agent
AGENT_MODEL = "gpt-4o"
