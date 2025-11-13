-- TimescaleDB Initialization Script
-- This script runs automatically when the container starts

-- Create extension (TimescaleDB is pre-installed in the image)
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create main data table for storing commodity prices
CREATE TABLE IF NOT EXISTS price_data (
    time TIMESTAMPTZ NOT NULL,
    instrument_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    bid NUMERIC NOT NULL,
    ask NUMERIC NOT NULL,
    spread NUMERIC,
    volume BIGINT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create hypertable for better compression and retention policies
-- TimescaleDB automatically handles the chunking
SELECT create_hypertable('price_data', 'time', if_not_exists => TRUE);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_price_data_instrument_time
    ON price_data (instrument_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_price_data_symbol
    ON price_data (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_price_data_time
    ON price_data (time DESC);

-- Create table for storing technical analysis results
CREATE TABLE IF NOT EXISTS analysis_results (
    time TIMESTAMPTZ NOT NULL,
    instrument_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    rsi NUMERIC,
    macd NUMERIC,
    macd_signal NUMERIC,
    macd_histogram NUMERIC,
    bollinger_upper NUMERIC,
    bollinger_middle NUMERIC,
    bollinger_lower NUMERIC,
    atr NUMERIC,
    sma_20 NUMERIC,
    sma_50 NUMERIC,
    sma_200 NUMERIC,
    signal_type TEXT,
    signal_confidence NUMERIC,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create hypertable for analysis results
SELECT create_hypertable('analysis_results', 'time', if_not_exists => TRUE);

-- Create indexes for analysis results
CREATE INDEX IF NOT EXISTS idx_analysis_instrument_time
    ON analysis_results (instrument_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_symbol
    ON analysis_results (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_signal_type
    ON analysis_results (signal_type) WHERE signal_type IS NOT NULL;

-- Create table for storing trading signals
CREATE TABLE IF NOT EXISTS trading_signals (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL,
    instrument_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    entry_price NUMERIC NOT NULL,
    target_price NUMERIC,
    stop_loss NUMERIC,
    risk_reward_ratio NUMERIC,
    confidence NUMERIC,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMPTZ
);

-- Create indexes for trading signals
CREATE INDEX IF NOT EXISTS idx_signals_instrument_time
    ON trading_signals (instrument_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_signals_symbol
    ON trading_signals (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_signals_status
    ON trading_signals (status) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_signals_created
    ON trading_signals (created_at DESC);

-- Create table for commodities metadata
CREATE TABLE IF NOT EXISTS instruments (
    id TEXT PRIMARY KEY,
    symbol TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    exchange TEXT,
    currency TEXT DEFAULT 'USD',
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for instruments
CREATE INDEX IF NOT EXISTS idx_instruments_category
    ON instruments (category);
CREATE INDEX IF NOT EXISTS idx_instruments_symbol
    ON instruments (symbol);

-- Insert supported commodities metadata
INSERT INTO instruments (id, symbol, name, category, description)
VALUES
    -- Precious Metals
    ('xau_usd', 'XAU/USD', 'Gold', 'Precious Metals', 'Gold spot price in USD per troy ounce'),
    ('xag_usd', 'XAG/USD', 'Silver', 'Precious Metals', 'Silver spot price in USD per troy ounce'),
    ('xpt_usd', 'XPT/USD', 'Platinum', 'Precious Metals', 'Platinum spot price in USD per troy ounce'),
    ('xpd_usd', 'XPD/USD', 'Palladium', 'Precious Metals', 'Palladium spot price in USD per troy ounce'),

    -- Energy
    ('bco_usd', 'BCO/USD', 'Brent Crude', 'Energy', 'Brent crude oil price in USD per barrel'),
    ('wtico_usd', 'WTICO/USD', 'WTI Crude', 'Energy', 'West Texas Intermediate crude oil price in USD per barrel'),
    ('natgas_usd', 'NATGAS/USD', 'Natural Gas', 'Energy', 'Natural gas price in USD per MMBtu'),

    -- Agriculture
    ('corn_usd', 'CORN/USD', 'Corn', 'Agriculture', 'Corn futures price in USD per bushel'),
    ('soybn_usd', 'SOYBN/USD', 'Soybeans', 'Agriculture', 'Soybean futures price in USD per bushel'),
    ('wheat_usd', 'WHEAT/USD', 'Wheat', 'Agriculture', 'Wheat futures price in USD per bushel'),
    ('sugar_usd', 'SUGAR/USD', 'Sugar', 'Agriculture', 'Sugar futures price in USD per pound')
ON CONFLICT DO NOTHING;

-- Create continuous aggregate for daily OHLC data (for performance)
CREATE MATERIALIZED VIEW IF NOT EXISTS price_data_daily AS
    SELECT
        time_bucket('1 day', time) as bucket,
        instrument_id,
        symbol,
        first(bid, time) as open_bid,
        max(bid) as high_bid,
        min(bid) as low_bid,
        last(bid, time) as close_bid,
        first(ask, time) as open_ask,
        max(ask) as high_ask,
        min(ask) as low_ask,
        last(ask, time) as close_ask,
        avg((bid + ask) / 2) as avg_price,
        sum(volume) as total_volume
    FROM price_data
    GROUP BY bucket, instrument_id, symbol;

-- Create index on continuous aggregate
CREATE INDEX IF NOT EXISTS idx_price_data_daily_bucket
    ON price_data_daily (bucket DESC, instrument_id);

-- Set up retention policy: keep raw price data for 90 days
SELECT add_retention_policy('price_data', INTERVAL '90 days', if_not_exists => true);

-- Set up retention policy: keep analysis results for 90 days
SELECT add_retention_policy('analysis_results', INTERVAL '90 days', if_not_exists => true);

-- Set up retention policy: keep signals for 1 year (for historical analysis)
SELECT add_retention_policy('trading_signals', INTERVAL '365 days', if_not_exists => true);

-- Grant permissions to application user (if using separate credentials)
-- Uncomment and modify if you need a separate read-only user
-- CREATE USER screener_readonly WITH PASSWORD 'readonly_password';
-- GRANT CONNECT ON DATABASE screener_db TO screener_readonly;
-- GRANT USAGE ON SCHEMA public TO screener_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO screener_readonly;
-- GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO screener_readonly;

-- Display completion message
\echo '✓ TimescaleDB initialization complete'
\echo '✓ Created hypertables: price_data, analysis_results'
\echo '✓ Created tables: trading_signals, instruments'
\echo '✓ Retention policies configured'
