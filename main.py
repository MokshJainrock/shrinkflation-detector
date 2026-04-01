"""
Shrinkflation Detector — main entrypoint.

Usage:
    python main.py --init         Create all DB tables
    python main.py --scrape       Run scrapers once
    python main.py --analyze      Run detector on all products
    python main.py --insight      Generate and print daily AI insight
    python main.py --report       Generate and print weekly AI report
    python main.py --all          Scrape + analyze + generate insight
    python main.py --schedule     Run --all every 24 hours automatically
    python main.py --dashboard    Launch Streamlit on localhost:8501
    python main.py --seed         Load sample data for demo purposes
"""

import argparse
import subprocess
import sys
import time
import random
from datetime import datetime, timezone, timedelta


def cmd_init():
    from db.models import init_db
    init_db()


def cmd_scrape():
    from scraper.openfoodfacts import scrape_openfoodfacts
    from scraper.kroger import scrape_kroger
    scrape_openfoodfacts()
    scrape_kroger()


def cmd_analyze():
    from analysis.detector import run_detection
    run_detection()


def cmd_insight():
    from agent.analyst import generate_daily_insight
    print("\nGenerating daily insight...\n")
    insight = generate_daily_insight()
    print(insight)


def cmd_report():
    from agent.analyst import generate_weekly_report
    print("\nGenerating weekly report...\n")
    report = generate_weekly_report()
    print(report)


def cmd_all():
    cmd_scrape()
    cmd_analyze()
    try:
        cmd_insight()
    except Exception as e:
        print(f"Insight generation skipped (set ANTHROPIC_API_KEY): {e}")


def cmd_schedule():
    import schedule as sched
    print("Scheduler started. Will run scrape + analyze + insight every 24 hours.")
    print("Press Ctrl+C to stop.\n")
    cmd_all()
    sched.every(24).hours.do(cmd_all)
    while True:
        sched.run_pending()
        time.sleep(60)


def cmd_dashboard():
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "dashboard/app.py",
        "--server.headless", "true",
    ])


def cmd_seed():
    """Generate realistic sample data for demo purposes. Idempotent."""
    from db.models import (
        Product, ProductSnapshot, ShrinkflationFlag, AgentInsight,
        get_session, init_db,
    )

    init_db()
    session = get_session()

    # Check if seed data already exists
    existing = session.query(Product).count()
    if existing > 0:
        print(f"Database already has {existing} products. Seed is idempotent — skipping.")
        session.close()
        return

    print("Seeding database with realistic sample data...")

    # ---- Sample Products ----
    SEED_PRODUCTS = [
        # (name, brand, category, initial_size, size_unit, initial_price)
        ("Classic Lay's Potato Chips", "Frito-Lay", "chips", 10.0, "oz", 4.29),
        ("Doritos Nacho Cheese", "Frito-Lay", "chips", 9.25, "oz", 4.99),
        ("Tostitos Scoops", "Frito-Lay", "chips", 10.0, "oz", 4.49),
        ("Ruffles Original", "Frito-Lay", "chips", 8.5, "oz", 4.29),
        ("Cheetos Crunchy", "Frito-Lay", "chips", 8.5, "oz", 4.49),
        ("Frosted Flakes", "Kellogg's", "cereal", 19.2, "oz", 5.49),
        ("Froot Loops", "Kellogg's", "cereal", 14.7, "oz", 4.99),
        ("Rice Krispies", "Kellogg's", "cereal", 18.0, "oz", 5.29),
        ("Corn Flakes", "Kellogg's", "cereal", 18.0, "oz", 4.79),
        ("Cheerios Original", "General Mills", "cereal", 18.0, "oz", 5.49),
        ("Honey Nut Cheerios", "General Mills", "cereal", 15.4, "oz", 5.49),
        ("Lucky Charms", "General Mills", "cereal", 14.9, "oz", 5.29),
        ("Cinnamon Toast Crunch", "General Mills", "cereal", 16.8, "oz", 5.29),
        ("Tropicana Orange Juice", "Tropicana", "juice", 52.0, "fl oz", 4.99),
        ("Tropicana Apple Juice", "Tropicana", "juice", 52.0, "fl oz", 4.79),
        ("Minute Maid Lemonade", "Coca-Cola", "juice", 59.0, "fl oz", 3.49),
        ("Oreo Original Cookies", "Nabisco", "cookies", 14.3, "oz", 5.49),
        ("Chips Ahoy Original", "Nabisco", "cookies", 13.0, "oz", 4.99),
        ("Nutter Butter", "Nabisco", "cookies", 16.0, "oz", 4.49),
        ("Ritz Crackers Original", "Nabisco", "crackers", 13.7, "oz", 4.79),
        ("Wheat Thins Original", "Nabisco", "crackers", 9.1, "oz", 4.49),
        ("Triscuit Original", "Nabisco", "crackers", 8.5, "oz", 4.29),
        ("Yoplait Original Strawberry", "General Mills", "yogurt", 6.0, "oz", 0.89),
        ("Chobani Greek Yogurt", "Chobani", "yogurt", 5.3, "oz", 1.49),
        ("Dannon Fruit on Bottom", "Dannon", "yogurt", 5.3, "oz", 1.19),
        ("Folgers Classic Roast", "Folgers", "coffee", 30.5, "oz", 10.99),
        ("Folgers 1850 Bold", "Folgers", "coffee", 12.0, "oz", 8.99),
        ("Maxwell House Original", "Kraft Heinz", "coffee", 30.6, "oz", 9.99),
        ("Barilla Spaghetti", "Barilla", "pasta", 16.0, "oz", 1.99),
        ("Barilla Penne", "Barilla", "pasta", 16.0, "oz", 1.99),
        ("Ronzoni Rotini", "Riviana Foods", "pasta", 16.0, "oz", 1.79),
        ("Dove Body Wash", "Unilever", "soap", 22.0, "fl oz", 7.99),
        ("Irish Spring Bar Soap", "Colgate-Palmolive", "soap", 3.7, "oz", 1.29),
        ("Tide Original Detergent", "P&G", "detergent", 92.0, "fl oz", 12.99),
        ("Gain Original Detergent", "P&G", "detergent", 88.0, "fl oz", 11.99),
        ("All Free Clear Detergent", "Henkel", "detergent", 88.0, "fl oz", 10.99),
        ("Heinz Tomato Ketchup", "Kraft Heinz", "ketchup", 38.0, "oz", 5.49),
        ("French's Classic Mustard", "McCormick", "ketchup", 14.0, "oz", 2.99),
        ("Hellmann's Real Mayo", "Unilever", "mayo", 30.0, "fl oz", 5.99),
        ("Duke's Real Mayo", "Sauer Brands", "mayo", 32.0, "fl oz", 4.99),
        ("Tillamook Cheddar", "Tillamook", "cheese", 8.0, "oz", 4.99),
        ("Kraft Singles American", "Kraft Heinz", "cheese", 16.0, "oz", 5.49),
        ("Philadelphia Cream Cheese", "Kraft Heinz", "cheese", 8.0, "oz", 3.99),
        ("Wonder Bread White", "Flowers Foods", "bread", 20.0, "oz", 3.99),
        ("Nature's Own Honey Wheat", "Flowers Foods", "bread", 20.0, "oz", 4.49),
        ("Sara Lee Artesano", "Bimbo Bakeries", "bread", 20.0, "oz", 4.29),
        ("Häagen-Dazs Vanilla", "Nestlé", "ice cream", 14.0, "fl oz", 5.99),
        ("Ben & Jerry's Half Baked", "Unilever", "ice cream", 16.0, "fl oz", 6.49),
        ("Breyers Natural Vanilla", "Unilever", "ice cream", 48.0, "fl oz", 5.99),
        ("Tillamook Ice Cream", "Tillamook", "ice cream", 48.0, "fl oz", 6.99),
    ]

    now = datetime.now(timezone.utc)
    products_created = []

    for name, brand, category, size, unit, price in SEED_PRODUCTS:
        p = Product(
            name=name,
            brand=brand,
            category=category,
            barcode=f"00{random.randint(10000, 99999)}{random.randint(10000, 99999)}",
            retailer="openfoodfacts",
        )
        session.add(p)
        session.flush()
        products_created.append((p, size, unit, price))

    # ---- Generate 90 days of snapshots ----
    # Some products will shrink, most stay stable
    SHRINK_INDICES = random.sample(range(len(products_created)), 25)

    for idx, (product, base_size, unit, base_price) in enumerate(products_created):
        will_shrink = idx in SHRINK_INDICES

        if will_shrink:
            # Pick a shrink day between 30-60 days ago
            shrink_day = random.randint(30, 60)
            size_reduction = random.uniform(0.03, 0.15)  # 3-15% reduction
            price_change = random.uniform(-0.01, 0.05)  # -1% to +5% price change
        else:
            shrink_day = None
            size_reduction = 0
            price_change = 0

        for day_offset in range(90, -1, -1):
            snapshot_date = now - timedelta(days=day_offset)

            # Compute size for this day
            if will_shrink and day_offset < shrink_day:
                current_size = round(base_size * (1 - size_reduction), 2)
            else:
                current_size = base_size

            # Compute price (slight daily jitter)
            if will_shrink and day_offset < shrink_day:
                current_price = round(base_price * (1 + price_change) + random.uniform(-0.05, 0.05), 2)
            else:
                current_price = round(base_price + random.uniform(-0.05, 0.05), 2)

            ppu = round(current_price / current_size, 4) if current_size > 0 else None

            snapshot = ProductSnapshot(
                product_id=product.id,
                size_value=current_size,
                size_unit=unit,
                price=current_price,
                price_per_unit=ppu,
                scraped_at=snapshot_date,
            )
            session.add(snapshot)

    session.commit()

    # ---- Generate shrinkflation flags for the shrunk products ----
    flagged_count = 0
    for idx in SHRINK_INDICES:
        product, base_size, unit, base_price = products_created[idx]

        shrink_day = random.randint(30, 60)
        size_reduction = random.uniform(0.03, 0.15)
        price_change = random.uniform(-0.01, 0.05)

        new_size = round(base_size * (1 - size_reduction), 2)
        new_price = round(base_price * (1 + price_change), 2)

        old_ppu = base_price / base_size
        new_ppu = new_price / new_size
        real_increase = ((new_ppu - old_ppu) / old_ppu) * 100

        if real_increase > 5:
            severity = "HIGH"
        elif real_increase > 2:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        flag = ShrinkflationFlag(
            product_id=product.id,
            old_size=base_size,
            new_size=new_size,
            old_price=base_price,
            new_price=new_price,
            real_price_increase_pct=round(real_increase, 2),
            severity=severity,
            detected_at=now - timedelta(days=random.randint(1, 30)),
            retailer="openfoodfacts",
        )
        session.add(flag)
        flagged_count += 1

    # ---- Seed a sample AI insight ----
    sample_insight = AgentInsight(
        insight_type="daily",
        content=(
            "Cereal brands reduced package sizes 3x more than any other category this week, "
            "with Kellogg's leading at 3 new shrinkflation flags. Frosted Flakes dropped from "
            "19.2 oz to 16.9 oz while the price increased by $0.20 — a hidden +15.8% price "
            "increase per ounce. Frito-Lay remains the overall worst offender with 5 flagged "
            "products this month."
        ),
        generated_at=now - timedelta(hours=6),
    )
    session.add(sample_insight)

    session.commit()
    session.close()

    print(f"Seed complete: {len(products_created)} products, ~{len(products_created) * 91} snapshots, "
          f"{flagged_count} shrinkflation flags, 1 AI insight")


def main():
    parser = argparse.ArgumentParser(description="Shrinkflation Detector")
    parser.add_argument("--init", action="store_true", help="Initialize the database")
    parser.add_argument("--scrape", action="store_true", help="Run scrapers")
    parser.add_argument("--analyze", action="store_true", help="Run detector")
    parser.add_argument("--insight", action="store_true", help="Generate daily AI insight")
    parser.add_argument("--report", action="store_true", help="Generate weekly AI report")
    parser.add_argument("--all", action="store_true", help="Scrape + analyze + insight")
    parser.add_argument("--schedule", action="store_true", help="Run on a daily schedule")
    parser.add_argument("--dashboard", action="store_true", help="Launch Streamlit dashboard")
    parser.add_argument("--seed", action="store_true", help="Load sample data for demo")

    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
        return

    if args.init:
        cmd_init()
    if args.seed:
        cmd_seed()
    if args.scrape:
        cmd_scrape()
    if args.analyze:
        cmd_analyze()
    if args.insight:
        cmd_insight()
    if args.report:
        cmd_report()
    if args.all:
        cmd_all()
    if args.schedule:
        cmd_schedule()
    if args.dashboard:
        cmd_dashboard()


if __name__ == "__main__":
    main()
