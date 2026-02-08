# Storage and Performance Configuration

## Current Settings

### Worker Schedule
- **Frequency**: Every 30 minutes (48 runs/day)
- **Snapshot retention**: 30 days
- **Markets snapshotted**: Only active/open markets with volume > 0

### Storage Calculation

**Daily snapshots**:
- Runs per day: 48
- Markets per run: ~5,000
- Snapshots per day: 48 × 5,000 = **240,000 rows**

**30-day retention**:
- Total snapshot rows: 240,000 × 30 = **7.2M rows**
- Size per row: ~100-150 bytes
- Total snapshot storage: **~0.7-1 GB**

**Other tables** (events, markets, categories, etc.): **~50-100 MB**

**Total database size**: **~0.8-1.2 GB**

---

## Railway Plans

| Plan | Storage | Cost | Fit |
|------|---------|------|-----|
| Hobby | 1 GB | Free | Tight (monitor usage) |
| Developer | 8 GB | $5/mo | Good |
| Team | 50 GB | $20/mo | Plenty |

With current settings (30 min, 30 days), you're at the edge of the 1 GB free tier.

---

## If You Need to Reduce Storage

### Option 1: Longer Intervals
- **Hourly** (60 min): ~180k snapshots/day → **~0.5 GB** (30 days)
- **Every 2 hours**: ~90k snapshots/day → **~0.25 GB** (30 days)

### Option 2: Shorter Retention
- **15 days**: Half the storage (~0.4-0.6 GB)
- **7 days**: Quarter the storage (~0.2-0.3 GB)

### Option 3: Selective Snapshots
Only snapshot:
- Trending markets
- Mention markets
- Markets with volume_24h > threshold

This could reduce snapshots by 50-80%.

---

## Trend Calculation

### How It Works Now

**30-min trend**:
- Compares current `last_price` to snapshot from 30 minutes ago (±15 min tolerance)
- Shows: `↗ +5¢`, `↘ -3¢`, or `→ Flat`

**24h trend**:
- Compares current `last_price` to snapshot from 24 hours ago (±15 min tolerance)
- Shows: `↗ +12¢`, `↘ -8¢`, or `→ Flat`

### Data Requirements

- Requires snapshots to exist from 30 min and 24h ago
- First few runs won't have 24h data yet
- After 24 hours of worker runs, full trends will appear

### Threshold

Price change must be >2¢ to show as up/down, otherwise "Flat".

---

## Monitoring Storage

Check your Railway Postgres usage:
1. Railway Dashboard → Postgres service
2. "Metrics" tab → Storage usage graph

Watch for the ~1 GB limit on the free tier.
