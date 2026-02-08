# Database Management

## Does the Worker Reset the Database?

**No**, the worker does NOT reset/clear the database each time. It performs **upserts** (insert or update):

- **Events & Markets**: If they already exist (by ticker), they get updated. If new, they get inserted.
- **Snapshots**: New snapshots are added each run (hourly time-series data).
- **Flags**: `is_trending` and `is_mention` flags are reset to false, then re-evaluated each run.

## How to Reset the Postgres Database

If you want to completely wipe and start fresh:

### Option 1: Drop and Recreate Tables (Via Bootstrap)

```bash
# This will drop all tables and recreate them
C:\Users\betti\anaconda3\python.exe -c "from config import engine; from db.models import Base; Base.metadata.drop_all(engine); Base.metadata.create_all(engine)"

# Then run bootstrap to add default settings
C:\Users\betti\anaconda3\python.exe bootstrap.py
```

### Option 2: Delete All Data But Keep Schema

```sql
-- Connect to your Railway Postgres and run:
TRUNCATE TABLE market_snapshots CASCADE;
TRUNCATE TABLE markets CASCADE;
TRUNCATE TABLE events CASCADE;
TRUNCATE TABLE email_digest_logs CASCADE;
TRUNCATE TABLE categories CASCADE;
-- Note: Don't truncate email_settings if you want to keep your config
```

### Option 3: Railway Dashboard

1. Go to Railway dashboard
2. Click your Postgres service
3. Go to "Data" tab
4. Manually delete tables or data

## Current Issue: Sports Markets Showing

The sports markets you're seeing are from **before the ingestion worker was updated** to filter them out. They're still in the database.

### To Fix:

**Option A**: Delete sports events from database:
```sql
-- Connect to Railway Postgres
DELETE FROM events WHERE category IN (
    SELECT name FROM categories WHERE is_sports = true
);
-- This will cascade delete all markets in those events
```

**Option B**: Wait for them to expire naturally (they won't get updated anymore)

**Option C**: Full reset (see options above)

## What the Worker Does Now

1. **Fetches** only `status="open"` events from Kalshi API
2. **Filters out** all sports categories before storing
3. **Only stores**:
   - Active/open markets
   - Markets <3 days old (all volumes) OR markets >3 days old with $1000+ volume
4. **Cleans up** low-volume old markets each run
5. **Updates** trending/mention flags based on category

## Summary

- **Sports still in DB?** Yes, from old ingestion runs. Delete them manually or do a fresh start.
- **Will new sports get added?** No, the worker now filters them out.
- **Best approach**: Run the SQL delete command above to remove sports, or do a full reset if you want completely clean data.
