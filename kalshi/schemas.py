"""Pydantic models for Kalshi API responses."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class MarketResponse(BaseModel):
    """Market response model."""
    ticker: str
    event_ticker: str
    market_type: str = "binary"
    title: str
    subtitle: Optional[str] = None
    yes_sub_title: Optional[str] = None
    no_sub_title: Optional[str] = None
    created_time: Optional[datetime] = None
    updated_time: Optional[datetime] = None
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    expiration_time: Optional[datetime] = None
    latest_expiration_time: Optional[datetime] = None
    settlement_timer_seconds: Optional[int] = None
    status: str
    volume: Optional[int] = 0
    volume_fp: Optional[str] = None
    volume_24h: Optional[int] = 0
    volume_24h_fp: Optional[str] = None
    open_interest: Optional[int] = 0
    open_interest_fp: Optional[str] = None
    yes_bid: Optional[int] = None
    yes_ask: Optional[int] = None
    no_bid: Optional[int] = None
    no_ask: Optional[int] = None
    last_price: Optional[int] = None
    liquidity: Optional[int] = None
    can_close_early: bool = False
    result: Optional[str] = None
    settlement_value: Optional[int] = None
    settlement_ts: Optional[datetime] = None


class EventResponse(BaseModel):
    """Event response model."""
    event_ticker: str
    series_ticker: Optional[str] = None
    title: str
    sub_title: Optional[str] = None
    category: Optional[str] = None
    mutually_exclusive: bool = True
    strike_date: Optional[datetime] = None
    strike_period: Optional[str] = None
    markets: Optional[List[MarketResponse]] = []


class MarketsListResponse(BaseModel):
    """Markets list response."""
    markets: List[MarketResponse]
    cursor: Optional[str] = None


class EventsListResponse(BaseModel):
    """Events list response."""
    events: List[EventResponse]
    cursor: Optional[str] = None


class SeriesResponse(BaseModel):
    """Series response model."""
    ticker: str
    title: str
    frequency: Optional[str] = None
    category: Optional[str] = None


class TagsByCategoriesResponse(BaseModel):
    """Tags by categories response."""
    tags_by_categories: Dict[str, Optional[List[str]]] = {}
    
    @field_validator('tags_by_categories', mode='before')
    @classmethod
    def handle_none_categories(cls, v):
        """Convert None values to empty lists."""
        if isinstance(v, dict):
            return {k: ([] if val is None else val) for k, val in v.items()}
        return v
