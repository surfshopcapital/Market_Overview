"""Migration script to update schema to optimized version."""
import sys
import logging
from config import SessionLocal, engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """Run schema migration."""
    logger.info("Starting schema migration...")
    
    try:
        with engine.connect() as conn:
            # Drop columns we don't need (if they exist)
            logger.info("Removing unnecessary columns from markets table...")
            
            columns_to_drop = [
                'no_bid', 'no_ask', 'updated_time', 'settlement_timer_seconds',
                'result', 'settlement_value', 'settlement_ts'
            ]
            
            for col in columns_to_drop:
                try:
                    conn.execute(f"ALTER TABLE markets DROP COLUMN IF EXISTS {col}")
                    logger.info(f"Dropped column: {col}")
                except Exception as e:
                    logger.warning(f"Could not drop {col}: {e}")
            
            # Drop columns from market_snapshots
            logger.info("Removing unnecessary columns from market_snapshots table...")
            snapshot_cols_to_drop = ['no_bid', 'no_ask']
            
            for col in snapshot_cols_to_drop:
                try:
                    conn.execute(f"ALTER TABLE market_snapshots DROP COLUMN IF EXISTS {col}")
                    logger.info(f"Dropped snapshot column: {col}")
                except Exception as e:
                    logger.warning(f"Could not drop {col}: {e}")
            
            conn.commit()
            logger.info("Schema migration completed successfully!")
            
    except Exception as e:
        logger.error(f"Error during migration: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    migrate()
