"""Bootstrap script to initialize database and create default settings."""
import sys
import logging
from config import init_db, SessionLocal
from db.models import EmailSettings, Category

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def bootstrap():
    """Initialize database and create default data."""
    logger.info("Starting database bootstrap...")
    
    try:
        # Initialize database tables
        logger.info("Creating database tables...")
        init_db()
        logger.info("Database tables created")
        
        # Create session
        db = SessionLocal()
        
        try:
            # Create default email settings if not exists
            existing_settings = db.query(EmailSettings).first()
            if not existing_settings:
                logger.info("Creating default email settings...")
                default_settings = EmailSettings(
                    id=1,
                    recipients=["surfshopcapital@gmail.com"],
                    send_times=["06:00", "12:00", "18:00", "00:00"],
                    timezone="America/New_York",
                    enabled_sections={
                        "new_markets": True,
                        "trending": True,
                        "mentions": True,
                        "relative_volume": True
                    },
                    new_markets_window_hours=24,
                    mentions_new_window_hours=24,
                    relative_volume_period_hours=24,
                    relative_volume_baseline_days=7,
                    relative_volume_top_n=10
                )
                db.add(default_settings)
                db.commit()
                logger.info("Default email settings created")
            else:
                logger.info("Email settings already exist")
            
            # Create common sports categories
            logger.info("Creating sports categories...")
            sports_categories = [
                "sports", "nfl", "nba", "mlb", "nhl", "soccer", 
                "football", "basketball", "baseball", "hockey", 
                "tennis", "golf", "mma", "ufc", "boxing", "olympics",
                "ncaa", "college-sports"
            ]
            
            for cat_name in sports_categories:
                existing_cat = db.query(Category).filter(
                    Category.name == cat_name
                ).first()
                
                if not existing_cat:
                    category = Category(name=cat_name, is_sports=True)
                    db.add(category)
            
            db.commit()
            logger.info(f"Created {len(sports_categories)} sports categories")
            
            logger.info("Bootstrap completed successfully!")
            
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"Error during bootstrap: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    bootstrap()
