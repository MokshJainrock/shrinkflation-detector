"""
Agent tool definitions — functions the AI agent can call to query the database.
Each returns a dict/list that gets serialized to JSON for the agent.
"""

import json
from datetime import datetime, timezone, timedelta

from sqlalchemy import func, desc

from db.models import Product, ProductSnapshot, ShrinkflationFlag, get_session


def _safe_query(fn):
    """Decorator that catches DB errors and returns a clean error message."""
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            return {"error": f"Query failed: {str(e)}. The database may be empty — try running --seed first."}
    return wrapper


@_safe_query
def get_summary_stats() -> dict:
    """Returns total products tracked, total shrinks detected, avg hidden price increase, worst category, worst brand."""
    session = get_session()

    total_products = session.query(func.count(Product.id)).scalar() or 0
    total_shrinks = (
        session.query(func.count(ShrinkflationFlag.id))
        .scalar() or 0
    )
    avg_increase = (
        session.query(func.avg(ShrinkflationFlag.real_price_increase_pct))
        .scalar()
    )
    avg_increase = round(float(avg_increase), 1) if avg_increase else 0.0

    # Worst category (most flags overall)
    worst_cat_row = (
        session.query(Product.category, func.count(ShrinkflationFlag.id).label("cnt"))
        .join(ShrinkflationFlag, ShrinkflationFlag.product_id == Product.id)
        .group_by(Product.category)
        .order_by(desc("cnt"))
        .first()
    )
    worst_category = worst_cat_row[0] if worst_cat_row else "N/A"

    # Worst brand (most flags overall)
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
        "shrinks_detected": total_shrinks,
        "avg_hidden_price_increase_pct": avg_increase,
        "worst_category": worst_category,
        "worst_brand": worst_brand,
    }


@_safe_query
def get_worst_offenders(limit: int = 10) -> list[dict]:
    """Returns ranked list of brands with most shrinkflation flags."""
    session = get_session()
    results = (
        session.query(
            Product.brand,
            func.count(ShrinkflationFlag.id).label("flag_count"),
            func.avg(ShrinkflationFlag.real_price_increase_pct).label("avg_increase"),
        )
        .join(ShrinkflationFlag, ShrinkflationFlag.product_id == Product.id)
        .group_by(Product.brand)
        .order_by(desc("flag_count"))
        .limit(limit)
        .all()
    )
    session.close()
    return [
        {
            "brand": r[0],
            "flag_count": r[1],
            "avg_real_price_increase_pct": round(float(r[2]), 1) if r[2] else 0,
        }
        for r in results
    ]


@_safe_query
def get_category_breakdown() -> list[dict]:
    """Returns shrinkflation rate by category."""
    session = get_session()

    # Total products per category
    cat_totals = dict(
        session.query(Product.category, func.count(Product.id))
        .group_by(Product.category)
        .all()
    )

    # Flags per category
    cat_flags = (
        session.query(
            Product.category,
            func.count(ShrinkflationFlag.id).label("flags"),
            func.avg(ShrinkflationFlag.real_price_increase_pct).label("avg_increase"),
        )
        .join(ShrinkflationFlag, ShrinkflationFlag.product_id == Product.id)
        .group_by(Product.category)
        .order_by(desc("flags"))
        .all()
    )
    session.close()

    return [
        {
            "category": r[0],
            "total_products": cat_totals.get(r[0], 0),
            "shrinkflation_flags": r[1],
            "shrinkflation_rate_pct": round(r[1] / cat_totals[r[0]] * 100, 1) if cat_totals.get(r[0]) else 0,
            "avg_size_reduction_pct": round(float(r[2]), 1) if r[2] else 0,
        }
        for r in cat_flags
    ]


@_safe_query
def get_recent_flags(days: int = 7, category: str | None = None, brand: str | None = None) -> list[dict]:
    """Returns recently flagged products with full details."""
    session = get_session()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    query = (
        session.query(ShrinkflationFlag, Product)
        .join(Product, Product.id == ShrinkflationFlag.product_id)
        .filter(ShrinkflationFlag.detected_at >= cutoff)
    )

    if category:
        query = query.filter(Product.category == category)
    if brand:
        query = query.filter(Product.brand == brand)

    results = query.order_by(desc(ShrinkflationFlag.detected_at)).limit(50).all()
    session.close()

    return [
        {
            "product": p.name,
            "brand": p.brand,
            "category": p.category,
            "old_size": f.old_size,
            "new_size": f.new_size,
            "old_price": f"${f.old_price:.2f}" if f.old_price else "N/A",
            "new_price": f"${f.new_price:.2f}" if f.new_price else "N/A",
            "real_price_increase_pct": f"+{f.real_price_increase_pct:.1f}%",
            "severity": f.severity,
            "detected_at": f.detected_at.strftime("%Y-%m-%d"),
        }
        for f, p in results
    ]


@_safe_query
def get_trend_data(weeks: int = 12) -> list[dict]:
    """Returns week-by-week count of new shrinkflation detections."""
    session = get_session()
    cutoff = datetime.now(timezone.utc) - timedelta(weeks=weeks)

    flags = (
        session.query(ShrinkflationFlag)
        .filter(ShrinkflationFlag.detected_at >= cutoff)
        .order_by(ShrinkflationFlag.detected_at)
        .all()
    )
    session.close()

    # Group by week in Python (SQLite-compatible)
    from collections import defaultdict
    weekly = defaultdict(int)
    for f in flags:
        if f.detected_at:
            # Get Monday of that week
            dt = f.detected_at
            monday = dt - timedelta(days=dt.weekday())
            week_key = monday.strftime("%Y-%m-%d")
            weekly[week_key] += 1

    return [
        {"week": w, "new_flags": c}
        for w, c in sorted(weekly.items())
    ]


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
        "snapshots": [
            {
                "date": s.scraped_at.strftime("%Y-%m-%d"),
                "size_value": s.size_value,
                "size_unit": s.size_unit,
                "price": f"${s.price:.2f}" if s.price else None,
            }
            for s in snapshots
        ],
        "shrinkflation_events": [
            {
                "old_size": f.old_size,
                "new_size": f.new_size,
                "real_increase_pct": f"+{f.real_price_increase_pct:.1f}%",
                "severity": f.severity,
                "date": f.detected_at.strftime("%Y-%m-%d"),
            }
            for f in flags
        ],
    }


@_safe_query
def compare_categories(cat1: str, cat2: str) -> dict:
    """Side-by-side comparison of shrinkflation rates between two categories."""
    session = get_session()

    def stats_for(cat):
        total = session.query(func.count(Product.id)).filter(Product.category == cat).scalar() or 0
        flags = (
            session.query(func.count(ShrinkflationFlag.id))
            .join(Product, Product.id == ShrinkflationFlag.product_id)
            .filter(Product.category == cat)
            .scalar() or 0
        )
        avg_inc = (
            session.query(func.avg(ShrinkflationFlag.real_price_increase_pct))
            .join(Product, Product.id == ShrinkflationFlag.product_id)
            .filter(Product.category == cat)
            .scalar()
        )
        return {
            "category": cat,
            "total_products": total,
            "shrinkflation_flags": flags,
            "rate_pct": round(flags / total * 100, 1) if total else 0,
            "avg_real_price_increase_pct": round(float(avg_inc), 1) if avg_inc else 0,
        }

    result = {cat1: stats_for(cat1), cat2: stats_for(cat2)}
    session.close()
    return result


@_safe_query
def generate_weekly_report() -> dict:
    """Pulls all stats for a weekly report."""
    return {
        "summary": get_summary_stats(),
        "worst_offenders": get_worst_offenders(5),
        "category_breakdown": get_category_breakdown(),
        "recent_flags": get_recent_flags(days=7),
        "trend": get_trend_data(weeks=4),
    }


# Tool definitions for the OpenAI function calling API
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_summary_stats",
            "description": "Get high-level summary stats: total products tracked, shrinks detected this month, avg hidden price increase, worst category, worst brand.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_worst_offenders",
            "description": "Get ranked list of brands with the most shrinkflation flags and their average real price increase.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Number of brands to return (default 10)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_category_breakdown",
            "description": "Get shrinkflation rate and average size reduction by product category.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_flags",
            "description": "Get recently flagged shrinkflation products with full details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "How many days back to look (default 7)"},
                    "category": {"type": "string", "description": "Filter by category"},
                    "brand": {"type": "string", "description": "Filter by brand"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_trend_data",
            "description": "Get week-by-week count of new shrinkflation detections over time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "weeks": {"type": "integer", "description": "How many weeks of history (default 12)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_history",
            "description": "Get full snapshot history for a specific product showing size and price changes over time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {"type": "string", "description": "Product name to search for (partial match)"},
                },
                "required": ["product_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_categories",
            "description": "Compare shrinkflation rates between two product categories side by side.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cat1": {"type": "string", "description": "First category name"},
                    "cat2": {"type": "string", "description": "Second category name"},
                },
                "required": ["cat1", "cat2"],
            },
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


# Map tool names to functions
TOOL_FUNCTIONS = {
    "get_summary_stats": lambda **_: get_summary_stats(),
    "get_worst_offenders": lambda limit=10, **_: get_worst_offenders(limit),
    "get_category_breakdown": lambda **_: get_category_breakdown(),
    "get_recent_flags": lambda days=7, category=None, brand=None, **_: get_recent_flags(days, category, brand),
    "get_trend_data": lambda weeks=12, **_: get_trend_data(weeks),
    "get_product_history": lambda product_name="", **_: get_product_history(product_name),
    "compare_categories": lambda cat1="", cat2="", **_: compare_categories(cat1, cat2),
    "generate_weekly_report": lambda **_: generate_weekly_report(),
}
