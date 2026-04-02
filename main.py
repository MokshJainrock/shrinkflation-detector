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

    print("Seeding database with 5,000+ products...")

    # ---- Brand/Category/Product templates ----
    BRANDS_BY_CATEGORY = {
        "chips": {
            "brands": ["Frito-Lay", "Pringles", "Kettle Brand", "Cape Cod", "Utz", "Herr's", "Wise", "Boulder Canyon", "Popchips", "Terra"],
            "products": ["Potato Chips", "Tortilla Chips", "Kettle Chips", "BBQ Chips", "Sour Cream & Onion", "Salt & Vinegar", "Cheese Puffs", "Corn Chips", "Veggie Chips", "Wavy Chips", "Ranch Chips", "Jalapeno Chips"],
            "size_range": (5.0, 13.0), "unit": "oz", "price_range": (3.49, 5.99),
        },
        "cereal": {
            "brands": ["Kellogg's", "General Mills", "Post", "Quaker", "Nature's Path", "Cascadian Farm", "Barbara's", "Kashi", "Magic Spoon", "Three Wishes"],
            "products": ["Frosted Flakes", "Corn Flakes", "Cheerios", "Honey Nut O's", "Granola", "Bran Flakes", "Fruit Loops", "Cocoa Puffs", "Rice Crispies", "Oat Squares", "Muesli", "Raisin Bran"],
            "size_range": (10.0, 24.0), "unit": "oz", "price_range": (3.99, 7.49),
        },
        "juice": {
            "brands": ["Tropicana", "Minute Maid", "Simply", "Ocean Spray", "Welch's", "Mott's", "V8", "Naked", "Bolthouse Farms", "Evolution Fresh"],
            "products": ["Orange Juice", "Apple Juice", "Grape Juice", "Cranberry Juice", "Lemonade", "Fruit Punch", "Green Juice", "Carrot Juice", "Mango Juice", "Pineapple Juice"],
            "size_range": (32.0, 64.0), "unit": "fl oz", "price_range": (3.29, 6.99),
        },
        "cookies": {
            "brands": ["Nabisco", "Pepperidge Farm", "Keebler", "Girl Scouts", "Tate's", "Enjoy Life", "Lenny & Larry's", "Voortman", "Archway", "Famous Amos"],
            "products": ["Chocolate Chip", "Oreos", "Shortbread", "Oatmeal Raisin", "Peanut Butter", "Double Chocolate", "Snickerdoodle", "Sugar Cookie", "Macaroons", "Biscotti", "Wafer Cookies", "Sandwich Cookies"],
            "size_range": (7.0, 18.0), "unit": "oz", "price_range": (3.49, 6.49),
        },
        "crackers": {
            "brands": ["Nabisco", "Keebler", "Pepperidge Farm", "Lance", "Triscuit", "Annie's", "Mary's Gone", "Simple Mills", "Back to Nature", "Crunchmaster"],
            "products": ["Saltines", "Wheat Crackers", "Ritz", "Graham Crackers", "Cheese Crackers", "Water Crackers", "Multigrain", "Pita Chips", "Rice Crackers", "Seed Crackers"],
            "size_range": (6.0, 16.0), "unit": "oz", "price_range": (3.29, 5.99),
        },
        "yogurt": {
            "brands": ["Chobani", "Dannon", "Yoplait", "Fage", "Siggi's", "Stonyfield", "Oikos", "Noosa", "Tillamook", "Wallaby"],
            "products": ["Greek Yogurt", "Strawberry", "Blueberry", "Vanilla", "Peach", "Mixed Berry", "Honey", "Plain", "Coconut", "Mango", "Key Lime", "Raspberry"],
            "size_range": (4.0, 32.0), "unit": "oz", "price_range": (0.89, 5.99),
        },
        "coffee": {
            "brands": ["Folgers", "Maxwell House", "Starbucks", "Dunkin'", "Peet's", "Lavazza", "Illy", "Green Mountain", "Death Wish", "Community Coffee"],
            "products": ["Classic Roast", "Dark Roast", "Medium Roast", "French Roast", "Colombian", "Breakfast Blend", "Espresso", "Decaf", "House Blend", "Pike Place"],
            "size_range": (10.0, 36.0), "unit": "oz", "price_range": (6.99, 14.99),
        },
        "pasta": {
            "brands": ["Barilla", "Ronzoni", "De Cecco", "Mueller's", "San Giorgio", "Banza", "Jovial", "DeLallo", "Racconto", "Colavita"],
            "products": ["Spaghetti", "Penne", "Rotini", "Fettuccine", "Rigatoni", "Angel Hair", "Linguine", "Farfalle", "Ziti", "Macaroni", "Orzo", "Lasagna Sheets"],
            "size_range": (12.0, 16.0), "unit": "oz", "price_range": (1.49, 3.99),
        },
        "soap": {
            "brands": ["Dove", "Irish Spring", "Dial", "Ivory", "Olay", "Dr. Bronner's", "Mrs. Meyer's", "Method", "Softsoap", "Cetaphil"],
            "products": ["Body Wash", "Bar Soap", "Hand Soap", "Liquid Soap", "Shower Gel", "Moisturizing Wash", "Antibacterial Soap", "Exfoliating Wash", "Sensitive Skin", "Charcoal Wash"],
            "size_range": (3.0, 24.0), "unit": "oz", "price_range": (1.29, 9.99),
        },
        "detergent": {
            "brands": ["Tide", "Gain", "All", "Persil", "Arm & Hammer", "Seventh Generation", "Method", "Mrs. Meyer's", "ECOS", "Biokleen"],
            "products": ["Original", "Free & Clear", "Sport", "Fresh Scent", "Pods", "Liquid", "Powder", "HE Formula", "Color Safe", "Sensitive"],
            "size_range": (40.0, 100.0), "unit": "fl oz", "price_range": (7.99, 15.99),
        },
        "ketchup": {
            "brands": ["Heinz", "Hunt's", "French's", "Sir Kensington's", "Annie's", "Primal Kitchen", "Organicville", "Red Gold", "Del Monte", "Portland Ketchup"],
            "products": ["Tomato Ketchup", "Organic Ketchup", "Spicy Ketchup", "No Sugar Added", "Yellow Mustard", "Dijon Mustard", "Honey Mustard", "BBQ Sauce", "Hot Sauce", "Sriracha"],
            "size_range": (12.0, 40.0), "unit": "oz", "price_range": (2.49, 6.99),
        },
        "mayo": {
            "brands": ["Hellmann's", "Duke's", "Kraft", "Sir Kensington's", "Primal Kitchen", "Just Mayo", "Blue Plate", "Kewpie", "Spectrum", "Trader Joe's"],
            "products": ["Real Mayo", "Light Mayo", "Olive Oil Mayo", "Avocado Oil Mayo", "Vegan Mayo", "Chipotle Mayo", "Garlic Aioli", "Tartar Sauce", "Ranch Dressing", "Caesar Dressing"],
            "size_range": (12.0, 36.0), "unit": "fl oz", "price_range": (3.49, 7.99),
        },
        "cheese": {
            "brands": ["Kraft", "Tillamook", "Sargento", "Cabot", "Cracker Barrel", "Borden", "Organic Valley", "Kerrygold", "Laughing Cow", "Babybel"],
            "products": ["Cheddar", "Mozzarella", "Swiss", "Pepper Jack", "Provolone", "Gouda", "Cream Cheese", "American Singles", "String Cheese", "Parmesan", "Colby Jack", "Brie"],
            "size_range": (5.0, 24.0), "unit": "oz", "price_range": (2.99, 8.99),
        },
        "bread": {
            "brands": ["Wonder", "Nature's Own", "Sara Lee", "Dave's Killer Bread", "Pepperidge Farm", "Arnold", "Franz", "King's Hawaiian", "Martin's", "Oroweat"],
            "products": ["White Bread", "Wheat Bread", "Sourdough", "Multigrain", "Rye", "Brioche", "Italian", "Potato Rolls", "Hamburger Buns", "Hot Dog Buns", "English Muffins", "Bagels"],
            "size_range": (13.0, 24.0), "unit": "oz", "price_range": (2.99, 6.49),
        },
        "ice cream": {
            "brands": ["Häagen-Dazs", "Ben & Jerry's", "Breyers", "Tillamook", "Blue Bunny", "Turkey Hill", "Edy's", "Talenti", "So Delicious", "Halo Top"],
            "products": ["Vanilla", "Chocolate", "Strawberry", "Cookie Dough", "Mint Chocolate Chip", "Rocky Road", "Butter Pecan", "Coffee", "Cookies & Cream", "Salted Caramel", "Moose Tracks", "Pistachio"],
            "size_range": (14.0, 56.0), "unit": "fl oz", "price_range": (3.99, 7.99),
        },
    }

    now = datetime.now(timezone.utc)
    products_created = []
    product_count = 0

    SIZE_VARIANTS = ["Snack Size", "Regular", "Family Size", "Value Pack"]
    seen_names = set()

    for category, info in BRANDS_BY_CATEGORY.items():
        for brand in info["brands"]:
            for product_name in info["products"]:
                # Create multiple size variants per product
                for variant in SIZE_VARIANTS:
                    full_name = f"{brand} {product_name} {variant}"
                    key = (full_name, brand, "openfoodfacts")
                    if key in seen_names:
                        continue
                    seen_names.add(key)

                    lo, hi = info["size_range"]
                    # Variants affect size
                    mult = {"Snack Size": 0.5, "Regular": 1.0, "Family Size": 1.8, "Value Pack": 2.5}[variant]
                    size = round(random.uniform(lo, hi) * mult, 1)
                    plo, phi = info["price_range"]
                    price = round(random.uniform(plo, phi) * mult * random.uniform(0.85, 1.0), 2)

                    p = Product(
                        name=full_name,
                        brand=brand,
                        category=category,
                        barcode=f"00{random.randint(10000, 99999)}{random.randint(10000, 99999)}",
                        retailer="openfoodfacts",
                    )
                    session.add(p)
                    session.flush()
                    products_created.append((p, size, info["unit"], price))
                    product_count += 1

    print(f"  Created {product_count} products across {len(BRANDS_BY_CATEGORY)} categories")

    # ---- Decide which products will shrink (~30%) ----
    num_shrink = int(len(products_created) * 0.30)
    SHRINK_INDICES = set(random.sample(range(len(products_created)), num_shrink))

    print(f"  Generating snapshots for {product_count} products (7 weekly snapshots each)...")

    # Generate 7 weekly snapshots (not 91 daily — much faster)
    batch_count = 0
    for idx, (product, base_size, unit, base_price) in enumerate(products_created):
        will_shrink = idx in SHRINK_INDICES

        if will_shrink:
            shrink_week = random.randint(2, 5)
            size_reduction = random.uniform(0.03, 0.15)
            price_change = random.uniform(-0.01, 0.06)
        else:
            shrink_week = None
            size_reduction = 0
            price_change = 0

        for week in range(7):
            snapshot_date = now - timedelta(weeks=6 - week)

            if will_shrink and week >= shrink_week:
                current_size = round(base_size * (1 - size_reduction), 2)
                current_price = round(base_price * (1 + price_change) + random.uniform(-0.05, 0.05), 2)
            else:
                current_size = base_size
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
            batch_count += 1

        # Commit in batches of 5000 to avoid memory issues
        if batch_count >= 5000:
            session.commit()
            batch_count = 0

    session.commit()
    print(f"  Created {product_count * 7} snapshots")

    # ---- Generate shrinkflation flags ----
    flagged_count = 0
    for idx in SHRINK_INDICES:
        product, base_size, unit, base_price = products_created[idx]

        size_reduction = random.uniform(0.03, 0.15)
        price_change = random.uniform(-0.01, 0.06)

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
            detected_at=now - timedelta(days=random.randint(1, 42)),
            retailer="openfoodfacts",
        )
        session.add(flag)
        flagged_count += 1

    # ---- Sample AI insight ----
    sample_insight = AgentInsight(
        insight_type="daily",
        content=(
            f"Across {product_count:,} tracked products, {flagged_count:,} show signs of shrinkflation "
            f"this month — a {flagged_count/product_count*100:.1f}% detection rate. Ice cream leads "
            f"all categories with brands like Häagen-Dazs and Ben & Jerry's quietly reducing pint "
            f"sizes while maintaining premium prices. Kellogg's cereals have the highest average "
            f"hidden price increase at +12.3% per ounce. Frito-Lay alone accounts for 8% of all "
            f"shrinkflation flags across the chip category."
        ),
        generated_at=now - timedelta(hours=2),
    )
    session.add(sample_insight)

    session.commit()
    session.close()

    print(f"\nSeed complete: {product_count:,} products, {product_count * 7:,} snapshots, "
          f"{flagged_count:,} shrinkflation flags")


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
