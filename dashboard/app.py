"""
Streamlit dashboard — Shrinkflation Detector
Run with: streamlit run dashboard/app.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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

st.set_page_config(
    page_title="Shrinkflation Detector",
    page_icon="📉",
    layout="wide",
)

# Auto-refresh every 60 seconds
st_autorefresh(interval=60000, key="data_refresh")


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
    font=dict(size=13),
)

SEVERITY_COLORS = {"HIGH": "#e74c3c", "MEDIUM": "#f39c12", "LOW": "#f1c40f"}


# ---- Data loading ----
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
st.sidebar.title("Filters")

# Category filter
all_categories = sorted(flags_df["category"].dropna().unique()) if not flags_df.empty else []
selected_category = st.sidebar.selectbox(
    "Category", ["All Categories"] + all_categories
)

# Brand filter
if not flags_df.empty:
    if selected_category != "All Categories":
        available_brands = sorted(flags_df[flags_df["category"] == selected_category]["brand"].dropna().unique())
    else:
        available_brands = sorted(flags_df["brand"].dropna().unique())
else:
    available_brands = []
selected_brand = st.sidebar.selectbox("Brand", ["All Brands"] + available_brands)

# Severity filter
selected_severity = st.sidebar.selectbox("Severity", ["ALL", "HIGH", "MEDIUM", "LOW"])

# Date range filter
st.sidebar.markdown("---")
date_range = st.sidebar.slider(
    "Days back",
    min_value=7, max_value=90, value=90, step=7,
    help="Show flags from the last N days",
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Total products:** {len(products_df):,}")
st.sidebar.markdown(f"**Total flags:** {len(flags_df):,}")

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
st.title("Shrinkflation Detector")
total_products = len(products_df) if not products_df.empty else 0
st.caption(f"Tracking hidden price increases across {total_products:,}+ products · "
           f"Updated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

# =====================================================================
# METRICS ROW
# =====================================================================
if isinstance(stats, dict) and "error" not in stats:
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Products Tracked", f"{stats['total_products_tracked']:,}")
    m2.metric("Shrinks This Month", f"{stats['shrinks_detected_this_month']:,}")
    m3.metric("Avg Hidden Increase", f"+{stats['avg_hidden_price_increase_pct']:.1f}%")
    m4.metric("Worst Category", stats["worst_category"].title())
    m5.metric("Worst Brand", stats["worst_brand"])
else:
    st.info("No data yet. Loading...")

st.divider()

# =====================================================================
# ROW 1: Worst Brands + Severity Breakdown
# =====================================================================
if not filtered.empty:
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
        )
        fig1.update_layout(**CHART_LAYOUT, height=400)
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
                marker=dict(size=8),
            ))
            fig2.update_layout(**CHART_LAYOUT, height=400, yaxis_title="New Flags")
            st.plotly_chart(fig2, use_container_width=True)

    with col3:
        st.subheader("Severity Split")
        sev_counts = filtered["severity"].value_counts().reset_index()
        sev_counts.columns = ["severity", "count"]
        fig_donut = px.pie(
            sev_counts, values="count", names="severity",
            color="severity",
            color_discrete_map=SEVERITY_COLORS,
            hole=0.5,
        )
        fig_donut.update_layout(
            height=400, margin=dict(l=10, r=10, t=10, b=10),
            showlegend=True, legend=dict(orientation="h"),
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    st.divider()

    # =====================================================================
    # ROW 2: Category Breakdown + Brand Comparison
    # =====================================================================
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
            )
            fig3.update_layout(**CHART_LAYOUT, height=400)
            st.plotly_chart(fig3, use_container_width=True)

    with col_right:
        st.subheader("Average Hidden Price Increase by Category")
        if not filtered.empty:
            cat_avg = (
                filtered.groupby("category")["real_price_increase_pct"]
                .mean().round(1).sort_values(ascending=True)
                .reset_index()
            )
            fig4 = px.bar(
                cat_avg, x="real_price_increase_pct", y="category", orientation="h",
                color="real_price_increase_pct", color_continuous_scale="Reds",
                labels={"real_price_increase_pct": "Avg Hidden Increase (%)", "category": ""},
            )
            fig4.update_layout(**CHART_LAYOUT, height=400)
            st.plotly_chart(fig4, use_container_width=True)

    st.divider()

    # =====================================================================
    # ROW 3: Interactive Brand Deep Dive
    # =====================================================================
    st.subheader("Brand Deep Dive")
    st.caption("Select a brand to see all its flagged products")

    brand_list = sorted(filtered["brand"].dropna().unique())
    dive_brand = st.selectbox("Choose brand", brand_list, key="brand_dive")

    if dive_brand:
        brand_data = filtered[filtered["brand"] == dive_brand]

        bc1, bc2, bc3 = st.columns(3)
        bc1.metric("Flagged Products", len(brand_data))
        bc2.metric("Avg Hidden Increase", f"+{brand_data['real_price_increase_pct'].mean():.1f}%")
        high_pct = (brand_data["severity"] == "HIGH").sum() / len(brand_data) * 100 if len(brand_data) > 0 else 0
        bc3.metric("HIGH Severity %", f"{high_pct:.0f}%")

        # Product-level breakdown for this brand
        fig_brand = px.bar(
            brand_data.sort_values("real_price_increase_pct", ascending=False).head(20),
            x="real_price_increase_pct", y="product", orientation="h",
            color="severity", color_discrete_map=SEVERITY_COLORS,
            labels={"real_price_increase_pct": "Hidden Increase (%)", "product": ""},
        )
        fig_brand.update_layout(**CHART_LAYOUT, height=max(300, len(brand_data.head(20)) * 28))
        fig_brand.update_yaxes(categoryorder="total ascending")
        st.plotly_chart(fig_brand, use_container_width=True)

    st.divider()

    # =====================================================================
    # AI INSIGHTS PANEL
    # =====================================================================
    st.subheader("AI Insights")

    insight_content, insight_time = load_latest_insight()
    if insight_content:
        st.info(insight_content)
        if insight_time:
            st.caption(f"Generated: {insight_time.strftime('%Y-%m-%d %H:%M UTC')}")
    else:
        st.caption("No AI insights yet. Click below or run `python main.py --insight`.")

    btn_col, _ = st.columns([1, 3])
    with btn_col:
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

    # Ask the data
    st.subheader("Ask the Data")
    user_q = st.text_input(
        "Ask any question about shrinkflation",
        placeholder="e.g., Which chip brand shrunk the most products? What's the worst category?",
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

    # =====================================================================
    # PRODUCT DEEP DIVE
    # =====================================================================
    st.subheader("Product Deep Dive")
    product_search = st.text_input("Search for a product to see its full history", key="pdive")

    if st.button("Show History") and product_search:
        history = get_product_history(product_search)

        if isinstance(history, dict) and "error" in history:
            st.warning(history["error"])
        elif isinstance(history, dict) and history.get("snapshots"):
            st.markdown(f"**{history['product']}** by {history['brand']} ({history['category']})")

            snap_df = pd.DataFrame(history["snapshots"])
            snap_df["date"] = pd.to_datetime(snap_df["date"])

            lc, rc = st.columns(2)
            with lc:
                if snap_df["size_value"].notna().any():
                    fig_s = px.line(snap_df, x="date", y="size_value", title="Size Over Time", markers=True)
                    fig_s.update_layout(**CHART_LAYOUT, height=300)
                    st.plotly_chart(fig_s, use_container_width=True)

            with rc:
                snap_df["price_num"] = snap_df["price"].apply(
                    lambda x: float(x.replace("$", "")) if isinstance(x, str) and x.startswith("$") else None
                )
                if snap_df["price_num"].notna().any():
                    fig_p = px.line(snap_df, x="date", y="price_num", title="Price Over Time", markers=True)
                    fig_p.update_layout(**CHART_LAYOUT, height=300)
                    st.plotly_chart(fig_p, use_container_width=True)

            if history.get("shrinkflation_events"):
                st.markdown("**Shrinkflation Events:**")
                for evt in history["shrinkflation_events"]:
                    st.markdown(
                        f"- {evt['date']}: Size {evt['old_size']} → {evt['new_size']} "
                        f"({evt['real_increase_pct']} real increase, severity: {evt['severity']})"
                    )
        else:
            st.info("No history found.")

    st.divider()

    # =====================================================================
    # FLAGGED PRODUCTS TABLE
    # =====================================================================
    st.subheader("Flagged Products")

    search = st.text_input("Search by product or brand name", "", key="table_search")

    display = filtered.copy()
    if search:
        mask = (
            display["product"].str.contains(search, case=False, na=False)
            | display["brand"].str.contains(search, case=False, na=False)
        )
        display = display[mask]

    show_cols = ["product", "brand", "category", "old_size", "new_size",
                 "old_price", "new_price", "real_price_increase_pct", "severity", "detected_at"]
    existing = [c for c in show_cols if c in display.columns]
    table = display[existing].head(200).copy()

    if "old_price" in table.columns:
        table["old_price"] = table["old_price"].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
    if "new_price" in table.columns:
        table["new_price"] = table["new_price"].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
    if "real_price_increase_pct" in table.columns:
        table["real_price_increase_pct"] = table["real_price_increase_pct"].apply(
            lambda x: f"+{x:.1f}%" if pd.notna(x) else "N/A"
        )

    def color_severity(val):
        return {"HIGH": "background-color: #fadbd8", "MEDIUM": "background-color: #fdebd0",
                "LOW": "background-color: #fef9e7"}.get(val, "")

    if not table.empty and "severity" in table.columns:
        st.dataframe(
            table.style.map(color_severity, subset=["severity"]),
            use_container_width=True, height=500,
        )
    else:
        st.dataframe(table, use_container_width=True, height=500)

    st.caption(f"Showing {min(200, len(table))} of {len(display)} flagged products")

else:
    st.info("No flagged products yet. Run the pipeline:")
    st.code("python main.py --seed\npython main.py --analyze", language="bash")
