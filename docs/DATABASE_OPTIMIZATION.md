# Database Performance Optimization Guide for ScreenerIII

This document provides a comprehensive guide to using ScreenerIII's database performance optimization utilities.

## Table of Contents

1. [Overview](#overview)
2. [Module Architecture](#module-architecture)
3. [Quick Start](#quick-start)
4. [Components](#components)
5. [Usage Examples](#usage-examples)
6. [SQL Scripts](#sql-scripts)
7. [Best Practices](#best-practices)
8. [Performance Tuning](#performance-tuning)
9. [Troubleshooting](#troubleshooting)

## Overview

The database optimization module provides comprehensive tools for:

- **Query Analysis** - Analyze execution plans and performance
- **Index Management** - Create, remove, and analyze indexes
- **TimescaleDB Optimization** - Continuous aggregates, compression, parallel execution
- **Connection Pool Tuning** - Calculate optimal pool sizes
- **Data Archival** - Archive and clean old data
- **Query Caching** - Cache results with TTL-based expiration
- **Performance Metrics** - Track execution times and slow queries

## Module Architecture

### Core Classes

#### `QueryOptimizer`
Analyzes and optimizes database queries.

```python
from src.core.db_optimization import QueryOptimizer

optimizer = QueryOptimizer()

# Get execution plan
plan = optimizer.explain_query("SELECT * FROM market_data WHERE instrument='EUR_USD'")

# Benchmark query performance
perf = optimizer.analyze_query_performance(
    sql="SELECT * FROM market_data LIMIT 100",
    repetitions=5
)

# Get slow queries
slow = optimizer.get_slow_queries(threshold=1.0)  # Queries slower than 1 second
```

#### `IndexManager`
Manages database indexes for optimal performance.

```python
from src.core.db_optimization import IndexManager

index_mgr = IndexManager()

# Create composite index
index_mgr.create_index(
    table_name='market_data',
    columns=['instrument', 'timeframe', 'timestamp'],
    unique=False
)

# Get index information
indexes = index_mgr.get_table_indexes('market_data')

# Analyze table for query planner
index_mgr.analyze_table('market_data')

# Get index usage statistics (PostgreSQL only)
stats = index_mgr.get_index_usage_stats()
```

#### `TimescaleDBOptimizer`
TimescaleDB-specific optimizations.

```python
from src.core.db_optimization import TimescaleDBOptimizer

tsdb_optimizer = TimescaleDBOptimizer()

# Create continuous aggregates
tsdb_optimizer.create_hourly_ohlc_aggregate()
tsdb_optimizer.create_daily_stats_aggregate()

# Optimize chunk sizes
tsdb_optimizer.optimize_chunk_sizes('market_data', chunk_size_ms=604800000)  # 1 week

# Enable parallel execution
tsdb_optimizer.enable_parallel_execution('market_data', max_workers=4)
```

#### `ConnectionPoolTuner`
Optimizes database connection pool settings.

```python
from src.core.db_optimization import ConnectionPoolTuner

pool_tuner = ConnectionPoolTuner()

# Calculate optimal pool size
recommendation = pool_tuner.calculate_optimal_pool_size(
    max_connections=100,
    concurrent_users=10,
    avg_query_time=0.1
)
# Returns: {'pool_size': 5, 'max_overflow': 10, 'recommended_max_connections': 15}

# Get current pool status
status = pool_tuner.get_pool_status()
```

#### `DataArchiver`
Manages data archival and cleanup.

```python
from src.core.db_optimization import DataArchiver

archiver = DataArchiver()

# Create archive table
archiver.create_archive_table('market_data', 'market_data_archive')

# Archive data older than 90 days
archived_count = archiver.archive_old_data(
    table_name='market_data',
    archive_table_name='market_data_archive',
    days_old=90,
    delete_after_archive=True
)

# Clean up very old data
archiver.cleanup_old_data('market_data', retention_days=180)
```

#### `QueryCache`
Simple query result caching.

```python
from src.core.db_optimization import QueryCache

cache = QueryCache(ttl_seconds=3600)  # 1 hour TTL

# Check cache
result = cache.get("SELECT * FROM market_data LIMIT 10")

if result is None:
    # Cache miss - execute query
    result = db.execute_query(...)
    cache.set("SELECT * FROM market_data LIMIT 10", result)

# Invalidate cache
cache.invalidate(pattern='market_data')
cache.invalidate()  # Clear all
```

#### `PerformanceMetrics`
Tracks database performance metrics.

```python
from src.core.db_optimization import PerformanceMetrics

metrics = PerformanceMetrics()

# Record query execution
metrics.record_query('query_hash_123', execution_time=0.05)

# Detect table scans
explain_plan = {...}  # From EXPLAIN output
scans = metrics.detect_table_scans(explain_plan)

# Get metrics summary
summary = metrics.get_metrics_summary()
```

#### `DatabaseOptimizer`
Main orchestrator for all optimizations.

```python
from src.core.db_optimization import get_optimizer

optimizer = get_optimizer()

# Run full optimization
results = optimizer.optimize_database(full_optimization=True)

# Create continuous aggregates
optimizer.create_continuous_aggregates()

# Optimize tables
optimizer.optimize_tables()

# Analyze query
plan = optimizer.analyze_query("SELECT * FROM market_data")

# Get recommendations
suggestions = optimizer.suggest_indexes()

# Clean up old data
deleted = optimizer.cleanup_old_data(days=180)

# Get comprehensive report
report = optimizer.get_optimization_report()
```

## Quick Start

### Installation

The optimization module is part of ScreenerIII. No additional installation needed.

### Basic Usage

```python
from src.core.db_optimization import get_optimizer

# Get optimizer instance
optimizer = get_optimizer()

# Run full optimization
results = optimizer.optimize_database()
print(results)
```

### Using the CLI Script

```bash
# Show help
python scripts/optimize_db.py --help

# Run full optimization
python scripts/optimize_db.py --optimize

# Analyze a specific query
python scripts/optimize_db.py --analyze-query "SELECT * FROM market_data LIMIT 100"

# Benchmark query performance
python scripts/optimize_db.py --analyze-query "SELECT * FROM market_data" --benchmark

# Create recommended indexes
python scripts/optimize_db.py --create-indexes

# Clean up data older than 180 days
python scripts/optimize_db.py --cleanup-data --days 180 --force

# Create TimescaleDB aggregates
python scripts/optimize_db.py --create-aggregates

# Optimize tables (VACUUM/ANALYZE)
python scripts/optimize_db.py --optimize-tables

# Generate optimization report
python scripts/optimize_db.py --report

# Show connection pool status
python scripts/optimize_db.py --pool-status --concurrent-users 10

# Show index usage statistics
python scripts/optimize_db.py --index-stats
```

## Components

### 1. QueryOptimizer

**Purpose**: Analyze and optimize database queries

**Key Methods**:
- `explain_query(sql, analyze=False)` - Get query execution plan
- `analyze_query_performance(sql, repetitions=5)` - Benchmark query
- `track_query_execution(query_hash, execution_time)` - Track execution time
- `get_slow_queries(threshold=1.0)` - Get queries slower than threshold
- `get_query_statistics()` - Get aggregated stats for tracked queries

**Example**:
```python
optimizer = QueryOptimizer()

# Get EXPLAIN plan
plan = optimizer.explain_query(
    "SELECT * FROM market_data WHERE instrument='EUR_USD' LIMIT 100"
)
print(plan['plan'])

# Benchmark query (5 runs)
perf = optimizer.analyze_query_performance(
    sql="SELECT * FROM market_data LIMIT 100",
    repetitions=5,
    warmup=True
)
print(f"Average time: {perf['avg_time']:.4f}s")
print(f"Min/Max: {perf['min_time']:.4f}s / {perf['max_time']:.4f}s")
```

### 2. IndexManager

**Purpose**: Manage database indexes

**Key Methods**:
- `create_index(table, columns, index_name, unique, if_not_exists)` - Create index
- `drop_index(index_name, table_name)` - Drop index
- `get_table_indexes(table_name)` - List indexes on table
- `analyze_table(table_name)` - Run ANALYZE on table
- `get_index_usage_stats()` - Get index usage statistics (PostgreSQL)

**Example**:
```python
index_mgr = IndexManager()

# Create composite index
success = index_mgr.create_index(
    table_name='trading_signals',
    columns=['is_active', 'instrument', 'timestamp'],
    index_name='idx_active_signals',
    unique=False
)

# Analyze table for query planner
index_mgr.analyze_table('trading_signals')

# Get index stats (PostgreSQL only)
stats = index_mgr.get_index_usage_stats()
for idx in stats.get('indexes', []):
    print(f"{idx['indexname']}: {idx['scans']} scans")
```

### 3. TimescaleDBOptimizer

**Purpose**: TimescaleDB-specific optimizations

**Key Methods**:
- `create_continuous_aggregate(...)` - Create continuous aggregate
- `create_hourly_ohlc_aggregate()` - Create hourly OHLC aggregate
- `create_daily_stats_aggregate()` - Create daily stats aggregate
- `optimize_chunk_sizes(table, chunk_size_ms)` - Tune chunk size
- `enable_parallel_execution(table, max_workers)` - Enable parallel queries

**Example**:
```python
tsdb_opt = TimescaleDBOptimizer()

# Create hourly OHLC aggregate
tsdb_opt.create_hourly_ohlc_aggregate()

# Create daily stats aggregate
tsdb_opt.create_daily_stats_aggregate()

# Query the aggregate
# SELECT * FROM market_data_hourly_ohlc
# WHERE time >= NOW() - INTERVAL '24 hours'
# ORDER BY time DESC;
```

### 4. ConnectionPoolTuner

**Purpose**: Optimize connection pool settings

**Key Methods**:
- `calculate_optimal_pool_size(max_connections, concurrent_users, avg_query_time)`
- `get_pool_status()`

**Example**:
```python
pool_tuner = ConnectionPoolTuner()

# Get recommendations for 10 concurrent users
recommendations = pool_tuner.calculate_optimal_pool_size(
    max_connections=100,
    concurrent_users=10,
    avg_query_time=0.1  # 100ms average
)
print(recommendations)
# {'pool_size': 5, 'max_overflow': 10, 'recommended_max_connections': 15}

# Get current pool status
status = pool_tuner.get_pool_status()
```

### 5. DataArchiver

**Purpose**: Archive and clean old data

**Key Methods**:
- `create_archive_table(table_name, archive_table_name)`
- `archive_old_data(table, archive_table, days_old, delete_after_archive)`
- `cleanup_old_data(table, retention_days)`

**Example**:
```python
archiver = DataArchiver()

# Archive data older than 90 days
count = archiver.archive_old_data(
    table_name='market_data',
    archive_table_name='market_data_archive',
    days_old=90,
    delete_after_archive=True
)

# Clean up very old data (180+ days)
archiver.cleanup_old_data('market_data', retention_days=180)
```

### 6. QueryCache

**Purpose**: Cache query results

**Key Methods**:
- `get(query, params)` - Get cached result
- `set(query, result, params)` - Cache result
- `invalidate(pattern)` - Invalidate cache
- `get_stats()` - Get cache statistics

**Example**:
```python
cache = QueryCache(ttl_seconds=3600)

# Check cache
result = cache.get("SELECT * FROM market_data LIMIT 100")

if result is None:
    # Execute query and cache result
    result = session.execute(...).all()
    cache.set("SELECT * FROM market_data LIMIT 100", result)

# Invalidate specific cache entries
cache.invalidate(pattern='market_data')

# Get cache stats
stats = cache.get_stats()
print(f"Cached entries: {stats['entries']}")
```

### 7. PerformanceMetrics

**Purpose**: Track performance metrics

**Key Methods**:
- `record_query(query_hash, execution_time, is_slow)`
- `detect_table_scans(explain_plan)`
- `get_metrics_summary()`

**Example**:
```python
metrics = PerformanceMetrics()

# Record query execution
metrics.record_query('query_123', execution_time=0.05)

# Get summary
summary = metrics.get_metrics_summary()
print(f"Total queries: {summary['total_queries']}")
print(f"Slow queries: {summary['slow_query_count']}")
```

### 8. DatabaseOptimizer

**Purpose**: Main orchestrator for all optimizations

**Key Methods**:
- `optimize_database(full_optimization)` - Run full optimization
- `create_continuous_aggregates()` - Setup TimescaleDB aggregates
- `optimize_tables()` - VACUUM/ANALYZE tables
- `analyze_query(sql)` - Analyze query
- `suggest_indexes()` - Get index suggestions
- `cleanup_old_data(days)` - Clean up old data
- `get_optimization_report()` - Get comprehensive report

**Example**:
```python
from src.core.db_optimization import get_optimizer

optimizer = get_optimizer()

# Run full optimization
results = optimizer.optimize_database()

# Get comprehensive report
report = optimizer.get_optimization_report()
print(f"Database: {report['database_type']}")
print(f"Pool recommendations: {report['pool_recommendations']}")
print(f"Index suggestions: {report['index_suggestions']}")
```

## Usage Examples

### Example 1: Analyze and Optimize a Slow Query

```python
from src.core.db_optimization import QueryOptimizer

optimizer = QueryOptimizer()

# Slow query to analyze
slow_query = """
SELECT m.*, s.signal_type, p.pattern_type
FROM market_data m
LEFT JOIN trading_signals s ON m.instrument = s.instrument
LEFT JOIN pattern_detections p ON m.instrument = p.instrument
WHERE m.timestamp > NOW() - INTERVAL '24 hours'
AND m.instrument = 'EUR_USD'
ORDER BY m.timestamp DESC
"""

# Get execution plan
plan = optimizer.explain_query(slow_query, analyze=True)
print("Execution Plan:")
print(plan['plan'])

# Benchmark performance
perf = optimizer.analyze_query_performance(slow_query, repetitions=5)
print(f"\nPerformance:")
print(f"Average time: {perf['avg_time']:.4f}s")
print(f"Std Dev: {perf['stddev']:.4f}s")

# Recommendation: Create indexes on join columns
# CREATE INDEX idx_market_data_instrument_timestamp
#   ON market_data (instrument, timestamp DESC);
# CREATE INDEX idx_trading_signals_instrument_timestamp
#   ON trading_signals (instrument, timestamp DESC);
```

### Example 2: Create Optimal Indexes

```python
from src.core.db_optimization import IndexManager

index_mgr = IndexManager()

# Create composite indexes for common queries
indexes = [
    {
        'table': 'market_data',
        'columns': ['instrument', 'timeframe', 'timestamp'],
        'name': 'idx_market_composite_01'
    },
    {
        'table': 'trading_signals',
        'columns': ['is_active', 'instrument', 'timestamp'],
        'name': 'idx_signals_active'
    },
    {
        'table': 'pattern_detections',
        'columns': ['pattern_type', 'is_complete', 'timestamp'],
        'name': 'idx_patterns_complete'
    }
]

for idx in indexes:
    success = index_mgr.create_index(
        table_name=idx['table'],
        columns=idx['columns'],
        index_name=idx['name']
    )
    if success:
        print(f"Created: {idx['name']}")

# Analyze tables for query planner
for table in ['market_data', 'trading_signals', 'pattern_detections']:
    index_mgr.analyze_table(table)
```

### Example 3: Setup TimescaleDB Continuous Aggregates

```python
from src.core.db_optimization import TimescaleDBOptimizer

tsdb_opt = TimescaleDBOptimizer()

# Create aggregates
print("Creating continuous aggregates...")
tsdb_opt.create_hourly_ohlc_aggregate()
tsdb_opt.create_daily_stats_aggregate()

# Now you can query the aggregates
# Get last 24 hours of hourly OHLC data:
# SELECT * FROM market_data_hourly_ohlc
# WHERE time >= NOW() - INTERVAL '24 hours'
# AND instrument = 'EUR_USD'
# ORDER BY time DESC;

# This query is much faster because it uses pre-computed aggregate!
```

### Example 4: Clean Up Old Data

```python
from src.core.db_optimization import DataArchiver

archiver = DataArchiver()

# Archive data older than 90 days
print("Archiving data...")
archived = archiver.archive_old_data(
    table_name='market_data',
    archive_table_name='market_data_archive',
    days_old=90,
    delete_after_archive=False  # Keep original
)
print(f"Archived {archived} records")

# Clean up very old data (older than 180 days)
print("Cleaning up old data...")
deleted = archiver.cleanup_old_data(
    table_name='market_data',
    retention_days=180
)
print(f"Deleted old data")
```

### Example 5: Get Optimization Report

```python
from src.core.db_optimization import get_optimizer
import json

optimizer = get_optimizer()

# Get comprehensive report
report = optimizer.get_optimization_report()

print("Database Information:")
print(f"  Type: {report['database_type']}")
print(f"  TimescaleDB: {report['is_timescaledb']}")

print("\nPool Recommendations:")
for key, value in report['pool_recommendations'].items():
    print(f"  {key}: {value}")

print("\nIndex Suggestions:")
for suggestion in report['index_suggestions']:
    print(f"  {suggestion['table']}: {suggestion['columns']}")
    print(f"    Reason: {suggestion['reason']}")

print("\nPerformance Metrics:")
for key, value in report['performance_metrics'].items():
    print(f"  {key}: {value}")

print("\nCache Statistics:")
for key, value in report['cache_stats'].items():
    print(f"  {key}: {value}")
```

## SQL Scripts

### timescaledb_aggregates.sql

Sets up TimescaleDB continuous aggregates for efficient time-series queries.

**Features**:
- Hourly OHLC aggregate from market_data
- Daily statistics aggregate
- Signal volume aggregate
- Pattern detection aggregate
- Automatic refresh policies
- Compression policies
- Parallel execution settings

**Usage**:
```bash
psql -h localhost -d screeneriii -f scripts/timescaledb_aggregates.sql
```

### database_maintenance.sql

General database maintenance and optimization utilities.

**Features**:
- Table optimization (VACUUM, ANALYZE)
- Index creation for common queries
- Table statistics queries
- Index usage statistics
- Query performance tuning
- Data archival setup
- Monitoring queries

**Usage**:
```bash
psql -h localhost -d screeneriii -f scripts/database_maintenance.sql
```

### index_optimization.sql

Index optimization strategies and utilities.

**Features**:
- Composite index creation
- Partial indexes (filtered)
- Expression-based indexes
- BRIN indexes for time-series
- GIN indexes for JSON
- Index bloat detection
- Index maintenance recommendations

**Usage**:
```bash
psql -h localhost -d screeneriii -f scripts/index_optimization.sql
```

## Best Practices

### 1. Index Strategy

- **Create indexes on frequently queried columns** - WHERE, JOIN, ORDER BY
- **Use composite indexes** - (instrument, timestamp) for common filter + sort
- **Consider partial indexes** - Index only active records for status fields
- **Monitor index usage** - Remove unused indexes
- **Avoid over-indexing** - Each index has maintenance cost

### 2. Query Optimization

- **Use appropriate index** - Check EXPLAIN PLAN
- **Filter early** - Apply WHERE clause before JOIN
- **Avoid full table scans** - Use indexes when possible
- **Use LIMIT** - Especially for large result sets
- **Cache repeated queries** - Use QueryCache for frequent queries

### 3. Data Archival

- **Archive old data regularly** - Keep active tables small
- **Compress archived data** - Save storage space
- **Set retention policies** - Automatic cleanup
- **Test backup restoration** - Before deleting data

### 4. Connection Pool

- **Calculate optimal size** - Based on concurrent users
- **Monitor pool usage** - Adjust if needed
- **Set connection timeout** - Prevent stuck connections
- **Use pre-ping** - Detect stale connections

### 5. Performance Monitoring

- **Track slow queries** - Queries > 1 second
- **Monitor table sizes** - Vacuum when bloated
- **Check index usage** - Remove unused indexes
- **Monitor cache hit ratio** - Should be > 90%

## Performance Tuning

### For High-Volume Data

1. **Compress old data**
   ```python
   optimizer = get_optimizer()
   optimizer.timescale_optimizer.add_compression_policy('market_data', '7 days')
   ```

2. **Create continuous aggregates**
   ```python
   optimizer.create_continuous_aggregates()
   ```

3. **Archive old data**
   ```python
   optimizer.archiver.archive_old_data('market_data', 'market_data_archive', days_old=90)
   ```

4. **Create BRIN indexes**
   ```bash
   psql -f scripts/index_optimization.sql
   ```

### For Frequent Queries

1. **Create composite indexes**
   ```python
   index_mgr = IndexManager()
   index_mgr.create_index('market_data', ['instrument', 'timestamp'])
   ```

2. **Use query caching**
   ```python
   cache = QueryCache(ttl_seconds=3600)
   ```

3. **Enable parallel execution**
   ```python
   tsdb_opt = TimescaleDBOptimizer()
   tsdb_opt.enable_parallel_execution('market_data', max_workers=4)
   ```

### For Write-Heavy Workloads

1. **Increase maintenance work memory**
   ```bash
   SET maintenance_work_mem = '1GB';
   ```

2. **Disable unnecessary indexes** during bulk loads
3. **Use BRIN indexes** instead of B-tree for time-series
4. **Batch inserts** in transactions

## Troubleshooting

### Slow Queries

```python
optimizer = QueryOptimizer()

# Get slow queries
slow = optimizer.get_slow_queries(threshold=1.0)

# Analyze top slow query
query = slow[0]['query_hash']
plan = optimizer.explain_query(query, analyze=True)
```

### Missing Indexes

```python
optimizer = get_optimizer()

# Get suggestions
suggestions = optimizer.suggest_indexes()

# Create suggested indexes
for s in suggestions:
    optimizer.index_manager.create_index(s['table'], s['columns'])
```

### High Memory Usage

```python
# Check cache size
cache_stats = optimizer.query_cache.get_stats()

# Clear cache if needed
optimizer.query_cache.invalidate()
```

### Connection Pool Issues

```python
pool_tuner = ConnectionPoolTuner()

# Get recommendations
recommendations = pool_tuner.calculate_optimal_pool_size(
    concurrent_users=20  # Adjust based on actual users
)

# Update config and restart application
```

## Command-Line Tool

The `scripts/optimize_db.py` script provides a command-line interface:

```bash
# Full optimization
python scripts/optimize_db.py --optimize

# Analyze specific query
python scripts/optimize_db.py --analyze-query "SELECT * FROM market_data"

# Create indexes
python scripts/optimize_db.py --create-indexes

# Clean data
python scripts/optimize_db.py --cleanup-data --days 180

# Generate report
python scripts/optimize_db.py --report --json
```

See `--help` for all options.

## Summary

The database optimization module provides comprehensive tools for:

1. **Query Analysis** - Understand query performance
2. **Index Optimization** - Create optimal indexes
3. **TimescaleDB Features** - Leverage time-series optimizations
4. **Connection Tuning** - Optimize resource usage
5. **Data Management** - Archive and clean old data
6. **Performance Monitoring** - Track metrics and identify issues

Use these tools to achieve optimal database performance for your ScreenerIII deployment.
