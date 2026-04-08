"""
Shrinkflation Detector — Streamlit Dashboard
Hybrid-aware, source-correct, recruiter-ready.

Data architecture:
  - documented_historical : 500+ verified cases from BLS, Consumer Reports,
                            mouseprint.org, FTC filings, and media investigations.
                            Loaded once at startup. Powers immediate analysis.
  - live_detected         : Confirmed shrinkflation found by comparing real API
                            snapshots (Open Food Facts sizes + Kroger prices) over
                            time. Requires ≥30-day gap, confirmed PPU increase.
                            Zero confirmed live cases early in deployment is correct.

Refresh policy:
  - No auto-refresh. Live scan runs once per 30-minute cache window.
  - Manual refresh button clears the cache and re-runs the scan.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timezone

from sqlalchemy import text

from db.models import (
    Product, ProductSnapshot, ShrinkflationFlag, IngestionRun, AgentInsight,
    get_session, get_engine, init_db, add_missing_columns,
)

# =====================================================================
# PAGE CONFIG
# =====================================================================
st.set_page_config(
    page_title="Shrinkflation Detector",
    page_icon="📉",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =====================================================================
# CSS
# =====================================================================
st.markdown("""
<style>
    .block-container { padding: 0.5rem 1rem 1rem 1rem; max-width: 100%; }

    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 1.2rem 1.5rem; border-radius: 12px; margin-bottom: 0.8rem; color: white;
    }
    .main-header h1 { color: white !important; margin: 0; font-size: 1.8rem; line-height: 1.2; }
    .main-header p { color: #94a3b8; margin: 0.3rem 0 0 0; font-size: 0.9rem; line-height: 1.4; }

    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        border: 1px solid #475569; border-radius: 10px; padding: 10px 14px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    div[data-testid="stMetric"] label { font-size: 0.75rem !important; color: #cbd5e1 !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 1.3rem !important; font-weight: 700 !important; color: #f1f5f9 !important;
    }
    @media (prefers-color-scheme: light) {
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border: 1px solid #dee2e6; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        div[data-testid="stMetric"] label { color: #495057 !important; }
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #1e293b !important; }
    }

    .stTabs [data-baseweb="tab-list"] { gap: 4px; flex-wrap: wrap; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0; padding: 6px 12px;
        font-weight: 600; font-size: 0.85rem; white-space: nowrap;
    }

    .severity-high { background:#e74c3c; color:white; padding:2px 10px; border-radius:12px; font-weight:600; font-size:0.8rem; }
    .severity-medium { background:#f39c12; color:white; padding:2px 10px; border-radius:12px; font-weight:600; font-size:0.8rem; }
    .severity-low { background:#f1c40f; color:#333; padding:2px 10px; border-radius:12px; font-weight:600; font-size:0.8rem; }

    .source-hist {
        display:inline-block; background:rgba(99,102,241,0.15); border:1px solid rgba(99,102,241,0.4);
        color:#818cf8; padding:3px 10px; border-radius:20px; font-size:0.72rem; font-weight:600; margin:2px;
    }
    .source-live {
        display:inline-block; background:rgba(34,197,94,0.15); border:1px solid rgba(34,197,94,0.4);
        color:#4ade80; padding:3px 10px; border-radius:20px; font-size:0.72rem; font-weight:600; margin:2px;
    }
    .source-combined {
        display:inline-block; background:rgba(251,191,36,0.15); border:1px solid rgba(251,191,36,0.4);
        color:#fbbf24; padding:3px 10px; border-radius:20px; font-size:0.72rem; font-weight:600; margin:2px;
    }

    .funnel-card {
        background: rgba(30,41,59,0.8); border:1px solid #334155; border-radius:10px;
        padding:1rem; margin-bottom:0.6rem; color:#e2e8f0;
    }
    .funnel-step { font-size:0.85rem; color:#94a3b8; margin:0.2rem 0; }
    .funnel-num { font-size:1.4rem; font-weight:700; color:#f1f5f9; }

    .info-card {
        background:rgba(30,41,59,0.8); border:1px solid #475569; border-radius:10px;
        padding:1rem; margin-bottom:0.8rem; box-shadow:0 1px 3px rgba(0,0,0,0.2); color:#e2e8f0;
    }

    .compare-card {
        background:linear-gradient(135deg,rgba(127,29,29,0.3) 0%,rgba(153,27,27,0.2) 100%);
        border:2px solid #f87171; border-radius:12px; padding:1.2rem; text-align:center; color:#fecaca;
    }
    .compare-card h3 { color:#fca5a5 !important; }

    .methodology-block {
        background:rgba(15,52,96,0.3); border-left:4px solid #3b82f6;
        border-radius:0 8px 8px 0; padding:0.8rem 1rem; margin:0.6rem 0; color:#cbd5e1;
        font-size:0.85rem; line-height:1.6;
    }

    .footer { text-align:center; color:#94a3b8; padding:1.5rem 0; font-size:0.8rem; line-height:1.6; }
    .footer a { color:#818cf8; }

    @media (max-width: 768px) {
        .block-container { padding: 0.3rem 0.5rem 1rem 0.5rem !important; }
        .main-header { padding: 0.8rem 1rem; border-radius: 8px; }
        .main-header h1 { font-size: 1.3rem !important; }
        .main-header p { font-size: 0.75rem !important; }
        div[data-testid="stMetric"] { padding: 8px 10px; }
        div[data-testid="stMetric"] label { font-size: 0.65rem !important; }
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] { font-size: 1.1rem !important; }
        div[data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
        div[data-testid="stHorizontalBlock"] > div { flex: 1 1 100% !important; min-width: 100% !important; }
        .stTabs [data-baseweb="tab"] { padding: 5px 8px; font-size: 0.75rem; }
        h2, h3, .stSubheader { font-size: 1.1rem !important; }
        .stPlotlyChart { min-height: 280px; }
    }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# CHART DEFAULTS
# =====================================================================
CHART_LAYOUT = dict(
    template="plotly_white",
    plot_bgcolor="white",
    paper_bgcolor="white",
    xaxis=dict(showgrid=True, gridcolor="#f0f0f0", zeroline=False),
    yaxis=dict(showgrid=False, zeroline=False),
    margin=dict(l=20, r=20, t=30, b=20),
    font=dict(size=13, family="Inter, system-ui, sans-serif", color="#1e293b"),
    coloraxis_showscale=False,
)
CHART_CONFIG = {"displayModeBar": False, "responsive": True}
SEVERITY_COLORS = {"HIGH": "#e74c3c", "MEDIUM": "#f39c12", "LOW": "#f1c40f"}
SOURCE_COLORS = {"documented_historical": "#818cf8", "live_detected": "#4ade80"}

# =====================================================================
# STARTUP — once per app lifecycle
# =====================================================================
@st.cache_resource
def _init_and_load():
    """Create tables + load documented historical cases. Idempotent."""
    init_db()
    from data.historical_loader import load_historical_cases
    load_historical_cases()

_init_and_load()

# Always run migrations (idempotent, fast) so columns added after
# the cached init_db() are present even if the DB file survived a
# Streamlit Cloud redeploy without cache invalidation.
add_missing_columns()

# =====================================================================
# LIVE SCAN — cached for 30 minutes, runs at most once per window
# =====================================================================
@st.cache_data(ttl=1800)
def _run_live_scan():
    """
    Run one live ingestion tick (OFF + Kroger) then one detection pass.
    TTL=1800 → runs at most once every 30 minutes per Streamlit session.
    Returns a stats dict for display in the pipeline status panel.
    """
    from scraper.live_tracker import run_live_update
    from scraper.kroger import scrape_kroger
    from analysis.detector import run_detection

    stats: dict = {"scanned_at": datetime.now(timezone.utc).isoformat()}

    try:
        off = run_live_update(max_categories=2)
        stats.update({
            "new_products": off.get("new_products", 0),
            "new_snapshots": off.get("new_snapshots", 0),
            "phase": off.get("phase", "unknown"),
            "panel_size": off.get("panel_size", 0),
        })
    except Exception as e:
        stats["off_error"] = str(e)[:120]

    try:
        matched, kr_snaps = scrape_kroger()
        stats["kroger_matched"] = matched
        stats["kroger_snapshots"] = kr_snaps
    except Exception as e:
        stats["kroger_error"] = str(e)[:120]

    try:
        new_flags = run_detection()
        stats["new_flags"] = new_flags
    except Exception as e:
        stats["detection_error"] = str(e)[:120]

    return stats


# =====================================================================
# DATA LOADERS — cached for 5 minutes (display data, not scan)
# =====================================================================
@st.cache_data(ttl=300)
def load_flags_df() -> pd.DataFrame:
    """
    Load all confirmed shrinkflation flags joined to products.
    Includes flag_source and price_per_unit_increase_pct.
    """
    engine = get_engine()
    try:
        df = pd.read_sql(
            """
            SELECT
                f.id,
                f.flag_source,
                f.old_size,
                f.new_size,
                f.size_unit,
                f.old_price,
                f.new_price,
                f.has_price_evidence,
                f.price_per_unit_increase_pct,
                f.severity,
                f.detected_at,
                p.name   AS product,
                p.brand,
                p.category,
                p.data_source AS product_source,
                p.retailer
            FROM shrinkflation_flags f
            JOIN products p ON p.id = f.product_id
            ORDER BY f.detected_at DESC
            """,
            engine,
        )
        # Ensure numeric columns are truly numeric — DB drivers sometimes
        # return object dtype when NULLs are mixed with numbers.
        for col in ("old_size", "new_size", "old_price", "new_price", "price_per_unit_increase_pct"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if "has_price_evidence" in df.columns:
            df["has_price_evidence"] = df["has_price_evidence"].astype(bool)
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_products_df() -> pd.DataFrame:
    """Load all products with source labels."""
    engine = get_engine()
    try:
        return pd.read_sql(
            "SELECT id, name, brand, category, data_source, retailer FROM products",
            engine,
        )
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_tracking_funnel() -> dict:
    """
    Compute live detection funnel metrics directly in SQL.
    Returns counts at each stage of the evidence pipeline.
    """
    engine = get_engine()
    try:
        with engine.connect() as conn:
            # Live products
            live_products = conn.execute(text(
                "SELECT COUNT(*) FROM products "
                "WHERE data_source IN ('live_openfoodfacts','live_kroger','live_combined')"
            )).scalar() or 0

            # Products with ≥2 real_observed snapshots
            with_2_snaps = conn.execute(text(
                """
                SELECT COUNT(*) FROM (
                    SELECT ps.product_id
                    FROM product_snapshots ps
                    JOIN products p ON p.id = ps.product_id
                    WHERE ps.observation_type = 'real_observed'
                      AND p.data_source IN ('live_openfoodfacts','live_kroger','live_combined')
                    GROUP BY ps.product_id
                    HAVING COUNT(*) >= 2
                ) t
                """
            )).scalar() or 0

            # Products with ≥1 enrichable snapshot (has both size and price in real_observed)
            enrichable = conn.execute(text(
                """
                SELECT COUNT(DISTINCT ps.product_id)
                FROM product_snapshots ps
                JOIN products p ON p.id = ps.product_id
                WHERE ps.observation_type = 'real_observed'
                  AND ps.price > 0
                  AND ps.size_value > 0
                  AND ps.size_unit_family NOT IN ('unknown')
                  AND ps.size_unit_family IS NOT NULL
                  AND p.data_source IN ('live_openfoodfacts','live_kroger','live_combined')
                """
            )).scalar() or 0

            # Confirmed live flags
            confirmed_live = conn.execute(text(
                "SELECT COUNT(*) FROM shrinkflation_flags "
                "WHERE flag_source = 'live_detected'"
            )).scalar() or 0

            # Last ingestion run
            last_run = conn.execute(text(
                """
                SELECT started_at, finished_at, status, source, phase,
                       products_added, snapshots_added, flags_added
                FROM ingestion_runs
                ORDER BY started_at DESC LIMIT 1
                """
            )).fetchone()

        return {
            "live_products": live_products,
            "with_2_snaps": with_2_snaps,
            "enrichable": enrichable,
            "confirmed_live": confirmed_live,
            "last_run": dict(last_run._mapping) if last_run else None,
        }
    except Exception as e:
        return {
            "live_products": 0, "with_2_snaps": 0,
            "enrichable": 0, "confirmed_live": 0,
            "last_run": None, "error": str(e),
        }


@st.cache_data(ttl=300)
def load_latest_insight():
    try:
        session = get_session()
        insight = (
            session.query(AgentInsight)
            .filter(AgentInsight.insight_type == "daily")
            .order_by(AgentInsight.generated_at.desc())
            .first()
        )
        session.close()
        return (insight.content, insight.generated_at) if insight else (None, None)
    except Exception:
        return None, None


# =====================================================================
# LOAD DATA
# =====================================================================
_scan_result = _run_live_scan()
flags_df = load_flags_df()
products_df = load_products_df()
funnel = load_tracking_funnel()

# Split flags by source — used throughout
_hist_mask = flags_df["flag_source"] == "documented_historical" if not flags_df.empty else pd.Series(dtype=bool)
_live_mask = flags_df["flag_source"] == "live_detected" if not flags_df.empty else pd.Series(dtype=bool)
hist_flags = flags_df[_hist_mask] if not flags_df.empty else pd.DataFrame()
live_flags = flags_df[_live_mask] if not flags_df.empty else pd.DataFrame()

# Split products by source
_hist_prod_mask = products_df["data_source"] == "documented_historical" if not products_df.empty else pd.Series(dtype=bool)
_live_prod_mask = products_df["data_source"].isin(["live_openfoodfacts", "live_kroger", "live_combined"]) if not products_df.empty else pd.Series(dtype=bool)


# =====================================================================
# SIDEBAR — filters apply to confirmed cases explorer only
# =====================================================================
with st.sidebar:
    st.markdown("## Filters")
    st.caption("Applies to the Explorer and Compare tabs.")

    # Source filter
    source_filter = st.selectbox(
        "Evidence Source",
        ["All Confirmed", "Documented Historical Only", "Confirmed Live Only"],
    )

    # Category filter — from all flags
    all_categories = sorted(flags_df["category"].dropna().unique()) if not flags_df.empty else []
    selected_category = st.selectbox("Category", ["All Categories"] + all_categories)

    # Brand filter
    if not flags_df.empty:
        _brand_pool = (
            flags_df[flags_df["category"] == selected_category]["brand"].dropna().unique()
            if selected_category != "All Categories"
            else flags_df["brand"].dropna().unique()
        )
        available_brands = sorted(_brand_pool)
    else:
        available_brands = []
    selected_brand = st.selectbox("Brand", ["All Brands"] + available_brands)

    selected_severity = st.selectbox("Severity", ["ALL", "HIGH", "MEDIUM", "LOW"])

    st.markdown("---")
    date_range = st.select_slider(
        "Time Range",
        options=["30 days", "90 days", "1 year", "2 years", "All time"],
        value="All time",
    )

    st.markdown("---")
    if st.button("Refresh Data", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.caption(
        "Data updates when the 30-minute scan window expires, "
        "or when you click Refresh Data."
    )

    st.markdown("---")
    st.markdown("**Quick Stats**")
    _sc1, _sc2 = st.columns(2)
    _sc1.metric("Products", f"{len(products_df):,}")
    _sc2.metric("Confirmed", f"{len(flags_df):,}")


# =====================================================================
# APPLY FILTERS → filtered_flags (used in Explorer/Compare/DeepDive)
# =====================================================================
filtered = flags_df.copy()
if not filtered.empty:
    if source_filter == "Documented Historical Only":
        filtered = filtered[filtered["flag_source"] == "documented_historical"]
    elif source_filter == "Confirmed Live Only":
        filtered = filtered[filtered["flag_source"] == "live_detected"]

    if selected_category != "All Categories":
        filtered = filtered[filtered["category"] == selected_category]
    if selected_brand != "All Brands":
        filtered = filtered[filtered["brand"] == selected_brand]
    if selected_severity != "ALL":
        filtered = filtered[filtered["severity"] == selected_severity]

    if "detected_at" in filtered.columns and date_range != "All time":
        _days_map = {"30 days": 30, "90 days": 90, "1 year": 365, "2 years": 730}
        filtered["detected_at"] = pd.to_datetime(filtered["detected_at"], utc=True, errors="coerce")
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=_days_map[date_range])
        filtered = filtered[filtered["detected_at"] >= cutoff]


# =====================================================================
# HEADER
# =====================================================================
_now_utc = datetime.now(timezone.utc)
_n_hist = len(hist_flags)
_n_live = len(live_flags)
_n_total = len(flags_df)
_n_prods = len(products_df)

_scan_at_str = _scan_result.get("scanned_at", "")
_scan_age_min = None
if _scan_at_str:
    try:
        _scan_dt = datetime.fromisoformat(_scan_at_str.replace("Z", "+00:00"))
        _scan_age_min = int((_now_utc - _scan_dt).total_seconds() / 60)
    except Exception:
        pass

_scan_age_label = (
    f"last scan {_scan_age_min}m ago"
    if _scan_age_min is not None
    else "scan time unknown"
)

st.markdown(f"""
<div class="main-header">
    <h1>📉 Shrinkflation Detector</h1>
    <p>
        {_n_prods:,} products tracked &middot;
        {_n_total:,} confirmed shrinkflation cases &middot;
        {_scan_age_label} &middot;
        {_now_utc.strftime('%b %d, %Y %H:%M UTC')}
    </p>
    <p style="margin-top:6px">
        <span class="source-hist">Documented Historical</span>
        <span class="source-live">Confirmed Live</span>
        <span class="source-combined">Combined</span>
    </p>
</div>
""", unsafe_allow_html=True)

# =====================================================================
# TOP METRIC ROW — all clearly labeled by source
# =====================================================================
_col_hist_p, _col_live_p, _col_funnel, _col_hist_f, _col_live_f, _col_total_f = st.columns(6)

_hist_prod_count = int(_hist_prod_mask.sum()) if not products_df.empty else 0
_live_prod_count = int(_live_prod_mask.sum()) if not products_df.empty else 0

_col_hist_p.metric("Historical Products", f"{_hist_prod_count:,}", help="Products loaded from documented research (BLS, Consumer Reports, etc.)")
_col_live_p.metric("Live Products Tracked", f"{_live_prod_count:,}", help="Products currently tracked via Open Food Facts and Kroger APIs")
_col_funnel.metric("With ≥2 Snapshots", f"{funnel['with_2_snaps']:,}", help="Live products with at least 2 real observations — required for detection")
_col_hist_f.metric("Historical Cases", f"{_n_hist:,}", help="Confirmed from published research (observation_type=documented_reference)")
_col_live_f.metric("Confirmed Live Cases", f"{_n_live:,}", help="Detected by live API tracking with strict price+size evidence")
_col_total_f.metric("Total Confirmed", f"{_n_total:,}", help="Historical + confirmed live (combined)")

st.markdown("")

# =====================================================================
# SECOND METRIC ROW — derived insights (all confirmed cases combined)
# =====================================================================
m1, m2, m3, m4 = st.columns(4)

if not flags_df.empty and "price_per_unit_increase_pct" in flags_df.columns:
    _ppu_series = flags_df[flags_df["has_price_evidence"] == True]["price_per_unit_increase_pct"].dropna()
    _avg_ppu = _ppu_series.mean() if len(_ppu_series) > 0 else None
else:
    _avg_ppu = None

if _avg_ppu is not None:
    m1.metric("Avg Hidden Increase (PPU)", f"+{_avg_ppu:.1f}%",
              help="Average price-per-unit increase across all confirmed cases with price evidence")
else:
    m1.metric("Avg Hidden Increase (PPU)", "N/A")

if not flags_df.empty and "category" in flags_df.columns:
    _worst_cat = flags_df["category"].value_counts().idxmax()
    m2.metric("Most-Flagged Category", _worst_cat.title())
else:
    m2.metric("Most-Flagged Category", "N/A")

if not flags_df.empty and "brand" in flags_df.columns:
    _worst_brand = flags_df["brand"].value_counts().idxmax()
    m3.metric("Most-Flagged Brand", _worst_brand)
else:
    m3.metric("Most-Flagged Brand", "N/A")

m4.metric("Live Detection Funnel", f"{funnel['enrichable']:,} eligible",
          help="Live products with at least one snapshot containing both confirmed size and price")

st.markdown("---")

# =====================================================================
# MAIN TABS
# =====================================================================
(tab_overview, tab_live_tracking, tab_compare,
 tab_deepdive, tab_explorer, tab_ai, tab_methodology) = st.tabs([
    "Overview",
    "Live Tracking",
    "Compare",
    "Deep Dive",
    "Explorer",
    "AI Insights",
    "Methodology",
])


# =================================================================
# TAB 1: OVERVIEW — historical powers this; live shown separately
# =================================================================
with tab_overview:

    # ---- Row 1: Confirmed cases split by source ----
    st.markdown("### Confirmed Shrinkflation Cases")
    st.caption(
        "All documented historical cases are confirmed from published research. "
        "Live confirmed cases require ≥30 days between two enriched observations "
        "with a verified PPU increase — so early-stage deployment shows few or zero."
    )

    ov_c1, ov_c2 = st.columns(2)

    with ov_c1:
        st.markdown(
            '<span class="source-hist">Documented Historical</span> '
            "— Cases by Category",
            unsafe_allow_html=True,
        )
        if not hist_flags.empty and "category" in hist_flags.columns:
            _cat_hist = (
                hist_flags.groupby("category").size()
                .reset_index(name="cases")
                .sort_values("cases", ascending=True)
            )
            fig_hist_cat = px.bar(
                _cat_hist, x="cases", y="category", orientation="h",
                color="cases", color_continuous_scale=["#e0e7ff", "#6366f1", "#4338ca"],
                labels={"cases": "Confirmed Cases", "category": ""},
                text="cases",
            )
            fig_hist_cat.update_traces(
                textposition="outside",
                textfont=dict(size=12, color="#1e293b"),
                hovertemplate="<b>%{y}</b><br>Cases: %{x}<extra></extra>",
            )
            fig_hist_cat.update_layout(**CHART_LAYOUT, height=380)
            st.plotly_chart(fig_hist_cat, use_container_width=True, config=CHART_CONFIG, theme=None)
        else:
            st.info("Historical data not loaded yet.")

    with ov_c2:
        st.markdown(
            '<span class="source-live">Confirmed Live</span> '
            "— Cases by Category",
            unsafe_allow_html=True,
        )
        if not live_flags.empty and "category" in live_flags.columns:
            _cat_live = (
                live_flags.groupby("category").size()
                .reset_index(name="cases")
                .sort_values("cases", ascending=True)
            )
            fig_live_cat = px.bar(
                _cat_live, x="cases", y="category", orientation="h",
                color="cases", color_continuous_scale=["#dcfce7", "#22c55e", "#15803d"],
                labels={"cases": "Confirmed Cases", "category": ""},
                text="cases",
            )
            fig_live_cat.update_traces(
                textposition="outside",
                textfont=dict(size=12, color="#1e293b"),
                hovertemplate="<b>%{y}</b><br>Cases: %{x}<extra></extra>",
            )
            fig_live_cat.update_layout(**CHART_LAYOUT, height=380)
            st.plotly_chart(fig_live_cat, use_container_width=True, config=CHART_CONFIG, theme=None)
        else:
            st.markdown("""
            <div class="funnel-card">
                <div class="funnel-num">0</div>
                <div class="funnel-step">No confirmed live cases yet.</div>
                <br>
                <div class="funnel-step">
                    Live detection requires two enriched observations at least 30 days apart,
                    each with a confirmed price AND size, plus a price-per-unit increase.
                    As the tracking panel builds history, confirmed cases will appear here.
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # ---- Row 2: Detection timeline split by source ----
    st.markdown("### Detection Timeline")
    st.caption(
        "Historical cases show when the documented shrinkflation occurred "
        "(year-level approximation). Live cases show the exact API detection date."
    )

    if not flags_df.empty and "detected_at" in flags_df.columns:
        _timeline_df = flags_df.copy()
        _timeline_df["detected_at"] = pd.to_datetime(_timeline_df["detected_at"], utc=True, errors="coerce")
        _timeline_df = _timeline_df.dropna(subset=["detected_at"])
        _timeline_df["year"] = _timeline_df["detected_at"].dt.year
        _timeline_df["source_label"] = _timeline_df["flag_source"].map({
            "documented_historical": "Documented Historical",
            "live_detected": "Confirmed Live",
        }).fillna("Unknown")

        _yearly = (
            _timeline_df.groupby(["year", "source_label"])
            .size().reset_index(name="count")
        )

        if not _yearly.empty:
            fig_timeline = px.bar(
                _yearly, x="year", y="count", color="source_label",
                color_discrete_map={
                    "Documented Historical": "#6366f1",
                    "Confirmed Live": "#22c55e",
                },
                labels={"year": "Year", "count": "Cases", "source_label": "Source"},
                barmode="stack",
            )
            fig_timeline.update_traces(
                hovertemplate="<b>%{x}</b><br>Cases: %{y}<extra></extra>",
            )
            fig_timeline.update_layout(
                **CHART_LAYOUT, height=320,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=12)),
            )
            fig_timeline.update_xaxes(type="linear", tickmode="linear", dtick=1)
            st.plotly_chart(fig_timeline, use_container_width=True, config=CHART_CONFIG, theme=None)
    else:
        st.info("No flag data available for timeline.")

    st.divider()

    # ---- Row 3: Top brands + severity breakdown (all confirmed) ----
    br_c1, br_c2 = st.columns([3, 2])

    with br_c1:
        st.markdown(
            "### Top 10 Most-Flagged Brands "
            '<span class="source-combined">All Confirmed</span>',
            unsafe_allow_html=True,
        )
        if not flags_df.empty:
            _brand_agg = (
                flags_df.groupby("brand")
                .agg(
                    cases=("id", "count"),
                    avg_ppu=("price_per_unit_increase_pct", "mean"),
                )
                .reset_index()
                .sort_values("cases", ascending=True)
                .tail(10)
            )
            fig_brands = px.bar(
                _brand_agg, x="cases", y="brand", orientation="h",
                color="cases", color_continuous_scale=["#dbeafe", "#3b82f6", "#1e40af"],
                labels={"cases": "Confirmed Cases", "brand": ""},
                text="cases",
            )
            fig_brands.update_traces(
                textposition="outside",
                textfont=dict(size=12, color="#1e293b"),
                hovertemplate="<b>%{y}</b><br>Cases: %{x}<extra></extra>",
            )
            fig_brands.update_layout(**CHART_LAYOUT, height=400)
            st.plotly_chart(fig_brands, use_container_width=True, config=CHART_CONFIG, theme=None)
        else:
            st.info("No flag data loaded.")

    with br_c2:
        st.markdown("### Severity Breakdown")
        if not flags_df.empty and "severity" in flags_df.columns:
            sev_counts = flags_df["severity"].value_counts().reset_index()
            sev_counts.columns = ["severity", "count"]
            fig_donut = px.pie(
                sev_counts, values="count", names="severity",
                color="severity", color_discrete_map=SEVERITY_COLORS,
                hole=0.55,
            )
            fig_donut.update_traces(
                textinfo="percent+value", textfont_size=12,
                hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
            )
            fig_donut.update_layout(
                height=380, margin=dict(l=10, r=10, t=10, b=10),
                plot_bgcolor="white", paper_bgcolor="white",
                font=dict(color="#1e293b"),
                showlegend=True, legend=dict(orientation="h", y=-0.1, font=dict(size=12)),
            )
            st.plotly_chart(fig_donut, use_container_width=True, config=CHART_CONFIG, theme=None)
        else:
            st.info("No severity data.")

    st.divider()

    # ---- Row 4: Avg PPU increase by category ----
    st.markdown(
        "### Avg Price-Per-Unit Increase by Category "
        '<span class="source-combined">All Confirmed (where price evidence exists)</span>',
        unsafe_allow_html=True,
    )
    _ppu_flags = flags_df[flags_df["has_price_evidence"] == True] if not flags_df.empty else pd.DataFrame()
    if not _ppu_flags.empty and "price_per_unit_increase_pct" in _ppu_flags.columns:
        _cat_ppu = (
            _ppu_flags.groupby("category")["price_per_unit_increase_pct"]
            .mean().round(1).sort_values(ascending=True)
            .reset_index()
        )
        fig_ppu = px.bar(
            _cat_ppu, x="price_per_unit_increase_pct", y="category", orientation="h",
            color="price_per_unit_increase_pct", color_continuous_scale=["#fee2e2", "#ef4444", "#991b1b"],
            labels={"price_per_unit_increase_pct": "Avg PPU Increase (%)", "category": ""},
            text="price_per_unit_increase_pct",
        )
        fig_ppu.update_traces(
            texttemplate="+%{text:.1f}%", textposition="outside",
            textfont=dict(size=12, color="#1e293b"),
            hovertemplate="<b>%{y}</b><br>Avg PPU Increase: +%{x:.1f}%<extra></extra>",
        )
        fig_ppu.update_layout(**CHART_LAYOUT, height=380)
        st.plotly_chart(fig_ppu, use_container_width=True, config=CHART_CONFIG, theme=None)
    else:
        st.info("Price-per-unit data not yet available.")


# =================================================================
# TAB 2: LIVE TRACKING — pipeline status, funnel, live flags only
# =================================================================
with tab_live_tracking:
    st.markdown("### Live Tracking Pipeline")
    st.caption(
        "The system continuously fetches product data from Open Food Facts (sizes) "
        "and Kroger (prices). Confirmed shrinkflation requires strict evidence: "
        "two observations ≥30 days apart, each with confirmed size AND price, "
        "showing a price-per-unit increase."
    )

    # ---- Funnel ----
    st.markdown("#### Evidence Funnel")
    f1, f2, f3, f4 = st.columns(4)

    f1.markdown(f"""
    <div class="funnel-card">
        <div class="funnel-step">Live Products Tracked</div>
        <div class="funnel-num">{funnel['live_products']:,}</div>
        <div class="funnel-step">Fetched from Open Food Facts + Kroger APIs</div>
    </div>
    """, unsafe_allow_html=True)

    f2.markdown(f"""
    <div class="funnel-card">
        <div class="funnel-step">With ≥2 Snapshots</div>
        <div class="funnel-num">{funnel['with_2_snaps']:,}</div>
        <div class="funnel-step">Need at least 2 real observations to compare</div>
    </div>
    """, unsafe_allow_html=True)

    f3.markdown(f"""
    <div class="funnel-card">
        <div class="funnel-step">With Price + Size Evidence</div>
        <div class="funnel-num">{funnel['enrichable']:,}</div>
        <div class="funnel-step">Have at least one snapshot with both confirmed size AND price</div>
    </div>
    """, unsafe_allow_html=True)

    f4.markdown(f"""
    <div class="funnel-card">
        <div class="funnel-step">Confirmed Live Cases</div>
        <div class="funnel-num">{funnel['confirmed_live']:,}</div>
        <div class="funnel-step">Met all detection criteria across ≥30-day gap</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="methodology-block">
        <strong>Why are confirmed live cases low?</strong><br>
        Live detection uses the strictest possible standard: two fully-enriched observations
        (confirmed size AND price, same product, compatible units) must exist at least 30 days apart,
        and the price-per-unit must have strictly increased. Early in deployment, most products
        haven't yet accumulated enough observation history. This is expected — and intentional.
        False positives cause real harm; false negatives do not.
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ---- Last ingestion run ----
    st.markdown("#### Last Pipeline Run")
    last_run = funnel.get("last_run")
    if last_run:
        lr_c1, lr_c2, lr_c3, lr_c4 = st.columns(4)
        _started = last_run.get("started_at", "")
        _finished = last_run.get("finished_at", "")
        _status = last_run.get("status", "unknown")
        _source = last_run.get("source", "unknown")
        _phase = last_run.get("phase", "unknown")

        lr_c1.metric("Source", f"{_source} / {_phase}")
        lr_c2.metric("Status", _status.upper())
        lr_c3.metric("Products Added", last_run.get("products_added", 0))
        lr_c4.metric("Snapshots Added", last_run.get("snapshots_added", 0))

        if isinstance(_started, datetime):
            st.caption(f"Started: {_started.strftime('%Y-%m-%d %H:%M UTC')}")
        elif _started:
            st.caption(f"Started: {str(_started)[:19]} UTC")
    else:
        st.info("No ingestion runs recorded yet. The pipeline runs on first page load.")

    st.divider()

    # ---- Scan result details ----
    st.markdown("#### Current Scan (this session)")
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("New Products (OFF)", _scan_result.get("new_products", 0))
    sc2.metric("New Snapshots (OFF)", _scan_result.get("new_snapshots", 0))
    sc3.metric("Kroger Snapshots", _scan_result.get("kroger_snapshots", 0))
    sc4.metric("New Flags Detected", _scan_result.get("new_flags", 0))

    if _scan_result.get("off_error"):
        st.warning(f"Open Food Facts error: {_scan_result['off_error']}")
    if _scan_result.get("kroger_error"):
        st.warning(f"Kroger error: {_scan_result['kroger_error']}")
    if _scan_result.get("detection_error"):
        st.warning(f"Detector error: {_scan_result['detection_error']}")

    _panel = _scan_result.get("panel_size", 0)
    _phase_label = _scan_result.get("phase", "unknown")
    if _panel:
        st.caption(
            f"Panel size: {_panel:,} live products | Phase: {_phase_label} "
            "(fill = building panel; track = scanning for changes)"
        )

    st.divider()

    # ---- Confirmed live cases detail ----
    st.markdown(
        "#### Confirmed Live Detections "
        '<span class="source-live">live_detected only</span>',
        unsafe_allow_html=True,
    )

    if not live_flags.empty:
        _live_display = live_flags[[
            "product", "brand", "category",
            "old_size", "new_size", "size_unit",
            "old_price", "new_price", "price_per_unit_increase_pct",
            "severity", "detected_at",
        ]].copy()
        _live_display["old_price"] = _live_display["old_price"].apply(
            lambda x: f"${x:.2f}" if pd.notna(x) else "N/A"
        )
        _live_display["new_price"] = _live_display["new_price"].apply(
            lambda x: f"${x:.2f}" if pd.notna(x) else "N/A"
        )
        _live_display["price_per_unit_increase_pct"] = _live_display["price_per_unit_increase_pct"].apply(
            lambda x: f"+{x:.1f}%" if pd.notna(x) else "N/A"
        )
        _live_display.columns = [
            "Product", "Brand", "Category",
            "Old Size", "New Size", "Unit",
            "Old Price", "New Price", "PPU Increase",
            "Severity", "Detected At",
        ]
        st.dataframe(_live_display, use_container_width=True, hide_index=True)
    else:
        st.markdown("""
        <div class="funnel-card">
            <div class="funnel-num">0</div>
            <div class="funnel-step">No confirmed live detections yet.</div>
            <br>
            <div class="funnel-step">
                This is expected. The live detector applies strict evidence rules:
                two enriched observations (size + price each) ≥30 days apart,
                same unit family, price-per-unit strictly higher.
                As the product panel accumulates history, confirmed cases will appear here.
            </div>
        </div>
        """, unsafe_allow_html=True)


# =================================================================
# TAB 3: COMPARE — side-by-side, operates on filtered data
# =================================================================
with tab_compare:
    st.subheader("Side-by-Side Comparison")
    st.caption(
        "Comparisons use whichever source filter you selected in the sidebar. "
        "Note: comparing confirmed live vs historical requires selecting 'All Confirmed'."
    )

    if filtered.empty:
        st.info("No confirmed cases match the current filter combination.")
    else:
        st.markdown("#### Brand vs Brand")
        comp_brands = sorted(filtered["brand"].dropna().unique())
        cc1, cc2 = st.columns(2)
        with cc1:
            brand_a = st.selectbox("Brand A", comp_brands, index=0, key="brand_a")
        with cc2:
            brand_b = st.selectbox(
                "Brand B", comp_brands,
                index=min(1, len(comp_brands) - 1), key="brand_b",
            )

        if brand_a and brand_b:
            data_a = filtered[filtered["brand"] == brand_a]
            data_b = filtered[filtered["brand"] == brand_b]

            c1, c2 = st.columns(2)
            for col, bdata, bname in [(c1, data_a, brand_a), (c2, data_b, brand_b)]:
                with col:
                    st.markdown(f"### {bname}")
                    bm1, bm2, bm3 = st.columns(3)
                    bm1.metric("Flags", len(bdata))
                    _avg = bdata["price_per_unit_increase_pct"].mean() if not bdata.empty else 0
                    bm2.metric("Avg PPU Inc.", f"+{_avg:.1f}%" if _avg else "N/A")
                    bm3.metric("HIGH", int((bdata["severity"] == "HIGH").sum()) if not bdata.empty else 0)

                    if not bdata.empty:
                        st.markdown("**Flagged Products:**")
                        _rankable = bdata.dropna(subset=["price_per_unit_increase_pct"])
                        _top = _rankable.nlargest(5, "price_per_unit_increase_pct")[
                            ["product", "price_per_unit_increase_pct", "severity"]
                        ] if not _rankable.empty else pd.DataFrame()
                        for _, row in _top.iterrows():
                            sev_class = f"severity-{str(row['severity']).lower()}"
                            _inc = row["price_per_unit_increase_pct"]
                            _inc_str = f"+{_inc:.1f}%" if pd.notna(_inc) else "N/A"
                            st.markdown(
                                f"- {row['product']} — {_inc_str} "
                                f"<span class='{sev_class}'>{row['severity']}</span>",
                                unsafe_allow_html=True,
                            )

            st.divider()
            _avg_a = data_a["price_per_unit_increase_pct"].mean() if not data_a.empty else 0
            _avg_b = data_b["price_per_unit_increase_pct"].mean() if not data_b.empty else 0
            if _avg_a > _avg_b:
                worse, better, diff = brand_a, brand_b, abs(_avg_a - _avg_b)
            else:
                worse, better, diff = brand_b, brand_a, abs(_avg_b - _avg_a)
            st.markdown(f"""
            <div class="compare-card">
                <h3>Verdict</h3>
                <p><strong>{worse}</strong> has a <strong>+{diff:.1f}%</strong> higher
                average hidden price increase than <strong>{better}</strong>
                (measured as price-per-unit change).</p>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # Category vs Category
        st.markdown("#### Category vs Category")
        all_cats = sorted(filtered["category"].dropna().unique())
        if len(all_cats) >= 2:
            ct1, ct2 = st.columns(2)
            with ct1:
                cat_a = st.selectbox("Category A", all_cats, index=0, key="cat_a")
            with ct2:
                cat_b = st.selectbox("Category B", all_cats, index=1, key="cat_b")

            d_a = filtered[filtered["category"] == cat_a]
            d_b = filtered[filtered["category"] == cat_b]

            compare_df = pd.DataFrame({
                "Metric": [
                    "Total Confirmed Cases", "Avg PPU Increase",
                    "HIGH Severity", "Max PPU Increase", "Brands Affected",
                ],
                cat_a.title(): [
                    str(len(d_a)),
                    f"+{d_a['price_per_unit_increase_pct'].mean():.1f}%" if not d_a.empty and d_a["price_per_unit_increase_pct"].notna().any() else "N/A",
                    str(int((d_a["severity"] == "HIGH").sum())) if not d_a.empty else "0",
                    f"+{d_a['price_per_unit_increase_pct'].max():.1f}%" if not d_a.empty and d_a["price_per_unit_increase_pct"].notna().any() else "N/A",
                    str(d_a["brand"].nunique()) if not d_a.empty else "0",
                ],
                cat_b.title(): [
                    str(len(d_b)),
                    f"+{d_b['price_per_unit_increase_pct'].mean():.1f}%" if not d_b.empty and d_b["price_per_unit_increase_pct"].notna().any() else "N/A",
                    str(int((d_b["severity"] == "HIGH").sum())) if not d_b.empty else "0",
                    f"+{d_b['price_per_unit_increase_pct'].max():.1f}%" if not d_b.empty and d_b["price_per_unit_increase_pct"].notna().any() else "N/A",
                    str(d_b["brand"].nunique()) if not d_b.empty else "0",
                ],
            })
            st.dataframe(compare_df, use_container_width=True, hide_index=True)
        else:
            st.info("Need at least 2 categories in the filtered data to compare.")


# =================================================================
# TAB 4: DEEP DIVE — brand + product timeline
# =================================================================
with tab_deepdive:
    st.subheader("Brand Deep Dive")
    st.caption("Uses all confirmed cases regardless of sidebar source filter.")

    if not flags_df.empty:
        brand_list = sorted(flags_df["brand"].dropna().unique())
        dive_brand = st.selectbox("Choose brand", brand_list, key="brand_dive")

        if dive_brand:
            brand_data = flags_df[flags_df["brand"] == dive_brand]

            bc1, bc2, bc3, bc4 = st.columns(4)
            bc1.metric("Flagged Products", len(brand_data))
            _bavg = brand_data["price_per_unit_increase_pct"].mean()
            bc2.metric("Avg PPU Increase", f"+{_bavg:.1f}%" if pd.notna(_bavg) else "N/A")
            _high_pct = (brand_data["severity"] == "HIGH").sum() / max(len(brand_data), 1) * 100
            bc3.metric("HIGH Severity", f"{_high_pct:.0f}%")
            bc4.metric("Categories", brand_data["category"].nunique())

            _brand_plot = brand_data.dropna(subset=["price_per_unit_increase_pct"])
            if not _brand_plot.empty:
                fig_brand = px.bar(
                    _brand_plot.sort_values("price_per_unit_increase_pct", ascending=False).head(20),
                    x="price_per_unit_increase_pct", y="product", orientation="h",
                    color="severity", color_discrete_map=SEVERITY_COLORS,
                    labels={"price_per_unit_increase_pct": "PPU Increase (%)", "product": ""},
                    text="price_per_unit_increase_pct",
                )
                fig_brand.update_traces(
                    texttemplate="+%{text:.1f}%", textposition="outside",
                    textfont=dict(size=11, color="#1e293b"),
                    hovertemplate="<b>%{y}</b><br>PPU Increase: +%{x:.1f}%<extra></extra>",
                )
                fig_brand.update_layout(
                    **CHART_LAYOUT,
                    height=max(300, len(_brand_plot.head(20)) * 30),
                )
                fig_brand.update_yaxes(categoryorder="total ascending")
                st.plotly_chart(fig_brand, use_container_width=True, config=CHART_CONFIG, theme=None)
            else:
                st.info("No price-per-unit data available for this brand's flags.")

            if "old_size" in brand_data.columns and "new_size" in brand_data.columns:
                _bdc = brand_data.dropna(subset=["old_size", "new_size"]).copy()
                if not _bdc.empty:
                    _bdc["size_change_pct"] = (_bdc["new_size"] - _bdc["old_size"]) / _bdc["old_size"] * 100
                    fig_hist = px.histogram(
                        _bdc, x="size_change_pct", nbins=15,
                        color="severity", color_discrete_map=SEVERITY_COLORS,
                        labels={"size_change_pct": "Size Change (%)"},
                        title=f"Size Change Distribution — {dive_brand}",
                    )
                    fig_hist.update_layout(**CHART_LAYOUT, height=280, barmode="stack")
                    st.plotly_chart(fig_hist, use_container_width=True, config=CHART_CONFIG, theme=None)
    else:
        st.info("No confirmed case data loaded yet.")

    st.divider()

    # ---- Product Timeline ----
    st.subheader("Product Snapshot Timeline")
    st.caption(
        "Shows the full observation history for a product. "
        "Historical products use year-level reference dates (not real observation times)."
    )

    if not products_df.empty:
        product_names = sorted(products_df["name"].dropna().unique())
        selected_product = st.selectbox(
            "Search & select product",
            [""] + list(product_names),
            key="product_timeline",
        )

        if selected_product:
            from agent.tools import get_product_history
            history = get_product_history(selected_product)

            if isinstance(history, dict) and "error" in history:
                st.warning(history["error"])
            elif isinstance(history, dict) and history.get("snapshots"):
                _src = history.get("data_source", "unknown")
                _src_badge = (
                    '<span class="source-hist">Documented Historical</span>'
                    if _src == "documented_historical"
                    else '<span class="source-live">Live Tracked</span>'
                )
                st.markdown(
                    f"**{history['product']}** by {history['brand']} "
                    f"({history['category']}) {_src_badge}",
                    unsafe_allow_html=True,
                )

                snap_df = pd.DataFrame(history["snapshots"])
                snap_df["date"] = pd.to_datetime(snap_df["date"], errors="coerce")
                snap_df = snap_df.dropna(subset=["date"]).sort_values("date")

                fig_combo = make_subplots(specs=[[{"secondary_y": True}]])

                if "size_value" in snap_df.columns and snap_df["size_value"].notna().any():
                    fig_combo.add_trace(
                        go.Scatter(
                            x=snap_df["date"], y=snap_df["size_value"],
                            mode="lines+markers", name="Size",
                            line=dict(color="#3498db", width=3),
                            marker=dict(size=8),
                        ),
                        secondary_y=False,
                    )

                if "price" in snap_df.columns:
                    snap_df["price_num"] = snap_df["price"].apply(
                        lambda x: float(str(x).replace("$", "")) if x and str(x).startswith("$") else None
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
                    title=f"Size & Price History — {history['product']}",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02),
                )
                fig_combo.update_yaxes(title_text="Size", secondary_y=False)
                fig_combo.update_yaxes(title_text="Price ($)", secondary_y=True)
                st.plotly_chart(fig_combo, use_container_width=True, config=CHART_CONFIG, theme=None)

                events = history.get("confirmed_events", [])
                if events:
                    st.markdown("**Confirmed Shrinkflation Events:**")
                    for evt in events:
                        sev = evt.get("severity", "")
                        sev_class = f"severity-{sev.lower()}" if sev else ""
                        _src_evt = evt.get("flag_source", "")
                        _src_label = (
                            "Documented Historical"
                            if _src_evt == "documented_historical"
                            else "Confirmed Live"
                        )
                        _ppu = evt.get("ppu_increase_pct", "N/A")
                        st.markdown(
                            f"- **{evt.get('date', 'N/A')}**: "
                            f"{evt.get('old_size')} → {evt.get('new_size')} {evt.get('size_unit', '')} "
                            f"({_ppu} PPU increase) "
                            f"<span class='{sev_class}'>{sev}</span> "
                            f"— {_src_label}",
                            unsafe_allow_html=True,
                        )
                else:
                    st.success("No confirmed shrinkflation events for this product.")
            else:
                st.info("No history found for this product.")
    else:
        st.info("Product data not loaded.")


# =================================================================
# TAB 5: EXPLORER — scatter, heatmap, PPU calculator
# =================================================================
with tab_explorer:
    st.subheader("Data Explorer")
    st.caption("Operates on the filtered dataset from the sidebar.")

    if filtered.empty:
        st.info("No confirmed cases match the current filter combination. Adjust the sidebar filters.")
    else:
        # Scatter: size change vs PPU increase
        st.markdown("### Size Reduction vs Price-Per-Unit Increase")
        st.caption("Each point = one confirmed case. Shows that size can shrink even when shelf price stays flat.")

        _scatter = filtered.dropna(subset=["old_size", "new_size", "price_per_unit_increase_pct"]).copy()
        if not _scatter.empty:
            _scatter["size_change_pct"] = (
                (_scatter["new_size"] - _scatter["old_size"]) / _scatter["old_size"] * 100
            )
            _scatter["size_marker"] = _scatter["severity"].map(
                {"HIGH": 14, "MEDIUM": 10, "LOW": 7}
            ).fillna(7)
            _scatter["source_label"] = _scatter["flag_source"].map({
                "documented_historical": "Documented Historical",
                "live_detected": "Confirmed Live",
            }).fillna("Unknown")

            fig_scatter = px.scatter(
                _scatter,
                x="size_change_pct", y="price_per_unit_increase_pct",
                color="source_label",
                color_discrete_map={
                    "Documented Historical": "#6366f1",
                    "Confirmed Live": "#22c55e",
                },
                size="size_marker",
                hover_data=["product", "brand", "severity"],
                labels={
                    "size_change_pct": "Size Change (%)",
                    "price_per_unit_increase_pct": "PPU Increase (%)",
                    "source_label": "Source",
                },
                opacity=0.75,
            )
            fig_scatter.add_hline(y=0, line_dash="dash", line_color="#cbd5e1", opacity=0.7)
            fig_scatter.add_vline(x=0, line_dash="dash", line_color="#cbd5e1", opacity=0.7)
            fig_scatter.update_layout(
                **CHART_LAYOUT, height=420,
                legend=dict(orientation="h", yanchor="bottom", y=-0.3, font=dict(size=12)),
            )
            st.plotly_chart(fig_scatter, use_container_width=True, config=CHART_CONFIG, theme=None)
        else:
            st.info("Not enough data for scatter plot with current filters.")

        st.divider()

        # Heatmap: brand × category
        st.markdown("### Brand × Category Heatmap")
        st.caption("Average PPU increase. Darker = higher hidden price increase.")

        _top_brands = filtered["brand"].value_counts().head(12).index.tolist()
        _heat_df = filtered[filtered["brand"].isin(_top_brands)]
        _heat_df = _heat_df.dropna(subset=["price_per_unit_increase_pct"])

        if not _heat_df.empty and _heat_df["category"].nunique() > 1:
            _pivot = _heat_df.pivot_table(
                values="price_per_unit_increase_pct",
                index="brand", columns="category",
                aggfunc="mean",
            ).round(1)
            fig_heat = px.imshow(
                _pivot, color_continuous_scale="RdYlGn_r",
                labels={"color": "Avg PPU Increase %"},
                text_auto=True, aspect="auto",
            )
            fig_heat.update_layout(
                height=420, margin=dict(l=20, r=20, t=30, b=10),
                plot_bgcolor="white", paper_bgcolor="white",
                font=dict(size=12, color="#1e293b"),
            )
            st.plotly_chart(fig_heat, use_container_width=True, config=CHART_CONFIG, theme=None)
        else:
            st.info("Not enough brand/category combinations for heatmap with current filters.")

        st.divider()

        # PPU Calculator — standalone, no DB data
        st.markdown("### Price-Per-Unit Impact Calculator")
        st.caption(
            "Enter any product's old and new size/price to calculate whether "
            "a real hidden price increase occurred."
        )
        calc_c1, calc_c2 = st.columns(2)
        with calc_c1:
            old_sz = st.number_input("Original Size (oz)", value=16.0, step=0.5, min_value=0.1)
            old_pr = st.number_input("Original Price ($)", value=5.49, step=0.25, min_value=0.01)
        with calc_c2:
            new_sz = st.number_input("New Size (oz)", value=14.0, step=0.5, min_value=0.1)
            new_pr = st.number_input("New Price ($)", value=5.99, step=0.25, min_value=0.01)

        if st.button("Calculate Impact", type="primary"):
            old_ppu = old_pr / old_sz
            new_ppu = new_pr / new_sz
            real_inc = ((new_ppu - old_ppu) / old_ppu) * 100
            sz_chg = ((new_sz - old_sz) / old_sz) * 100

            r1, r2, r3 = st.columns(3)
            r1.metric("Size Change", f"{sz_chg:+.1f}%")
            r2.metric("Price/oz", f"${old_ppu:.3f} → ${new_ppu:.3f}")
            r3.metric("Real Increase (PPU)", f"{real_inc:+.1f}%")

            if real_inc > 20:
                st.error(f"HIGH shrinkflation — you're paying {real_inc:.1f}% more per unit.")
            elif real_inc > 8:
                st.warning(f"MEDIUM shrinkflation — {real_inc:.1f}% more per unit.")
            elif real_inc > 0:
                st.info(f"LOW shrinkflation — {real_inc:.1f}% more per unit.")
            else:
                st.success(f"No hidden increase — paying {abs(real_inc):.1f}% less per unit.")

            monthly = st.slider("How many do you buy per month?", 1, 20, 4)
            annual_extra = (new_ppu - old_ppu) * new_sz * monthly * 12
            if annual_extra > 0:
                st.markdown(f"**Annual Impact:** Extra **${annual_extra:.2f}/year** on this product.")

    st.divider()

    # Full data table
    st.markdown("### Confirmed Cases Table")
    if not filtered.empty:
        search = st.text_input("Search by product or brand", "", key="table_search")
        display = filtered.copy()
        if search:
            mask = (
                display["product"].str.contains(search, case=False, na=False)
                | display["brand"].str.contains(search, case=False, na=False)
            )
            display = display[mask]

        _show_cols = [
            "flag_source", "product", "brand", "category",
            "old_size", "new_size", "size_unit",
            "old_price", "new_price", "price_per_unit_increase_pct",
            "severity", "detected_at",
        ]
        existing = [c for c in _show_cols if c in display.columns]
        table = display[existing].copy()

        if "old_price" in table.columns:
            table["old_price"] = table["old_price"].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
        if "new_price" in table.columns:
            table["new_price"] = table["new_price"].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
        if "price_per_unit_increase_pct" in table.columns:
            table["price_per_unit_increase_pct"] = table["price_per_unit_increase_pct"].apply(
                lambda x: f"+{x:.1f}%" if pd.notna(x) else "N/A"
            )

        _ts1, _ts2, _ts3 = st.columns(3)
        _ts1.metric("Showing", f"{len(table):,}")
        _ppu_col = display["price_per_unit_increase_pct"].dropna()
        if not _ppu_col.empty:
            _ts2.metric("Avg PPU Increase", f"+{_ppu_col.mean():.1f}%")
            _ts3.metric("Max PPU Increase", f"+{_ppu_col.max():.1f}%")

        def _color_sev(val):
            return {
                "HIGH": "background-color: #fadbd8; color: #922b21; font-weight: 600",
                "MEDIUM": "background-color: #fdebd0; color: #935116; font-weight: 600",
                "LOW": "background-color: #fef9e7; color: #7d6608; font-weight: 600",
            }.get(val, "")

        if not table.empty and "severity" in table.columns:
            st.dataframe(
                table.style.map(_color_sev, subset=["severity"]),
                use_container_width=True, height=450,
            )
        else:
            st.dataframe(table, use_container_width=True, height=450)

        dl1, dl2, _ = st.columns([1, 1, 2])
        with dl1:
            st.download_button(
                "Download CSV",
                data=display[existing].to_csv(index=False),
                file_name=f"shrinkflation_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )
        with dl2:
            st.download_button(
                "Download JSON",
                data=display[existing].to_json(orient="records", indent=2),
                file_name=f"shrinkflation_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
            )


# =================================================================
# TAB 6: AI INSIGHTS
# =================================================================
with tab_ai:
    st.subheader("AI-Powered Insights")
    st.caption(
        "The AI analyst queries the live database to surface findings. "
        "All numbers come from real data — no fabricated stats."
    )

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
        st.info("No AI insights generated yet.")

    if st.button("Generate New Insight", type="primary"):
        try:
            from agent.analyst import generate_daily_insight
            with st.spinner("AI analyzing data..."):
                new_insight = generate_daily_insight()
            st.success(new_insight)
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Could not generate insight: {e}. Set OPENAI_API_KEY in .env to enable AI features.")

    st.markdown("---")

    st.markdown("#### Ask the Data")
    user_q = st.text_input(
        "Your question",
        placeholder="Which category has the most confirmed cases? How many live products are tracked?",
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

    st.markdown("**Quick Questions:**")
    quick_qs = [
        "How many confirmed live cases are there and why might that be low?",
        "What brand has the most documented historical flags?",
        "Which category has the highest average price-per-unit increase?",
        "How many live products have at least 2 snapshots?",
    ]
    for q in quick_qs:
        if st.button(q, key=f"qq_{q}"):
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
# TAB 7: METHODOLOGY
# =================================================================
with tab_methodology:
    st.subheader("How This Works")

    st.markdown("""
    <div class="methodology-block">
        <strong>Two data sources, clearly separated</strong><br>
        This dashboard maintains a strict distinction between two evidence types.
        Documented historical cases come from published research and media investigations.
        Confirmed live cases are detected by automated API tracking with strict evidence rules.
        The two types are never combined into a single misleading count.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### Documented Historical Cases")
    st.markdown("""
    **Source:** Published research and investigations from:
    - U.S. Bureau of Labor Statistics (BLS) consumer price analysis
    - Consumer Reports product size tracking
    - mouseprint.org documented size reductions
    - FTC filings and consumer protection reports
    - Major media investigations (NPR, NYT, WSJ, CNN)

    **How they're stored:** Each case gets a "before" snapshot (start of documented year)
    and an "after" snapshot (mid-year approximation). Both are tagged
    `observation_type = documented_reference` to signal that timestamps are
    year-level approximations — not real observation times.

    **What they prove:** These are verified real-world events. The size reduction happened.
    Price evidence exists for many but not all cases.
    """)

    st.markdown("#### Confirmed Live Cases")
    st.markdown("""
    **Sources:**
    - **Open Food Facts API** — product sizes and barcodes (free, global database)
    - **Kroger API** — real US retail prices (developer account required)

    **Detection pipeline:**
    1. Fetch product data from Open Food Facts (sizes, barcodes)
    2. Match products to Kroger listings to obtain real shelf prices
    3. Build "enriched observations" — snapshots with BOTH confirmed size AND price
    4. Apply temporal pairing: if a size snapshot and price snapshot arrive within 24 hours
       of each other, they can be combined into one enriched observation
    5. If two size candidates exist in the same 24-hour window, the pairing is **rejected**
       (ambiguous — cannot determine which size was current)
    6. Compare pairs of enriched observations at least **30 days apart**
    7. Confirm: size decrease ≥2%, price-per-unit strictly higher in newer observation
    8. Record the flag only if ALL conditions are met

    **Why confirmed live cases may be sparse:** The system has been designed to prefer
    false negatives over false positives. A product that shrinks but whose price also dropped
    enough to keep PPU flat will not be flagged. A product where size data is ambiguous will
    not be flagged. This is correct behavior, not a bug.
    """)

    st.markdown("#### Price-Per-Unit (PPU) Increase")
    st.markdown("""
    The core metric is not the raw shelf price — it is the **price per unit of size**.

    ```
    PPU = price / size_value
    ```

    Example: A product shrinks from 9.75 oz at $4.99 to 9.25 oz at $4.89.
    - Old PPU: $4.99 / 9.75 = $0.512/oz
    - New PPU: $4.89 / 9.25 = $0.528/oz
    - PPU increase: +3.1%

    The shelf price *fell* by $0.10 — but you're paying more per ounce. That is shrinkflation.

    **Severity thresholds:**
    - HIGH: PPU increase ≥ 20%
    - MEDIUM: PPU increase ≥ 8%
    - LOW: PPU increase > 0% (any confirmed increase)
    """)

    st.markdown("#### What This Dashboard Does NOT Do")
    st.markdown("""
    - Does NOT present unconfirmed size changes as shrinkflation
    - Does NOT use historical prices as proxies for live prices
    - Does NOT combine historical and live counts without labeling them separately
    - Does NOT auto-refresh (scan runs on a 30-minute cache window)
    - Does NOT fabricate trend lines when live data is sparse
    - Does NOT hide zero live detections — they are shown honestly with an explanation
    """)

    st.markdown("#### Refresh Behavior")
    st.markdown("""
    The live scan (Open Food Facts + Kroger + detector) runs **at most once every 30 minutes**
    per Streamlit session, governed by `@st.cache_data(ttl=1800)`.

    To force a refresh before the 30-minute window expires, click **Refresh Data** in the sidebar.

    Data display caches (charts, tables, metrics) expire every **5 minutes** independently.
    """)


# =====================================================================
# FOOTER
# =====================================================================
st.markdown("---")
st.markdown(f"""
<div class="footer">
    <strong>Shrinkflation Detector</strong><br>
    Documented historical data: verified cases from BLS, Consumer Reports, mouseprint.org, FTC, and media investigations.<br>
    Live data: <a href="https://world.openfoodfacts.org/" target="_blank">Open Food Facts</a> API +
    <a href="https://developer.kroger.com/" target="_blank">Kroger API</a> — scanned on a 30-minute cycle.<br>
    All data is real. No fabricated, simulated, or random records. Historical and live evidence are always labeled separately.<br>
    Built with Python, Streamlit, SQLAlchemy, and Plotly.
</div>
""", unsafe_allow_html=True)
