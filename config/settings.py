import importlib.util
import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _get_secret(key, default=""):
    """Prefer Streamlit secrets, then fall back to environment variables."""
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            try:
                val = st.secrets[key]
                if val:
                    logger.info("Secret '%s' loaded from Streamlit secrets", key)
                    return val
            except Exception:
                pass
            try:
                val = st.secrets.get(key)
                if val:
                    logger.info("Secret '%s' loaded from Streamlit secrets (.get)", key)
                    return val
            except Exception:
                pass
    except Exception:
        pass

    val = os.getenv(key, default)
    if val and val != default:
        logger.info("Secret '%s' loaded from environment variable", key)
    return val


def _normalize_database_url(raw_url: str) -> str:
    url = (raw_url or "").strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    # The repo's previous placeholder pointed at a local Postgres instance,
    # but the project does not install a Postgres driver by default.
    if not url or url == "postgresql://localhost/shrinkflation_db":
        return "sqlite:///shrinkflation.db"

    if url.startswith("postgresql"):
        has_driver = (
            importlib.util.find_spec("psycopg") is not None
            or importlib.util.find_spec("psycopg2") is not None
        )
        if not has_driver:
            logger.warning(
                "PostgreSQL URL configured but no PostgreSQL driver is installed; "
                "falling back to sqlite:///shrinkflation.db"
            )
            return "sqlite:///shrinkflation.db"

    return url


DATABASE_URL = _normalize_database_url(_get_secret("DATABASE_URL", "sqlite:///shrinkflation.db"))
KROGER_CLIENT_ID = _get_secret("KROGER_CLIENT_ID")
KROGER_CLIENT_SECRET = _get_secret("KROGER_CLIENT_SECRET")
KROGER_LOCATION_ID = _get_secret("KROGER_LOCATION_ID", "01400513")
OPENAI_API_KEY = _get_secret("OPENAI_API_KEY")

# Open Food Facts
OFF_BASE_URL = "https://world.openfoodfacts.org/api/v2/search"
OFF_CATEGORIES = [
    "chips",
    "cereal",
    "ice cream",
    "yogurt",
    "cookies",
    "crackers",
    "pasta",
    "candy",
    "bread",
    "coffee",
    "ketchup",
    "mayonnaise",
    "peanut butter",
    "juice",
    "frozen meals",
    "detergent",
    "soap",
]

# Kroger
KROGER_TOKEN_URL = "https://api.kroger.com/v1/connect/oauth2/token"
KROGER_SEARCH_URL = "https://api.kroger.com/v1/products"

# Detection thresholds
SIZE_DECREASE_THRESHOLD_PCT = 2.0
HIGH_SEVERITY_PCT = 10.0
MEDIUM_SEVERITY_PCT = 5.0
PRICE_MATCH_WINDOW_DAYS = 7

# Agent
AGENT_MODEL = "gpt-4o"
