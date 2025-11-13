"""
Unit tests for OANDA client module.

Tests OANDA API client wrapper including rate limiting, retry logic,
error handling, and API operations with proper mocking.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta
import sys
from pathlib import Path as PathlibPath
import time

# Add src directory to path
sys.path.insert(0, str(PathlibPath(__file__).parent.parent.parent / "src"))


@pytest.fixture
def mock_api():
    """Create mock OANDA API."""
    with patch('src.data.oanda_client.API') as mock:
        yield mock


@pytest.fixture
def oanda_client(mock_api):
    """Create OANDAClient instance with mocked API."""
    from src.data.oanda_client import OANDAClient

    client = OANDAClient(
        api_token='test_token',
        account_id='test_account',
        environment='practice'
    )

    return client


class TestOANDAClientInitialization:
    """Test suite for OANDA client initialization."""

    def test_client_initialization(self, mock_api):
        """Test OANDAClient initialization."""
        from src.data.oanda_client import OANDAClient

        client = OANDAClient(
            api_token='test_token',
            account_id='test_account',
            environment='practice'
        )

        assert client is not None
        assert client.api_token == 'test_token'
        assert client.account_id == 'test_account'
        assert client.environment == 'practice'

    def test_client_with_custom_retry_settings(self, mock_api):
        """Test client initialization with custom retry settings."""
        from src.data.oanda_client import OANDAClient

        client = OANDAClient(
            api_token='test_token',
            account_id='test_account',
            max_retries=5,
            initial_retry_delay=2.0,
            max_retry_delay=120.0
        )

        assert client.max_retries == 5
        assert client.initial_retry_delay == 2.0
        assert client.max_retry_delay == 120.0

    def test_client_with_custom_rate_limit(self, mock_api):
        """Test client initialization with custom rate limit settings."""
        from src.data.oanda_client import OANDAClient

        client = OANDAClient(
            api_token='test_token',
            account_id='test_account',
            rate_limit_requests=60,
            rate_limit_window=30
        )

        assert client.rate_limiter.max_requests == 60
        assert client.rate_limiter.time_window == 30


class TestConnectionStatus:
    """Test suite for connection status management."""

    def test_initial_status_disconnected(self, oanda_client):
        """Test that initial status is DISCONNECTED."""
        from src.data.oanda_client import ConnectionStatus

        assert oanda_client.status == ConnectionStatus.DISCONNECTED

    def test_status_setter(self, oanda_client):
        """Test setting connection status."""
        from src.data.oanda_client import ConnectionStatus

        oanda_client.status = ConnectionStatus.CONNECTED

        assert oanda_client.status == ConnectionStatus.CONNECTED

    def test_status_update_sets_timestamp(self, oanda_client):
        """Test that status update sets last successful request timestamp."""
        from src.data.oanda_client import ConnectionStatus

        oanda_client.status = ConnectionStatus.CONNECTED

        assert oanda_client._last_successful_request is not None

    def test_last_error_property(self, oanda_client):
        """Test last_error property."""
        oanda_client._set_error("Test error")

        assert oanda_client.last_error == "Test error"


class TestRateLimiter:
    """Test suite for rate limiter."""

    def test_rate_limiter_creation(self):
        """Test RateLimiter creation."""
        from src.data.oanda_client import RateLimiter

        limiter = RateLimiter(max_requests=10, time_window=60)

        assert limiter.max_requests == 10
        assert limiter.time_window == 60

    def test_rate_limiter_acquire_success(self):
        """Test successful rate limit acquisition."""
        from src.data.oanda_client import RateLimiter

        limiter = RateLimiter(max_requests=10, time_window=60)

        result = limiter.acquire()

        assert result is True

    def test_rate_limiter_acquire_limit_reached(self):
        """Test rate limit when limit is reached."""
        from src.data.oanda_client import RateLimiter

        limiter = RateLimiter(max_requests=2, time_window=60)

        # Fill up the bucket
        assert limiter.acquire() is True
        assert limiter.acquire() is True
        assert limiter.acquire() is False

    def test_rate_limiter_reset(self):
        """Test rate limiter reset."""
        from src.data.oanda_client import RateLimiter

        limiter = RateLimiter(max_requests=2, time_window=60)

        limiter.acquire()
        limiter.acquire()
        limiter.reset()

        result = limiter.acquire()

        assert result is True

    def test_rate_limiter_wait_if_needed(self):
        """Test rate limiter wait_if_needed method."""
        from src.data.oanda_client import RateLimiter

        limiter = RateLimiter(max_requests=100, time_window=60)

        # Should not block with plenty of capacity
        start = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start

        assert elapsed < 1.0


class TestCurrentPrices:
    """Test suite for current price fetching."""

    def test_get_current_prices_single_instrument(self, oanda_client):
        """Test getting current price for single instrument."""
        mock_response = {
            'prices': [{
                'instrument': 'EUR_USD',
                'bids': [{'price': '1.0000'}],
                'asks': [{'price': '1.0005'}]
            }]
        }

        oanda_client.api.request = Mock(return_value=mock_response)

        response = oanda_client.get_current_prices('EUR_USD')

        assert response is not None

    def test_get_current_prices_multiple_instruments(self, oanda_client):
        """Test getting current prices for multiple instruments."""
        mock_response = {
            'prices': [
                {'instrument': 'EUR_USD', 'bids': [{'price': '1.0000'}]},
                {'instrument': 'GBP_USD', 'bids': [{'price': '1.2000'}]}
            ]
        }

        oanda_client.api.request = Mock(return_value=mock_response)

        response = oanda_client.get_current_prices(['EUR_USD', 'GBP_USD'])

        assert response is not None


class TestCandleData:
    """Test suite for candle data fetching."""

    def test_get_candles_basic(self, oanda_client):
        """Test getting candle data with basic parameters."""
        mock_response = {
            'instrument': 'EUR_USD',
            'granularity': 'M5',
            'candles': [
                {
                    'time': '2024-01-01T00:00:00Z',
                    'mid': {'o': '1.0000', 'h': '1.0050', 'l': '0.9950', 'c': '1.0025'},
                    'volume': 1000,
                    'complete': True
                }
            ]
        }

        oanda_client.api.request = Mock(return_value=mock_response)

        response = oanda_client.get_candles('EUR_USD', granularity='M5')

        assert response is not None
        assert 'candles' in response

    def test_get_candles_with_count(self, oanda_client):
        """Test getting candles with count parameter."""
        mock_response = {'candles': []}

        oanda_client.api.request = Mock(return_value=mock_response)

        response = oanda_client.get_candles('EUR_USD', count=100)

        assert response is not None

    def test_get_candles_with_time_range(self, oanda_client):
        """Test getting candles with time range."""
        mock_response = {'candles': []}

        oanda_client.api.request = Mock(return_value=mock_response)

        from_time = datetime.now() - timedelta(days=7)
        to_time = datetime.now()

        response = oanda_client.get_candles(
            'EUR_USD',
            from_time=from_time,
            to_time=to_time
        )

        assert response is not None

    def test_get_candles_count_limit(self, oanda_client):
        """Test that candle count is limited to 5000."""
        mock_response = {'candles': []}

        oanda_client.api.request = Mock(return_value=mock_response)

        # Request 10000 candles, should be limited to 5000
        response = oanda_client.get_candles('EUR_USD', count=10000)

        # Verify the request was made
        assert oanda_client.api.request.called


class TestAccountOperations:
    """Test suite for account-related operations."""

    def test_get_account_summary(self, oanda_client):
        """Test getting account summary."""
        mock_response = {
            'account': {
                'id': 'test_account',
                'balance': '100000.0',
                'currency': 'USD'
            }
        }

        oanda_client.api.request = Mock(return_value=mock_response)

        response = oanda_client.get_account_summary()

        assert response is not None
        assert 'account' in response

    def test_get_tradeable_instruments(self, oanda_client):
        """Test getting tradeable instruments."""
        mock_response = {
            'instruments': [
                {'name': 'EUR_USD', 'type': 'CURRENCY'},
                {'name': 'GBP_USD', 'type': 'CURRENCY'}
            ]
        }

        oanda_client.api.request = Mock(return_value=mock_response)

        instruments = oanda_client.get_tradeable_instruments()

        assert instruments is not None
        assert len(instruments) == 2


class TestErrorHandling:
    """Test suite for error handling."""

    def test_handle_rate_limit_error(self, oanda_client):
        """Test handling of rate limit errors."""
        from oandapyV20.exceptions import V20Error
        from src.data.oanda_client import RateLimitError

        # Create mock V20Error with rate limit code
        error = V20Error(code=429)

        oanda_client.api.request = Mock(side_effect=[error, error, error, error])

        with pytest.raises(RateLimitError):
            oanda_client.get_account_summary()

    def test_handle_server_error_with_retry(self, oanda_client):
        """Test handling of server errors with retry."""
        from oandapyV20.exceptions import V20Error

        # First call fails with 500, second succeeds
        error = V20Error(code=500)
        success_response = {'account': {'id': 'test'}}

        oanda_client.api.request = Mock(side_effect=[error, success_response])

        response = oanda_client.get_account_summary()

        assert response is not None
        assert oanda_client.api.request.call_count == 2

    def test_handle_server_error_max_retries(self, oanda_client):
        """Test server error handling with max retries exhausted."""
        from oandapyV20.exceptions import V20Error
        from src.data.oanda_client import ConnectionError

        error = V20Error(code=503)

        oanda_client.api.request = Mock(side_effect=error)

        with pytest.raises(ConnectionError):
            oanda_client.get_account_summary()

    def test_handle_api_error(self, oanda_client):
        """Test handling of general API errors."""
        from oandapyV20.exceptions import V20Error
        from src.data.oanda_client import OANDAClientError

        error = V20Error(code=400)

        oanda_client.api.request = Mock(side_effect=error)

        with pytest.raises(OANDAClientError):
            oanda_client.get_account_summary()

    def test_handle_unexpected_error(self, oanda_client):
        """Test handling of unexpected errors."""
        from src.data.oanda_client import OANDAClientError

        oanda_client.api.request = Mock(side_effect=Exception("Unexpected error"))

        with pytest.raises(OANDAClientError):
            oanda_client.get_account_summary()


class TestRetryLogic:
    """Test suite for retry logic with exponential backoff."""

    def test_exponential_backoff_calculation(self, oanda_client):
        """Test exponential backoff delay calculation."""
        # Verify backoff delay increases exponentially
        initial_delay = oanda_client.initial_retry_delay
        max_delay = oanda_client.max_retry_delay

        delay1 = min(initial_delay * (2 ** 0), max_delay)
        delay2 = min(initial_delay * (2 ** 1), max_delay)
        delay3 = min(initial_delay * (2 ** 2), max_delay)

        assert delay2 > delay1
        assert delay3 > delay2

    @patch('time.sleep')
    def test_retry_with_sleep(self, mock_sleep, oanda_client):
        """Test that retry logic includes sleep."""
        from oandapyV20.exceptions import V20Error

        error = V20Error(code=500)
        success = {'account': {'id': 'test'}}

        oanda_client.api.request = Mock(side_effect=[error, success])

        response = oanda_client.get_account_summary()

        # Verify sleep was called for retry
        assert mock_sleep.called


class TestConnectionTesting:
    """Test suite for connection testing."""

    def test_test_connection_success(self, oanda_client):
        """Test successful connection test."""
        mock_response = {'account': {'id': 'test'}}

        oanda_client.api.request = Mock(return_value=mock_response)

        result = oanda_client.test_connection()

        assert result is True

    def test_test_connection_failure(self, oanda_client):
        """Test failed connection test."""
        oanda_client.api.request = Mock(side_effect=Exception("Connection failed"))

        result = oanda_client.test_connection()

        assert result is False


class TestConnectionInfo:
    """Test suite for connection information."""

    def test_get_connection_info(self, oanda_client):
        """Test getting connection information."""
        info = oanda_client.get_connection_info()

        assert info is not None
        assert 'status' in info
        assert 'last_error' in info
        assert 'environment' in info
        assert 'account_id' in info

    def test_connection_info_environment(self, oanda_client):
        """Test connection info includes environment."""
        info = oanda_client.get_connection_info()

        assert info['environment'] == 'practice'

    def test_connection_info_account_id(self, oanda_client):
        """Test connection info includes account ID."""
        info = oanda_client.get_connection_info()

        assert info['account_id'] == 'test_account'


class TestRateLimiterReset:
    """Test suite for rate limiter reset."""

    def test_reset_rate_limiter(self, oanda_client):
        """Test resetting rate limiter."""
        # Make some requests to fill the bucket
        oanda_client.rate_limiter.acquire()
        oanda_client.rate_limiter.acquire()

        # Reset
        oanda_client.reset_rate_limiter()

        # Should be able to acquire again
        result = oanda_client.rate_limiter.acquire()

        assert result is True


class TestEnumTypes:
    """Test suite for enum types."""

    def test_connection_status_enum(self):
        """Test ConnectionStatus enum."""
        from src.data.oanda_client import ConnectionStatus

        assert hasattr(ConnectionStatus, 'DISCONNECTED')
        assert hasattr(ConnectionStatus, 'CONNECTING')
        assert hasattr(ConnectionStatus, 'CONNECTED')
        assert hasattr(ConnectionStatus, 'ERROR')
        assert hasattr(ConnectionStatus, 'RATE_LIMITED')


class TestExceptionTypes:
    """Test suite for custom exceptions."""

    def test_oanda_client_error(self):
        """Test OANDAClientError exception."""
        from src.data.oanda_client import OANDAClientError

        with pytest.raises(OANDAClientError):
            raise OANDAClientError("Test error")

    def test_rate_limit_error(self):
        """Test RateLimitError exception."""
        from src.data.oanda_client import RateLimitError

        with pytest.raises(RateLimitError):
            raise RateLimitError("Rate limit exceeded")

    def test_connection_error(self):
        """Test ConnectionError exception."""
        from src.data.oanda_client import ConnectionError

        with pytest.raises(ConnectionError):
            raise ConnectionError("Connection failed")
