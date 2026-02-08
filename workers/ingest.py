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
            
            # Step 2: Fetch and filter events (exclude sports, get nested markets)
            logger.info("Fetching all events...")
            events = self.client.get_all_events(
                with_nested_markets=True
            )
            logger.info(f"Fetched {len(events)} total events from API")
            
            # Filter out sports events
            sports_cats = self._get_sports_categories()
            filtered_events = [e for e in events if e.category not in sports_cats]
            logger.info(f"Filtered to {len(filtered_events)} non-sports events")
            
            self._upsert_events_optimized(filtered_events)
            
            # Step 3: Identify trending and mention markets
            self._identify_trending_markets()
            self._identify_mention_markets()
            
            # Step 4: Create snapshots for active markets only
            self._create_snapshots()
            
            # Step 5: Clean up low-volume old markets
            self._cleanup_low_volume_markets()
            
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
    
    def _get_sports_categories(self) -> set:
        """Get set of sports category names."""
        sports_cats = self.db.query(Category.name).filter(
            Category.is_sports == True
        ).all()
        return {cat[0] for cat in sports_cats}
    
    def _upsert_events_optimized(self, events: List[EventResponse]):
        """Optimized upsert of events and their markets (bulk operations)."""
        logger.info(f"Upserting {len(events)} events with markets...")
        
        from sqlalchemy.dialects.postgresql import insert
        
        try:
            # Prepare bulk event data
            event_values = []
            market_values = []
            three_days_ago = datetime.utcnow() - timedelta(days=3)
            
            for event in events:
                event_values.append({
                    'event_ticker': event.event_ticker,
                    'series_ticker': event.series_ticker,
                    'title': event.title,
                    'sub_title': event.sub_title,
                    'category': event.category,
                    'mutually_exclusive': event.mutually_exclusive,
                    'strike_date': event.strike_date,
                    'strike_period': event.strike_period
                })
                
                # Process nested markets
                if event.markets:
                    for market in event.markets:
                        # Skip if:
                        # 1. Market is older than 3 days AND volume < 1000
                        # 2. Market is not active (status != 'active')
                        if market.status != 'active':
                            continue
                        
                        if market.created_time and market.created_time < three_days_ago:
                            if (market.volume or 0) < 1000:
                                continue
                        
                        market_values.append({
                            'ticker': market.ticker,
                            'event_ticker': market.event_ticker,
                            'market_type': market.market_type,
                            'title': market.title,
                            'subtitle': market.subtitle,
                            'yes_sub_title': market.yes_sub_title,
                            'no_sub_title': market.no_sub_title,
                            'created_time': market.created_time,
                            'updated_time': market.updated_time,
                            'open_time': market.open_time,
                            'close_time': market.close_time,
                            'expiration_time': market.expiration_time,
                            'status': market.status,
                            'volume': market.volume or 0,
                            'volume_24h': market.volume_24h or 0,
                            'open_interest': market.open_interest or 0,
                            'yes_bid': market.yes_bid,
                            'yes_ask': market.yes_ask,
                            'last_price': market.last_price,
                            'liquidity': market.liquidity,
                            'can_close_early': market.can_close_early,
                            'last_updated_at': datetime.utcnow()
                        })
            
            # Bulk upsert events
            if event_values:
                stmt = insert(Event).values(event_values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['event_ticker'],
                    set_={
                        'series_ticker': stmt.excluded.series_ticker,
                        'title': stmt.excluded.title,
                        'sub_title': stmt.excluded.sub_title,
                        'category': stmt.excluded.category,
                        'updated_at': datetime.utcnow()
                    }
                )
                self.db.execute(stmt)
            
            # Bulk upsert markets
            if market_values:
                logger.info(f"Upserting {len(market_values)} active markets (sports + low-volume filtered)")
                
                stmt = insert(Market).values(market_values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['ticker'],
                    set_={
                        'title': stmt.excluded.title,
                        'subtitle': stmt.excluded.subtitle,
                        'yes_sub_title': stmt.excluded.yes_sub_title,
                        'no_sub_title': stmt.excluded.no_sub_title,
                        'updated_time': stmt.excluded.updated_time,
                        'close_time': stmt.excluded.close_time,
                        'expiration_time': stmt.excluded.expiration_time,
                        'status': stmt.excluded.status,
                        'volume': stmt.excluded.volume,
                        'volume_24h': stmt.excluded.volume_24h,
                        'open_interest': stmt.excluded.open_interest,
                        'yes_bid': stmt.excluded.yes_bid,
                        'yes_ask': stmt.excluded.yes_ask,
                        'last_price': stmt.excluded.last_price,
                        'liquidity': stmt.excluded.liquidity,
                        'can_close_early': stmt.excluded.can_close_early,
                        'last_updated_at': datetime.utcnow()
                    }
                )
                self.db.execute(stmt)
            
            self.db.commit()
            logger.info("Events and markets upserted successfully")
            
        except Exception as e:
            logger.error(f"Error in optimized upsert: {e}")
            self.db.rollback()
            raise
    
    def _cleanup_low_volume_markets(self):
        """Remove low-volume markets older than 3 days."""
        logger.info("Cleaning up low-volume markets...")
        
        try:
            three_days_ago = datetime.utcnow() - timedelta(days=3)
            
            deleted = self.db.query(Market).filter(
                Market.created_time < three_days_ago,
                Market.volume < 1000,
                Market.status == "active"
            ).delete()
            
            self.db.commit()
            logger.info(f"Deleted {deleted} low-volume markets older than 3 days")
            
        except Exception as e:
            logger.error(f"Error cleaning up markets: {e}")
            self.db.rollback()
    
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
        """Create market snapshots for time-series analysis (active markets only)."""
        logger.info("Creating market snapshots...")
        
        try:
            snapshot_time = datetime.utcnow()
            
            # Get only active markets with volume > 0
            markets = self.db.query(Market).filter(
                Market.status == "active",
                Market.volume > 0
            ).all()
            
            # Bulk insert snapshots
            from sqlalchemy.dialects.postgresql import insert
            
            snapshot_values = [
                {
                    'ticker': market.ticker,
                    'snapshot_time': snapshot_time,
                    'volume': market.volume,
                    'volume_24h': market.volume_24h,
                    'open_interest': market.open_interest,
                    'yes_bid': market.yes_bid,
                    'yes_ask': market.yes_ask,
                    'last_price': market.last_price,
                    'liquidity': market.liquidity
                }
                for market in markets
            ]
            
            if snapshot_values:
                stmt = insert(MarketSnapshot).values(snapshot_values)
                self.db.execute(stmt)
            
            self.db.commit()
            logger.info(f"Created {len(snapshot_values)} snapshots")
            
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
