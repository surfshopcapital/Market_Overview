"""Data ingestion worker to fetch and store Kalshi market data."""
import logging
import sys
from datetime import datetime, timedelta
from typing import List, Set
import pytz
from sqlalchemy import and_
from sqlalchemy.dialects.postgresql import insert

from config import settings, SessionLocal
from db.models import Event, Market, MarketSnapshot, Category
from kalshi import KalshiClient, MarketResponse, EventResponse

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/ingestion.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Sports categories to exclude
SPORTS_CATEGORIES = {
    "sports", "nfl", "nba", "mlb", "nhl", "soccer", "football", 
    "basketball", "baseball", "hockey", "tennis", "golf", "mma",
    "ufc", "boxing", "olympics", "ncaa", "college-sports"
}

# Keywords to identify mention markets
MENTION_KEYWORDS = [
    "mention", "mentioned", "mentions", "say", "says", "tweet", 
    "tweets", "post", "posts", "announce", "announces"
]


class DataIngester:
    """Data ingestion worker."""
    
    def __init__(self):
        self.client = KalshiClient()
        self.db = SessionLocal()
        self.tz = pytz.timezone(settings.TIMEZONE)
    
    def __del__(self):
        """Clean up database connection."""
        if hasattr(self, 'db'):
            self.db.close()
    
    def run(self):
        """Run the ingestion process."""
        logger.info("=" * 80)
        logger.info("Starting data ingestion run")
        logger.info("=" * 80)
        
        try:
            # Step 1: Update categories and identify sports
            self._update_categories()
            
            # Step 2: Fetch and upsert events
            logger.info("Fetching events...")
            events = self.client.get_all_events(
                status="open",
                with_nested_markets=True
            )
            logger.info(f"Fetched {len(events)} events")
            self._upsert_events(events)
            
            # Step 3: Fetch and upsert markets
            logger.info("Fetching markets...")
            markets = self.client.get_all_markets(status="open")
            logger.info(f"Fetched {len(markets)} open markets")
            self._upsert_markets(markets)
            
            # Step 4: Identify trending markets
            self._identify_trending_markets()
            
            # Step 5: Identify mention markets
            self._identify_mention_markets()
            
            # Step 6: Create snapshots for volume tracking
            self._create_snapshots()
            
            logger.info("Data ingestion completed successfully")
            
        except Exception as e:
            logger.error(f"Error during data ingestion: {e}", exc_info=True)
            raise
    
    def _update_categories(self):
        """Update categories and mark sports categories."""
        logger.info("Updating categories...")
        
        try:
            # Get tags by categories from API
            tags_response = self.client.get_tags_by_categories()
            
            for category, tags in tags_response.tags_by_categories.items():
                is_sports = category.lower() in SPORTS_CATEGORIES
                
                # Upsert category
                stmt = insert(Category).values(
                    name=category,
                    is_sports=is_sports
                ).on_conflict_do_update(
                    index_elements=['name'],
                    set_={'is_sports': is_sports}
                )
                self.db.execute(stmt)
            
            self.db.commit()
            logger.info(f"Updated {len(tags_response.tags_by_categories)} categories")
            
        except Exception as e:
            logger.error(f"Error updating categories: {e}")
            self.db.rollback()
    
    def _upsert_events(self, events: List[EventResponse]):
        """Upsert events into database."""
        logger.info(f"Upserting {len(events)} events...")
        
        for event in events:
            try:
                # Check if event exists
                existing = self.db.query(Event).filter(
                    Event.event_ticker == event.event_ticker
                ).first()
                
                if existing:
                    # Update existing event
                    existing.series_ticker = event.series_ticker
                    existing.title = event.title
                    existing.sub_title = event.sub_title
                    existing.category = event.category
                    existing.mutually_exclusive = event.mutually_exclusive
                    existing.strike_date = event.strike_date
                    existing.strike_period = event.strike_period
                    existing.updated_at = datetime.utcnow()
                else:
                    # Insert new event
                    new_event = Event(
                        event_ticker=event.event_ticker,
                        series_ticker=event.series_ticker,
                        title=event.title,
                        sub_title=event.sub_title,
                        category=event.category,
                        mutually_exclusive=event.mutually_exclusive,
                        strike_date=event.strike_date,
                        strike_period=event.strike_period,
                        first_seen_at=datetime.utcnow()
                    )
                    self.db.add(new_event)
                
                # Process nested markets if present
                if event.markets:
                    self._upsert_markets(event.markets)
                
            except Exception as e:
                logger.error(f"Error upserting event {event.event_ticker}: {e}")
                self.db.rollback()
                continue
        
        self.db.commit()
        logger.info("Events upserted successfully")
    
    def _upsert_markets(self, markets: List[MarketResponse]):
        """Upsert markets into database."""
        logger.info(f"Upserting {len(markets)} markets...")
        
        for market in markets:
            try:
                # Check if market exists
                existing = self.db.query(Market).filter(
                    Market.ticker == market.ticker
                ).first()
                
                if existing:
                    # Update existing market
                    existing.title = market.title
                    existing.subtitle = market.subtitle
                    existing.yes_sub_title = market.yes_sub_title
                    existing.no_sub_title = market.no_sub_title
                    existing.updated_time = market.updated_time
                    existing.close_time = market.close_time
                    existing.expiration_time = market.expiration_time
                    existing.status = market.status
                    existing.volume = market.volume or 0
                    existing.volume_24h = market.volume_24h or 0
                    existing.open_interest = market.open_interest or 0
                    existing.yes_bid = market.yes_bid
                    existing.yes_ask = market.yes_ask
                    existing.no_bid = market.no_bid
                    existing.no_ask = market.no_ask
                    existing.last_price = market.last_price
                    existing.liquidity = market.liquidity
                    existing.can_close_early = market.can_close_early
                    existing.result = market.result
                    existing.settlement_value = market.settlement_value
                    existing.settlement_ts = market.settlement_ts
                    existing.last_updated_at = datetime.utcnow()
                else:
                    # Insert new market
                    new_market = Market(
                        ticker=market.ticker,
                        event_ticker=market.event_ticker,
                        market_type=market.market_type,
                        title=market.title,
                        subtitle=market.subtitle,
                        yes_sub_title=market.yes_sub_title,
                        no_sub_title=market.no_sub_title,
                        created_time=market.created_time,
                        updated_time=market.updated_time,
                        open_time=market.open_time,
                        close_time=market.close_time,
                        expiration_time=market.expiration_time,
                        settlement_timer_seconds=market.settlement_timer_seconds,
                        status=market.status,
                        volume=market.volume or 0,
                        volume_24h=market.volume_24h or 0,
                        open_interest=market.open_interest or 0,
                        yes_bid=market.yes_bid,
                        yes_ask=market.yes_ask,
                        no_bid=market.no_bid,
                        no_ask=market.no_ask,
                        last_price=market.last_price,
                        liquidity=market.liquidity,
                        can_close_early=market.can_close_early,
                        result=market.result,
                        settlement_value=market.settlement_value,
                        settlement_ts=market.settlement_ts,
                        first_seen_at=datetime.utcnow()
                    )
                    self.db.add(new_market)
                
            except Exception as e:
                logger.error(f"Error upserting market {market.ticker}: {e}")
                self.db.rollback()
                continue
        
        self.db.commit()
        logger.info("Markets upserted successfully")
    
    def _identify_trending_markets(self):
        """Identify trending markets based on volume_24h."""
        logger.info("Identifying trending markets...")
        
        try:
            # Reset all trending flags
            self.db.query(Market).update({"is_trending": False})
            
            # Get top markets by 24h volume
            trending_markets = self.db.query(Market).filter(
                Market.status == "open",
                Market.volume_24h > 0
            ).order_by(
                Market.volume_24h.desc()
            ).limit(50).all()
            
            # Mark as trending
            for market in trending_markets:
                market.is_trending = True
            
            self.db.commit()
            logger.info(f"Identified {len(trending_markets)} trending markets")
            
        except Exception as e:
            logger.error(f"Error identifying trending markets: {e}")
            self.db.rollback()
    
    def _identify_mention_markets(self):
        """Identify mention markets based on title keywords."""
        logger.info("Identifying mention markets...")
        
        try:
            # Reset all mention flags
            self.db.query(Market).update({"is_mention": False})
            
            # Find markets with mention keywords in title
            mention_markets = []
            all_markets = self.db.query(Market).filter(
                Market.status == "open"
            ).all()
            
            for market in all_markets:
                title_lower = market.title.lower()
                if any(keyword in title_lower for keyword in MENTION_KEYWORDS):
                    market.is_mention = True
                    mention_markets.append(market)
            
            self.db.commit()
            logger.info(f"Identified {len(mention_markets)} mention markets")
            
        except Exception as e:
            logger.error(f"Error identifying mention markets: {e}")
            self.db.rollback()
    
    def _create_snapshots(self):
        """Create market snapshots for time-series analysis."""
        logger.info("Creating market snapshots...")
        
        try:
            snapshot_time = datetime.utcnow()
            
            # Get all open markets
            markets = self.db.query(Market).filter(
                Market.status == "open"
            ).all()
            
            for market in markets:
                snapshot = MarketSnapshot(
                    ticker=market.ticker,
                    snapshot_time=snapshot_time,
                    volume=market.volume,
                    volume_24h=market.volume_24h,
                    open_interest=market.open_interest,
                    yes_bid=market.yes_bid,
                    yes_ask=market.yes_ask,
                    no_bid=market.no_bid,
                    no_ask=market.no_ask,
                    last_price=market.last_price,
                    liquidity=market.liquidity
                )
                self.db.add(snapshot)
            
            self.db.commit()
            logger.info(f"Created {len(markets)} snapshots")
            
            # Clean up old snapshots (keep last 60 days)
            cutoff_date = datetime.utcnow() - timedelta(days=60)
            deleted = self.db.query(MarketSnapshot).filter(
                MarketSnapshot.snapshot_time < cutoff_date
            ).delete()
            self.db.commit()
            logger.info(f"Deleted {deleted} old snapshots")
            
        except Exception as e:
            logger.error(f"Error creating snapshots: {e}")
            self.db.rollback()


def main():
    """Main entry point."""
    try:
        ingester = DataIngester()
        ingester.run()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in ingestion worker: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
