"""Database utility functions for Streamlit pages."""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
from sqlalchemy import desc, func, and_
from sqlalchemy.orm import Session

from db.models import Market, Event, MarketSnapshot, Category


def get_new_events(
    db: Session, 
    window_hours: int = 24,
    search_term: Optional[str] = None,
    category_filter: Optional[str] = None
) -> pd.DataFrame:
    """Get new events within time window."""
    cutoff = datetime.utcnow() - timedelta(hours=window_hours)
    
    query = db.query(
        Event.event_ticker,
        Event.title,
        Event.category,
        Event.first_seen_at,
        func.sum(Market.volume).label("total_volume"),
        func.count(Market.ticker).label("market_count")
    ).join(
        Market, Market.event_ticker == Event.event_ticker
    ).filter(
        Event.first_seen_at >= cutoff
    )
    
    if search_term:
        query = query.filter(
            Event.title.ilike(f"%{search_term}%")
        )
    
    if category_filter and category_filter != "All":
        query = query.filter(Event.category == category_filter)
    
    query = query.group_by(
        Event.event_ticker, Event.title, Event.category, Event.first_seen_at
    ).order_by(
        desc("total_volume")
    )
    
    results = query.all()
    
    return pd.DataFrame([
        {
            "Event Ticker": r.event_ticker,
            "Title": r.title,
            "Category": r.category or "N/A",
            "Opened": r.first_seen_at.strftime("%Y-%m-%d %H:%M UTC"),
            "Total Volume": int(r.total_volume or 0),
            "Markets": int(r.market_count)
        }
        for r in results
    ])


def get_markets_for_event(db: Session, event_ticker: str) -> pd.DataFrame:
    """Get all markets for an event."""
    markets = db.query(Market).filter(
        Market.event_ticker == event_ticker
    ).order_by(
        desc(Market.volume)
    ).all()
    
    return pd.DataFrame([
        {
            "Ticker": m.ticker,
            "Title": m.title,
            "Opened": m.open_time.strftime("%Y-%m-%d %H:%M UTC") if m.open_time else "N/A",
            "Closes": m.close_time.strftime("%Y-%m-%d %H:%M UTC") if m.close_time else "N/A",
            "Volume": int(m.volume or 0),
            "Yes Bid": f"{m.yes_bid}¢" if m.yes_bid else "—",
            "Yes Ask": f"{m.yes_ask}¢" if m.yes_ask else "—",
            "Last Price": f"{m.last_price}¢" if m.last_price else "—",
            "Status": m.status
        }
        for m in markets
    ])


def get_trending_markets(
    db: Session,
    search_term: Optional[str] = None,
    category_filter: Optional[str] = None
) -> pd.DataFrame:
    """Get trending markets."""
    query = db.query(Market, Event).join(
        Event, Market.event_ticker == Event.event_ticker
    ).filter(
        Market.is_trending == True,
        Market.status == "open"
    )
    
    if search_term:
        query = query.filter(
            Market.title.ilike(f"%{search_term}%")
        )
    
    if category_filter and category_filter != "All":
        query = query.filter(Event.category == category_filter)
    
    query = query.order_by(desc(Market.volume_24h))
    
    results = query.all()
    
    return pd.DataFrame([
        {
            "Ticker": m.ticker,
            "Market Title": m.title,
            "Event": e.title,
            "Category": e.category or "N/A",
            "24h Volume": int(m.volume_24h or 0),
            "Total Volume": int(m.volume or 0),
            "Yes Bid": f"{m.yes_bid}¢" if m.yes_bid else "—",
            "Yes Ask": f"{m.yes_ask}¢" if m.yes_ask else "—",
            "Event Ticker": e.event_ticker
        }
        for m, e in results
    ])


def get_mention_markets(
    db: Session,
    new_window_hours: int = 24,
    search_term: Optional[str] = None
) -> pd.DataFrame:
    """Get mention markets sorted by expiration."""
    cutoff = datetime.utcnow() - timedelta(hours=new_window_hours)
    
    query = db.query(Market, Event).join(
        Event, Market.event_ticker == Event.event_ticker
    ).filter(
        Market.is_mention == True,
        Market.status == "open",
        Market.expiration_time.isnot(None)
    )
    
    if search_term:
        query = query.filter(
            Market.title.ilike(f"%{search_term}%")
        )
    
    query = query.order_by(Market.expiration_time.asc())
    
    results = query.all()
    
    data = []
    for m, e in results:
        is_new = m.first_seen_at >= cutoff
        
        # Calculate time remaining
        time_remaining = "N/A"
        if m.expiration_time:
            delta = m.expiration_time - datetime.utcnow()
            if delta.total_seconds() > 0:
                days = delta.days
                hours = delta.seconds // 3600
                minutes = (delta.seconds % 3600) // 60
                if days > 0:
                    time_remaining = f"{days}d {hours}h"
                elif hours > 0:
                    time_remaining = f"{hours}h {minutes}m"
                else:
                    time_remaining = f"{minutes}m"
            else:
                time_remaining = "Expired"
        
        data.append({
            "New": "🆕" if is_new else "",
            "Ticker": m.ticker,
            "Market Title": m.title,
            "Event": e.title,
            "Category": e.category or "N/A",
            "Expires": m.expiration_time.strftime("%Y-%m-%d %H:%M UTC") if m.expiration_time else "N/A",
            "Time Remaining": time_remaining,
            "Yes Bid": f"{m.yes_bid}¢" if m.yes_bid else "—",
            "Yes Ask": f"{m.yes_ask}¢" if m.yes_ask else "—",
            "Event Ticker": e.event_ticker
        })
    
    return pd.DataFrame(data)


def get_relative_volume_events(
    db: Session,
    period_hours: int = 24,
    baseline_days: int = 7,
    search_term: Optional[str] = None
) -> pd.DataFrame:
    """Get events with high relative volume (excluding sports)."""
    # Get sports categories
    sports_cats = db.query(Category.name).filter(
        Category.is_sports == True
    ).all()
    sports_categories = [cat[0] for cat in sports_cats]
    
    current_cutoff = datetime.utcnow() - timedelta(hours=period_hours)
    baseline_cutoff = datetime.utcnow() - timedelta(days=baseline_days)
    
    # Get events with current volume
    query = db.query(
        Event.event_ticker,
        Event.title,
        Event.category,
        func.sum(Market.volume).label("current_volume")
    ).join(
        Market, Market.event_ticker == Event.event_ticker
    ).filter(
        Market.status == "open"
    )
    
    if sports_categories:
        query = query.filter(~Event.category.in_(sports_categories))
    
    if search_term:
        query = query.filter(Event.title.ilike(f"%{search_term}%"))
    
    query = query.group_by(
        Event.event_ticker, Event.title, Event.category
    )
    
    events = query.all()
    
    data = []
    for event in events:
        if not event.current_volume or event.current_volume == 0:
            continue
        
        # Get baseline from snapshots
        baseline = db.query(
            func.avg(MarketSnapshot.volume).label("avg_volume")
        ).join(
            Market, Market.ticker == MarketSnapshot.ticker
        ).filter(
            Market.event_ticker == event.event_ticker,
            MarketSnapshot.snapshot_time >= baseline_cutoff,
            MarketSnapshot.snapshot_time < current_cutoff
        ).scalar()
        
        if not baseline or baseline < 100:
            continue
        
        baseline_daily = baseline / baseline_days
        relative = event.current_volume / baseline_daily if baseline_daily > 0 else 0
        
        if relative >= 1.5:  # At least 1.5x baseline
            data.append({
                "Event Ticker": event.event_ticker,
                "Title": event.title,
                "Category": event.category or "N/A",
                "Current Volume": int(event.current_volume),
                "Baseline Avg": int(baseline_daily),
                "Relative": round(relative, 2),
                "Confidence": "High" if baseline_daily >= 1000 else "Medium" if baseline_daily >= 500 else "Low"
            })
    
    # Sort by relative volume
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values("Relative", ascending=False)
    
    return df


def get_daily_volume_history(
    db: Session,
    event_ticker: str,
    days: int = 30
) -> pd.DataFrame:
    """Get daily volume history for an event."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    # Get snapshots grouped by day
    results = db.query(
        func.date(MarketSnapshot.snapshot_time).label("date"),
        func.sum(MarketSnapshot.volume).label("total_volume")
    ).join(
        Market, Market.ticker == MarketSnapshot.ticker
    ).filter(
        Market.event_ticker == event_ticker,
        MarketSnapshot.snapshot_time >= cutoff
    ).group_by(
        func.date(MarketSnapshot.snapshot_time)
    ).order_by(
        func.date(MarketSnapshot.snapshot_time).asc()
    ).all()
    
    return pd.DataFrame([
        {
            "Date": r.date.strftime("%Y-%m-%d"),
            "Volume": int(r.total_volume or 0)
        }
        for r in results
    ])


def get_all_categories(db: Session) -> List[str]:
    """Get all unique categories."""
    categories = db.query(Event.category).distinct().filter(
        Event.category.isnot(None)
    ).all()
    return ["All"] + sorted([cat[0] for cat in categories if cat[0]])
