-- ============================================================================
-- TimescaleDB Continuous Aggregates Setup
--
-- This script sets up continuous aggregates for efficient time-series queries
-- on the ScreenerIII database. These pre-computed aggregates significantly
-- improve query performance for common time-based queries.
--
-- Prerequisites:
-- - TimescaleDB extension must be installed and enabled
-- - Tables must already be converted to hypertables
-- - Run with a user who has CREATE MATERIALIZED VIEW permissions
--
-- Usage:
--   psql -h localhost -d screeneriii -f timescaledb_aggregates.sql
-- ============================================================================

-- ============================================================================
-- 1. HOURLY OHLC AGGREGATE
--
-- Creates a continuous aggregate of hourly OHLC data from market_data table.
-- Automatically maintained by TimescaleDB.
-- ============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS market_data_hourly_ohlc
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', timestamp) AS time,
    instrument,
    timeframe,
    FIRST(open, timestamp) AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    LAST(close, timestamp) AS close,
    SUM(volume) AS volume
FROM market_data
GROUP BY time_bucket('1 hour', timestamp), instrument, timeframe
WITH DATA;

-- Create index on hourly aggregate for faster queries
CREATE INDEX IF NOT EXISTS idx_market_data_hourly_ohlc_time
ON market_data_hourly_ohlc (time DESC);

CREATE INDEX IF NOT EXISTS idx_market_data_hourly_ohlc_instrument_time
ON market_data_hourly_ohlc (instrument, time DESC);

-- Add automatic refresh policy for hourly aggregate
SELECT add_continuous_aggregate_policy(
    'market_data_hourly_ohlc',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 2. DAILY STATISTICS AGGREGATE
--
-- Creates a continuous aggregate of daily statistics from market_data table.
-- ============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS market_data_daily_stats
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', timestamp) AS time,
    instrument,
    timeframe,
    FIRST(open, timestamp) AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    LAST(close, timestamp) AS close,
    SUM(volume) AS volume,
    COUNT(*) AS candle_count
FROM market_data
GROUP BY time_bucket('1 day', timestamp), instrument, timeframe
WITH DATA;

-- Create indexes on daily aggregate
CREATE INDEX IF NOT EXISTS idx_market_data_daily_stats_time
ON market_data_daily_stats (time DESC);

CREATE INDEX IF NOT EXISTS idx_market_data_daily_stats_instrument_time
ON market_data_daily_stats (instrument, time DESC);

-- Add automatic refresh policy for daily aggregate
SELECT add_continuous_aggregate_policy(
    'market_data_daily_stats',
    start_offset => INTERVAL '2 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day'
)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 3. SIGNAL VOLUME AGGREGATE
--
-- Creates a continuous aggregate tracking signal generation patterns.
-- ============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS trading_signals_hourly_stats
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', timestamp) AS time,
    instrument,
    signal_type,
    COUNT(*) AS signal_count,
    AVG(confidence) AS avg_confidence,
    MIN(confidence) AS min_confidence,
    MAX(confidence) AS max_confidence
FROM trading_signals
GROUP BY time_bucket('1 hour', timestamp), instrument, signal_type
WITH DATA;

-- Create indexes on signal aggregate
CREATE INDEX IF NOT EXISTS idx_trading_signals_hourly_time
ON trading_signals_hourly_stats (time DESC);

CREATE INDEX IF NOT EXISTS idx_trading_signals_hourly_instrument_signal
ON trading_signals_hourly_stats (instrument, signal_type, time DESC);

-- ============================================================================
-- 4. PATTERN DETECTION AGGREGATE
--
-- Creates a continuous aggregate for pattern detection statistics.
-- ============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS pattern_detections_daily_stats
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', timestamp) AS time,
    instrument,
    pattern_type,
    COUNT(*) AS pattern_count,
    AVG(confidence) AS avg_confidence,
    SUM(CASE WHEN is_complete THEN 1 ELSE 0 END) AS completed_count,
    SUM(CASE WHEN is_validated THEN 1 ELSE 0 END) AS validated_count
FROM pattern_detections
GROUP BY time_bucket('1 day', timestamp), instrument, pattern_type
WITH DATA;

-- Create indexes on pattern aggregate
CREATE INDEX IF NOT EXISTS idx_pattern_detections_daily_time
ON pattern_detections_daily_stats (time DESC);

CREATE INDEX IF NOT EXISTS idx_pattern_detections_daily_pattern_type
ON pattern_detections_daily_stats (pattern_type, time DESC);

-- ============================================================================
-- 5. COMPRESSION POLICIES
--
-- Enable automatic compression of chunks older than 7 days.
-- This significantly reduces storage while maintaining query performance.
-- ============================================================================

-- Enable compression on market_data table
ALTER TABLE market_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'instrument'
);

-- Add compression policy (compress chunks after 7 days)
SELECT add_compression_policy(
    'market_data',
    INTERVAL '7 days'
)
ON CONFLICT DO NOTHING;

-- Enable compression on trading_signals
ALTER TABLE trading_signals SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'instrument'
);

SELECT add_compression_policy(
    'trading_signals',
    INTERVAL '7 days'
)
ON CONFLICT DO NOTHING;

-- Enable compression on pattern_detections
ALTER TABLE pattern_detections SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'instrument'
);

SELECT add_compression_policy(
    'pattern_detections',
    INTERVAL '7 days'
)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 6. RETENTION POLICIES (Optional)
--
-- Uncomment below to automatically delete data older than specified period.
-- BE CAREFUL: This will permanently delete old data!
-- ============================================================================

-- Keep 90 days of data, automatically delete older data
-- SELECT add_retention_policy('market_data', INTERVAL '90 days');
-- SELECT add_retention_policy('trading_signals', INTERVAL '90 days');
-- SELECT add_retention_policy('pattern_detections', INTERVAL '90 days');

-- ============================================================================
-- 7. PERFORMANCE TUNING SETTINGS
--
-- Configure TimescaleDB for optimal performance
-- ============================================================================

-- Enable parallel queries for better performance on multi-core systems
SET max_parallel_workers_per_gather = 4;
SET max_parallel_workers = 8;
SET parallel_tuple_cost = 0.01;
SET parallel_setup_cost = 250;

-- Increase work memory for better aggregation performance
SET work_mem = '256MB';

-- ============================================================================
-- 8. VACUUM AND ANALYZE
--
-- Optimize database after setting up aggregates
-- ============================================================================

VACUUM ANALYZE market_data;
VACUUM ANALYZE trading_signals;
VACUUM ANALYZE pattern_detections;

-- ============================================================================
-- 9. VERIFICATION QUERIES
--
-- Use these to verify the aggregates are working properly
-- ============================================================================

-- Check continuous aggregates exist
-- SELECT view_name, materialization_hypertable, view_definition
-- FROM timescaledb_information.continuous_aggregates;

-- Check compression policies
-- SELECT hypertable_name, policy_name, config
-- FROM timescaledb_information.compression_policies;

-- Check retention policies
-- SELECT hypertable_name, policy_name, config
-- FROM timescaledb_information.retention_policies;

-- Check aggregate refresh times
-- SELECT view_name, last_run_started_at, last_run_duration, last_successful_run
-- FROM timescaledb_information.continuous_aggregate_stats
-- WHERE view_name IN (
--     'market_data_hourly_ohlc',
--     'market_data_daily_stats',
--     'trading_signals_hourly_stats',
--     'pattern_detections_daily_stats'
-- );

-- ============================================================================
-- 10. QUERY EXAMPLES
--
-- Example queries using the continuous aggregates
-- ============================================================================

-- Get last 24 hours of hourly OHLC data
-- SELECT * FROM market_data_hourly_ohlc
-- WHERE time >= NOW() - INTERVAL '24 hours'
--   AND instrument = 'EUR_USD'
-- ORDER BY time DESC;

-- Get daily statistics for the last 30 days
-- SELECT * FROM market_data_daily_stats
-- WHERE time >= NOW() - INTERVAL '30 days'
--   AND instrument = 'EUR_USD'
-- ORDER BY time DESC;

-- Get signal volume trends
-- SELECT time, instrument, signal_type, signal_count, avg_confidence
-- FROM trading_signals_hourly_stats
-- WHERE time >= NOW() - INTERVAL '7 days'
-- ORDER BY time DESC;

-- ============================================================================
-- END OF SCRIPT
-- ============================================================================
