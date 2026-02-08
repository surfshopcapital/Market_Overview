# Kalshi Markets Dashboard - Project Summary

## Overview

A production-ready Streamlit dashboard for monitoring Kalshi prediction markets with automated data ingestion, email digests, and comprehensive market analytics.

## Key Features

### Dashboard Pages
1. **New Markets** - Recently opened events/markets with volume tracking
2. **Trending** - High-volume markets matching Kalshi's trending
3. **Mentions** - Mention markets sorted by expiration with "new" indicators
4. **Relative Volume** - Events with unusually high volume vs. baseline (sports excluded)
5. **Email Settings** - Configure digest preferences and test delivery

### Automation
- **Hourly Data Ingestion** - Fetches latest markets, events, and volume data
- **4x Daily Email Digests** - Scheduled at 6am, noon, 6pm, midnight Eastern Time
- **Smart Categorization** - Auto-identifies trending and mention markets
- **Time-Series Tracking** - Hourly snapshots for volume analysis

### Technical Stack
- **Frontend**: Streamlit 1.29+
- **Database**: PostgreSQL 15+
- **API Client**: Custom Kalshi client with auth, pagination, rate limiting
- **Email**: Resend for HTML digests (3,000/month free)
- **Deployment**: Railway (database + workers) + Streamlit Cloud (optional)
- **Language**: Python 3.11+

## Project Structure

```
.
├── app/                        # Streamlit dashboard
│   ├── main.py                # Main app + navigation
│   ├── pages/                 # Individual pages
│   │   ├── new_markets.py
│   │   ├── trending.py
│   │   ├── mentions.py
│   │   ├── relative_volume.py
│   │   └── email_settings.py
│   └── utils/
│       └── db_utils.py        # Database query helpers
├── config/                     # Configuration
│   ├── settings.py            # Environment settings
│   └── database.py            # DB connection management
├── db/                         # Database
│   ├── schema.sql             # PostgreSQL schema
│   └── models.py              # SQLAlchemy models
├── kalshi/                     # Kalshi API client
│   ├── client.py              # HTTP client with auth
│   └── schemas.py             # Response models
├── workers/                    # Background workers
│   ├── ingest.py              # Data ingestion (hourly)
│   └── emailer.py             # Email digest (4x daily)
├── logs/                       # Worker logs
├── .github/workflows/          # CI/CD
│   └── deploy.yml
├── .streamlit/                 # Streamlit config
│   └── config.toml
├── bootstrap.py                # Database initialization
├── quickstart.py              # Local dev setup
├── test_system.py             # System tests
├── requirements.txt           # Python dependencies
├── railway.toml               # Railway deployment config
├── Dockerfile.worker          # Worker container
├── .env.example               # Environment template
├── .gitignore
├── README.md                  # Main documentation
├── DEPLOYMENT.md              # Deployment guide
├── CONTRIBUTING.md            # Contribution guidelines
├── CHANGELOG.md               # Version history
└── LICENSE                    # MIT License
```

## API Integration

### Kalshi API Endpoints Used
- `GET /events` - Events with nested markets
- `GET /markets` - Markets with filters (status, timestamps)
- `GET /search/tags_by_categories` - Category taxonomy
- `POST /login` - Authentication

### Features
- JWT authentication with auto-refresh
- Rate limiting (10 req/s with token bucket)
- Exponential backoff retry logic
- Cursor-based pagination
- Structured response validation (Pydantic)

## Database Schema

### Core Tables
- **events** - Event metadata (ticker, title, category, timestamps)
- **markets** - Market data (ticker, prices, volume, status, flags)
- **market_snapshots** - Hourly snapshots for time-series analysis
- **email_settings** - Digest configuration (singleton)
- **email_digest_logs** - Delivery history
- **categories** - Category metadata (sports exclusion)

### Key Indexes
- Event/market tickers (primary keys)
- Timestamps (created, updated, first_seen, expiration)
- Flags (is_trending, is_mention)
- Volume fields

## Data Flow

1. **Ingestion Worker (Hourly)**
   - Fetches open events/markets from Kalshi API
   - Upserts events and markets
   - Identifies trending markets (top 50 by volume_24h)
   - Identifies mention markets (keyword matching)
   - Creates snapshots for all open markets
   - Cleans up old snapshots (>60 days)

2. **Email Worker (4x Daily)**
   - Checks email settings for schedule
   - Queries database for digest sections:
     - New Markets: Top 10 by volume (within window)
     - Trending: All trending markets
     - Mentions: All mentions, sorted by expiration
     - Relative Volume: Top N events (configurable)
   - Generates HTML email
   - Sends via Resend
   - Logs delivery status

3. **Streamlit Dashboard**
   - Connects to PostgreSQL (read-only recommended)
   - Caches queries with short TTL
   - Displays data with interactive filters
   - Provides drill-down into events/markets
   - Allows email settings configuration

## Deployment Options

### Option 1: Railway (All-in-One)
- Database, workers, and Streamlit on Railway
- Single platform management
- Unified billing and monitoring

### Option 2: Railway + Streamlit Cloud (Recommended)
- Railway: PostgreSQL + workers
- Streamlit Cloud: Frontend only
- Simpler Streamlit deployment
- Free frontend tier available

## Configuration

### Required Environment Variables
```bash
DATABASE_URL                 # PostgreSQL connection
KALSHI_API_BASE_URL         # Optional - Kalshi public API (no auth)
RESEND_API_KEY              # Email delivery
EMAIL_FROM
LOG_LEVEL                   # INFO/DEBUG
TIMEZONE                    # America/New_York
```

### Email Settings (Configurable via Dashboard)
- Recipients (default: surfshopcapital@gmail.com)
- Send times (default: 06:00, 12:00, 18:00, 00:00 ET)
- Enabled sections (New Markets, Trending, Mentions, Relative Volume)
- Time windows (12h/24h/48h/7d)
- Baseline periods (7d/14d/30d)
- Top N limits (5-50)

## Performance

### Scalability
- **Database**: Indexed queries, connection pooling
- **API Client**: Rate limiting, pagination, caching
- **Workers**: Independent cron jobs, fail-safe
- **Frontend**: Query caching, lazy loading

### Resource Usage
- **Ingestion**: ~2-5 min per run, ~100 API calls
- **Email**: ~30 sec per digest
- **Database**: ~100-500 MB (depends on snapshot retention)
- **Railway Cost**: ~$5-10/month

## Testing

### Manual Tests
```bash
# System tests
python test_system.py

# Data ingestion
python workers/ingest.py

# Email digest
python workers/emailer.py --force

# Streamlit app
streamlit run app/main.py
```

### Automated Tests
- GitHub Actions workflow (`.github/workflows/deploy.yml`)
- Deploys to Railway on push to main

## Monitoring

### Health Checks
1. Check last ingestion: `SELECT MAX(first_seen_at) FROM events`
2. Check email logs: `SELECT * FROM email_digest_logs ORDER BY sent_at DESC`
3. Check worker logs: `railway logs --service ingestion-worker`

### Alerts
- Railway service failures (via dashboard notifications)
- Email delivery failures (logged in email_digest_logs)
- Database connection errors (worker logs)

## Security

### Best Practices
- Environment variables for secrets (never committed)
- Read-only database user for Streamlit
- HTTPS enforced (Railway/Streamlit Cloud)
- Regular credential rotation recommended
- Railway MFA enabled

### Data Privacy
- No PII stored
- Public market data only
- Email recipients configurable
- Logs contain no sensitive data

## Future Enhancements

### Planned Features
- WebSocket support for real-time updates
- User authentication and multi-user support
- Custom alerts and push notifications
- Advanced analytics (price charts, correlations)
- Portfolio tracking integration
- Mobile app (React Native)

### Potential Improvements
- GraphQL API for dashboard
- Redis caching layer
- Elasticsearch for advanced search
- Machine learning for volume predictions
- Slack/Discord integration
- Custom webhooks

## Support

### Resources
- **Documentation**: README.md, DEPLOYMENT.md
- **API Docs**: https://docs.kalshi.com
- **Railway Docs**: https://docs.railway.app
- **Streamlit Docs**: https://docs.streamlit.io

### Community
- GitHub Issues for bug reports
- Discussions for feature requests
- Railway Discord for deployment help
- Streamlit Forum for frontend questions

## License

MIT License - See LICENSE file for details

## Credits

Built for Surf Shop Capital by a senior full-stack + data engineer using:
- Streamlit for rapid frontend development
- PostgreSQL for reliable data storage
- Railway for seamless deployment
- Kalshi API for market data
- Resend for email delivery

---

**Version**: 1.0.0  
**Last Updated**: 2026-02-08  
**Status**: Production-ready
