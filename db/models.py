"""SQLAlchemy models for Kalshi markets data."""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, TIMESTAMP, 
    ForeignKey, Index, ARRAY, JSON, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base


class Event(Base):
    """Event model."""
    __tablename__ = "events"
    
    event_ticker = Column(String(100), primary_key=True)
    series_ticker = Column(String(100), index=True)
    title = Column(Text, nullable=False)
    sub_title = Column(Text)
    category = Column(String(100), index=True)
    mutually_exclusive = Column(Boolean, default=True)
    strike_date = Column(TIMESTAMP(timezone=True))
    strike_period = Column(String(50))
    created_at = Column(TIMESTAMP(timezone=True), default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())
    first_seen_at = Column(TIMESTAMP(timezone=True), default=func.now())
    
    # Relationship to markets
    markets = relationship("Market", back_populates="event", cascade="all, delete-orphan")


class Market(Base):
    """Market model."""
    __tablename__ = "markets"
    
    ticker = Column(String(100), primary_key=True)
    event_ticker = Column(String(100), ForeignKey("events.event_ticker", ondelete="CASCADE"), index=True)
    market_type = Column(String(20), default="binary")
    title = Column(Text, nullable=False)
    subtitle = Column(Text)
    yes_sub_title = Column(Text)
    no_sub_title = Column(Text)
    
    # Timestamps
    created_time = Column(TIMESTAMP(timezone=True), index=True)
    updated_time = Column(TIMESTAMP(timezone=True))
    open_time = Column(TIMESTAMP(timezone=True), index=True)
    close_time = Column(TIMESTAMP(timezone=True), index=True)
    expiration_time = Column(TIMESTAMP(timezone=True), index=True)
    settlement_timer_seconds = Column(Integer)
    
    # Status and trading data
    status = Column(String(20), index=True)
    volume = Column(Integer, default=0)
    volume_24h = Column(Integer, default=0, index=True)
    open_interest = Column(Integer, default=0)
    
    # Prices (in cents)
    yes_bid = Column(Integer)
    yes_ask = Column(Integer)
    no_bid = Column(Integer)
    no_ask = Column(Integer)
    last_price = Column(Integer)
    liquidity = Column(Integer)
    
    # Other properties
    can_close_early = Column(Boolean, default=False)
    result = Column(String(10))
    settlement_value = Column(Integer)
    settlement_ts = Column(TIMESTAMP(timezone=True))
    
    # Custom flags
    is_mention = Column(Boolean, default=False, index=True)
    is_trending = Column(Boolean, default=False, index=True)
    
    # Tracking timestamps
    first_seen_at = Column(TIMESTAMP(timezone=True), default=func.now(), index=True)
    last_updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationship to event
    event = relationship("Event", back_populates="markets")
    
    # Relationship to snapshots
    snapshots = relationship("MarketSnapshot", back_populates="market", cascade="all, delete-orphan")


class MarketSnapshot(Base):
    """Market snapshot for time-series data."""
    __tablename__ = "market_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(100), ForeignKey("markets.ticker", ondelete="CASCADE"), nullable=False)
    snapshot_time = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    
    # Snapshot data
    volume = Column(Integer)
    volume_24h = Column(Integer)
    open_interest = Column(Integer)
    yes_bid = Column(Integer)
    yes_ask = Column(Integer)
    no_bid = Column(Integer)
    no_ask = Column(Integer)
    last_price = Column(Integer)
    liquidity = Column(Integer)
    
    created_at = Column(TIMESTAMP(timezone=True), default=func.now())
    
    # Relationship to market
    market = relationship("Market", back_populates="snapshots")
    
    __table_args__ = (
        Index("idx_snapshots_ticker_time", "ticker", "snapshot_time"),
    )


class EmailSettings(Base):
    """Email settings model (singleton)."""
    __tablename__ = "email_settings"
    
    id = Column(Integer, primary_key=True, default=1)
    recipients = Column(ARRAY(Text), nullable=False, default=["surfshopcapital@gmail.com"])
    send_times = Column(ARRAY(Text), nullable=False, default=["06:00", "12:00", "18:00", "00:00"])
    timezone = Column(String(50), nullable=False, default="America/New_York")
    enabled_sections = Column(
        JSON, 
        nullable=False, 
        default={"new_markets": True, "trending": True, "mentions": True, "relative_volume": True}
    )
    new_markets_window_hours = Column(Integer, nullable=False, default=24)
    mentions_new_window_hours = Column(Integer, nullable=False, default=24)
    relative_volume_period_hours = Column(Integer, nullable=False, default=24)
    relative_volume_baseline_days = Column(Integer, nullable=False, default=7)
    relative_volume_top_n = Column(Integer, nullable=False, default=10)
    updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        CheckConstraint("id = 1", name="check_single_row"),
    )


class EmailDigestLog(Base):
    """Email digest log model."""
    __tablename__ = "email_digest_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sent_at = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    recipients = Column(ARRAY(Text), nullable=False)
    sections_included = Column(ARRAY(Text), nullable=False)
    new_markets_count = Column(Integer, default=0)
    trending_markets_count = Column(Integer, default=0)
    mentions_count = Column(Integer, default=0)
    relative_volume_count = Column(Integer, default=0)
    success = Column(Boolean, nullable=False)
    error_message = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now())


class Category(Base):
    """Category model for sports exclusion."""
    __tablename__ = "categories"
    
    name = Column(String(100), primary_key=True)
    is_sports = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now())
