"""
Streamlit dashboard — Shrinkflation Detector
Live-only view of source-backed shrinkflation observations.

Run with: streamlit run dashboard/app.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timezone, timedelta

from db.models import (
    Product, ProductSnapshot, ShrinkflationFlag, AgentInsight,
    get_session, get_engine, init_db,
)
from agent.tools import (
    get_summary_stats, get_worst_offenders, get_category_breakdown,
    get_trend_data, get_product_history,
)

LOAD_ERRORS = {}

# =====================================================================
# PAGE CONFIG
# =====================================================================
st.set_page_config(
    page_title="Shrinkflation Detector",
    page_icon="📉",
    layout="wide",
    initial_sidebar_state="collapsed",  # collapsed by default = mobile-friendly
)

# =====================================================================
# RESPONSIVE CSS — works on desktop, tablet, and mobile
# =====================================================================
st.markdown("""
<style>
    /* ---- Base responsive styles ---- */
    .block-container {
        padding: 0.5rem 1rem 1rem 1rem;
        max-width: 100%;
    }

    /* ---- Main header ---- */
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 1.2rem 1.5rem;
        border-radius: 12px;
        margin-bottom: 0.8rem;
        color: white;
    }
    .main-header h1 { color: white !important; margin: 0; font-size: 1.8rem; line-height: 1.2; }
    .main-header p { color: #94a3b8; margin: 0.3rem 0 0 0; font-size: 0.9rem; line-height: 1.4; }

    /* ---- Metric cards (dark-mode safe) ---- */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        border: 1px solid #475569;
        border-radius: 10px;
        padding: 10px 14px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    div[data-testid="stMetric"] label {
        font-size: 0.75rem !important;
        color: #cbd5e1 !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 1.3rem !important;
        font-weight: 700 !important;
        color: #f1f5f9 !important;
    }

    /* Light mode override */
    @media (prefers-color-scheme: light) {
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border: 1px solid #dee2e6;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        div[data-testid="stMetric"] label { color: #495057 !important; }
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #1e293b !important; }
    }

    /* Streamlit dark theme detection (more reliable) */
    [data-testid="stAppViewContainer"][data-theme="dark"] div[data-testid="stMetric"],
    .stApp[data-theme="dark"] div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        border-color: #475569;
    }

    /* ---- Tabs ---- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        flex-wrap: wrap;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 6px 12px;
        font-weight: 600;
        font-size: 0.85rem;
        white-space: nowrap;
    }

    /* ---- Severity badges ---- */
    .severity-high { background: #e74c3c; color: white; padding: 2px 10px; border-radius: 12px; font-weight: 600; font-size: 0.8rem; }
    .severity-medium { background: #f39c12; color: white; padding: 2px 10px; border-radius: 12px; font-weight: 600; font-size: 0.8rem; }
    .severity-low { background: #f1c40f; color: #333; padding: 2px 10px; border-radius: 12px; font-weight: 600; font-size: 0.8rem; }

    /* ---- Data source badge (works in both themes) ---- */
    .source-badge {
        display: inline-block;
        background: rgba(99, 102, 241, 0.15);
        border: 1px solid rgba(99, 102, 241, 0.3);
        color: #818cf8;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 2px;
    }

    /* ---- Info cards (dark-mode safe) ---- */
    .info-card {
        background: rgba(30, 41, 59, 0.8);
        border: 1px solid #475569;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.8rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        color: #e2e8f0;
    }

    /* ---- Comparison card (dark-mode safe) ---- */
    .compare-card {
        background: linear-gradient(135deg, rgba(127, 29, 29, 0.3) 0%, rgba(153, 27, 27, 0.2) 100%);
        border: 2px solid #f87171;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        color: #fecaca;
    }
    .compare-card h3 { color: #fca5a5 !important; }
    .compare-card p { color: #e2e8f0; }

    /* ---- Update status ---- */
    .update-status {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-left: 8px;
        vertical-align: middle;
    }
    .update-live { background: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.4); }
    .update-stale { background: rgba(234, 179, 8, 0.2); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.4); }

    /* ---- Footer ---- */
    .footer {
        text-align: center;
        color: #94a3b8;
        padding: 1.5rem 0;
        font-size: 0.8rem;
        line-height: 1.6;
    }
    .footer a { color: #818cf8; }

    /* ============================================
       MOBILE RESPONSIVE — screens < 768px
       ============================================ */
    @media (max-width: 768px) {
        .block-container {
            padding: 0.3rem 0.5rem 1rem 0.5rem !important;
        }

        .main-header {
            padding: 0.8rem 1rem;
            border-radius: 8px;
        }
        .main-header h1 { font-size: 1.3rem !important; }
        .main-header p { font-size: 0.75rem !important; }

        /* Stack metric cards vertically */
        div[data-testid="stMetric"] {
            padding: 8px 10px;
            margin-bottom: 4px;
        }
        div[data-testid="stMetric"] label { font-size: 0.65rem !important; }
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] { font-size: 1.1rem !important; }

        /* Stack columns on mobile */
        div[data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
        }
        div[data-testid="stHorizontalBlock"] > div {
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }

        /* Smaller tab text */
        .stTabs [data-baseweb="tab"] {
            padding: 5px 8px;
            font-size: 0.75rem;
        }

        /* Smaller subheaders */
        h2, h3, .stSubheader { font-size: 1.1rem !important; }

        /* Comparison card */
        .compare-card { padding: 0.8rem; }
        .compare-card h3 { font-size: 1rem !important; }

        /* Download buttons stack */
        .stDownloadButton button {
            width: 100% !important;
            margin-bottom: 4px;
        }

        /* Plotly charts: minimum touch-friendly height */
        .stPlotlyChart { min-height: 280px; }
    }

    /* ============================================
       TABLET RESPONSIVE — 768px-1024px
       ============================================ */
    @media (min-width: 769px) and (max-width: 1024px) {
        .block-container {
            padding: 0.5rem 0.8rem 1rem 0.8rem !important;
        }
        .main-header h1 { font-size: 1.5rem !important; }

        /* 2-column on tablet instead of 3 */
        div[data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# Auto-refresh every 60 seconds to show new live data
st_autorefresh(interval=60000, key="data_refresh")


# =====================================================================
# STARTUP: Live-only database + live scanner
# =====================================================================

DATA_VERSION = 4  # Bump this to invalidate old seeded/static databases

@st.cache_resource
def _init_and_load(_version=DATA_VERSION):
    """
    Runs ONCE per app lifecycle:
    1. Create tables
    2. Reset old seeded / pre-live-only databases when schema version changes
    """
    from db.models import Base
    import os

    init_db()
    engine = get_engine()

    # Track data version in a file to detect stale DB across restarts
    version_file = os.path.join(os.path.dirname(__file__), ".data_version")
    current_version = None
    try:
        with open(version_file) as f:
            current_version = int(f.read().strip())
    except Exception:
        pass

    session = get_session()
    total_products = session.query(Product).count()
    live_products = session.query(Product).filter(Product.retailer == "openfoodfacts").count()
    session.close()

    reset_reason = None
    if current_version != DATA_VERSION:
        reset_reason = f"Data version changed ({current_version} -> {DATA_VERSION})"
    elif total_products and live_products != total_products:
        reset_reason = "Removed legacy non-live products from database"

    if reset_reason:
        print(f"[DB] {reset_reason} — rebuilding live-only database")
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)

    try:
        with open(version_file, "w") as f:
            f.write(str(DATA_VERSION))
    except Exception:
        pass


_init_and_load()


# ---- Live scan on every refresh (OFF + Kroger) ──────────────────────────
@st.cache_data(ttl=55)
def _run_live_scan():
    """
    Fetch NEW products on every page refresh (cached 55s → fresh scan each 60s).

    Two live sources:
      1. Open Food Facts API — product sizes, barcodes (free, no key)
      2. Kroger API — real US retail prices (free developer account)

    Products get ADDED to the existing real data in the DB.
    """
    from scraper.live_tracker import run_live_update
    from analysis.detector import run_detection

    stats = {"new_products": 0, "new_snapshots": 0, "kroger_snapshots": 0}

    # Source 1: Open Food Facts (sizes + barcodes)
    try:
        off_stats = run_live_update(max_categories=2)
        stats["new_products"] = off_stats.get("new_products", 0)
        stats["new_snapshots"] = off_stats.get("new_snapshots", 0)
        stats["size_changes_observed"] = off_stats.get("size_changes_observed", 0)
    except Exception as e:
        stats["off_error"] = str(e)

    # Source 2: Kroger (real retail prices)
    try:
        from scraper.kroger import scrape_kroger
        matched, kr_snaps = scrape_kroger()
        stats["kroger_snapshots"] = kr_snaps
        print(f"[Kroger] Done: {matched} matched, {kr_snaps} snapshots")
    except Exception as e:
        stats["kroger_error"] = str(e)
        print(f"[Kroger] Error: {e}")

    # Run shrinkflation detector
    try:
        new_flags = run_detection()
        stats["new_flags"] = new_flags
    except Exception:
        stats["new_flags"] = 0

    try:
        session = get_session()
        stats["db_product_count"] = (
            session.query(Product)
            .filter(Product.retailer == "openfoodfacts")
            .count()
        )
        stats["db_flag_count"] = (
            session.query(ShrinkflationFlag)
            .join(Product, Product.id == ShrinkflationFlag.product_id)
            .filter(Product.retailer == "openfoodfacts")
            .count()
        )
        session.close()
    except Exception as e:
        stats["db_error"] = str(e)

    stats["scanned_at"] = datetime.now(timezone.utc).isoformat()
    return stats


_scan_result = _run_live_scan()

# ---- Chart config (mobile-friendly) ----
CHART_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(showgrid=False),
    yaxis=dict(showgrid=False),
    margin=dict(l=10, r=10, t=40, b=20),
    font=dict(size=12, family="Inter, system-ui, sans-serif"),
)

CHART_CONFIG = {
    "displayModeBar": False,  # hide plotly toolbar on mobile
    "responsive": True,
}

SEVERITY_COLORS = {"HIGH": "#e74c3c", "MEDIUM": "#f39c12", "LOW": "#f1c40f"}


# =====================================================================
# DATA LOADING
# =====================================================================
def _record_load_error(name: str, error: Exception | None):
    if error is None:
        LOAD_ERRORS.pop(name, None)
    else:
        LOAD_ERRORS[name] = str(error)


@st.cache_data(ttl=60)
def load_flags(_refresh_token=None):
    try:
        session = get_session()
        rows = (
            session.query(ShrinkflationFlag, Product)
            .join(Product, Product.id == ShrinkflationFlag.product_id)
            .filter(Product.retailer == "openfoodfacts")
            .order_by(ShrinkflationFlag.detected_at.desc())
            .all()
        )
        data = [
            {
                "id": flag.id,
                "product_id": flag.product_id,
                "old_size": flag.old_size,
                "new_size": flag.new_size,
                "old_price": flag.old_price,
                "new_price": flag.new_price,
                "real_price_increase_pct": flag.real_price_increase_pct,
                "severity": flag.severity,
                "size_unit": flag.size_unit,
                "evidence_type": flag.evidence_type,
                "detected_at": flag.detected_at,
                "retailer": flag.retailer,
                "product": product.name,
                "brand": product.brand,
                "category": product.category,
            }
            for flag, product in rows
        ]
        session.close()
        _record_load_error("flags", None)
        return pd.DataFrame(data)
    except Exception as e:
        _record_load_error("flags", e)
        return pd.DataFrame()


@st.cache_data(ttl=60)
def load_all_products(_refresh_token=None):
    try:
        session = get_session()
        rows = (
            session.query(Product)
            .filter(Product.retailer == "openfoodfacts")
            .order_by(Product.last_seen_at.desc())
            .all()
        )
        data = [
            {
                "id": product.id,
                "name": product.name,
                "brand": product.brand,
                "category": product.category,
                "barcode": product.barcode,
                "retailer": product.retailer,
                "source_key": product.source_key,
                "image_url": product.image_url,
                "created_at": product.created_at,
                "last_seen_at": product.last_seen_at,
                "source_last_modified_at": product.source_last_modified_at,
            }
            for product in rows
        ]
        session.close()
        _record_load_error("products", None)
        return pd.DataFrame(data)
    except Exception as e:
        _record_load_error("products", e)
        return pd.DataFrame()


@st.cache_data(ttl=60)
def load_inventory_summary(_refresh_token=None):
    empty_summary = {
        "total_products": 0,
        "category_count": 0,
        "brand_count": 0,
        "barcoded_products": 0,
        "barcode_coverage_pct": 0.0,
        "timestamped_products": 0,
        "source_timestamp_coverage_pct": 0.0,
        "size_snapshot_count": 0,
        "price_matched_products": 0,
        "exact_price_match_pct": 0.0,
        "top_category": "N/A",
        "top_brand": "N/A",
        "latest_seen_at": None,
    }

    session = None
    try:
        session = get_session()
        products = (
            session.query(Product)
            .filter(Product.retailer == "openfoodfacts")
            .order_by(Product.last_seen_at.desc())
            .all()
        )
        snapshot_rows = (
            session.query(ProductSnapshot.product_id, ProductSnapshot.snapshot_type, ProductSnapshot.source_name)
            .join(Product, Product.id == ProductSnapshot.product_id)
            .filter(Product.retailer == "openfoodfacts")
            .all()
        )
        _record_load_error("inventory_summary", None)
    except Exception as e:
        if session is not None:
            session.close()
        _record_load_error("inventory_summary", e)
        return empty_summary

    session.close()
    total_products = len(products)
    if total_products == 0:
        return empty_summary

    categories = [
        str(product.category).strip()
        for product in products
        if product.category and str(product.category).strip()
    ]
    brands = [
        str(product.brand).strip()
        for product in products
        if product.brand and str(product.brand).strip()
    ]
    barcoded_products = sum(
        1 for product in products if product.barcode and str(product.barcode).strip()
    )
    timestamped_products = sum(
        1 for product in products if product.source_last_modified_at is not None
    )
    size_snapshot_count = sum(
        1
        for _product_id, snapshot_type, _source_name in snapshot_rows
        if snapshot_type == "size"
    )
    price_matched_products = len({
        product_id
        for product_id, snapshot_type, source_name in snapshot_rows
        if snapshot_type == "price" and source_name == "kroger"
    })
    top_category = pd.Series(categories).value_counts().idxmax() if categories else "N/A"
    top_brand = pd.Series(brands).value_counts().idxmax() if brands else "N/A"
    latest_seen_at = max(
        (product.last_seen_at for product in products if product.last_seen_at is not None),
        default=None,
    )

    return {
        "total_products": total_products,
        "category_count": len(set(categories)),
        "brand_count": len(set(brands)),
        "barcoded_products": barcoded_products,
        "barcode_coverage_pct": (barcoded_products / total_products * 100) if total_products else 0.0,
        "timestamped_products": timestamped_products,
        "source_timestamp_coverage_pct": (timestamped_products / total_products * 100) if total_products else 0.0,
        "size_snapshot_count": size_snapshot_count,
        "price_matched_products": price_matched_products,
        "exact_price_match_pct": (price_matched_products / total_products * 100) if total_products else 0.0,
        "top_category": top_category,
        "top_brand": top_brand,
        "latest_seen_at": latest_seen_at,
    }


@st.cache_data(ttl=60)
def load_latest_insight(_refresh_token=None):
    try:
        session = get_session()
        insight = (
            session.query(AgentInsight)
            .filter(AgentInsight.insight_type == "daily")
            .order_by(AgentInsight.generated_at.desc())
            .first()
        )
        session.close()
        if insight:
            return insight.content, insight.generated_at
        return None, None
    except Exception:
        return None, None


# ---- Load data ----
_data_refresh_token = _scan_result.get("scanned_at")
flags_df = load_flags(_data_refresh_token)
products_df = load_all_products(_data_refresh_token)
inventory_summary = load_inventory_summary(_data_refresh_token)

# =====================================================================
# SIDEBAR — Filters (touch-friendly)
# =====================================================================
with st.sidebar:
    st.markdown("## Filters")

    _sidebar_product_count = len(products_df) or _scan_result.get("db_product_count", 0)
    _sidebar_flag_count = len(flags_df) or _scan_result.get("db_flag_count", 0)

    filter_source = products_df if not products_df.empty else flags_df
    all_categories = (
        sorted(
            filter_source["category"]
            .dropna()
            .astype(str)
            .str.strip()
            .replace("", pd.NA)
            .dropna()
            .unique()
        )
        if not filter_source.empty and "category" in filter_source.columns
        else []
    )
    selected_category = st.selectbox("Category", ["All Categories"] + all_categories)

    if not filter_source.empty and "brand" in filter_source.columns:
        brand_source = filter_source
        if selected_category != "All Categories" and "category" in filter_source.columns:
            brand_source = filter_source[filter_source["category"] == selected_category]
        available_brands = sorted(
            brand_source["brand"]
            .dropna()
            .astype(str)
            .str.strip()
            .replace("", pd.NA)
            .dropna()
            .unique()
        )
    else:
        available_brands = []
    selected_brand = st.selectbox("Brand", ["All Brands"] + available_brands)

    selected_severity = st.selectbox("Severity", ["ALL", "HIGH", "MEDIUM", "LOW"])

    # Retailer filter
    all_retailers = sorted(flags_df["retailer"].dropna().unique()) if not flags_df.empty and "retailer" in flags_df.columns else []
    if all_retailers:
        selected_retailer = st.selectbox("Retailer", ["All Retailers"] + all_retailers)
    else:
        selected_retailer = "All Retailers"

    st.markdown("---")
    date_range = st.select_slider(
        "Time Range",
        options=["30 days", "90 days", "1 year", "2 years", "All time"],
        value="All time",
    )

    st.markdown("---")
    st.markdown("**Quick Stats**")
    col_s1, col_s2 = st.columns(2)
    col_s1.metric("Products", f"{_sidebar_product_count:,}")
    col_s2.metric("Flags", f"{_sidebar_flag_count:,}")

    st.markdown("---")
    st.caption("Live data from Open Food Facts, refreshed every 60 seconds. Kroger prices use exact UPC matches only.")

# ---- Apply filters ----
_days_map = {"30 days": 30, "90 days": 90, "1 year": 365, "2 years": 730}
filtered = flags_df.copy()
filtered_products = products_df.copy()

if not filtered.empty:
    if selected_category != "All Categories":
        filtered = filtered[filtered["category"] == selected_category]
    if selected_brand != "All Brands":
        filtered = filtered[filtered["brand"] == selected_brand]
    if selected_severity != "ALL":
        filtered = filtered[filtered["severity"] == selected_severity]
    if selected_retailer != "All Retailers" and "retailer" in filtered.columns:
        filtered = filtered[filtered["retailer"] == selected_retailer]
    if "detected_at" in filtered.columns and date_range != "All time":
        filtered["detected_at"] = pd.to_datetime(filtered["detected_at"], utc=True)
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=_days_map[date_range])
        filtered = filtered[filtered["detected_at"] >= cutoff]

if not filtered_products.empty:
    if selected_category != "All Categories" and "category" in filtered_products.columns:
        filtered_products = filtered_products[filtered_products["category"] == selected_category]
    if selected_brand != "All Brands" and "brand" in filtered_products.columns:
        filtered_products = filtered_products[filtered_products["brand"] == selected_brand]
    if "last_seen_at" in filtered_products.columns and date_range != "All time":
        filtered_products["last_seen_at"] = pd.to_datetime(
            filtered_products["last_seen_at"], utc=True, errors="coerce"
        )
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=_days_map[date_range])
        filtered_products = filtered_products[filtered_products["last_seen_at"] >= cutoff]


# =====================================================================
# HEADER
# =====================================================================
total_prods = len(products_df) or _scan_result.get("db_product_count", 0)
total_flags = len(filtered) or _scan_result.get("db_flag_count", 0)

# Determine update status from the scan that just ran
_now_utc = datetime.now(timezone.utc)
_new_p = _scan_result.get("new_products", 0)
_new_s = _scan_result.get("new_snapshots", 0)
_kr_s = _scan_result.get("kroger_snapshots", 0)

_update_badge = '<span class="update-status update-live">LIVE — scanning every 60s</span>'
_parts = []
if _new_p or _new_s:
    _parts.append(f"+{_new_p} products, +{_new_s} OFF snapshots")
if _scan_result.get("size_changes_observed"):
    _parts.append(f"{_scan_result['size_changes_observed']} live size changes observed")
if _kr_s:
    _parts.append(f"+{_kr_s} Kroger price snapshots")
if _scan_result.get("new_flags"):
    _parts.append(f"{_scan_result['new_flags']} new shrink flags")
if _scan_result.get("off_error"):
    _parts.append(f"OFF: {_scan_result['off_error'][:60]}")
if _scan_result.get("kroger_error"):
    _parts.append(f"Kroger: {_scan_result['kroger_error'][:80]}")
_update_detail = "Live scan: " + (" | ".join(_parts) if _parts else "scan complete, no new live observations this tick")

st.markdown(f"""
<div class="main-header">
    <h1>Shrinkflation Detector {_update_badge}</h1>
    <p>{total_prods:,} products tracked &middot; {total_flags:,} shrinkflation cases detected
    &middot; Refreshed {_now_utc.strftime('%b %d, %Y %H:%M:%S UTC')}</p>
    <p style="margin-top:4px; font-size:0.8rem; color:#64748b">{_update_detail}</p>
    <p style="margin-top:6px">
        <span class="source-badge">Open Food Facts API</span>
        <span class="source-badge">Kroger API</span>
        <span class="source-badge">Live Snapshots Only</span>
        <span class="source-badge">Exact UPC Prices</span>
    </p>
</div>
""", unsafe_allow_html=True)

# =====================================================================
# METRICS ROW — computed from filtered data, responds to all filters
# =====================================================================
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Products Tracked", f"{total_prods:,}")
m2.metric("Shrinks Detected", f"{total_flags:,}")

if not filtered.empty and "real_price_increase_pct" in filtered.columns:
    _avg_inc = filtered["real_price_increase_pct"].mean()
    m3.metric("Avg Hidden Increase", f"+{_avg_inc:.1f}%")

    if "category" in filtered.columns:
        _worst_cat = filtered["category"].value_counts().idxmax()
        m4.metric("Worst Category", _worst_cat.title())
    else:
        m4.metric("Worst Category", "N/A")

    if "brand" in filtered.columns:
        _worst_brand = filtered["brand"].value_counts().idxmax()
        m5.metric("Worst Brand", _worst_brand)
    else:
        m5.metric("Worst Brand", "N/A")
else:
    m3.metric("Tracked Categories", f"{inventory_summary['category_count']:,}")
    m4.metric("Tracked Brands", f"{inventory_summary['brand_count']:,}")
    m5.metric("Barcode Coverage", f"{inventory_summary['barcode_coverage_pct']:.1f}%")

st.markdown("")

if LOAD_ERRORS:
    for name, error in LOAD_ERRORS.items():
        st.warning(f"Dashboard {name} load warning: {error}")
if _scan_result.get("db_error"):
    st.warning(f"Dashboard database count warning: {_scan_result['db_error']}")

# =====================================================================
# MAIN TABBED LAYOUT
# =====================================================================
if not filtered.empty:
    tab_overview, tab_compare, tab_deepdive, tab_explorer, tab_ai, tab_data = st.tabs([
        "Overview", "Compare", "Deep Dive", "Explorer", "AI Insights", "Data"
    ])

    # =================================================================
    # TAB 1: OVERVIEW
    # =================================================================
    with tab_overview:
        # Row 1: Top brands + Trend
        col1, col2 = st.columns([3, 2])

        with col1:
            st.subheader("Top 10 Worst Brands")
            brand_stats = (
                filtered.groupby("brand")
                .agg(flags=("id", "count"), avg_increase=("real_price_increase_pct", "mean"))
                .reset_index()
                .sort_values("flags", ascending=False)
                .head(10)
            )
            fig1 = px.bar(
                brand_stats, x="flags", y="brand", orientation="h",
                color="avg_increase", color_continuous_scale="Reds",
                labels={"flags": "Verified Flags", "brand": "", "avg_increase": "Avg Increase %"},
                text="flags",
            )
            fig1.update_traces(textposition="outside")
            fig1.update_layout(**CHART_LAYOUT, height=400)
            fig1.update_yaxes(categoryorder="total ascending")
            st.plotly_chart(fig1, width="stretch", config=CHART_CONFIG)

        with col2:
            st.subheader("Severity Breakdown")
            sev_counts = filtered["severity"].value_counts().reset_index()
            sev_counts.columns = ["severity", "count"]
            fig_donut = px.pie(
                sev_counts, values="count", names="severity",
                color="severity", color_discrete_map=SEVERITY_COLORS,
                hole=0.55,
            )
            fig_donut.update_traces(textinfo="percent+value", textfont_size=11)
            fig_donut.update_layout(
                height=400, margin=dict(l=10, r=10, t=10, b=10),
                showlegend=True, legend=dict(orientation="h", y=-0.1),
            )
            st.plotly_chart(fig_donut, width="stretch", config=CHART_CONFIG)

        st.divider()

        # Row 2: Detection timeline — computed from filtered data
        st.subheader("Detection Timeline")
        if not filtered.empty and "detected_at" in filtered.columns:
            _trend_df = filtered.copy()
            _trend_df["detected_at"] = pd.to_datetime(_trend_df["detected_at"], utc=True)
            # Group by month for a readable long-running live timeline
            _trend_df["period"] = _trend_df["detected_at"].dt.to_period("M").dt.to_timestamp()
            _monthly = _trend_df.groupby("period").size().reset_index(name="detections")
            _monthly = _monthly.sort_values("period")

            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=_monthly["period"], y=_monthly["detections"],
                marker_color="#e74c3c",
                name="Detections",
                hovertemplate="<b>%{x|%b %Y}</b><br>%{y} cases detected<extra></extra>",
            ))
            # Add trend line if enough data
            if len(_monthly) >= 3:
                _monthly["ma"] = _monthly["detections"].rolling(3, min_periods=1).mean()
                fig2.add_trace(go.Scatter(
                    x=_monthly["period"], y=_monthly["ma"],
                    mode="lines", line=dict(color="#3498db", width=2, dash="dash"),
                    name="3-Month Avg",
                ))
            fig2.update_layout(**CHART_LAYOUT, height=350, yaxis_title="Cases Detected",
                               xaxis_title="", legend=dict(orientation="h", yanchor="bottom", y=1.02))
            st.plotly_chart(fig2, width="stretch", config=CHART_CONFIG)
        else:
            st.info("No detection data available yet for timeline.")

        st.divider()

        # Row 3: Category breakdown
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Cases by Category")
            if not filtered.empty and "category" in filtered.columns:
                _cat_counts = (
                    filtered.groupby("category").size()
                    .reset_index(name="cases")
                    .sort_values("cases", ascending=True)
                )
                fig3 = px.bar(
                    _cat_counts, x="cases", y="category", orientation="h",
                    color="cases", color_continuous_scale="YlOrRd",
                    labels={"cases": "Shrinkflation Cases", "category": ""},
                    text="cases",
                )
                fig3.update_traces(texttemplate="%{text}", textposition="outside")
                fig3.update_layout(**CHART_LAYOUT, height=400)
                st.plotly_chart(fig3, width="stretch", config=CHART_CONFIG)

        with col_right:
            st.subheader("Avg Hidden Price Increase")
            cat_avg = (
                filtered.groupby("category")["real_price_increase_pct"]
                .mean().round(1).sort_values(ascending=True)
                .reset_index()
            )
            fig4 = px.bar(
                cat_avg, x="real_price_increase_pct", y="category", orientation="h",
                color="real_price_increase_pct", color_continuous_scale="Reds",
                labels={"real_price_increase_pct": "Avg Increase (%)", "category": ""},
                text="real_price_increase_pct",
            )
            fig4.update_traces(texttemplate="+%{text:.1f}%", textposition="outside")
            fig4.update_layout(**CHART_LAYOUT, height=400)
            st.plotly_chart(fig4, width="stretch", config=CHART_CONFIG)

        st.divider()

        # Row 4: Treemap
        st.subheader("Shrinkflation Map — Category / Brand / Severity")
        tree_data = (
            filtered.groupby(["category", "brand", "severity"])
            .agg(count=("id", "count"), avg_inc=("real_price_increase_pct", "mean"))
            .reset_index()
        )
        if not tree_data.empty:
            fig_tree = px.treemap(
                tree_data, path=["category", "brand", "severity"],
                values="count", color="avg_inc",
                color_continuous_scale="RdYlGn_r",
                labels={"count": "Flags", "avg_inc": "Avg Increase %"},
                hover_data={"avg_inc": ":.1f"},
            )
            fig_tree.update_layout(height=450, margin=dict(l=5, r=5, t=30, b=5))
            st.plotly_chart(fig_tree, width="stretch", config=CHART_CONFIG)

    # =================================================================
    # TAB 2: COMPARE
    # =================================================================
    with tab_compare:
        st.subheader("Brand vs Brand Comparison")
        st.caption("Select two brands to compare their shrinkflation profiles")

        comp_brands = sorted(filtered["brand"].dropna().unique())
        cc1, cc2 = st.columns(2)
        with cc1:
            brand_a = st.selectbox("Brand A", comp_brands, index=0, key="brand_a")
        with cc2:
            brand_b = st.selectbox("Brand B", comp_brands,
                                   index=min(1, len(comp_brands) - 1), key="brand_b")

        if brand_a and brand_b:
            data_a = filtered[filtered["brand"] == brand_a]
            data_b = filtered[filtered["brand"] == brand_b]

            c1, c2 = st.columns(2)

            with c1:
                st.markdown(f"### {brand_a}")
                ma1, ma2, ma3 = st.columns(3)
                ma1.metric("Flags", len(data_a))
                avg_a = data_a["real_price_increase_pct"].mean() if not data_a.empty else 0
                ma2.metric("Avg Increase", f"+{avg_a:.1f}%")
                high_a = (data_a["severity"] == "HIGH").sum() if not data_a.empty else 0
                ma3.metric("HIGH", high_a)

                if not data_a.empty:
                    st.markdown("**Flagged Products:**")
                    top_a = data_a.nlargest(5, "real_price_increase_pct")[["product", "real_price_increase_pct", "severity"]]
                    for _, row in top_a.iterrows():
                        sev_class = f"severity-{row['severity'].lower()}"
                        st.markdown(
                            f"- {row['product']} — +{row['real_price_increase_pct']:.1f}% "
                            f"<span class='{sev_class}'>{row['severity']}</span>",
                            unsafe_allow_html=True,
                        )

            with c2:
                st.markdown(f"### {brand_b}")
                mb1, mb2, mb3 = st.columns(3)
                mb1.metric("Flags", len(data_b))
                avg_b = data_b["real_price_increase_pct"].mean() if not data_b.empty else 0
                mb2.metric("Avg Increase", f"+{avg_b:.1f}%")
                high_b = (data_b["severity"] == "HIGH").sum() if not data_b.empty else 0
                mb3.metric("HIGH", high_b)

                if not data_b.empty:
                    st.markdown("**Flagged Products:**")
                    top_b = data_b.nlargest(5, "real_price_increase_pct")[["product", "real_price_increase_pct", "severity"]]
                    for _, row in top_b.iterrows():
                        sev_class = f"severity-{row['severity'].lower()}"
                        st.markdown(
                            f"- {row['product']} — +{row['real_price_increase_pct']:.1f}% "
                            f"<span class='{sev_class}'>{row['severity']}</span>",
                            unsafe_allow_html=True,
                        )

            # Verdict
            st.divider()
            if avg_a > avg_b:
                worse, better = brand_a, brand_b
                diff = abs(avg_a - avg_b)
            else:
                worse, better = brand_b, brand_a
                diff = abs(avg_b - avg_a)

            st.markdown(f"""
            <div class="compare-card">
                <h3>Verdict</h3>
                <p><strong>{worse}</strong> has a <strong>+{diff:.1f}%</strong> higher average hidden price increase than <strong>{better}</strong>.</p>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # Category vs Category
        st.subheader("Category vs Category")
        all_cats = sorted(filtered["category"].dropna().unique())
        ct1, ct2 = st.columns(2)
        with ct1:
            cat_a = st.selectbox("Category A", all_cats, index=0, key="cat_a")
        with ct2:
            cat_b = st.selectbox("Category B", all_cats,
                                 index=min(1, len(all_cats) - 1), key="cat_b")

        if cat_a and cat_b:
            d_a = filtered[filtered["category"] == cat_a]
            d_b = filtered[filtered["category"] == cat_b]

            compare_df = pd.DataFrame({
                "Metric": ["Total Flags", "Avg Hidden Increase", "HIGH Severity",
                           "Max Increase", "Brands Affected"],
                cat_a.title(): [
                    str(len(d_a)),
                    f"+{d_a['real_price_increase_pct'].mean():.1f}%" if not d_a.empty else "0%",
                    str(int((d_a["severity"] == "HIGH").sum())) if not d_a.empty else "0",
                    f"+{d_a['real_price_increase_pct'].max():.1f}%" if not d_a.empty else "0%",
                    str(d_a["brand"].nunique()) if not d_a.empty else "0",
                ],
                cat_b.title(): [
                    str(len(d_b)),
                    f"+{d_b['real_price_increase_pct'].mean():.1f}%" if not d_b.empty else "0%",
                    str(int((d_b["severity"] == "HIGH").sum())) if not d_b.empty else "0",
                    f"+{d_b['real_price_increase_pct'].max():.1f}%" if not d_b.empty else "0%",
                    str(d_b["brand"].nunique()) if not d_b.empty else "0",
                ],
            })
            st.dataframe(compare_df, width="stretch", hide_index=True)

    # =================================================================
    # TAB 3: DEEP DIVE
    # =================================================================
    with tab_deepdive:
        st.subheader("Brand Deep Dive")
        brand_list = sorted(filtered["brand"].dropna().unique())
        dive_brand = st.selectbox("Choose brand", brand_list, key="brand_dive")

        if dive_brand:
            brand_data = filtered[filtered["brand"] == dive_brand]

            bc1, bc2, bc3, bc4 = st.columns(4)
            bc1.metric("Flagged Products", len(brand_data))
            bc2.metric("Avg Increase", f"+{brand_data['real_price_increase_pct'].mean():.1f}%")
            high_pct = (brand_data["severity"] == "HIGH").sum() / max(len(brand_data), 1) * 100
            bc3.metric("HIGH Severity", f"{high_pct:.0f}%")
            bc4.metric("Categories", brand_data["category"].nunique())

            fig_brand = px.bar(
                brand_data.sort_values("real_price_increase_pct", ascending=False).head(20),
                x="real_price_increase_pct", y="product", orientation="h",
                color="severity", color_discrete_map=SEVERITY_COLORS,
                labels={"real_price_increase_pct": "Hidden Increase (%)", "product": ""},
                text="real_price_increase_pct",
            )
            fig_brand.update_traces(texttemplate="+%{text:.1f}%", textposition="outside")
            fig_brand.update_layout(**CHART_LAYOUT, height=max(300, len(brand_data.head(20)) * 30))
            fig_brand.update_yaxes(categoryorder="total ascending")
            st.plotly_chart(fig_brand, width="stretch", config=CHART_CONFIG)

            # Size change distribution
            if "old_size" in brand_data.columns and "new_size" in brand_data.columns:
                bdc = brand_data.copy()
                bdc["size_change_pct"] = (bdc["new_size"] - bdc["old_size"]) / bdc["old_size"] * 100
                fig_hist = px.histogram(
                    bdc, x="size_change_pct", nbins=15,
                    color="severity", color_discrete_map=SEVERITY_COLORS,
                    labels={"size_change_pct": "Size Change (%)"},
                    title=f"Size Change Distribution — {dive_brand}",
                )
                fig_hist.update_layout(**CHART_LAYOUT, height=280, barmode="stack")
                st.plotly_chart(fig_hist, width="stretch", config=CHART_CONFIG)

        st.divider()

        # Product Timeline
        st.subheader("Product Timeline")
        st.caption("Select a product to see its price and size history")

        if not products_df.empty:
            product_names = sorted(products_df["name"].dropna().unique())
            selected_product = st.selectbox(
                "Search & select product",
                [""] + list(product_names),
                key="product_timeline",
            )

            if selected_product:
                history = get_product_history(selected_product)

                if isinstance(history, dict) and "error" in history:
                    st.warning(history["error"])
                elif isinstance(history, dict) and history.get("snapshots"):
                    st.markdown(f"**{history['product']}** by {history['brand']} ({history['category']})")

                    snap_df = pd.DataFrame(history["snapshots"])
                    snap_df["date"] = pd.to_datetime(snap_df["date"])

                    fig_combo = make_subplots(specs=[[{"secondary_y": True}]])

                    if snap_df["size_value"].notna().any():
                        fig_combo.add_trace(
                            go.Scatter(
                                x=snap_df["date"], y=snap_df["size_value"],
                                mode="lines+markers", name="Size",
                                line=dict(color="#3498db", width=3),
                                marker=dict(size=8),
                            ),
                            secondary_y=False,
                        )

                    snap_df["price_num"] = snap_df["price"].apply(
                        lambda x: float(x.replace("$", "")) if isinstance(x, str) and x.startswith("$") else None
                    )
                    if snap_df["price_num"].notna().any():
                        fig_combo.add_trace(
                            go.Scatter(
                                x=snap_df["date"], y=snap_df["price_num"],
                                mode="lines+markers", name="Price ($)",
                                line=dict(color="#e74c3c", width=3),
                                marker=dict(size=8),
                            ),
                            secondary_y=True,
                        )

                    fig_combo.update_layout(
                        **CHART_LAYOUT, height=380,
                        title=f"Size & Price — {history['product']}",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02),
                    )
                    fig_combo.update_yaxes(title_text="Size", secondary_y=False)
                    fig_combo.update_yaxes(title_text="Price ($)", secondary_y=True)
                    st.plotly_chart(fig_combo, width="stretch", config=CHART_CONFIG)

                    if history.get("shrinkflation_events"):
                        st.markdown("**Shrinkflation Events:**")
                        for evt in history["shrinkflation_events"]:
                            sev = evt["severity"]
                            sev_class = f"severity-{sev.lower()}"
                            st.markdown(
                                f"- **{evt['date']}**: Size {evt['old_size']} → {evt['new_size']} "
                                f"({evt['real_increase_pct']} real increase) "
                                f"<span class='{sev_class}'>{sev}</span>",
                                unsafe_allow_html=True,
                            )
                    else:
                        st.success("No shrinkflation events detected.")
                else:
                    st.info("No history found.")

    # =================================================================
    # TAB 4: EXPLORER
    # =================================================================
    with tab_explorer:
        st.subheader("Data Explorer")

        # Scatter plot
        st.markdown("### Size Reduction vs Price Increase")
        st.caption("Each dot = one flagged product. Hover for details.")

        if "old_size" in filtered.columns and "new_size" in filtered.columns:
            scatter_df = filtered.copy()
            scatter_df["size_change_pct"] = (
                (scatter_df["new_size"] - scatter_df["old_size"]) / scatter_df["old_size"] * 100
            )
            scatter_df["size_marker"] = scatter_df["severity"].map({"HIGH": 14, "MEDIUM": 10, "LOW": 7})

            fig_scatter = px.scatter(
                scatter_df, x="size_change_pct", y="real_price_increase_pct",
                color="category", size="size_marker",
                hover_data=["product", "brand", "severity"],
                labels={
                    "size_change_pct": "Size Change (%)",
                    "real_price_increase_pct": "Real Price Increase (%)",
                    "category": "Category",
                },
                opacity=0.7,
            )
            fig_scatter.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
            fig_scatter.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.5)
            fig_scatter.update_layout(**CHART_LAYOUT, height=450,
                                      legend=dict(orientation="h", yanchor="bottom", y=-0.35))
            st.plotly_chart(fig_scatter, width="stretch", config=CHART_CONFIG)

        st.divider()

        # Heatmap
        st.markdown("### Brand x Category Heatmap")
        st.caption("Darker = higher hidden price increase")

        top_brands = filtered["brand"].value_counts().head(12).index.tolist()
        heatmap_df = filtered[filtered["brand"].isin(top_brands)]

        if not heatmap_df.empty:
            pivot = heatmap_df.pivot_table(
                values="real_price_increase_pct",
                index="brand", columns="category",
                aggfunc="mean",
            ).round(1)

            fig_heat = px.imshow(
                pivot, color_continuous_scale="RdYlGn_r",
                labels={"color": "Avg Increase %"},
                text_auto=True, aspect="auto",
            )
            fig_heat.update_layout(height=450, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig_heat, width="stretch", config=CHART_CONFIG)

        st.divider()

        # Price Impact Calculator
        st.markdown("### Price Impact Calculator")
        st.caption("Calculate the real cost of shrinkflation on any product")

        calc_col1, calc_col2 = st.columns(2)
        with calc_col1:
            old_size_input = st.number_input("Original Size (oz)", value=16.0, step=0.5, min_value=0.1)
            old_price_input = st.number_input("Original Price ($)", value=5.49, step=0.25, min_value=0.01)
        with calc_col2:
            new_size_input = st.number_input("New Size (oz)", value=14.0, step=0.5, min_value=0.1)
            new_price_input = st.number_input("New Price ($)", value=5.99, step=0.25, min_value=0.01)

        if st.button("Calculate Impact", type="primary"):
            old_ppu = old_price_input / old_size_input
            new_ppu = new_price_input / new_size_input
            real_increase = ((new_ppu - old_ppu) / old_ppu) * 100
            size_change = ((new_size_input - old_size_input) / old_size_input) * 100

            res1, res2, res3 = st.columns(3)
            res1.metric("Size Change", f"{size_change:+.1f}%")
            res2.metric("Price/oz", f"${old_ppu:.3f} → ${new_ppu:.3f}")
            res3.metric("Real Increase", f"{real_increase:+.1f}%")

            if real_increase > 10:
                st.error(f"HIGH shrinkflation! You're paying **{real_increase:.1f}% more** per unit.")
            elif real_increase > 5:
                st.warning(f"MEDIUM shrinkflation. **{real_increase:.1f}% more** per unit.")
            elif real_increase > 0:
                st.info(f"Mild increase: **{real_increase:.1f}%** per unit.")
            else:
                st.success(f"No shrinkflation — paying **{abs(real_increase):.1f}% less** per unit.")

            monthly = st.slider("How many do you buy per month?", 1, 20, 4)
            annual_extra = (new_ppu - old_ppu) * new_size_input * monthly * 12
            if annual_extra > 0:
                st.markdown(f"**Annual Impact:** Extra **${annual_extra:.2f}/year** on this product alone.")

    # =================================================================
    # TAB 5: AI INSIGHTS
    # =================================================================
    with tab_ai:
        st.subheader("AI-Powered Insights")

        insight_content, insight_time = load_latest_insight()
        if insight_content:
            st.markdown(f"""
            <div class="info-card">
                <strong>Latest Analysis</strong><br><br>
                {insight_content}
            </div>
            """, unsafe_allow_html=True)
            if insight_time:
                st.caption(f"Generated: {insight_time.strftime('%Y-%m-%d %H:%M UTC')}")
        else:
            st.caption("No AI insights yet.")

        if st.button("Generate New Insight", type="primary"):
            try:
                from agent.analyst import generate_daily_insight
                with st.spinner("AI analyzing data..."):
                    new_insight = generate_daily_insight()
                st.success(new_insight)
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Could not generate: {e}. Set OPENAI_API_KEY in .env")

        st.markdown("---")

        st.subheader("Ask the Data")
        user_q = st.text_input(
            "Your question",
            placeholder="Which brand has the worst shrinkflation? What's the worst category?",
        )
        if st.button("Ask", type="secondary") and user_q:
            try:
                from agent.analyst import chat_with_data_streaming
                container = st.empty()
                full = ""
                for chunk in chat_with_data_streaming(user_q):
                    full += chunk
                    container.markdown(full)
            except Exception as e:
                st.error(f"Agent error: {e}")

        st.divider()

        st.markdown("**Quick Questions:**")
        quick_qs = [
            "What brand has the worst shrinkflation?",
            "Which category is most affected?",
            "Compare Frito-Lay vs General Mills",
            "What's the biggest size reduction?",
        ]
        for q in quick_qs:
            if st.button(f"{q}", key=f"qq_{q}"):
                try:
                    from agent.analyst import chat_with_data_streaming
                    container = st.empty()
                    full = ""
                    for chunk in chat_with_data_streaming(q):
                        full += chunk
                        container.markdown(full)
                except Exception as e:
                    st.error(f"Agent error: {e}")

    # =================================================================
    # TAB 6: DATA TABLE
    # =================================================================
    with tab_data:
        st.subheader("Flagged Products Data")

        search = st.text_input("Search by product or brand", "", key="table_search")

        display = filtered.copy()
        if search:
            mask = (
                display["product"].str.contains(search, case=False, na=False)
                | display["brand"].str.contains(search, case=False, na=False)
            )
            display = display[mask]

        all_show_cols = ["product", "brand", "category", "old_size", "new_size",
                         "old_price", "new_price", "real_price_increase_pct", "severity",
                         "retailer", "detected_at"]
        existing = [c for c in all_show_cols if c in display.columns]
        table = display[existing].copy()

        if "old_price" in table.columns:
            table["old_price"] = table["old_price"].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
        if "new_price" in table.columns:
            table["new_price"] = table["new_price"].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
        if "real_price_increase_pct" in table.columns:
            table["real_price_increase_pct"] = table["real_price_increase_pct"].apply(
                lambda x: f"+{x:.1f}%" if pd.notna(x) else "N/A"
            )

        st1, st2, st3 = st.columns(3)
        st1.metric("Showing", f"{len(table):,}")
        if not display.empty and "real_price_increase_pct" in filtered.columns:
            st2.metric("Avg Increase", f"+{filtered['real_price_increase_pct'].mean():.1f}%")
            st3.metric("Max Increase", f"+{filtered['real_price_increase_pct'].max():.1f}%")

        def color_severity(val):
            return {
                "HIGH": "background-color: #fadbd8; color: #922b21; font-weight: 600",
                "MEDIUM": "background-color: #fdebd0; color: #935116; font-weight: 600",
                "LOW": "background-color: #fef9e7; color: #7d6608; font-weight: 600",
            }.get(val, "")

        if not table.empty and "severity" in table.columns:
            st.dataframe(
                table.style.map(color_severity, subset=["severity"]),
                width="stretch", height=500,
            )
        else:
            st.dataframe(table, width="stretch", height=500)

        st.caption(f"Showing {len(table):,} of {len(display):,} flagged products")

        st.markdown("---")
        dl1, dl2, _ = st.columns([1, 1, 2])
        with dl1:
            csv = display[existing].to_csv(index=False)
            st.download_button(
                "Download CSV",
                data=csv,
                file_name=f"shrinkflation_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )
        with dl2:
            json_data = display[existing].to_json(orient="records", indent=2)
            st.download_button(
                "Download JSON",
                data=json_data,
                file_name=f"shrinkflation_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
            )

else:
    live_display_df = filtered_products if not filtered_products.empty else products_df

    if not products_df.empty:
        if filtered_products.empty and (
            selected_category != "All Categories"
            or selected_brand != "All Brands"
            or date_range != "All time"
        ):
            st.info(
                "No live products match the current filters yet. Showing the overall tracked inventory below so "
                "you can still review genuine source-backed data."
            )
        else:
            st.info(
                "Live products are loading correctly. Shrinkflation flags appear only after the "
                "same product is observed again later at a smaller size."
            )

        overview_tab, preview_tab, category_tab, integrity_tab = st.tabs(
            ["Live Overview", "Live Products", "Category Mix", "Data Integrity"]
        )

        with overview_tab:
            ov1, ov2, ov3, ov4 = st.columns(4)
            ov1.metric("Live Products", f"{len(live_display_df):,}")
            ov2.metric("Tracked Categories", f"{inventory_summary['category_count']:,}")
            ov3.metric("Tracked Brands", f"{inventory_summary['brand_count']:,}")
            ov4.metric("Exact UPC Price Matches", f"{inventory_summary['price_matched_products']:,}")

            chart_col1, chart_col2 = st.columns([3, 2])

            with chart_col1:
                st.subheader("Top Brands by Live Products")
                if "brand" in live_display_df.columns:
                    brand_counts = (
                        live_display_df["brand"]
                        .fillna("Unknown")
                        .replace("", "Unknown")
                        .value_counts()
                        .reset_index()
                    )
                    brand_counts.columns = ["brand", "products"]
                    if not brand_counts.empty:
                        fig_live_brands = px.bar(
                            brand_counts.head(12),
                            x="products",
                            y="brand",
                            orientation="h",
                            color="products",
                            color_continuous_scale="Tealgrn",
                            labels={"products": "Products Collected", "brand": ""},
                            text="products",
                        )
                        fig_live_brands.update_traces(textposition="outside")
                        fig_live_brands.update_layout(**CHART_LAYOUT, height=420)
                        fig_live_brands.update_yaxes(categoryorder="total ascending")
                        st.plotly_chart(fig_live_brands, width="stretch", config=CHART_CONFIG)
                    else:
                        st.caption("Brand data will appear here as more live products are collected.")
                else:
                    st.caption("Brand data will appear here as more live products are collected.")

            with chart_col2:
                st.subheader("Barcode Coverage")
                barcode_with = (
                    int(live_display_df["barcode"].fillna("").astype(str).str.strip().ne("").sum())
                    if "barcode" in live_display_df.columns
                    else 0
                )
                barcode_without = max(len(live_display_df) - barcode_with, 0)
                barcode_chart_df = pd.DataFrame(
                    {
                        "status": ["With Barcode", "Missing Barcode"],
                        "count": [barcode_with, barcode_without],
                    }
                )
                fig_barcode = px.pie(
                    barcode_chart_df,
                    values="count",
                    names="status",
                    hole=0.55,
                    color="status",
                    color_discrete_map={
                        "With Barcode": "#22c55e",
                        "Missing Barcode": "#ef4444",
                    },
                )
                fig_barcode.update_traces(textinfo="percent+value", textfont_size=11)
                fig_barcode.update_layout(
                    height=420,
                    margin=dict(l=10, r=10, t=10, b=10),
                    showlegend=True,
                    legend=dict(orientation="h", y=-0.1),
                )
                st.plotly_chart(fig_barcode, width="stretch", config=CHART_CONFIG)

            latest_seen_label = "N/A"
            if inventory_summary["latest_seen_at"] is not None:
                latest_seen_label = pd.to_datetime(
                    inventory_summary["latest_seen_at"], utc=True, errors="coerce"
                ).strftime("%Y-%m-%d %H:%M UTC")
            st.caption(
                f"Latest live observation: {latest_seen_label} | "
                f"Size snapshots stored: {inventory_summary['size_snapshot_count']:,}"
            )

        with preview_tab:
            st.subheader("Recently Collected Products")
            preview = live_display_df.copy()
            for column in ["last_seen_at", "source_last_modified_at"]:
                if column in preview.columns:
                    preview[column] = pd.to_datetime(preview[column], utc=True, errors="coerce")
                    preview[column] = preview[column].dt.strftime("%Y-%m-%d %H:%M UTC")

            preview_columns = [
                "name",
                "brand",
                "category",
                "barcode",
                "last_seen_at",
                "source_last_modified_at",
            ]
            existing_preview_columns = [col for col in preview_columns if col in preview.columns]
            st.dataframe(
                preview[existing_preview_columns].head(100),
                width="stretch",
                height=520,
                hide_index=True,
            )
            st.caption(
                f"Showing {min(len(preview), 100):,} of {len(preview):,} live products currently stored."
            )

        with category_tab:
            st.subheader("Products by Category")
            if "category" in live_display_df.columns:
                category_counts = (
                    live_display_df["category"]
                    .fillna("Unknown")
                    .replace("", "Unknown")
                    .value_counts()
                    .reset_index()
                )
                category_counts.columns = ["category", "products"]
                if not category_counts.empty:
                    fig_live_categories = px.bar(
                        category_counts.head(15),
                        x="products",
                        y="category",
                        orientation="h",
                        color="products",
                        color_continuous_scale="Blues",
                        labels={"products": "Products Collected", "category": ""},
                        text="products",
                    )
                    fig_live_categories.update_traces(textposition="outside")
                    fig_live_categories.update_layout(**CHART_LAYOUT, height=420)
                    fig_live_categories.update_yaxes(categoryorder="total ascending")
                    st.plotly_chart(fig_live_categories, width="stretch", config=CHART_CONFIG)
                else:
                    st.caption("Category data will appear here as products are scanned.")
            else:
                st.caption("Category data will appear here as products are scanned.")

        with integrity_tab:
            in1, in2, in3, in4 = st.columns(4)
            in1.metric("Barcode Coverage", f"{inventory_summary['barcode_coverage_pct']:.1f}%")
            in2.metric(
                "Source Timestamp Coverage",
                f"{inventory_summary['source_timestamp_coverage_pct']:.1f}%",
            )
            in3.metric(
                "Exact UPC Match Coverage",
                f"{inventory_summary['exact_price_match_pct']:.1f}%",
            )
            in4.metric("Size Snapshots Stored", f"{inventory_summary['size_snapshot_count']:,}")

            integrity_rules = pd.DataFrame(
                [
                    {
                        "Rule": "No static seed data",
                        "Status": "Enabled",
                        "Details": "Historical demo rows are not loaded into the dashboard database.",
                    },
                    {
                        "Rule": "Live product source",
                        "Status": "Open Food Facts",
                        "Details": "Products are inserted only from live Open Food Facts API responses that pass name, identity, and package-size parsing checks.",
                    },
                    {
                        "Rule": "Price source",
                        "Status": "Exact UPC only",
                        "Details": "Kroger prices are attached only when the API returns an exact barcode match for the same product.",
                    },
                    {
                        "Rule": "Shrink detection",
                        "Status": "Live snapshots only",
                        "Details": "A shrink case is created only after a later live observation records a smaller package size for the same product.",
                    },
                ]
            )
            st.dataframe(integrity_rules, width="stretch", hide_index=True)
            st.caption(
                f"Top live category: {inventory_summary['top_category']} | "
                f"Top live brand: {inventory_summary['top_brand']}"
            )

        if _scan_result.get("off_error"):
            st.warning(f"Open Food Facts scan warning: {_scan_result['off_error']}")
        if _scan_result.get("kroger_error"):
            st.warning(f"Kroger scan warning: {_scan_result['kroger_error']}")
    else:
        st.info("Scanner is running — products from Open Food Facts will appear as they're fetched. Dashboard refreshes every 60 seconds.")
        if _scan_result.get("off_error"):
            st.warning(f"Open Food Facts scan warning: {_scan_result['off_error']}")
        if _scan_result.get("kroger_error"):
            st.warning(f"Kroger scan warning: {_scan_result['kroger_error']}")

# =====================================================================
# FOOTER
# =====================================================================
st.markdown("---")
st.markdown(f"""
<div class="footer">
    <strong>Shrinkflation Detector</strong><br>
    Live product data comes from the <a href="https://world.openfoodfacts.org/" target="_blank">Open Food Facts</a> API and is rescanned every 60 seconds.<br>
    Kroger price data is optional and only attached when an exact UPC match is returned by the Kroger API.<br>
    No static shrinkflation seed data is loaded into the dashboard database.<br>
    Built with Python, Streamlit, SQLAlchemy, and Plotly
</div>
""", unsafe_allow_html=True)
