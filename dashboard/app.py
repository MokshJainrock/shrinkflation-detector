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
    Product, ProductSnapshot, ShrinkflationFlag, AgentInsight, get_session, get_engine, init_db,
)
from agent.tools import get_summary_stats, get_worst_offenders, get_category_breakdown, get_trend_data


# Auto-seed on first run (for Streamlit Cloud deployment)
@st.cache_resource
def _ensure_db():
    init_db()
    session = get_session()
    if session.query(Product).count() == 0:
        session.close()
        # Import and run seed inline
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from main import cmd_seed
        cmd_seed()
    else:
        session.close()

_ensure_db()

st.set_page_config(
    page_title="Shrinkflation Detector",
    page_icon="📉",
    layout="wide",
)

# Auto-refresh every 60 seconds
st_autorefresh(interval=60000, key="data_refresh")

# ---- Minimal chart style ----
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
        df = pd.read_sql(
            """
            SELECT f.*, p.name as product, p.brand, p.category
            FROM shrinkflation_flags f
            JOIN products p ON p.id = f.product_id
            ORDER BY f.detected_at DESC
            """,
            engine,
        )
        return df
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


# ---- Header ----
st.title("Shrinkflation Detector")
st.caption("Tracking hidden price increases across 5,000+ products")
st.caption(f"Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

# ---- Metrics row ----
stats = get_summary_stats()

if isinstance(stats, dict) and "error" not in stats:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Products Tracked", f"{stats['total_products_tracked']:,}")
    m2.metric("Shrinks This Month", f"{stats['shrinks_detected_this_month']:,}")
    m3.metric("Avg Hidden Increase", f"+{stats['avg_hidden_price_increase_pct']:.1f}%")
    m4.metric("Worst Category", stats["worst_category"].title())
else:
    st.info("No data yet. Run `python main.py --seed` to load sample data, then `python main.py --analyze`.")

st.divider()

# ---- Charts row ----
flags_df = load_flags()

if not flags_df.empty:
    left, right = st.columns(2)

    with left:
        st.subheader("Top 10 Worst Brands")
        offenders = get_worst_offenders(10)
        if offenders and not isinstance(offenders, dict):
            off_df = pd.DataFrame(offenders)
            fig1 = px.bar(
                off_df,
                x="flag_count",
                y="brand",
                orientation="h",
                color="avg_real_price_increase_pct",
                color_continuous_scale="Reds",
                labels={"flag_count": "Shrinkflation Flags", "brand": "", "avg_real_price_increase_pct": "Avg Increase %"},
            )
            fig1.update_layout(**CHART_LAYOUT, height=400)
            fig1.update_yaxes(categoryorder="total ascending")
            st.plotly_chart(fig1, use_container_width=True)

    with right:
        st.subheader("Weekly Trend — New Shrinks Detected")
        trend = get_trend_data(12)
        if trend and not isinstance(trend, dict):
            trend_df = pd.DataFrame(trend)
            trend_df["week"] = pd.to_datetime(trend_df["week"])
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=trend_df["week"],
                y=trend_df["new_flags"],
                mode="lines+markers",
                fill="tozeroy",
                line=dict(color="#e74c3c", width=2),
                marker=dict(size=6),
            ))
            fig2.update_layout(**CHART_LAYOUT, height=400, yaxis_title="New Flags")
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ---- Category breakdown ----
    st.subheader("Shrinkflation Rate by Category")
    cats = get_category_breakdown()
    if cats and not isinstance(cats, dict):
        cat_df = pd.DataFrame(cats)
        fig3 = px.bar(
            cat_df.sort_values("shrinkflation_rate_pct", ascending=True),
            x="shrinkflation_rate_pct",
            y="category",
            orientation="h",
            color="shrinkflation_rate_pct",
            color_continuous_scale="YlOrRd",
            labels={"shrinkflation_rate_pct": "Shrinkflation Rate (%)", "category": ""},
        )
        fig3.update_layout(**CHART_LAYOUT, height=400)
        st.plotly_chart(fig3, use_container_width=True)

    st.divider()

    # ---- AI Insights Panel ----
    st.subheader("AI Insights")

    insight_content, insight_time = load_latest_insight()

    if insight_content:
        st.info(insight_content)
        if insight_time:
            st.caption(f"Generated: {insight_time.strftime('%Y-%m-%d %H:%M UTC')}")
    else:
        st.caption("No AI insights yet. Click 'Generate Insight' or run `python main.py --insight`.")

    col_btn, col_spacer = st.columns([1, 3])
    with col_btn:
        if st.button("Generate New Insight", type="primary"):
            try:
                from agent.analyst import generate_daily_insight
                with st.spinner("AI is analyzing the data..."):
                    new_insight = generate_daily_insight()
                st.success(new_insight)
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Could not generate insight: {e}")

    st.markdown("---")

    # Ask the data
    st.subheader("Ask the Data")
    user_q = st.text_input(
        "Ask any question about the shrinkflation data",
        placeholder="e.g., Which brand has shrunk the most products this year?",
    )
    if st.button("Ask", type="secondary") and user_q:
        try:
            from agent.analyst import chat_with_data_streaming
            response_container = st.empty()
            full_response = ""
            for chunk in chat_with_data_streaming(user_q):
                full_response += chunk
                response_container.markdown(full_response)
        except Exception as e:
            st.error(f"Agent error: {e}. Make sure OPENAI_API_KEY is set in .env")

    st.divider()

    # ---- Flagged products table ----
    st.subheader("Flagged Products")

    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        search = st.text_input("Search by product or brand", "")
    with filter_col2:
        severity_filter = st.selectbox("Severity", ["ALL", "HIGH", "MEDIUM", "LOW"])

    display_df = flags_df.copy()
    if search:
        mask = (
            display_df["product"].str.contains(search, case=False, na=False)
            | display_df["brand"].str.contains(search, case=False, na=False)
        )
        display_df = display_df[mask]
    if severity_filter != "ALL":
        display_df = display_df[display_df["severity"] == severity_filter]

    # Format columns
    show_cols = ["product", "brand", "category", "old_size", "new_size",
                 "old_price", "new_price", "real_price_increase_pct", "severity", "detected_at"]
    existing = [c for c in show_cols if c in display_df.columns]
    display_subset = display_df[existing].head(100).copy()

    if "old_price" in display_subset.columns:
        display_subset["old_price"] = display_subset["old_price"].apply(
            lambda x: f"${x:.2f}" if pd.notna(x) else "N/A"
        )
    if "new_price" in display_subset.columns:
        display_subset["new_price"] = display_subset["new_price"].apply(
            lambda x: f"${x:.2f}" if pd.notna(x) else "N/A"
        )
    if "real_price_increase_pct" in display_subset.columns:
        display_subset["real_price_increase_pct"] = display_subset["real_price_increase_pct"].apply(
            lambda x: f"+{x:.1f}%" if pd.notna(x) else "N/A"
        )

    def color_severity(val):
        colors = {"HIGH": "background-color: #fadbd8", "MEDIUM": "background-color: #fdebd0", "LOW": "background-color: #fef9e7"}
        return colors.get(val, "")

    if not display_subset.empty and "severity" in display_subset.columns:
        styled = display_subset.style.map(color_severity, subset=["severity"])
        st.dataframe(styled, use_container_width=True, height=400)
    else:
        st.dataframe(display_subset, use_container_width=True, height=400)

    st.caption(f"Showing {min(100, len(display_subset))} of {len(display_df)} flagged products")

    st.divider()

    # ---- Product deep dive ----
    st.subheader("Product Deep Dive")
    product_search = st.text_input("Enter product name to see full history", key="product_dive")

    if st.button("Show History") and product_search:
        from agent.tools import get_product_history
        history = get_product_history(product_search)

        if isinstance(history, dict) and "error" in history:
            st.warning(history["error"])
        elif isinstance(history, dict) and history.get("snapshots"):
            st.markdown(f"**{history['product']}** by {history['brand']} ({history['category']})")

            snap_df = pd.DataFrame(history["snapshots"])
            snap_df["date"] = pd.to_datetime(snap_df["date"])

            left_chart, right_chart = st.columns(2)

            with left_chart:
                if snap_df["size_value"].notna().any():
                    fig_size = px.line(
                        snap_df, x="date", y="size_value",
                        title="Size Over Time",
                        markers=True,
                    )
                    fig_size.update_layout(**CHART_LAYOUT, height=300)
                    st.plotly_chart(fig_size, use_container_width=True)

            with right_chart:
                snap_df["price_num"] = snap_df["price"].apply(
                    lambda x: float(x.replace("$", "")) if isinstance(x, str) and x.startswith("$") else None
                )
                if snap_df["price_num"].notna().any():
                    fig_price = px.line(
                        snap_df, x="date", y="price_num",
                        title="Price Over Time",
                        markers=True,
                    )
                    fig_price.update_layout(**CHART_LAYOUT, height=300)
                    st.plotly_chart(fig_price, use_container_width=True)

            if history.get("shrinkflation_events"):
                st.markdown("**Shrinkflation Events:**")
                for evt in history["shrinkflation_events"]:
                    st.markdown(
                        f"- {evt['date']}: Size {evt['old_size']} → {evt['new_size']} "
                        f"({evt['real_increase_pct']} real increase, severity: {evt['severity']})"
                    )
        else:
            st.info("No snapshot history found for this product.")

else:
    st.info("No flagged products yet. Run the pipeline first:")
    st.code("python main.py --seed      # Load sample data\npython main.py --analyze   # Run detector", language="bash")

st.markdown("---")
