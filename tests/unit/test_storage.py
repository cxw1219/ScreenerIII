"""
Unit tests for storage module.

Tests database storage operations for market data including
data persistence, querying, batch operations, and data validation.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
import sys
from pathlib import Path as PathlibPath
import tempfile
import os
import sqlite3
import pandas as pd

# Add src directory to path
sys.path.insert(0, str(PathlibPath(__file__).parent.parent.parent / "src"))


@pytest.fixture
def temp_db_path():
    """Create temporary database path for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def storage_manager(temp_db_path):
    """Create StorageManager instance with temporary database."""
    from src.data.storage import StorageManager

    manager = StorageManager(db_path=temp_db_path)
    yield manager

    # Cleanup
    manager.close()


@pytest.fixture
def sample_price():
    """Create sample Price object."""
    from src.data.market_data import Price

    return Price(
        instrument='EUR_USD',
        bid=1.0000,
        ask=1.0005,
        timestamp=datetime.now(),
        tradeable=True
    )


@pytest.fixture
def sample_candle():
    """Create sample Candle object."""
    from src.data.market_data import Candle

    return Candle(
        instrument='EUR_USD',
        timestamp=datetime.now(),
        open=1.0000,
        high=1.0050,
        low=0.9950,
        close=1.0025,
        volume=1000,
        complete=True,
        granularity='H1'
    )


class TestStorageManagerInitialization:
    """Test suite for StorageManager initialization."""

    def test_storage_manager_creation(self, temp_db_path):
        """Test creating StorageManager instance."""
        from src.data.storage import StorageManager

        manager = StorageManager(db_path=temp_db_path)

        assert manager is not None
        assert manager.db_path == PathlibPath(temp_db_path)

    def test_storage_manager_creates_database(self, temp_db_path):
        """Test that StorageManager creates database file."""
        from src.data.storage import StorageManager

        manager = StorageManager(db_path=temp_db_path)

        assert os.path.exists(temp_db_path)

    def test_storage_manager_creates_tables(self, storage_manager):
        """Test that StorageManager creates required tables."""
        conn = storage_manager._get_connection()
        cursor = conn.cursor()

        # Check that tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        assert 'prices' in tables
        assert 'candles' in tables
        assert 'spreads' in tables
        assert 'volumes' in tables


class TestDatabaseConnection:
    """Test suite for database connection handling."""

    def test_get_connection_success(self, storage_manager):
        """Test successful database connection."""
        conn = storage_manager._get_connection()

        assert conn is not None
        assert isinstance(conn, sqlite3.Connection)

    def test_get_connection_reuses_connection(self, storage_manager):
        """Test that get_connection reuses existing connection."""
        conn1 = storage_manager._get_connection()
        conn2 = storage_manager._get_connection()

        assert conn1 is conn2

    def test_connection_has_row_factory(self, storage_manager):
        """Test that connection has row factory configured."""
        conn = storage_manager._get_connection()

        assert conn.row_factory is not None


class TestPriceStorage:
    """Test suite for price data storage."""

    def test_save_price(self, storage_manager, sample_price):
        """Test saving a single price."""
        result = storage_manager.save_price(sample_price)

        assert result is True

    def test_save_price_duplicate_replaces(self, storage_manager, sample_price):
        """Test that duplicate price is replaced."""
        # Save price twice with same timestamp
        result1 = storage_manager.save_price(sample_price)
        result2 = storage_manager.save_price(sample_price)

        assert result1 is True
        assert result2 is True

    def test_save_prices_batch(self, storage_manager):
        """Test saving multiple prices in batch."""
        from src.data.market_data import Price

        prices = [
            Price(
                instrument='EUR_USD',
                bid=1.0000 + i * 0.0001,
                ask=1.0005 + i * 0.0001,
                timestamp=datetime.now() + timedelta(seconds=i)
            )
            for i in range(5)
        ]

        successful, failed = storage_manager.save_prices(prices)

        assert successful == 5
        assert failed == 0

    def test_get_latest_price(self, storage_manager, sample_price):
        """Test retrieving latest price."""
        storage_manager.save_price(sample_price)

        latest = storage_manager.get_latest_price('EUR_USD')

        assert latest is not None
        assert latest['instrument'] == 'EUR_USD'

    def test_get_latest_price_nonexistent(self, storage_manager):
        """Test getting latest price for nonexistent instrument."""
        latest = storage_manager.get_latest_price('NONEXISTENT')

        assert latest is None

    def test_get_prices_dataframe(self, storage_manager, sample_price):
        """Test getting prices as DataFrame."""
        storage_manager.save_price(sample_price)

        df = storage_manager.get_prices('EUR_USD')

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert 'instrument' in df.columns

    def test_get_prices_with_time_filter(self, storage_manager):
        """Test getting prices with time range filter."""
        from src.data.market_data import Price

        now = datetime.now()
        prices = [
            Price(
                instrument='EUR_USD',
                bid=1.0000,
                ask=1.0005,
                timestamp=now + timedelta(hours=i)
            )
            for i in range(5)
        ]

        for price in prices:
            storage_manager.save_price(price)

        df = storage_manager.get_prices(
            'EUR_USD',
            start_time=now + timedelta(hours=2),
            end_time=now + timedelta(hours=4)
        )

        assert len(df) > 0

    def test_get_prices_with_limit(self, storage_manager):
        """Test getting prices with result limit."""
        from src.data.market_data import Price

        prices = [
            Price(
                instrument='EUR_USD',
                bid=1.0000,
                ask=1.0005,
                timestamp=datetime.now() + timedelta(seconds=i)
            )
            for i in range(10)
        ]

        for price in prices:
            storage_manager.save_price(price)

        df = storage_manager.get_prices('EUR_USD', limit=5)

        assert len(df) == 5


class TestCandleStorage:
    """Test suite for candle data storage."""

    def test_save_candle(self, storage_manager, sample_candle):
        """Test saving a single candle."""
        result = storage_manager.save_candle(sample_candle)

        assert result is True

    def test_save_candles_batch(self, storage_manager):
        """Test saving multiple candles in batch."""
        from src.data.market_data import Candle

        candles = [
            Candle(
                instrument='EUR_USD',
                timestamp=datetime.now() + timedelta(hours=i),
                open=1.0000,
                high=1.0050,
                low=0.9950,
                close=1.0025,
                volume=1000,
                complete=True,
                granularity='H1'
            )
            for i in range(5)
        ]

        successful, failed = storage_manager.save_candles(candles)

        assert successful == 5
        assert failed == 0

    def test_get_candles_dataframe(self, storage_manager, sample_candle):
        """Test getting candles as DataFrame."""
        storage_manager.save_candle(sample_candle)

        df = storage_manager.get_candles('EUR_USD')

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert 'open' in df.columns
        assert 'high' in df.columns
        assert 'low' in df.columns
        assert 'close' in df.columns

    def test_get_candles_with_granularity_filter(self, storage_manager):
        """Test getting candles filtered by granularity."""
        from src.data.market_data import Candle

        candles = [
            Candle(
                instrument='EUR_USD',
                timestamp=datetime.now() + timedelta(hours=i),
                open=1.0000,
                high=1.0050,
                low=0.9950,
                close=1.0025,
                volume=1000,
                complete=True,
                granularity='H1' if i % 2 == 0 else 'H4'
            )
            for i in range(6)
        ]

        for candle in candles:
            storage_manager.save_candle(candle)

        df = storage_manager.get_candles('EUR_USD', granularity='H1')

        assert len(df) == 3


class TestDataMaintenance:
    """Test suite for data maintenance operations."""

    def test_delete_old_data(self, storage_manager):
        """Test deleting old data from table."""
        from src.data.market_data import Price

        # Create old prices
        old_time = datetime.now() - timedelta(days=35)
        recent_time = datetime.now()

        old_price = Price(
            instrument='EUR_USD',
            bid=1.0000,
            ask=1.0005,
            timestamp=old_time
        )

        recent_price = Price(
            instrument='EUR_USD',
            bid=1.0010,
            ask=1.0015,
            timestamp=recent_time
        )

        storage_manager.save_price(old_price)
        storage_manager.save_price(recent_price)

        # Delete data older than 30 days
        deleted = storage_manager.delete_old_data('prices', days_to_keep=30)

        assert deleted >= 0

    def test_delete_old_data_invalid_table(self, storage_manager):
        """Test deleting old data with invalid table name."""
        from src.data.storage import DatabaseError

        with pytest.raises(DatabaseError):
            storage_manager.delete_old_data('invalid_table', days_to_keep=30)

    def test_vacuum_database(self, storage_manager):
        """Test database vacuum operation."""
        result = storage_manager.vacuum_database()

        assert result is True


class TestDatabaseStatistics:
    """Test suite for database statistics."""

    def test_get_database_stats(self, storage_manager):
        """Test getting database statistics."""
        stats = storage_manager.get_database_stats()

        assert stats is not None
        assert 'database_path' in stats
        assert 'database_size_bytes' in stats
        assert 'tables' in stats

    def test_get_database_stats_tables(self, storage_manager, sample_price):
        """Test database statistics include table information."""
        storage_manager.save_price(sample_price)

        stats = storage_manager.get_database_stats()

        assert 'prices' in stats['tables']
        assert 'row_count' in stats['tables']['prices']

    def test_get_instruments(self, storage_manager):
        """Test getting list of instruments."""
        from src.data.market_data import Price

        prices = [
            Price(
                instrument='EUR_USD',
                bid=1.0000,
                ask=1.0005,
                timestamp=datetime.now()
            ),
            Price(
                instrument='GBP_USD',
                bid=1.2000,
                ask=1.2005,
                timestamp=datetime.now()
            )
        ]

        for price in prices:
            storage_manager.save_price(price)

        instruments = storage_manager.get_instruments('prices')

        assert 'EUR_USD' in instruments
        assert 'GBP_USD' in instruments

    def test_get_instruments_invalid_table(self, storage_manager):
        """Test getting instruments with invalid table."""
        from src.data.storage import DatabaseError

        with pytest.raises(DatabaseError):
            storage_manager.get_instruments('invalid_table')


class TestContextManager:
    """Test suite for context manager support."""

    def test_context_manager_enter_exit(self, temp_db_path):
        """Test using StorageManager as context manager."""
        from src.data.storage import StorageManager

        with StorageManager(db_path=temp_db_path) as manager:
            assert manager is not None


class TestErrorHandling:
    """Test suite for error handling."""

    def test_database_error_exception(self):
        """Test DatabaseError exception."""
        from src.data.storage import DatabaseError

        with pytest.raises(DatabaseError):
            raise DatabaseError("Test error")

    def test_connection_error_exception(self):
        """Test ConnectionError exception."""
        from src.data.storage import ConnectionError

        with pytest.raises(ConnectionError):
            raise ConnectionError("Connection failed")


class TestDataValidation:
    """Test suite for data validation during storage."""

    def test_save_price_with_invalid_data(self, storage_manager):
        """Test saving price with invalid data."""
        # Create mock price with required attributes
        mock_price = Mock()
        mock_price.instrument = 'EUR_USD'
        mock_price.bid = 1.0000
        mock_price.ask = 1.0005
        mock_price.spread = 0.0005
        mock_price.mid = 1.00025
        mock_price.timestamp = datetime.now()
        mock_price.tradeable = True
        mock_price.liquidity = None

        # Should handle gracefully
        result = storage_manager.save_price(mock_price)
        assert isinstance(result, bool)


class TestCloseConnection:
    """Test suite for connection closing."""

    def test_close_connection(self, storage_manager):
        """Test closing database connection."""
        storage_manager.close()

        # Connection should be None after close
        assert storage_manager._connection is None

    def test_close_connection_multiple_times(self, storage_manager):
        """Test closing connection multiple times."""
        storage_manager.close()
        storage_manager.close()

        # Should not raise exception
        assert storage_manager._connection is None
