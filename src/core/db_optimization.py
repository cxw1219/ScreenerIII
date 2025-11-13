"""
Database Performance Optimization Module

Provides comprehensive database performance optimization utilities for ScreenerIII,
including query analysis, index management, TimescaleDB optimizations,
connection pool tuning, data archival, query caching, and performance metrics.

Features:
- QueryOptimizer: Analyze slow queries and query plans
- IndexManager: Create and manage optimal indexes
- TimescaleDB optimizations: Continuous aggregates, compression, chunk sizing
- ConnectionPoolTuner: Optimize connection pool settings
- DataArchiver: Archive and clean old data
- QueryCache: Result caching with invalidation
- PerformanceMetrics: Track execution times and detect issues
"""

import hashlib
import json
import pickle
import time
from typing import Optional, Dict, Any, List, Tuple, Callable
from datetime import datetime, timedelta
from contextlib import contextmanager
from functools import wraps
from collections import defaultdict
from abc import ABC, abstractmethod

from sqlalchemy import (
    text,
    inspect,
    event,
    Index,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    JSON,
)
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, OperationalError

from .database import (
    Database,
    get_db,
    Base,
    MarketData,
    TradingSignal,
    PatternDetection,
    ScreenerRun,
    DatabaseError,
)
from .logger import get_logger

logger = get_logger(__name__)


class QueryOptimizer:
    """
    Analyzes and optimizes database queries.

    Provides methods to:
    - Analyze query execution plans
    - Identify slow queries
    - Suggest index improvements
    - Track execution times
    """

    def __init__(self, db: Optional[Database] = None):
        """
        Initialize QueryOptimizer.

        Args:
            db: Database instance (uses global instance if not provided)
        """
        self.db = db or get_db()
        self.execution_times: Dict[str, List[float]] = defaultdict(list)
        self.slow_queries: List[Dict[str, Any]] = []

    def explain_query(self, sql: str, analyze: bool = False) -> Dict[str, Any]:
        """
        Analyze query execution plan using EXPLAIN.

        Args:
            sql: SQL query to analyze
            analyze: If True, execute query and show actual costs (PostgreSQL only)

        Returns:
            Dict containing execution plan details

        Raises:
            DatabaseError: If analysis fails
        """
        try:
            with self.db.session_scope() as session:
                if self.db.db_type == 'sqlite':
                    explain_sql = f"EXPLAIN QUERY PLAN {sql}"
                else:  # PostgreSQL / TimescaleDB
                    explain_sql = f"EXPLAIN (FORMAT JSON {'ANALYZE' if analyze else ''}) {sql}"

                result = session.execute(text(explain_sql))

                if self.db.db_type == 'sqlite':
                    return {
                        'plan': [dict(row._mapping) for row in result],
                        'database': 'sqlite',
                    }
                else:
                    plan_data = result.fetchall()
                    if plan_data:
                        return {
                            'plan': json.loads(plan_data[0][0]),
                            'database': 'postgresql',
                        }
                    return {'plan': None, 'database': 'postgresql'}

        except Exception as e:
            logger.error(f"Failed to explain query: {e}")
            raise DatabaseError(f"Query explanation failed: {e}")

    def analyze_query_performance(
        self,
        sql: str,
        repetitions: int = 5,
        warmup: bool = True,
    ) -> Dict[str, Any]:
        """
        Measure actual query performance.

        Args:
            sql: SQL query to analyze
            repetitions: Number of times to execute query
            warmup: If True, run query once before timing

        Returns:
            Dict with performance metrics (min, max, avg, stddev)
        """
        try:
            times: List[float] = []

            with self.db.session_scope() as session:
                # Warmup run
                if warmup:
                    session.execute(text(sql))
                    session.commit()

                # Timed runs
                for _ in range(repetitions):
                    start_time = time.perf_counter()
                    session.execute(text(sql))
                    session.commit()
                    elapsed = time.perf_counter() - start_time
                    times.append(elapsed)

            # Calculate statistics
            import statistics
            return {
                'query_hash': hashlib.md5(sql.encode()).hexdigest()[:8],
                'times': times,
                'min_time': min(times),
                'max_time': max(times),
                'avg_time': statistics.mean(times),
                'stddev': statistics.stdev(times) if len(times) > 1 else 0,
                'total_time': sum(times),
                'repetitions': repetitions,
            }

        except Exception as e:
            logger.error(f"Failed to analyze query performance: {e}")
            raise DatabaseError(f"Performance analysis failed: {e}")

    def track_query_execution(self, query_hash: str, execution_time: float) -> None:
        """
        Track query execution time for monitoring.

        Args:
            query_hash: Hash or identifier of the query
            execution_time: Time taken to execute in seconds
        """
        self.execution_times[query_hash].append(execution_time)

        # Log if query is slow (> 1 second)
        if execution_time > 1.0:
            self.slow_queries.append({
                'query_hash': query_hash,
                'execution_time': execution_time,
                'timestamp': datetime.utcnow(),
            })
            logger.warning(
                f"Slow query detected: {query_hash} took {execution_time:.2f}s"
            )

    def get_slow_queries(self, threshold: float = 1.0) -> List[Dict[str, Any]]:
        """
        Get list of queries slower than threshold.

        Args:
            threshold: Time threshold in seconds

        Returns:
            List of slow query records
        """
        return [q for q in self.slow_queries if q['execution_time'] > threshold]

    def get_query_statistics(self) -> Dict[str, Dict[str, float]]:
        """
        Get aggregated statistics for tracked queries.

        Returns:
            Dict mapping query hash to statistics (min, max, avg, count)
        """
        import statistics

        stats = {}
        for query_hash, times in self.execution_times.items():
            if times:
                stats[query_hash] = {
                    'count': len(times),
                    'min': min(times),
                    'max': max(times),
                    'avg': statistics.mean(times),
                    'total': sum(times),
                }
        return stats


class IndexManager:
    """
    Manages database indexes for optimal query performance.

    Provides methods to:
    - Create composite indexes
    - Suggest missing indexes
    - Remove duplicate indexes
    - Get index usage statistics
    - Rebuild indexes
    """

    def __init__(self, db: Optional[Database] = None):
        """
        Initialize IndexManager.

        Args:
            db: Database instance
        """
        self.db = db or get_db()

    def create_index(
        self,
        table_name: str,
        columns: List[str],
        index_name: Optional[str] = None,
        unique: bool = False,
        if_not_exists: bool = True,
    ) -> bool:
        """
        Create a new index on table.

        Args:
            table_name: Table name
            columns: List of column names
            index_name: Optional custom index name
            unique: If True, create unique index
            if_not_exists: Skip if index already exists

        Returns:
            bool: True if successful

        Raises:
            DatabaseError: If creation fails
        """
        try:
            if not index_name:
                index_name = f"idx_{table_name}_{'_'.join(columns)}"

            # Check if index exists
            if if_not_exists and self._index_exists(table_name, index_name):
                logger.info(f"Index {index_name} already exists")
                return True

            with self.db.session_scope() as session:
                cols_str = ', '.join(columns)
                unique_str = 'UNIQUE ' if unique else ''
                sql = f"CREATE {unique_str}INDEX {index_name} ON {table_name} ({cols_str})"

                session.execute(text(sql))
                logger.info(f"Created index: {index_name} on {table_name}({cols_str})")
                return True

        except Exception as e:
            logger.error(f"Failed to create index {index_name}: {e}")
            raise DatabaseError(f"Index creation failed: {e}")

    def drop_index(self, index_name: str, table_name: Optional[str] = None) -> bool:
        """
        Drop an index.

        Args:
            index_name: Name of index to drop
            table_name: Table name (for SQLite)

        Returns:
            bool: True if successful
        """
        try:
            with self.db.session_scope() as session:
                if self.db.db_type == 'sqlite':
                    sql = f"DROP INDEX IF EXISTS {index_name}"
                else:  # PostgreSQL/TimescaleDB
                    sql = f"DROP INDEX IF EXISTS {index_name} CASCADE"

                session.execute(text(sql))
                logger.info(f"Dropped index: {index_name}")
                return True

        except Exception as e:
            logger.error(f"Failed to drop index {index_name}: {e}")
            return False

    def _index_exists(self, table_name: str, index_name: str) -> bool:
        """
        Check if index exists.

        Args:
            table_name: Table name
            index_name: Index name

        Returns:
            bool: True if index exists
        """
        try:
            with self.db.session_scope() as session:
                if self.db.db_type == 'sqlite':
                    sql = """
                    SELECT name FROM sqlite_master
                    WHERE type='index' AND name=:name AND tbl_name=:table
                    """
                else:  # PostgreSQL/TimescaleDB
                    sql = """
                    SELECT indexname FROM pg_indexes
                    WHERE tablename=:table AND indexname=:name
                    """

                result = session.execute(
                    text(sql),
                    {'name': index_name, 'table': table_name}
                ).scalar()
                return result is not None

        except Exception:
            return False

    def get_table_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get all indexes on a table.

        Args:
            table_name: Table name

        Returns:
            List of index information dicts
        """
        try:
            with self.db.session_scope() as session:
                if self.db.db_type == 'sqlite':
                    sql = """
                    SELECT name, sql FROM sqlite_master
                    WHERE type='index' AND tbl_name=:table
                    """
                    result = session.execute(text(sql), {'table': table_name})
                    return [
                        {'name': row[0], 'definition': row[1]}
                        for row in result
                    ]

                else:  # PostgreSQL/TimescaleDB
                    sql = """
                    SELECT indexname, indexdef FROM pg_indexes
                    WHERE tablename=:table
                    """
                    result = session.execute(text(sql), {'table': table_name})
                    return [
                        {'name': row[0], 'definition': row[1]}
                        for row in result
                    ]

        except Exception as e:
            logger.error(f"Failed to get indexes for {table_name}: {e}")
            return []

    def analyze_table(self, table_name: str) -> bool:
        """
        Run ANALYZE on table for query planner.

        Args:
            table_name: Table name

        Returns:
            bool: True if successful
        """
        try:
            with self.db.session_scope() as session:
                if self.db.db_type == 'sqlite':
                    sql = f"ANALYZE {table_name}"
                else:  # PostgreSQL/TimescaleDB
                    sql = f"ANALYZE {table_name}"

                session.execute(text(sql))
                logger.info(f"Analyzed table: {table_name}")
                return True

        except Exception as e:
            logger.error(f"Failed to analyze table {table_name}: {e}")
            return False

    def get_index_usage_stats(self) -> Dict[str, Any]:
        """
        Get index usage statistics (PostgreSQL only).

        Returns:
            Dict with index usage information
        """
        if self.db.db_type not in ['postgresql', 'timescaledb']:
            logger.info("Index usage stats only available for PostgreSQL")
            return {}

        try:
            with self.db.session_scope() as session:
                sql = """
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan as scans,
                    idx_tup_read as tuples_read,
                    idx_tup_fetch as tuples_fetched
                FROM pg_stat_user_indexes
                ORDER BY idx_scan DESC
                """
                result = session.execute(text(sql))
                return {
                    'indexes': [dict(row._mapping) for row in result]
                }

        except Exception as e:
            logger.error(f"Failed to get index usage stats: {e}")
            return {}


class TimescaleDBOptimizer:
    """
    TimescaleDB-specific optimizations.

    Provides methods to:
    - Create continuous aggregates
    - Configure compression policies
    - Optimize chunk sizes
    - Configure parallel execution
    """

    def __init__(self, db: Optional[Database] = None):
        """
        Initialize TimescaleDBOptimizer.

        Args:
            db: Database instance
        """
        self.db = db or get_db()

    def create_continuous_aggregate(
        self,
        aggregate_name: str,
        materialized_table: str,
        source_table: str,
        bucket_interval: str,
        select_query: str,
        refresh_interval: str = '1 hour',
    ) -> bool:
        """
        Create a continuous aggregate view for time-series data.

        Args:
            aggregate_name: Name of the aggregate view
            materialized_table: Name of materialized table
            source_table: Source hypertable
            bucket_interval: Time bucket interval (e.g., '1 hour')
            select_query: SELECT query for the aggregate
            refresh_interval: Auto-refresh interval

        Returns:
            bool: True if successful
        """
        if not self.db.is_timescaledb:
            logger.warning("TimescaleDB not available, skipping continuous aggregate")
            return False

        try:
            with self.db.session_scope() as session:
                # Create the continuous aggregate
                create_sql = f"""
                CREATE MATERIALIZED VIEW IF NOT EXISTS {aggregate_name}
                WITH (timescaledb.continuous) AS
                {select_query}
                WITH DATA
                """

                session.execute(text(create_sql))

                # Add automatic refresh policy
                refresh_sql = f"""
                SELECT add_continuous_aggregate_policy(
                    '{aggregate_name}',
                    start_offset => INTERVAL '{refresh_interval}',
                    end_offset => INTERVAL '1 hour',
                    schedule_interval => INTERVAL '{refresh_interval}'
                )
                """

                try:
                    session.execute(text(refresh_sql))
                except Exception as e:
                    logger.warning(f"Failed to add refresh policy: {e}")

                logger.info(
                    f"Created continuous aggregate: {aggregate_name} "
                    f"on {source_table} with {bucket_interval} buckets"
                )
                return True

        except Exception as e:
            logger.error(f"Failed to create continuous aggregate: {e}")
            raise DatabaseError(f"Continuous aggregate creation failed: {e}")

    def create_hourly_ohlc_aggregate(self) -> bool:
        """
        Create hourly OHLC continuous aggregate from minute data.

        Returns:
            bool: True if successful
        """
        if not self.db.is_timescaledb:
            return False

        try:
            query = """
            SELECT
                time_bucket('1 hour', timestamp) as time,
                instrument,
                timeframe,
                FIRST(open, timestamp) as open,
                MAX(high) as high,
                MIN(low) as low,
                LAST(close, timestamp) as close,
                SUM(volume) as volume
            FROM market_data
            GROUP BY time_bucket('1 hour', timestamp), instrument, timeframe
            """

            return self.create_continuous_aggregate(
                aggregate_name='market_data_hourly_ohlc',
                materialized_table='market_data_hourly',
                source_table='market_data',
                bucket_interval='1 hour',
                select_query=query,
                refresh_interval='1 hour',
            )

        except Exception as e:
            logger.error(f"Failed to create hourly OHLC aggregate: {e}")
            return False

    def create_daily_stats_aggregate(self) -> bool:
        """
        Create daily statistics continuous aggregate.

        Returns:
            bool: True if successful
        """
        if not self.db.is_timescaledb:
            return False

        try:
            query = """
            SELECT
                time_bucket('1 day', timestamp) as time,
                instrument,
                timeframe,
                FIRST(open, timestamp) as open,
                MAX(high) as high,
                MIN(low) as low,
                LAST(close, timestamp) as close,
                SUM(volume) as volume
            FROM market_data
            GROUP BY time_bucket('1 day', timestamp), instrument, timeframe
            """

            return self.create_continuous_aggregate(
                aggregate_name='market_data_daily_stats',
                materialized_table='market_data_daily',
                source_table='market_data',
                bucket_interval='1 day',
                select_query=query,
                refresh_interval='1 day',
            )

        except Exception as e:
            logger.error(f"Failed to create daily stats aggregate: {e}")
            return False

    def optimize_chunk_sizes(self, table_name: str, chunk_size_ms: int) -> bool:
        """
        Optimize chunk time interval for hypertable.

        Args:
            table_name: Hypertable name
            chunk_size_ms: Chunk interval in milliseconds

        Returns:
            bool: True if successful
        """
        if not self.db.is_timescaledb:
            return False

        try:
            with self.db.session_scope() as session:
                sql = f"""
                SELECT set_chunk_time_interval(
                    '{table_name}'::regclass,
                    INTERVAL '{chunk_size_ms}ms'
                )
                """
                session.execute(text(sql))
                logger.info(f"Set chunk size for {table_name}: {chunk_size_ms}ms")
                return True

        except Exception as e:
            logger.error(f"Failed to optimize chunk size: {e}")
            return False

    def enable_parallel_execution(self, table_name: str, max_workers: int = 4) -> bool:
        """
        Enable parallel query execution for hypertable.

        Args:
            table_name: Hypertable name
            max_workers: Maximum worker threads

        Returns:
            bool: True if successful
        """
        if not self.db.is_timescaledb:
            return False

        try:
            with self.db.session_scope() as session:
                # Set max parallel workers
                sql = f"SET max_parallel_workers_per_gather = {max_workers}"
                session.execute(text(sql))
                logger.info(f"Enabled parallel execution for {table_name}")
                return True

        except Exception as e:
            logger.error(f"Failed to enable parallel execution: {e}")
            return False


class ConnectionPoolTuner:
    """
    Optimizes database connection pool settings.

    Calculates optimal pool size based on workload and provides tuning utilities.
    """

    def __init__(self, db: Optional[Database] = None):
        """
        Initialize ConnectionPoolTuner.

        Args:
            db: Database instance
        """
        self.db = db or get_db()

    def calculate_optimal_pool_size(
        self,
        max_connections: int = 100,
        concurrent_users: int = 10,
        avg_query_time: float = 0.1,
    ) -> Dict[str, int]:
        """
        Calculate optimal connection pool size based on workload.

        Args:
            max_connections: Maximum connections allowed by database
            concurrent_users: Expected concurrent users
            avg_query_time: Average query execution time in seconds

        Returns:
            Dict with recommended pool_size and max_overflow
        """
        # Formula: pool_size = (concurrent_users * avg_query_time) + buffer
        # max_overflow allows temporary extra connections
        buffer = 2
        pool_size = max(5, int(concurrent_users * avg_query_time) + buffer)
        max_overflow = max(10, max_connections - pool_size)

        return {
            'pool_size': min(pool_size, max_connections // 2),
            'max_overflow': min(max_overflow, max_connections // 2),
            'recommended_max_connections': pool_size + max_overflow,
        }

    def get_pool_status(self) -> Dict[str, Any]:
        """
        Get current connection pool status.

        Returns:
            Dict with pool statistics
        """
        if self.db.db_type == 'sqlite':
            return {'message': 'Connection pooling not applicable for SQLite'}

        try:
            engine = self.db.engine
            pool = engine.pool

            return {
                'pool_size': pool.size() if hasattr(pool, 'size') else 'N/A',
                'checked_out': pool.checkedout() if hasattr(pool, 'checkedout') else 'N/A',
                'available': pool.checkedout() if hasattr(pool, 'checkedout') else 'N/A',
                'overflow': pool.overflow() if hasattr(pool, 'overflow') else 'N/A',
            }

        except Exception as e:
            logger.error(f"Failed to get pool status: {e}")
            return {'error': str(e)}


class DataArchiver:
    """
    Manages data archival and cleanup.

    Provides methods to:
    - Archive old data
    - Compress archived data
    - Clean up very old data
    - Move data to secondary storage
    """

    def __init__(self, db: Optional[Database] = None):
        """
        Initialize DataArchiver.

        Args:
            db: Database instance
        """
        self.db = db or get_db()

    def create_archive_table(self, table_name: str, archive_table_name: str) -> bool:
        """
        Create an archive table for storing old data.

        Args:
            table_name: Source table name
            archive_table_name: Archive table name

        Returns:
            bool: True if successful
        """
        try:
            with self.db.session_scope() as session:
                # Create archive table with same schema
                sql = f"""
                CREATE TABLE IF NOT EXISTS {archive_table_name}
                (LIKE {table_name} INCLUDING ALL)
                """
                session.execute(text(sql))
                logger.info(f"Created archive table: {archive_table_name}")
                return True

        except Exception as e:
            logger.error(f"Failed to create archive table: {e}")
            return False

    def archive_old_data(
        self,
        table_name: str,
        archive_table_name: str,
        days_old: int = 90,
        delete_after_archive: bool = False,
    ) -> int:
        """
        Move data older than specified days to archive table.

        Args:
            table_name: Source table name
            archive_table_name: Archive table name
            days_old: Archive data older than this many days
            delete_after_archive: Delete data after archiving

        Returns:
            int: Number of records archived

        Raises:
            DatabaseError: If archival fails
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            with self.db.session_scope() as session:
                # Move data to archive
                move_sql = f"""
                INSERT INTO {archive_table_name}
                SELECT * FROM {table_name}
                WHERE timestamp < :cutoff_date
                """
                session.execute(text(move_sql), {'cutoff_date': cutoff_date})
                affected = session.connection().execute(
                    text("SELECT CHANGES() as count")
                ).scalar()

                # Delete from original table if requested
                if delete_after_archive:
                    delete_sql = f"""
                    DELETE FROM {table_name}
                    WHERE timestamp < :cutoff_date
                    """
                    session.execute(text(delete_sql), {'cutoff_date': cutoff_date})

                logger.info(
                    f"Archived {affected} records from {table_name} "
                    f"older than {days_old} days"
                )
                return affected or 0

        except Exception as e:
            logger.error(f"Failed to archive data: {e}")
            raise DatabaseError(f"Data archival failed: {e}")

    def cleanup_old_data(
        self,
        table_name: str,
        retention_days: int = 180,
    ) -> int:
        """
        Permanently delete very old data.

        Args:
            table_name: Table name
            retention_days: Keep data newer than this many days

        Returns:
            int: Number of records deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

            with self.db.session_scope() as session:
                delete_sql = f"""
                DELETE FROM {table_name}
                WHERE timestamp < :cutoff_date
                """
                session.execute(text(delete_sql), {'cutoff_date': cutoff_date})

                logger.info(
                    f"Cleaned up {table_name}: deleted data older than {retention_days} days"
                )
                return 0  # SQLite/PostgreSQL don't easily return affected rows

        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            raise DatabaseError(f"Data cleanup failed: {e}")


class QueryCache:
    """
    Simple query result caching with invalidation.

    Caches query results in memory with optional TTL-based expiration.
    """

    def __init__(self, ttl_seconds: int = 3600):
        """
        Initialize QueryCache.

        Args:
            ttl_seconds: Time-to-live for cached results in seconds
        """
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.ttl_seconds = ttl_seconds

    def _get_cache_key(self, query: str, params: Dict[str, Any]) -> str:
        """
        Generate cache key from query and parameters.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            str: Cache key
        """
        cache_str = f"{query}:{json.dumps(params, sort_keys=True, default=str)}"
        return hashlib.md5(cache_str.encode()).hexdigest()

    def get(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        Get cached result if available and not expired.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Cached result or None if expired/not found
        """
        if params is None:
            params = {}

        cache_key = self._get_cache_key(query, params)

        if cache_key in self.cache:
            result, timestamp = self.cache[cache_key]

            # Check if expired
            if time.time() - timestamp < self.ttl_seconds:
                logger.debug(f"Cache hit for key: {cache_key}")
                return result

            # Remove expired entry
            del self.cache[cache_key]

        return None

    def set(self, query: str, result: Any, params: Optional[Dict[str, Any]] = None) -> None:
        """
        Cache a query result.

        Args:
            query: SQL query
            result: Result to cache
            params: Query parameters
        """
        if params is None:
            params = {}

        cache_key = self._get_cache_key(query, params)
        self.cache[cache_key] = (result, time.time())
        logger.debug(f"Cached result for key: {cache_key}")

    def invalidate(self, pattern: Optional[str] = None) -> int:
        """
        Invalidate cache entries.

        Args:
            pattern: Optional pattern to match cache keys (None = clear all)

        Returns:
            int: Number of entries invalidated
        """
        if pattern is None:
            count = len(self.cache)
            self.cache.clear()
            logger.info(f"Cleared all cache entries ({count} total)")
            return count

        count = 0
        keys_to_remove = [k for k in self.cache if pattern in k]
        for key in keys_to_remove:
            del self.cache[key]
            count += 1

        logger.info(f"Invalidated {count} cache entries matching pattern: {pattern}")
        return count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache size and entry count
        """
        total_size = sum(
            len(pickle.dumps(result)) for result, _ in self.cache.values()
        )

        return {
            'entries': len(self.cache),
            'total_size_bytes': total_size,
            'ttl_seconds': self.ttl_seconds,
        }


class PerformanceMetrics:
    """
    Tracks database performance metrics.

    Monitors:
    - Query execution times
    - Slow query detection
    - Table scans
    - Lock contention
    """

    def __init__(self):
        """Initialize PerformanceMetrics."""
        self.metrics: Dict[str, Any] = {
            'total_queries': 0,
            'slow_queries': [],
            'table_scans': [],
            'locks': [],
        }
        self.slow_query_threshold = 1.0  # seconds

    def record_query(
        self,
        query_hash: str,
        execution_time: float,
        is_slow: bool = False,
    ) -> None:
        """
        Record a query execution.

        Args:
            query_hash: Query identifier hash
            execution_time: Time taken in seconds
            is_slow: Whether query is considered slow
        """
        self.metrics['total_queries'] += 1

        if execution_time > self.slow_query_threshold or is_slow:
            self.metrics['slow_queries'].append({
                'query_hash': query_hash,
                'execution_time': execution_time,
                'timestamp': datetime.utcnow().isoformat(),
            })

    def detect_table_scans(self, explain_plan: Dict[str, Any]) -> List[str]:
        """
        Detect full table scans in query plan.

        Args:
            explain_plan: Query execution plan from EXPLAIN

        Returns:
            List of scan types detected
        """
        scans = []

        def traverse_plan(node: Dict[str, Any]) -> None:
            if 'Node Type' in node:
                if 'Scan' in node['Node Type']:
                    scans.append(node['Node Type'])
            if 'Plans' in node:
                for child in node['Plans']:
                    traverse_plan(child)

        if explain_plan and isinstance(explain_plan, dict):
            traverse_plan(explain_plan)

        return scans

    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get summary of collected metrics.

        Returns:
            Dict with metrics summary
        """
        return {
            'total_queries': self.metrics['total_queries'],
            'slow_query_count': len(self.metrics['slow_queries']),
            'slow_queries': self.metrics['slow_queries'][-10:],  # Last 10
            'slow_query_threshold': self.slow_query_threshold,
        }


class DatabaseOptimizer:
    """
    Main orchestrator for database optimizations.

    Combines all optimization utilities and provides high-level optimization methods.
    """

    def __init__(self, db: Optional[Database] = None):
        """
        Initialize DatabaseOptimizer.

        Args:
            db: Database instance
        """
        self.db = db or get_db()
        self.query_optimizer = QueryOptimizer(db)
        self.index_manager = IndexManager(db)
        self.timescale_optimizer = TimescaleDBOptimizer(db)
        self.pool_tuner = ConnectionPoolTuner(db)
        self.archiver = DataArchiver(db)
        self.query_cache = QueryCache()
        self.metrics = PerformanceMetrics()

    def optimize_database(self, full_optimization: bool = True) -> Dict[str, Any]:
        """
        Run comprehensive database optimization.

        Args:
            full_optimization: If True, run all optimization steps

        Returns:
            Dict with optimization results
        """
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'optimizations': {},
        }

        try:
            # 1. Analyze and optimize tables
            results['optimizations']['tables'] = self._optimize_tables()

            # 2. Create recommended indexes
            results['optimizations']['indexes'] = self._optimize_indexes()

            # 3. Setup TimescaleDB features if available
            if self.db.is_timescaledb:
                results['optimizations']['timescaledb'] = self._setup_timescaledb()

            # 4. Get performance metrics
            results['optimizations']['performance'] = self.metrics.get_metrics_summary()

            logger.info("Database optimization completed successfully")

        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            results['error'] = str(e)

        return results

    def _optimize_tables(self) -> Dict[str, bool]:
        """Optimize tables with VACUUM/ANALYZE."""
        results = {}

        if self.db.db_type == 'sqlite':
            try:
                with self.db.session_scope() as session:
                    session.execute(text("VACUUM"))
                    logger.info("Executed VACUUM on SQLite database")
                results['vacuum'] = True
            except Exception as e:
                logger.error(f"VACUUM failed: {e}")
                results['vacuum'] = False

        elif self.db.is_timescaledb:
            try:
                with self.db.engine.connect() as conn:
                    conn.execution_options(isolation_level="AUTOCOMMIT")
                    conn.execute(text("VACUUM ANALYZE"))
                logger.info("Executed VACUUM ANALYZE on PostgreSQL")
                results['vacuum_analyze'] = True
            except Exception as e:
                logger.error(f"VACUUM ANALYZE failed: {e}")
                results['vacuum_analyze'] = False

        return results

    def _optimize_indexes(self) -> Dict[str, Any]:
        """Create and optimize indexes."""
        results = {}

        try:
            # Analyze all main tables
            for table_name in ['market_data', 'trading_signals', 'pattern_detections']:
                if self.index_manager.analyze_table(table_name):
                    results[f'analyze_{table_name}'] = True

            # Get index stats
            results['index_stats'] = self.index_manager.get_index_usage_stats()

        except Exception as e:
            logger.error(f"Index optimization failed: {e}")

        return results

    def _setup_timescaledb(self) -> Dict[str, bool]:
        """Setup TimescaleDB continuous aggregates and compression."""
        results = {}

        try:
            # Create continuous aggregates
            results['hourly_ohlc'] = self.timescale_optimizer.create_hourly_ohlc_aggregate()
            results['daily_stats'] = self.timescale_optimizer.create_daily_stats_aggregate()

            # Enable parallel execution
            results['parallel_execution'] = self.timescale_optimizer.enable_parallel_execution(
                'market_data'
            )

        except Exception as e:
            logger.error(f"TimescaleDB optimization failed: {e}")

        return results

    def create_continuous_aggregates(self) -> bool:
        """
        Setup TimescaleDB continuous aggregates for common queries.

        Returns:
            bool: True if successful
        """
        if not self.db.is_timescaledb:
            logger.warning("TimescaleDB not available")
            return False

        try:
            logger.info("Creating continuous aggregates...")
            self.timescale_optimizer.create_hourly_ohlc_aggregate()
            self.timescale_optimizer.create_daily_stats_aggregate()
            return True

        except Exception as e:
            logger.error(f"Failed to create continuous aggregates: {e}")
            return False

    def optimize_tables(self) -> bool:
        """
        Optimize tables with VACUUM, ANALYZE, REINDEX.

        Returns:
            bool: True if successful
        """
        return bool(self._optimize_tables())

    def analyze_query(self, sql: str) -> Dict[str, Any]:
        """
        Analyze query execution plan.

        Args:
            sql: SQL query

        Returns:
            Dict with execution plan details
        """
        return self.query_optimizer.explain_query(sql)

    def suggest_indexes(self) -> List[Dict[str, Any]]:
        """
        Suggest missing indexes for common query patterns.

        Returns:
            List of index suggestions
        """
        suggestions = [
            {
                'table': 'market_data',
                'columns': ['instrument', 'timeframe', 'timestamp'],
                'reason': 'Composite query optimization',
            },
            {
                'table': 'trading_signals',
                'columns': ['is_active', 'instrument', 'timestamp'],
                'reason': 'Common filter and sorting',
            },
            {
                'table': 'pattern_detections',
                'columns': ['pattern_type', 'is_complete', 'timestamp'],
                'reason': 'Pattern search optimization',
            },
        ]

        return suggestions

    def cleanup_old_data(self, days: int = 180) -> int:
        """
        Clean up data older than specified days.

        Args:
            days: Delete data older than this many days

        Returns:
            int: Number of records deleted (approximate)
        """
        try:
            total = 0

            for table_name in ['market_data', 'trading_signals', 'pattern_detections']:
                try:
                    count = self.archiver.cleanup_old_data(table_name, days)
                    total += count
                except Exception as e:
                    logger.warning(f"Failed to cleanup {table_name}: {e}")

            return total

        except Exception as e:
            logger.error(f"Data cleanup failed: {e}")
            return 0

    def get_optimization_report(self) -> Dict[str, Any]:
        """
        Get comprehensive optimization report.

        Returns:
            Dict with optimization recommendations and status
        """
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'database_type': self.db.db_type,
            'is_timescaledb': self.db.is_timescaledb,
            'pool_recommendations': self.pool_tuner.calculate_optimal_pool_size(),
            'index_suggestions': self.suggest_indexes(),
            'query_statistics': self.query_optimizer.get_query_statistics(),
            'performance_metrics': self.metrics.get_metrics_summary(),
            'cache_stats': self.query_cache.get_stats(),
        }


# Global optimizer instance
_optimizer: Optional[DatabaseOptimizer] = None


def get_optimizer(db: Optional[Database] = None) -> DatabaseOptimizer:
    """
    Get or create global DatabaseOptimizer instance.

    Args:
        db: Database instance (uses global if not provided)

    Returns:
        DatabaseOptimizer: Global optimizer instance
    """
    global _optimizer
    if _optimizer is None:
        _optimizer = DatabaseOptimizer(db)
    return _optimizer


if __name__ == '__main__':
    # Example usage
    try:
        optimizer = get_optimizer()

        print("Database Optimization Report")
        print("=" * 60)

        # Run optimization
        results = optimizer.optimize_database()
        print(f"\nOptimization Results: {json.dumps(results, indent=2, default=str)}")

        # Get recommendations
        report = optimizer.get_optimization_report()
        print(f"\nOptimization Report: {json.dumps(report, indent=2, default=str)}")

    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        print(f"Error: {e}")
