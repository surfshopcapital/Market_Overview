# Quick Reference Guide

## Common Commands

### Local Development

```bash
# Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials

# Initialize
python bootstrap.py

# Run ingestion (one-time)
python workers/ingest.py

# Run Streamlit
streamlit run app/main.py

# Test email (local)
python workers/emailer.py --force

# Run system tests
python test_system.py

# Quick start (all-in-one)
python quickstart.py
```

### Railway Commands

```bash
# Setup
npm install -g @railway/cli
railway login
railway init

# Deploy
railway up

# View logs
railway logs
railway logs --service ingestion-worker
railway logs --follow

# Environment
railway variables
railway variables set KEY=value

# Database
railway run psql $DATABASE_URL
railway run psql $DATABASE_URL < db/schema.sql

# Manual triggers
railway run python workers/ingest.py
railway run python workers/emailer.py --force
```

### Database Queries

```sql
-- Check last ingestion
SELECT MAX(first_seen_at) FROM events;

-- Count markets by status
SELECT status, COUNT(*) FROM markets GROUP BY status;

-- View email logs
SELECT * FROM email_digest_logs ORDER BY sent_at DESC LIMIT 10;

-- Check trending markets
SELECT title, volume_24h FROM markets 
WHERE is_trending = true 
ORDER BY volume_24h DESC;

-- View mention markets
SELECT title, expiration_time FROM markets 
WHERE is_mention = true 
ORDER BY expiration_time ASC;

-- Check sports categories
SELECT name FROM categories WHERE is_sports = true;

-- Reset email settings
UPDATE email_settings 
SET recipients = ARRAY['surfshopcapital@gmail.com']
WHERE id = 1;
```

## Environment Variables

### Required
```bash
DATABASE_URL=postgresql://user:pass@host:5432/kalshi_markets
KALSHI_API_BASE_URL=https://api.elections.kalshi.com/trade-api/v2
SENDGRID_API_KEY=your_sendgrid_key
EMAIL_FROM=noreply@yourdomain.com
```

### Optional
```bash
KALSHI_API_BASE_URL=https://api.elections.kalshi.com/trade-api/v2
EMAIL_FROM_NAME=Kalshi Markets Digest
APP_ENV=production
LOG_LEVEL=INFO
TIMEZONE=America/New_York
```

## File Locations

### Configuration
- `.env` - Local environment variables
- `.env.example` - Template for environment variables
- `config/settings.py` - Settings management
- `config/database.py` - Database connection

### Database
- `db/schema.sql` - PostgreSQL schema
- `db/models.py` - SQLAlchemy models

### Workers
- `workers/ingest.py` - Data ingestion worker
- `workers/emailer.py` - Email digest worker
- `logs/ingestion.log` - Ingestion logs
- `logs/emailer.log` - Email logs

### Dashboard
- `app/main.py` - Main Streamlit app
- `app/pages/*.py` - Individual pages
- `app/utils/db_utils.py` - Database helpers

### Deployment
- `railway.toml` - Railway configuration
- `Dockerfile.worker` - Worker container
- `.github/workflows/deploy.yml` - CI/CD

### Documentation
- `README.md` - Main documentation
- `DEPLOYMENT.md` - Deployment guide
- `PROJECT_SUMMARY.md` - Project overview
- `CONTRIBUTING.md` - Contribution guidelines
- `CHANGELOG.md` - Version history

## Email Digest Schedule

All times in America/New_York (Eastern Time):

| Time | UTC Equivalent | Railway Cron |
|------|----------------|--------------|
| 6:00 AM | 11:00 UTC (EST) / 10:00 UTC (EDT) | `0 11 * * *` |
| 12:00 PM | 17:00 UTC (EST) / 16:00 UTC (EDT) | `0 17 * * *` |
| 6:00 PM | 23:00 UTC (EST) / 22:00 UTC (EDT) | `0 23 * * *` |
| 12:00 AM | 05:00 UTC (EST) / 04:00 UTC (EDT) | `0 5 * * *` |

**Note**: Times shown assume EST (UTC-5). Adjust for EDT (UTC-4) during daylight saving.

## Cron Schedule Format

```
* * * * *
│ │ │ │ │
│ │ │ │ └─ Day of week (0-7, Sun-Sat)
│ │ │ └─── Month (1-12)
│ │ └───── Day of month (1-31)
│ └─────── Hour (0-23)
└───────── Minute (0-59)
```

Examples:
- `0 * * * *` - Every hour at minute 0
- `*/30 * * * *` - Every 30 minutes
- `0 0 * * *` - Daily at midnight UTC
- `0 12 * * 1` - Every Monday at noon UTC

## API Rate Limits

Kalshi API:
- **Default**: 10 requests/second
- **Implementation**: Token bucket with exponential backoff
- **Retry**: 3 attempts with backoff factor 1

## Database Maintenance

```sql
-- Vacuum database
VACUUM ANALYZE;

-- Check table sizes
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Clean old snapshots (>60 days)
DELETE FROM market_snapshots 
WHERE snapshot_time < NOW() - INTERVAL '60 days';

-- Reindex tables
REINDEX TABLE events;
REINDEX TABLE markets;
REINDEX TABLE market_snapshots;
```

## Troubleshooting

### Workers not running
```bash
# Check status
railway status

# View logs
railway logs --service ingestion-worker

# Manual trigger
railway run python workers/ingest.py
```

### No data in dashboard
```sql
-- Check last ingestion
SELECT MAX(first_seen_at) FROM events;

-- If null, run manual ingestion
railway run python workers/ingest.py
```

### Emails not sending
```bash
# Check logs
railway logs --service email-worker-6am

# Test manually
railway run python workers/emailer.py --force

# Check SendGrid dashboard
# https://app.sendgrid.com
```

### Database connection failed
```bash
# Test connection
railway run psql $DATABASE_URL -c "SELECT 1;"

# Check DATABASE_URL
railway variables | grep DATABASE_URL
```

## Monitoring Checklist

Daily:
- [ ] Check dashboard loads
- [ ] Verify recent data (last ingestion time)
- [ ] Check email digest logs

Weekly:
- [ ] Review worker logs for errors
- [ ] Check database size
- [ ] Verify email delivery rate

Monthly:
- [ ] Review Railway usage and costs
- [ ] Update dependencies if needed
- [ ] Rotate API keys (recommended)
- [ ] Backup database

## URLs

### Production
- **Streamlit Dashboard**: Your deployed URL
- **Railway Project**: https://railway.app/project/[your-project-id]

### Development
- **Local Streamlit**: http://localhost:8501
- **Local Database**: postgres://localhost:5432/kalshi_markets

### External Services
- **Kalshi API**: https://api.elections.kalshi.com/trade-api/v2
- **Kalshi Docs**: https://docs.kalshi.com
- **SendGrid**: https://app.sendgrid.com
- **Railway**: https://railway.app

## Support

| Issue | Resource |
|-------|----------|
| Deployment | DEPLOYMENT.md |
| Configuration | README.md |
| Bug Reports | GitHub Issues |
| Feature Requests | GitHub Discussions |
| Railway Help | Discord: https://discord.gg/railway |
| Streamlit Help | Forum: https://discuss.streamlit.io |

## Quick Fixes

### Reset email settings
```sql
UPDATE email_settings SET
  recipients = ARRAY['surfshopcapital@gmail.com'],
  send_times = ARRAY['06:00', '12:00', '18:00', '00:00'],
  timezone = 'America/New_York'
WHERE id = 1;
```

### Force refresh data
```bash
railway run python workers/ingest.py
```

### Send test email
```bash
railway run python workers/emailer.py --force
```

### Clear Streamlit cache
In Streamlit app: Press 'C' or click menu → "Clear cache"

### Check system health
```bash
python test_system.py
```

## Keyboard Shortcuts (Streamlit)

- `R` - Rerun app
- `C` - Clear cache
- `Ctrl/Cmd + S` - Save (in editor)
- `Ctrl/Cmd + Enter` - Rerun

## Version Info

- **Python**: 3.11+
- **PostgreSQL**: 15+
- **Streamlit**: 1.29+
- **SQLAlchemy**: 2.0+
- **Pydantic**: 2.5+

---

**Keep this guide handy for quick reference!**
