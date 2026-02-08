# System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Kalshi Markets Dashboard                            │
│                          Production Architecture                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND LAYER                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     Streamlit Dashboard                               │  │
│  │                   (Railway or Streamlit Cloud)                       │  │
│  ├──────────────────────────────────────────────────────────────────────┤  │
│  │                                                                       │  │
│  │  📄 Page 1: New Markets          📈 Page 2: Trending                │  │
│  │  - Last 12h/24h/48h/7d           - High volume markets              │  │
│  │  - Event drill-down              - Volume sorting                   │  │
│  │  - Volume tracking               - Category filters                 │  │
│  │                                                                       │  │
│  │  💬 Page 3: Mentions              🔥 Page 4: Relative Volume         │  │
│  │  - Expiration sorted             - Sports excluded                  │  │
│  │  - "New" indicators              - Baseline comparison              │  │
│  │  - Time remaining                - Volume charts                    │  │
│  │                                                                       │  │
│  │  ⚙️  Page 5: Email Settings                                          │  │
│  │  - Recipients config             - Test email                       │  │
│  │  - Send times                    - Digest logs                      │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                      │                                       │
│                                      │ SQL Queries (Read-Only)              │
│                                      ▼                                       │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                             DATABASE LAYER                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    PostgreSQL 15+ (Railway)                           │  │
│  ├──────────────────────────────────────────────────────────────────────┤  │
│  │                                                                       │  │
│  │  📊 events                   📈 markets                              │  │
│  │  - event_ticker (PK)         - ticker (PK)                           │  │
│  │  - title, category           - prices, volume                        │  │
│  │  - timestamps                - status, flags                         │  │
│  │                              - is_trending, is_mention               │  │
│  │                                                                       │  │
│  │  📸 market_snapshots         ⚙️  email_settings                      │  │
│  │  - hourly volume data        - recipients, times                    │  │
│  │  - time-series analysis      - thresholds                           │  │
│  │                                                                       │  │
│  │  📧 email_digest_logs        🏷️  categories                          │  │
│  │  - delivery status           - sports exclusion                     │  │
│  │  - counts, errors                                                    │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                       ▲                              ▲                       │
│                       │                              │                       │
│                  SQL Write                      SQL Write                    │
│                       │                              │                       │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                            WORKER LAYER                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │               Data Ingestion Worker (Railway Cron)                    │  │
│  │               Schedule: 0 * * * * (Every Hour)                       │  │
│  ├──────────────────────────────────────────────────────────────────────┤  │
│  │                                                                       │  │
│  │  1. Fetch Events/Markets from Kalshi API                            │  │
│  │  2. Upsert Events (by event_ticker)                                 │  │
│  │  3. Upsert Markets (by ticker)                                      │  │
│  │  4. Identify Trending (top 50 by volume_24h)                        │  │
│  │  5. Identify Mentions (keyword matching)                            │  │
│  │  6. Create Snapshots (hourly volume data)                           │  │
│  │  7. Cleanup (delete snapshots >60 days)                             │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                      │                                       │
│                            HTTP Requests                                     │
│                                      ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │             Email Digest Workers (Railway Cron × 4)                  │  │
│  │             Schedules: 11:00, 17:00, 23:00, 05:00 UTC               │  │
│  │             (6am, 12pm, 6pm, 12am Eastern Time)                      │  │
│  ├──────────────────────────────────────────────────────────────────────┤  │
│  │                                                                       │  │
│  │  1. Check email settings schedule                                   │  │
│  │  2. Query database for digest data:                                 │  │
│  │     - Top 10 New Markets (by volume)                                │  │
│  │     - All Trending Markets                                          │  │
│  │     - All "New" Mention Markets                                     │  │
│  │     - Top N Relative Volume Standouts                               │  │
│  │  3. Generate HTML email                                             │  │
│  │  4. Send via Resend                                               │  │
│  │  5. Log delivery status                                             │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                      │                                       │
│                              SMTP/API                                        │
│                                      ▼                                       │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL SERVICES                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────┐   ┌──────────────────────┐                     │
│  │    Kalshi API          │   │    Resend          │                     │
│  │  (Market Data Source)  │   │  (Email Delivery)    │                     │
│  ├────────────────────────┤   ├──────────────────────┤                     │
│  │                        │   │                      │                     │
│  │  - GET /events         │   │  - Send HTML emails  │                     │
│  │  - GET /markets        │   │  - Delivery tracking │                     │
│  │  - GET /search/tags    │   │  - 100 emails/day    │                     │
│  │  - POST /login         │   │    (free tier)       │                     │
│  │                        │   │                      │                     │
│  │  Rate Limit:           │   │  Recipients:         │                     │
│  │  10 req/s              │   │  surfshopcapital@    │                     │
│  │                        │   │  gmail.com           │                     │
│  └────────────────────────┘   └──────────────────────┘                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                            DATA FLOW                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. Kalshi API → Ingestion Worker → PostgreSQL                             │
│     (Every hour)                                                             │
│                                                                              │
│  2. PostgreSQL → Streamlit Dashboard → User Browser                         │
│     (On-demand, cached queries)                                              │
│                                                                              │
│  3. PostgreSQL → Email Worker → Resend → Recipients                       │
│     (4x daily: 6am, 12pm, 6pm, 12am ET)                                    │
│                                                                              │
│  4. User → Email Settings Page → PostgreSQL                                 │
│     (Configuration updates)                                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         DEPLOYMENT TOPOLOGY                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                          Railway                                 │       │
│  │                                                                  │       │
│  │  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐│       │
│  │  │   PostgreSQL    │  │  Ingestion Cron  │  │  Email Cron ×4 ││       │
│  │  │   (Persistent)  │  │   (Hourly Run)   │  │  (Daily Runs)  ││       │
│  │  └─────────────────┘  └──────────────────┘  └────────────────┘│       │
│  │                                                                  │       │
│  │  Optional:                                                       │       │
│  │  ┌────────────────────────────────────────────────────────────┐│       │
│  │  │              Streamlit Service                              ││       │
│  │  │              (Web Server)                                   ││       │
│  │  └────────────────────────────────────────────────────────────┘│       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                                                              │
│  OR                                                                          │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                     Streamlit Cloud                              │       │
│  │                                                                  │       │
│  │  ┌────────────────────────────────────────────────────────────┐│       │
│  │  │              Streamlit App                                  ││       │
│  │  │              (Connects to Railway PostgreSQL)               ││       │
│  │  └────────────────────────────────────────────────────────────┘│       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         MONITORING & LOGGING                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  📊 Worker Logs:                     📈 Database Queries:                   │
│  - logs/ingestion.log                - Last ingestion time                  │
│  - logs/emailer.log                  - Market counts by status              │
│  - Railway log viewer                - Email digest logs                    │
│                                                                              │
│  🔔 Alerts:                          📧 Email Logs:                         │
│  - Railway service failures          - email_digest_logs table              │
│  - Database connection errors        - Success/failure tracking             │
│  - API rate limit hits               - Recipient confirmation               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         SECURITY & SECRETS                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  🔒 Environment Variables (Railway):                                        │
│  - DATABASE_URL          (PostgreSQL connection)                            │
│  - KALSHI_API_BASE_URL   (public API - no auth)                             │
│  - RESEND_API_KEY      (Email delivery)                                   │
│  - EMAIL_FROM            (Sender address)                                   │
│                                                                              │
│  🔐 Best Practices:                                                         │
│  - No hardcoded secrets in code                                             │
│  - .env for local development                                               │
│  - Railway secrets for production                                           │
│  - Read-only DB user for Streamlit (recommended)                            │
│  - HTTPS enforced (Railway + Streamlit Cloud)                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         KEY TECHNOLOGIES                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Language:        Python 3.11+                                              │
│  Frontend:        Streamlit 1.29+                                           │
│  Database:        PostgreSQL 15+                                            │
│  ORM:             SQLAlchemy 2.0+                                           │
│  Validation:      Pydantic 2.5+                                             │
│  HTTP Client:     Requests + Retry                                          │
│  Email:           Resend API                                              │
│  Deployment:      Railway (backend) + Streamlit Cloud (frontend)            │
│  Scheduling:      Railway Cron                                              │
│  Logging:         Structlog                                                 │
│  Charts:          Plotly                                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         PERFORMANCE METRICS                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Ingestion Worker:                                                           │
│  - Runtime: ~2-5 minutes                                                    │
│  - API Calls: ~100 per run                                                  │
│  - Frequency: Every hour                                                    │
│                                                                              │
│  Email Worker:                                                               │
│  - Runtime: ~30 seconds                                                     │
│  - Queries: 4-6 per run                                                     │
│  - Frequency: 4x daily                                                      │
│                                                                              │
│  Dashboard:                                                                  │
│  - Page load: <2 seconds (cached)                                           │
│  - Query time: <500ms (indexed)                                             │
│  - Cache TTL: 5 minutes                                                     │
│                                                                              │
│  Database:                                                                   │
│  - Size: ~100-500 MB (with 60 days snapshots)                              │
│  - Connections: 10 (pool size)                                              │
│  - Indexes: 20+ (optimized)                                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         COST ESTIMATES                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Railway:           $5-10/month (PostgreSQL + cron workers)                 │
│  Streamlit Cloud:   Free (Community tier) or $10/month                      │
│  Resend:          Free (3,000 emails/month, only need ~4/day)                 │
│                                                                              │
│  Total:             $5-20/month depending on configuration                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Architecture Summary

**3-Tier Architecture:**
1. **Frontend**: Streamlit dashboard (read-only queries)
2. **Backend**: PostgreSQL database (persistent storage)
3. **Workers**: Cron jobs for data ingestion + email digests

**Data Flow:**
```
Kalshi API → Ingestion → PostgreSQL → Dashboard → User
                    ↓
                Email Worker → Resend → Recipients
```

**Deployment:**
```
Railway: PostgreSQL + Workers (cron)
Streamlit Cloud: Dashboard (optional)
```

**Key Features:**
- Hourly data refresh
- 4x daily email digests
- 5 analytical pages
- Real-time filtering
- Trend identification
- Volume analysis
- Email configuration

---

For detailed information, see:
- **README.md** - Full documentation
- **DEPLOYMENT.md** - Deployment guide
- **PROJECT_SUMMARY.md** - Project overview
