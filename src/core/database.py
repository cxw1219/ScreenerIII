"""
Database Module

This module provides SQLAlchemy setup, engine creation, session management,
and base models for storing market data, signals, and patterns.

Supports both SQLite (for development) and TimescaleDB/PostgreSQL (for production)
with automatic detection based on connection string.
"""

import time
from typing import Optional, Generator, Any, Literal
from contextlib import contextmanager
from datetime import datetime, timedelta
from urllib.parse import urlparse

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    Text,
    JSON,
    Index,
    event,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
    Session,
    scoped_session,
)
from sqlalchemy.exc import (
    SQLAlchemyError,
    OperationalError,
    IntegrityError,
    ProgrammingError,
)
from sqlalchemy.pool import QueuePool, NullPool

from .config_loader import get_config
from .logger import get_logger

logger = get_logger(__name__)

# Create declarative base for all models
Base = declarative_base()

# Type alias for database types
DatabaseType = Literal['sqlite', 'postgresql', 'timescaledb']


class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Exception raised when database connection fails."""
    pass


class Database:
    """
    Database manager handling SQLAlchemy engine and session creation.

    Provides connection pooling, error recovery, and session management.
    Supports both SQLite and TimescaleDB/PostgreSQL with automatic detection.
    """

    _instance: Optional['Database'] = None
    _engine: Optional[Engine] = None
    _session_factory: Optional[sessionmaker] = None
    _scoped_session: Optional[scoped_session] = None
    _db_type: Optional[DatabaseType] = None
    _is_timescaledb: bool = False

    def __new__(cls) -> 'Database':
        """Implement singleton pattern for database instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize database connection and session factory."""
        if self._engine is None:
            self._initialize()

    def _detect_database_type(self, database_url: str) -> DatabaseType:
        """
        Detect database type from connection string.

        Args:
            database_url: Database connection URL

        Returns:
            DatabaseType: Type of database (sqlite, postgresql, or timescaledb)
        """
        parsed = urlparse(database_url)
        scheme = parsed.scheme.lower()

        if scheme.startswith('sqlite'):
            return 'sqlite'
        elif scheme.startswith('postgresql') or scheme.startswith('postgres'):
            return 'postgresql'
        else:
            logger.warning(f"Unknown database scheme: {scheme}, defaulting to SQLite")
            return 'sqlite'

    def _check_timescaledb_extension(self) -> bool:
        """
        Check if TimescaleDB extension is available and enabled.

        Returns:
            bool: True if TimescaleDB is available
        """
        if self._db_type == 'sqlite':
            return False

        try:
            with self.session_scope() as session:
                result = session.execute(
                    text("SELECT COUNT(*) FROM pg_extension WHERE extname = 'timescaledb'")
                ).scalar()
                return result > 0
        except Exception as e:
            logger.debug(f"TimescaleDB extension check failed: {e}")
            return False

    def _initialize(self) -> None:
        """
        Initialize database engine and session factory.

        Raises:
            DatabaseConnectionError: If database connection fails
        """
        try:
            config = get_config()

            # Detect database type
            self._db_type = self._detect_database_type(config.database_url)
            is_sqlite = self._db_type == 'sqlite'

            # Engine configuration
            engine_kwargs = {
                'echo': config.database_echo,
                'future': True,  # Use SQLAlchemy 2.0 style
            }

            # Add connection pooling for non-SQLite databases
            if not is_sqlite:
                engine_kwargs.update({
                    'poolclass': QueuePool,
                    'pool_size': config.database_pool_size,
                    'max_overflow': config.database_max_overflow,
                    'pool_pre_ping': True,  # Test connections before using
                    'pool_recycle': 3600,  # Recycle connections after 1 hour
                })
            else:
                # SQLite specific settings
                engine_kwargs['connect_args'] = {
                    'check_same_thread': False,
                    'timeout': 30,
                }

            # Create engine
            self._engine = create_engine(config.database_url, **engine_kwargs)

            # Add event listeners
            self._setup_event_listeners()

            # Create session factory
            self._session_factory = sessionmaker(
                bind=self._engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )

            # Create scoped session for thread-local sessions
            self._scoped_session = scoped_session(self._session_factory)

            # Check for TimescaleDB if using PostgreSQL
            if self._db_type == 'postgresql':
                self._is_timescaledb = self._check_timescaledb_extension()
                if self._is_timescaledb:
                    logger.info("TimescaleDB extension detected and enabled")
                    self._db_type = 'timescaledb'

            logger.info(
                f"Database initialized: {self._db_type.upper()} "
                f"(TimescaleDB: {self._is_timescaledb})"
            )

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseConnectionError(f"Database initialization failed: {e}")

    def _setup_event_listeners(self) -> None:
        """Setup SQLAlchemy event listeners for connection management."""

        @event.listens_for(self._engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Event listener for new database connections."""
            logger.debug("New database connection established")

        @event.listens_for(self._engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Event listener for connection checkout from pool."""
            logger.debug("Connection checked out from pool")

        @event.listens_for(self._engine, "checkin")
        def receive_checkin(dbapi_conn, connection_record):
            """Event listener for connection return to pool."""
            logger.debug("Connection returned to pool")

    @property
    def engine(self) -> Engine:
        """Get SQLAlchemy engine instance."""
        if self._engine is None:
            raise DatabaseError("Database not initialized")
        return self._engine

    @property
    def db_type(self) -> Optional[DatabaseType]:
        """Get the database type."""
        return self._db_type

    @property
    def is_timescaledb(self) -> bool:
        """Check if TimescaleDB is enabled."""
        return self._is_timescaledb

    def get_session(self) -> Session:
        """
        Get a new database session.

        Returns:
            Session: New SQLAlchemy session
        """
        if self._session_factory is None:
            raise DatabaseError("Session factory not initialized")
        return self._session_factory()

    def get_scoped_session(self) -> scoped_session:
        """
        Get scoped (thread-local) session.

        Returns:
            scoped_session: Thread-local session
        """
        if self._scoped_session is None:
            raise DatabaseError("Scoped session not initialized")
        return self._scoped_session

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope for database operations.

        Usage:
            with db.session_scope() as session:
                session.add(model_instance)
                # Automatically commits on success, rolls back on error

        Yields:
            Session: Database session
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
            logger.debug("Database transaction committed")
        except IntegrityError as e:
            session.rollback()
            logger.warning(f"Integrity error, transaction rolled back: {e}")
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Error in database transaction, rolled back: {e}")
            raise
        finally:
            session.close()

    def create_tables(self) -> None:
        """
        Create all tables defined in models.

        Raises:
            DatabaseError: If table creation fails
        """
        try:
            Base.metadata.create_all(self._engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise DatabaseError(f"Table creation failed: {e}")

    def drop_tables(self) -> None:
        """
        Drop all tables (use with caution!).

        Raises:
            DatabaseError: If table dropping fails
        """
        try:
            Base.metadata.drop_all(self._engine)
            logger.warning("All database tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise DatabaseError(f"Table dropping failed: {e}")

    def test_connection(self, max_retries: int = 3) -> bool:
        """
        Test database connection with retries.

        Args:
            max_retries: Maximum number of connection attempts

        Returns:
            bool: True if connection successful
        """
        for attempt in range(max_retries):
            try:
                with self.session_scope() as session:
                    session.execute("SELECT 1")
                logger.info("Database connection test successful")
                return True
            except OperationalError as e:
                logger.warning(
                    f"Connection attempt {attempt + 1}/{max_retries} failed: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error("Database connection test failed after all retries")
                    return False
        return False

    def close(self) -> None:
        """Close database connections and dispose of engine."""
        if self._engine:
            self._engine.dispose()
            logger.info("Database connections closed")

    def create_hypertable(
        self,
        table_name: str,
        time_column: str = 'timestamp',
        chunk_time_interval: str = '1 week',
        if_not_exists: bool = True,
    ) -> bool:
        """
        Convert a regular PostgreSQL table to a TimescaleDB hypertable.

        Args:
            table_name: Name of the table to convert
            time_column: Name of the time column for partitioning
            chunk_time_interval: Size of time chunks (e.g., '1 day', '1 week')
            if_not_exists: Skip if hypertable already exists

        Returns:
            bool: True if successful

        Raises:
            DatabaseError: If TimescaleDB is not available or operation fails
        """
        if not self._is_timescaledb:
            logger.warning(
                f"Cannot create hypertable '{table_name}': TimescaleDB not available"
            )
            return False

        try:
            with self.session_scope() as session:
                # Check if already a hypertable
                check_query = text(
                    """
                    SELECT COUNT(*) FROM timescaledb_information.hypertables
                    WHERE hypertable_name = :table_name
                    """
                )
                is_hypertable = session.execute(
                    check_query, {'table_name': table_name}
                ).scalar()

                if is_hypertable:
                    logger.info(f"Table '{table_name}' is already a hypertable")
                    return True

                # Create hypertable
                create_query = text(
                    f"""
                    SELECT create_hypertable(
                        :table_name,
                        :time_column,
                        chunk_time_interval => INTERVAL :interval,
                        if_not_exists => :if_not_exists
                    )
                    """
                )

                session.execute(
                    create_query,
                    {
                        'table_name': table_name,
                        'time_column': time_column,
                        'interval': chunk_time_interval,
                        'if_not_exists': if_not_exists,
                    },
                )

                logger.info(
                    f"Created hypertable '{table_name}' with chunk interval: {chunk_time_interval}"
                )
                return True

        except ProgrammingError as e:
            logger.error(f"Failed to create hypertable '{table_name}': {e}")
            raise DatabaseError(f"Hypertable creation failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating hypertable '{table_name}': {e}")
            raise DatabaseError(f"Hypertable creation failed: {e}")

    def add_compression_policy(
        self,
        table_name: str,
        compress_after: str = '7 days',
    ) -> bool:
        """
        Add automatic compression policy to a hypertable.

        Args:
            table_name: Name of the hypertable
            compress_after: Compress chunks older than this interval

        Returns:
            bool: True if successful

        Raises:
            DatabaseError: If operation fails
        """
        if not self._is_timescaledb:
            logger.warning("Cannot add compression policy: TimescaleDB not available")
            return False

        try:
            with self.session_scope() as session:
                # Enable compression on the hypertable
                enable_compression = text(
                    """
                    ALTER TABLE :table_name SET (
                        timescaledb.compress,
                        timescaledb.compress_segmentby = 'instrument'
                    )
                    """
                )

                # Add compression policy
                add_policy = text(
                    """
                    SELECT add_compression_policy(
                        :table_name,
                        INTERVAL :compress_after
                    )
                    """
                )

                session.execute(text(f"ALTER TABLE {table_name} SET (timescaledb.compress)"))
                session.execute(
                    add_policy,
                    {'table_name': table_name, 'compress_after': compress_after},
                )

                logger.info(
                    f"Added compression policy to '{table_name}': compress after {compress_after}"
                )
                return True

        except Exception as e:
            logger.error(f"Failed to add compression policy to '{table_name}': {e}")
            raise DatabaseError(f"Compression policy addition failed: {e}")

    def add_retention_policy(
        self,
        table_name: str,
        retention_period: str = '90 days',
    ) -> bool:
        """
        Add data retention policy to automatically drop old data.

        Args:
            table_name: Name of the hypertable
            retention_period: Keep data newer than this interval

        Returns:
            bool: True if successful

        Raises:
            DatabaseError: If operation fails
        """
        if not self._is_timescaledb:
            logger.warning("Cannot add retention policy: TimescaleDB not available")
            return False

        try:
            with self.session_scope() as session:
                add_policy = text(
                    """
                    SELECT add_retention_policy(
                        :table_name,
                        INTERVAL :retention_period
                    )
                    """
                )

                session.execute(
                    add_policy,
                    {'table_name': table_name, 'retention_period': retention_period},
                )

                logger.info(
                    f"Added retention policy to '{table_name}': keep last {retention_period}"
                )
                return True

        except Exception as e:
            logger.error(f"Failed to add retention policy to '{table_name}': {e}")
            raise DatabaseError(f"Retention policy addition failed: {e}")

    def setup_timescaledb_optimizations(self) -> None:
        """
        Setup TimescaleDB-specific optimizations for all time-series tables.

        This includes:
        - Converting tables to hypertables
        - Adding compression policies
        - Adding retention policies
        - Creating optimized indexes

        Raises:
            DatabaseError: If operations fail
        """
        if not self._is_timescaledb:
            logger.info("Skipping TimescaleDB optimizations: not using TimescaleDB")
            return

        try:
            # Convert market_data to hypertable with 1-week chunks
            self.create_hypertable('market_data', 'timestamp', '1 week')

            # Convert trading_signals to hypertable with 1-day chunks (more recent data)
            self.create_hypertable('trading_signals', 'timestamp', '1 day')

            # Convert pattern_detections to hypertable with 1-day chunks
            self.create_hypertable('pattern_detections', 'timestamp', '1 day')

            # Add compression policies (compress data older than 7 days)
            self.add_compression_policy('market_data', '7 days')
            self.add_compression_policy('trading_signals', '7 days')
            self.add_compression_policy('pattern_detections', '7 days')

            # Add retention policies (keep 90 days of data)
            # Uncomment if you want automatic data deletion
            # self.add_retention_policy('market_data', '90 days')
            # self.add_retention_policy('trading_signals', '90 days')
            # self.add_retention_policy('pattern_detections', '90 days')

            logger.info("TimescaleDB optimizations applied successfully")

        except Exception as e:
            logger.error(f"Failed to setup TimescaleDB optimizations: {e}")
            raise DatabaseError(f"TimescaleDB optimization setup failed: {e}")


# Models for storing market data, signals, and patterns

class MarketData(Base):
    """
    Model for storing historical market/candle data.

    Optimized for time-series queries with proper indexing for both SQLite and TimescaleDB.
    In TimescaleDB, this table is converted to a hypertable partitioned by timestamp.
    """

    __tablename__ = 'market_data'

    id = Column(Integer, primary_key=True, autoincrement=True)
    instrument = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)

    # OHLCV data
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Composite indexes for efficient time-series queries
    # These work well for both SQLite and TimescaleDB
    __table_args__ = (
        Index('idx_market_data_instrument_timeframe_timestamp',
              'instrument', 'timeframe', 'timestamp', unique=True),
        Index('idx_market_data_timestamp_desc', 'timestamp'),
        Index('idx_market_data_instrument_timestamp', 'instrument', 'timestamp'),
    )

    def __repr__(self) -> str:
        return (
            f"<MarketData(instrument={self.instrument}, timeframe={self.timeframe}, "
            f"timestamp={self.timestamp}, close={self.close})>"
        )


class TradingSignal(Base):
    """
    Model for storing trading signals generated by the screener.

    Optimized for time-series queries and signal tracking.
    In TimescaleDB, this table is converted to a hypertable partitioned by timestamp.
    """

    __tablename__ = 'trading_signals'

    id = Column(Integer, primary_key=True, autoincrement=True)
    instrument = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)

    # Signal information
    signal_type = Column(String(20), nullable=False)  # 'BUY', 'SELL', 'NEUTRAL'
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    strategy = Column(String(50), nullable=False)  # Strategy that generated signal

    # Price levels
    entry_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)

    # Additional data
    indicators = Column(JSON, nullable=True)  # Store indicator values as JSON
    extra_data = Column(JSON, nullable=True)  # Additional signal metadata

    # Status tracking
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    executed_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Optimized indexes for signal queries
    __table_args__ = (
        Index('idx_trading_signals_instrument_timestamp', 'instrument', 'timestamp'),
        Index('idx_trading_signals_timestamp_desc', 'timestamp'),
        Index('idx_trading_signals_signal_type_active', 'signal_type', 'is_active'),
        Index('idx_trading_signals_active_timestamp', 'is_active', 'timestamp'),
    )

    def __repr__(self) -> str:
        return (
            f"<TradingSignal(instrument={self.instrument}, type={self.signal_type}, "
            f"confidence={self.confidence:.2f}, timestamp={self.timestamp})>"
        )


class PatternDetection(Base):
    """
    Model for storing detected chart patterns.

    Optimized for pattern queries and time-series analysis.
    In TimescaleDB, this table is converted to a hypertable partitioned by timestamp.
    """

    __tablename__ = 'pattern_detections'

    id = Column(Integer, primary_key=True, autoincrement=True)
    instrument = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)

    # Pattern information
    pattern_type = Column(String(50), nullable=False, index=True)  # e.g., 'head_shoulders', 'triangle'
    pattern_name = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0

    # Pattern details
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    key_points = Column(JSON, nullable=True)  # Important points in the pattern

    # Price levels
    breakout_level = Column(Float, nullable=True)
    target_level = Column(Float, nullable=True)

    # Status
    is_complete = Column(Boolean, default=False, nullable=False, index=True)
    is_validated = Column(Boolean, default=False, nullable=False)

    # Additional data
    extra_data = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Optimized indexes for pattern queries
    __table_args__ = (
        Index('idx_pattern_detections_instrument_pattern_timestamp',
              'instrument', 'pattern_type', 'timestamp'),
        Index('idx_pattern_detections_timestamp_desc', 'timestamp'),
        Index('idx_pattern_detections_complete_validated', 'is_complete', 'is_validated'),
    )

    def __repr__(self) -> str:
        return (
            f"<PatternDetection(instrument={self.instrument}, pattern={self.pattern_name}, "
            f"confidence={self.confidence:.2f}, timestamp={self.timestamp})>"
        )


class ScreenerRun(Base):
    """Model for tracking screener execution runs."""

    __tablename__ = 'screener_runs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Run configuration
    instruments_scanned = Column(JSON, nullable=False)  # List of instruments
    timeframes = Column(JSON, nullable=False)  # List of timeframes
    strategies = Column(JSON, nullable=False)  # List of strategies used

    # Results
    signals_generated = Column(Integer, default=0, nullable=False)
    patterns_detected = Column(Integer, default=0, nullable=False)

    # Performance metrics
    execution_time = Column(Float, nullable=True)  # Seconds
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)

    # Timestamps
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<ScreenerRun(id={self.id}, timestamp={self.run_timestamp}, "
            f"signals={self.signals_generated}, patterns={self.patterns_detected})>"
        )


# Global database instance
_db: Optional[Database] = None


def get_db() -> Database:
    """
    Get or create the global database instance.

    Returns:
        Database: The global database instance
    """
    global _db
    if _db is None:
        _db = Database()
    return _db


def init_db(setup_timescaledb: bool = True) -> Database:
    """
    Initialize database and create all tables.

    Args:
        setup_timescaledb: If True, setup TimescaleDB optimizations (hypertables, etc.)

    Returns:
        Database: Initialized database instance
    """
    db = get_db()
    db.create_tables()

    # Setup TimescaleDB optimizations if enabled and available
    if setup_timescaledb and db.is_timescaledb:
        try:
            db.setup_timescaledb_optimizations()
            logger.info("TimescaleDB optimizations configured successfully")
        except Exception as e:
            logger.warning(f"Failed to setup TimescaleDB optimizations: {e}")

    return db


if __name__ == '__main__':
    # Test database connection
    try:
        db = get_db()
        if db.test_connection():
            print("Database connection successful!")
            db.create_tables()
            print("Database tables created successfully!")
        else:
            print("Database connection failed!")
    except Exception as e:
        print(f"Database error: {e}")
