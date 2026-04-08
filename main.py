"""
Shrinkflation Detector — main entrypoint.

Usage:
    python main.py --init         Create all DB tables
    python main.py --scrape       Run one ingestion tick (OFF + Kroger) once
    python main.py --analyze      Run the strict evidence-based detector
    python main.py --insight      Generate and print daily AI insight
    python main.py --report       Generate and print weekly AI report
    python main.py --all          Scrape + analyze + generate insight
    python main.py --schedule     Run --all every 24 hours automatically
    python main.py --dashboard    Launch Streamlit on localhost:8501
    python main.py --seed         Run one full ingestion cycle (live APIs)
    python main.py --live         Start continuous 30-minute ingestion scheduler

Database reset:
    There is no destructive wipe command. If you need a clean DB, delete
    the database file manually, then run --init to recreate tables.
"""

import argparse
import subprocess
import sys
import time


def cmd_init():
    from db.models import init_db
    init_db()
    print("Database initialized.")


def cmd_scrape():
    """
    Run one ingestion tick: Open Food Facts (sizes) + Kroger (prices).

    Data sources:
      - Open Food Facts API — real product sizes and barcodes (.net mirror,
        falls back to .org). Free, no authentication required.
      - Kroger API — real US retail shelf prices. Requires KROGER_CLIENT_ID
        and KROGER_CLIENT_SECRET in .env or Streamlit secrets.

    This function does NOT run the shrinkflation detector.
    Detection runs separately via --analyze or cmd_analyze().
    """
    from scraper.live_tracker import run_live_update
    from scraper.kroger import scrape_kroger

    print("Running Open Food Facts ingestion...")
    off_stats = run_live_update(max_categories=3)
    print(
        f"  OFF: +{off_stats.get('new_products', 0)} products | "
        f"+{off_stats.get('new_snapshots', 0)} snapshots | "
        f"phase={off_stats.get('phase', '?')} | "
        f"panel={off_stats.get('panel_size', '?')}"
    )

    print("Running Kroger price enrichment...")
    try:
        matched, kr_snaps = scrape_kroger()
        print(f"  Kroger: {matched} matched | {kr_snaps} price snapshots")
    except Exception as e:
        print(f"  Kroger error (check KROGER_CLIENT_ID/SECRET in .env): {e}")


def cmd_analyze():
    from analysis.detector import run_detection
    new_flags = run_detection()
    print(f"Detection complete — {new_flags} new flags created.")


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
        print(f"Insight generation skipped (set OPENAI_API_KEY in .env): {e}")


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
    """
    Run one complete ingestion tick synchronously via the pipeline.

    Sources:
      - Open Food Facts API  — real product sizes and barcodes
      - Kroger API           — real US retail prices
    """
    from ingestion.pipeline import run_once
    run_once()


def cmd_live():
    """
    Start the background ingestion scheduler.
    Runs ingest_tick() (OFF + Kroger) every 30 minutes via APScheduler.
    Blocks until Ctrl+C.
    """
    from db.models import init_db
    from ingestion.pipeline import start_scheduler, stop_scheduler

    print("=" * 60)
    print("Shrinkflation Detector — Live Ingestion Scheduler")
    print("  Ingesting Open Food Facts + Kroger every 30 minutes")
    print("  Press Ctrl+C to stop")
    print("=" * 60)

    init_db()
    start_scheduler()

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        stop_scheduler()
        print("\nStopped.")


def main():
    parser = argparse.ArgumentParser(description="Shrinkflation Detector")
    parser.add_argument("--init",      action="store_true", help="Initialize the database")
    parser.add_argument("--scrape",    action="store_true", help="Run one ingestion tick (OFF + Kroger)")
    parser.add_argument("--analyze",   action="store_true", help="Run the shrinkflation detector")
    parser.add_argument("--insight",   action="store_true", help="Generate daily AI insight")
    parser.add_argument("--report",    action="store_true", help="Generate weekly AI report")
    parser.add_argument("--all",       action="store_true", help="Scrape + analyze + insight")
    parser.add_argument("--schedule",  action="store_true", help="Run --all every 24 hours")
    parser.add_argument("--dashboard", action="store_true", help="Launch Streamlit dashboard")
    parser.add_argument("--seed",      action="store_true", help="Run one ingestion cycle via pipeline")
    parser.add_argument("--live",      action="store_true", help="Start 30-minute ingestion scheduler")

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
    if args.live:
        cmd_live()
    if args.dashboard:
        cmd_dashboard()


if __name__ == "__main__":
    main()
