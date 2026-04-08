"""
Live ingestion pipeline — runs every 30 minutes.

What this pipeline does:
  - calls live_tracker.run_live_update() to ingest OFF product snapshots
  - calls kroger.scrape_kroger() to enrich with real prices
  - logs each run to the IngestionRun table

What this pipeline does NOT do:
  - run the shrinkflation detector (separate concern)
  - create ShrinkflationFlags
  - use size-only inference

Note on Streamlit Cloud deployment:
  APScheduler background threads are not reliable on Streamlit Cloud free tier.
  On Streamlit Cloud, ingestion is triggered inline by _run_live_scan() in
  dashboard/app.py on each 30-minute page refresh.
  This pipeline file is used for local development and server deployments only.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy import to avoid circular imports and Streamlit context issues
_scheduler = None
_scheduler_lock = threading.Lock()
_tick_counter = 0
_tick_lock = threading.Lock()


def ingest_tick():
    """
    One ingestion tick.

    Fetches product snapshots from Open Food Facts and enriches with
    Kroger prices. Does NOT run the shrinkflation detector.
    """
    global _tick_counter
    from scraper.live_tracker import run_live_update
    from scraper.kroger import scrape_kroger

    with _tick_lock:
        _tick_counter += 1
        tick = _tick_counter

    start = datetime.now(timezone.utc)
    logger.info(f"[pipeline] ── tick #{tick} started ──")

    # ── Open Food Facts ──────────────────────────────────────────────────
    off_stats = {}
    try:
        off_stats = run_live_update(max_categories=3)
        logger.info(
            f"[pipeline] tick #{tick} OFF: "
            f"+{off_stats.get('new_products', 0)} products | "
            f"+{off_stats.get('new_snapshots', 0)} snapshots | "
            f"phase={off_stats.get('phase', '?')} | "
            f"panel={off_stats.get('panel_size', '?')} | "
            f"errors={off_stats.get('off_errors', 0)}"
        )
    except Exception as exc:
        logger.error(f"[pipeline] tick #{tick} OFF failed: {exc}", exc_info=True)

    # ── Kroger price enrichment ──────────────────────────────────────────
    try:
        matched, kr_snaps = scrape_kroger(max_categories=2)
        logger.info(
            f"[pipeline] tick #{tick} Kroger: "
            f"{matched} matched | {kr_snaps} price snapshots"
        )
    except Exception as exc:
        logger.error(f"[pipeline] tick #{tick} Kroger failed: {exc}", exc_info=True)

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    logger.info(f"[pipeline] ── tick #{tick} done in {elapsed:.1f}s ──")


def start_scheduler():
    """
    Start the background ingestion scheduler — runs ingest_tick() every 30 minutes.
    Safe to call multiple times (singleton guard).
    Returns the scheduler instance.
    """
    global _scheduler

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger
    except ImportError:
        logger.error("[pipeline] APScheduler not installed — cannot start scheduler")
        return None

    with _scheduler_lock:
        if _scheduler is not None and _scheduler.running:
            logger.debug("[pipeline] Scheduler already running — no-op")
            return _scheduler

        _scheduler = BackgroundScheduler(timezone="UTC")
        _scheduler.add_job(
            ingest_tick,
            trigger=IntervalTrigger(seconds=1800),  # 30 minutes
            id="live_ingest",
            name="Live ingestion: OFF + Kroger every 30 min",
            replace_existing=True,
            misfire_grace_time=120,
        )
        _scheduler.start()
        logger.info("[pipeline] Scheduler started — ingesting every 30 minutes")

    # Fire the first tick immediately in a background thread so the DB
    # has data before the first scheduled run
    threading.Thread(target=ingest_tick, daemon=True, name="ingest-tick-0").start()

    return _scheduler


def stop_scheduler():
    """Gracefully shut down the scheduler."""
    global _scheduler
    with _scheduler_lock:
        if _scheduler and _scheduler.running:
            _scheduler.shutdown(wait=False)
            logger.info("[pipeline] Scheduler stopped")
            _scheduler = None


def run_once():
    """Run a single ingestion tick synchronously. Useful for testing."""
    logger.info("[pipeline] Running single ingestion tick...")
    ingest_tick()
    logger.info("[pipeline] Done.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    print("=" * 60)
    print("Shrinkflation Detector — Live Ingestion Pipeline")
    print("  Ingesting OFF + Kroger every 30 minutes")
    print("  Press Ctrl+C to stop")
    print("=" * 60)

    from db.models import init_db
    init_db()

    start_scheduler()

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        stop_scheduler()
        print("\nStopped.")
