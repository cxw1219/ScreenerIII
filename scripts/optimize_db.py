#!/usr/bin/env python3
"""
Database Optimization Script

Standalone script for running database optimizations on ScreenerIII.

Usage:
    python optimize_db.py --help
    python optimize_db.py --optimize
    python optimize_db.py --analyze-query "SELECT * FROM market_data LIMIT 10"
    python optimize_db.py --cleanup-data --days 180
    python optimize_db.py --create-aggregates
    python optimize_db.py --report
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.database import get_db, init_db
from src.core.db_optimization import get_optimizer, DatabaseOptimizer
from src.core.logger import get_logger

logger = get_logger(__name__)


def print_header(title: str) -> None:
    """Print formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_success(message: str) -> None:
    """Print success message."""
    print(f"\u2713 {message}")


def print_error(message: str) -> None:
    """Print error message."""
    print(f"\u2717 {message}")


def print_info(message: str) -> None:
    """Print info message."""
    print(f"  {message}")


def cmd_optimize(optimizer: DatabaseOptimizer, args: argparse.Namespace) -> int:
    """Run full database optimization."""
    print_header("Running Full Database Optimization")

    try:
        results = optimizer.optimize_database(full_optimization=True)

        if 'error' in results:
            print_error(f"Optimization encountered errors: {results['error']}")
            return 1

        print_success("Database optimization completed")

        print("\nOptimization Results:")
        for category, details in results.get('optimizations', {}).items():
            print_info(f"{category}: {json.dumps(details, default=str)}")

        return 0

    except Exception as e:
        print_error(f"Optimization failed: {e}")
        logger.error(f"Optimization error: {e}", exc_info=True)
        return 1


def cmd_analyze_query(optimizer: DatabaseOptimizer, args: argparse.Namespace) -> int:
    """Analyze a query."""
    print_header("Query Analysis")

    try:
        if not args.query:
            print_error("No query provided. Use --analyze-query <sql>")
            return 1

        print(f"Analyzing query:\n{args.query}\n")

        # Get execution plan
        plan = optimizer.query_optimizer.explain_query(args.query)
        print("Execution Plan:")
        print(json.dumps(plan, indent=2, default=str))

        # Performance analysis if requested
        if args.benchmark:
            print("\nBenchmarking query performance...")
            perf = optimizer.query_optimizer.analyze_query_performance(args.query)
            print("Performance Results:")
            print(json.dumps(perf, indent=2, default=str))

        return 0

    except Exception as e:
        print_error(f"Query analysis failed: {e}")
        logger.error(f"Analysis error: {e}", exc_info=True)
        return 1


def cmd_create_indexes(optimizer: DatabaseOptimizer, args: argparse.Namespace) -> int:
    """Create recommended indexes."""
    print_header("Creating Recommended Indexes")

    try:
        suggestions = optimizer.suggest_indexes()

        print(f"Found {len(suggestions)} index suggestions:\n")

        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. Table: {suggestion['table']}")
            print(f"   Columns: {', '.join(suggestion['columns'])}")
            print(f"   Reason: {suggestion['reason']}")

            if not args.skip_create:
                # Create the index
                columns = suggestion['columns']
                table = suggestion['table']
                index_name = f"idx_{table}_{'_'.join(columns[:2])}"

                try:
                    optimizer.index_manager.create_index(
                        table,
                        columns,
                        index_name,
                        if_not_exists=True,
                    )
                    print_success(f"Created index: {index_name}")
                except Exception as e:
                    print_error(f"Failed to create index: {e}")

        print("\nIndex creation completed")
        return 0

    except Exception as e:
        print_error(f"Index creation failed: {e}")
        logger.error(f"Index error: {e}", exc_info=True)
        return 1


def cmd_cleanup_data(optimizer: DatabaseOptimizer, args: argparse.Namespace) -> int:
    """Clean up old data."""
    print_header(f"Cleaning Up Data Older Than {args.days} Days")

    try:
        if not args.force:
            response = input(
                f"\nThis will delete data older than {args.days} days. "
                "Continue? (yes/no): "
            )
            if response.lower() != 'yes':
                print("Cleanup cancelled")
                return 0

        total_deleted = optimizer.cleanup_old_data(days=args.days)
        print_success(f"Cleanup completed. Deleted approximately {total_deleted} records")

        return 0

    except Exception as e:
        print_error(f"Data cleanup failed: {e}")
        logger.error(f"Cleanup error: {e}", exc_info=True)
        return 1


def cmd_create_aggregates(optimizer: DatabaseOptimizer, args: argparse.Namespace) -> int:
    """Create TimescaleDB continuous aggregates."""
    print_header("Creating TimescaleDB Continuous Aggregates")

    if not optimizer.db.is_timescaledb:
        print_error("TimescaleDB is not available in this database")
        return 1

    try:
        print("Creating continuous aggregates...")

        results = optimizer.create_continuous_aggregates()

        if results:
            print_success("Continuous aggregates created successfully")
        else:
            print_error("Failed to create continuous aggregates")

        return 0 if results else 1

    except Exception as e:
        print_error(f"Failed to create aggregates: {e}")
        logger.error(f"Aggregate creation error: {e}", exc_info=True)
        return 1


def cmd_optimize_tables(optimizer: DatabaseOptimizer, args: argparse.Namespace) -> int:
    """Optimize tables with VACUUM/ANALYZE."""
    print_header("Optimizing Tables (VACUUM/ANALYZE)")

    try:
        optimizer.optimize_tables()
        print_success("Table optimization completed")
        return 0

    except Exception as e:
        print_error(f"Table optimization failed: {e}")
        logger.error(f"Optimization error: {e}", exc_info=True)
        return 1


def cmd_report(optimizer: DatabaseOptimizer, args: argparse.Namespace) -> int:
    """Generate optimization report."""
    print_header("Database Optimization Report")

    try:
        report = optimizer.get_optimization_report()

        print("Database Information:")
        print_info(f"Type: {report['database_type']}")
        print_info(f"TimescaleDB: {report['is_timescaledb']}")

        print("\nConnection Pool Recommendations:")
        pool_rec = report['pool_recommendations']
        print_info(f"Recommended pool_size: {pool_rec['pool_size']}")
        print_info(f"Recommended max_overflow: {pool_rec['max_overflow']}")

        print("\nIndex Suggestions:")
        for suggestion in report['index_suggestions']:
            print_info(f"{suggestion['table']}: {', '.join(suggestion['columns'])}")

        print("\nPerformance Metrics:")
        metrics = report['performance_metrics']
        print_info(f"Total Queries: {metrics['total_queries']}")
        print_info(f"Slow Queries: {metrics['slow_query_count']}")

        print("\nCache Statistics:")
        cache = report['cache_stats']
        print_info(f"Cached Entries: {cache['entries']}")
        print_info(f"Cache Size: {cache['total_size_bytes']} bytes")

        if args.json:
            print("\nFull Report (JSON):")
            print(json.dumps(report, indent=2, default=str))

        return 0

    except Exception as e:
        print_error(f"Report generation failed: {e}")
        logger.error(f"Report error: {e}", exc_info=True)
        return 1


def cmd_pool_status(optimizer: DatabaseOptimizer, args: argparse.Namespace) -> int:
    """Show connection pool status."""
    print_header("Connection Pool Status")

    try:
        status = optimizer.pool_tuner.get_pool_status()

        for key, value in status.items():
            print_info(f"{key}: {value}")

        print("\nOptimal Pool Recommendations:")
        recommendations = optimizer.pool_tuner.calculate_optimal_pool_size(
            concurrent_users=args.concurrent_users,
            max_connections=args.max_connections,
        )

        for key, value in recommendations.items():
            print_info(f"{key}: {value}")

        return 0

    except Exception as e:
        print_error(f"Failed to get pool status: {e}")
        logger.error(f"Pool status error: {e}", exc_info=True)
        return 1


def cmd_index_stats(optimizer: DatabaseOptimizer, args: argparse.Namespace) -> int:
    """Show index usage statistics."""
    print_header("Index Usage Statistics")

    try:
        stats = optimizer.index_manager.get_index_usage_stats()

        if not stats:
            print_info("No index statistics available (not using PostgreSQL)")
            return 0

        indexes = stats.get('indexes', [])
        print(f"Found {len(indexes)} indexes:\n")

        for idx in indexes:
            print(f"Index: {idx.get('indexname')}")
            print(f"  Table: {idx.get('tablename')}")
            print(f"  Scans: {idx.get('scans')}")
            print(f"  Tuples Read: {idx.get('tuples_read')}")
            print(f"  Tuples Fetched: {idx.get('tuples_fetched')}\n")

        return 0

    except Exception as e:
        print_error(f"Failed to get index stats: {e}")
        logger.error(f"Index stats error: {e}", exc_info=True)
        return 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ScreenerIII Database Optimization Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --optimize
  %(prog)s --analyze-query "SELECT * FROM market_data WHERE instrument='EUR_USD'"
  %(prog)s --cleanup-data --days 180 --force
  %(prog)s --create-aggregates
  %(prog)s --report --json
  %(prog)s --pool-status --concurrent-users 10
        """,
    )

    # Main commands
    parser.add_argument(
        '--optimize',
        action='store_true',
        help='Run full database optimization',
    )

    parser.add_argument(
        '--analyze-query',
        dest='query',
        type=str,
        help='Analyze a specific query',
    )

    parser.add_argument(
        '--create-indexes',
        action='store_true',
        help='Create recommended indexes',
    )

    parser.add_argument(
        '--cleanup-data',
        action='store_true',
        help='Clean up old data',
    )

    parser.add_argument(
        '--create-aggregates',
        action='store_true',
        help='Create TimescaleDB continuous aggregates',
    )

    parser.add_argument(
        '--optimize-tables',
        action='store_true',
        help='Optimize tables with VACUUM/ANALYZE',
    )

    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate optimization report',
    )

    parser.add_argument(
        '--pool-status',
        action='store_true',
        help='Show connection pool status',
    )

    parser.add_argument(
        '--index-stats',
        action='store_true',
        help='Show index usage statistics',
    )

    # Options
    parser.add_argument(
        '--days',
        type=int,
        default=180,
        help='Days of data to keep when cleaning up (default: 180)',
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompts',
    )

    parser.add_argument(
        '--skip-create',
        action='store_true',
        help='Skip creating indexes (just show suggestions)',
    )

    parser.add_argument(
        '--benchmark',
        action='store_true',
        help='Benchmark query performance',
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output report as JSON',
    )

    parser.add_argument(
        '--concurrent-users',
        type=int,
        default=10,
        help='Expected concurrent users for pool sizing (default: 10)',
    )

    parser.add_argument(
        '--max-connections',
        type=int,
        default=100,
        help='Maximum database connections (default: 100)',
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output',
    )

    args = parser.parse_args()

    # Check if at least one command is specified
    if not any([
        args.optimize,
        args.query,
        args.create_indexes,
        args.cleanup_data,
        args.create_aggregates,
        args.optimize_tables,
        args.report,
        args.pool_status,
        args.index_stats,
    ]):
        parser.print_help()
        return 0

    # Initialize database and optimizer
    try:
        print_header("ScreenerIII Database Optimizer")

        print("Initializing database...")
        db = get_db()

        if not db.test_connection():
            print_error("Failed to connect to database")
            return 1

        print_success("Database connection established")
        print_info(f"Database Type: {db.db_type}")
        print_info(f"TimescaleDB: {db.is_timescaledb}")

        optimizer = get_optimizer(db)

    except Exception as e:
        print_error(f"Failed to initialize database: {e}")
        logger.error(f"Initialization error: {e}", exc_info=True)
        return 1

    # Execute selected command
    try:
        if args.optimize:
            return cmd_optimize(optimizer, args)

        elif args.query:
            return cmd_analyze_query(optimizer, args)

        elif args.create_indexes:
            return cmd_create_indexes(optimizer, args)

        elif args.cleanup_data:
            return cmd_cleanup_data(optimizer, args)

        elif args.create_aggregates:
            return cmd_create_aggregates(optimizer, args)

        elif args.optimize_tables:
            return cmd_optimize_tables(optimizer, args)

        elif args.report:
            return cmd_report(optimizer, args)

        elif args.pool_status:
            return cmd_pool_status(optimizer, args)

        elif args.index_stats:
            return cmd_index_stats(optimizer, args)

        else:
            parser.print_help()
            return 0

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        return 1

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
