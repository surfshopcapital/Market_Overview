"""Database utility functions for Streamlit pages."""
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import pandas as pd
from sqlalchemy import desc, func, and_
from sqlalchemy.orm import Session

from db.models import Market, Event, MarketSnapshot, Category


def get_new_events(
    db: Session, 
    window_hours: int = 24,
    search_term: Optional[str] = None,
    category_filter: Optional[str] = None,
    exclude_categories: Optional[List[str]] = None
) -> pd.DataFrame:
    """Get new events within time window (excluding sports + optional categories)."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    
    # Get sports categories to exclude
    sports_cats = db.query(Category.name).filter(
        Category.is_sports == True
    ).all()
    sports_categories = [cat[0] for cat in sports_cats]
    
    query = db.query(
        Event.event_ticker,
        Event.title,
        Event.category,
        Event.first_seen_at,
        func.sum(Market.volume).label("total_volume"),
        func.sum(Market.volume_24h).label("volume_24h"),
        func.count(Market.ticker).label("market_count"),
        func.max(Market.open_time).label("most_recent_market_opened")
    ).join(
        Market, Market.event_ticker == Event.event_ticker
    ).filter(
        Event.first_seen_at >= cutoff
    )
    
    # Exclude sports
    if sports_categories:
        query = query.filter(~Event.category.in_(sports_categories))
    
    # Exclude additional categories (crypto, climate, etc.)
    if exclude_categories:
        for cat in exclude_categories:
            query = query.filter(func.lower(Event.category) != cat.lower())
    
    if search_term:
        query = query.filter(Event.title.ilike(f"%{search_term}%"))
    
    if category_filter and category_filter != "All":
        query = query.filter(Event.category == category_filter)
    
    query = query.group_by(
        Event.event_ticker, Event.title, Event.category, Event.first_seen_at
    ).order_by(
        desc(func.max(Market.open_time))  # Most recent market opened first
    )
    
    results = query.all()
    
    return pd.DataFrame([
        {
            "Event Ticker": r.event_ticker,
            "Title": r.title,
            "Category": r.category or "N/A",
            "Event Opened": r.first_seen_at.strftime("%Y-%m-%d %H:%M UTC") if r.first_seen_at else "N/A",
            "Most Recent Market Opened": r.most_recent_market_opened.strftime("%Y-%m-%d %H:%M UTC") if r.most_recent_market_opened else "N/A",
            "Total Volume": int(r.total_volume or 0),
            "24h Volume": int(r.volume_24h or 0),
            "Markets": int(r.market_count)
        }
        for r in results
    ])


def get_markets_for_event(db: Session, event_ticker: str, include_trends: bool = True) -> pd.DataFrame:
    """Get all markets for an event."""
    markets = db.query(Market).filter(
        Market.event_ticker == event_ticker
    ).order_by(
        desc(Market.volume)
    ).all()
    
    data = []
    for m in markets:
        row = {
            "Yes Subtitle": m.yes_sub_title or "—",
            "Title": m.title,
            "Opened": m.open_time.strftime("%Y-%m-%d %H:%M UTC") if m.open_time else "N/A",
            "Closes": m.close_time.strftime("%Y-%m-%d %H:%M UTC") if m.close_time else "N/A",
            "Volume": int(m.volume or 0),
            "24h Volume": int(m.volume_24h or 0),
            "Open Interest": int(m.open_interest or 0),
            "Yes Bid": f"{m.yes_bid}¢" if m.yes_bid else "—",
            "Yes Ask": f"{m.yes_ask}¢" if m.yes_ask else "—",
            "Last Price": f"{m.last_price}¢" if m.last_price else "—"
        }
        if include_trends:
            row["30m Trend"] = get_price_trend(db, m.ticker, hours_ago=0.5) or "—"
            row["24h Trend"] = get_price_trend(db, m.ticker, hours_ago=24) or "—"
        row["Ticker"] = m.ticker  # Keep for Kalshi links
        data.append(row)
    
    df = pd.DataFrame(data)
    if include_trends and not df.empty:
        cols = ["Yes Subtitle", "Title", "Opened", "Closes", "Volume", "24h Volume", "Open Interest", "30m Trend", "24h Trend", "Yes Bid", "Yes Ask", "Last Price", "Ticker"]
        df = df[[c for c in cols if c in df.columns]]
    return df


def get_trending_markets(
    db: Session,
    search_term: Optional[str] = None,
    category_filter: Optional[str] = None
) -> pd.DataFrame:
    """Get trending markets (excluding sports)."""
    # Get sports categories to exclude
    sports_cats = db.query(Category.name).filter(
        Category.is_sports == True
    ).all()
    sports_categories = [cat[0] for cat in sports_cats]
    
    query = db.query(Market, Event).join(
        Event, Market.event_ticker == Event.event_ticker
    ).filter(
        Market.is_trending == True,
        Market.status.in_(['active', 'open'])
    )
    
    # Exclude sports
    if sports_categories:
        query = query.filter(~Event.category.in_(sports_categories))
    
    if search_term:
        query = query.filter(
            Market.title.ilike(f"%{search_term}%")
        )
    
    if category_filter and category_filter != "All":
        query = query.filter(Event.category == category_filter)
    
    query = query.order_by(desc(Market.volume_24h))
    
    results = query.all()
    
    data = []
    for m, e in results:
        # Calculate trends from snapshots
        trend_30m = get_price_trend(db, m.ticker, hours_ago=0.5)  # 30 minutes
        trend_24h = get_price_trend(db, m.ticker, hours_ago=24)   # 24 hours
        
        data.append({
            "Yes Subtitle": m.yes_sub_title or "—",
            "Market Title": m.title,
            "Event": e.title,
            "Category": e.category or "N/A",
            "24h Volume": int(m.volume_24h or 0),
            "Total Volume": int(m.volume or 0),
            "Open Interest": int(m.open_interest or 0),
            "Yes Bid": f"{m.yes_bid}¢" if m.yes_bid else "—",
            "Yes Ask": f"{m.yes_ask}¢" if m.yes_ask else "—",
            "Last Price": f"{m.last_price}¢" if m.last_price else "—",
            "30m Trend": trend_30m or "—",
            "24h Trend": trend_24h or "—",
            "Event Ticker": e.event_ticker,
            "Ticker": m.ticker
        })
    
    return pd.DataFrame(data)


def get_mention_events(
    db: Session,
    new_window_hours: int = 24,
    search_term: Optional[str] = None
) -> pd.DataFrame:
    """Get mention events (events with at least one mention market), sorted by soonest expiration."""
    now_utc = datetime.now(timezone.utc)
    
    # Get events that have mention markets
    subq = db.query(
        Event.event_ticker,
        Event.title,
        Event.category,
        Event.first_seen_at,
        func.count(Market.ticker).label("mention_count"),
        func.sum(Market.volume).label("total_volume"),
        func.sum(Market.volume_24h).label("volume_24h"),
        func.min(Market.expiration_time).label("soonest_expiration")
    ).join(
        Market, Market.event_ticker == Event.event_ticker
    ).filter(
        Market.is_mention == True,
        Market.status.in_(['active', 'open']),
        Market.expiration_time.isnot(None)
    )
    
    if search_term:
        subq = subq.filter(Event.title.ilike(f"%{search_term}%"))
    
    subq = subq.group_by(Event.event_ticker, Event.title, Event.category, Event.first_seen_at).subquery()
    
    results = db.query(subq).order_by(subq.c.soonest_expiration.asc()).all()
    
    data = []
    for r in results:
        time_remaining = "N/A"
        if r.soonest_expiration:
            exp_time = r.soonest_expiration if r.soonest_expiration.tzinfo else r.soonest_expiration.replace(tzinfo=timezone.utc)
            delta = exp_time - now_utc
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
            "Event Ticker": r.event_ticker,
            "Title": r.title,
            "Category": r.category or "N/A",
            "Event Opened": r.first_seen_at.strftime("%Y-%m-%d %H:%M UTC") if r.first_seen_at else "N/A",
            "Mention Markets": int(r.mention_count),
            "Volume": int(r.total_volume or 0),
            "24h Volume": int(r.volume_24h or 0),
            "Soonest Expires": r.soonest_expiration.strftime("%Y-%m-%d %H:%M UTC") if r.soonest_expiration else "N/A",
            "Time Remaining": time_remaining
        })
    
    return pd.DataFrame(data)


def get_mention_markets_for_event(
    db: Session,
    event_ticker: str
) -> pd.DataFrame:
    """Get mention markets for an event (for drill-down)."""
    markets = db.query(Market).filter(
        Market.event_ticker == event_ticker,
        Market.is_mention == True,
        Market.status.in_(['active', 'open'])
    ).order_by(Market.expiration_time.asc()).all()
    
    data = []
    for m in markets:
        trend_30m = get_price_trend(db, m.ticker, hours_ago=0.5)
        trend_24h = get_price_trend(db, m.ticker, hours_ago=24)
        
        data.append({
            "Yes Subtitle": m.yes_sub_title or "—",
            "Volume": int(m.volume or 0),
            "24h Volume": int(m.volume_24h or 0),
            "Open Interest": int(m.open_interest or 0),
            "Yes Bid": f"{m.yes_bid}¢" if m.yes_bid else "—",
            "Yes Ask": f"{m.yes_ask}¢" if m.yes_ask else "—",
            "Last Price": f"{m.last_price}¢" if m.last_price else "—",
            "30m Trend": trend_30m or "—",
            "24h Trend": trend_24h or "—",
            "Ticker": m.ticker
        })
    
    return pd.DataFrame(data)


def get_relative_volume_events(
    db: Session,
    period_hours: int = 24,
    baseline_days: int = 7,
    search_term: Optional[str] = None
) -> pd.DataFrame:
    """Get events with high relative volume (excluding sports). Optimized with aggregated snapshots."""
    # Get sports categories
    sports_cats = db.query(Category.name).filter(
        Category.is_sports == True
    ).all()
    sports_categories = [cat[0] for cat in sports_cats]
    
    current_cutoff = datetime.now(timezone.utc) - timedelta(hours=period_hours)
    baseline_cutoff = datetime.now(timezone.utc) - timedelta(days=baseline_days)
    
    # Get events with current volume
    query = db.query(
        Event.event_ticker,
        Event.title,
        Event.category,
        func.sum(Market.volume).label("current_volume")
    ).join(
        Market, Market.event_ticker == Event.event_ticker
    ).filter(
        Market.status.in_(['active', 'open'])
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
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
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
    """Get all unique categories (excluding sports)."""
    # Get sports categories
    sports_cats = db.query(Category.name).filter(
        Category.is_sports == True
    ).all()
    sports_categories = {cat[0] for cat in sports_cats}
    
    categories = db.query(Event.category).distinct().filter(
        Event.category.isnot(None)
    ).all()
    
    # Filter out sports categories
    non_sports_cats = [cat[0] for cat in categories if cat[0] and cat[0] not in sports_categories]
    
    return ["All"] + sorted(non_sports_cats)


def get_new_counts(db: Session, window_hours: int = 24) -> Dict[str, int]:
    """Get counts of new events and markets (excluding sports)."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    
    # Get sports categories
    sports_cats = db.query(Category.name).filter(
        Category.is_sports == True
    ).all()
    sports_categories = [cat[0] for cat in sports_cats]
    
    # Count new events
    event_query = db.query(func.count(Event.event_ticker)).filter(
        Event.first_seen_at >= cutoff
    )
    if sports_categories:
        event_query = event_query.filter(~Event.category.in_(sports_categories))
    
    new_events = event_query.scalar() or 0
    
    # Count new markets in non-sports events
    market_query = db.query(func.count(Market.ticker)).join(
        Event, Market.event_ticker == Event.event_ticker
    ).filter(
        Market.first_seen_at >= cutoff
    )
    if sports_categories:
        market_query = market_query.filter(~Event.category.in_(sports_categories))
    
    new_markets = market_query.scalar() or 0
    
    return {
        "new_events": new_events,
        "new_markets": new_markets
    }


def get_price_trend(db: Session, ticker: str, hours_ago: float) -> Optional[str]:
    """Calculate price trend by comparing current price to snapshot from N hours ago.
    
    Returns: Arrow indicator string like "↗ +5¢" or "↘ -3¢" or "→ Flat", or None if no data.
    """
    try:
        # Get current market
        current = db.query(Market).filter(Market.ticker == ticker).first()
        if not current or not current.last_price:
            return None
        
        # Get snapshot from ~N hours ago (allow ±15 min tolerance)
        target_time = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
        min_time = target_time - timedelta(minutes=15)
        max_time = target_time + timedelta(minutes=15)
        
        snapshot = db.query(MarketSnapshot).filter(
            MarketSnapshot.ticker == ticker,
            MarketSnapshot.snapshot_time >= min_time,
            MarketSnapshot.snapshot_time <= max_time
        ).order_by(
            func.abs(func.extract('epoch', MarketSnapshot.snapshot_time - target_time))
        ).first()
        
        if not snapshot or snapshot.last_price is None:
            return None
        
        # Calculate change
        change = current.last_price - snapshot.last_price
        
        if change > 2:
            return f"↗ +{change}¢"
        elif change < -2:
            return f"↘ {change}¢"
        else:
            return "→ Flat"
            
    except Exception:
        return None
