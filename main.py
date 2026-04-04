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
    python main.py --seed         Pull live data from Open Food Facts + Open Prices APIs
    python main.py --reseed       Wipe DB and re-seed from live APIs
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime


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
        print(f"Insight generation skipped (set OPENAI_API_KEY): {e}")


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


def cmd_reseed():
    """Wipe DB and re-populate entirely from live Open Food Facts + Open Prices APIs."""
    from db.models import Base, get_engine, init_db
    engine = get_engine()
    Base.metadata.drop_all(engine)
    print("Database wiped.")
    init_db()
    cmd_seed()


def cmd_seed():
    """
    Populate the database using live API calls only.

    Data sources (all real, no fabricated data):
    - Open Food Facts API  — real product sizes and barcodes (openfoodfacts.org)
    - Open Prices API      — crowd-sourced real retail prices from grocery receipts
    """
    from scraper.product_scanner import run_full_scan
    print("Starting live data scan from Open Food Facts + Open Prices APIs...")
    print("  Step 1 — Scanning verified shrinkflation cases via OFF API")
    print("  Step 2 — Discovering newly changed products from OFF live feed")
    run_full_scan(batch_size=200, scan_recent=True)


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
    parser.add_argument("--reseed", action="store_true", help="Wipe DB and re-seed fresh")

    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
        return

    if args.init:
        cmd_init()
    if args.reseed:
        cmd_reseed()
    elif args.seed:
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
