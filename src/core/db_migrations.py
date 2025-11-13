"""
Database Migration Module

This module provides utilities for managing database migrations,
including SQLite to TimescaleDB migration, schema versioning,
and TimescaleDB hypertable setup.
"""

import time
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from contextlib import contextmanager

from sqlalchemy import (
    create_engine,
    text,
    MetaData,
    Table,
    Column,
    Integer,
    String,
    DateTime,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError

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


class MigrationError(Exception):
    """Custom exception for migration-related errors."""
    pass


class SchemaVersion(Base):
    """
    Model for tracking database schema versions.

    This table stores the version history of database schema changes.
    """

    __tablename__ = 'schema_versions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(20), nullable=False, unique=True)
    description = Column(String(200), nullable=True)
    applied_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    applied_by = Column(String(100), default='system', nullable=False)

    def __repr__(self) -> str:
        return f"<SchemaVersion(version={self.version}, applied_at={self.applied_at})>"


class DatabaseMigrator:
    """
    Database migration manager for ScreenerIII.

    Handles:
    - Schema version management
    - SQLite to TimescaleDB migration
    - TimescaleDB hypertable setup
    - Data integrity verification
    """

    # Current schema version
    CURRENT_VERSION = "1.0.0"

    def __init__(self, db: Optional[Database] = None):
        """
        Initialize the database migrator.

        Args:
            db: Database instance (uses global instance if not provided)
        """
        self.db = db or get_db()

    def ensure_schema_version_table(self) -> None:
        """
        Ensure the schema_versions table exists.

        This table is used to track database migrations.
        """
        try:
            SchemaVersion.__table__.create(self.db.engine, checkfirst=True)
            logger.info("Schema version table ready")
        except Exception as e:
            logger.error(f"Failed to create schema version table: {e}")
            raise MigrationError(f"Schema version table creation failed: {e}")

    def get_current_version(self) -> Optional[str]:
        """
        Get the current schema version from the database.

        Returns:
            Optional[str]: Current version or None if no version recorded
        """
        try:
            self.ensure_schema_version_table()

            with self.db.session_scope() as session:
                result = (
                    session.query(SchemaVersion)
                    .order_by(SchemaVersion.applied_at.desc())
                    .first()
                )

                if result:
                    return result.version
                return None

        except Exception as e:
            logger.error(f"Failed to get current schema version: {e}")
            return None

    def record_version(
        self,
        version: str,
        description: str = "",
        applied_by: str = "system",
    ) -> None:
        """
        Record a schema version in the database.

        Args:
            version: Version string (e.g., "1.0.0")
            description: Description of the changes
            applied_by: Name of the entity applying the migration

        Raises:
            MigrationError: If version recording fails
        """
        try:
            self.ensure_schema_version_table()

            with self.db.session_scope() as session:
                schema_version = SchemaVersion(
                    version=version,
                    description=description,
                    applied_by=applied_by,
                )
                session.add(schema_version)

            logger.info(f"Recorded schema version: {version}")

        except Exception as e:
            logger.error(f"Failed to record schema version: {e}")
            raise MigrationError(f"Version recording failed: {e}")

    def setup_timescaledb(
        self,
        chunk_intervals: Optional[Dict[str, str]] = None,
        compression_after: str = "7 days",
        retention_period: Optional[str] = None,
    ) -> bool:
        """
        Setup TimescaleDB hypertables and policies.

        Args:
            chunk_intervals: Custom chunk intervals per table
            compression_after: Compress data older than this
            retention_period: Optional retention period (e.g., "90 days")

        Returns:
            bool: True if successful

        Raises:
            MigrationError: If setup fails
        """
        if not self.db.is_timescaledb:
            logger.warning("TimescaleDB not available, skipping setup")
            return False

        try:
            # Default chunk intervals
            if chunk_intervals is None:
                chunk_intervals = {
                    'market_data': '1 week',
                    'trading_signals': '1 day',
                    'pattern_detections': '1 day',
                }

            # Create hypertables
            for table_name, interval in chunk_intervals.items():
                logger.info(f"Setting up hypertable for {table_name}")
                self.db.create_hypertable(
                    table_name=table_name,
                    time_column='timestamp',
                    chunk_time_interval=interval,
                    if_not_exists=True,
                )

            # Add compression policies
            for table_name in chunk_intervals.keys():
                logger.info(f"Adding compression policy for {table_name}")
                try:
                    self.db.add_compression_policy(table_name, compression_after)
                except Exception as e:
                    logger.warning(f"Compression policy for {table_name} failed: {e}")

            # Add retention policies if specified
            if retention_period:
                for table_name in chunk_intervals.keys():
                    logger.info(f"Adding retention policy for {table_name}")
                    try:
                        self.db.add_retention_policy(table_name, retention_period)
                    except Exception as e:
                        logger.warning(f"Retention policy for {table_name} failed: {e}")

            logger.info("TimescaleDB setup completed successfully")
            return True

        except Exception as e:
            logger.error(f"TimescaleDB setup failed: {e}")
            raise MigrationError(f"TimescaleDB setup failed: {e}")

    def migrate_sqlite_to_postgres(
        self,
        sqlite_url: str,
        batch_size: int = 1000,
        verify: bool = True,
    ) -> Dict[str, int]:
        """
        Migrate data from SQLite to PostgreSQL/TimescaleDB.

        Args:
            sqlite_url: SQLite database URL (e.g., "sqlite:///old_data.db")
            batch_size: Number of records to process at once
            verify: Verify data after migration

        Returns:
            Dict[str, int]: Count of migrated records per table

        Raises:
            MigrationError: If migration fails
        """
        logger.info(f"Starting migration from SQLite to {self.db.db_type}")

        # Create SQLite engine
        try:
            sqlite_engine = create_engine(sqlite_url)
            sqlite_session_factory = sessionmaker(bind=sqlite_engine)
        except Exception as e:
            raise MigrationError(f"Failed to connect to SQLite database: {e}")

        # Tables to migrate
        models = [
            ('market_data', MarketData),
            ('trading_signals', TradingSignal),
            ('pattern_detections', PatternDetection),
            ('screener_runs', ScreenerRun),
        ]

        migration_stats = {}

        for table_name, model_class in models:
            try:
                logger.info(f"Migrating {table_name}...")
                count = self._migrate_table(
                    sqlite_session_factory,
                    model_class,
                    batch_size,
                )
                migration_stats[table_name] = count
                logger.info(f"Migrated {count} records from {table_name}")

            except Exception as e:
                logger.error(f"Failed to migrate {table_name}: {e}")
                raise MigrationError(f"Table migration failed for {table_name}: {e}")

        # Verify migration if requested
        if verify:
            logger.info("Verifying migration...")
            self._verify_migration(sqlite_session_factory, migration_stats)

        sqlite_engine.dispose()
        logger.info("Migration completed successfully")

        return migration_stats

    def _migrate_table(
        self,
        source_session_factory: sessionmaker,
        model_class: type,
        batch_size: int,
    ) -> int:
        """
        Migrate a single table from source to destination.

        Args:
            source_session_factory: Source database session factory
            model_class: SQLAlchemy model class
            batch_size: Batch size for bulk operations

        Returns:
            int: Number of records migrated
        """
        total_count = 0
        offset = 0

        while True:
            # Read batch from source
            source_session = source_session_factory()
            try:
                records = (
                    source_session.query(model_class)
                    .offset(offset)
                    .limit(batch_size)
                    .all()
                )

                if not records:
                    break

                # Write batch to destination
                with self.db.session_scope() as dest_session:
                    for record in records:
                        # Create new record (detached from source session)
                        dest_session.merge(record)

                total_count += len(records)
                offset += batch_size

                logger.debug(f"Migrated {total_count} records so far...")

            finally:
                source_session.close()

        return total_count

    def _verify_migration(
        self,
        source_session_factory: sessionmaker,
        migration_stats: Dict[str, int],
    ) -> None:
        """
        Verify migration by comparing record counts.

        Args:
            source_session_factory: Source database session factory
            migration_stats: Statistics from migration

        Raises:
            MigrationError: If verification fails
        """
        models = [
            ('market_data', MarketData),
            ('trading_signals', TradingSignal),
            ('pattern_detections', PatternDetection),
            ('screener_runs', ScreenerRun),
        ]

        for table_name, model_class in models:
            source_session = source_session_factory()
            try:
                # Count in source
                source_count = source_session.query(model_class).count()

                # Count in destination
                with self.db.session_scope() as dest_session:
                    dest_count = dest_session.query(model_class).count()

                # Verify
                if source_count != dest_count:
                    raise MigrationError(
                        f"Verification failed for {table_name}: "
                        f"source={source_count}, destination={dest_count}"
                    )

                logger.info(
                    f"Verified {table_name}: {dest_count} records match source"
                )

            finally:
                source_session.close()

    def create_indexes(self) -> None:
        """
        Create or recreate all indexes on tables.

        This is useful after bulk data loading to optimize query performance.
        """
        try:
            logger.info("Creating indexes...")

            # Indexes are defined in the models via __table_args__
            # SQLAlchemy creates them automatically with create_all()
            Base.metadata.create_all(self.db.engine, checkfirst=True)

            logger.info("Indexes created successfully")

        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            raise MigrationError(f"Index creation failed: {e}")

    def vacuum_analyze(self) -> None:
        """
        Run VACUUM ANALYZE on PostgreSQL database to optimize performance.

        This is recommended after bulk data loading or migration.
        Only works with PostgreSQL/TimescaleDB.
        """
        if self.db.db_type == 'sqlite':
            logger.info("VACUUM ANALYZE not applicable for SQLite")
            return

        try:
            logger.info("Running VACUUM ANALYZE...")

            with self.db.engine.connect() as conn:
                # VACUUM cannot run inside a transaction block
                conn.execution_options(isolation_level="AUTOCOMMIT")
                conn.execute(text("VACUUM ANALYZE"))

            logger.info("VACUUM ANALYZE completed successfully")

        except Exception as e:
            logger.warning(f"VACUUM ANALYZE failed (non-fatal): {e}")

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the database.

        Returns:
            Dict[str, Any]: Database statistics including table sizes and row counts
        """
        stats = {
            'database_type': self.db.db_type,
            'is_timescaledb': self.db.is_timescaledb,
            'schema_version': self.get_current_version(),
            'tables': {},
        }

        models = [
            ('market_data', MarketData),
            ('trading_signals', TradingSignal),
            ('pattern_detections', PatternDetection),
            ('screener_runs', ScreenerRun),
        ]

        try:
            with self.db.session_scope() as session:
                for table_name, model_class in models:
                    count = session.query(model_class).count()
                    stats['tables'][table_name] = {
                        'row_count': count,
                    }

                    # Get size for PostgreSQL
                    if self.db.db_type in ['postgresql', 'timescaledb']:
                        try:
                            size_result = session.execute(
                                text(
                                    f"SELECT pg_size_pretty(pg_total_relation_size(:table_name))"
                                ),
                                {'table_name': table_name},
                            ).scalar()
                            stats['tables'][table_name]['size'] = size_result
                        except Exception:
                            pass

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")

        return stats


def initialize_database(
    setup_timescaledb: bool = True,
    force_recreate: bool = False,
) -> Database:
    """
    Initialize database with proper setup and migrations.

    Args:
        setup_timescaledb: Setup TimescaleDB optimizations if available
        force_recreate: Force recreate all tables (WARNING: destroys data)

    Returns:
        Database: Initialized database instance
    """
    db = get_db()
    migrator = DatabaseMigrator(db)

    try:
        # Drop existing tables if force recreate
        if force_recreate:
            logger.warning("Force recreating database tables...")
            db.drop_tables()

        # Create all tables
        db.create_tables()
        logger.info("Database tables created")

        # Ensure schema version table exists
        migrator.ensure_schema_version_table()

        # Check current version
        current_version = migrator.get_current_version()
        if current_version is None:
            migrator.record_version(
                DatabaseMigrator.CURRENT_VERSION,
                "Initial schema setup",
            )
            logger.info(f"Initialized schema version: {DatabaseMigrator.CURRENT_VERSION}")
        else:
            logger.info(f"Current schema version: {current_version}")

        # Setup TimescaleDB if available and requested
        if setup_timescaledb and db.is_timescaledb:
            logger.info("Setting up TimescaleDB optimizations...")
            migrator.setup_timescaledb()

        # Create indexes
        migrator.create_indexes()

        logger.info("Database initialization completed successfully")
        return db

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


if __name__ == '__main__':
    # Example usage
    try:
        # Initialize database
        db = initialize_database(setup_timescaledb=True)

        # Get database statistics
        migrator = DatabaseMigrator(db)
        stats = migrator.get_database_stats()

        print("\nDatabase Statistics:")
        print(f"Database Type: {stats['database_type']}")
        print(f"TimescaleDB: {stats['is_timescaledb']}")
        print(f"Schema Version: {stats['schema_version']}")
        print("\nTables:")
        for table_name, table_stats in stats['tables'].items():
            print(f"  {table_name}: {table_stats}")

    except Exception as e:
        print(f"Error: {e}")
