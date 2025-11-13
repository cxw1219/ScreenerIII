# Data Collection Module

A comprehensive data collection module for fetching, validating, and storing market data from OANDA.

## Features

### OANDA Client (`oanda_client.py`)
- **OANDA API wrapper** using oandapyV20
- **Rate limiting** with token bucket algorithm (default: 120 req/min)
- **Automatic retry** with exponential backoff
- **Connection status management** (disconnected, connecting, connected, error, rate_limited)
- **Comprehensive error handling** for network failures
- **Real-time pricing** data fetching
- **Historical candle** data retrieval
- **Account information** queries

### Market Data Structures (`market_data.py`)
- **Price dataclass**: Real-time bid/ask/mid prices with spread calculation
- **Candle dataclass**: OHLCV (Open, High, Low, Close, Volume) candle data
- **SpreadData dataclass**: Spread metrics and analysis
- **VolumeData dataclass**: Volume metrics with moving averages
- **HistoricalDataManager**: In-memory management of historical candle data
- **Data validation**: Comprehensive validation for all data structures
- **Type hints**: Full type annotations throughout

### Database Storage (`storage.py`)
- **SQLite database** for persistent storage
- **Save operations**: Store prices, candles, spreads, and volumes
- **Query operations**: Retrieve historical data with filters
- **Data maintenance**: Cleanup old data, vacuum database
- **Database statistics**: Monitor storage usage and data counts
- **Transaction safety**: Proper error handling and rollback
- **Indexed queries**: Optimized database indexes for fast retrieval

## Installation

Ensure you have the required dependencies installed:

```bash
pip install -r requirements.txt
```

Required packages:
- oandapyV20==0.7.2
- pandas==2.1.4
- numpy==1.26.2
- python-dotenv==1.0.0
- SQLAlchemy==2.0.23

## Quick Start

### 1. Initialize OANDA Client

```python
from src.data import OANDAClient

client = OANDAClient(
    api_token='your_api_token',
    account_id='your_account_id',
    environment='practice',  # or 'live'
    max_retries=3,
    rate_limit_requests=120
)

# Test connection
if client.test_connection():
    print("Connected to OANDA!")
```

### 2. Fetch Real-Time Prices

```python
from src.data import Price

# Fetch current prices
response = client.get_current_prices(['EUR_USD', 'GBP_USD'])

# Parse into Price objects
for price_data in response['prices']:
    price = Price.from_oanda_response(price_data)
    print(f"{price.instrument}: Bid={price.bid}, Ask={price.ask}")
```

### 3. Fetch Historical Candles

```python
from src.data import Candle
from datetime import datetime, timedelta

# Fetch last 100 hourly candles
response = client.get_candles(
    instrument='EUR_USD',
    granularity='H1',
    count=100
)

# Parse into Candle objects
candles = []
for candle_data in response['candles']:
    candle = Candle.from_oanda_response(
        instrument='EUR_USD',
        data=candle_data,
        price_type='mid',
        granularity='H1'
    )
    candles.append(candle)
```

### 4. Store Data in Database

```python
from src.data import StorageManager

# Initialize storage
storage = StorageManager(db_path='market_data.db')

# Save prices
success_count, fail_count = storage.save_prices(prices)
print(f"Saved {success_count} prices")

# Save candles
success_count, fail_count = storage.save_candles(candles)
print(f"Saved {success_count} candles")

# Query historical data
df = storage.get_candles(
    instrument='EUR_USD',
    granularity='H1',
    start_time=datetime.now() - timedelta(days=7),
    limit=100
)
print(f"Retrieved {len(df)} candles")
```

### 5. Use Historical Data Manager

```python
from src.data import HistoricalDataManager

# Initialize manager
hist_manager = HistoricalDataManager()

# Add candles
hist_manager.add_candles('EUR_USD', candles)

# Get statistics
stats = hist_manager.get_statistics('EUR_USD')
print(f"Data range: {stats['start_time']} to {stats['end_time']}")
print(f"Total candles: {stats['count']}")

# Query candles
df = hist_manager.get_candles(
    instrument='EUR_USD',
    start_time=datetime.now() - timedelta(days=1)
)
```

## Advanced Usage

### Rate Limiting

The client includes built-in rate limiting to prevent API throttling:

```python
from src.data import RateLimiter

# Custom rate limiter (60 requests per 60 seconds)
limiter = RateLimiter(max_requests=60, time_window=60)

# Automatically wait if needed
limiter.wait_if_needed()
# ... make API request ...
```

### Retry Logic with Exponential Backoff

The client automatically retries failed requests with exponential backoff:

```python
client = OANDAClient(
    api_token='your_token',
    account_id='your_account',
    max_retries=5,
    initial_retry_delay=1.0,
    max_retry_delay=60.0
)
```

### Connection Status Monitoring

```python
from src.data import ConnectionStatus

# Get current status
status = client.status
print(f"Status: {status.value}")

# Get detailed connection info
info = client.get_connection_info()
print(f"Last successful request: {info['last_successful_request']}")
print(f"Last error: {info['last_error']}")
```

### Data Validation

All data structures include automatic validation:

```python
from src.data import Price, ValidationError

try:
    # This will raise ValidationError (ask < bid)
    price = Price(
        instrument='EUR_USD',
        bid=1.1000,
        ask=1.0900,  # Invalid!
        timestamp=datetime.now()
    )
except ValidationError as e:
    print(f"Validation failed: {e}")
```

### Database Maintenance

```python
# Delete old data (keep last 30 days)
deleted = storage.delete_old_data(table='prices', days_to_keep=30)
print(f"Deleted {deleted} old records")

# Vacuum database to reclaim space
storage.vacuum_database()

# Get database statistics
stats = storage.get_database_stats()
print(f"Database size: {stats['database_size_bytes']} bytes")
for table, info in stats['tables'].items():
    print(f"{table}: {info['row_count']} rows")
```

## Error Handling

The module includes comprehensive error handling:

```python
from src.data import OANDAClientError, RateLimitError

try:
    prices = client.get_current_prices('EUR_USD')
except RateLimitError:
    print("Rate limit exceeded, wait before retrying")
except OANDAClientError as e:
    print(f"OANDA API error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Data Structures

### Price
```python
@dataclass
class Price:
    instrument: str
    bid: float
    ask: float
    timestamp: datetime
    spread: Optional[float] = None
    mid: Optional[float] = None
    tradeable: bool = True
    liquidity: Optional[Dict[str, Any]] = None
```

### Candle
```python
@dataclass
class Candle:
    instrument: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    complete: bool = True
    granularity: Optional[str] = None
```

## Granularity Options

Available candle granularities:
- **Seconds**: S5, S10, S15, S30
- **Minutes**: M1, M2, M4, M5, M10, M15, M30
- **Hours**: H1, H2, H3, H4, H6, H8, H12
- **Days**: D
- **Weeks**: W
- **Months**: M

## Database Schema

### prices
- instrument (TEXT)
- bid (REAL)
- ask (REAL)
- spread (REAL)
- mid (REAL)
- timestamp (TEXT)
- tradeable (INTEGER)
- liquidity (TEXT - JSON)

### candles
- instrument (TEXT)
- timestamp (TEXT)
- open (REAL)
- high (REAL)
- low (REAL)
- close (REAL)
- volume (INTEGER)
- complete (INTEGER)
- granularity (TEXT)

### spreads
- instrument (TEXT)
- timestamp (TEXT)
- spread (REAL)
- spread_pips (REAL)
- spread_percentage (REAL)

### volumes
- instrument (TEXT)
- timestamp (TEXT)
- volume (INTEGER)
- volume_ma (REAL)
- relative_volume (REAL)

## Environment Variables

Create a `.env` file with your OANDA credentials:

```
OANDA_API_TOKEN=your_api_token_here
OANDA_ACCOUNT_ID=your_account_id_here
```

## Testing

Run the example usage script:

```bash
python src/data/example_usage.py
```

## Module Statistics

- **Total lines**: 1,734
- **Files**: 4
- **Classes**: 10+
- **Functions**: 50+
- **Test coverage**: Comprehensive error handling throughout

## Best Practices

1. **Always test connection** before making multiple requests
2. **Use rate limiting** to avoid API throttling
3. **Store credentials** in environment variables
4. **Close database connections** when done
5. **Validate data** before processing
6. **Handle errors gracefully** with try/except blocks
7. **Clean up old data** regularly to manage storage
8. **Monitor connection status** for production systems

## Logging

The module uses Python's logging framework. Configure it in your application:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Thread Safety

- Rate limiter is thread-safe
- Connection status uses locks for thread-safe access
- Database connection is not thread-safe by default (set check_same_thread=False)

## License

Part of ScreenerIII project.
