from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON,
    create_engine, event, UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from config.settings import DATABASE_URL

Base = declarative_base()
_ENGINE = None
_SESSION_FACTORY = None


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(500), nullable=False)
    brand = Column(String(500))
    category = Column(String(255))
    barcode = Column(String(100), nullable=True)
    retailer = Column(String(100), default="openfoodfacts")
    source_key = Column(String(255), nullable=False)
    image_url = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    source_last_modified_at = Column(DateTime, nullable=True)

    snapshots = relationship("ProductSnapshot", back_populates="product", order_by="ProductSnapshot.scraped_at")
    flags = relationship("ShrinkflationFlag", back_populates="product")

    __table_args__ = (
        UniqueConstraint("source_key", "retailer", name="uq_product_source_key_retailer"),
    )


class ProductSnapshot(Base):
    __tablename__ = "product_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    size_value = Column(Float, nullable=True)
    size_unit = Column(String(50), nullable=True)
    price = Column(Float, nullable=True)
    price_per_unit = Column(Float, nullable=True)
    snapshot_type = Column(String(20), nullable=False, default="size")
    source_name = Column(String(100), nullable=False, default="openfoodfacts")
    source_updated_at = Column(DateTime, nullable=True)
    scraped_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    product = relationship("Product", back_populates="snapshots")


class ShrinkflationFlag(Base):
    __tablename__ = "shrinkflation_flags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    old_size = Column(Float)
    new_size = Column(Float)
    old_price = Column(Float)
    new_price = Column(Float)
    real_price_increase_pct = Column(Float)
    severity = Column(String(10))  # HIGH, MEDIUM, LOW
    size_unit = Column(String(50), nullable=True)
    evidence_type = Column(String(20), nullable=True)
    detected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    retailer = Column(String(100))

    product = relationship("Product", back_populates="flags")


class AgentInsight(Base):
    __tablename__ = "agent_insights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    insight_type = Column(String(50))  # daily, weekly, chat
    content = Column(Text)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    data_snapshot = Column(Text, nullable=True)  # JSON stored as text for SQLite compat


def get_engine():
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE

    connect_args = {}
    if DATABASE_URL.startswith("sqlite"):
        connect_args = {"check_same_thread": False, "timeout": 30}
    _ENGINE = create_engine(DATABASE_URL, connect_args=connect_args)

    if DATABASE_URL.startswith("sqlite"):
        @event.listens_for(_ENGINE, "connect")
        def _set_sqlite_pragmas(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA busy_timeout=30000;")
            cursor.close()

    return _ENGINE


def get_session():
    global _SESSION_FACTORY
    if _SESSION_FACTORY is None:
        _SESSION_FACTORY = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SESSION_FACTORY()


def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("Database tables created successfully.")
