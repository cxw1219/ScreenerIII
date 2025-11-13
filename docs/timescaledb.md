# TimescaleDB Documentation for ScreenerIII

## Table of Contents
1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Schema Design](#schema-design)
5. [Data Retention Policies](#data-retention-policies)
6. [Migration from SQLite](#migration-from-sqlite)
7. [Performance Tuning](#performance-tuning)
8. [Backup and Recovery](#backup-and-recovery)
9. [Troubleshooting](#troubleshooting)

---

## Introduction

### What is TimescaleDB?

TimescaleDB is an open-source time-series database built as a PostgreSQL extension. It's specifically optimized for time-series data, making it ideal for applications that need to store and query large volumes of timestamped data efficiently.

### Why TimescaleDB for ScreenerIII?

**Advantages over SQLite for Time-Series Data:**

- **Scalability**: Handle billions of data points without performance degradation
- **Compression**: Automatic compression of old data reduces storage costs by up to 90%
- **Query Performance**: Specialized time-series queries run 100-1000x faster
- **Continuous Aggregates**: Pre-computed aggregations for faster dashboard queries
- **Retention Policies**: Automatic deletion of old data based on configurable policies
- **Distributed Queries**: Option to scale horizontally across multiple servers
- **Real-time Analysis**: Handle high-frequency inserts while maintaining query performance
- **Advanced Indexing**: Time-series specific indexes like BRIN (Block Range Indexes)
- **Multi-node Capabilities**: Replication and high availability options

**Use Case in ScreenerIII:**
ScreenerIII processes large volumes of market data (price, volume, technical indicators) with timestamps. TimescaleDB efficiently handles:
- High-frequency stock market data ingestion
- Complex time-range queries for historical analysis
- Automatic data compression for old records
- Fast aggregations for technical indicators

---

## Installation

### Option 1: Docker Setup (Recommended for Development)

Docker is the easiest way to get started with TimescaleDB locally.

#### Prerequisites
- Docker and Docker Compose installed

#### Docker Compose Configuration

Create `docker-compose.yml` in your project root:

```yaml
version: '3.8'

services:
  timescaledb:
    image: timescale/timescaledb:latest-pg15
    environment:
      POSTGRES_USER: screener_user
      POSTGRES_PASSWORD: secure_password_123
      POSTGRES_DB: screener_db
    ports:
      - "5432:5432"
    volumes:
      - timescaledb_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U screener_user -d screener_db"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  timescaledb_data:
```

#### Running TimescaleDB with Docker

```bash
# Start the container
docker-compose up -d

# Verify it's running
docker-compose ps

# Connect to the database
docker exec -it <container_id> psql -U screener_user -d screener_db

# Check TimescaleDB version
SELECT default_version FROM pg_available_extensions WHERE name = 'timescaledb';
```

#### Stopping the Container

```bash
docker-compose down

# Remove volumes (data)
docker-compose down -v
```

---

### Option 2: Native Installation

#### Linux (Ubuntu/Debian)

```bash
# Add TimescaleDB repository
sudo sh -c "echo 'deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -c -s) main' > /etc/apt/sources.list.d/timescaledb.list"
wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo apt-key add -

# Update and install
sudo apt-get update
sudo apt-get install timescaledb-2-postgresql-15

# Initialize the database
sudo timescaledb-tune --quiet --yes

# Restart PostgreSQL
sudo systemctl restart postgresql
```

#### macOS

```bash
# Using Homebrew
brew install timescaledb

# Start PostgreSQL service
brew services start postgresql

# Initialize database
createdb screener_db
psql screener_db -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
```

#### Windows

1. Download PostgreSQL with TimescaleDB from: https://www.enterprisedb.com/docs/supported-open-source/timescaledb/
2. Run the installer and follow the prompts
3. During installation, select TimescaleDB extension
4. Use pgAdmin or `psql` command line to verify installation

---

### Option 3: Cloud Solutions

#### Timescale Cloud (Recommended)

1. Visit https://console.cloud.timescale.com
2. Sign up for a free trial account
3. Create a new service (PostgreSQL with TimescaleDB)
4. Choose region and resources
5. Copy the connection string from the dashboard
6. Use in your environment variables

**Advantages:**
- Managed service (no maintenance)
- Automatic backups and replication
- High availability options
- Monitoring and alerting included

#### AWS RDS with TimescaleDB

1. Launch RDS PostgreSQL instance (version 14+)
2. Connect via psql or your application
3. Create TimescaleDB extension:

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

4. Configure database parameter group for optimization

#### Other Cloud Options

- **Google Cloud SQL**: Managed PostgreSQL with TimescaleDB
- **Azure Database for PostgreSQL**: Has TimescaleDB available
- **DigitalOcean Managed Databases**: PostgreSQL with TimescaleDB support

---

## Configuration

### Connection String Format

#### Standard PostgreSQL Format

```
postgresql://username:password@host:port/database

# Example
postgresql://screener_user:secure_password_123@localhost:5432/screener_db
```

#### With SSL (Production Recommended)

```
postgresql://username:password@host:port/database?sslmode=require

# Full example with all parameters
postgresql://screener_user:secure_password_123@db.example.com:5432/screener_db?sslmode=require&application_name=screenerIII
```

#### Connection String Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `sslmode` | SSL connection mode | `disable`, `require`, `verify-ca` |
| `connect_timeout` | Connection timeout in seconds | `10` |
| `statement_timeout` | Query timeout in milliseconds | `30000` |
| `application_name` | App identifier | `screenerIII` |

### Environment Variables Setup

Create `.env` file in your project root:

```bash
# Database Configuration
DATABASE_URL=postgresql://screener_user:secure_password_123@localhost:5432/screener_db

# Connection Pool Settings
DB_POOL_MIN=2
DB_POOL_MAX=20
DB_POOL_TIMEOUT=30

# TimescaleDB Specific
TIMESCALEDB_CHUNK_TIME_INTERVAL=7 days

# SSL Configuration (for production)
DB_SSL_MODE=require
DB_SSL_CERT=/path/to/cert.pem
DB_SSL_KEY=/path/to/key.pem

# Logging
DB_LOG_LEVEL=info
```

**Never commit `.env` files to version control. Add to `.gitignore`:**

```
.env
.env.local
.env.*.local
```

### Security Best Practices

#### 1. Strong Password Policy

```sql
-- Set password for database user
ALTER USER screener_user WITH PASSWORD 'strong_random_password_32_chars!';
```

#### 2. Role-Based Access Control

```sql
-- Create application role (limited permissions)
CREATE ROLE screener_app WITH LOGIN PASSWORD 'app_password';

-- Grant specific schema permissions
GRANT USAGE ON SCHEMA public TO screener_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO screener_app;

-- Create read-only role for analytics
CREATE ROLE screener_analytics WITH LOGIN PASSWORD 'analytics_password';
GRANT USAGE ON SCHEMA public TO screener_analytics;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO screener_analytics;
```

#### 3. SSL/TLS Encryption

```bash
# Generate self-signed certificate (development only)
openssl req -x509 -newkey rsa:4096 -keyout server.key -out server.crt -days 365 -nodes

# Copy to PostgreSQL directory
sudo cp server.key /var/lib/postgresql/15/main/
sudo cp server.crt /var/lib/postgresql/15/main/
sudo chmod 600 /var/lib/postgresql/15/main/server.key
sudo chown postgres:postgres /var/lib/postgresql/15/main/server.*

# Enable SSL in postgresql.conf
echo "ssl = on" | sudo tee -a /etc/postgresql/15/main/postgresql.conf
sudo systemctl restart postgresql
```

#### 4. Firewall Rules

```bash
# Allow connections only from application server
sudo ufw allow from 192.168.1.100 to any port 5432
```

#### 5. Connection Pooling with pgBouncer (Production)

```ini
# pgbouncer.ini
[databases]
screener_db = host=localhost port=5432 dbname=screener_db

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
```

---

## Schema Design

### Hypertables Explanation

A **hypertable** is a virtual abstraction layer over a PostgreSQL table that's automatically partitioned by time. It enables efficient time-series operations.

#### Creating a Hypertable

```sql
-- Step 1: Create regular table with time column
CREATE TABLE IF NOT EXISTS stock_prices (
    id BIGSERIAL NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    price NUMERIC(10, 4) NOT NULL,
    volume BIGINT NOT NULL,
    time TIMESTAMPTZ NOT NULL,
    open_price NUMERIC(10, 4),
    high_price NUMERIC(10, 4),
    low_price NUMERIC(10, 4),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Step 2: Convert to hypertable
SELECT create_hypertable('stock_prices', 'time', if_not_exists => TRUE);

-- Step 3: Add indexes for better query performance
CREATE INDEX idx_stock_prices_symbol_time
    ON stock_prices (symbol, time DESC);

CREATE INDEX idx_stock_prices_time_brin
    ON stock_prices USING BRIN (time);
```

#### Example Hypertables for ScreenerIII

```sql
-- Price data hypertable
CREATE TABLE IF NOT EXISTS price_data (
    id BIGSERIAL NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    open_price NUMERIC(10, 4),
    high_price NUMERIC(10, 4),
    low_price NUMERIC(10, 4),
    close_price NUMERIC(10, 4) NOT NULL,
    volume BIGINT NOT NULL,
    adj_close NUMERIC(10, 4),
    time TIMESTAMPTZ NOT NULL,
    exchange VARCHAR(10),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
SELECT create_hypertable('price_data', 'time', if_not_exists => TRUE);

-- Technical indicators hypertable
CREATE TABLE IF NOT EXISTS technical_indicators (
    id BIGSERIAL NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    indicator_type VARCHAR(50) NOT NULL,
    value NUMERIC(12, 6) NOT NULL,
    time TIMESTAMPTZ NOT NULL,
    period INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
SELECT create_hypertable('technical_indicators', 'time', if_not_exists => TRUE);

-- Screener results hypertable
CREATE TABLE IF NOT EXISTS screener_results (
    id BIGSERIAL NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    screener_id UUID NOT NULL,
    matched BOOLEAN NOT NULL,
    score NUMERIC(5, 2),
    time TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
SELECT create_hypertable('screener_results', 'time', if_not_exists => TRUE);
```

### Chunking Strategy

Chunking is how TimescaleDB automatically partitions data. The **chunk time interval** determines the time range for each chunk.

#### Setting Chunk Interval

```sql
-- Get current chunk interval
SELECT interval_length FROM _timescaledb_catalog.dimension
WHERE hypertable_id = (
    SELECT id FROM _timescaledb_catalog.hypertable
    WHERE table_name = 'stock_prices'
);

-- Set custom chunk interval (for new hypertables)
SELECT create_hypertable(
    'stock_prices', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Change chunk interval for existing hypertable
SELECT set_chunk_time_interval('price_data', INTERVAL '1 week');

-- Recommended intervals by data frequency:
-- - High frequency (minute/second data): 1 day
-- - Daily data: 1 week or 1 month
-- - Low frequency: 1 month or 1 quarter
```

#### How to Choose Chunk Interval

| Data Frequency | Recommended Interval | Max Chunk Size |
|---|---|---|
| Tick data (second) | 1 hour | 1-5 GB |
| Minute bars | 1 day | 5-10 GB |
| Hourly bars | 1 week | 5-10 GB |
| Daily/Weekly | 1 month | 1-5 GB |

Optimal chunk size: 1-10 GB per chunk

### Indexes and Optimization

#### BRIN Indexes (Block Range Indexes)

Best for time-ordered data - much smaller than B-tree indexes.

```sql
-- BRIN index on time column (already created, but shown here)
CREATE INDEX idx_stock_prices_time_brin
    ON stock_prices USING BRIN (time);

-- BRIN with custom page range
CREATE INDEX idx_technical_indicators_time_brin
    ON technical_indicators USING BRIN (time)
    WITH (pages_per_range = 128);
```

#### Composite Indexes

```sql
-- Index for common query patterns
CREATE INDEX idx_symbol_time
    ON stock_prices (symbol, time DESC);

-- Index with WHERE clause (partial index)
CREATE INDEX idx_recent_prices
    ON stock_prices (symbol, time DESC)
    WHERE time > NOW() - INTERVAL '90 days';
```

#### Index Usage Queries

```sql
-- Check index sizes
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_indexes
WHERE tablename IN ('stock_prices', 'price_data', 'technical_indicators')
ORDER BY pg_relation_size(indexrelid) DESC;

-- Check unused indexes
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan ASC;
```

#### Query Planning Tips

```sql
-- Analyze query execution plan
EXPLAIN ANALYZE
SELECT * FROM stock_prices
WHERE symbol = 'AAPL'
AND time > NOW() - INTERVAL '30 days'
ORDER BY time DESC;

-- Vacuum and analyze for better query plans
VACUUM ANALYZE stock_prices;

-- Check table statistics
SELECT
    schemaname,
    tablename,
    n_live_tup,
    n_dead_tup,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## Data Retention Policies

### Automatic Data Cleanup

TimescaleDB's `retention_policy` automatically deletes old data based on age.

#### Setting Up Retention Policies

```sql
-- Delete data older than 1 year
SELECT add_retention_policy('stock_prices', INTERVAL '1 year');

-- Delete data older than 2 years for indicators
SELECT add_retention_policy('technical_indicators', INTERVAL '2 years');

-- Delete old screener results after 6 months
SELECT add_retention_policy('screener_results', INTERVAL '6 months');
```

#### Modifying Retention Policies

```sql
-- View existing policies
SELECT * FROM _timescaledb_catalog.continuous_agg;

-- Remove a retention policy
SELECT remove_retention_policy('stock_prices', if_exists => TRUE);

-- Update retention interval
SELECT remove_retention_policy('stock_prices', if_exists => TRUE);
SELECT add_retention_policy('stock_prices', INTERVAL '2 years');
```

#### Recommended Retention Periods by Data Type

| Data Type | Retention Period | Reason |
|---|---|---|
| Price data (full resolution) | 1-2 years | Disk space management |
| Technical indicators | 2-3 years | Historical analysis needs |
| Daily summaries (aggregate) | 5-10 years | Keep aggregated data longer |
| Screener results | 6-12 months | Backtesting reference |
| System logs | 90 days | Compliance and debugging |

### Data Compression

Compression reduces storage by 90%+ for old data (stored as read-only).

#### Enabling Compression

```sql
-- Enable compression on hypertable
ALTER TABLE stock_prices SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'time DESC'
);

-- Set compression policy (compress data older than 7 days)
SELECT add_compression_policy('stock_prices', INTERVAL '7 days');

-- Manually compress older chunks
SELECT compress_chunk(chunk) FROM show_chunks('stock_prices',
    older_than => INTERVAL '7 days'
);
```

#### Compression Configuration

```sql
-- Configure compression settings
ALTER TABLE price_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'time DESC'
);

-- Add compression policy
SELECT add_compression_policy(
    'price_data',
    compress_after => INTERVAL '7 days'
);

-- View compression statistics
SELECT
    chunk_schema,
    chunk_name,
    pg_size_pretty(before_compression_total_bytes) as before,
    pg_size_pretty(after_compression_total_bytes) as after,
    ROUND(100.0 * (1 - after_compression_total_bytes::float /
        before_compression_total_bytes), 2) as compression_ratio
FROM chunk_compression_stats('stock_prices')
ORDER BY chunk_name DESC;
```

#### When to Compress

- **Daily data**: Compress after 7-14 days
- **Minute data**: Compress after 1-3 days
- **Archived data**: Compress data older than 6 months aggressively

---

## Migration from SQLite

### Step 1: Preparation

#### Check SQLite Database Size

```bash
# Get SQLite database size
sqlite3 /path/to/screener.db ".dbinfo"

# Estimated rows
sqlite3 /path/to/screener.db "SELECT COUNT(*) FROM stock_prices;"
```

#### Export Data from SQLite

```bash
# Export schema
sqlite3 /path/to/screener.db ".schema" > schema_export.sql

# Export data as CSV (for specific table)
sqlite3 /path/to/screener.db ".mode csv" \
    ".headers on" \
    ".output prices_data.csv" \
    "SELECT * FROM stock_prices ORDER BY symbol, time;"
```

### Step 2: Create TimescaleDB Schema

```sql
-- Connect to TimescaleDB
psql -U screener_user -d screener_db

-- Create hypertables matching SQLite schema
CREATE TABLE stock_prices (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    price NUMERIC(10, 4) NOT NULL,
    volume BIGINT NOT NULL,
    time TIMESTAMPTZ NOT NULL,
    open_price NUMERIC(10, 4),
    high_price NUMERIC(10, 4),
    low_price NUMERIC(10, 4),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable
SELECT create_hypertable('stock_prices', 'time', if_not_exists => TRUE);

-- Create indexes
CREATE INDEX idx_stock_prices_symbol_time
    ON stock_prices (symbol, time DESC);
CREATE INDEX idx_stock_prices_time_brin
    ON stock_prices USING BRIN (time);
```

### Step 3: Import Data

#### Method A: CSV Import (Recommended for Large Datasets)

```bash
# Export from SQLite to CSV
sqlite3 /path/to/screener.db ".mode csv" \
    ".headers on" \
    ".output stock_prices.csv" \
    "SELECT id, symbol, price, volume, time, open_price, high_price, low_price, created_at FROM stock_prices;"

# Import to TimescaleDB
psql -U screener_user -d screener_db -c "\
    COPY stock_prices (id, symbol, price, volume, time, open_price, high_price, low_price, created_at) \
    FROM STDIN WITH (FORMAT csv, HEADER) \
    " < stock_prices.csv
```

#### Method B: Direct SQL Export/Import

```bash
# Export SQLite data as SQL
sqlite3 /path/to/screener.db << 'EOF' > migration_data.sql
.mode insert stock_prices
SELECT * FROM stock_prices ORDER BY time;
EOF

# Import to TimescaleDB
psql -U screener_user -d screener_db -f migration_data.sql
```

#### Method C: Python Script for Complex Migrations

```python
import sqlite3
import psycopg2
from datetime import datetime
from psycopg2.extras import execute_batch

# Connect to SQLite
sqlite_conn = sqlite3.connect('/path/to/screener.db')
sqlite_cursor = sqlite_conn.cursor()

# Connect to TimescaleDB
ts_conn = psycopg2.connect(
    host='localhost',
    database='screener_db',
    user='screener_user',
    password='password'
)
ts_cursor = ts_conn.cursor()

# Migrate stock_prices table
batch_size = 1000
sqlite_cursor.execute("SELECT * FROM stock_prices")
rows = sqlite_cursor.fetchall()

for i in range(0, len(rows), batch_size):
    batch = rows[i:i+batch_size]

    execute_batch(
        ts_cursor,
        """
        INSERT INTO stock_prices (id, symbol, price, volume, time,
            open_price, high_price, low_price, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        """,
        batch
    )
    ts_conn.commit()
    print(f"Migrated {i + len(batch)} rows")

sqlite_cursor.close()
sqlite_conn.close()
ts_cursor.close()
ts_conn.close()
```

### Step 4: Verification

```sql
-- Count rows to verify migration
SELECT COUNT(*) FROM stock_prices;

-- Check date range
SELECT MIN(time), MAX(time) FROM stock_prices;

-- Verify data integrity
SELECT symbol, COUNT(*) as row_count
FROM stock_prices
GROUP BY symbol
ORDER BY symbol;

-- Check for missing values
SELECT COUNT(*) as null_counts
FROM stock_prices
WHERE price IS NULL
   OR volume IS NULL
   OR time IS NULL;

-- Sample data verification
SELECT * FROM stock_prices
WHERE symbol = 'AAPL'
ORDER BY time DESC
LIMIT 10;
```

### Step 5: Optimization After Migration

```sql
-- Analyze tables for query optimization
ANALYZE stock_prices;

-- Reindex if needed
REINDEX TABLE stock_prices;

-- Vacuum to clean up space
VACUUM ANALYZE stock_prices;

-- Check table statistics
SELECT
    schemaname,
    tablename,
    n_live_tup,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_stat_user_tables
WHERE tablename = 'stock_prices';
```

---

## Performance Tuning

### Continuous Aggregates

Continuous aggregates are pre-computed, automatically updated summaries for faster queries.

#### Creating Continuous Aggregates

```sql
-- Create hourly price aggregate
CREATE MATERIALIZED VIEW price_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket(INTERVAL '1 hour', time) as bucket,
    symbol,
    FIRST(open_price, time) as open_price,
    MAX(high_price) as high_price,
    MIN(low_price) as low_price,
    LAST(close_price, time) as close_price,
    SUM(volume) as total_volume,
    COUNT(*) as tick_count
FROM price_data
GROUP BY bucket, symbol;

-- Create daily price aggregate
CREATE MATERIALIZED VIEW price_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket(INTERVAL '1 day', time) as bucket,
    symbol,
    FIRST(open_price, time) as open_price,
    MAX(high_price) as high_price,
    MIN(low_price) as low_price,
    LAST(close_price, time) as close_price,
    SUM(volume) as total_volume
FROM price_data
GROUP BY bucket, symbol;

-- Create technical indicator averages
CREATE MATERIALIZED VIEW indicator_daily_avg
WITH (timescaledb.continuous) AS
SELECT
    time_bucket(INTERVAL '1 day', time) as bucket,
    symbol,
    indicator_type,
    AVG(value) as avg_value,
    MAX(value) as max_value,
    MIN(value) as min_value
FROM technical_indicators
GROUP BY bucket, symbol, indicator_type;
```

#### Refreshing Continuous Aggregates

```sql
-- Manual refresh (refresh everything)
CALL refresh_continuous_aggregate('price_hourly', NULL, NULL);

-- Refresh specific time range
CALL refresh_continuous_aggregate('price_hourly',
    '2024-11-01'::timestamptz,
    '2024-11-13'::timestamptz);

-- Set automatic refresh policy (refresh hourly view every hour)
SELECT add_continuous_agg_policy('price_hourly',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '0 minutes',
    schedule_interval => INTERVAL '1 hour');
```

#### Query Continuous Aggregates

```sql
-- Query hourly aggregates
SELECT
    bucket,
    symbol,
    open_price,
    high_price,
    low_price,
    close_price,
    total_volume
FROM price_hourly
WHERE symbol = 'AAPL'
AND bucket > NOW() - INTERVAL '7 days'
ORDER BY bucket DESC;

-- Much faster than querying raw data!
-- Compare: SELECT ... FROM price_data WHERE symbol='AAPL' AND time > NOW() - INTERVAL '7 days'
```

### Query Optimization Tips

#### 1. Use Time-Based Predicates

```sql
-- GOOD: Specific time range
SELECT * FROM stock_prices
WHERE symbol = 'AAPL'
AND time > NOW() - INTERVAL '30 days'
ORDER BY time DESC;

-- BAD: No time constraint (scans all chunks)
SELECT * FROM stock_prices
WHERE symbol = 'AAPL'
ORDER BY time DESC;
```

#### 2. Leverage Time Bucketing

```sql
-- Aggregate data efficiently
SELECT
    time_bucket('1 day', time) as day,
    symbol,
    AVG(price) as avg_price,
    COUNT(*) as ticks
FROM stock_prices
WHERE time > NOW() - INTERVAL '1 year'
GROUP BY day, symbol
ORDER BY day DESC, symbol;
```

#### 3. Use Approximate Aggregates

```sql
-- Approximate count (much faster on large tables)
SELECT approximate_row_count(hypertable)
FROM (SELECT 'stock_prices'::regclass as hypertable);

-- Use for sampling
SELECT * FROM stock_prices
WHERE symbol = 'AAPL'
LIMIT (SELECT approximate_row_count('stock_prices') / 1000)
OFFSET random() * approximate_row_count('stock_prices');
```

#### 4. Connection Pooling

```python
# Python example with psycopg2 connection pool
from psycopg2 import pool

connection_pool = pool.SimpleConnectionPool(
    minconn=5,
    maxconn=20,
    host='localhost',
    database='screener_db',
    user='screener_user',
    password='password'
)

# Use connection from pool
conn = connection_pool.getconn()
try:
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM stock_prices")
    result = cursor.fetchone()
finally:
    connection_pool.putconn(conn)
```

### Monitoring and Maintenance

#### Query Performance Monitoring

```sql
-- Enable query logging
ALTER SYSTEM SET log_min_duration_statement = 1000; -- Log queries > 1 second
SELECT pg_reload_conf();

-- Check slow queries
SELECT
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Clear statistics
SELECT pg_stat_statements_reset();
```

#### Table and Index Maintenance

```sql
-- Analyze tables (update statistics)
ANALYZE stock_prices;
ANALYZE price_data;

-- Vacuum (cleanup dead rows)
VACUUM ANALYZE stock_prices;

-- Reindex (rebuild indexes)
REINDEX TABLE stock_prices;

-- Check bloat
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    round(100 * pg_total_relation_size(schemaname||'.'||tablename) /
        pg_total_relation_size('public'), 2) as pct_of_public
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

#### Database Health Check

```sql
-- Check chunk count
SELECT count(*) FROM _timescaledb_catalog.chunk
WHERE hypertable_id = (
    SELECT id FROM _timescaledb_catalog.hypertable
    WHERE table_name = 'stock_prices'
);

-- Check hypertable details
SELECT
    table_name,
    num_chunks,
    num_dimensions,
    compression_enabled
FROM timescaledb_information.hypertables;

-- Monitor space usage
SELECT
    hypertable_name,
    pg_size_pretty(total_bytes) as total_size,
    pg_size_pretty(compressed_bytes) as compressed,
    round(100.0 * compressed_bytes::float / total_bytes, 2) as compression_ratio
FROM hypertable_disk_size
ORDER BY total_bytes DESC;
```

---

## Backup and Recovery

### Backup Strategies

#### Full Database Backup

```bash
# Full backup using pg_dump
pg_dump -U screener_user -h localhost screener_db \
    --verbose \
    --compress=9 \
    --file=screener_db_full_backup.sql.gz

# With format options (more efficient)
pg_dump -U screener_user -h localhost screener_db \
    --format=directory \
    --jobs=4 \
    --verbose \
    --file=screener_db_backup_dir
```

#### Incremental/Continuous Backups

```bash
# Enable WAL archiving in postgresql.conf
wal_level = replica
wal_keep_size = 1GB
archive_mode = on
archive_command = 'cp %p /backup/wal_archive/%f'

# Or for remote backup
archive_command = 'rsync -a %p remote_server:/backup/wal_archive/%f'
```

#### Backup Schedule Script

```bash
#!/bin/bash
# backup_timescaledb.sh

BACKUP_DIR="/backups/timescaledb"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="screener_db"
DB_USER="screener_user"

mkdir -p $BACKUP_DIR

# Full backup weekly
if [ $(date +%w) -eq 0 ]; then
    pg_dump -U $DB_USER $DB_NAME \
        --compress=9 \
        --file=$BACKUP_DIR/full_backup_${DATE}.sql.gz
fi

# Incremental daily
pg_dump -U $DB_USER $DB_NAME \
    --compress=9 \
    --snapshot=self \
    --file=$BACKUP_DIR/incremental_${DATE}.sql.gz

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "incremental_*.sql.gz" -mtime +30 -delete

# Send to remote storage
rsync -av $BACKUP_DIR/ backup_server:/remote/backups/
```

Add to crontab:
```bash
# Run daily at 2 AM
0 2 * * * /usr/local/bin/backup_timescaledb.sh
```

### Point-in-Time Recovery (PITR)

```bash
# Restore to specific point in time
pg_restore -U screener_user -h localhost \
    --create \
    --no-owner \
    --file=/tmp/recovery.sql \
    screener_db_backup.sql.gz

# Then use recovery_target_time in recovery.conf
recovery_target_timeline = 'latest'
recovery_target_time = '2024-11-13 14:30:00'
```

### Disaster Recovery Procedure

#### Step 1: Verify Backup Integrity

```bash
# Test backup restoration to temporary database
pg_restore -d test_screener_db screener_db_backup.sql.gz

# Run sanity checks
psql -d test_screener_db -c "SELECT COUNT(*) FROM stock_prices;"
```

#### Step 2: Restore from Backup

```bash
# Stop the application
systemctl stop screeneriii

# Shutdown PostgreSQL
sudo systemctl stop postgresql

# Remove corrupted data
sudo rm -rf /var/lib/postgresql/15/main/base/

# Restore from backup
pg_restore -U postgres -d screener_db screener_db_backup.sql.gz

# Restart PostgreSQL
sudo systemctl start postgresql

# Verify data
psql -U screener_user -d screener_db -c "SELECT COUNT(*) FROM stock_prices;"

# Restart application
systemctl start screeneriii
```

### Backup Verification

```sql
-- Verify backup data integrity
SELECT
    schemaname,
    tablename,
    n_live_tup,
    last_vacuum,
    last_analyze
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- Check for missing chunks
SELECT
    chunk_schema,
    chunk_name
FROM _timescaledb_catalog.chunk
WHERE hypertable_id = (
    SELECT id FROM _timescaledb_catalog.hypertable
    WHERE table_name = 'stock_prices'
)
ORDER BY chunk_name;
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. High Memory Usage

**Problem:** TimescaleDB using excessive memory

**Solutions:**
```sql
-- Check memory settings
SHOW shared_buffers;
SHOW effective_cache_size;

-- Adjust in postgresql.conf
shared_buffers = 256MB                  # 25% of RAM
effective_cache_size = 1GB              # 50% of RAM
work_mem = 64MB                         # RAM / (max_connections * 2)
maintenance_work_mem = 256MB

-- Restart PostgreSQL
sudo systemctl restart postgresql
```

#### 2. Slow Queries

**Problem:** Queries running slower than expected

**Solutions:**
```sql
-- Check query plan
EXPLAIN ANALYZE
SELECT * FROM stock_prices
WHERE symbol = 'AAPL' AND time > NOW() - INTERVAL '30 days';

-- Ensure proper indexes exist
CREATE INDEX idx_symbol_time ON stock_prices (symbol, time DESC);

-- Analyze table statistics
ANALYZE stock_prices;

-- Consider continuous aggregates
CREATE MATERIALIZED VIEW price_daily WITH (timescaledb.continuous) AS
SELECT time_bucket('1 day', time), symbol, AVG(price)
FROM stock_prices
GROUP BY time_bucket('1 day', time), symbol;
```

#### 3. Connection Pool Exhaustion

**Problem:** "FATAL: remaining connection slots are reserved for non-replication superuser connections"

**Solutions:**
```sql
-- Increase max connections
ALTER SYSTEM SET max_connections = 200;
SELECT pg_reload_conf();

-- Or implement connection pooling with PgBouncer
-- See Configuration section for pgbouncer.ini setup

-- Monitor connections
SELECT
    datname,
    count(*) as connections
FROM pg_stat_activity
GROUP BY datname;
```

#### 4. Chunk Not Found Error

**Problem:** "Error: chunk not found" during queries

**Solutions:**
```sql
-- Verify hypertable structure
SELECT * FROM _timescaledb_catalog.hypertable
WHERE table_name = 'stock_prices';

-- Rebuild hypertable if corrupted
BEGIN;
ALTER TABLE stock_prices RENAME TO stock_prices_old;
SELECT create_hypertable('stock_prices', 'time');
COPY stock_prices FROM stock_prices_old;
DROP TABLE stock_prices_old;
COMMIT;
```

#### 5. Disk Space Issues

**Problem:** "FATAL: remaining connection slots are reserved"

**Solutions:**
```sql
-- Check disk usage
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Enable compression
ALTER TABLE stock_prices SET (timescaledb.compress);
SELECT add_compression_policy('stock_prices', INTERVAL '7 days');

-- Set aggressive retention
SELECT add_retention_policy('stock_prices', INTERVAL '6 months');

-- Drop old chunks manually
SELECT drop_chunks('stock_prices', older_than => INTERVAL '1 year');
```

#### 6. Extension Not Found

**Problem:** "could not open extension control file"

**Solutions:**
```bash
# Reinstall TimescaleDB extension
sudo timescaledb-tune --quiet --yes
sudo systemctl restart postgresql

# Or install via SQL
CREATE EXTENSION IF NOT EXISTS timescaledb WITH SCHEMA public;

# Verify installation
SELECT default_version FROM pg_available_extensions
WHERE name = 'timescaledb';
```

#### 7. Lock Timeout Issues

**Problem:** "ERROR: canceling statement due to lock timeout"

**Solutions:**
```sql
-- Check locks
SELECT
    pid,
    usename,
    application_name,
    state,
    query
FROM pg_stat_activity
WHERE state != 'idle';

-- Increase lock timeout
ALTER SYSTEM SET lock_timeout = '10min';
SELECT pg_reload_conf();

-- Kill long-running queries (use with caution)
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE query_start < NOW() - INTERVAL '1 hour'
AND query NOT LIKE '%pg_stat%';
```

### Getting Help

1. **TimescaleDB Documentation**: https://docs.timescale.com/
2. **PostgreSQL Logs**: `/var/log/postgresql/postgresql.log`
3. **Community Forum**: https://www.timescale.com/community
4. **GitHub Issues**: https://github.com/timescale/timescaledb/issues

### Debug Logging

```sql
-- Enable detailed logging
ALTER SYSTEM SET log_min_duration_statement = 0;
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_duration = on;
SELECT pg_reload_conf();

-- View logs
tail -f /var/log/postgresql/postgresql.log

-- Disable after debugging
ALTER SYSTEM SET log_min_duration_statement = -1;
ALTER SYSTEM SET log_statement = 'none';
SELECT pg_reload_conf();
```

---

## Additional Resources

- **Official Documentation**: https://docs.timescale.com/
- **Installation Guide**: https://docs.timescale.com/getting-started/latest/installation/
- **Schema Design Best Practices**: https://docs.timescale.com/tutorials/latest/
- **Performance Tuning**: https://docs.timescale.com/use-cases/latest/
- **Community Support**: https://www.timescale.com/community

---

**Last Updated**: November 13, 2024
**For ScreenerIII**: Market data analysis and technical screening platform
