"""
Continuous ingestion pipeline — the live data engine.

Two scheduled jobs run automatically:

  1. Every 1 hour   →  ingest_live_categories()
     • Rotates through 17 OFF product categories (chips, cereal, ice cream, etc.)
     • Fetches the most-recently-updated products from Open Food Facts API
     • Saves new ProductSnapshot rows to the database
     • Runs shrinkflation detection: compares current snapshot vs 30-day-old snapshot
     • Flags any product whose size decreased

  2. Every 24 hours (03:00 UTC)  →  ingest_verified_cases()
     • Searches OFF API for the real current version of each documented case
     • Retrieves real crowd-sourced prices from Open Prices API where available
     • Creates/updates Product + Snapshot records backed by live API responses
     • Discovers any newly changed products from OFF's recently-modified feed
     • Runs full shrinkflation detection pass

Neither job uses any static, random, or fabricated data.
Every record in the database traces back to a live HTTP response from:
  - https://world.openfoodfacts.org/api/v2/  (product sizes + barcodes)
  - https://prices.openfoodfacts.org/api/v1/  (crowd-sourced real prices)

Usage
-----
Standalone (runs until Ctrl+C):
    python -m ingestion.pipeline

From Streamlit dashboard (background thread, auto-started on load):
    from ingestion.pipeline import start_scheduler
    start_scheduler()

One-shot CLI sync run:
    python main.py --seed          # same as run_once()
    python main.py --live          # start_scheduler() + block until Ctrl+C
"""

import logging
import threading
import time
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

# Module-level scheduler singleton — one instance per process
_scheduler: BackgroundScheduler | None = None
_scheduler_lock = threading.Lock()


# ══════════════════════════════════════════════════════════════════════════════
# JOB 1 — Hourly: rotate through OFF categories
# ══════════════════════════════════════════════════════════════════════════════

def ingest_live_categories():
    """
    Fetch the most-recently-updated products from Open Food Facts for a
    rotating set of categories, store new snapshots, then run detection.

    Runs every hour. Rotates through 17 categories so all are covered within
    a 4-hour window without hammering the API.
    """
    from scraper.live_tracker import run_live_update
    from analysis.detector import run_detection

    start = datetime.now(timezone.utc)
    logger.info("[pipeline] ── hourly ingest started ──")

    # ── Step 1: fetch + store snapshots ────────────────────────────────────
    try:
        stats = run_live_update(max_categories=5)
        logger.info(
            f"[pipeline] live update complete: "
            f"{stats.get('new_products', 0)} new products, "
            f"{stats.get('new_snapshots', 0)} snapshots, "
            f"{stats.get('size_changes_detected', 0)} size changes"
        )
    except Exception as exc:
        logger.error(f"[pipeline] live_update failed: {exc}", exc_info=True)
        return

    # ── Step 2: run shrinkflation detector ─────────────────────────────────
    try:
        new_flags = run_detection()
        logger.info(f"[pipeline] detection complete: {new_flags} new shrinkflation flags")
    except Exception as exc:
        logger.error(f"[pipeline] detection failed: {exc}", exc_info=True)
        new_flags = 0

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    logger.info(f"[pipeline] ── hourly cycle done in {elapsed:.1f}s ──")

    _write_run_log(
        job_type="hourly",
        stats={**stats, "new_flags": new_flags},
        elapsed=elapsed,
    )


# ══════════════════════════════════════════════════════════════════════════════
# JOB 2 — Daily at 03:00 UTC: deep scan of verified cases
# ══════════════════════════════════════════════════════════════════════════════

def ingest_verified_cases():
    """
    Hit Open Food Facts for every documented shrinkflation case to get the
    real current size, cross-reference with Open Prices for real retail prices,
    and discover any brand-new size changes from OFF's live feed.

    Runs once per day at 03:00 UTC.
    """
    from data.verified_cases import VERIFIED_CASES
    from scraper.product_scanner import scan_verified_products, scan_recently_changed
    from analysis.detector import run_detection
    from db.models import get_session, init_db

    start = datetime.now(timezone.utc)
    logger.info("[pipeline] ── daily verified-case scan started ──")

    # ── Step 1: scan documented cases via OFF API ───────────────────────────
    try:
        init_db()
        session = get_session()
        scanned, case_flags = scan_verified_products(
            session, VERIFIED_CASES, batch_size=200
        )
        logger.info(
            f"[pipeline] verified scan: {scanned} products checked, "
            f"{case_flags} new flags"
        )
    except Exception as exc:
        logger.error(f"[pipeline] verified scan failed: {exc}", exc_info=True)
        return
    finally:
        try:
            session.close()
        except Exception:
            pass

    # ── Step 2: discover newly changed products from OFF live feed ──────────
    try:
        session = get_session()
        recent_prods, recent_flags = scan_recently_changed(
            session, max_products=200
        )
        logger.info(
            f"[pipeline] discovery scan: {recent_prods} products, "
            f"{recent_flags} new flags"
        )
    except Exception as exc:
        logger.error(f"[pipeline] discovery scan failed: {exc}", exc_info=True)
        recent_prods, recent_flags = 0, 0
    finally:
        try:
            session.close()
        except Exception:
            pass

    # ── Step 3: full detection pass over entire product table ───────────────
    try:
        total_flags = run_detection()
        logger.info(f"[pipeline] full detection: {total_flags} total flags in DB")
    except Exception as exc:
        logger.error(f"[pipeline] detection failed: {exc}", exc_info=True)
        total_flags = 0

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    logger.info(f"[pipeline] ── daily cycle done in {elapsed:.1f}s ──")

    _write_run_log(
        job_type="daily",
        stats={
            "cases_scanned": scanned,
            "case_flags": case_flags,
            "discovery_products": recent_prods,
            "discovery_flags": recent_flags,
            "total_flags_in_db": total_flags,
        },
        elapsed=elapsed,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Run-log writer  (persists to AgentInsight so dashboard can show last-run)
# ══════════════════════════════════════════════════════════════════════════════

def _write_run_log(job_type: str, stats: dict, elapsed: float):
    """Write a one-line ingestion run record to AgentInsight table."""
    try:
        from db.models import AgentInsight, get_session
        session = get_session()
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
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


# ══════════════════════════════════════════════════════════════════════════════
# Scheduler lifecycle
# ══════════════════════════════════════════════════════════════════════════════

def start_scheduler(run_immediately: bool = False) -> BackgroundScheduler:
    """
    Start the APScheduler background scheduler (singleton — safe to call many times).

    Schedule:
      • Every 1 hour      → ingest_live_categories()
      • Daily at 03:00 UTC → ingest_verified_cases()

    Parameters
    ----------
    run_immediately : bool
        If True, run both jobs once right now before the first scheduled tick.
        Useful when the database is empty on a fresh Streamlit Cloud deploy.
    """
    global _scheduler
    with _scheduler_lock:
        if _scheduler is not None and _scheduler.running:
            logger.debug("[pipeline] scheduler already running — no-op")
            return _scheduler

        _scheduler = BackgroundScheduler(timezone="UTC")

        _scheduler.add_job(
            ingest_live_categories,
            trigger=IntervalTrigger(hours=1),
            id="hourly_live_categories",
            name="Hourly: OFF live category ingest",
            replace_existing=True,
            misfire_grace_time=300,       # allow 5-min late start
        )

        _scheduler.add_job(
            ingest_verified_cases,
            trigger=CronTrigger(hour=3, minute=0),
            id="daily_verified_cases",
            name="Daily: verified shrinkflation case scan",
            replace_existing=True,
            misfire_grace_time=3600,      # allow 1-hour late start
        )

        _scheduler.start()
        logger.info(
            "[pipeline] scheduler started — "
            "hourly category ingest + daily verified-case scan registered"
        )

    if run_immediately:
        # Run in background threads so the caller isn't blocked
        threading.Thread(target=ingest_live_categories, daemon=True).start()
        threading.Thread(target=ingest_verified_cases, daemon=True).start()

    return _scheduler


def stop_scheduler():
    """Gracefully shut down the scheduler."""
    global _scheduler
    with _scheduler_lock:
        if _scheduler and _scheduler.running:
            _scheduler.shutdown(wait=False)
            logger.info("[pipeline] scheduler stopped")
            _scheduler = None


def run_once():
    """
    Run one complete ingestion cycle synchronously (blocks until finished).
    Used by `python main.py --seed` and cold-start fallback.
    """
    print("[pipeline] Running one full ingestion cycle (synchronous)...")
    ingest_live_categories()
    ingest_verified_cases()
    print("[pipeline] One-shot ingestion cycle complete.")


# ══════════════════════════════════════════════════════════════════════════════
# Standalone entry-point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    print("=" * 60)
    print("Shrinkflation Detector — Live Ingestion Pipeline")
    print("  • Hourly:  Open Food Facts category scan")
    print("  • Daily:   Verified shrinkflation case deep-scan")
    print("Press Ctrl+C to stop.")
    print("=" * 60)

    # Kick off an immediate cycle so there's data straight away
    from db.models import init_db
    init_db()

    start_scheduler(run_immediately=True)

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        stop_scheduler()
        print("\nPipeline stopped.")
