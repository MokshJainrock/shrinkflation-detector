from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON,
    create_engine, UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from config.settings import DATABASE_URL

Base = declarative_base()


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(500), nullable=False)
    brand = Column(String(500))
    category = Column(String(255))
    barcode = Column(String(100), nullable=True)
    retailer = Column(String(100), default="openfoodfacts")
    image_url = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    snapshots = relationship("ProductSnapshot", back_populates="product", order_by="ProductSnapshot.scraped_at")
    flags = relationship("ShrinkflationFlag", back_populates="product")

    __table_args__ = (
        UniqueConstraint("name", "brand", "retailer", name="uq_product_name_brand_retailer"),
    )


class ProductSnapshot(Base):
    __tablename__ = "product_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    size_value = Column(Float, nullable=True)
    size_unit = Column(String(50), nullable=True)
    price = Column(Float, nullable=True)
    price_per_unit = Column(Float, nullable=True)
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
    connect_args = {}
    if DATABASE_URL.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_engine(DATABASE_URL, connect_args=connect_args)


def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("Database tables created successfully.")
