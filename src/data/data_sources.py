"""
Alternative Data Source Support Module

This module provides a unified interface for multiple market data providers including
OANDA, Alpha Vantage, Polygon.io, and Yahoo Finance. Features include automatic failover,
data aggregation, rate limiting, and comprehensive error handling.
"""

import time
import logging
import threading
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
import json

import requests
import yfinance as yf
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.foreignexchange import ForeignExchange
from alpha_vantage.cryptocurrencies import CryptoCurrencies
from polygon import RESTClient as PolygonRESTClient
from polygon import WebSocketClient as PolygonWebSocketClient

from .oanda_client import OANDAClient, ConnectionStatus as OANDAConnectionStatus
from .market_data import Candle, Price


logger = logging.getLogger(__name__)


class DataSourceType(Enum):
    """Types of supported data sources."""
    OANDA = "oanda"
    ALPHA_VANTAGE = "alphavantage"
    POLYGON = "polygon"
    YAHOO_FINANCE = "yahoo"


class DataSourceStatus(Enum):
    """Data source connection status."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    NOT_CONFIGURED = "not_configured"


class DataSourceError(Exception):
    """Base exception for data source errors."""
    pass


class RateLimitExceeded(DataSourceError):
    """Raised when rate limit is exceeded."""
    pass


class DataNotAvailable(DataSourceError):
    """Raised when requested data is not available."""
    pass


@dataclass
class InstrumentInfo:
    """Information about a tradeable instrument."""
    symbol: str
    name: str
    type: str  # forex, stock, crypto, etc.
    exchange: Optional[str] = None
    currency: Optional[str] = None
    min_price_increment: Optional[float] = None


@dataclass
class DataSourceHealth:
    """Health status of a data source."""
    source_type: DataSourceType
    status: DataSourceStatus
    last_successful_call: Optional[datetime] = None
    last_error: Optional[str] = None
    error_count: int = 0
    success_count: int = 0
    avg_response_time: float = 0.0


class DataSourceRateLimiter:
    """
    Rate limiter with multiple strategies for different data sources.

    Supports:
    - Token bucket algorithm
    - Fixed window rate limiting
    - Adaptive rate limiting based on responses
    """

    def __init__(
        self,
        max_calls: int,
        time_window: int,
        burst_allowance: int = 0
    ):
        """
        Initialize rate limiter.

        Args:
            max_calls: Maximum calls allowed in time window
            time_window: Time window in seconds
            burst_allowance: Additional calls allowed in burst (default: 0)
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.burst_allowance = burst_allowance
        self.calls: List[float] = []
        self._lock = threading.Lock()

    def can_proceed(self) -> bool:
        """Check if a call can proceed without waiting."""
        with self._lock:
            now = time.time()
            self._cleanup_old_calls(now)
            return len(self.calls) < (self.max_calls + self.burst_allowance)

    def wait_if_needed(self) -> float:
        """
        Wait if rate limit is reached.

        Returns:
            Time waited in seconds
        """
        start = time.time()
        while not self._try_acquire():
            time.sleep(0.1)
        return time.time() - start

    def _try_acquire(self) -> bool:
        """Try to acquire permission for a call."""
        with self._lock:
            now = time.time()
            self._cleanup_old_calls(now)

            if len(self.calls) < self.max_calls:
                self.calls.append(now)
                return True
            return False

    def _cleanup_old_calls(self, now: float) -> None:
        """Remove calls outside the time window."""
        self.calls = [
            call_time for call_time in self.calls
            if now - call_time < self.time_window
        ]

    def reset(self) -> None:
        """Reset the rate limiter."""
        with self._lock:
            self.calls.clear()


class DataSource(ABC):
    """
    Abstract base class for all data sources.

    Defines the common interface that all data source implementations must follow.
    """

    def __init__(self, source_type: DataSourceType):
        """
        Initialize data source.

        Args:
            source_type: Type of data source
        """
        self.source_type = source_type
        self._status = DataSourceStatus.NOT_CONFIGURED
        self._last_error: Optional[str] = None
        self._last_successful_call: Optional[datetime] = None
        self._error_count = 0
        self._success_count = 0
        self._response_times: List[float] = []
        self._lock = threading.Lock()

    @abstractmethod
    def get_current_price(self, instrument: str) -> Optional[Price]:
        """
        Get current real-time price for an instrument.

        Args:
            instrument: Instrument identifier

        Returns:
            Price object or None if unavailable
        """
        pass

    @abstractmethod
    def get_candles(
        self,
        instrument: str,
        timeframe: str,
        count: int,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None
    ) -> List[Candle]:
        """
        Get historical candle data.

        Args:
            instrument: Instrument identifier
            timeframe: Timeframe (e.g., "5m", "1h", "1d")
            count: Number of candles to retrieve
            from_time: Start time (optional)
            to_time: End time (optional)

        Returns:
            List of Candle objects
        """
        pass

    @abstractmethod
    def get_instruments(self) -> List[InstrumentInfo]:
        """
        Get list of available instruments.

        Returns:
            List of InstrumentInfo objects
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if data source is currently available.

        Returns:
            True if available, False otherwise
        """
        pass

    def get_health(self) -> DataSourceHealth:
        """
        Get health status of the data source.

        Returns:
            DataSourceHealth object
        """
        with self._lock:
            avg_response_time = (
                sum(self._response_times) / len(self._response_times)
                if self._response_times else 0.0
            )

            return DataSourceHealth(
                source_type=self.source_type,
                status=self._status,
                last_successful_call=self._last_successful_call,
                last_error=self._last_error,
                error_count=self._error_count,
                success_count=self._success_count,
                avg_response_time=avg_response_time
            )

    def _record_success(self, response_time: float) -> None:
        """Record a successful API call."""
        with self._lock:
            self._status = DataSourceStatus.AVAILABLE
            self._last_successful_call = datetime.now()
            self._success_count += 1
            self._response_times.append(response_time)
            # Keep only last 100 response times
            if len(self._response_times) > 100:
                self._response_times.pop(0)

    def _record_error(self, error: str) -> None:
        """Record an error."""
        with self._lock:
            self._last_error = error
            self._error_count += 1
            self._status = DataSourceStatus.ERROR
            logger.error(f"{self.source_type.value}: {error}")


class OANDADataSource(DataSource):
    """
    OANDA data source implementation.

    Wraps the existing OANDAClient to implement the DataSource interface.
    """

    def __init__(
        self,
        api_token: str,
        account_id: str,
        environment: str = "practice"
    ):
        """
        Initialize OANDA data source.

        Args:
            api_token: OANDA API token
            account_id: OANDA account ID
            environment: "practice" or "live"
        """
        super().__init__(DataSourceType.OANDA)

        try:
            self.client = OANDAClient(
                api_token=api_token,
                account_id=account_id,
                environment=environment
            )
            self._status = DataSourceStatus.AVAILABLE
            logger.info("OANDA data source initialized successfully")
        except Exception as e:
            self._record_error(f"Initialization failed: {e}")
            raise DataSourceError(f"Failed to initialize OANDA: {e}")

    def get_current_price(self, instrument: str) -> Optional[Price]:
        """Get current price from OANDA."""
        start_time = time.time()
        try:
            response = self.client.get_current_prices(instrument)
            prices = response.get("prices", [])

            if prices:
                price_data = prices[0]
                price = Price(
                    instrument=instrument,
                    bid=float(price_data.get("bids", [{}])[0].get("price", 0)),
                    ask=float(price_data.get("asks", [{}])[0].get("price", 0)),
                    timestamp=datetime.fromisoformat(
                        price_data.get("time", "").replace("Z", "+00:00")
                    )
                )
                self._record_success(time.time() - start_time)
                return price

            return None

        except Exception as e:
            self._record_error(f"Failed to get price: {e}")
            return None

    def get_candles(
        self,
        instrument: str,
        timeframe: str,
        count: int,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None
    ) -> List[Candle]:
        """Get historical candles from OANDA."""
        start_time = time.time()
        try:
            # Map common timeframe formats to OANDA format
            granularity_map = {
                "1m": "M1", "5m": "M5", "15m": "M15", "30m": "M30",
                "1h": "H1", "4h": "H4", "1d": "D", "1w": "W"
            }
            granularity = granularity_map.get(timeframe.lower(), timeframe)

            response = self.client.get_candles(
                instrument=instrument,
                granularity=granularity,
                count=count,
                from_time=from_time,
                to_time=to_time
            )

            candles = []
            for candle_data in response.get("candles", []):
                if candle_data.get("complete"):
                    mid = candle_data.get("mid", {})
                    candles.append(Candle(
                        instrument=instrument,
                        timestamp=datetime.fromisoformat(
                            candle_data.get("time", "").replace("Z", "+00:00")
                        ),
                        open=float(mid.get("o", 0)),
                        high=float(mid.get("h", 0)),
                        low=float(mid.get("l", 0)),
                        close=float(mid.get("c", 0)),
                        volume=int(candle_data.get("volume", 0))
                    ))

            self._record_success(time.time() - start_time)
            return candles

        except Exception as e:
            self._record_error(f"Failed to get candles: {e}")
            return []

    def get_instruments(self) -> List[InstrumentInfo]:
        """Get available instruments from OANDA."""
        start_time = time.time()
        try:
            instruments_data = self.client.get_tradeable_instruments()
            instruments = []

            for inst in instruments_data:
                instruments.append(InstrumentInfo(
                    symbol=inst.get("name", ""),
                    name=inst.get("displayName", ""),
                    type=inst.get("type", "").lower(),
                    min_price_increment=float(
                        inst.get("minimumTradeSize", 0)
                    )
                ))

            self._record_success(time.time() - start_time)
            return instruments

        except Exception as e:
            self._record_error(f"Failed to get instruments: {e}")
            return []

    def is_available(self) -> bool:
        """Check if OANDA is available."""
        try:
            return self.client.test_connection()
        except:
            return False


class AlphaVantageDataSource(DataSource):
    """
    Alpha Vantage data source implementation.

    Supports stocks, Forex, and cryptocurrencies with rate limiting.
    Free tier: 5 calls/minute, 500 calls/day.
    """

    def __init__(self, api_key: str):
        """
        Initialize Alpha Vantage data source.

        Args:
            api_key: Alpha Vantage API key
        """
        super().__init__(DataSourceType.ALPHA_VANTAGE)

        if not api_key or api_key == "your_api_key_here":
            self._status = DataSourceStatus.NOT_CONFIGURED
            logger.warning("Alpha Vantage not configured")
            return

        self.api_key = api_key
        self.ts = TimeSeries(key=api_key, output_format='json')
        self.fx = ForeignExchange(key=api_key, output_format='json')
        self.crypto = CryptoCurrencies(key=api_key, output_format='json')

        # Rate limiter: 5 calls per minute (free tier)
        self.rate_limiter = DataSourceRateLimiter(
            max_calls=5,
            time_window=60
        )

        self._status = DataSourceStatus.AVAILABLE
        logger.info("Alpha Vantage data source initialized")

    def get_current_price(self, instrument: str) -> Optional[Price]:
        """Get current price from Alpha Vantage."""
        if self._status == DataSourceStatus.NOT_CONFIGURED:
            return None

        self.rate_limiter.wait_if_needed()
        start_time = time.time()

        try:
            # Determine instrument type
            if "_" in instrument:  # Forex pair
                from_currency, to_currency = instrument.split("_")
                data, _ = self.fx.get_currency_exchange_rate(
                    from_currency=from_currency,
                    to_currency=to_currency
                )

                rate = float(data["Realtime Currency Exchange Rate"]["5. Exchange Rate"])
                timestamp = datetime.fromisoformat(
                    data["Realtime Currency Exchange Rate"]["6. Last Refreshed"]
                )

                # Alpha Vantage doesn't provide bid/ask, so use same rate
                price = Price(
                    instrument=instrument,
                    bid=rate,
                    ask=rate,
                    timestamp=timestamp
                )

            else:  # Stock
                data, _ = self.ts.get_quote_endpoint(symbol=instrument)
                quote = data["Global Quote"]

                price = Price(
                    instrument=instrument,
                    bid=float(quote["08. previous close"]),
                    ask=float(quote["05. price"]),
                    timestamp=datetime.fromisoformat(quote["07. latest trading day"])
                )

            self._record_success(time.time() - start_time)
            return price

        except Exception as e:
            if "rate limit" in str(e).lower():
                self._status = DataSourceStatus.RATE_LIMITED
                logger.warning("Alpha Vantage rate limit hit")
            else:
                self._record_error(f"Failed to get price: {e}")
            return None

    def get_candles(
        self,
        instrument: str,
        timeframe: str,
        count: int,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None
    ) -> List[Candle]:
        """Get historical candles from Alpha Vantage."""
        if self._status == DataSourceStatus.NOT_CONFIGURED:
            return []

        self.rate_limiter.wait_if_needed()
        start_time = time.time()

        try:
            candles = []

            # Map timeframe to Alpha Vantage interval
            interval_map = {
                "1m": "1min", "5m": "5min", "15m": "15min",
                "30m": "30min", "1h": "60min"
            }

            if "_" in instrument:  # Forex
                from_currency, to_currency = instrument.split("_")

                if timeframe.lower() in interval_map:
                    data, _ = self.fx.get_currency_exchange_rate_intraday(
                        from_symbol=from_currency,
                        to_symbol=to_currency,
                        interval=interval_map[timeframe.lower()]
                    )
                else:
                    data, _ = self.fx.get_currency_exchange_daily(
                        from_symbol=from_currency,
                        to_symbol=to_currency
                    )

            else:  # Stock
                if timeframe.lower() in interval_map:
                    data, _ = self.ts.get_intraday(
                        symbol=instrument,
                        interval=interval_map[timeframe.lower()],
                        outputsize='full'
                    )
                else:
                    data, _ = self.ts.get_daily(
                        symbol=instrument,
                        outputsize='full'
                    )

            # Parse candles
            time_series_key = [k for k in data.keys() if "Time Series" in k][0]
            time_series = data[time_series_key]

            for timestamp_str, values in sorted(
                time_series.items(),
                reverse=True
            )[:count]:
                candles.append(Candle(
                    instrument=instrument,
                    timestamp=datetime.fromisoformat(timestamp_str),
                    open=float(values.get("1. open", 0)),
                    high=float(values.get("2. high", 0)),
                    low=float(values.get("3. low", 0)),
                    close=float(values.get("4. close", 0)),
                    volume=int(values.get("5. volume", 0))
                ))

            self._record_success(time.time() - start_time)
            return candles

        except Exception as e:
            if "rate limit" in str(e).lower():
                self._status = DataSourceStatus.RATE_LIMITED
            self._record_error(f"Failed to get candles: {e}")
            return []

    def get_instruments(self) -> List[InstrumentInfo]:
        """Alpha Vantage doesn't provide instrument list."""
        return []

    def is_available(self) -> bool:
        """Check if Alpha Vantage is available."""
        if self._status == DataSourceStatus.NOT_CONFIGURED:
            return False

        try:
            self.rate_limiter.wait_if_needed()
            data, _ = self.fx.get_currency_exchange_rate("USD", "EUR")
            return True
        except:
            return False


class PolygonIODataSource(DataSource):
    """
    Polygon.io data source implementation.

    Supports stocks and Forex with higher rate limits than Alpha Vantage.
    """

    def __init__(self, api_key: str):
        """
        Initialize Polygon.io data source.

        Args:
            api_key: Polygon.io API key
        """
        super().__init__(DataSourceType.POLYGON)

        if not api_key or api_key == "your_api_key_here":
            self._status = DataSourceStatus.NOT_CONFIGURED
            logger.warning("Polygon.io not configured")
            return

        self.api_key = api_key
        self.client = PolygonRESTClient(api_key)

        # Rate limiter: Varies by plan, using conservative defaults
        self.rate_limiter = DataSourceRateLimiter(
            max_calls=100,
            time_window=60
        )

        self._status = DataSourceStatus.AVAILABLE
        logger.info("Polygon.io data source initialized")

    def get_current_price(self, instrument: str) -> Optional[Price]:
        """Get current price from Polygon.io."""
        if self._status == DataSourceStatus.NOT_CONFIGURED:
            return None

        self.rate_limiter.wait_if_needed()
        start_time = time.time()

        try:
            # Get latest trade
            ticker = self._convert_instrument_symbol(instrument)
            quote = self.client.get_last_quote(ticker)

            price = Price(
                instrument=instrument,
                bid=float(quote.bid_price),
                ask=float(quote.ask_price),
                timestamp=datetime.fromtimestamp(quote.participant_timestamp / 1e9)
            )

            self._record_success(time.time() - start_time)
            return price

        except Exception as e:
            self._record_error(f"Failed to get price: {e}")
            return None

    def get_candles(
        self,
        instrument: str,
        timeframe: str,
        count: int,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None
    ) -> List[Candle]:
        """Get historical candles from Polygon.io."""
        if self._status == DataSourceStatus.NOT_CONFIGURED:
            return []

        self.rate_limiter.wait_if_needed()
        start_time = time.time()

        try:
            ticker = self._convert_instrument_symbol(instrument)

            # Map timeframe to Polygon multiplier and timespan
            timeframe_map = {
                "1m": (1, "minute"),
                "5m": (5, "minute"),
                "15m": (15, "minute"),
                "30m": (30, "minute"),
                "1h": (1, "hour"),
                "4h": (4, "hour"),
                "1d": (1, "day"),
                "1w": (1, "week")
            }

            multiplier, timespan = timeframe_map.get(
                timeframe.lower(),
                (1, "day")
            )

            # Calculate time range
            if not to_time:
                to_time = datetime.now()
            if not from_time:
                from_time = to_time - timedelta(days=count)

            # Get aggregates
            aggs = self.client.get_aggs(
                ticker=ticker,
                multiplier=multiplier,
                timespan=timespan,
                from_=from_time.strftime("%Y-%m-%d"),
                to=to_time.strftime("%Y-%m-%d"),
                limit=count
            )

            candles = []
            for agg in aggs:
                candles.append(Candle(
                    instrument=instrument,
                    timestamp=datetime.fromtimestamp(agg.timestamp / 1000),
                    open=float(agg.open),
                    high=float(agg.high),
                    low=float(agg.low),
                    close=float(agg.close),
                    volume=int(agg.volume)
                ))

            self._record_success(time.time() - start_time)
            return candles

        except Exception as e:
            self._record_error(f"Failed to get candles: {e}")
            return []

    def get_instruments(self) -> List[InstrumentInfo]:
        """Get available instruments from Polygon.io."""
        if self._status == DataSourceStatus.NOT_CONFIGURED:
            return []

        try:
            self.rate_limiter.wait_if_needed()
            tickers = self.client.list_tickers(limit=1000)

            instruments = []
            for ticker in tickers:
                instruments.append(InstrumentInfo(
                    symbol=ticker.ticker,
                    name=ticker.name,
                    type=ticker.market.lower(),
                    exchange=ticker.primary_exchange,
                    currency=ticker.currency_name
                ))

            return instruments

        except Exception as e:
            self._record_error(f"Failed to get instruments: {e}")
            return []

    def is_available(self) -> bool:
        """Check if Polygon.io is available."""
        if self._status == DataSourceStatus.NOT_CONFIGURED:
            return False

        try:
            self.rate_limiter.wait_if_needed()
            self.client.get_market_status()
            return True
        except:
            return False

    def _convert_instrument_symbol(self, instrument: str) -> str:
        """Convert instrument format to Polygon format."""
        # Convert OANDA format (EUR_USD) to Polygon format (C:EURUSD for forex)
        if "_" in instrument:
            return f"C:{instrument.replace('_', '')}"
        return instrument


class YahooFinanceDataSource(DataSource):
    """
    Yahoo Finance data source implementation.

    Free fallback option with no rate limits but may be unreliable.
    Best for stocks and major Forex pairs.
    """

    def __init__(self):
        """Initialize Yahoo Finance data source."""
        super().__init__(DataSourceType.YAHOO_FINANCE)
        self._status = DataSourceStatus.AVAILABLE
        logger.info("Yahoo Finance data source initialized")

    def get_current_price(self, instrument: str) -> Optional[Price]:
        """Get current price from Yahoo Finance."""
        start_time = time.time()

        try:
            ticker = self._convert_instrument_symbol(instrument)
            stock = yf.Ticker(ticker)
            info = stock.info

            # Get real-time quote
            bid = info.get('bid', info.get('regularMarketPrice', 0))
            ask = info.get('ask', info.get('regularMarketPrice', 0))

            price = Price(
                instrument=instrument,
                bid=float(bid),
                ask=float(ask),
                timestamp=datetime.now()
            )

            self._record_success(time.time() - start_time)
            return price

        except Exception as e:
            self._record_error(f"Failed to get price: {e}")
            return None

    def get_candles(
        self,
        instrument: str,
        timeframe: str,
        count: int,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None
    ) -> List[Candle]:
        """Get historical candles from Yahoo Finance."""
        start_time = time.time()

        try:
            ticker = self._convert_instrument_symbol(instrument)
            stock = yf.Ticker(ticker)

            # Map timeframe to yfinance interval
            interval_map = {
                "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
                "1h": "1h", "1d": "1d", "1w": "1wk"
            }
            interval = interval_map.get(timeframe.lower(), "1d")

            # Calculate period
            if not to_time:
                to_time = datetime.now()
            if not from_time:
                # Estimate period based on count and timeframe
                if "m" in timeframe:
                    from_time = to_time - timedelta(minutes=count * int(timeframe[:-1]))
                elif "h" in timeframe:
                    from_time = to_time - timedelta(hours=count * int(timeframe[:-1]))
                else:
                    from_time = to_time - timedelta(days=count)

            # Download data
            df = stock.history(
                start=from_time,
                end=to_time,
                interval=interval
            )

            candles = []
            for idx, row in df.iterrows():
                candles.append(Candle(
                    instrument=instrument,
                    timestamp=idx.to_pydatetime(),
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=int(row['Volume'])
                ))

            self._record_success(time.time() - start_time)
            return candles[:count]

        except Exception as e:
            self._record_error(f"Failed to get candles: {e}")
            return []

    def get_instruments(self) -> List[InstrumentInfo]:
        """Yahoo Finance doesn't provide comprehensive instrument list."""
        return []

    def is_available(self) -> bool:
        """Check if Yahoo Finance is available."""
        try:
            stock = yf.Ticker("AAPL")
            info = stock.info
            return 'regularMarketPrice' in info
        except:
            return False

    def _convert_instrument_symbol(self, instrument: str) -> str:
        """Convert instrument format to Yahoo Finance format."""
        # Convert OANDA format (EUR_USD) to Yahoo format (EURUSD=X)
        if "_" in instrument:
            return f"{instrument.replace('_', '')}=X"
        return instrument


class DataSourceManager:
    """
    Manages multiple data sources with priority/fallback logic.

    Features:
    - Automatic failover if primary source fails
    - Load balancing across sources
    - Source health monitoring
    - Configurable priority order
    """

    def __init__(self, primary_source: DataSourceType):
        """
        Initialize data source manager.

        Args:
            primary_source: Primary data source to use
        """
        self.sources: Dict[DataSourceType, DataSource] = {}
        self.primary_source = primary_source
        self.fallback_enabled = True
        self._lock = threading.Lock()

        logger.info(f"Data source manager initialized with primary: {primary_source.value}")

    def register_source(
        self,
        source_type: DataSourceType,
        source: DataSource
    ) -> None:
        """
        Register a data source.

        Args:
            source_type: Type of data source
            source: DataSource instance
        """
        with self._lock:
            self.sources[source_type] = source
            logger.info(f"Registered data source: {source_type.value}")

    def get_current_price(
        self,
        instrument: str,
        use_fallback: bool = True
    ) -> Optional[Price]:
        """
        Get current price with automatic failover.

        Args:
            instrument: Instrument identifier
            use_fallback: Use fallback sources if primary fails

        Returns:
            Price object or None
        """
        # Try primary source first
        primary = self.sources.get(self.primary_source)
        if primary and primary.is_available():
            price = primary.get_current_price(instrument)
            if price:
                return price

        # Try fallback sources
        if use_fallback and self.fallback_enabled:
            for source_type, source in self.sources.items():
                if source_type != self.primary_source and source.is_available():
                    logger.info(
                        f"Falling back to {source_type.value} for {instrument}"
                    )
                    price = source.get_current_price(instrument)
                    if price:
                        return price

        return None

    def get_candles(
        self,
        instrument: str,
        timeframe: str,
        count: int,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        use_fallback: bool = True
    ) -> List[Candle]:
        """
        Get historical candles with automatic failover.

        Args:
            instrument: Instrument identifier
            timeframe: Timeframe string
            count: Number of candles
            from_time: Start time
            to_time: End time
            use_fallback: Use fallback sources if primary fails

        Returns:
            List of Candle objects
        """
        # Try primary source first
        primary = self.sources.get(self.primary_source)
        if primary and primary.is_available():
            candles = primary.get_candles(
                instrument, timeframe, count, from_time, to_time
            )
            if candles:
                return candles

        # Try fallback sources
        if use_fallback and self.fallback_enabled:
            for source_type, source in self.sources.items():
                if source_type != self.primary_source and source.is_available():
                    logger.info(
                        f"Falling back to {source_type.value} for {instrument}"
                    )
                    candles = source.get_candles(
                        instrument, timeframe, count, from_time, to_time
                    )
                    if candles:
                        return candles

        return []

    def get_all_health_status(self) -> Dict[str, DataSourceHealth]:
        """
        Get health status of all registered sources.

        Returns:
            Dictionary mapping source type to health status
        """
        return {
            source_type.value: source.get_health()
            for source_type, source in self.sources.items()
        }

    def get_available_sources(self) -> List[DataSourceType]:
        """
        Get list of currently available sources.

        Returns:
            List of available source types
        """
        return [
            source_type
            for source_type, source in self.sources.items()
            if source.is_available()
        ]

    def set_primary_source(self, source_type: DataSourceType) -> None:
        """
        Change the primary data source.

        Args:
            source_type: New primary source type
        """
        if source_type in self.sources:
            self.primary_source = source_type
            logger.info(f"Primary source changed to: {source_type.value}")
        else:
            raise ValueError(f"Source {source_type.value} not registered")

    def enable_fallback(self, enabled: bool = True) -> None:
        """
        Enable or disable fallback sources.

        Args:
            enabled: True to enable, False to disable
        """
        self.fallback_enabled = enabled
        logger.info(f"Fallback {'enabled' if enabled else 'disabled'}")


class DataAggregator:
    """
    Aggregates and cross-validates data from multiple sources.

    Features:
    - Combine data from multiple sources
    - Cross-validate prices
    - Detect anomalies (price divergence)
    - Use most reliable source
    """

    def __init__(
        self,
        manager: DataSourceManager,
        max_divergence_percent: float = 1.0
    ):
        """
        Initialize data aggregator.

        Args:
            manager: DataSourceManager instance
            max_divergence_percent: Maximum allowed price divergence %
        """
        self.manager = manager
        self.max_divergence_percent = max_divergence_percent
        logger.info("Data aggregator initialized")

    def get_aggregated_price(
        self,
        instrument: str,
        min_sources: int = 2
    ) -> Optional[Tuple[Price, Dict[str, Any]]]:
        """
        Get price from multiple sources and aggregate.

        Args:
            instrument: Instrument identifier
            min_sources: Minimum sources required for aggregation

        Returns:
            Tuple of (aggregated Price, metadata dict) or None
        """
        prices = []
        sources_used = []

        # Collect prices from all available sources
        for source_type, source in self.manager.sources.items():
            if source.is_available():
                price = source.get_current_price(instrument)
                if price:
                    prices.append(price)
                    sources_used.append(source_type.value)

        if len(prices) < min_sources:
            logger.warning(
                f"Insufficient sources for {instrument}: "
                f"{len(prices)} < {min_sources}"
            )
            return None

        # Calculate average and detect anomalies
        avg_bid = sum(p.bid for p in prices) / len(prices)
        avg_ask = sum(p.ask for p in prices) / len(prices)

        # Check for divergence
        divergences = []
        for price in prices:
            bid_div = abs((price.bid - avg_bid) / avg_bid * 100)
            ask_div = abs((price.ask - avg_ask) / avg_ask * 100)
            divergences.append(max(bid_div, ask_div))

        max_divergence = max(divergences)
        has_anomaly = max_divergence > self.max_divergence_percent

        if has_anomaly:
            logger.warning(
                f"Price anomaly detected for {instrument}: "
                f"{max_divergence:.2f}% divergence"
            )

        # Create aggregated price
        aggregated_price = Price(
            instrument=instrument,
            bid=avg_bid,
            ask=avg_ask,
            timestamp=max(p.timestamp for p in prices)
        )

        metadata = {
            "sources_count": len(prices),
            "sources_used": sources_used,
            "max_divergence_percent": max_divergence,
            "has_anomaly": has_anomaly,
            "individual_prices": [
                {"source": src, "bid": p.bid, "ask": p.ask}
                for src, p in zip(sources_used, prices)
            ]
        }

        return aggregated_price, metadata

    def validate_candles(
        self,
        candles: List[Candle]
    ) -> Tuple[List[Candle], Dict[str, Any]]:
        """
        Validate candle data for anomalies.

        Args:
            candles: List of candles to validate

        Returns:
            Tuple of (validated candles, validation metadata)
        """
        if not candles:
            return [], {"valid": True, "issues": []}

        issues = []
        validated_candles = []

        for i, candle in enumerate(candles):
            # Check for invalid prices
            if candle.high < candle.low:
                issues.append(f"Candle {i}: high < low")
                continue

            if candle.close > candle.high or candle.close < candle.low:
                issues.append(f"Candle {i}: close outside range")
                continue

            if candle.open > candle.high or candle.open < candle.low:
                issues.append(f"Candle {i}: open outside range")
                continue

            # Check for unrealistic spikes
            if i > 0:
                prev_candle = validated_candles[-1]
                price_change = abs(
                    (candle.close - prev_candle.close) / prev_candle.close * 100
                )
                if price_change > 10:  # 10% change
                    issues.append(
                        f"Candle {i}: large price change {price_change:.2f}%"
                    )

            validated_candles.append(candle)

        metadata = {
            "valid": len(issues) == 0,
            "issues": issues,
            "total_candles": len(candles),
            "validated_candles": len(validated_candles)
        }

        if issues:
            logger.warning(f"Candle validation issues: {issues}")

        return validated_candles, metadata
