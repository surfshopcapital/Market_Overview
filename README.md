# Kalshi Markets Dashboard

Production-ready Streamlit dashboard for Kalshi prediction markets with PostgreSQL backend, Railway deployment, scheduled hourly data ingestion, and 4x daily email digests.

## Architecture

### Components

1. **Streamlit Dashboard** (Frontend)
   - 5 pages: New Markets, Trending, Mentions, Relative Volume, Email Settings
   - Read-only queries from PostgreSQL
   - Deployed on Streamlit Cloud or Railway

2. **PostgreSQL Database**
   - Stores events, markets, snapshots, email settings
   - Deployed on Railway

3. **Data Ingestion Worker**
   - Runs hourly via Railway Cron
   - Fetches data from Kalshi API
   - Identifies trending and mention markets
   - Creates volume snapshots

4. **Email Digest Worker**
   - Runs 4x daily (6am, 12pm, 6pm, 12am ET)
   - Generates and sends HTML email digests
   - Configurable via dashboard

## Features

### Page 1: New Markets
- View events/markets opened in last 12h/24h/48h/7d
- Display event title, category, open time, total volume
- Drill down to see all markets within event
- Search and filter by category

### Page 2: Trending
- Shows markets with high 24h volume
- Matches Kalshi's trending markets
- Drill down to event details

### Page 3: Mentions
- All mention markets sorted by expiration
- Highlights new mentions (within configurable window)
- Shows time remaining until expiration
- Color-coded for new markets

### Page 4: Relative Volume (No Sports)
- Identifies events with unusually high volume vs. 7/14/30 day baseline
- Excludes sports categories
- Shows relative multiple (current/baseline)
- Volume history charts
- Confidence indicators

### Page 5: Email Settings
- Configure recipients
- Set send times (default: 6am, 12pm, 6pm, 12am ET)
- Enable/disable sections
- Adjust thresholds
- Send test email
- View digest logs

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Kalshi API credentials
- SendGrid API key (for emails)
- Railway account (for deployment)
- Streamlit Cloud account (optional, for frontend)

### Environment Variables

Create a `.env` file:

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/kalshi_markets

# Kalshi API
KALSHI_API_BASE_URL=https://api.elections.kalshi.com/trade-api/v2
KALSHI_API_KEY=your_api_key_here
KALSHI_API_SECRET=your_api_secret_here
KALSHI_EMAIL=your_kalshi_email@example.com
KALSHI_PASSWORD=your_kalshi_password

# Email (SendGrid)
SENDGRID_API_KEY=your_sendgrid_api_key
EMAIL_FROM=noreply@yourdomain.com
EMAIL_FROM_NAME=Kalshi Markets Digest

# Application
APP_ENV=production
LOG_LEVEL=INFO
TIMEZONE=America/New_York
```

### Local Development

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Setup database:**
```bash
# Create database
createdb kalshi_markets

# Run schema
psql kalshi_markets < db/schema.sql
```

3. **Initialize database:**
```bash
python -c "from config import init_db; init_db()"
```

4. **Run ingestion worker (one-time):**
```bash
python workers/ingest.py
```

5. **Run Streamlit dashboard:**
```bash
streamlit run app/main.py
```

6. **Test email digest:**
```bash
python workers/emailer.py --force
```

## Deployment

### Railway Deployment (All-in-One)

Railway can host the database, workers, and optionally the Streamlit app.

#### Step 1: Setup Railway Project

1. Install Railway CLI:
```bash
npm install -g @railway/cli
```

2. Login and create project:
```bash
railway login
railway init
```

3. Create PostgreSQL database:
```bash
railway add postgresql
```

4. Get database URL:
```bash
railway variables
```

#### Step 2: Configure Environment Variables

In Railway dashboard, add all environment variables from `.env.example`.

#### Step 3: Initialize Database

```bash
# Connect to Railway database
railway run psql $DATABASE_URL < db/schema.sql
```

#### Step 4: Deploy Workers

The `railway.toml` file defines the cron schedules:

- **Ingestion**: Every hour
- **Email Digests**: 6am, 12pm, 6pm, 12am ET

```bash
railway up
```

#### Step 5: Monitor

```bash
# View logs
railway logs

# Check services
railway status
```

### Streamlit Cloud Deployment (Frontend Only)

If you want to separate the frontend:

#### Step 1: Streamlit Cloud Setup

1. Push code to GitHub
2. Go to https://share.streamlit.io
3. Connect GitHub repo
4. Set main file: `app/main.py`

#### Step 2: Configure Secrets

In Streamlit Cloud, go to Settings → Secrets and add:

```toml
[database]
DATABASE_URL = "postgresql://user:password@railway-host:5432/kalshi_markets"

[app]
LOG_LEVEL = "INFO"
TIMEZONE = "America/New_York"
```

**Note:** Streamlit app only needs `DATABASE_URL` (read-only access).

### Alternative: All-in Railway

You can also deploy Streamlit on Railway:

```bash
# Add Streamlit service to railway.toml
railway add
# Select "Web Service"
# Build command: pip install -r requirements.txt
# Start command: streamlit run app/main.py --server.port $PORT
```

## Kalshi API Usage

The system uses these Kalshi API endpoints:

- `GET /events` - Fetch events with nested markets
- `GET /markets` - Fetch markets with filters
- `GET /search/tags_by_categories` - Get category taxonomy
- `POST /login` - Authentication

### Rate Limiting

- Default: 10 requests/second
- Implemented with token bucket algorithm
- Automatic retry with exponential backoff

### Authentication

- Login with email/password
- Access token cached (24h validity)
- Auto-refresh before expiration

## Data Model

### Events
- Primary key: `event_ticker`
- Contains: title, category, series, timestamps
- Relationship: one-to-many markets

### Markets
- Primary key: `ticker`
- Contains: prices, volume, status, timestamps
- Flags: `is_trending`, `is_mention`
- Foreign key: `event_ticker`

### Market Snapshots
- Time-series data for volume analysis
- Created hourly by ingestion worker
- Retained for 60 days

### Email Settings
- Singleton table (id=1)
- Recipients, send times, thresholds
- Enabled sections configuration

## Monitoring

### Logs

Workers log to:
- `logs/ingestion.log`
- `logs/emailer.log`

### Database Logs

Email digest logs stored in `email_digest_logs` table:
```sql
SELECT * FROM email_digest_logs 
ORDER BY sent_at DESC 
LIMIT 10;
```

### Health Checks

Check recent ingestion:
```sql
SELECT MAX(first_seen_at) as last_ingestion 
FROM events;
```

## Troubleshooting

### No data in dashboard
- Check ingestion worker logs
- Verify Kalshi API credentials
- Run manual ingestion: `python workers/ingest.py`

### Emails not sending
- Verify SendGrid API key
- Check email worker logs
- Test manually: `python workers/emailer.py --force`
- Check `email_digest_logs` for errors

### Database connection issues
- Verify `DATABASE_URL`
- Check PostgreSQL is running
- Test connection: `psql $DATABASE_URL`

### Rate limiting errors
- API client implements exponential backoff
- Reduce ingestion frequency if needed
- Check Kalshi API limits

## Maintenance

### Update categories (sports exclusion)
```sql
-- Mark a category as sports
UPDATE categories 
SET is_sports = true 
WHERE name = 'nfl';
```

### Clean old snapshots
```sql
-- Keep last 60 days (automatic in worker)
DELETE FROM market_snapshots 
WHERE snapshot_time < NOW() - INTERVAL '60 days';
```

### Reset email settings
```sql
-- Reset to defaults
UPDATE email_settings 
SET recipients = ARRAY['surfshopcapital@gmail.com'],
    send_times = ARRAY['06:00', '12:00', '18:00', '00:00']
WHERE id = 1;
```

## Cost Estimates

### Railway
- PostgreSQL: $5-20/month (shared to dedicated)
- Cron workers: Free tier (5 services)
- Total: ~$5-20/month

### SendGrid
- Free tier: 100 emails/day
- 4 emails/day = well within limit

### Streamlit Cloud
- Free tier: 1 app
- Community (free) or paid ($10/month)

## Development

### Project Structure
```
.
├── app/                    # Streamlit pages
│   ├── main.py            # Main app + navigation
│   ├── pages/             # Individual pages
│   └── utils/             # Helper functions
├── config/                # Configuration
│   ├── settings.py        # Settings management
│   └── database.py        # DB connection
├── db/                    # Database
│   ├── schema.sql         # Schema definition
│   └── models.py          # SQLAlchemy models
├── kalshi/                # Kalshi API client
│   ├── client.py          # API client
│   └── schemas.py         # Response models
├── workers/               # Background workers
│   ├── ingest.py          # Data ingestion
│   └── emailer.py         # Email digest
├── requirements.txt       # Python dependencies
├── railway.toml           # Railway config
├── Dockerfile.worker      # Worker container
└── README.md              # This file
```

### Adding a New Page

1. Create `app/pages/your_page.py`
2. Add to navigation in `app/main.py`
3. Add database query to `app/utils/db_utils.py`

### Modifying Email Template

Edit `workers/emailer.py`, `_generate_html()` method.

## License

MIT

## Support

For issues or questions:
- Check troubleshooting section
- Review logs
- Open GitHub issue

---

**Built with:** Python, Streamlit, PostgreSQL, SQLAlchemy, SendGrid, Railway
