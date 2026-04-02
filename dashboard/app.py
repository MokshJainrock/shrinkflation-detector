"""
Streamlit dashboard — Shrinkflation Detector (Enhanced Interactive Edition)
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
from datetime import datetime, timezone

from db.models import (
    Product, ProductSnapshot, ShrinkflationFlag, AgentInsight,
    get_session, get_engine, init_db,
)
from agent.tools import (
    get_summary_stats, get_worst_offenders, get_category_breakdown,
    get_trend_data, get_product_history,
)

# =====================================================================
# PAGE CONFIG & CUSTOM CSS
# =====================================================================
st.set_page_config(
    page_title="Shrinkflation Detector",
    page_icon="📉",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Main header styling */
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        color: white;
    }
    .main-header h1 { color: white; margin: 0; font-size: 2.2rem; }
    .main-header p { color: #94a3b8; margin: 0.3rem 0 0 0; font-size: 1rem; }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border: 1px solid #dee2e6;
        border-radius: 10px;
        padding: 12px 16px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetric"] label { font-size: 0.85rem !important; color: #495057 !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 700 !important; }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 20px;
        font-weight: 600;
    }

    /* Severity badges */
    .severity-high { background: #e74c3c; color: white; padding: 2px 10px; border-radius: 12px; font-weight: 600; font-size: 0.8rem; }
    .severity-medium { background: #f39c12; color: white; padding: 2px 10px; border-radius: 12px; font-weight: 600; font-size: 0.8rem; }
    .severity-low { background: #f1c40f; color: #333; padding: 2px 10px; border-radius: 12px; font-weight: 600; font-size: 0.8rem; }

    /* Info cards */
    .info-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.2rem;
        margin-bottom: 0.8rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }

    /* Hide default streamlit padding */
    .block-container { padding-top: 1rem; }

    /* Comparison card */
    .compare-card {
        background: linear-gradient(135deg, #fff5f5 0%, #fed7d7 100%);
        border: 2px solid #fc8181;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
    }
    .compare-card-ok {
        background: linear-gradient(135deg, #f0fff4 0%, #c6f6d5 100%);
        border: 2px solid #68d391;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
    }

    /* Footer */
    .footer { text-align: center; color: #94a3b8; padding: 2rem 0; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

# Auto-refresh every 90 seconds
st_autorefresh(interval=90000, key="data_refresh")


# ---- Auto-seed on first run ----
@st.cache_resource
def _ensure_db():
    init_db()
    session = get_session()
    if session.query(Product).count() == 0:
        session.close()
        from main import cmd_seed
        cmd_seed()
    else:
        session.close()

_ensure_db()

# ---- Chart style ----
CHART_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(showgrid=False),
    yaxis=dict(showgrid=False),
    margin=dict(l=20, r=20, t=40, b=20),
    font=dict(size=13, family="Inter, sans-serif"),
)

SEVERITY_COLORS = {"HIGH": "#e74c3c", "MEDIUM": "#f39c12", "LOW": "#f1c40f"}
CATEGORY_COLORS = px.colors.qualitative.Set3


# =====================================================================
# DATA LOADING
# =====================================================================
@st.cache_data(ttl=60)
def load_flags():
    engine = get_engine()
    try:
        return pd.read_sql(
            """SELECT f.*, p.name as product, p.brand, p.category
               FROM shrinkflation_flags f
               JOIN products p ON p.id = f.product_id
               ORDER BY f.detected_at DESC""",
            engine,
        )
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60)
def load_all_products():
    engine = get_engine()
    try:
        return pd.read_sql("SELECT * FROM products", engine)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60)
def load_snapshots_for_product(product_id):
    engine = get_engine()
    try:
        return pd.read_sql(
            f"SELECT * FROM product_snapshots WHERE product_id = {product_id} ORDER BY scraped_at",
            engine,
        )
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60)
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
        if insight:
            return insight.content, insight.generated_at
        return None, None
    except Exception:
        return None, None


# ---- Load data ----
flags_df = load_flags()
products_df = load_all_products()
stats = get_summary_stats()

# =====================================================================
# SIDEBAR — Interactive Filters
# =====================================================================
with st.sidebar:
    st.markdown("## 🔍 Filters")

    # Category filter
    all_categories = sorted(flags_df["category"].dropna().unique()) if not flags_df.empty else []
    selected_category = st.selectbox("📂 Category", ["All Categories"] + all_categories)

    # Brand filter (dependent on category)
    if not flags_df.empty:
        if selected_category != "All Categories":
            available_brands = sorted(flags_df[flags_df["category"] == selected_category]["brand"].dropna().unique())
        else:
            available_brands = sorted(flags_df["brand"].dropna().unique())
    else:
        available_brands = []
    selected_brand = st.selectbox("🏷️ Brand", ["All Brands"] + available_brands)

    # Severity filter
    selected_severity = st.selectbox("⚠️ Severity", ["ALL", "HIGH", "MEDIUM", "LOW"])

    # Date range filter
    st.markdown("---")
    date_range = st.slider(
        "📅 Days back",
        min_value=7, max_value=90, value=90, step=7,
        help="Show flags from the last N days",
    )

    # Quick stats
    st.markdown("---")
    st.markdown("### 📊 Quick Stats")
    col_s1, col_s2 = st.columns(2)
    col_s1.metric("Products", f"{len(products_df):,}")
    col_s2.metric("Flags", f"{len(flags_df):,}")

    if not flags_df.empty:
        high_count = (flags_df["severity"] == "HIGH").sum()
        med_count = (flags_df["severity"] == "MEDIUM").sum()
        low_count = (flags_df["severity"] == "LOW").sum()
        st.markdown(f"🔴 HIGH: **{high_count:,}** · 🟡 MEDIUM: **{med_count:,}** · 🟢 LOW: **{low_count:,}**")

    st.markdown("---")
    st.markdown("*Data is simulated for demo.*")
    st.markdown("*Real data via `--scrape` flag.*")

# ---- Apply filters ----
filtered = flags_df.copy()
if not filtered.empty:
    if selected_category != "All Categories":
        filtered = filtered[filtered["category"] == selected_category]
    if selected_brand != "All Brands":
        filtered = filtered[filtered["brand"] == selected_brand]
    if selected_severity != "ALL":
        filtered = filtered[filtered["severity"] == selected_severity]
    if "detected_at" in filtered.columns:
        filtered["detected_at"] = pd.to_datetime(filtered["detected_at"], utc=True)
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=date_range)
        filtered = filtered[filtered["detected_at"] >= cutoff]


# =====================================================================
# HEADER
# =====================================================================
st.markdown(f"""
<div class="main-header">
    <h1>📉 Shrinkflation Detector</h1>
    <p>Tracking hidden price increases across {len(products_df):,}+ grocery products ·
    Updated {datetime.now(timezone.utc).strftime('%b %d, %Y %H:%M UTC')} ·
    {len(filtered):,} flagged products match your filters</p>
</div>
""", unsafe_allow_html=True)

# =====================================================================
# METRICS ROW
# =====================================================================
if isinstance(stats, dict) and "error" not in stats:
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("🛒 Products Tracked", f"{stats['total_products_tracked']:,}")
    m2.metric("📉 Shrinks This Month", f"{stats['shrinks_detected_this_month']:,}")
    m3.metric("💰 Avg Hidden Increase", f"+{stats['avg_hidden_price_increase_pct']:.1f}%")
    m4.metric("📂 Worst Category", stats["worst_category"].title())
    m5.metric("🏷️ Worst Brand", stats["worst_brand"])

    # Extra metric: % of products affected
    if stats["total_products_tracked"] > 0:
        pct_affected = round(stats["shrinks_detected_this_month"] / stats["total_products_tracked"] * 100, 1)
        m6.metric("📈 % Affected", f"{pct_affected}%")
    else:
        m6.metric("📈 % Affected", "0%")
else:
    st.info("No data yet. Loading seed data...")

st.markdown("")

# =====================================================================
# MAIN CONTENT — TABBED LAYOUT
# =====================================================================
if not filtered.empty:
    tab_overview, tab_compare, tab_deepdive, tab_explorer, tab_ai, tab_data = st.tabs([
        "📊 Overview", "⚖️ Compare", "🔬 Deep Dive", "🗺️ Explorer", "🤖 AI Insights", "📋 Data Table"
    ])

    # =================================================================
    # TAB 1: OVERVIEW
    # =================================================================
    with tab_overview:
        col1, col2, col3 = st.columns([2, 2, 1])

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
                labels={"flags": "Shrinkflation Flags", "brand": "", "avg_increase": "Avg Increase %"},
                text="flags",
            )
            fig1.update_traces(textposition="outside")
            fig1.update_layout(**CHART_LAYOUT, height=420)
            fig1.update_yaxes(categoryorder="total ascending")
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            st.subheader("Weekly Detection Trend")
            trend = get_trend_data(12)
            if trend and not isinstance(trend, dict):
                trend_df = pd.DataFrame(trend)
                trend_df["week"] = pd.to_datetime(trend_df["week"])
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(
                    x=trend_df["week"], y=trend_df["new_flags"],
                    mode="lines+markers", fill="tozeroy",
                    line=dict(color="#e74c3c", width=3),
                    marker=dict(size=8, color="#c0392b"),
                    name="New Flags",
                    hovertemplate="Week of %{x|%b %d}<br>New Flags: %{y}<extra></extra>",
                ))
                # Add moving average
                if len(trend_df) >= 3:
                    trend_df["ma"] = trend_df["new_flags"].rolling(3, min_periods=1).mean()
                    fig2.add_trace(go.Scatter(
                        x=trend_df["week"], y=trend_df["ma"],
                        mode="lines", line=dict(color="#3498db", width=2, dash="dash"),
                        name="3-Week Avg",
                    ))
                fig2.update_layout(**CHART_LAYOUT, height=420, yaxis_title="New Flags",
                                   legend=dict(orientation="h", yanchor="bottom", y=1.02))
                st.plotly_chart(fig2, use_container_width=True)

        with col3:
            st.subheader("Severity Split")
            sev_counts = filtered["severity"].value_counts().reset_index()
            sev_counts.columns = ["severity", "count"]
            fig_donut = px.pie(
                sev_counts, values="count", names="severity",
                color="severity", color_discrete_map=SEVERITY_COLORS,
                hole=0.55,
            )
            fig_donut.update_traces(
                textinfo="percent+value",
                textfont_size=12,
                hovertemplate="%{label}: %{value} flags (%{percent})<extra></extra>",
            )
            fig_donut.update_layout(
                height=420, margin=dict(l=10, r=10, t=10, b=10),
                showlegend=True, legend=dict(orientation="h", y=-0.1),
            )
            st.plotly_chart(fig_donut, use_container_width=True)

        st.divider()

        # ---- Category breakdown row ----
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Shrinkflation Rate by Category")
            cats = get_category_breakdown()
            if cats and not isinstance(cats, dict):
                cat_df = pd.DataFrame(cats)
                fig3 = px.bar(
                    cat_df.sort_values("shrinkflation_rate_pct", ascending=True),
                    x="shrinkflation_rate_pct", y="category", orientation="h",
                    color="shrinkflation_rate_pct", color_continuous_scale="YlOrRd",
                    labels={"shrinkflation_rate_pct": "Shrinkflation Rate (%)", "category": ""},
                    text="shrinkflation_rate_pct",
                )
                fig3.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
                fig3.update_layout(**CHART_LAYOUT, height=420)
                st.plotly_chart(fig3, use_container_width=True)

        with col_right:
            st.subheader("Average Hidden Price Increase by Category")
            cat_avg = (
                filtered.groupby("category")["real_price_increase_pct"]
                .mean().round(1).sort_values(ascending=True)
                .reset_index()
            )
            fig4 = px.bar(
                cat_avg, x="real_price_increase_pct", y="category", orientation="h",
                color="real_price_increase_pct", color_continuous_scale="Reds",
                labels={"real_price_increase_pct": "Avg Hidden Increase (%)", "category": ""},
                text="real_price_increase_pct",
            )
            fig4.update_traces(texttemplate="+%{text:.1f}%", textposition="outside")
            fig4.update_layout(**CHART_LAYOUT, height=420)
            st.plotly_chart(fig4, use_container_width=True)

        st.divider()

        # ---- Treemap of all flags ----
        st.subheader("Shrinkflation Treemap — Category → Brand → Severity")
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
            fig_tree.update_layout(height=500, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig_tree, use_container_width=True)

    # =================================================================
    # TAB 2: COMPARE — Side-by-side comparison tool
    # =================================================================
    with tab_compare:
        st.subheader("⚖️ Brand vs Brand Comparison")
        st.caption("Select two brands to compare their shrinkflation profiles side by side")

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

            # Side by side metrics
            c1, c2 = st.columns(2)

            with c1:
                st.markdown(f"### 🏷️ {brand_a}")
                ma1, ma2, ma3 = st.columns(3)
                ma1.metric("Flags", len(data_a))
                avg_a = data_a["real_price_increase_pct"].mean() if not data_a.empty else 0
                ma2.metric("Avg Increase", f"+{avg_a:.1f}%")
                high_a = (data_a["severity"] == "HIGH").sum() if not data_a.empty else 0
                ma3.metric("HIGH Severity", high_a)

                if not data_a.empty:
                    sev_a = data_a["severity"].value_counts().reset_index()
                    sev_a.columns = ["severity", "count"]
                    fig_a = px.pie(sev_a, values="count", names="severity",
                                   color="severity", color_discrete_map=SEVERITY_COLORS, hole=0.5)
                    fig_a.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
                    fig_a.update_traces(textinfo="percent+label")
                    st.plotly_chart(fig_a, use_container_width=True)

                    # Top flagged products
                    st.markdown("**Top Flagged Products:**")
                    top_a = data_a.nlargest(5, "real_price_increase_pct")[["product", "real_price_increase_pct", "severity"]]
                    for _, row in top_a.iterrows():
                        sev_class = f"severity-{row['severity'].lower()}"
                        st.markdown(f"- {row['product']} — +{row['real_price_increase_pct']:.1f}% "
                                    f"<span class='{sev_class}'>{row['severity']}</span>", unsafe_allow_html=True)

            with c2:
                st.markdown(f"### 🏷️ {brand_b}")
                mb1, mb2, mb3 = st.columns(3)
                mb1.metric("Flags", len(data_b))
                avg_b = data_b["real_price_increase_pct"].mean() if not data_b.empty else 0
                mb2.metric("Avg Increase", f"+{avg_b:.1f}%")
                high_b = (data_b["severity"] == "HIGH").sum() if not data_b.empty else 0
                mb3.metric("HIGH Severity", high_b)

                if not data_b.empty:
                    sev_b = data_b["severity"].value_counts().reset_index()
                    sev_b.columns = ["severity", "count"]
                    fig_b = px.pie(sev_b, values="count", names="severity",
                                   color="severity", color_discrete_map=SEVERITY_COLORS, hole=0.5)
                    fig_b.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
                    fig_b.update_traces(textinfo="percent+label")
                    st.plotly_chart(fig_b, use_container_width=True)

                    st.markdown("**Top Flagged Products:**")
                    top_b = data_b.nlargest(5, "real_price_increase_pct")[["product", "real_price_increase_pct", "severity"]]
                    for _, row in top_b.iterrows():
                        sev_class = f"severity-{row['severity'].lower()}"
                        st.markdown(f"- {row['product']} — +{row['real_price_increase_pct']:.1f}% "
                                    f"<span class='{sev_class}'>{row['severity']}</span>", unsafe_allow_html=True)

            # Comparison verdict
            st.divider()
            if avg_a > avg_b:
                winner, loser = brand_b, brand_a
                diff = abs(avg_a - avg_b)
            else:
                winner, loser = brand_a, brand_b
                diff = abs(avg_b - avg_a)

            st.markdown(f"""
            <div class="compare-card">
                <h3>📊 Verdict</h3>
                <p><strong>{loser}</strong> has a <strong>+{diff:.1f}%</strong> higher average hidden price increase than <strong>{winner}</strong>.</p>
                <p>{loser} is the worse offender in this matchup.</p>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # ---- Category vs Category ----
        st.subheader("📂 Category vs Category")
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
                "Metric": ["Total Flags", "Avg Hidden Increase %", "HIGH Severity Count",
                           "Max Increase %", "Unique Brands Affected"],
                cat_a: [
                    len(d_a),
                    f"+{d_a['real_price_increase_pct'].mean():.1f}%" if not d_a.empty else "0%",
                    (d_a["severity"] == "HIGH").sum() if not d_a.empty else 0,
                    f"+{d_a['real_price_increase_pct'].max():.1f}%" if not d_a.empty else "0%",
                    d_a["brand"].nunique() if not d_a.empty else 0,
                ],
                cat_b: [
                    len(d_b),
                    f"+{d_b['real_price_increase_pct'].mean():.1f}%" if not d_b.empty else "0%",
                    (d_b["severity"] == "HIGH").sum() if not d_b.empty else 0,
                    f"+{d_b['real_price_increase_pct'].max():.1f}%" if not d_b.empty else "0%",
                    d_b["brand"].nunique() if not d_b.empty else 0,
                ],
            })
            st.dataframe(compare_df, use_container_width=True, hide_index=True)

    # =================================================================
    # TAB 3: DEEP DIVE — Brand & Product level
    # =================================================================
    with tab_deepdive:
        st.subheader("🔬 Brand Deep Dive")
        st.caption("Select a brand to see all its flagged products with detailed analysis")

        brand_list = sorted(filtered["brand"].dropna().unique())
        dive_brand = st.selectbox("Choose brand", brand_list, key="brand_dive")

        if dive_brand:
            brand_data = filtered[filtered["brand"] == dive_brand]

            bc1, bc2, bc3, bc4 = st.columns(4)
            bc1.metric("Flagged Products", len(brand_data))
            bc2.metric("Avg Hidden Increase", f"+{brand_data['real_price_increase_pct'].mean():.1f}%")
            high_pct = (brand_data["severity"] == "HIGH").sum() / len(brand_data) * 100 if len(brand_data) > 0 else 0
            bc3.metric("HIGH Severity %", f"{high_pct:.0f}%")
            bc4.metric("Categories Affected", brand_data["category"].nunique())

            # Product-level bar chart
            fig_brand = px.bar(
                brand_data.sort_values("real_price_increase_pct", ascending=False).head(25),
                x="real_price_increase_pct", y="product", orientation="h",
                color="severity", color_discrete_map=SEVERITY_COLORS,
                labels={"real_price_increase_pct": "Hidden Increase (%)", "product": ""},
                text="real_price_increase_pct",
            )
            fig_brand.update_traces(texttemplate="+%{text:.1f}%", textposition="outside")
            fig_brand.update_layout(**CHART_LAYOUT, height=max(350, len(brand_data.head(25)) * 28))
            fig_brand.update_yaxes(categoryorder="total ascending")
            st.plotly_chart(fig_brand, use_container_width=True)

            # Size change distribution for this brand
            if "old_size" in brand_data.columns and "new_size" in brand_data.columns:
                brand_data_calc = brand_data.copy()
                brand_data_calc["size_change_pct"] = (
                    (brand_data_calc["new_size"] - brand_data_calc["old_size"]) / brand_data_calc["old_size"] * 100
                )
                fig_hist = px.histogram(
                    brand_data_calc, x="size_change_pct", nbins=20,
                    color="severity", color_discrete_map=SEVERITY_COLORS,
                    labels={"size_change_pct": "Size Change (%)"},
                    title=f"Size Change Distribution for {dive_brand}",
                )
                fig_hist.update_layout(**CHART_LAYOUT, height=300, barmode="stack")
                st.plotly_chart(fig_hist, use_container_width=True)

        st.divider()

        # ---- Product Timeline ----
        st.subheader("📦 Product Timeline")
        st.caption("Select a product to see its full price and size history over time")

        # Use selectbox with search instead of text input
        if not products_df.empty:
            product_names = sorted(products_df["name"].dropna().unique())
            selected_product = st.selectbox(
                "Search & select a product",
                [""] + list(product_names),
                key="product_timeline",
                help="Type to search for a product",
            )

            if selected_product:
                history = get_product_history(selected_product)

                if isinstance(history, dict) and "error" in history:
                    st.warning(history["error"])
                elif isinstance(history, dict) and history.get("snapshots"):
                    st.markdown(f"**{history['product']}** by {history['brand']} ({history['category']})")

                    snap_df = pd.DataFrame(history["snapshots"])
                    snap_df["date"] = pd.to_datetime(snap_df["date"])

                    # Combined chart with dual Y-axes
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
                        **CHART_LAYOUT, height=400,
                        title=f"Size & Price Timeline — {history['product']}",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02),
                    )
                    fig_combo.update_yaxes(title_text="Size", secondary_y=False)
                    fig_combo.update_yaxes(title_text="Price ($)", secondary_y=True)
                    st.plotly_chart(fig_combo, use_container_width=True)

                    # Shrinkflation events
                    if history.get("shrinkflation_events"):
                        st.markdown("**🚨 Shrinkflation Events:**")
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
                        st.success("No shrinkflation events detected for this product.")
                else:
                    st.info("No history found for this product.")

    # =================================================================
    # TAB 4: EXPLORER — Scatter plots, heatmaps, interactive viz
    # =================================================================
    with tab_explorer:
        st.subheader("🗺️ Data Explorer")

        # ---- Scatter: Size Reduction vs Price Increase ----
        st.markdown("### Size Reduction vs Price Increase")
        st.caption("Each dot is a flagged product. Hover for details. Bigger dots = higher severity.")

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
            fig_scatter.update_layout(**CHART_LAYOUT, height=500,
                                      legend=dict(orientation="h", yanchor="bottom", y=-0.3))
            st.plotly_chart(fig_scatter, use_container_width=True)

        st.divider()

        # ---- Heatmap: Brand × Category ----
        st.markdown("### Brand × Category Heatmap")
        st.caption("Color intensity = average hidden price increase. Darker = worse.")

        # Get top 15 brands by flag count for readability
        top_brands = filtered["brand"].value_counts().head(15).index.tolist()
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
                text_auto=True,
                aspect="auto",
            )
            fig_heat.update_layout(height=500, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig_heat, use_container_width=True)

        st.divider()

        # ---- Price Impact Calculator ----
        st.markdown("### 💵 Price Impact Calculator")
        st.caption("See how much more you're actually paying after shrinkflation")

        calc_col1, calc_col2 = st.columns(2)
        with calc_col1:
            old_size_input = st.number_input("Original Size (oz)", value=16.0, step=0.5, min_value=0.1)
            old_price_input = st.number_input("Original Price ($)", value=4.99, step=0.25, min_value=0.01)
        with calc_col2:
            new_size_input = st.number_input("New Size (oz)", value=14.0, step=0.5, min_value=0.1)
            new_price_input = st.number_input("New Price ($)", value=4.99, step=0.25, min_value=0.01)

        if st.button("Calculate Impact", type="primary"):
            old_ppu = old_price_input / old_size_input
            new_ppu = new_price_input / new_size_input
            real_increase = ((new_ppu - old_ppu) / old_ppu) * 100
            size_change = ((new_size_input - old_size_input) / old_size_input) * 100

            res1, res2, res3 = st.columns(3)
            res1.metric("Size Change", f"{size_change:+.1f}%")
            res2.metric("Price per oz (old → new)", f"${old_ppu:.3f} → ${new_ppu:.3f}")
            res3.metric("Real Price Increase", f"{real_increase:+.1f}%")

            if real_increase > 5:
                st.error(f"🔴 HIGH shrinkflation detected! You're paying **{real_increase:.1f}% more** per unit.")
            elif real_increase > 2:
                st.warning(f"🟡 MEDIUM shrinkflation. You're paying **{real_increase:.1f}% more** per unit.")
            elif real_increase > 0:
                st.info(f"🟢 Mild increase of **{real_increase:.1f}%** per unit.")
            else:
                st.success(f"✅ No shrinkflation — you're actually paying **{abs(real_increase):.1f}% less** per unit.")

            # Annual impact
            weekly_purchase = st.slider("How many of these do you buy per month?", 1, 20, 4)
            annual_extra = (new_ppu - old_ppu) * new_size_input * weekly_purchase * 12
            if annual_extra > 0:
                st.markdown(f"**💸 Annual Impact:** You're paying an extra **${annual_extra:.2f}/year** "
                            f"on this product alone due to shrinkflation.")

    # =================================================================
    # TAB 5: AI INSIGHTS
    # =================================================================
    with tab_ai:
        st.subheader("🤖 AI-Powered Insights")

        insight_content, insight_time = load_latest_insight()
        if insight_content:
            st.markdown(f"""
            <div class="info-card">
                <strong>Latest AI Insight</strong><br><br>
                {insight_content}
            </div>
            """, unsafe_allow_html=True)
            if insight_time:
                st.caption(f"Generated: {insight_time.strftime('%Y-%m-%d %H:%M UTC')}")
        else:
            st.caption("No AI insights yet. Click below or run `python main.py --insight`.")

        btn_col, _ = st.columns([1, 3])
        with btn_col:
            if st.button("🔄 Generate New Insight", type="primary"):
                try:
                    from agent.analyst import generate_daily_insight
                    with st.spinner("AI analyzing data..."):
                        new_insight = generate_daily_insight()
                    st.success(new_insight)
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Could not generate: {e}. Set OPENAI_API_KEY in .env")

        st.markdown("---")

        # Ask the data
        st.subheader("💬 Ask the Data")
        st.caption("Ask natural language questions about shrinkflation trends")

        user_q = st.text_input(
            "Your question",
            placeholder="e.g., Which chip brand shrunk the most? What's the worst category this month?",
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
                st.error(f"Agent error: {e}. Make sure OPENAI_API_KEY is set in .env")

        st.divider()

        # Quick questions
        st.markdown("**Quick Questions:**")
        quick_qs = [
            "What brand has the worst shrinkflation?",
            "Which category is most affected?",
            "How has shrinkflation changed over the past month?",
            "What's the biggest single product size reduction?",
        ]
        for q in quick_qs:
            if st.button(f"💡 {q}", key=f"qq_{q}"):
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
    # TAB 6: DATA TABLE — Full searchable/downloadable table
    # =================================================================
    with tab_data:
        st.subheader("📋 Flagged Products Data")

        # Search
        search = st.text_input("🔍 Search by product or brand name", "", key="table_search")

        display = filtered.copy()
        if search:
            mask = (
                display["product"].str.contains(search, case=False, na=False)
                | display["brand"].str.contains(search, case=False, na=False)
            )
            display = display[mask]

        # Column selection
        all_show_cols = ["product", "brand", "category", "old_size", "new_size",
                         "old_price", "new_price", "real_price_increase_pct", "severity", "detected_at"]
        existing = [c for c in all_show_cols if c in display.columns]

        table = display[existing].copy()

        # Format columns
        if "old_price" in table.columns:
            table["old_price"] = table["old_price"].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
        if "new_price" in table.columns:
            table["new_price"] = table["new_price"].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
        if "real_price_increase_pct" in table.columns:
            table["real_price_increase_pct"] = table["real_price_increase_pct"].apply(
                lambda x: f"+{x:.1f}%" if pd.notna(x) else "N/A"
            )

        # Stats bar
        st1, st2, st3, st4 = st.columns(4)
        st1.metric("Showing", f"{len(table):,} products")
        if not display.empty:
            st2.metric("Avg Increase", f"+{filtered['real_price_increase_pct'].mean():.1f}%")
            st3.metric("Max Increase", f"+{filtered['real_price_increase_pct'].max():.1f}%")
            st4.metric("Categories", filtered["category"].nunique())

        # Color-coded table
        def color_severity(val):
            return {"HIGH": "background-color: #fadbd8; color: #922b21; font-weight: 600",
                    "MEDIUM": "background-color: #fdebd0; color: #935116; font-weight: 600",
                    "LOW": "background-color: #fef9e7; color: #7d6608; font-weight: 600"}.get(val, "")

        if not table.empty and "severity" in table.columns:
            st.dataframe(
                table.style.map(color_severity, subset=["severity"]),
                use_container_width=True, height=600,
            )
        else:
            st.dataframe(table, use_container_width=True, height=600)

        st.caption(f"Showing {len(table):,} of {len(display):,} flagged products")

        # Download buttons
        st.markdown("---")
        dl1, dl2, _ = st.columns([1, 1, 3])
        with dl1:
            csv = display[existing].to_csv(index=False)
            st.download_button(
                "📥 Download CSV",
                data=csv,
                file_name=f"shrinkflation_flags_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )
        with dl2:
            # JSON export
            json_data = display[existing].to_json(orient="records", indent=2)
            st.download_button(
                "📥 Download JSON",
                data=json_data,
                file_name=f"shrinkflation_flags_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
            )

else:
    st.info("No flagged products yet. Run the pipeline:")
    st.code("python main.py --seed\npython main.py --analyze", language="bash")


# =====================================================================
# FOOTER
# =====================================================================
st.markdown("---")
st.markdown("""
<div class="footer">
    <p><strong>Shrinkflation Detector</strong> · Tracking hidden price increases in grocery products</p>
    <p>Data sourced from Open Food Facts API + Kroger API · AI insights powered by GPT-4o</p>
    <p>Built with Python, Streamlit, SQLAlchemy, and Plotly</p>
</div>
""", unsafe_allow_html=True)
