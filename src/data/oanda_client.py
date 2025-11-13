"""
OANDA API Client Wrapper

This module provides a comprehensive wrapper for the OANDA API using oandapyV20,
with features including rate limiting, error handling, retry logic with exponential
backoff, and connection status management.
"""

import time
import logging
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
from enum import Enum
import threading

from oandapyV20 import API
from oandapyV20.exceptions import V20Error
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.accounts as accounts


logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """Connection status states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"


class OANDAClientError(Exception):
    """Base exception for OANDA client errors."""
    pass


class RateLimitError(OANDAClientError):
    """Raised when rate limit is exceeded."""
    pass


class ConnectionError(OANDAClientError):
    """Raised when connection fails."""
    pass


class RateLimiter:
    """
    Rate limiter with token bucket algorithm.

    Attributes:
        max_requests: Maximum number of requests allowed in the time window
        time_window: Time window in seconds
    """

    def __init__(self, max_requests: int = 120, time_window: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests per time window (default: 120)
            time_window: Time window in seconds (default: 60)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: List[float] = []
        self._lock = threading.Lock()

    def acquire(self) -> bool:
        """
        Attempt to acquire permission for a request.

        Returns:
            True if request is allowed, False otherwise
        """
        with self._lock:
            now = time.time()
            # Remove requests older than the time window
            self.requests = [req_time for req_time in self.requests
                           if now - req_time < self.time_window]

            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            return False

    def wait_if_needed(self) -> None:
        """Wait if rate limit is reached."""
        while not self.acquire():
            time.sleep(0.1)

    def reset(self) -> None:
        """Reset the rate limiter."""
        with self._lock:
            self.requests.clear()


class OANDAClient:
    """
    OANDA API client wrapper with advanced features.

    Features:
    - Rate limiting
    - Automatic retry with exponential backoff
    - Connection status management
    - Comprehensive error handling
    - Real-time and historical data fetching
    """

    def __init__(
        self,
        api_token: str,
        account_id: str,
        environment: str = "practice",
        max_retries: int = 3,
        initial_retry_delay: float = 1.0,
        max_retry_delay: float = 60.0,
        rate_limit_requests: int = 120,
        rate_limit_window: int = 60
    ):
        """
        Initialize OANDA client.

        Args:
            api_token: OANDA API token
            account_id: OANDA account ID
            environment: "practice" or "live" (default: "practice")
            max_retries: Maximum number of retry attempts (default: 3)
            initial_retry_delay: Initial delay in seconds for retries (default: 1.0)
            max_retry_delay: Maximum delay in seconds for retries (default: 60.0)
            rate_limit_requests: Max requests per rate limit window (default: 120)
            rate_limit_window: Rate limit window in seconds (default: 60)
        """
        self.api_token = api_token
        self.account_id = account_id
        self.environment = environment
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.max_retry_delay = max_retry_delay

        # Initialize API client
        self.api = API(access_token=api_token, environment=environment)

        # Rate limiter
        self.rate_limiter = RateLimiter(
            max_requests=rate_limit_requests,
            time_window=rate_limit_window
        )

        # Connection status
        self._status = ConnectionStatus.DISCONNECTED
        self._last_error: Optional[str] = None
        self._last_successful_request: Optional[datetime] = None
        self._status_lock = threading.Lock()

        logger.info(
            f"OANDA client initialized for {environment} environment"
        )

    @property
    def status(self) -> ConnectionStatus:
        """Get current connection status."""
        with self._status_lock:
            return self._status

    @status.setter
    def status(self, value: ConnectionStatus) -> None:
        """Set connection status."""
        with self._status_lock:
            self._status = value
            if value == ConnectionStatus.CONNECTED:
                self._last_successful_request = datetime.now()
            logger.debug(f"Connection status changed to: {value.value}")

    @property
    def last_error(self) -> Optional[str]:
        """Get last error message."""
        with self._status_lock:
            return self._last_error

    def _set_error(self, error: str) -> None:
        """Set error message and update status."""
        with self._status_lock:
            self._last_error = error
            self.status = ConnectionStatus.ERROR

    def _execute_request(
        self,
        endpoint: Any,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Execute API request with retry logic and exponential backoff.

        Args:
            endpoint: OANDA API endpoint object
            retry_count: Current retry attempt number

        Returns:
            Response data dictionary

        Raises:
            RateLimitError: If rate limit is exceeded
            ConnectionError: If connection fails after retries
            OANDAClientError: For other API errors
        """
        # Wait for rate limiter
        self.rate_limiter.wait_if_needed()

        try:
            self.status = ConnectionStatus.CONNECTING
            response = self.api.request(endpoint)
            self.status = ConnectionStatus.CONNECTED
            return response

        except V20Error as e:
            error_code = getattr(e, 'code', None)
            error_msg = str(e)

            # Handle rate limiting
            if error_code == 429 or 'rate limit' in error_msg.lower():
                self.status = ConnectionStatus.RATE_LIMITED
                logger.warning("Rate limit exceeded, waiting before retry")

                if retry_count < self.max_retries:
                    delay = min(
                        self.initial_retry_delay * (2 ** retry_count),
                        self.max_retry_delay
                    )
                    time.sleep(delay)
                    return self._execute_request(endpoint, retry_count + 1)
                else:
                    raise RateLimitError(
                        f"Rate limit exceeded after {retry_count} retries"
                    )

            # Handle connection errors
            elif error_code in [500, 502, 503, 504]:
                logger.warning(
                    f"Server error {error_code}, attempt {retry_count + 1}"
                )

                if retry_count < self.max_retries:
                    delay = min(
                        self.initial_retry_delay * (2 ** retry_count),
                        self.max_retry_delay
                    )
                    time.sleep(delay)
                    return self._execute_request(endpoint, retry_count + 1)
                else:
                    self._set_error(f"Server error after {retry_count} retries")
                    raise ConnectionError(
                        f"Connection failed after {retry_count} retries: {error_msg}"
                    )

            # Handle other errors
            else:
                self._set_error(f"API error: {error_msg}")
                raise OANDAClientError(f"OANDA API error: {error_msg}")

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self._set_error(error_msg)

            if retry_count < self.max_retries:
                delay = min(
                    self.initial_retry_delay * (2 ** retry_count),
                    self.max_retry_delay
                )
                logger.warning(f"Retrying after error: {error_msg}")
                time.sleep(delay)
                return self._execute_request(endpoint, retry_count + 1)
            else:
                raise OANDAClientError(error_msg)

    def get_current_prices(
        self,
        instruments: Union[str, List[str]],
        include_unitsavailable: bool = False
    ) -> Dict[str, Any]:
        """
        Get current real-time prices for specified instruments.

        Args:
            instruments: Single instrument or list of instruments (e.g., "EUR_USD")
            include_unitsavailable: Include units available in response

        Returns:
            Dictionary containing pricing information

        Raises:
            OANDAClientError: If request fails
        """
        if isinstance(instruments, list):
            instruments_str = ",".join(instruments)
        else:
            instruments_str = instruments

        params = {
            "instruments": instruments_str,
            "includeUnitsAvailable": include_unitsavailable
        }

        endpoint = pricing.PricingInfo(
            accountID=self.account_id,
            params=params
        )

        try:
            response = self._execute_request(endpoint)
            logger.debug(f"Fetched prices for {instruments_str}")
            return response
        except Exception as e:
            logger.error(f"Failed to fetch prices for {instruments_str}: {e}")
            raise

    def get_candles(
        self,
        instrument: str,
        granularity: str = "M5",
        count: Optional[int] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        price: str = "M"
    ) -> Dict[str, Any]:
        """
        Get historical candle data for an instrument.

        Args:
            instrument: Instrument name (e.g., "EUR_USD")
            granularity: Candle granularity (S5, S10, S15, S30, M1, M2, M4, M5,
                        M10, M15, M30, H1, H2, H3, H4, H6, H8, H12, D, W, M)
            count: Number of candles to return (max 5000)
            from_time: Start time for candles
            to_time: End time for candles
            price: Price type - M (midpoint), B (bid), A (ask)

        Returns:
            Dictionary containing candle data

        Raises:
            OANDAClientError: If request fails
        """
        params = {
            "granularity": granularity,
            "price": price
        }

        if count is not None:
            params["count"] = min(count, 5000)

        if from_time is not None:
            params["from"] = from_time.strftime("%Y-%m-%dT%H:%M:%S.000000000Z")

        if to_time is not None:
            params["to"] = to_time.strftime("%Y-%m-%dT%H:%M:%S.000000000Z")

        endpoint = instruments.InstrumentsCandles(
            instrument=instrument,
            params=params
        )

        try:
            response = self._execute_request(endpoint)
            logger.debug(
                f"Fetched {len(response.get('candles', []))} candles "
                f"for {instrument}"
            )
            return response
        except Exception as e:
            logger.error(f"Failed to fetch candles for {instrument}: {e}")
            raise

    def get_account_summary(self) -> Dict[str, Any]:
        """
        Get account summary information.

        Returns:
            Dictionary containing account summary

        Raises:
            OANDAClientError: If request fails
        """
        endpoint = accounts.AccountSummary(accountID=self.account_id)

        try:
            response = self._execute_request(endpoint)
            logger.debug("Fetched account summary")
            return response
        except Exception as e:
            logger.error(f"Failed to fetch account summary: {e}")
            raise

    def get_tradeable_instruments(self) -> List[Dict[str, Any]]:
        """
        Get list of tradeable instruments for the account.

        Returns:
            List of instrument dictionaries

        Raises:
            OANDAClientError: If request fails
        """
        endpoint = accounts.AccountInstruments(accountID=self.account_id)

        try:
            response = self._execute_request(endpoint)
            instruments_list = response.get("instruments", [])
            logger.debug(f"Fetched {len(instruments_list)} tradeable instruments")
            return instruments_list
        except Exception as e:
            logger.error(f"Failed to fetch tradeable instruments: {e}")
            raise

    def test_connection(self) -> bool:
        """
        Test connection to OANDA API.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.get_account_summary()
            logger.info("Connection test successful")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get connection status information.

        Returns:
            Dictionary with connection information
        """
        return {
            "status": self.status.value,
            "last_error": self.last_error,
            "last_successful_request": self._last_successful_request,
            "environment": self.environment,
            "account_id": self.account_id
        }

    def reset_rate_limiter(self) -> None:
        """Reset the rate limiter."""
        self.rate_limiter.reset()
        logger.info("Rate limiter reset")
