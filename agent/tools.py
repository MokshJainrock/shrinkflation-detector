"""
Agent tool definitions — functions the AI agent can call to query the database.
Each returns a dict/list that gets serialized to JSON for the agent.

Phase 6 note: uses price_per_unit_increase_pct (renamed from real_price_increase_pct
in Phase 5.1). All queries filter or label by flag_source where relevant.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import func, desc

from db.models import Product, ProductSnapshot, ShrinkflationFlag, get_session


def _safe_query(fn):
    """Decorator that catches DB errors and returns a clean error message."""
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            return {"error": f"Query failed: {str(e)}"}
    return wrapper


@_safe_query
def get_summary_stats() -> dict:
    """
    Returns high-level summary stats, source-split.

    flag_source values:
      - documented_historical : seeded from published research
      - live_detected         : confirmed by live API tracking
    """
    session = get_session()

    total_products = session.query(func.count(Product.id)).scalar() or 0

    hist_products = (
        session.query(func.count(Product.id))
        .filter(Product.data_source == "documented_historical")
        .scalar() or 0
    )

    live_products = total_products - hist_products

    hist_flags = (
        session.query(func.count(ShrinkflationFlag.id))
        .filter(ShrinkflationFlag.flag_source == "documented_historical")
        .scalar() or 0
    )

    live_flags = (
        session.query(func.count(ShrinkflationFlag.id))
        .filter(ShrinkflationFlag.flag_source == "live_detected")
        .scalar() or 0
    )

    total_flags = hist_flags + live_flags

    # Average PPU increase — only meaningful for flags with price evidence
    avg_increase = (
        session.query(func.avg(ShrinkflationFlag.price_per_unit_increase_pct))
        .filter(ShrinkflationFlag.has_price_evidence == True)
        .scalar()
    )
    avg_increase = round(float(avg_increase), 1) if avg_increase else 0.0

    # Worst category by total confirmed flags
    worst_cat_row = (
        session.query(Product.category, func.count(ShrinkflationFlag.id).label("cnt"))
        .join(ShrinkflationFlag, ShrinkflationFlag.product_id == Product.id)
        .group_by(Product.category)
        .order_by(desc("cnt"))
        .first()
    )
    worst_category = worst_cat_row[0] if worst_cat_row else "N/A"

    # Worst brand by total confirmed flags
    worst_brand_row = (
        session.query(Product.brand, func.count(ShrinkflationFlag.id).label("cnt"))
        .join(ShrinkflationFlag, ShrinkflationFlag.product_id == Product.id)
        .group_by(Product.brand)
        .order_by(desc("cnt"))
        .first()
    )
    worst_brand = worst_brand_row[0] if worst_brand_row else "N/A"

    session.close()
    return {
        "total_products_tracked": total_products,
        "historical_products": hist_products,
        "live_products": live_products,
        "documented_historical_cases": hist_flags,
        "confirmed_live_cases": live_flags,
        "total_confirmed_cases": total_flags,
        "avg_ppu_increase_pct": avg_increase,
        "worst_category": worst_category,
        "worst_brand": worst_brand,
    }


@_safe_query
def get_worst_offenders(limit: int = 10, flag_source: Optional[str] = None) -> list:
    """
    Returns ranked list of brands with most shrinkflation flags.
    flag_source: None = all, 'documented_historical', or 'live_detected'
    """
    session = get_session()
    query = (
        session.query(
            Product.brand,
            func.count(ShrinkflationFlag.id).label("flag_count"),
            func.avg(ShrinkflationFlag.price_per_unit_increase_pct).label("avg_ppu_increase"),
        )
        .join(ShrinkflationFlag, ShrinkflationFlag.product_id == Product.id)
    )
    if flag_source:
        query = query.filter(ShrinkflationFlag.flag_source == flag_source)
    results = (
        query.group_by(Product.brand)
        .order_by(desc("flag_count"))
        .limit(limit)
        .all()
    )
    session.close()
    return [
        {
            "brand": r[0],
            "flag_count": r[1],
            "avg_ppu_increase_pct": round(float(r[2]), 1) if r[2] else None,
        }
        for r in results
    ]


@_safe_query
def get_category_breakdown(flag_source: Optional[str] = None) -> list:
    """
    Returns shrinkflation counts by category.
    flag_source: None = all, 'documented_historical', or 'live_detected'
    """
    session = get_session()

    cat_totals = dict(
        session.query(Product.category, func.count(Product.id))
        .group_by(Product.category)
        .all()
    )

    query = (
        session.query(
            Product.category,
            func.count(ShrinkflationFlag.id).label("flags"),
            func.avg(ShrinkflationFlag.price_per_unit_increase_pct).label("avg_ppu_increase"),
        )
        .join(ShrinkflationFlag, ShrinkflationFlag.product_id == Product.id)
    )
    if flag_source:
        query = query.filter(ShrinkflationFlag.flag_source == flag_source)

    cat_flags = query.group_by(Product.category).order_by(desc("flags")).all()
    session.close()

    return [
        {
            "category": r[0],
            "total_products": cat_totals.get(r[0], 0),
            "confirmed_cases": r[1],
            "avg_ppu_increase_pct": round(float(r[2]), 1) if r[2] else None,
        }
        for r in cat_flags
    ]


@_safe_query
def get_recent_flags(days: int = 30, flag_source: Optional[str] = None) -> list:
    """Returns recently flagged products with full details."""
    session = get_session()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    query = (
        session.query(ShrinkflationFlag, Product)
        .join(Product, Product.id == ShrinkflationFlag.product_id)
        .filter(ShrinkflationFlag.detected_at >= cutoff)
    )
    if flag_source:
        query = query.filter(ShrinkflationFlag.flag_source == flag_source)

    results = query.order_by(desc(ShrinkflationFlag.detected_at)).limit(50).all()
    session.close()

    return [
        {
            "product": p.name,
            "brand": p.brand,
            "category": p.category,
            "flag_source": f.flag_source,
            "old_size": f.old_size,
            "new_size": f.new_size,
            "size_unit": f.size_unit,
            "old_price": f"${f.old_price:.2f}" if f.old_price else "N/A",
            "new_price": f"${f.new_price:.2f}" if f.new_price else "N/A",
            "ppu_increase_pct": f"+{f.price_per_unit_increase_pct:.1f}%" if f.price_per_unit_increase_pct else "N/A",
            "has_price_evidence": f.has_price_evidence,
            "severity": f.severity,
            "detected_at": f.detected_at.strftime("%Y-%m-%d") if f.detected_at else "N/A",
        }
        for f, p in results
    ]


@_safe_query
def get_trend_data(weeks: int = 12, flag_source: Optional[str] = None) -> list:
    """Returns week-by-week count of new shrinkflation detections."""
    session = get_session()
    cutoff = datetime.now(timezone.utc) - timedelta(weeks=weeks)

    query = session.query(ShrinkflationFlag).filter(
        ShrinkflationFlag.detected_at >= cutoff
    )
    if flag_source:
        query = query.filter(ShrinkflationFlag.flag_source == flag_source)

    flags = query.order_by(ShrinkflationFlag.detected_at).all()
    session.close()

    from collections import defaultdict
    weekly = defaultdict(int)
    for f in flags:
        if f.detected_at:
            dt = f.detected_at
            monday = dt - timedelta(days=dt.weekday())
            week_key = monday.strftime("%Y-%m-%d")
            weekly[week_key] += 1

    return [{"week": w, "new_flags": c} for w, c in sorted(weekly.items())]


@_safe_query
def get_product_history(product_name: str) -> dict:
    """Returns full snapshot history for a specific product."""
    session = get_session()
    product = (
        session.query(Product)
        .filter(Product.name.ilike(f"%{product_name}%"))
        .first()
    )

    if not product:
        session.close()
        return {"error": f"No product found matching '{product_name}'"}

    snapshots = (
        session.query(ProductSnapshot)
        .filter(ProductSnapshot.product_id == product.id)
        .order_by(ProductSnapshot.scraped_at)
        .all()
    )

    flags = (
        session.query(ShrinkflationFlag)
        .filter(ShrinkflationFlag.product_id == product.id)
        .order_by(ShrinkflationFlag.detected_at)
        .all()
    )
    session.close()

    return {
        "product": product.name,
        "brand": product.brand,
        "category": product.category,
        "data_source": product.data_source,
        "snapshots": [
            {
                "date": s.scraped_at.strftime("%Y-%m-%d") if s.scraped_at else "N/A",
                "size_value": s.size_value,
                "size_unit": s.size_unit,
                "price": f"${s.price:.2f}" if s.price else None,
                "observation_type": s.observation_type,
            }
            for s in snapshots
        ],
        "confirmed_events": [
            {
                "flag_source": f.flag_source,
                "old_size": f.old_size,
                "new_size": f.new_size,
                "size_unit": f.size_unit,
                "ppu_increase_pct": f"+{f.price_per_unit_increase_pct:.1f}%" if f.price_per_unit_increase_pct else "N/A",
                "has_price_evidence": f.has_price_evidence,
                "severity": f.severity,
                "date": f.detected_at.strftime("%Y-%m-%d") if f.detected_at else "N/A",
            }
            for f in flags
        ],
    }


@_safe_query
def get_tracking_funnel() -> dict:
    """
    Returns metrics describing where products are in the detection pipeline.
    Used by the AI agent to explain current detection capacity.
    """
    session = get_session()
    from sqlalchemy import text

    engine = session.bind

    live_products = (
        session.query(func.count(Product.id))
        .filter(Product.data_source.in_(["live_openfoodfacts", "live_kroger"]))
        .scalar() or 0
    )

    # Products with ≥2 real_observed snapshots
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT ps.product_id
                FROM product_snapshots ps
                JOIN products p ON p.id = ps.product_id
                WHERE ps.observation_type = 'real_observed'
                AND p.data_source IN ('live_openfoodfacts', 'live_kroger')
                GROUP BY ps.product_id
                HAVING COUNT(*) >= 2
            ) t
        """))
        with_2_snaps = result.scalar() or 0

        result2 = conn.execute(text("""
            SELECT COUNT(DISTINCT ps.product_id)
            FROM product_snapshots ps
            JOIN products p ON p.id = ps.product_id
            WHERE ps.observation_type = 'real_observed'
            AND ps.price > 0 AND ps.size_value > 0
            AND ps.size_unit_family NOT IN ('unknown', '')
            AND p.data_source IN ('live_openfoodfacts', 'live_kroger')
        """))
        with_enriched = result2.scalar() or 0

    live_confirmed = (
        session.query(func.count(ShrinkflationFlag.id))
        .filter(ShrinkflationFlag.flag_source == "live_detected")
        .scalar() or 0
    )

    session.close()
    return {
        "live_products_tracked": live_products,
        "with_2_or_more_snapshots": with_2_snaps,
        "with_enrichable_snapshot": with_enriched,
        "confirmed_live_cases": live_confirmed,
        "note": (
            "Live detection requires: 2+ snapshots ≥30 days apart, each with confirmed "
            "size AND price, plus a PPU increase. This strict standard means few or zero "
            "confirmed live cases is expected early in deployment."
        ),
    }


@_safe_query
def generate_weekly_report() -> dict:
    """Pulls all stats for a weekly report."""
    return {
        "summary": get_summary_stats(),
        "worst_offenders_all": get_worst_offenders(5),
        "worst_offenders_live": get_worst_offenders(5, flag_source="live_detected"),
        "category_breakdown": get_category_breakdown(),
        "recent_live_flags": get_recent_flags(days=30, flag_source="live_detected"),
        "tracking_funnel": get_tracking_funnel(),
    }


# Tool definitions for the OpenAI function calling API
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_summary_stats",
            "description": (
                "Get high-level summary stats: total products tracked (split by source), "
                "documented historical cases, confirmed live cases, avg PPU increase, "
                "worst category, worst brand."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_worst_offenders",
            "description": "Get ranked list of brands with the most shrinkflation flags.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Number of brands to return (default 10)"},
                    "flag_source": {
                        "type": "string",
                        "description": "Filter by 'documented_historical' or 'live_detected'. Omit for all.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_category_breakdown",
            "description": "Get confirmed shrinkflation counts by category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "flag_source": {
                        "type": "string",
                        "description": "Filter by 'documented_historical' or 'live_detected'. Omit for all.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_flags",
            "description": "Get recently confirmed shrinkflation products.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "How many days back (default 30)"},
                    "flag_source": {
                        "type": "string",
                        "description": "Filter by 'documented_historical' or 'live_detected'. Omit for all.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_trend_data",
            "description": "Get week-by-week count of new shrinkflation detections.",
            "parameters": {
                "type": "object",
                "properties": {
                    "weeks": {"type": "integer", "description": "How many weeks of history (default 12)"},
                    "flag_source": {
                        "type": "string",
                        "description": "Filter by 'documented_historical' or 'live_detected'. Omit for all.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_history",
            "description": "Get full snapshot history for a specific product.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {"type": "string", "description": "Product name (partial match)"},
                },
                "required": ["product_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_tracking_funnel",
            "description": (
                "Get live tracking funnel metrics: how many products are tracked, "
                "how many have enough snapshots, how many are enrichable, "
                "how many confirmed live detections exist."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_weekly_report",
            "description": "Compile all stats and data needed for a comprehensive weekly shrinkflation report.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

TOOL_FUNCTIONS = {
    "get_summary_stats": lambda **_: get_summary_stats(),
    "get_worst_offenders": lambda limit=10, flag_source=None, **_: get_worst_offenders(limit, flag_source),
    "get_category_breakdown": lambda flag_source=None, **_: get_category_breakdown(flag_source),
    "get_recent_flags": lambda days=30, flag_source=None, **_: get_recent_flags(days, flag_source),
    "get_trend_data": lambda weeks=12, flag_source=None, **_: get_trend_data(weeks, flag_source),
    "get_product_history": lambda product_name="", **_: get_product_history(product_name),
    "get_tracking_funnel": lambda **_: get_tracking_funnel(),
    "generate_weekly_report": lambda **_: generate_weekly_report(),
}
