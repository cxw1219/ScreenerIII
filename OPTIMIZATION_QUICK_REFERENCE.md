# ScreenerIII Database Optimization - Quick Reference

## Command-Line Quick Commands

```bash
# Get help
python scripts/optimize_db.py --help

# Full database optimization
python scripts/optimize_db.py --optimize

# Analyze a query
python scripts/optimize_db.py --analyze-query "SELECT * FROM market_data LIMIT 100"
python scripts/optimize_db.py --analyze-query "SELECT * FROM market_data" --benchmark

# Create recommended indexes
python scripts/optimize_db.py --create-indexes

# View index suggestions without creating
python scripts/optimize_db.py --create-indexes --skip-create

# Clean up old data (180+ days)
python scripts/optimize_db.py --cleanup-data --days 180 --force

# Create TimescaleDB continuous aggregates
python scripts/optimize_db.py --create-aggregates

# Optimize tables (VACUUM/ANALYZE)
python scripts/optimize_db.py --optimize-tables

# Generate optimization report
python scripts/optimize_db.py --report
python scripts/optimize_db.py --report --json

# Connection pool status
python scripts/optimize_db.py --pool-status
python scripts/optimize_db.py --pool-status --concurrent-users 20

# Index usage statistics
python scripts/optimize_db.py --index-stats
```

## Python API Quick Reference

### Import
```python
from src.core.db_optimization import get_optimizer, QueryOptimizer, IndexManager
```

### Get Optimizer
```python
optimizer = get_optimizer()
```

### Query Analysis
```python
# Explain query plan
plan = optimizer.query_optimizer.explain_query("SELECT * FROM market_data")

# Benchmark query
perf = optimizer.query_optimizer.analyze_query_performance(
    "SELECT * FROM market_data LIMIT 100",
    repetitions=5
)

# Get slow queries
slow = optimizer.query_optimizer.get_slow_queries(threshold=1.0)
```

### Index Management
```python
# Create index
optimizer.index_manager.create_index(
    'market_data',
    ['instrument', 'timeframe', 'timestamp']
)

# Get table indexes
indexes = optimizer.index_manager.get_table_indexes('market_data')

# Analyze table
optimizer.index_manager.analyze_table('market_data')

# Get index stats (PostgreSQL)
stats = optimizer.index_manager.get_index_usage_stats()
```

### TimescaleDB Optimization
```python
# Create hourly OHLC aggregate
optimizer.timescale_optimizer.create_hourly_ohlc_aggregate()

# Create daily stats aggregate
optimizer.timescale_optimizer.create_daily_stats_aggregate()

# Enable parallel execution
optimizer.timescale_optimizer.enable_parallel_execution('market_data', max_workers=4)
```

### Connection Pool
```python
# Get recommendations
rec = optimizer.pool_tuner.calculate_optimal_pool_size(
    max_connections=100,
    concurrent_users=10
)

# Get pool status
status = optimizer.pool_tuner.get_pool_status()
```

### Data Archival
```python
# Archive old data
count = optimizer.archiver.archive_old_data(
    'market_data',
    'market_data_archive',
    days_old=90,
    delete_after_archive=True
)

# Clean up very old data
optimizer.archiver.cleanup_old_data('market_data', retention_days=180)
```

### Query Caching
```python
cache = optimizer.query_cache

# Get from cache
result = cache.get("SELECT * FROM market_data")

# Set cache
cache.set("SELECT * FROM market_data", result)

# Invalidate cache
cache.invalidate()  # Clear all
cache.invalidate(pattern='market_data')  # Clear matching
```

### Performance Metrics
```python
# Record query
optimizer.metrics.record_query('hash', 0.05)

# Get summary
summary = optimizer.metrics.get_metrics_summary()
```

### Full Optimization
```python
# Run full optimization
results = optimizer.optimize_database(full_optimization=True)

# Get report
report = optimizer.get_optimization_report()
```

## Common Tasks

### Task 1: Find and Fix Slow Queries
```bash
# 1. Get slow queries
python scripts/optimize_db.py --analyze-query "YOUR_SLOW_QUERY" --benchmark

# 2. Look at execution plan to find bottlenecks
# 3. Create recommended indexes
python scripts/optimize_db.py --create-indexes

# 4. Verify improvement
python scripts/optimize_db.py --analyze-query "YOUR_SLOW_QUERY" --benchmark
```

### Task 2: Setup TimescaleDB for Production
```bash
# 1. Create aggregates
python scripts/optimize_db.py --create-aggregates

# 2. Setup SQL compression
psql -f scripts/timescaledb_aggregates.sql

# 3. Enable parallel execution
python scripts/optimize_db.py --pool-status
```

### Task 3: Archive Old Data
```bash
# 1. Create archive tables
python scripts/optimize_db.py --create-indexes  # Creates archive schema

# 2. Archive 90+ day old data
python scripts/optimize_db.py --cleanup-data --days 90 --force

# 3. Verify and cleanup 180+ day old data
python scripts/optimize_db.py --cleanup-data --days 180 --force
```

### Task 4: Generate Optimization Report
```bash
# Full report
python scripts/optimize_db.py --report

# JSON format
python scripts/optimize_db.py --report --json > optimization_report.json

# Check recommendations
# - Pool size recommendations
# - Index suggestions
# - Performance metrics
# - Cache statistics
```

### Task 5: Optimize All Tables
```bash
# 1. Create indexes
python scripts/optimize_db.py --create-indexes

# 2. Optimize tables
python scripts/optimize_db.py --optimize-tables

# 3. Get statistics
python scripts/optimize_db.py --index-stats
```

## SQL Script Usage

### Setup TimescaleDB
```bash
psql -h localhost -d screeneriii -f scripts/timescaledb_aggregates.sql
```

Result: Continuous aggregates for hourly/daily queries

### General Maintenance
```bash
psql -h localhost -d screeneriii -f scripts/database_maintenance.sql
```

Result: Indexes, statistics, and optimization settings

### Index Optimization
```bash
psql -h localhost -d screeneriii -f scripts/index_optimization.sql
```

Result: Composite, partial, and BRIN indexes

## Performance Improvement Checklist

- [ ] Run optimization report: `python scripts/optimize_db.py --report`
- [ ] Create recommended indexes: `python scripts/optimize_db.py --create-indexes`
- [ ] Optimize tables: `python scripts/optimize_db.py --optimize-tables`
- [ ] Create continuous aggregates: `python scripts/optimize_db.py --create-aggregates`
- [ ] Set pool size recommendations: Check pool-status output
- [ ] Archive old data: `python scripts/optimize_db.py --cleanup-data --days 90`
- [ ] Verify improvements: Re-run report after optimizations

## Monitoring

### Weekly
```bash
# Check slow queries
python scripts/optimize_db.py --analyze-query "SELECT * FROM market_data LIMIT 1000"

# Check index usage
python scripts/optimize_db.py --index-stats

# Get updated report
python scripts/optimize_db.py --report
```

### Monthly
```bash
# Full optimization
python scripts/optimize_db.py --optimize

# Archive old data
python scripts/optimize_db.py --cleanup-data --days 90 --force

# Verify optimization
python scripts/optimize_db.py --report
```

## Troubleshooting

### Query Slow?
```bash
python scripts/optimize_db.py --analyze-query "YOUR_QUERY" --benchmark
# Check execution plan, create indexes if needed
```

### High Memory?
```python
optimizer.query_cache.invalidate()  # Clear cache
```

### Pool Issues?
```bash
python scripts/optimize_db.py --pool-status --concurrent-users 20
# Adjust pool settings based on recommendations
```

### TimescaleDB Not Working?
```bash
# Check if extension is installed
# psql -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
# Then re-run: python scripts/optimize_db.py --create-aggregates
```

## Key Metrics to Monitor

| Metric | Target | How to Check |
|--------|--------|--------------|
| Cache Hit Ratio | >80% | `--report` |
| Slow Query Count | <5 | `--report` |
| Index Hit Ratio | >90% | `--index-stats` |
| Table Bloat | <20% | Monitor table sizes |
| Query Avg Time | <100ms | `--analyze-query` |
| Pool Utilization | 60-80% | `--pool-status` |

## Important Paths

```
Python Modules:
  /home/user/ScreenerIII/src/core/db_optimization.py

CLI Tools:
  /home/user/ScreenerIII/scripts/optimize_db.py

SQL Scripts:
  /home/user/ScreenerIII/scripts/timescaledb_aggregates.sql
  /home/user/ScreenerIII/scripts/database_maintenance.sql
  /home/user/ScreenerIII/scripts/index_optimization.sql

Documentation:
  /home/user/ScreenerIII/docs/DATABASE_OPTIMIZATION.md
  /home/user/ScreenerIII/DATABASE_OPTIMIZATION_SUMMARY.md
  /home/user/ScreenerIII/OPTIMIZATION_QUICK_REFERENCE.md (this file)
```

## Support

For detailed information, see:
- `/home/user/ScreenerIII/docs/DATABASE_OPTIMIZATION.md` - Complete guide
- `/home/user/ScreenerIII/DATABASE_OPTIMIZATION_SUMMARY.md` - Implementation details
- CLI help: `python scripts/optimize_db.py --help`
