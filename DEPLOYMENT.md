# Deployment Guide

This guide covers deploying the Kalshi Markets Dashboard to production using Railway and Streamlit Cloud.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Option 1: Railway (All-in-One)](#option-1-railway-all-in-one)
- [Option 2: Railway + Streamlit Cloud](#option-2-railway--streamlit-cloud)
- [Post-Deployment](#post-deployment)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Overview

**Architecture:**
- **Database:** PostgreSQL on Railway
- **Workers:** Hourly ingestion + 4x daily email digests on Railway Cron
- **Frontend:** Streamlit on Railway or Streamlit Cloud

## Prerequisites

1. **Railway Account**
   - Sign up at https://railway.app
   - Install CLI: `npm install -g @railway/cli`

2. **Streamlit Cloud Account** (optional)
   - Sign up at https://share.streamlit.io

3. **API Keys**
   - Kalshi API credentials (from https://kalshi.com)
   - Resend API key (from https://resend.com, 3,000 emails/month free)

4. **Git Repository**
   - Push code to GitHub/GitLab

## Option 1: Railway (All-in-One)

Deploy everything (database, workers, and frontend) on Railway.

### Step 1: Create Railway Project

```bash
# Login to Railway
railway login

# Create new project
railway init

# Link to existing project (if you already created one)
railway link
```

### Step 2: Add PostgreSQL Database

```bash
# Add PostgreSQL plugin
railway add --plugin postgresql
```

Railway will automatically set the `DATABASE_URL` environment variable.

### Step 3: Set Environment Variables

Go to Railway dashboard → Your Project → Variables, and add:

```
KALSHI_API_BASE_URL=https://api.elections.kalshi.com/trade-api/v2

RESEND_API_KEY=re_your_resend_key
EMAIL_FROM=onboarding@resend.dev
EMAIL_FROM_NAME=Kalshi Markets Digest

LOG_LEVEL=INFO
TIMEZONE=America/New_York
```

### Step 4: Initialize Database

```bash
# Get DATABASE_URL
railway variables

# Run schema (locally, connecting to Railway DB)
export DATABASE_URL="postgresql://..."
psql $DATABASE_URL < db/schema.sql

# Or run bootstrap script
railway run python bootstrap.py
```

### Step 5: Deploy Services

The `railway.toml` file defines all services. Deploy with:

```bash
railway up
```

This will deploy:
- Ingestion worker (hourly cron)
- 4x email workers (6am, noon, 6pm, midnight ET)

### Step 6: Add Streamlit Service (Optional)

If hosting Streamlit on Railway:

```bash
# Create new service
railway service create streamlit-app

# Configure service
railway service --name streamlit-app
```

Add environment variables for the service:
- Start command: `streamlit run app/main.py --server.port $PORT`
- Build command: `pip install -r requirements.txt`

### Step 7: Verify Deployment

```bash
# Check service status
railway status

# View logs
railway logs

# Check specific service
railway logs --service ingestion-worker
```

## Option 2: Railway + Streamlit Cloud

Deploy backend on Railway, frontend on Streamlit Cloud (recommended for simplicity).

### Railway Setup (Database + Workers)

Follow Steps 1-5 from Option 1.

### Streamlit Cloud Setup

1. **Connect Repository**
   - Go to https://share.streamlit.io
   - Click "New app"
   - Select your GitHub repository
   - Set main file: `app/main.py`
   - Set branch: `main`

2. **Configure Secrets**
   
   Click "Advanced settings" → "Secrets" and add:

   ```toml
   # Database connection (read-only)
   DATABASE_URL = "postgresql://user:pass@railway-host:5432/kalshi_markets"
   
   # App settings
   LOG_LEVEL = "INFO"
   TIMEZONE = "America/New_York"
   ```

   Get the `DATABASE_URL` from Railway dashboard.

3. **Deploy**
   
   Click "Deploy" - Streamlit Cloud will build and deploy automatically.

## Post-Deployment

### 1. Run Initial Data Ingestion

```bash
# Trigger ingestion worker manually
railway run --service ingestion-worker python workers/ingest.py
```

Or wait for the hourly cron to run.

### 2. Configure Email Settings

1. Open your Streamlit dashboard
2. Navigate to "Email Settings" page
3. Verify default settings or customize:
   - Recipients
   - Send times
   - Enabled sections
   - Thresholds

### 3. Test Email Digest

Click "Send Test Email Now" in the Email Settings page to verify email delivery.

### 4. Verify Cron Schedules

Check Railway dashboard → Your Project → Services → Cron Jobs

Verify schedules:
- **Ingestion**: `0 * * * *` (every hour)
- **Email 6am ET**: `0 11 * * *` (11:00 UTC)
- **Email noon ET**: `0 17 * * *` (17:00 UTC)
- **Email 6pm ET**: `0 23 * * *` (23:00 UTC)
- **Email midnight ET**: `0 5 * * *` (05:00 UTC)

**Note:** Railway cron uses UTC. Eastern Time schedules are converted:
- ET = UTC - 5 hours (EST)
- ET = UTC - 4 hours (EDT during daylight saving)

## Monitoring

### Railway Logs

```bash
# View all logs
railway logs

# View specific service
railway logs --service ingestion-worker
railway logs --service email-worker-6am

# Follow logs in real-time
railway logs --follow
```

### Database Health Checks

```bash
# Connect to database
railway run psql $DATABASE_URL

# Check recent ingestion
SELECT MAX(first_seen_at) as last_ingestion FROM events;

# Check email logs
SELECT * FROM email_digest_logs ORDER BY sent_at DESC LIMIT 10;

# Count markets
SELECT status, COUNT(*) FROM markets GROUP BY status;
```

### Streamlit Dashboard

Monitor via the dashboard itself:
- Check "Email Settings" page for recent digest logs
- Verify data freshness on each page
- Look for error messages

### Alerts

Set up Railway notifications:
1. Go to Railway dashboard → Project settings
2. Add notification channels (Slack, Discord, email)
3. Configure alerts for service failures

## Troubleshooting

### Workers Not Running

**Check cron schedule:**
```bash
railway logs --service ingestion-worker
```

Look for error messages. Common issues:
- Database connection failed → Check `DATABASE_URL`
- API authentication failed → Verify Kalshi credentials
- Module not found → Check `PYTHONPATH` in Dockerfile

**Manually trigger:**
```bash
railway run --service ingestion-worker python workers/ingest.py
```

### Emails Not Sending

1. **Check Resend API key:**
   ```bash
   railway variables | grep RESEND
   ```

2. **Check email logs:**
   ```sql
   SELECT * FROM email_digest_logs 
   WHERE success = false 
   ORDER BY sent_at DESC;
   ```

3. **Test manually:**
   ```bash
   railway run python workers/emailer.py --force
   ```

4. **Verify Resend:**
   - Check Resend dashboard for rejected emails
   - Verify sender email is authenticated
   - Check spam folders

### No Data in Dashboard

1. **Check last ingestion:**
   ```sql
   SELECT MAX(first_seen_at) FROM events;
   ```

2. **Run manual ingestion:**
   ```bash
   railway run python workers/ingest.py
   ```

3. **Check Kalshi API:**
   - Verify credentials
   - Check rate limits
   - Test API manually: `curl https://api.elections.kalshi.com/trade-api/v2/markets`

### Database Connection Errors

1. **Verify DATABASE_URL:**
   ```bash
   railway variables | grep DATABASE_URL
   ```

2. **Test connection:**
   ```bash
   railway run psql $DATABASE_URL -c "SELECT 1;"
   ```

3. **Check PostgreSQL status:**
   - Railway dashboard → Database service
   - Look for restart events or errors

### Streamlit App Errors

1. **Check Streamlit logs:**
   - Streamlit Cloud: Dashboard → App → Logs
   - Railway: `railway logs --service streamlit-app`

2. **Verify DATABASE_URL:**
   - Streamlit Cloud: Settings → Secrets
   - Railway: Variables tab

3. **Common fixes:**
   - Clear Streamlit cache: Reboot app
   - Check Python version compatibility
   - Verify all dependencies in requirements.txt

## Scaling

### Increase Cron Frequency

Edit `railway.toml` to adjust schedules:

```toml
# Run ingestion every 30 minutes
- schedule: "*/30 * * * *"
  command: "python workers/ingest.py"
```

### Add More Email Times

Add new email worker services in `railway.toml`:

```toml
email-worker-9am:
  # ... same config ...
  cron:
    - schedule: "0 14 * * *"  # 9am ET = 14:00 UTC
      command: "python workers/emailer.py --force"
```

### Upgrade Database

Railway offers:
- Shared (free): Development/testing
- Dedicated ($5/mo): Small production
- High Memory ($10/mo): Larger datasets

Upgrade via Railway dashboard → Database service → Plan

## Backup and Recovery

### Database Backups

Railway automatically backs up PostgreSQL. Manual backup:

```bash
# Backup
railway run pg_dump $DATABASE_URL > backup.sql

# Restore
railway run psql $DATABASE_URL < backup.sql
```

### Configuration Backup

Export environment variables:
```bash
railway variables > env_backup.txt
```

## Cost Estimates

### Railway
- **Hobby Plan** (Free):
  - $5 credit/month
  - 500 hours execution
  - Shared CPU/memory
  - Good for testing

- **Developer Plan** ($5/mo):
  - $5 credit included
  - Dedicated PostgreSQL
  - More resources

- **Team Plan** ($20/mo):
  - $20 credit included
  - Production workload

**Expected usage:**
- Database: ~$5/mo
- Cron workers: Minimal (5 services)
- **Total: $5-10/mo**

### Streamlit Cloud
- **Community** (Free): 1 app
- **Team** ($42/mo): Unlimited apps, custom domains

### Resend
- **Free**: 3,000 emails/month (100/day), permanent - no trial
- **Pro** ($20/mo): 50,000 emails/month

**4 emails/day = ~120/month → Free tier sufficient**

## Security Best Practices

1. **Never commit secrets:**
   - Use `.env` for local development
   - Use Railway/Streamlit secrets for production
   - Add `.env` to `.gitignore`

2. **Use read-only database user for Streamlit:**
   ```sql
   CREATE USER streamlit_readonly WITH PASSWORD 'password';
   GRANT CONNECT ON DATABASE kalshi_markets TO streamlit_readonly;
   GRANT USAGE ON SCHEMA public TO streamlit_readonly;
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO streamlit_readonly;
   ```

3. **Rotate API keys regularly:**
   - Kalshi API keys
   - Resend API key
   - Database passwords

4. **Enable Railway MFA:**
   - Railway dashboard → Account → Security

5. **Use HTTPS only:**
   - Railway and Streamlit Cloud enforce HTTPS by default

## Support

- **Railway Discord:** https://discord.gg/railway
- **Streamlit Forum:** https://discuss.streamlit.io
- **Kalshi API Docs:** https://docs.kalshi.com
- **Resend Support:** https://resend.com/docs

---

**Need help?** Check logs first, then consult troubleshooting section.
