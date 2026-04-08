"""
Shrinkflation detector — strict, evidence-based live detection.

A live ShrinkflationFlag is created ONLY when ALL of the following hold:

  1.  The product was discovered by live ingestion (data_source in
      LIVE_DATA_SOURCES). documented_historical products are never touched.

  2.  Two enriched observations exist for the product, with a temporal gap
      of at least MIN_DETECTION_GAP_DAYS between them.

  3.  Each enriched observation has a confirmed size AND a confirmed price.
      An observation may be:
        - self-contained: one snapshot with both size_value and price set, OR
        - temporal pair:  a price-only snapshot (Kroger) paired with a size
          snapshot (OFF or Kroger) that is within PRICE_SIZE_WINDOW_HOURS of
          it AND is the ONLY size-eligible snapshot in that window.
          If multiple size-eligible snapshots fall within the window, the
          pairing is ambiguous and the observation is rejected.

  4.  Both observations use the same size unit family (mass / volume / count).

  5.  The unit family of both observations is not "unknown".

  6.  The newer observation's size_value < older observation's size_value by
      at least MIN_SIZE_DECREASE_PCT.

  7.  The newer observation's price-per-unit (price / size_value, in the
      same unit as size_value) is strictly greater than the older
      observation's price-per-unit. This is NOT a comparison of raw shelf
      prices — it is a comparison of price / size_value at each time point.
      A product that shrinks from 9.75 oz at $4.99 to 9.25 oz at $4.89 has
      a PPU of $0.512 → $0.528 (+3.1%) — that is shrinkflation even though
      the shelf price fell.

  8.  The event is not already recorded (dedupe_key unique constraint).

  9.  The flag row links to:
        - the price snapshot for old and new observations
          (evidence_old_snapshot_id, evidence_new_snapshot_id)
        - the size snapshot for old and new observations, when they differ
          from the price snapshot (evidence_old_size_snapshot_id,
          evidence_new_size_snapshot_id). NULL for self-contained observations.

Transition selection:
  The detector does NOT simply compare the oldest vs newest enriched
  observation. Instead it scans all (i, j) pairs ordered by time and finds
  the FIRST j (earliest new_obs) for which a valid i (old_obs) exists. Among
  valid i for that j, it picks the latest one (closest pre-event observation).
  This ensures the PPU delta reflects the actual shrink boundary, not an
  earlier unrelated price hike.

Ambiguity rule:
  Any case where evidence is ambiguous is conservatively rejected. This
  includes: multiple size snapshots within the pairing window of one price
  snapshot, incompatible unit families, unknown unit families, or a gap
  between observations too small to be meaningful. False negatives are
  explicitly preferred over false positives.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.exc import IntegrityError

from db.models import (
    IngestionRun, Product, ProductSnapshot, ShrinkflationFlag,
    get_session,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tunable parameters
# ---------------------------------------------------------------------------

# Minimum temporal gap between old and new enriched observation
MIN_DETECTION_GAP_DAYS: int = 30

# Maximum window to match a Kroger price snapshot with an OFF size snapshot
# for a temporal pair. If more than one size-eligible snapshot falls within
# this window, the pairing is rejected as ambiguous.
PRICE_SIZE_WINDOW_HOURS: int = 24

# Minimum size decrease (%) to consider shrinkflation
MIN_SIZE_DECREASE_PCT: float = 2.0

# How far back to look for the "old" observation
LOOKBACK_DAYS: int = 90

# Severity thresholds (price-per-unit increase %)
HIGH_SEVERITY_PPU_PCT: float = 20.0
MEDIUM_SEVERITY_PPU_PCT: float = 8.0

# Only operate on live products
LIVE_DATA_SOURCES = ("live_openfoodfacts", "live_kroger", "live_combined")


# ---------------------------------------------------------------------------
# Enriched observation dataclass
# ---------------------------------------------------------------------------

@dataclass
class _EnrichedObservation:
    """
    A time-point observation with confirmed size AND price.

    For self-contained observations (one snapshot with both fields):
      size_snapshot_id == price_snapshot_id

    For temporal-pair observations (two snapshots combined):
      size_snapshot_id  : the snapshot that provided size_value / size_unit
      price_snapshot_id : the snapshot that provided price
      These differ and both are written to the flag for full traceability.

    observed_at: the price snapshot's scraped_at (the binding timestamp).
    """
    observed_at: datetime
    size_value: float
    size_unit: str
    size_unit_family: str
    price: float
    size_snapshot_id: int
    price_snapshot_id: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_severity(ppu_increase_pct: float) -> str:
    if ppu_increase_pct >= HIGH_SEVERITY_PPU_PCT:
        return "HIGH"
    if ppu_increase_pct >= MEDIUM_SEVERITY_PPU_PCT:
        return "MEDIUM"
    return "LOW"


def _normalize_ts(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts


# ---------------------------------------------------------------------------
# Snapshot query
# ---------------------------------------------------------------------------

def _get_live_snapshots(session, product_id: int, cutoff: datetime) -> list:
    """
    Return all real_observed snapshots for a product within the lookback window.
    Explicitly excludes documented_reference snapshots.
    Ordered oldest-first.
    """
    return (
        session.query(ProductSnapshot)
        .filter(
            ProductSnapshot.product_id == product_id,
            ProductSnapshot.observation_type == "real_observed",
            ProductSnapshot.scraped_at >= cutoff,
        )
        .order_by(ProductSnapshot.scraped_at.asc())
        .all()
    )


# ---------------------------------------------------------------------------
# Enriched observation builder (concern 3: ambiguity rejection)
# ---------------------------------------------------------------------------

def _build_enriched_observations(snapshots: list) -> list:
    """
    Build enriched observations from a product's live snapshot timeline.

    Pairing rules:
      Type 1 — self-contained: snapshot has both size_value and price.
               Used directly. size_snapshot_id == price_snapshot_id.

      Type 2 — temporal pair: a price-only snapshot paired with the nearest
               size-eligible snapshot within PRICE_SIZE_WINDOW_HOURS.
               REJECTED if multiple size-eligible snapshots exist within the
               window (ambiguous — cannot determine which size was current
               at the time of the price observation).

    Size eligibility requires:
      - size_value > 0
      - size_unit is not None
      - size_unit_family not in (None, "unknown")

    Size-only snapshots (no price) cannot stand alone and are only used as
    pairing targets.
    """
    enriched = []
    window_secs = PRICE_SIZE_WINDOW_HOURS * 3600

    valid_snaps = [s for s in snapshots if s.scraped_at is not None]

    for snap in valid_snaps:
        ts = _normalize_ts(snap.scraped_at)

        has_valid_size = (
            snap.size_value is not None
            and snap.size_value > 0
            and snap.size_unit is not None
            and snap.size_unit_family not in (None, "unknown")
        )
        has_valid_price = snap.price is not None and snap.price > 0

        if has_valid_size and has_valid_price:
            # Type 1: self-contained
            enriched.append(_EnrichedObservation(
                observed_at=ts,
                size_value=snap.size_value,
                size_unit=snap.size_unit,
                size_unit_family=snap.size_unit_family,
                price=snap.price,
                size_snapshot_id=snap.id,
                price_snapshot_id=snap.id,
            ))
            continue

        if has_valid_price and not has_valid_size:
            # Type 2: find size candidates within the pairing window
            candidates = []
            for candidate in valid_snaps:
                if candidate.id == snap.id:
                    continue
                cand_size_ok = (
                    candidate.size_value is not None
                    and candidate.size_value > 0
                    and candidate.size_unit is not None
                    and candidate.size_unit_family not in (None, "unknown")
                )
                if not cand_size_ok:
                    continue
                cand_ts = _normalize_ts(candidate.scraped_at)
                gap = abs((cand_ts - ts).total_seconds())
                if gap <= window_secs:
                    candidates.append((gap, candidate))

            if len(candidates) == 0:
                # No size data near this price snapshot — skip
                continue

            if len(candidates) > 1:
                # Multiple size candidates — ambiguous, reject conservatively
                logger.debug(
                    f"[detector] price snap id={snap.id} at {ts.isoformat()}: "
                    f"rejected — {len(candidates)} size candidates within "
                    f"{PRICE_SIZE_WINDOW_HOURS}h window (ambiguous pairing)"
                )
                continue

            # Exactly one candidate — unambiguous pairing
            _, size_snap = candidates[0]
            enriched.append(_EnrichedObservation(
                observed_at=ts,
                size_value=size_snap.size_value,
                size_unit=size_snap.size_unit,
                size_unit_family=size_snap.size_unit_family,
                price=snap.price,
                size_snapshot_id=size_snap.id,
                price_snapshot_id=snap.id,
            ))

        # size-only snapshots: not usable standalone → skip

    enriched.sort(key=lambda o: o.observed_at)
    return enriched


# ---------------------------------------------------------------------------
# Transition finder (concern 2: first valid transition, not oldest-vs-newest)
# ---------------------------------------------------------------------------

def _find_first_valid_transition(
    enriched: list,
    stats: dict,
) -> tuple:
    """
    Find the first valid (old_obs, new_obs) shrinkflation transition.

    Scanning order:
      - Iterate new_obs from earliest to latest (j = 1..n-1).
      - For each new_obs, iterate candidate old_obs from latest to earliest
        (i = j-1..0), stopping at the first valid old_obs found.
      - Return the (old_obs, new_obs) pair from the first j with a valid i.

    "Latest valid old_obs for a given new_obs" = the closest pre-event
    observation, which gives the most accurate PPU delta and avoids
    contamination from earlier raw price hikes.

    "First j" = the earliest time at which the shrink transition is
    confirmable, ensuring the flag reflects when the event was first detected.

    Returns (None, None) if no valid pair exists.
    Increments stats counters for each rejection category encountered.
    The counters reflect per-pair rejections; a product may hit multiple
    categories across different candidate pairs.
    """
    n = len(enriched)
    for j in range(1, n):
        new_obs = enriched[j]
        for i in range(j - 1, -1, -1):
            old_obs = enriched[i]

            # Gap check
            gap_days = (
                (new_obs.observed_at - old_obs.observed_at).total_seconds() / 86400
            )
            if gap_days < MIN_DETECTION_GAP_DAYS:
                # Don't count — gap-too-small is expected during fill phase
                continue

            # Unit family compatibility
            if old_obs.size_unit_family == "unknown" or new_obs.size_unit_family == "unknown":
                stats["rejected_unknown_unit_family"] += 1
                continue

            if old_obs.size_unit_family != new_obs.size_unit_family:
                stats["rejected_incompatible_units"] += 1
                continue

            # Size decrease
            size_change_pct = (
                (old_obs.size_value - new_obs.size_value) / old_obs.size_value * 100
            )
            if size_change_pct < MIN_SIZE_DECREASE_PCT:
                # Includes no-change and size-increase cases — silent skip
                continue

            # PPU increase (REQUIRED — no size-only inference)
            old_ppu = old_obs.price / old_obs.size_value
            new_ppu = new_obs.price / new_obs.size_value
            ppu_increase_pct = ((new_ppu - old_ppu) / old_ppu) * 100
            if ppu_increase_pct <= 0:
                stats["rejected_no_ppu_increase"] += 1
                continue

            # Valid pair found
            return old_obs, new_obs

    return None, None


# ---------------------------------------------------------------------------
# Detection gate
# ---------------------------------------------------------------------------

def _try_detect(
    session,
    product: Product,
    cutoff: datetime,
    stats: dict,
) -> Optional[ShrinkflationFlag]:
    """
    Attempt to create one flag for a product.
    Returns a ShrinkflationFlag (not yet committed), or None.
    """
    product_id = product.id

    # Step 1 — live real_observed snapshots only
    snapshots = _get_live_snapshots(session, product_id, cutoff)
    if not snapshots:
        return None

    # Step 2 — build enriched observations (ambiguity rejected inside)
    enriched = _build_enriched_observations(snapshots)
    if len(enriched) < 2:
        if snapshots:
            logger.debug(
                f"[detector] product_id={product_id} ({product.name!r}): "
                f"too few enriched observations "
                f"({len(snapshots)} raw snapshots → {len(enriched)} enriched)"
            )
            stats["rejected_too_few_enriched"] += 1
        return None

    # Step 3 — find first valid transition
    old_obs, new_obs = _find_first_valid_transition(enriched, stats)
    if old_obs is None:
        return None

    # Step 4 — dedupe check
    dedupe_key = (
        f"{product_id}::{round(old_obs.size_value, 3)}::"
        f"{round(new_obs.size_value, 3)}::live_detected"
    )
    existing = (
        session.query(ShrinkflationFlag)
        .filter_by(dedupe_key=dedupe_key)
        .first()
    )
    if existing:
        stats["skipped_already_flagged"] += 1
        return None

    # Step 5 — compute final metrics
    gap_days = (new_obs.observed_at - old_obs.observed_at).total_seconds() / 86400
    old_ppu = old_obs.price / old_obs.size_value
    new_ppu = new_obs.price / new_obs.size_value
    ppu_increase_pct = ((new_ppu - old_ppu) / old_ppu) * 100
    size_change_pct = (old_obs.size_value - new_obs.size_value) / old_obs.size_value * 100
    severity = _compute_severity(ppu_increase_pct)

    # Determine size evidence snapshot IDs.
    # For self-contained observations: size_snapshot_id == price_snapshot_id.
    # Store NULL in the size fields to avoid redundancy and signal self-contained.
    old_size_snap_id = (
        old_obs.size_snapshot_id
        if old_obs.size_snapshot_id != old_obs.price_snapshot_id
        else None
    )
    new_size_snap_id = (
        new_obs.size_snapshot_id
        if new_obs.size_snapshot_id != new_obs.price_snapshot_id
        else None
    )

    flag = ShrinkflationFlag(
        product_id=product_id,
        flag_source="live_detected",
        old_size=old_obs.size_value,
        new_size=new_obs.size_value,
        size_unit=old_obs.size_unit,
        old_price=old_obs.price,
        new_price=new_obs.price,
        has_price_evidence=True,
        price_per_unit_increase_pct=round(ppu_increase_pct, 2),
        severity=severity,
        # Price-source snapshots (always populated for live_detected)
        evidence_old_snapshot_id=old_obs.price_snapshot_id,
        evidence_new_snapshot_id=new_obs.price_snapshot_id,
        # Size-source snapshots (NULL when self-contained)
        evidence_old_size_snapshot_id=old_size_snap_id,
        evidence_new_size_snapshot_id=new_size_snap_id,
        detected_at=datetime.now(timezone.utc),
        dedupe_key=dedupe_key,
    )

    logger.info(
        f"[detector] FLAGGED product_id={product_id} ({product.name!r}): "
        f"size {old_obs.size_value}{old_obs.size_unit} → "
        f"{new_obs.size_value}{new_obs.size_unit} "
        f"({size_change_pct:.1f}% decrease), "
        f"PPU {old_ppu:.4f} → {new_ppu:.4f} (+{ppu_increase_pct:.1f}%) "
        f"[{severity}], gap={gap_days:.0f}d, "
        f"price_snap_old={old_obs.price_snapshot_id} "
        f"size_snap_old={old_obs.size_snapshot_id} "
        f"price_snap_new={new_obs.price_snapshot_id} "
        f"size_snap_new={new_obs.size_snapshot_id}"
    )
    return flag


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_detection() -> int:
    """
    Run the shrinkflation detector over all live-tracked products.

    Operates only on products with data_source in LIVE_DATA_SOURCES.
    documented_historical products and their snapshots are never touched.

    Returns the number of new flags created.
    """
    session = get_session()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=LOOKBACK_DAYS)

    stats = {
        "products_checked": 0,
        "new_flags": 0,
        "rejected_too_few_enriched": 0,
        "rejected_gap_too_small": 0,
        "rejected_unknown_unit_family": 0,
        "rejected_incompatible_units": 0,
        "rejected_no_ppu_increase": 0,
        "skipped_already_flagged": 0,
        "errors": 0,
    }

    run = IngestionRun(
        source="detector",
        phase="track",
        status="running",
    )
    session.add(run)
    session.commit()

    try:
        live_products = (
            session.query(Product)
            .filter(Product.data_source.in_(LIVE_DATA_SOURCES))
            .all()
        )

        logger.info(
            f"[detector] Running on {len(live_products)} live products "
            f"(lookback={LOOKBACK_DAYS}d, min_gap={MIN_DETECTION_GAP_DAYS}d, "
            f"window={PRICE_SIZE_WINDOW_HOURS}h)"
        )

        for product in live_products:
            stats["products_checked"] += 1
            try:
                flag = _try_detect(session, product, cutoff, stats)
                if flag is not None:
                    session.add(flag)
                    try:
                        session.flush()
                        stats["new_flags"] += 1
                    except IntegrityError:
                        session.rollback()
                        stats["skipped_already_flagged"] += 1
            except Exception as e:
                session.rollback()
                stats["errors"] += 1
                logger.error(
                    f"[detector] Error on product_id={product.id}: {e}",
                    exc_info=True,
                )

        session.commit()

        run.finished_at = datetime.now(timezone.utc)
        run.flags_added = stats["new_flags"]
        run.errors_count = stats["errors"]
        run.status = "complete"
        run.notes = (
            f"checked={stats['products_checked']};"
            f"flagged={stats['new_flags']};"
            f"too_few={stats['rejected_too_few_enriched']};"
            f"no_ppu={stats['rejected_no_ppu_increase']};"
            f"dupes={stats['skipped_already_flagged']}"
        )
        session.commit()

    except Exception as e:
        logger.error(f"[detector] Fatal error: {e}", exc_info=True)
        run.finished_at = datetime.now(timezone.utc)
        run.status = "failed"
        run.notes = f"error={str(e)[:200]}"
        session.commit()

    finally:
        session.close()

    logger.info(
        f"[detector] Complete — "
        f"checked={stats['products_checked']}, "
        f"new_flags={stats['new_flags']}, "
        f"errors={stats['errors']}"
    )
    return stats["new_flags"]


if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(
        level=_logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
    )
    count = run_detection()
    print(f"Detection complete — {count} new flags")
