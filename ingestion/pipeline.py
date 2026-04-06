"""
Live-only ingestion pipeline — scans Open Food Facts every 60 seconds.

NO seed data, NO verified cases, NO historical records.
Every single product in the database comes from a live API call.

Schedule:
  • Every 1 minute → fetch 2 categories from Open Food Facts API,
                      store product snapshots, run shrinkflation detector

Data sources:
  - https://world.openfoodfacts.org/api/v2/  (product sizes + barcodes)
  - https://prices.openfoodfacts.org/api/v1/  (crowd-sourced real prices)
"""

import logging
import threading
import time
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_scheduler_lock = threading.Lock()

# Rotate through categories — each tick scans 2, cycling through all
_tick_counter = 0
_tick_lock = threading.Lock()


def ingest_tick():
    """
    One scan tick — runs every 60 seconds.

    Fetches 2 categories from Open Food Facts (rotates each tick so all 17
    categories are covered within ~9 minutes). Stores real product snapshots.
    Runs shrinkflation detection on all stored products.
    """
    global _tick_counter
    from scraper.live_tracker import run_live_update
    from analysis.detector import run_detection

    with _tick_lock:
        _tick_counter += 1
        tick = _tick_counter

    start = datetime.now(timezone.utc)
    logger.info(f"[pipeline] ── tick #{tick} started ──")

    # ── Fetch live products from OFF ──────────────────────────────────────
    try:
        stats = run_live_update(max_categories=2)
        new_p = stats.get("new_products", 0)
        new_s = stats.get("new_snapshots", 0)
        changes = stats.get("size_changes_observed", 0)
        logger.info(
            f"[pipeline] tick #{tick}: {new_p} new products, "
            f"{new_s} snapshots, {changes} live size changes"
        )
    except Exception as exc:
        logger.error(f"[pipeline] live_update failed: {exc}", exc_info=True)
        return

    # ── Run detector ──────────────────────────────────────────────────────
    try:
        new_flags = run_detection()
        logger.info(f"[pipeline] tick #{tick}: {new_flags} detection flags")
    except Exception as exc:
        logger.error(f"[pipeline] detection failed: {exc}", exc_info=True)
        new_flags = 0

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    logger.info(f"[pipeline] ── tick #{tick} done in {elapsed:.1f}s ──")

    _write_run_log(
        job_type="live",
        stats={**stats, "new_flags": new_flags, "tick": tick},
        elapsed=elapsed,
    )


def _write_run_log(job_type: str, stats: dict, elapsed: float):
    """Persist run metadata so dashboard can show last-scan time."""
    try:
        from db.models import AgentInsight, get_session
        session = get_session()
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        session.add(AgentInsight(
            insight_type=f"ingest_{job_type}",
            content=(
                f"[{job_type}] {ts} | "
                + " | ".join(f"{k}: {v}" for k, v in stats.items())
                + f" | elapsed: {elapsed:.1f}s"
            ),
            generated_at=datetime.now(timezone.utc),
        ))
        session.commit()
        session.close()
    except Exception as exc:
        logger.warning(f"[pipeline] could not write run log: {exc}")


def start_scheduler() -> BackgroundScheduler:
    """
    Start the live scanner — runs ingest_tick() every 60 seconds.
    Safe to call multiple times (singleton).
    """
    global _scheduler
    with _scheduler_lock:
        if _scheduler is not None and _scheduler.running:
            logger.debug("[pipeline] scheduler already running — no-op")
            return _scheduler

        _scheduler = BackgroundScheduler(timezone="UTC")

        _scheduler.add_job(
            ingest_tick,
            trigger=IntervalTrigger(seconds=60),
            id="live_scan",
            name="Live: OFF category scan every 60s",
            replace_existing=True,
            misfire_grace_time=30,
        )

        _scheduler.start()
        logger.info("[pipeline] scheduler started — scanning every 60 seconds")

    # Fire first tick immediately in a background thread
    threading.Thread(target=ingest_tick, daemon=True).start()

    return _scheduler


def stop_scheduler():
    """Gracefully shut down."""
    global _scheduler
    with _scheduler_lock:
        if _scheduler and _scheduler.running:
            _scheduler.shutdown(wait=False)
            logger.info("[pipeline] scheduler stopped")
            _scheduler = None


def run_once():
    """Run a single scan tick synchronously."""
    print("[pipeline] Running one live scan...")
    ingest_tick()
    print("[pipeline] Done.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    print("=" * 60)
    print("Shrinkflation Detector — Live Scanner")
    print("  Scanning Open Food Facts every 60 seconds")
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
