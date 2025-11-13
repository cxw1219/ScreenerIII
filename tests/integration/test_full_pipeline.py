"""
Integration tests for full pipeline.

Tests end-to-end workflows including:
- Data fetching from OANDA
- Data analysis and signal generation
- Database persistence
- Display output
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
import sys
from pathlib import Path as PathlibPath
import tempfile
import os

# Add src directory to path
sys.path.insert(0, str(PathlibPath(__file__).parent.parent.parent / "src"))


@pytest.fixture
def temp_db_path():
    """Create temporary database for integration tests."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def mock_oanda_response():
    """Create mock OANDA API response."""
    return {
        'prices': [
            {
                'instrument': 'EUR_USD',
                'time': datetime.now().isoformat(),
                'bids': [{'price': '1.0000'}],
                'asks': [{'price': '1.0005'}],
                'closeoutBid': '1.0000',
                'closeoutAsk': '1.0005'
            }
        ]
    }


@pytest.fixture
def mock_candle_response():
    """Create mock candle data response."""
    now = datetime.now()
    return {
        'instrument': 'EUR_USD',
        'granularity': 'H1',
        'candles': [
            {
                'time': (now - timedelta(hours=i)).isoformat(),
                'mid': {
                    'o': str(1.0000 + i * 0.0001),
                    'h': str(1.0050 + i * 0.0001),
                    'l': str(0.9950 + i * 0.0001),
                    'c': str(1.0025 + i * 0.0001)
                },
                'volume': 1000,
                'complete': True
            }
            for i in range(100)
        ]
    }


class TestDataFetchingPipeline:
    """Test suite for data fetching pipeline."""

    @patch('src.data.oanda_client.API')
    def test_fetch_current_prices(self, mock_api, mock_oanda_response):
        """Test fetching current prices from OANDA."""
        from src.data.oanda_client import OANDAClient

        mock_api_instance = mock_api.return_value
        mock_api_instance.request = Mock(return_value=mock_oanda_response)

        client = OANDAClient(
            api_token='test_token',
            account_id='test_account'
        )

        response = client.get_current_prices('EUR_USD')

        assert response is not None
        assert 'prices' in response

    @patch('src.data.oanda_client.API')
    def test_fetch_candle_data(self, mock_api, mock_candle_response):
        """Test fetching historical candle data."""
        from src.data.oanda_client import OANDAClient

        mock_api_instance = mock_api.return_value
        mock_api_instance.request = Mock(return_value=mock_candle_response)

        client = OANDAClient(
            api_token='test_token',
            account_id='test_account'
        )

        response = client.get_candles('EUR_USD', granularity='H1', count=100)

        assert response is not None
        assert 'candles' in response
        assert len(response['candles']) > 0


class TestDataStoragePipeline:
    """Test suite for data storage pipeline."""

    def test_store_and_retrieve_prices(self, temp_db_path):
        """Test storing and retrieving price data."""
        from src.data.storage import StorageManager
        from src.data.market_data import Price

        manager = StorageManager(db_path=temp_db_path)

        # Create and store price
        price = Price(
            instrument='EUR_USD',
            bid=1.0000,
            ask=1.0005,
            timestamp=datetime.now()
        )

        result = manager.save_price(price)
        assert result is True

        # Retrieve price
        latest = manager.get_latest_price('EUR_USD')
        assert latest is not None
        assert latest['instrument'] == 'EUR_USD'

        manager.close()

    def test_store_and_retrieve_candles(self, temp_db_path):
        """Test storing and retrieving candle data."""
        from src.data.storage import StorageManager
        from src.data.market_data import Candle
        import pandas as pd

        manager = StorageManager(db_path=temp_db_path)

        # Create and store candles
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
            for i in range(10)
        ]

        successful, failed = manager.save_candles(candles)
        assert successful == 10
        assert failed == 0

        # Retrieve candles
        df = manager.get_candles('EUR_USD', granularity='H1')
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10

        manager.close()


class TestAnalysisPipeline:
    """Test suite for analysis pipeline."""

    def test_calculate_indicators_from_data(self, sample_ohlcv_data):
        """Test calculating technical indicators from OHLCV data."""
        # This tests that we can compute indicators on sample data
        import pandas as pd

        df = sample_ohlcv_data
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

        # Calculate simple moving average
        df['sma_20'] = df['close'].rolling(window=20).mean()

        assert 'sma_20' in df.columns
        assert not df['sma_20'].isna().all()


class TestDatabasePipeline:
    """Test suite for database pipeline with ORM models."""

    @patch('src.core.database.get_config')
    def test_create_market_data_record(self, mock_config, temp_db_path):
        """Test creating MarketData record in database."""
        from src.core.database import Database, MarketData

        mock_config.return_value = Mock(
            database_url=f'sqlite:///{temp_db_path}',
            database_echo=False,
            database_pool_size=5,
            database_max_overflow=10
        )

        db = Database()
        db.create_tables()

        # Create and save market data
        market_data = MarketData(
            instrument='EUR_USD',
            timeframe='H1',
            timestamp=datetime.now(),
            open=1.0000,
            high=1.0050,
            low=0.9950,
            close=1.0025,
            volume=1000
        )

        with db.session_scope() as session:
            session.add(market_data)

        # Retrieve
        with db.session_scope() as session:
            retrieved = session.query(MarketData).filter_by(instrument='EUR_USD').first()
            assert retrieved is not None
            assert retrieved.instrument == 'EUR_USD'

        db.close()

    @patch('src.core.database.get_config')
    def test_create_trading_signal_record(self, mock_config, temp_db_path):
        """Test creating TradingSignal record in database."""
        from src.core.database import Database, TradingSignal

        mock_config.return_value = Mock(
            database_url=f'sqlite:///{temp_db_path}',
            database_echo=False,
            database_pool_size=5,
            database_max_overflow=10
        )

        db = Database()
        db.create_tables()

        # Create and save trading signal
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

        with db.session_scope() as session:
            session.add(signal)

        # Retrieve
        with db.session_scope() as session:
            retrieved = session.query(TradingSignal).filter_by(instrument='EUR_USD').first()
            assert retrieved is not None
            assert retrieved.signal_type == 'BUY'
            assert retrieved.confidence == 0.85

        db.close()


class TestDisplayPipeline:
    """Test suite for display pipeline."""

    def test_format_and_display_market_data(self):
        """Test formatting and displaying market data."""
        from src.interface.display import TerminalDisplay

        display = TerminalDisplay()

        market_data = [
            {
                'symbol': 'EUR_USD',
                'price': 1.0050,
                'bid': 1.0048,
                'ask': 1.0052,
                'change_24h': 0.15,
                'signal': 'BUY',
                'direction': 'LONG',
                'target': 1.0100,
                'stop_loss': 1.0025,
                'risk_reward': 2.0,
                'atr': 0.0020,
                'volume': 150000,
                'confidence': 0.85
            }
        ]

        # Should not raise exception
        row = display.format_market_row(market_data[0])
        assert row is not None
        assert isinstance(row, str)


class TestEndToEndPipeline:
    """Test suite for complete end-to-end workflow."""

    @patch('src.data.oanda_client.API')
    @patch('src.core.database.get_config')
    def test_complete_workflow(self, mock_db_config, mock_api, temp_db_path, mock_candle_response):
        """Test complete workflow from data fetch to display."""
        from src.data.oanda_client import OANDAClient
        from src.core.database import Database, MarketData
        from src.interface.display import TerminalDisplay

        # Setup mocks
        mock_db_config.return_value = Mock(
            database_url=f'sqlite:///{temp_db_path}',
            database_echo=False,
            database_pool_size=5,
            database_max_overflow=10
        )

        mock_api_instance = mock_api.return_value
        mock_api_instance.request = Mock(return_value=mock_candle_response)

        # 1. Fetch data from OANDA
        client = OANDAClient(
            api_token='test_token',
            account_id='test_account'
        )

        candle_data = client.get_candles('EUR_USD', granularity='H1', count=100)
        assert candle_data is not None
        assert len(candle_data['candles']) > 0

        # 2. Store in database
        db = Database()
        db.create_tables()

        with db.session_scope() as session:
            for candle in candle_data['candles'][:5]:  # Just store first 5
                market_data = MarketData(
                    instrument='EUR_USD',
                    timeframe='H1',
                    timestamp=datetime.fromisoformat(candle['time'].replace('Z', '+00:00')),
                    open=float(candle['mid']['o']),
                    high=float(candle['mid']['h']),
                    low=float(candle['mid']['l']),
                    close=float(candle['mid']['c']),
                    volume=candle['volume']
                )
                session.add(market_data)

        # 3. Retrieve from database
        with db.session_scope() as session:
            retrieved = session.query(MarketData).filter_by(instrument='EUR_USD').all()
            assert len(retrieved) >= 5

        # 4. Format for display
        display = TerminalDisplay()

        display_data = {
            'symbol': 'EUR_USD',
            'price': 1.0025,
            'signal': 'BUY'
        }

        row = display.format_market_row(display_data)
        assert row is not None

        db.close()


class TestErrorRecovery:
    """Test suite for error recovery in pipeline."""

    @patch('src.data.oanda_client.API')
    def test_retry_on_transient_error(self, mock_api):
        """Test that pipeline retries on transient errors."""
        from src.data.oanda_client import OANDAClient
        from oandapyV20.exceptions import V20Error

        # First call fails, second succeeds
        error = V20Error(code=503)
        success = {'account': {'id': 'test'}}

        mock_api_instance = mock_api.return_value
        mock_api_instance.request = Mock(side_effect=[error, success])

        client = OANDAClient(
            api_token='test_token',
            account_id='test_account'
        )

        # Should succeed after retry
        response = client.get_account_summary()
        assert response is not None

    def test_database_error_handling(self, temp_db_path):
        """Test database error handling in pipeline."""
        from src.data.storage import StorageManager

        manager = StorageManager(db_path=temp_db_path)

        # Try to save invalid data
        invalid_price = Mock()
        invalid_price.instrument = None  # Invalid
        invalid_price.bid = 'invalid'
        invalid_price.ask = 'invalid'

        # Should handle gracefully
        result = manager.save_price(invalid_price)
        assert isinstance(result, bool)

        manager.close()


class TestDataValidationPipeline:
    """Test suite for data validation in pipeline."""

    def test_price_validation(self):
        """Test price data validation."""
        from src.data.market_data import Price, ValidationError

        # Valid price
        valid_price = Price(
            instrument='EUR_USD',
            bid=1.0000,
            ask=1.0005,
            timestamp=datetime.now()
        )
        assert valid_price.spread == 0.0005

        # Invalid price (ask < bid) should raise error
        with pytest.raises(ValidationError):
            invalid_price = Price(
                instrument='EUR_USD',
                bid=1.0005,
                ask=1.0000,
                timestamp=datetime.now()
            )


class TestPerformanceMetrics:
    """Test suite for performance metrics collection."""

    @patch('src.core.database.get_config')
    def test_screener_run_tracking(self, mock_config, temp_db_path):
        """Test tracking screener run metrics."""
        from src.core.database import Database, ScreenerRun

        mock_config.return_value = Mock(
            database_url=f'sqlite:///{temp_db_path}',
            database_echo=False,
            database_pool_size=5,
            database_max_overflow=10
        )

        db = Database()
        db.create_tables()

        # Create screener run record
        run = ScreenerRun(
            instruments_scanned=['EUR_USD', 'GBP_USD'],
            timeframes=['H1', 'H4'],
            strategies=['RSI', 'MACD'],
            signals_generated=5,
            patterns_detected=2,
            execution_time=1.5,
            success=True
        )

        with db.session_scope() as session:
            session.add(run)

        # Retrieve and verify
        with db.session_scope() as session:
            retrieved = session.query(ScreenerRun).first()
            assert retrieved is not None
            assert retrieved.signals_generated == 5
            assert retrieved.execution_time == 1.5

        db.close()
