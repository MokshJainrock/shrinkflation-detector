"""
Phase 5 / 5.1 detector unit tests.

All tests run against an in-memory SQLite database — no external deps.
Tests cover:
  - Original 10 scenario cases
  - Phase 5.1 additions:
      [11] Ambiguity rejection (two size candidates in pairing window)
      [12] First-valid-transition: price hike before shrink
      [13] Evidence IDs: temporal pair vs self-contained
"""
from __future__ import annotations

import sys
import os

# Ensure project root is on path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from datetime import datetime, timezone, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base, Product, ProductSnapshot, ShrinkflationFlag, resolve_unit_family
from analysis.detector import (
    _build_enriched_observations,
    _find_first_valid_transition,
    _try_detect,
    MIN_DETECTION_GAP_DAYS,
    PRICE_SIZE_WINDOW_HOURS,
    MIN_SIZE_DECREASE_PCT,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def session():
    """Provide an in-memory SQLite session, torn down after each test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def _product(session, name="Test Product", brand="TestBrand", data_source="live_openfoodfacts"):
    p = Product(name=name, brand=brand, data_source=data_source,
                identity_key=f"{brand.lower()}::{name.lower()}")
    session.add(p)
    session.flush()
    return p


def _snap(session, product_id, scraped_at, size_value=None, size_unit=None,
          price=None, data_source="live_openfoodfacts",
          observation_type="real_observed"):
    unit_family = resolve_unit_family(size_unit) if size_unit else None
    price_per_unit = (price / size_value) if (price and size_value) else None
    s = ProductSnapshot(
        product_id=product_id,
        size_value=size_value,
        size_unit=size_unit,
        size_unit_family=unit_family,
        price=price,
        price_per_unit=price_per_unit,
        data_source=data_source,
        observation_type=observation_type,
        scraped_at=scraped_at,
    )
    session.add(s)
    session.flush()
    return s


def _t(days_ago=0, hours_ago=0):
    """Return a UTC datetime offset from now."""
    return datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hours_ago)


# ---------------------------------------------------------------------------
# Scenario helpers
# ---------------------------------------------------------------------------

def _run_try_detect(session, product):
    from datetime import timedelta
    from analysis.detector import LOOKBACK_DAYS
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    stats = {
        "rejected_too_few_enriched": 0,
        "rejected_gap_too_small": 0,
        "rejected_unknown_unit_family": 0,
        "rejected_incompatible_units": 0,
        "rejected_no_ppu_increase": 0,
        "skipped_already_flagged": 0,
        "errors": 0,
    }
    return _try_detect(session, product, cutoff, stats), stats


# ---------------------------------------------------------------------------
# [1] Classic shrinkflation — self-contained snapshots
# ---------------------------------------------------------------------------

def test_classic_shrinkflation_detected(session):
    """Two self-contained snapshots with size decrease and PPU increase."""
    p = _product(session)
    T_old = _t(days_ago=45)
    T_new = _t(days_ago=1)
    _snap(session, p.id, T_old, size_value=16.0, size_unit="oz", price=4.99)
    _snap(session, p.id, T_new, size_value=14.0, size_unit="oz", price=4.99)
    session.commit()

    flag, _ = _run_try_detect(session, p)
    assert flag is not None
    assert flag.old_size == 16.0
    assert flag.new_size == 14.0
    assert flag.has_price_evidence is True
    assert flag.flag_source == "live_detected"
    assert flag.price_per_unit_increase_pct > 0


# ---------------------------------------------------------------------------
# [2] Size decreases but shelf price also drops → PPU still increases
# ---------------------------------------------------------------------------

def test_price_drop_but_ppu_still_increases(session):
    """9.75oz@$4.99 → 9.25oz@$4.89: shelf price down but PPU up."""
    p = _product(session)
    _snap(session, p.id, _t(days_ago=45), size_value=9.75, size_unit="oz", price=4.99)
    _snap(session, p.id, _t(days_ago=1),  size_value=9.25, size_unit="oz", price=4.89)
    session.commit()

    flag, _ = _run_try_detect(session, p)
    assert flag is not None
    old_ppu = 4.99 / 9.75
    new_ppu = 4.89 / 9.25
    assert new_ppu > old_ppu, "PPU must have increased"
    assert flag.price_per_unit_increase_pct > 0


# ---------------------------------------------------------------------------
# [3] No PPU increase — size decreases but price falls enough
# ---------------------------------------------------------------------------

def test_no_flag_when_ppu_does_not_increase(session):
    """Size shrinks but price cut is large enough that PPU actually drops."""
    p = _product(session)
    # old PPU = 4.99/16 = 0.312; new PPU = 2.00/14 = 0.143 — PPU dropped
    _snap(session, p.id, _t(days_ago=45), size_value=16.0, size_unit="oz", price=4.99)
    _snap(session, p.id, _t(days_ago=1),  size_value=14.0, size_unit="oz", price=2.00)
    session.commit()

    flag, _ = _run_try_detect(session, p)
    assert flag is None


# ---------------------------------------------------------------------------
# [4] Size stays the same — not shrinkflation
# ---------------------------------------------------------------------------

def test_no_flag_when_size_unchanged(session):
    p = _product(session)
    _snap(session, p.id, _t(days_ago=45), size_value=16.0, size_unit="oz", price=4.99)
    _snap(session, p.id, _t(days_ago=1),  size_value=16.0, size_unit="oz", price=5.99)
    session.commit()

    flag, _ = _run_try_detect(session, p)
    assert flag is None


# ---------------------------------------------------------------------------
# [5] Size increases — not shrinkflation
# ---------------------------------------------------------------------------

def test_no_flag_when_size_increases(session):
    p = _product(session)
    _snap(session, p.id, _t(days_ago=45), size_value=14.0, size_unit="oz", price=4.99)
    _snap(session, p.id, _t(days_ago=1),  size_value=16.0, size_unit="oz", price=5.49)
    session.commit()

    flag, _ = _run_try_detect(session, p)
    assert flag is None


# ---------------------------------------------------------------------------
# [6] Size decrease below threshold (1% < MIN_SIZE_DECREASE_PCT=2%)
# ---------------------------------------------------------------------------

def test_no_flag_when_size_decrease_below_threshold(session):
    p = _product(session)
    # 1% decrease: 16.0 → 15.84
    _snap(session, p.id, _t(days_ago=45), size_value=16.0,  size_unit="oz", price=4.99)
    _snap(session, p.id, _t(days_ago=1),  size_value=15.84, size_unit="oz", price=4.99)
    session.commit()

    flag, _ = _run_try_detect(session, p)
    assert flag is None


# ---------------------------------------------------------------------------
# [7] Gap too small (< MIN_DETECTION_GAP_DAYS)
# ---------------------------------------------------------------------------

def test_no_flag_when_gap_too_small(session):
    p = _product(session)
    # Only 10 days apart
    _snap(session, p.id, _t(days_ago=11), size_value=16.0, size_unit="oz", price=4.99)
    _snap(session, p.id, _t(days_ago=1),  size_value=14.0, size_unit="oz", price=4.99)
    session.commit()

    flag, _ = _run_try_detect(session, p)
    assert flag is None


# ---------------------------------------------------------------------------
# [8] Severity levels
# ---------------------------------------------------------------------------

def test_severity_high(session):
    p = _product(session)
    # old PPU = 5.00/20 = 0.25; new PPU = 5.00/15 = 0.333 → +33% (HIGH)
    _snap(session, p.id, _t(days_ago=45), size_value=20.0, size_unit="oz", price=5.00)
    _snap(session, p.id, _t(days_ago=1),  size_value=15.0, size_unit="oz", price=5.00)
    session.commit()

    flag, _ = _run_try_detect(session, p)
    assert flag is not None
    assert flag.severity == "HIGH"


def test_severity_medium(session):
    p = _product(session)
    # old PPU = 5.00/20 = 0.25; new PPU = 5.00/18 = 0.278 → +11% (MEDIUM)
    _snap(session, p.id, _t(days_ago=45), size_value=20.0, size_unit="oz", price=5.00)
    _snap(session, p.id, _t(days_ago=1),  size_value=18.0, size_unit="oz", price=5.00)
    session.commit()

    flag, _ = _run_try_detect(session, p)
    assert flag is not None
    assert flag.severity == "MEDIUM"


def test_severity_low(session):
    p = _product(session)
    # ~3% size decrease, small PPU increase → LOW
    # old PPU = 3.00/16 = 0.1875; new PPU = 3.00/15.5 = 0.1935 → +3.2%
    _snap(session, p.id, _t(days_ago=45), size_value=16.0, size_unit="oz", price=3.00)
    _snap(session, p.id, _t(days_ago=1),  size_value=15.5, size_unit="oz", price=3.00)
    session.commit()

    flag, _ = _run_try_detect(session, p)
    assert flag is not None
    assert flag.severity == "LOW"


# ---------------------------------------------------------------------------
# [9] Documented historical products are ignored
# ---------------------------------------------------------------------------

def test_no_flag_for_historical_product(session):
    p = _product(session, data_source="documented_historical")
    _snap(session, p.id, _t(days_ago=45), size_value=16.0, size_unit="oz",
          price=4.99, data_source="documented_historical",
          observation_type="documented_reference")
    _snap(session, p.id, _t(days_ago=1),  size_value=14.0, size_unit="oz",
          price=4.99, data_source="documented_historical",
          observation_type="documented_reference")
    session.commit()

    # run_detection won't touch documented_historical products; test _try_detect
    # with a product that has only documented_reference snapshots
    flag, _ = _run_try_detect(session, p)
    # _try_detect queries for real_observed only → 0 snapshots → None
    assert flag is None


# ---------------------------------------------------------------------------
# [10] Dedupe — same transition not flagged twice
# ---------------------------------------------------------------------------

def test_dedupe_prevents_double_flag(session):
    p = _product(session)
    _snap(session, p.id, _t(days_ago=45), size_value=16.0, size_unit="oz", price=4.99)
    _snap(session, p.id, _t(days_ago=1),  size_value=14.0, size_unit="oz", price=4.99)
    session.commit()

    flag1, _ = _run_try_detect(session, p)
    assert flag1 is not None
    session.add(flag1)
    session.commit()

    flag2, stats2 = _run_try_detect(session, p)
    assert flag2 is None
    assert stats2["skipped_already_flagged"] == 1


# ---------------------------------------------------------------------------
# [11] Phase 5.1: Ambiguity rejection
# ---------------------------------------------------------------------------

def test_ambiguous_pairing_rejected(session):
    """
    Price-only Kroger snapshot with TWO size-eligible OFF snapshots within
    the 24h window → pairing is ambiguous → no enriched observation → no flag.
    """
    p = _product(session)
    T_base = _t(days_ago=45)
    # Price-only snapshot (no size)
    _snap(session, p.id, T_base, size_value=None, size_unit=None,
          price=4.99, data_source="live_kroger")
    # Two size candidates within 24h
    _snap(session, p.id, T_base + timedelta(hours=2),
          size_value=16.0, size_unit="oz", price=None)
    _snap(session, p.id, T_base + timedelta(hours=5),
          size_value=15.0, size_unit="oz", price=None)

    # New "after" enriched point (self-contained, well after gap)
    T_new = _t(days_ago=1)
    _snap(session, p.id, T_new, size_value=14.0, size_unit="oz", price=4.99)
    session.commit()

    flag, _ = _run_try_detect(session, p)
    # Old enriched obs was rejected (ambiguous) → only 1 enriched obs total → no flag
    assert flag is None


def test_unambiguous_pairing_accepted(session):
    """
    Price-only Kroger snapshot with exactly ONE size snapshot in window → accepted.
    """
    p = _product(session)
    T_old = _t(days_ago=45)
    # Price-only snapshot (no size)
    price_snap = _snap(session, p.id, T_old, size_value=None, size_unit=None,
                       price=4.99, data_source="live_kroger")
    # Exactly one size candidate within 24h
    size_snap = _snap(session, p.id, T_old + timedelta(hours=3),
                      size_value=16.0, size_unit="oz", price=None)

    T_new = _t(days_ago=1)
    _snap(session, p.id, T_new, size_value=14.0, size_unit="oz", price=4.99)
    session.commit()

    flag, _ = _run_try_detect(session, p)
    assert flag is not None
    assert flag.old_size == 16.0
    assert flag.new_size == 14.0


# ---------------------------------------------------------------------------
# [12] Phase 5.1: First-valid-transition (price hike before shrink)
# ---------------------------------------------------------------------------

def test_first_valid_transition_skips_pre_shrink_price_hike(session):
    """
    Timeline:
      t0 (-100d): 16oz @ $3.00  (PPU = 0.1875)
      t1 (-60d):  16oz @ $4.99  (PPU = 0.3119) ← price hike, no size change
      t2 (-1d):   14oz @ $4.99  (PPU = 0.3564) ← shrink

    The detector should pair t1→t2 (not t0→t2), so that:
      - The PPU delta is based on the pre-shrink price ($4.99), not the old price ($3.00)
      - The flagged old_price reflects the actual price at shrink time
    """
    p = _product(session)
    t0 = _t(days_ago=100)
    t1 = _t(days_ago=60)
    t2 = _t(days_ago=1)

    _snap(session, p.id, t0, size_value=16.0, size_unit="oz", price=3.00)
    s1 = _snap(session, p.id, t1, size_value=16.0, size_unit="oz", price=4.99)
    s2 = _snap(session, p.id, t2, size_value=14.0, size_unit="oz", price=4.99)
    session.commit()

    flag, _ = _run_try_detect(session, p)
    assert flag is not None
    # Must use t1 as old_obs (latest valid old), not t0
    assert flag.old_price == pytest.approx(4.99)
    assert flag.old_size == 16.0
    assert flag.new_size == 14.0
    # PPU delta should be based on t1 price, not t0 price
    expected_ppu_pct = ((4.99 / 14.0) - (4.99 / 16.0)) / (4.99 / 16.0) * 100
    assert flag.price_per_unit_increase_pct == pytest.approx(expected_ppu_pct, rel=0.01)


# ---------------------------------------------------------------------------
# [13] Phase 5.1: Evidence ID population
# ---------------------------------------------------------------------------

def test_evidence_ids_self_contained(session):
    """Self-contained snapshots: size_snap_id == price_snap_id → size fields NULL."""
    p = _product(session)
    s1 = _snap(session, p.id, _t(days_ago=45), size_value=16.0, size_unit="oz", price=4.99)
    s2 = _snap(session, p.id, _t(days_ago=1),  size_value=14.0, size_unit="oz", price=4.99)
    session.commit()

    flag, _ = _run_try_detect(session, p)
    assert flag is not None
    # Price snapshot IDs populated
    assert flag.evidence_old_snapshot_id == s1.id
    assert flag.evidence_new_snapshot_id == s2.id
    # Size snapshot IDs NULL (self-contained)
    assert flag.evidence_old_size_snapshot_id is None
    assert flag.evidence_new_size_snapshot_id is None


def test_evidence_ids_temporal_pair(session):
    """Temporal pair: size and price from different snapshots → all 4 IDs populated."""
    p = _product(session)
    T_old = _t(days_ago=45)

    # Old: price-only Kroger snap + size OFF snap within 24h
    price_snap_old = _snap(session, p.id, T_old,
                           size_value=None, size_unit=None, price=4.99,
                           data_source="live_kroger")
    size_snap_old = _snap(session, p.id, T_old + timedelta(hours=3),
                          size_value=16.0, size_unit="oz", price=None,
                          data_source="live_openfoodfacts")

    # New: self-contained (both size and price)
    T_new = _t(days_ago=1)
    snap_new = _snap(session, p.id, T_new, size_value=14.0, size_unit="oz", price=4.99)
    session.commit()

    flag, _ = _run_try_detect(session, p)
    assert flag is not None

    # Old evidence: price from Kroger snap, size from OFF snap
    assert flag.evidence_old_snapshot_id == price_snap_old.id
    assert flag.evidence_old_size_snapshot_id == size_snap_old.id

    # New evidence: self-contained (price snap id = size snap id → size field NULL)
    assert flag.evidence_new_snapshot_id == snap_new.id
    assert flag.evidence_new_size_snapshot_id is None


# ---------------------------------------------------------------------------
# [14] Temporal pair: size candidate outside window is not used
# ---------------------------------------------------------------------------

def test_temporal_pair_outside_window_ignored(session):
    """Size snapshot > 24h away from price snapshot → no pairing → no enriched obs."""
    p = _product(session)
    T_base = _t(days_ago=45)
    # Price-only Kroger
    _snap(session, p.id, T_base, size_value=None, size_unit=None,
          price=4.99, data_source="live_kroger")
    # Size snapshot 25h away (outside 24h window)
    _snap(session, p.id, T_base + timedelta(hours=25),
          size_value=16.0, size_unit="oz", price=None)

    T_new = _t(days_ago=1)
    _snap(session, p.id, T_new, size_value=14.0, size_unit="oz", price=4.99)
    session.commit()

    flag, _ = _run_try_detect(session, p)
    # Old enriched obs failed to build (no candidate in window) → only 1 enriched obs
    assert flag is None


# ---------------------------------------------------------------------------
# [15] Unit family mismatch rejected
# ---------------------------------------------------------------------------

def test_incompatible_unit_families_rejected(session):
    """oz (mass) vs fl oz (volume) comparison should be rejected."""
    p = _product(session)
    _snap(session, p.id, _t(days_ago=45), size_value=16.0, size_unit="oz",    price=4.99)
    _snap(session, p.id, _t(days_ago=1),  size_value=14.0, size_unit="fl oz", price=4.99)
    session.commit()

    flag, stats = _run_try_detect(session, p)
    assert flag is None
    assert stats["rejected_incompatible_units"] >= 1


# ---------------------------------------------------------------------------
# [16] Only one snapshot → no flag
# ---------------------------------------------------------------------------

def test_single_snapshot_no_flag(session):
    p = _product(session)
    _snap(session, p.id, _t(days_ago=45), size_value=16.0, size_unit="oz", price=4.99)
    session.commit()

    flag, _ = _run_try_detect(session, p)
    assert flag is None
