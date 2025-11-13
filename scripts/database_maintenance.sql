-- ============================================================================
-- Database Maintenance Script for ScreenerIII
--
-- Provides utilities for database maintenance, index optimization,
-- and performance tuning on both SQLite and PostgreSQL/TimescaleDB.
--
-- Usage (PostgreSQL):
--   psql -h localhost -d screeneriii -f database_maintenance.sql
--
-- Usage (SQLite):
--   sqlite3 screener.db < database_maintenance.sql
-- ============================================================================

-- ============================================================================
-- SECTION 1: Table Optimization
--
-- VACUUM - Reclaims unused space
-- ANALYZE - Updates statistics for query planner
-- ============================================================================

-- For SQLite:
-- VACUUM;
-- ANALYZE;

-- For PostgreSQL/TimescaleDB:
-- Uncommit the following and run:
VACUUM ANALYZE market_data;
VACUUM ANALYZE trading_signals;
VACUUM ANALYZE pattern_detections;
VACUUM ANALYZE screener_runs;

-- ============================================================================
-- SECTION 2: Index Management
--
-- Create useful indexes if they don't exist
-- ============================================================================

-- Market Data Indexes
CREATE INDEX IF NOT EXISTS idx_market_data_instrument
ON market_data (instrument);

CREATE INDEX IF NOT EXISTS idx_market_data_timestamp
ON market_data (timestamp);

CREATE INDEX IF NOT EXISTS idx_market_data_instrument_timeframe_timestamp
ON market_data (instrument, timeframe, timestamp);

CREATE INDEX IF NOT EXISTS idx_market_data_timestamp_desc
ON market_data (timestamp DESC);

-- Trading Signals Indexes
CREATE INDEX IF NOT EXISTS idx_trading_signals_instrument
ON trading_signals (instrument);

CREATE INDEX IF NOT EXISTS idx_trading_signals_timestamp
ON trading_signals (timestamp);

CREATE INDEX IF NOT EXISTS idx_trading_signals_signal_type
ON trading_signals (signal_type);

CREATE INDEX IF NOT EXISTS idx_trading_signals_is_active
ON trading_signals (is_active);

CREATE INDEX IF NOT EXISTS idx_trading_signals_instrument_timestamp
ON trading_signals (instrument, timestamp);

CREATE INDEX IF NOT EXISTS idx_trading_signals_active_timestamp
ON trading_signals (is_active, timestamp);

CREATE INDEX IF NOT EXISTS idx_trading_signals_signal_type_active
ON trading_signals (signal_type, is_active);

-- Pattern Detections Indexes
CREATE INDEX IF NOT EXISTS idx_pattern_detections_instrument
ON pattern_detections (instrument);

CREATE INDEX IF NOT EXISTS idx_pattern_detections_timestamp
ON pattern_detections (timestamp);

CREATE INDEX IF NOT EXISTS idx_pattern_detections_pattern_type
ON pattern_detections (pattern_type);

CREATE INDEX IF NOT EXISTS idx_pattern_detections_is_complete
ON pattern_detections (is_complete);

CREATE INDEX IF NOT EXISTS idx_pattern_detections_instrument_pattern_timestamp
ON pattern_detections (instrument, pattern_type, timestamp);

CREATE INDEX IF NOT EXISTS idx_pattern_detections_complete_validated
ON pattern_detections (is_complete, is_validated);

-- Screener Runs Indexes
CREATE INDEX IF NOT EXISTS idx_screener_runs_run_timestamp
ON screener_runs (run_timestamp);

-- ============================================================================
-- SECTION 3: Table Statistics
--
-- Get table size and row count information
-- ============================================================================

-- For PostgreSQL/TimescaleDB:
-- SELECT
--     schemaname,
--     tablename,
--     pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
--     (SELECT count(*) FROM market_data) as row_count
-- FROM pg_tables
-- WHERE tablename IN ('market_data', 'trading_signals', 'pattern_detections', 'screener_runs');

-- ============================================================================
-- SECTION 4: Index Statistics
--
-- Get information about indexes and their usage
-- ============================================================================

-- For PostgreSQL/TimescaleDB - List all indexes:
-- SELECT
--     schemaname,
--     tablename,
--     indexname,
--     indexdef
-- FROM pg_indexes
-- WHERE tablename IN ('market_data', 'trading_signals', 'pattern_detections', 'screener_runs');

-- For PostgreSQL/TimescaleDB - Index usage statistics:
-- SELECT
--     schemaname,
--     tablename,
--     indexname,
--     idx_scan as index_scans,
--     idx_tup_read as tuples_read,
--     idx_tup_fetch as tuples_fetched
-- FROM pg_stat_user_indexes
-- WHERE tablename IN ('market_data', 'trading_signals', 'pattern_detections', 'screener_runs')
-- ORDER BY idx_scan DESC;

-- ============================================================================
-- SECTION 5: Query Performance Tuning
--
-- Settings to improve query performance
-- ============================================================================

-- For PostgreSQL/TimescaleDB:
-- Adjust these based on your system's capabilities

-- Increase memory available for operations
SET work_mem = '256MB';

-- Enable parallel query execution
SET max_parallel_workers_per_gather = 4;
SET max_parallel_workers = 8;

-- Optimize cost estimates
SET parallel_tuple_cost = 0.01;
SET parallel_setup_cost = 250;

-- Enable JIT compilation (PostgreSQL 11+)
-- SET jit = on;

-- ============================================================================
-- SECTION 6: Unused Index Detection
--
-- Find indexes that are not being used
-- ============================================================================

-- For PostgreSQL/TimescaleDB:
-- SELECT
--     schemaname,
--     tablename,
--     indexname,
--     idx_scan,
--     idx_tup_read,
--     idx_tup_fetch
-- FROM pg_stat_user_indexes
-- WHERE idx_scan = 0
-- AND indexname NOT LIKE 'pg_toast%'
-- ORDER BY tablename, indexname;

-- ============================================================================
-- SECTION 7: Bloat Analysis
--
-- Find tables and indexes with significant bloat
-- ============================================================================

-- For PostgreSQL/TimescaleDB:
-- This query helps identify tables that have excessive wasted space

-- SELECT
--     schemaname,
--     tablename,
--     round(100 * (pg_relation_size(schemaname||'.'||tablename) -
--         pg_relation_size(schemaname||'.'||tablename, 'main')) /
--         pg_relation_size(schemaname||'.'||tablename), 2) as bloat_ratio,
--     pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as size
-- FROM pg_tables
-- WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
-- ORDER BY bloat_ratio DESC;

-- ============================================================================
-- SECTION 8: Data Archive and Cleanup
--
-- Archive old data to separate tables
-- ============================================================================

-- Create archive tables if they don't exist
CREATE TABLE IF NOT EXISTS market_data_archive
(LIKE market_data INCLUDING ALL);

CREATE TABLE IF NOT EXISTS trading_signals_archive
(LIKE trading_signals INCLUDING ALL);

CREATE TABLE IF NOT EXISTS pattern_detections_archive
(LIKE pattern_detections INCLUDING ALL);

-- Archive data older than 90 days (optional - uncomment to use)
-- INSERT INTO market_data_archive
-- SELECT * FROM market_data
-- WHERE timestamp < NOW() - INTERVAL '90 days'
-- ON CONFLICT DO NOTHING;

-- INSERT INTO trading_signals_archive
-- SELECT * FROM trading_signals
-- WHERE timestamp < NOW() - INTERVAL '90 days'
-- ON CONFLICT DO NOTHING;

-- INSERT INTO pattern_detections_archive
-- SELECT * FROM pattern_detections
-- WHERE timestamp < NOW() - INTERVAL '90 days'
-- ON CONFLICT DO NOTHING;

-- Delete archived data from main tables (careful - this is permanent!)
-- DELETE FROM market_data
-- WHERE timestamp < NOW() - INTERVAL '90 days';

-- DELETE FROM trading_signals
-- WHERE timestamp < NOW() - INTERVAL '90 days';

-- DELETE FROM pattern_detections
-- WHERE timestamp < NOW() - INTERVAL '90 days';

-- ============================================================================
-- SECTION 9: Data Retention Setup
--
-- Automatic cleanup of very old data (180+ days)
-- ============================================================================

-- For TimescaleDB: Add retention policies (optional)
-- SELECT add_retention_policy('market_data', INTERVAL '180 days');
-- SELECT add_retention_policy('trading_signals', INTERVAL '180 days');
-- SELECT add_retention_policy('pattern_detections', INTERVAL '180 days');

-- ============================================================================
-- SECTION 10: Connection and Transaction Settings
--
-- Optimal settings for transaction handling
-- ============================================================================

-- Keep temporary files in memory (for sorting/hashing)
-- SET temp_buffers = '32MB';

-- Increase max connections if needed
-- SET max_connections = 200;

-- Optimize for read-heavy workloads
-- SET random_page_cost = 1.1;

-- ============================================================================
-- SECTION 11: Monitoring and Health Checks
--
-- Queries to monitor database health
-- ============================================================================

-- For PostgreSQL/TimescaleDB - Current connections:
-- SELECT
--     datname,
--     count(*) as connections,
--     max(EXTRACT(EPOCH FROM (NOW() - query_start))) as max_query_duration_seconds
-- FROM pg_stat_activity
-- GROUP BY datname;

-- For PostgreSQL/TimescaleDB - Idle transactions:
-- SELECT
--     pid,
--     usename,
--     application_name,
--     state,
--     query,
--     query_start
-- FROM pg_stat_activity
-- WHERE state = 'idle in transaction'
-- ORDER BY query_start;

-- For PostgreSQL/TimescaleDB - Table sizes:
-- SELECT
--     schemaname,
--     tablename,
--     pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
--     pg_size_pretty(pg_relation_size(schemaname||'.'||tablename, 'main')) as table_size,
--     pg_size_pretty(pg_relation_size(schemaname||'.'||tablename, 'fsm')) as fsm_size,
--     pg_size_pretty(pg_relation_size(schemaname||'.'||tablename, 'vm')) as vm_size
-- FROM pg_tables
-- WHERE schemaname = 'public'
-- ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- ============================================================================
-- SECTION 12: TimescaleDB Specific Checks
--
-- Verify TimescaleDB configuration and hypertable setup
-- ============================================================================

-- For TimescaleDB - List hypertables:
-- SELECT * FROM timescaledb_information.hypertables;

-- For TimescaleDB - Check chunk distribution:
-- SELECT
--     hypertable_name,
--     chunk_name,
--     range_start,
--     range_end
-- FROM timescaledb_information.chunks
-- LIMIT 10;

-- For TimescaleDB - Compression statistics:
-- SELECT * FROM timescaledb_information.compression_policies;

-- ============================================================================
-- END OF MAINTENANCE SCRIPT
--
-- After running this script, monitor your database performance and adjust
-- settings based on your specific workload and hardware capabilities.
--
-- Key metrics to monitor:
-- - Query execution time
-- - Index hit ratio (should be > 90%)
-- - Cache hit ratio
-- - Table/index bloat
-- - Lock contention
-- ============================================================================
