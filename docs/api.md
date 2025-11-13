# ScreenerIII API Documentation

## Overview

This document describes the internal API modules and classes for ScreenerIII. The API is organized into distinct layers: Data, Analysis, Interface, and Core.

## Table of Contents

1. [OANDA API Client](#oanda-api-client)
2. [Data Formatting API](#data-formatting-api)
3. [Configuration API](#configuration-api)
4. [Future Modules](#future-modules)

---

## OANDA API Client

**Module**: `src/data/oanda_client.py`

Comprehensive Python wrapper for the OANDA v20 REST API with advanced features including rate limiting, retry logic, and connection management.

### Classes

#### RateLimiter

Rate limiter implementing the token bucket algorithm.

```python
class RateLimiter:
    def __init__(
        self,
        max_requests: int = 120,
        time_window: int = 60
    ) -> None:
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests per time window (default: 120)
            time_window: Time window in seconds (default: 60)
        """
```

**Methods**:

- `acquire() -> bool`
  - Attempt to acquire permission for a request
  - Returns: True if allowed, False if limit reached

- `wait_if_needed() -> None`
  - Block until a request slot becomes available
  - Thread-safe blocking wait

- `reset() -> None`
  - Reset the rate limiter state
  - Clears all tracked requests

**Usage Example**:
```python
limiter = RateLimiter(max_requests=120, time_window=60)

# Check if request allowed without blocking
if limiter.acquire():
    # Make API request
    pass

# Wait if needed (blocking)
limiter.wait_if_needed()
# Now safe to make request
```

#### ConnectionStatus Enum

Connection state enumeration.

```python
class ConnectionStatus(Enum):
    DISCONNECTED = "disconnected"      # Initial state
    CONNECTING = "connecting"          # Request in progress
    CONNECTED = "connected"            # Successfully connected
    ERROR = "error"                    # Error occurred
    RATE_LIMITED = "rate_limited"      # Rate limit exceeded
```

#### OANDAClient

Main API client wrapper with comprehensive error handling.

```python
class OANDAClient:
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
    ) -> None:
        """
        Initialize OANDA client.

        Args:
            api_token: OANDA API token
            account_id: OANDA account ID
            environment: "practice" or "live" (default: "practice")
            max_retries: Maximum retry attempts (default: 3)
            initial_retry_delay: Initial retry delay in seconds (default: 1.0)
            max_retry_delay: Maximum retry delay in seconds (default: 60.0)
            rate_limit_requests: Max requests per window (default: 120)
            rate_limit_window: Rate limit window in seconds (default: 60)
        """
```

**Properties**:

- `status: ConnectionStatus`
  - Get current connection status (read-only, thread-safe)

- `last_error: Optional[str]`
  - Get last error message (read-only, thread-safe)

**Methods**:

##### get_current_prices()
```python
def get_current_prices(
    self,
    instruments: Union[str, List[str]],
    include_unitsavailable: bool = False
) -> Dict[str, Any]:
    """
    Get current real-time prices for specified instruments.

    Args:
        instruments: Single instrument string or list
                    (e.g., "XAU_USD" or ["XAU_USD", "XAG_USD"])
        include_unitsavailable: Include units available in response

    Returns:
        Dictionary with structure:
        {
            "prices": [
                {
                    "instrument": "XAU_USD",
                    "bid": 2025.50,
                    "ask": 2025.75,
                    "time": "2024-01-15T10:30:00Z"
                }
            ]
        }

    Raises:
        OANDAClientError: If request fails
        RateLimitError: If rate limited
        ConnectionError: If connection fails
    """
```

**Usage Example**:
```python
client = OANDAClient(
    api_token="your_token",
    account_id="your_account_id",
    environment="practice"
)

# Single instrument
prices = client.get_current_prices("XAU_USD")

# Multiple instruments
prices = client.get_current_prices(["XAU_USD", "XAG_USD", "BCO_USD"])
```

##### get_candles()
```python
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
        instrument: Instrument name (e.g., "XAU_USD")
        granularity: Candle timeframe
                    (S5, S10, S15, S30, M1, M5, M15, M30, H1, H4, D, W, M)
        count: Number of candles to return (max 5000)
        from_time: Start time for candle range (datetime object)
        to_time: End time for candle range (datetime object)
        price: Price type - M (midpoint), B (bid), A (ask)

    Returns:
        Dictionary with structure:
        {
            "instrument": "XAU_USD",
            "granularity": "M1",
            "candles": [
                {
                    "complete": true,
                    "volume": 150,
                    "time": "2024-01-15T10:30:00Z",
                    "mid": {
                        "o": 2025.50,
                        "h": 2025.75,
                        "l": 2025.25,
                        "c": 2025.60
                    }
                }
            ]
        }

    Raises:
        OANDAClientError: If request fails
    """
```

**Usage Example**:
```python
from datetime import datetime, timedelta

# Fetch last 100 candles
candles = client.get_candles("XAU_USD", granularity="M1", count=100)

# Fetch candles for date range
start = datetime(2024, 1, 15, 0, 0, 0)
end = datetime(2024, 1, 15, 23, 59, 59)
candles = client.get_candles(
    "XAU_USD",
    granularity="H1",
    from_time=start,
    to_time=end
)
```

##### get_account_summary()
```python
def get_account_summary() -> Dict[str, Any]:
    """
    Get account summary information.

    Returns:
        Dictionary with structure:
        {
            "account": {
                "id": "account_id",
                "alias": "account_name",
                "currency": "USD",
                "balance": 100000.00,
                "unrealizedPL": 1234.56,
                "marginAvailable": 50000.00,
                "marginUsed": 0.00,
                "marginRate": 0.05,
                "orders": [],
                "trades": [],
                "positions": []
            }
        }

    Raises:
        OANDAClientError: If request fails
    """
```

##### get_tradeable_instruments()
```python
def get_tradeable_instruments() -> List[Dict[str, Any]]:
    """
    Get list of tradeable instruments for the account.

    Returns:
        List of instrument dictionaries with structure:
        [
            {
                "name": "XAU_USD",
                "type": "METAL",
                "displayName": "Gold",
                "pipLocation": -2,
                "displayPrecision": 5,
                "tradeUnitsPrecision": 0,
                "minimumTradeSize": "1",
                "maximumTradeSize": "10000000",
                "maximumPositionSize": "0",
                "financing": {...},
                "tags": []
            }
        ]

    Raises:
        OANDAClientError: If request fails
    """
```

##### test_connection()
```python
def test_connection() -> bool:
    """
    Test connection to OANDA API.

    Returns:
        True if connection successful, False otherwise
    """
```

**Usage Example**:
```python
if client.test_connection():
    print("Connected to OANDA API")
else:
    print("Connection failed")
```

##### get_connection_info()
```python
def get_connection_info() -> Dict[str, Any]:
    """
    Get connection status information.

    Returns:
        Dictionary with structure:
        {
            "status": "connected",
            "last_error": None,
            "last_successful_request": datetime object,
            "environment": "practice",
            "account_id": "your_account_id"
        }
    """
```

### Exception Classes

```python
class OANDAClientError(Exception):
    """Base exception for OANDA client errors."""

class RateLimitError(OANDAClientError):
    """Raised when rate limit is exceeded."""

class ConnectionError(OANDAClientError):
    """Raised when connection fails."""
```

### Error Handling

The client implements automatic retry logic with exponential backoff:

1. **Rate Limit Errors (429)**: Wait and retry up to 3 times
2. **Server Errors (5xx)**: Automatic retry with backoff
3. **Connection Errors**: Exponential backoff retry
4. **API Errors**: Raise OANDAClientError

**Retry Backoff Formula**:
```
delay = min(initial_delay * (2 ^ retry_count), max_delay)
delay = min(1.0 * (2 ^ retry_count), 60.0)
```

---

## Data Formatting API

**Module**: `src/interface/formatter.py`

Utility functions for formatting financial data for terminal display.

### Functions

#### format_price()
```python
def format_price(
    price: Union[float, int, Decimal, None],
    decimals: int = 5,
    currency: str = "$"
) -> str:
    """
    Format a price value with currency symbol and decimals.

    Args:
        price: Price value to format
        decimals: Number of decimal places (default: 5)
        currency: Currency symbol (default: "$")

    Returns:
        Formatted price string

    Examples:
        format_price(2025.56789) -> "$2,025.56789"
        format_price(None) -> "N/A"
    """
```

#### format_percentage()
```python
def format_percentage(
    value: Union[float, int, None],
    decimals: int = 2,
    show_sign: bool = True
) -> str:
    """
    Format a percentage value with sign.

    Args:
        value: Percentage value (e.g., 5.5 for 5.5%)
        decimals: Number of decimal places (default: 2)
        show_sign: Show + sign for positive values (default: True)

    Returns:
        Formatted percentage string

    Examples:
        format_percentage(5.5) -> "+5.50%"
        format_percentage(-2.3) -> "-2.30%"
    """
```

#### format_number()
```python
def format_number(
    value: Union[float, int, None],
    decimals: int = 2,
    use_commas: bool = True
) -> str:
    """
    Format a numeric value with optional comma separators.

    Args:
        value: Numeric value to format
        decimals: Number of decimal places (default: 2)
        use_commas: Use comma separators (default: True)

    Returns:
        Formatted number string

    Examples:
        format_number(1234567.89) -> "1,234,567.89"
    """
```

#### format_volume()
```python
def format_volume(volume: Union[int, float, None]) -> str:
    """
    Format volume with K/M/B suffixes for readability.

    Args:
        volume: Volume value to format

    Returns:
        Formatted volume string

    Examples:
        format_volume(1500) -> "1.50K"
        format_volume(2500000) -> "2.50M"
        format_volume(1500000000) -> "1.50B"
    """
```

#### format_ratio()
```python
def format_ratio(
    ratio: Union[float, None],
    decimals: int = 2
) -> str:
    """
    Format a ratio value (e.g., risk/reward).

    Examples:
        format_ratio(2.5) -> "2.50"
    """
```

#### format_signal()
```python
def format_signal(signal: Optional[str]) -> str:
    """
    Format a trading signal for display.

    Args:
        signal: Signal string (e.g., 'BUY', 'SELL', 'HOLD')

    Returns:
        Upper-case formatted signal

    Examples:
        format_signal('BUY') -> "BUY"
        format_signal(None) -> "HOLD"
    """
```

#### format_confidence()
```python
def format_confidence(confidence: Union[float, int, None]) -> str:
    """
    Format confidence level as percentage.

    Args:
        confidence: Confidence value (0-1 or 0-100)

    Returns:
        Formatted confidence percentage

    Examples:
        format_confidence(0.85) -> "85%"
        format_confidence(75) -> "75%"
    """
```

#### format_table_row()
```python
def format_table_row(
    columns: List[Any],
    widths: List[int],
    alignments: Optional[List[str]] = None
) -> str:
    """
    Format a table row with specified column widths.

    Args:
        columns: List of column values
        widths: List of column widths
        alignments: List of alignments ('left', 'right', 'center')

    Returns:
        Formatted row string
    """
```

#### format_spread()
```python
def format_spread(bid: Optional[float], ask: Optional[float]) -> str:
    """
    Format bid-ask spread for display.

    Examples:
        format_spread(1.2000, 1.2005) -> "1.20000 / 1.20050"
    """
```

#### align_text()
```python
def align_text(
    text: str,
    width: int,
    alignment: str = "left"
) -> str:
    """
    Align text within specified width.

    Args:
        text: Text to align
        width: Total width for alignment
        alignment: 'left', 'right', or 'center'
    """
```

#### create_separator()
```python
def create_separator(
    width: int,
    char: str = "-"
) -> str:
    """
    Create a separator line for formatting.

    Examples:
        create_separator(10) -> "----------"
        create_separator(5, "=") -> "====="
    """
```

#### truncate_text()
```python
def truncate_text(
    text: str,
    max_length: int,
    suffix: str = "..."
) -> str:
    """
    Truncate text to maximum length.

    Examples:
        truncate_text("Long text here", 10) -> "Long te..."
    """
```

#### format_timestamp()
```python
def format_timestamp(
    timestamp: Optional[str],
    time_format: str = "%Y-%m-%d %H:%M:%S"
) -> str:
    """
    Format a timestamp string for display.
    """
```

---

## Configuration API

**Module**: `config/`

### settings.py

Application-wide configuration constants.

**Key Variables**:
```python
# Application
APP_NAME = "ScreenerIII"
APP_VERSION = "1.0.0"
DEBUG = bool

# API
OANDA_API_KEY = str              # From .env
OANDA_ACCOUNT_ID = str           # From .env
OANDA_ENVIRONMENT = str          # 'live' or 'practice'
OANDA_API_URLS = dict            # API endpoints

# Database
DATABASE_PATH = Path
DATABASE_CONFIG = dict

# Logging
LOG_LEVEL = str                  # DEBUG, INFO, WARNING, ERROR
LOGGING_CONFIG = dict

# Technical Analysis
SIGNAL_CONFIDENCE_THRESHOLD = 0.6
MIN_RISK_REWARD_RATIO = 1.5
MAX_WORKERS = 4
CACHE_TIMEOUT = 60
```

### markets.py

Market definitions and helper functions.

**Key Data Structures**:

```python
MARKETS = {
    "XAU_USD": {
        "symbol": "XAU_USD",
        "display_name": "Gold",
        "category": "Precious Metals",
        "pip_location": -2,
        "min_trade_size": 1,
        "max_trade_size": 10000,
        "typical_spread": 0.5
    },
    # ... 11 more markets
}

MARKETS_BY_CATEGORY = {
    "Precious Metals": ["XAU_USD", "XAG_USD", "XPT_USD", "XPD_USD"],
    "Energy": ["BCO_USD", "WTICO_USD", "NATGAS_USD"],
    "Agriculture": ["CORN_USD", "SOYBN_USD", "WHEAT_USD", "SUGAR_USD"]
}
```

**Helper Functions**:

```python
def get_market_info(symbol: str) -> dict:
    """Get market information for a symbol."""

def get_markets_by_category(category: str) -> list:
    """Get list of market symbols in a category."""

def get_display_name(symbol: str) -> str:
    """Get display name for a symbol."""

def get_category(symbol: str) -> str:
    """Get category for a symbol."""
```

### indicators.py

Technical indicator parameters and settings.

**Indicator Groups**:
- Moving Averages (MA_SETTINGS, EMA_SETTINGS, SMA_SETTINGS)
- Oscillators (RSI_SETTINGS, MACD_SETTINGS, STOCHASTIC_SETTINGS)
- Trend (ADX_SETTINGS, PSAR_SETTINGS)
- Volatility (BOLLINGER_SETTINGS, ATR_SETTINGS)
- Volume (OBV_SETTINGS, VOLUME_SETTINGS)
- Advanced (ICHIMOKU_SETTINGS, CCI_SETTINGS)
- Levels (FIBONACCI_LEVELS)
- Analysis (TREND_SETTINGS, SUPPORT_RESISTANCE_SETTINGS)

**Signal Weighting**:
```python
SIGNAL_WEIGHTS = {
    "trend": 0.30,
    "momentum": 0.25,
    "volatility": 0.15,
    "volume": 0.15,
    "pattern": 0.15
}
```

**Risk Settings**:
```python
RISK_SETTINGS = {
    "default_risk_percent": 1.0,
    "max_risk_percent": 2.0,
    "min_risk_reward": 1.5,
    "optimal_risk_reward": 2.0,
    "stop_loss_atr_multiplier": 2.0,
    "take_profit_atr_multiplier": 4.0
}
```

---

## Future Modules

The following modules are planned for future implementation:

### src/core/
- `data_collector.py`: Real-time market data collection
- `orchestrator.py`: Component orchestration
- `signal_generator.py`: Trading signal generation

### src/analysis/
- `technical_analyzer.py`: Technical indicator calculations
- `pattern_recognition.py`: Chart pattern detection
- `risk_manager.py`: Position sizing and risk calculation

### src/interface/
- `dashboard.py`: Terminal-based UI
- `alerts.py`: Signal notification system

### src/utils/
- `validators.py`: Data validation utilities
- `time_helpers.py`: Time and timezone utilities
- `cache.py`: Caching mechanisms

---

## Usage Examples

### Complete Client Initialization and Usage

```python
from src.data.oanda_client import OANDAClient
from config.markets import ALL_MARKET_SYMBOLS
import os

# Initialize client
client = OANDAClient(
    api_token=os.getenv("OANDA_API_KEY"),
    account_id=os.getenv("OANDA_ACCOUNT_ID"),
    environment=os.getenv("OANDA_ENVIRONMENT", "practice")
)

# Test connection
if client.test_connection():
    print("Connected!")

    # Get prices for all markets
    prices = client.get_current_prices(ALL_MARKET_SYMBOLS)

    # Get historical data
    candles = client.get_candles("XAU_USD", granularity="M1", count=200)

    # Get account info
    account = client.get_account_summary()

    # Check status
    info = client.get_connection_info()
    print(f"Status: {info['status']}")
```

### Data Formatting Example

```python
from src.interface.formatter import (
    format_price, format_percentage, format_volume,
    format_signal, format_confidence
)

price = 2025.56789
change = 1.25
volume = 1500000
signal = "BUY"
confidence = 0.85

print(format_price(price))           # $2,025.56789
print(format_percentage(change))     # +1.25%
print(format_volume(volume))         # 1.50M
print(format_signal(signal))         # BUY
print(format_confidence(confidence)) # 85%
```
