"""
Database models for the Shrinkflation Detector.

Source labels used throughout:
  data_source (Product, ProductSnapshot):
    - "documented_historical"  : seeded from verified_cases.py research
    - "live_openfoodfacts"     : fetched from Open Food Facts API at runtime
    - "live_kroger"            : fetched from Kroger API at runtime
    - "live_combined"          : snapshot enriched from multiple live sources

  flag_source (ShrinkflationFlag):
    - "documented_historical"  : pre-seeded from published research
    - "live_detected"          : created by the live detector with real snapshots

  observation_type (ProductSnapshot):
    - "real_observed"          : timestamp is an actual API fetch time
    - "documented_reference"   : timestamp is a year-level approximation from
                                 historical research (not a real observation time)

  size_unit_family (ProductSnapshot):
    - "mass"    : g, kg, oz, lb
    - "volume"  : ml, l, fl oz, fl_oz
    - "count"   : pcs, units, ct, count, sheets, pods
    - "unknown" : anything else
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint, create_engine, text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from config.settings import DATABASE_URL

Base = declarative_base()

# ---------------------------------------------------------------------------
# Unit family lookup — used at insert time to populate size_unit_family
# ---------------------------------------------------------------------------
_MASS_UNITS = {"g", "kg", "oz", "lb", "lbs", "gram", "grams", "ounce", "ounces", "pound", "pounds"}
_VOLUME_UNITS = {"ml", "l", "litre", "liter", "litres", "liters", "fl oz", "fl_oz", "floz",
                 "fluid ounce", "fluid ounces", "cl", "dl"}
_COUNT_UNITS = {"pcs", "pieces", "ct", "count", "units", "unit", "sheets", "pods", "tabs",
                "tablets", "capsules", "caps", "wipes", "bags", "sachets"}


def resolve_unit_family(unit: Optional[str]) -> str:
    """Return the unit family for a size unit string."""
    if not unit:
        return "unknown"
    u = unit.strip().lower()
    if u in _MASS_UNITS:
        return "mass"
    if u in _VOLUME_UNITS:
        return "volume"
    if u in _COUNT_UNITS:
        return "count"
    return "unknown"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Product(Base):
    """
    A product tracked in the database.

    One row per (name, brand, data_source) — the same physical product may
    have separate rows for live_openfoodfacts and live_kroger sources until
    a future merge pass links them via identity_key.
    """
    __tablename__ = "products"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(500), nullable=False)
    brand       = Column(String(500), nullable=False, default="Unknown")
    category    = Column(String(255), nullable=True)
    barcode     = Column(String(100), nullable=True)

    # Where the product record came from
    data_source = Column(String(50), nullable=False)
    # "documented_historical" | "live_openfoodfacts" | "live_kroger"

    # Actual retail store (Kroger, Walmart, etc.) — separate from data_source
    # For documented_historical rows, this holds the research source attribution
    # (e.g. "BLS/Consumer Reports", "mouseprint.org")
    retailer    = Column(String(200), nullable=True)

    # Normalised lower-case "{brand}::{name}" for soft deduplication queries.
    # NOT unique — same product can arrive from multiple sources.
    identity_key = Column(String(700), nullable=True, index=True)

    image_url   = Column(String(1000), nullable=True)
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    snapshots = relationship(
        "ProductSnapshot",
        back_populates="product",
        order_by="ProductSnapshot.scraped_at",
    )
    flags = relationship("ShrinkflationFlag", back_populates="product")

    __table_args__ = (
        # Prevents the same product from the same data source being inserted twice.
        UniqueConstraint("name", "brand", "data_source", name="uq_product_name_brand_source"),
        Index("ix_products_data_source", "data_source"),
        Index("ix_products_category", "category"),
    )


class ProductSnapshot(Base):
    """
    A point-in-time observation of a product's size and/or price.

    For historical products, two snapshots are created (before + after) with
    observation_type="documented_reference" to signal the timestamps are
    year-level approximations, not real fetch times.

    For live products, observation_type="real_observed" and scraped_at is the
    actual UTC time the API was called.
    """
    __tablename__ = "product_snapshots"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    product_id  = Column(Integer, ForeignKey("products.id"), nullable=False)

    size_value  = Column(Float, nullable=True)
    size_unit   = Column(String(50), nullable=True)

    # Derived from size_unit at insert time. Enables cross-unit family filtering.
    # "mass" | "volume" | "count" | "unknown"
    size_unit_family = Column(String(20), nullable=True)

    price           = Column(Float, nullable=True)
    price_per_unit  = Column(Float, nullable=True)  # price / size_value

    # Where this observation came from
    data_source = Column(String(50), nullable=False)
    # "documented_historical" | "live_openfoodfacts" | "live_kroger" | "live_combined"

    # Whether the timestamp is real or a year-level approximation
    observation_type = Column(String(30), nullable=False, default="real_observed")
    # "real_observed" | "documented_reference"

    scraped_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    product = relationship("Product", back_populates="snapshots")

    __table_args__ = (
        # Composite index for the most common query: latest snapshot per product
        Index("ix_snapshots_product_scraped", "product_id", "scraped_at"),
        Index("ix_snapshots_data_source", "data_source"),
    )


class ShrinkflationFlag(Base):
    """
    A confirmed or documented shrinkflation event.

    Strict rule enforced by has_price_evidence:
      - has_price_evidence=True  → both old_price and new_price are non-null.
        This is the only kind that counts as a live detection.
      - has_price_evidence=False → size-only observation. Only valid for
        flag_source="documented_historical" where the research source
        confirms shrinkflation independently of our price data.

    Live detectors (detector.py, live_tracker.py) MUST NOT create flags with
    has_price_evidence=False. That enforcement lives in the detector code, but
    this schema makes the state queryable and auditable.

    Evidence linkage: evidence_old_snapshot_id and evidence_new_snapshot_id
    point to the two ProductSnapshot rows that triggered this flag. These are
    nullable for documented_historical flags (which predate our snapshot system)
    but required for live_detected flags.

    Deduplication: dedupe_key is a unique constraint that prevents the same
    product transition from being re-flagged across ingestion runs.
    """
    __tablename__ = "shrinkflation_flags"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    product_id  = Column(Integer, ForeignKey("products.id"), nullable=False)

    # Origin of this flag
    flag_source = Column(String(30), nullable=False)
    # "documented_historical" | "live_detected"

    # Size evidence
    old_size    = Column(Float, nullable=True)
    new_size    = Column(Float, nullable=True)
    size_unit   = Column(String(50), nullable=True)  # unit for old_size/new_size

    # Price evidence
    old_price   = Column(Float, nullable=True)
    new_price   = Column(Float, nullable=True)

    # Whether both old_price and new_price are non-null.
    # Queryable enforcement of the "no size-only inference" rule.
    has_price_evidence = Column(Boolean, nullable=False, default=False)

    # Price-per-unit change percentage. Only meaningful when has_price_evidence=True.
    # Renamed from real_price_increase_pct for accuracy.
    price_per_unit_increase_pct = Column(Float, nullable=True)

    severity    = Column(String(10), nullable=True)  # HIGH | MEDIUM | LOW | None

    # Links back to the exact snapshots that generated this flag.
    #
    # For self-contained observations (size and price from the same snapshot):
    #   evidence_old_snapshot_id  = that snapshot's id
    #   evidence_old_size_snapshot_id = NULL  (redundant — same row)
    #
    # For temporal-pair observations (OFF size snap + Kroger price snap):
    #   evidence_old_snapshot_id  = the PRICE snapshot id  (Kroger)
    #   evidence_old_size_snapshot_id = the SIZE snapshot id   (OFF)
    #
    # This makes every flag fully auditable: both the price source and the
    # size source are directly traceable without secondary time-range queries.
    #
    # Nullable for documented_historical flags (which predate our snapshot system).
    # Required for live_detected flags.
    evidence_old_snapshot_id = Column(
        Integer, ForeignKey("product_snapshots.id"), nullable=True
    )
    evidence_new_snapshot_id = Column(
        Integer, ForeignKey("product_snapshots.id"), nullable=True
    )
    # Size-source snapshots — NULL when size and price came from the same row.
    evidence_old_size_snapshot_id = Column(
        Integer, ForeignKey("product_snapshots.id"), nullable=True
    )
    evidence_new_size_snapshot_id = Column(
        Integer, ForeignKey("product_snapshots.id"), nullable=True
    )

    detected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Unique key to prevent re-flagging the same transition.
    # Format: "{product_id}::{old_size}::{new_size}::{flag_source}"
    dedupe_key  = Column(String(300), nullable=True, unique=True)

    product = relationship("Product", back_populates="flags")
    evidence_old_snapshot = relationship(
        "ProductSnapshot", foreign_keys=[evidence_old_snapshot_id]
    )
    evidence_new_snapshot = relationship(
        "ProductSnapshot", foreign_keys=[evidence_new_snapshot_id]
    )
    evidence_old_size_snapshot = relationship(
        "ProductSnapshot", foreign_keys=[evidence_old_size_snapshot_id]
    )
    evidence_new_size_snapshot = relationship(
        "ProductSnapshot", foreign_keys=[evidence_new_size_snapshot_id]
    )

    __table_args__ = (
        Index("ix_flags_flag_source", "flag_source"),
        Index("ix_flags_has_price_evidence", "has_price_evidence"),
        Index("ix_flags_product_detected", "product_id", "detected_at"),
    )


class IngestionRun(Base):
    """
    Audit log for each ingestion cycle.

    Supports fill-phase vs track-phase distinction:
      - phase="fill"  : initial seed (historical load, one-time scrape)
      - phase="track" : ongoing live scan (every 30 minutes)

    A run is inserted at start with status="running", then updated at end.
    If the process crashes, status stays "running" — detectable as a stale run.
    """
    __tablename__ = "ingestion_runs"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    source        = Column(String(50), nullable=False)
    # "openfoodfacts" | "kroger" | "detector" | "historical_load"

    phase         = Column(String(20), nullable=False, default="track")
    # "fill" | "track"

    started_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at   = Column(DateTime, nullable=True)  # None if still running

    products_added   = Column(Integer, nullable=False, default=0)
    snapshots_added  = Column(Integer, nullable=False, default=0)
    flags_added      = Column(Integer, nullable=False, default=0)
    errors_count     = Column(Integer, nullable=False, default=0)

    status  = Column(String(20), nullable=False, default="running")
    # "running" | "complete" | "failed"

    notes   = Column(Text, nullable=True)  # Error details or skip reason

    __table_args__ = (
        Index("ix_ingestion_runs_source_started", "source", "started_at"),
    )


class AgentInsight(Base):
    """AI-generated analysis stored for display on the dashboard."""
    __tablename__ = "agent_insights"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    insight_type  = Column(String(50))           # "daily" | "weekly" | "chat"
    content       = Column(Text)
    generated_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    data_snapshot = Column(Text, nullable=True)  # JSON stored as text (SQLite compat)


# ---------------------------------------------------------------------------
# Engine singleton — created once per process, not once per call
# ---------------------------------------------------------------------------
_engine = None


def get_engine():
    """Return the SQLAlchemy engine, creating it on first call."""
    global _engine
    if _engine is None:
        connect_args = {}
        if DATABASE_URL.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        _engine = create_engine(DATABASE_URL, connect_args=connect_args)
    return _engine


def get_session():
    """Return a new SQLAlchemy session bound to the singleton engine."""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def add_missing_columns():
    """
    Idempotent ALTER TABLE migration for databases created with an older schema.

    SQLAlchemy's create_all(checkfirst=True) creates missing *tables* but never
    adds new columns to existing tables.  This function bridges that gap by
    issuing explicit ALTER TABLE … ADD COLUMN statements for every column that
    was introduced after the initial schema, using try/except so re-running it
    against an already-migrated (or freshly created) database is always safe.

    Column type strings use SQLite affinity names (TEXT, REAL, INTEGER) so this
    function works with SQLite regardless of the SQLAlchemy column type used in
    the ORM definitions above.

    Call this once, right after create_all(), inside init_db().
    """
    engine = get_engine()

    # Each entry: (table_name, column_name, sqlite_column_definition)
    #
    # IMPORTANT: SQLite does NOT allow ALTER TABLE ADD COLUMN with UNIQUE
    # or NOT NULL (without DEFAULT) constraints when the table already
    # contains rows.  Columns that need UNIQUE are added plain here and
    # then get a CREATE UNIQUE INDEX below.
    _MIGRATIONS: list[tuple[str, str, str]] = [
        # products
        ("products", "data_source",   "TEXT DEFAULT 'documented_historical'"),
        ("products", "identity_key",  "TEXT"),

        # product_snapshots
        ("product_snapshots", "size_unit_family", "TEXT"),
        ("product_snapshots", "data_source",       "TEXT DEFAULT 'documented_historical'"),
        ("product_snapshots", "observation_type",  "TEXT DEFAULT 'real_observed'"),

        # shrinkflation_flags
        ("shrinkflation_flags", "flag_source",                  "TEXT DEFAULT 'documented_historical'"),
        ("shrinkflation_flags", "size_unit",                    "TEXT"),
        ("shrinkflation_flags", "has_price_evidence",           "INTEGER DEFAULT 0"),
        ("shrinkflation_flags", "price_per_unit_increase_pct",  "REAL"),
        ("shrinkflation_flags", "evidence_old_snapshot_id",     "INTEGER"),
        ("shrinkflation_flags", "evidence_new_snapshot_id",     "INTEGER"),
        ("shrinkflation_flags", "evidence_old_size_snapshot_id","INTEGER"),
        ("shrinkflation_flags", "evidence_new_size_snapshot_id","INTEGER"),
        ("shrinkflation_flags", "dedupe_key",                   "TEXT"),
    ]

    # Unique indexes to create after columns exist.
    # CREATE UNIQUE INDEX IF NOT EXISTS is idempotent and works on
    # existing tables — unlike the UNIQUE constraint in ADD COLUMN.
    _INDEXES: list[tuple[str, str, str]] = [
        # (index_name, table_name, column_name)
        ("uq_flags_dedupe_key", "shrinkflation_flags", "dedupe_key"),
    ]

    with engine.connect() as conn:
        for table, column, definition in _MIGRATIONS:
            try:
                conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                )
                conn.commit()
            except Exception:
                # Column already exists (OperationalError) — safe to ignore.
                conn.rollback()

        for idx_name, table, column in _INDEXES:
            try:
                conn.execute(
                    text(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx_name} ON {table}({column})")
                )
                conn.commit()
            except Exception:
                conn.rollback()


def init_db():
    """Create all tables that do not exist, then migrate any missing columns."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    add_missing_columns()
