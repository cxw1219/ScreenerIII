"""
Unit tests for database module.

Tests database operations including connection, table creation, session management,
TimescaleDB features, and error handling.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta
import sys
from pathlib import Path as PathlibPath

# Add src directory to path
sys.path.insert(0, str(PathlibPath(__file__).parent.parent.parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError, IntegrityError, ProgrammingError
from sqlalchemy.orm import Session


class TestDatabaseInitialization:
    """Test suite for database initialization."""

    @patch('src.core.database.get_config')
    def test_database_singleton_pattern(self, mock_config):
        """Test that Database implements singleton pattern."""
        from src.core.database import Database

        # Configure mock
        mock_config.return_value = Mock(
            database_url='sqlite:///test.db',
            database_echo=False,
            database_pool_size=5,
            database_max_overflow=10
        )

        db1 = Database()
        db2 = Database()

        assert db1 is db2

    @patch('src.core.database.get_config')
    def test_database_initialization_sqlite(self, mock_config):
        """Test database initialization with SQLite."""
        from src.core.database import Database

        mock_config.return_value = Mock(
            database_url='sqlite:///test.db',
            database_echo=False,
            database_pool_size=5,
            database_max_overflow=10
        )

        db = Database()

        assert db._engine is not None
        assert db.db_type == 'sqlite'
        assert not db.is_timescaledb

    @patch('src.core.database.get_config')
    def test_database_type_detection_postgresql(self, mock_config):
        """Test database type detection for PostgreSQL."""
        from src.core.database import Database

        url = 'postgresql://user:pass@localhost/db'
        assert Database()._detect_database_type(url) == 'postgresql'

    @patch('src.core.database.get_config')
    def test_database_type_detection_sqlite(self, mock_config):
        """Test database type detection for SQLite."""
        from src.core.database import Database

        url = 'sqlite:///test.db'
        assert Database()._detect_database_type(url) == 'sqlite'


class TestSessionManagement:
    """Test suite for database session management."""

    @patch('src.core.database.get_config')
    def test_get_session(self, mock_config):
        """Test getting a new database session."""
        from src.core.database import Database

        mock_config.return_value = Mock(
            database_url='sqlite:///test.db',
            database_echo=False,
            database_pool_size=5,
            database_max_overflow=10
        )

        db = Database()
        session = db.get_session()

        assert session is not None
        assert isinstance(session, Session)
        session.close()

    @patch('src.core.database.get_config')
    def test_session_scope_success(self, mock_config):
        """Test session scope with successful transaction."""
        from src.core.database import Database

        mock_config.return_value = Mock(
            database_url='sqlite:///test.db',
            database_echo=False,
            database_pool_size=5,
            database_max_overflow=10
        )

        db = Database()

        with db.session_scope() as session:
            # Session should be valid
            assert session is not None

    @patch('src.core.database.get_config')
    def test_session_scope_rollback_on_error(self, mock_config):
        """Test that session scope rolls back on error."""
        from src.core.database import Database

        mock_config.return_value = Mock(
            database_url='sqlite:///test.db',
            database_echo=False,
            database_pool_size=5,
            database_max_overflow=10
        )

        db = Database()

        with pytest.raises(ValueError):
            with db.session_scope() as session:
                raise ValueError("Test error")


class TestTableOperations:
    """Test suite for table creation and management."""

    @patch('src.core.database.get_config')
    def test_create_tables(self, mock_config):
        """Test creating all database tables."""
        from src.core.database import Database

        mock_config.return_value = Mock(
            database_url='sqlite:///test.db',
            database_echo=False,
            database_pool_size=5,
            database_max_overflow=10
        )

        db = Database()

        # Should not raise exception
        db.create_tables()

    @patch('src.core.database.get_config')
    def test_drop_tables(self, mock_config):
        """Test dropping all database tables."""
        from src.core.database import Database

        mock_config.return_value = Mock(
            database_url='sqlite:///test.db',
            database_echo=False,
            database_pool_size=5,
            database_max_overflow=10
        )

        db = Database()
        db.create_tables()

        # Should not raise exception
        db.drop_tables()


class TestConnectionHandling:
    """Test suite for database connection handling."""

    @patch('src.core.database.get_config')
    def test_connection_test_success(self, mock_config):
        """Test successful database connection test."""
        from src.core.database import Database

        mock_config.return_value = Mock(
            database_url='sqlite:///test.db',
            database_echo=False,
            database_pool_size=5,
            database_max_overflow=10
        )

        db = Database()
        result = db.test_connection()

        assert result is True

    @patch('src.core.database.get_config')
    def test_close_connection(self, mock_config):
        """Test closing database connections."""
        from src.core.database import Database

        mock_config.return_value = Mock(
            database_url='sqlite:///test.db',
            database_echo=False,
            database_pool_size=5,
            database_max_overflow=10
        )

        db = Database()

        # Should not raise exception
        db.close()


class TestTimescaleDBFeatures:
    """Test suite for TimescaleDB-specific features."""

    @patch('src.core.database.get_config')
    def test_timescaledb_detection_false_for_sqlite(self, mock_config):
        """Test that TimescaleDB is not detected for SQLite."""
        from src.core.database import Database

        mock_config.return_value = Mock(
            database_url='sqlite:///test.db',
            database_echo=False,
            database_pool_size=5,
            database_max_overflow=10
        )

        db = Database()

        assert db.is_timescaledb is False

    @patch('src.core.database.get_config')
    def test_create_hypertable_fails_without_timescaledb(self, mock_config):
        """Test that hypertable creation fails without TimescaleDB."""
        from src.core.database import Database

        mock_config.return_value = Mock(
            database_url='sqlite:///test.db',
            database_echo=False,
            database_pool_size=5,
            database_max_overflow=10
        )

        db = Database()
        result = db.create_hypertable('market_data')

        assert result is False

    @patch('src.core.database.get_config')
    def test_compression_policy_fails_without_timescaledb(self, mock_config):
        """Test that compression policy fails without TimescaleDB."""
        from src.core.database import Database

        mock_config.return_value = Mock(
            database_url='sqlite:///test.db',
            database_echo=False,
            database_pool_size=5,
            database_max_overflow=10
        )

        db = Database()
        result = db.add_compression_policy('market_data')

        assert result is False

    @patch('src.core.database.get_config')
    def test_retention_policy_fails_without_timescaledb(self, mock_config):
        """Test that retention policy fails without TimescaleDB."""
        from src.core.database import Database

        mock_config.return_value = Mock(
            database_url='sqlite:///test.db',
            database_echo=False,
            database_pool_size=5,
            database_max_overflow=10
        )

        db = Database()
        result = db.add_retention_policy('market_data')

        assert result is False

    @patch('src.core.database.get_config')
    def test_setup_timescaledb_optimizations_skipped(self, mock_config):
        """Test that TimescaleDB optimizations are skipped for non-TimescaleDB."""
        from src.core.database import Database

        mock_config.return_value = Mock(
            database_url='sqlite:///test.db',
            database_echo=False,
            database_pool_size=5,
            database_max_overflow=10
        )

        db = Database()

        # Should not raise exception
        db.setup_timescaledb_optimizations()


class TestDatabaseModels:
    """Test suite for database models."""

    def test_market_data_model_creation(self):
        """Test MarketData model creation."""
        from src.core.database import MarketData

        market_data = MarketData(
            instrument='EUR_USD',
            timeframe='H1',
            timestamp=datetime.now(),
            open=1.0,
            high=1.1,
            low=0.9,
            close=1.05,
            volume=1000
        )

        assert market_data.instrument == 'EUR_USD'
        assert market_data.timeframe == 'H1'
        assert market_data.open == 1.0
        assert market_data.high == 1.1
        assert market_data.low == 0.9
        assert market_data.close == 1.05
        assert market_data.volume == 1000

    def test_market_data_repr(self):
        """Test MarketData string representation."""
        from src.core.database import MarketData

        market_data = MarketData(
            instrument='EUR_USD',
            timeframe='H1',
            timestamp=datetime.now(),
            open=1.0,
            high=1.1,
            low=0.9,
            close=1.05,
            volume=1000
        )

        repr_str = repr(market_data)
        assert 'EUR_USD' in repr_str
        assert 'H1' in repr_str

    def test_trading_signal_model_creation(self):
        """Test TradingSignal model creation."""
        from src.core.database import TradingSignal

        signal = TradingSignal(
            instrument='EUR_USD',
            timeframe='H1',
            timestamp=datetime.now(),
            signal_type='BUY',
            confidence=0.85,
            strategy='RSI_CROSSOVER',
            entry_price=1.0050,
            stop_loss=1.0025,
            take_profit=1.0100
        )

        assert signal.instrument == 'EUR_USD'
        assert signal.signal_type == 'BUY'
        assert signal.confidence == 0.85
        assert signal.strategy == 'RSI_CROSSOVER'

    def test_pattern_detection_model_creation(self):
        """Test PatternDetection model creation."""
        from src.core.database import PatternDetection

        now = datetime.now()
        pattern = PatternDetection(
            instrument='EUR_USD',
            timeframe='H1',
            timestamp=now,
            pattern_type='head_shoulders',
            pattern_name='Head and Shoulders',
            confidence=0.75,
            start_time=now - timedelta(hours=24),
            end_time=now
        )

        assert pattern.instrument == 'EUR_USD'
        assert pattern.pattern_type == 'head_shoulders'
        assert pattern.confidence == 0.75

    def test_screener_run_model_creation(self):
        """Test ScreenerRun model creation."""
        from src.core.database import ScreenerRun

        run = ScreenerRun(
            instruments_scanned=['EUR_USD', 'GBP_USD'],
            timeframes=['H1', 'H4'],
            strategies=['RSI', 'MACD'],
            signals_generated=5,
            patterns_detected=2,
            execution_time=1.5,
            success=True
        )

        assert run.signals_generated == 5
        assert run.patterns_detected == 2
        assert run.execution_time == 1.5
        assert run.success is True


class TestDatabaseErrors:
    """Test suite for database error handling."""

    @patch('src.core.database.get_config')
    def test_database_error_on_invalid_url(self, mock_config):
        """Test database error handling with invalid URL."""
        from src.core.database import Database, DatabaseConnectionError

        mock_config.return_value = Mock(
            database_url='invalid://url',
            database_echo=False,
            database_pool_size=5,
            database_max_overflow=10
        )

        # Creating database with invalid URL should raise error
        with pytest.raises(DatabaseConnectionError):
            db = Database()

    def test_database_error_exception(self):
        """Test DatabaseError exception."""
        from src.core.database import DatabaseError

        with pytest.raises(DatabaseError):
            raise DatabaseError("Test error")

    def test_database_connection_error_exception(self):
        """Test DatabaseConnectionError exception."""
        from src.core.database import DatabaseConnectionError

        with pytest.raises(DatabaseConnectionError):
            raise DatabaseConnectionError("Connection failed")


class TestDatabaseHelperFunctions:
    """Test suite for database helper functions."""

    @patch('src.core.database.get_config')
    def test_get_db_singleton(self, mock_config):
        """Test get_db returns singleton instance."""
        from src.core.database import get_db

        mock_config.return_value = Mock(
            database_url='sqlite:///test.db',
            database_echo=False,
            database_pool_size=5,
            database_max_overflow=10
        )

        db1 = get_db()
        db2 = get_db()

        assert db1 is db2

    @patch('src.core.database.get_config')
    def test_init_db_creates_tables(self, mock_config):
        """Test init_db creates all tables."""
        from src.core.database import init_db

        mock_config.return_value = Mock(
            database_url='sqlite:///test.db',
            database_echo=False,
            database_pool_size=5,
            database_max_overflow=10
        )

        db = init_db()

        assert db is not None


class TestDatabaseProperties:
    """Test suite for database properties."""

    @patch('src.core.database.get_config')
    def test_engine_property(self, mock_config):
        """Test database engine property."""
        from src.core.database import Database

        mock_config.return_value = Mock(
            database_url='sqlite:///test.db',
            database_echo=False,
            database_pool_size=5,
            database_max_overflow=10
        )

        db = Database()
        engine = db.engine

        assert engine is not None

    @patch('src.core.database.get_config')
    def test_db_type_property(self, mock_config):
        """Test database type property."""
        from src.core.database import Database

        mock_config.return_value = Mock(
            database_url='sqlite:///test.db',
            database_echo=False,
            database_pool_size=5,
            database_max_overflow=10
        )

        db = Database()
        db_type = db.db_type

        assert db_type == 'sqlite'

    @patch('src.core.database.get_config')
    def test_is_timescaledb_property(self, mock_config):
        """Test is_timescaledb property."""
        from src.core.database import Database

        mock_config.return_value = Mock(
            database_url='sqlite:///test.db',
            database_echo=False,
            database_pool_size=5,
            database_max_overflow=10
        )

        db = Database()
        is_timescale = db.is_timescaledb

        assert isinstance(is_timescale, bool)
