-- Kalshi Markets Database Schema

-- Events table
CREATE TABLE IF NOT EXISTS events (
    event_ticker VARCHAR(100) PRIMARY KEY,
    series_ticker VARCHAR(100),
    title TEXT NOT NULL,
    sub_title TEXT,
    category VARCHAR(100),
    mutually_exclusive BOOLEAN DEFAULT TRUE,
    strike_date TIMESTAMP,
    strike_period VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_events_category ON events(category);
CREATE INDEX idx_events_series_ticker ON events(series_ticker);
CREATE INDEX idx_events_created_at ON events(created_at);
CREATE INDEX idx_events_first_seen_at ON events(first_seen_at);

-- Markets table
CREATE TABLE IF NOT EXISTS markets (
    ticker VARCHAR(100) PRIMARY KEY,
    event_ticker VARCHAR(100) REFERENCES events(event_ticker) ON DELETE CASCADE,
    market_type VARCHAR(20) DEFAULT 'binary',
    title TEXT NOT NULL,
    subtitle TEXT,
    yes_sub_title TEXT,
    no_sub_title TEXT,
    created_time TIMESTAMP,
    updated_time TIMESTAMP,
    open_time TIMESTAMP,
    close_time TIMESTAMP,
    expiration_time TIMESTAMP,
    settlement_timer_seconds INTEGER,
    status VARCHAR(20),
    volume INTEGER DEFAULT 0,
    volume_24h INTEGER DEFAULT 0,
    open_interest INTEGER DEFAULT 0,
    yes_bid INTEGER,
    yes_ask INTEGER,
    no_bid INTEGER,
    no_ask INTEGER,
    last_price INTEGER,
    liquidity INTEGER,
    can_close_early BOOLEAN DEFAULT FALSE,
    result VARCHAR(10),
    settlement_value INTEGER,
    settlement_ts TIMESTAMP,
    is_mention BOOLEAN DEFAULT FALSE,
    is_trending BOOLEAN DEFAULT FALSE,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_markets_event_ticker ON markets(event_ticker);
CREATE INDEX idx_markets_status ON markets(status);
CREATE INDEX idx_markets_created_time ON markets(created_time);
CREATE INDEX idx_markets_open_time ON markets(open_time);
CREATE INDEX idx_markets_close_time ON markets(close_time);
CREATE INDEX idx_markets_expiration_time ON markets(expiration_time);
CREATE INDEX idx_markets_first_seen_at ON markets(first_seen_at);
CREATE INDEX idx_markets_is_mention ON markets(is_mention);
CREATE INDEX idx_markets_is_trending ON markets(is_trending);
CREATE INDEX idx_markets_volume_24h ON markets(volume_24h);

-- Market snapshots for time-series data
CREATE TABLE IF NOT EXISTS market_snapshots (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(100) REFERENCES markets(ticker) ON DELETE CASCADE,
    snapshot_time TIMESTAMP NOT NULL,
    volume INTEGER,
    volume_24h INTEGER,
    open_interest INTEGER,
    yes_bid INTEGER,
    yes_ask INTEGER,
    no_bid INTEGER,
    no_ask INTEGER,
    last_price INTEGER,
    liquidity INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_snapshots_ticker ON market_snapshots(ticker);
CREATE INDEX idx_snapshots_snapshot_time ON market_snapshots(snapshot_time);
CREATE INDEX idx_snapshots_ticker_time ON market_snapshots(ticker, snapshot_time);

-- Email settings table
CREATE TABLE IF NOT EXISTS email_settings (
    id INTEGER PRIMARY KEY DEFAULT 1,
    recipients TEXT[] NOT NULL DEFAULT ARRAY['surfshopcapital@gmail.com'],
    send_times TEXT[] NOT NULL DEFAULT ARRAY['06:00', '12:00', '18:00', '00:00'],
    timezone VARCHAR(50) NOT NULL DEFAULT 'America/New_York',
    enabled_sections JSONB NOT NULL DEFAULT '{"new_markets": true, "trending": true, "mentions": true, "relative_volume": true}',
    new_markets_window_hours INTEGER NOT NULL DEFAULT 24,
    mentions_new_window_hours INTEGER NOT NULL DEFAULT 24,
    relative_volume_period_hours INTEGER NOT NULL DEFAULT 24,
    relative_volume_baseline_days INTEGER NOT NULL DEFAULT 7,
    relative_volume_top_n INTEGER NOT NULL DEFAULT 10,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_single_row CHECK (id = 1)
);

-- Insert default email settings
INSERT INTO email_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- Email digest logs
CREATE TABLE IF NOT EXISTS email_digest_logs (
    id SERIAL PRIMARY KEY,
    sent_at TIMESTAMP NOT NULL,
    recipients TEXT[] NOT NULL,
    sections_included TEXT[] NOT NULL,
    new_markets_count INTEGER DEFAULT 0,
    trending_markets_count INTEGER DEFAULT 0,
    mentions_count INTEGER DEFAULT 0,
    relative_volume_count INTEGER DEFAULT 0,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_digest_logs_sent_at ON email_digest_logs(sent_at);

-- Category metadata for sports exclusion
CREATE TABLE IF NOT EXISTS categories (
    name VARCHAR(100) PRIMARY KEY,
    is_sports BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_events_updated_at BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_email_settings_updated_at BEFORE UPDATE ON email_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
