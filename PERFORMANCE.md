# Performance Optimizations

## Changes Made for Speed

### 1. Sports Filtering
- **Before**: Processed all events including sports
- **After**: Sports events completely excluded during ingestion
- **Impact**: ~40-60% fewer markets to process

### 2. Volume Threshold
- **Rule**: Markets older than 3 days with <$1000 volume are excluded
- **Impact**: Removes low-activity markets that don't need tracking

### 3. Active Markets Only
- **Rule**: Only `status="active"` markets are processed
- **Impact**: No processing of closed/settled markets

### 4. Bulk Database Operations
- **Before**: Row-by-row INSERT/UPDATE (N queries for N markets)
- **After**: Bulk INSERT ... ON CONFLICT (1-2 queries total)
- **Impact**: ~90% faster database operations

### 5. Streamlined Schema
- **Removed fields**: `no_bid`, `no_ask` (derived: 100 - yes_ask/yes_bid)
- **Removed fields**: `updated_time`, `settlement_timer_seconds`, `result`, `settlement_value`, `settlement_ts`
- **Impact**: Smaller rows, faster inserts, less storage

### 6. Snapshot Optimization
- **Before**: Snapshot every open market
- **After**: Only snapshot markets with volume > 0
- **Impact**: 50-70% fewer snapshots

### 7. Faster Refresh Cadence
- **Before**: Hourly (60 minutes)
- **After**: Every 15 minutes
- **Impact**: More up-to-date data with 4x frequency

## Expected Performance

### Before Optimizations
- Ingestion time: 20+ minutes
- Markets processed: ~2000-3000
- Database writes: ~6000-9000 queries

### After Optimizations
- Ingestion time: **2-5 minutes**
- Markets processed: ~800-1200 (non-sports, active, high-volume)
- Database writes: **20-50 bulk queries**

## Speed Improvement: ~4-10x faster

---

## What Was Slowing Things Down?

1. **Row-by-row DB operations** - Each market was a separate query
2. **Processing all markets** - Including sports, closed, and low-volume
3. **No filtering** - Downloaded and processed everything from API
4. **Redundant fields** - Storing data that can be derived

## Dashboard Features Added

- **Manual Refresh Button** on every page
- **Last Updated Timestamp** showing time since refresh
- **Auto-refresh indicator** (every 15 min)
- **Instant feedback** when clicking refresh
