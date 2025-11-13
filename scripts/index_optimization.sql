-- ============================================================================
-- Index Optimization Script for ScreenerIII
--
-- Strategies and utilities for optimizing indexes to improve query performance.
--
-- Usage:
--   psql -h localhost -d screeneriii -f index_optimization.sql
-- ============================================================================

-- ============================================================================
-- SECTION 1: Analyze Existing Indexes
--
-- Get detailed information about all indexes
-- ============================================================================

-- List all indexes with their size
-- SELECT
--     t.tablename,
--     i.indexname,
--     pg_size_pretty(pg_relation_size(i.indexrelid)) as index_size,
--     a.idx_scan as scans,
--     a.idx_tup_read as tuples_read,
--     a.idx_tup_fetch as tuples_fetched,
--     CASE
--         WHEN a.idx_scan = 0 THEN 'UNUSED'
--         WHEN a.idx_scan < 10 THEN 'RARELY USED'
--         WHEN a.idx_tup_fetch = 0 THEN 'NOT EFFECTIVE'
--         ELSE 'USEFUL'
--     END as index_status
-- FROM pg_indexes i
-- JOIN pg_tables t ON i.tablename = t.tablename AND i.schemaname = t.schemaname
-- LEFT JOIN pg_stat_user_indexes a ON i.indexname = a.indexname
-- WHERE t.schemaname = 'public'
-- ORDER BY pg_relation_size(i.indexrelid) DESC;

-- ============================================================================
-- SECTION 2: Composite Index Strategy
--
-- Create composite indexes for common multi-column queries
-- ============================================================================

-- Market Data: Composite index for time-series queries
CREATE INDEX IF NOT EXISTS idx_market_data_composite_01
ON market_data (instrument, timeframe, timestamp DESC)
INCLUDE (open, high, low, close, volume);

-- Trading Signals: Composite index for signal filtering
CREATE INDEX IF NOT EXISTS idx_trading_signals_composite_01
ON trading_signals (is_active, instrument, signal_type, timestamp DESC)
INCLUDE (confidence, entry_price);

-- Pattern Detections: Composite index for pattern search
CREATE INDEX IF NOT EXISTS idx_pattern_detections_composite_01
ON pattern_detections (instrument, pattern_type, is_complete, timestamp DESC)
INCLUDE (confidence, breakout_level);

-- ============================================================================
-- SECTION 3: Partial Indexes
--
-- Create indexes on subsets of data (only active/recent records)
-- Reduces index size and improves query performance for common filters
-- ============================================================================

-- Index only active trading signals (much smaller than full index)
CREATE INDEX IF NOT EXISTS idx_trading_signals_active_only
ON trading_signals (instrument, timestamp DESC)
WHERE is_active = true;

-- Index only complete patterns
CREATE INDEX IF NOT EXISTS idx_pattern_detections_complete_only
ON pattern_detections (pattern_type, timestamp DESC)
WHERE is_complete = true;

-- Index recent data (last 30 days)
CREATE INDEX IF NOT EXISTS idx_market_data_recent_only
ON market_data (instrument, timestamp DESC)
WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL '30 days';

-- ============================================================================
-- SECTION 4: Expression-based Indexes
--
-- Index expressions for common query patterns
-- ============================================================================

-- Index by date (useful for daily queries)
CREATE INDEX IF NOT EXISTS idx_market_data_date
ON market_data (DATE(timestamp), instrument);

-- Index by hour (useful for hourly queries)
CREATE INDEX IF NOT EXISTS idx_trading_signals_hour
ON trading_signals (DATE_TRUNC('hour', timestamp), instrument, signal_type);

-- ============================================================================
-- SECTION 5: BRIN Indexes
--
-- Block Range Indexes - efficient for large time-series data
-- Much smaller than B-tree but slightly slower
-- Great for append-only tables sorted by timestamp
-- ============================================================================

-- BRIN index on timestamp (much smaller than B-tree)
CREATE INDEX IF NOT EXISTS idx_market_data_brin_timestamp
ON market_data USING BRIN (timestamp)
WITH (pages_per_range = 128);

-- BRIN on trading signals
CREATE INDEX IF NOT EXISTS idx_trading_signals_brin_timestamp
ON trading_signals USING BRIN (timestamp)
WITH (pages_per_range = 128);

-- ============================================================================
-- SECTION 6: GIN Indexes
--
-- Generalized Inverted Indexes - for JSON data
-- Improves queries on JSON columns
-- ============================================================================

-- Index JSON data in trading signals (indicators field)
CREATE INDEX IF NOT EXISTS idx_trading_signals_gin_indicators
ON trading_signals USING GIN (indicators);

-- Index JSON data in pattern detections
CREATE INDEX IF NOT EXISTS idx_pattern_detections_gin_key_points
ON pattern_detections USING GIN (key_points);

-- ============================================================================
-- SECTION 7: Multi-column Prefix Indexes
--
-- Optimize queries that filter by different column combinations
-- ============================================================================

-- For queries like: instrument, (instrument + timeframe), (instrument + timeframe + timestamp)
CREATE INDEX IF NOT EXISTS idx_market_data_prefix_01
ON market_data (instrument);

CREATE INDEX IF NOT EXISTS idx_market_data_prefix_02
ON market_data (instrument, timeframe);

CREATE INDEX IF NOT EXISTS idx_market_data_prefix_03
ON market_data (instrument, timeframe, timestamp);

-- ============================================================================
-- SECTION 8: Index Maintenance
--
-- Regular maintenance to keep indexes optimized
-- ============================================================================

-- Reindex all indexes (use when indexes become fragmented)
-- REINDEX INDEX CONCURRENTLY idx_market_data_timestamp;
-- REINDEX INDEX CONCURRENTLY idx_trading_signals_timestamp;
-- REINDEX INDEX CONCURRENTLY idx_pattern_detections_timestamp;

-- Analyze all tables (update statistics for query planner)
ANALYZE market_data;
ANALYZE trading_signals;
ANALYZE pattern_detections;
ANALYZE screener_runs;

-- ============================================================================
-- SECTION 9: Index Creation Strategy
--
-- Best practices and recommendations
-- ============================================================================

-- Rule 1: Don't over-index
-- Each index uses disk space and slows down INSERT/UPDATE/DELETE operations
-- Create indexes only for columns frequently used in WHERE, JOIN, or ORDER BY clauses

-- Rule 2: Index selectivity
-- Create indexes on columns with high cardinality (many unique values)
-- Low cardinality columns (like is_active with only 2 values) benefit from partial indexes

-- Rule 3: Column order in composite indexes
-- Put most selective columns first
-- Example: (is_active, instrument) is better than (instrument, is_active)
--   because is_active filters out 90% of rows quickly

-- Rule 4: Covering indexes (INCLUDE clause)
-- Add non-indexed columns to avoid lookups on the main table
-- Only works on B-tree indexes in PostgreSQL 11+

-- Rule 5: Partial indexes
-- Index only rows matching a condition to reduce index size
-- Perfect for "is_active = true" queries on status fields

-- Rule 6: BRIN vs B-tree
-- Use BRIN for very large tables with naturally sorted data
-- BRIN uses 90% less space but may be slightly slower
-- Good for time-series data like market_data

-- ============================================================================
-- SECTION 10: Query Optimization Examples
--
-- Before and after examples of query optimization with indexes
-- ============================================================================

-- QUERY PATTERN 1: Get recent OHLC data
-- Before: Sequential scan of entire market_data table
-- After: Use index on (instrument, timeframe, timestamp DESC)
--
-- SELECT open, high, low, close, volume, timestamp
-- FROM market_data
-- WHERE instrument = 'EUR_USD'
--   AND timeframe = 'M5'
--   AND timestamp > NOW() - INTERVAL '24 hours'
-- ORDER BY timestamp DESC
-- LIMIT 100;

-- QUERY PATTERN 2: Find active buy signals
-- Before: Full scan, then filter
-- After: Use partial index on is_active = true
--
-- SELECT *
-- FROM trading_signals
-- WHERE is_active = true
--   AND signal_type = 'BUY'
--   AND instrument = 'EUR_USD'
-- ORDER BY timestamp DESC;

-- QUERY PATTERN 3: Search completed patterns
-- Before: Scan entire pattern_detections table
-- After: Use partial index on is_complete = true
--
-- SELECT *
-- FROM pattern_detections
-- WHERE is_complete = true
--   AND pattern_type = 'HEAD_AND_SHOULDERS'
-- ORDER BY timestamp DESC;

-- ============================================================================
-- SECTION 11: Index Bloat Detection and Remediation
-- ============================================================================

-- Detect bloated indexes (PostgreSQL)
-- SELECT
--     current_database() as db,
--     schemaname,
--     tablename,
--     ROUND(100.0 * pg_relation_size(indexrelid) /
--         pg_relation_size(relid)) AS index_ratio,
--     pg_size_pretty(pg_relation_size(indexrelid)) as index_size
-- FROM pg_stat_user_indexes
-- WHERE pg_relation_size(relid) > 0
-- ORDER BY pg_relation_size(indexrelid) DESC;

-- Rebuild a bloated index without locking the table
-- REINDEX INDEX CONCURRENTLY idx_name;

-- ============================================================================
-- SECTION 12: MonitoringQueries
-- ============================================================================

-- Find missing indexes (queries that do full table scans)
-- SELECT
--     schemaname,
--     tablename,
--     seq_scan,
--     seq_tup_read,
--     idx_scan,
--     CASE
--         WHEN seq_scan - idx_scan > 0 THEN 'CONSIDER INDEXING'
--         ELSE 'OK'
--     END as suggestion
-- FROM pg_stat_user_tables
-- WHERE seq_scan > 1000
-- ORDER BY seq_scan DESC;

-- Find hot indexes (heavily used)
-- SELECT
--     schemaname,
--     tablename,
--     indexname,
--     idx_scan,
--     idx_tup_fetch,
--     pg_size_pretty(pg_relation_size(indexrelid)) as size
-- FROM pg_stat_user_indexes
-- WHERE idx_scan > 100000
-- ORDER BY idx_scan DESC
-- LIMIT 10;

-- ============================================================================
-- SECTION 13: Index Statistics
-- ============================================================================

-- Get detailed statistics for all indexes
-- SELECT
--     schemaname,
--     tablename,
--     indexname,
--     idx_blks_hit,
--     idx_blks_read,
--     CASE
--         WHEN (idx_blks_hit + idx_blks_read) = 0 THEN 0
--         ELSE ROUND(100.0 * idx_blks_hit / (idx_blks_hit + idx_blks_read), 2)
--     END as cache_hit_ratio
-- FROM pg_statio_user_indexes
-- ORDER BY cache_hit_ratio ASC;

-- ============================================================================
-- SECTION 14: Recommended Indexes Summary
--
-- These indexes are recommended for optimal ScreenerIII performance
-- ============================================================================

-- CRITICAL indexes (high impact on common queries):
-- ✓ market_data (instrument, timeframe, timestamp DESC)
-- ✓ trading_signals (is_active, instrument, timestamp DESC)
-- ✓ pattern_detections (pattern_type, is_complete, timestamp DESC)

-- IMPORTANT indexes (useful for specific queries):
-- ✓ market_data (timestamp DESC) - for time range queries
-- ✓ trading_signals (signal_type) - for signal type filtering
-- ✓ pattern_detections (instrument, pattern_type) - for pattern search

-- OPTIONAL indexes (nice to have, use if space permits):
-- ✓ trading_signals BRIN (timestamp) - space-efficient for large tables
-- ✓ pattern_detections BRIN (timestamp) - space-efficient for large tables

-- ============================================================================
-- END OF INDEX OPTIMIZATION SCRIPT
-- ============================================================================
