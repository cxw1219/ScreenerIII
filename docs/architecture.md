# ScreenerIII Architecture

## Overview

ScreenerIII is a real-time commodity market scanner with technical analysis and pattern recognition capabilities. It integrates with the OANDA API to provide live market data across 12 supported commodity markets including precious metals, energy, and agricultural commodities.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ScreenerIII Application                      │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
    ┌───▼────────┐     ┌─────▼─────────┐     ┌────▼──────────┐
    │  OANDA API │     │  SQLite DB    │     │ Configuration │
    │  Client    │     │  & Storage    │     │  & Settings   │
    └────────────┘     └───────────────┘     └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
    ┌───▼──────────┐   ┌─────▼────────┐   ┌──────▼─────┐
    │ Data Layer   │   │ Analysis     │   │ Interface  │
    │ - Market Data│   │ Layer        │   │ Layer      │
    │ - Storage    │   │ - Technical  │   │ - Display  │
    │ - Retrieval  │   │   Analysis   │   │ - Formatting
    │              │   │ - Patterns   │   │            │
    └──────────────┘   │ - Signals    │   └────────────┘
                       └──────────────┘

                    ┌──────────────────────┐
                    │  Core Engine Loop    │
                    │ - Market Collection  │
                    │ - Analysis           │
                    │ - Signal Generation  │
                    │ - Display Update     │
                    └──────────────────────┘
```

## Core Components

### 1. Main Application (main.py)

The `ScreenerApp` class is the central orchestrator that manages the entire application lifecycle:

- **Initialization**: Sets up logging, configuration, database, and components
- **Configuration Management**: Loads environment variables and validates settings
- **Database Management**: Initializes SQLite database with proper session handling
- **Component Initialization**: Prepares all required modules (currently in TODO state)
- **Main Loop**: Runs the market data collection and analysis cycle
- **Graceful Shutdown**: Handles signals and cleanup

**Key Methods**:
- `setup_logging()`: Configures logging with file and console handlers
- `load_configuration()`: Validates and loads .env environment variables
- `initialize_database()`: Creates database connections and tables
- `initialize_components()`: Prepares API client and analysis modules
- `market_data_loop()`: Main continuous loop for market updates
- `shutdown()`: Graceful application termination

### 2. Data Layer (src/data/)

#### OANDA API Client (oanda_client.py)

Comprehensive wrapper for the OANDA API with advanced features:

**Features**:
- Rate limiting using token bucket algorithm
- Automatic retry with exponential backoff
- Connection status management
- Thread-safe operations
- Comprehensive error handling

**Main Classes**:
- `RateLimiter`: Token bucket implementation for rate limiting
  - `acquire()`: Check if request allowed
  - `wait_if_needed()`: Block until request is allowed

- `OANDAClient`: Main API wrapper
  - `get_current_prices()`: Real-time pricing data
  - `get_candles()`: Historical candle data
  - `get_account_summary()`: Account information
  - `get_tradeable_instruments()`: Available markets
  - `test_connection()`: Connection validation

**Connection Status Enum**:
- `DISCONNECTED`: Initial state
- `CONNECTING`: Request in progress
- `CONNECTED`: Successfully connected
- `ERROR`: Connection error occurred
- `RATE_LIMITED`: Rate limit exceeded

**Error Handling**:
- `OANDAClientError`: Base exception
- `RateLimitError`: Rate limit exceeded
- `ConnectionError`: Connection failures

### 3. Configuration (config/)

#### settings.py

Global application settings including:
- API configuration and endpoints
- Database paths and timeouts
- Logging configuration
- Update intervals and display settings
- Performance tuning parameters
- Alert settings and thresholds

#### markets.py

Market definitions and categorizations:
- 12 supported commodity markets
- 3 market categories: Precious Metals, Energy, Agriculture
- Market metadata (symbol, display name, pip location, spreads)
- Helper functions for market lookups

#### indicators.py

Technical indicator parameters:
- 13+ indicator configurations
- Moving average settings (SMA, EMA, WMA)
- Oscillators (RSI, Stochastic, CCI)
- Trend indicators (MACD, ADX)
- Volatility measures (ATR, Bollinger Bands)
- Volume analysis settings
- Signal weighting parameters for combined signals

### 4. Interface Layer (src/interface/)

#### formatter.py

Display formatting utilities:
- `format_price()`: Price formatting with currency
- `format_percentage()`: Percentage display with sign
- `format_number()`: Numeric formatting with commas
- `format_volume()`: Volume with K/M/B suffixes
- `format_ratio()`: Risk/reward ratios
- `format_signal()`: Trading signal display
- `format_table_row()`: Table formatting
- `format_confidence()`: Confidence levels
- Table creation and alignment utilities

## Data Flow

### Market Update Cycle

```
1. Market Data Collection (10-second intervals)
   │
   ├─ OANDA API Request
   │  └─ Current prices for all 12 markets
   │
   ├─ Historical Data Fetch
   │  └─ 200 1-minute candles per market
   │
   └─ Database Storage
      └─ Store prices and metadata

2. Technical Analysis
   │
   ├─ Moving Averages (Fast, Medium, Slow)
   ├─ Momentum Indicators (RSI, MACD, Stochastic)
   ├─ Volatility Measures (ATR, Bollinger Bands)
   ├─ Trend Strength (ADX)
   └─ Volume Analysis

3. Pattern Recognition
   │
   ├─ Detect Reversal Patterns
   ├─ Identify Breakouts
   ├─ Find Support/Resistance
   └─ Recognize Consolidation

4. Signal Generation
   │
   ├─ Weighted Combination of Indicators
   ├─ Confidence Score Calculation
   ├─ Risk/Reward Analysis
   └─ Generate BUY/SELL/HOLD Signals

5. Display Update
   │
   ├─ Format Market Data
   ├─ Color-code Signals
   ├─ Group by Category
   └─ Terminal Output
```

## Database Schema

SQLite database (`data/screener.db`) stores:

**Planned Tables**:
- `market_prices`: Real-time and historical prices
  - Symbol, timestamp, open, high, low, close, volume

- `indicators`: Calculated indicator values
  - Symbol, timestamp, RSI, MACD, Bollinger bands, ATR

- `signals`: Generated trading signals
  - Symbol, timestamp, signal type, confidence, target, stop loss

- `trades`: Historical trade data
  - Entry/exit prices, P&L, duration

## Configuration Parameters

### Market Parameters
- **Update Interval**: 10 seconds
- **Candle Granularity**: 1-minute candles
- **Historical Data**: 200 candles per market

### Analysis Parameters
- **Signal Confidence Threshold**: 60%
- **Minimum Risk/Reward**: 1.5:1
- **ATR Multiplier (Stop Loss)**: 2.0
- **ATR Multiplier (Take Profit)**: 4.0

### Technical Indicator Defaults
- **RSI Period**: 14, Oversold: 30, Overbought: 70
- **MACD**: Fast 12, Slow 26, Signal 9
- **Moving Averages**: 9, 21, 50, 200 periods
- **Bollinger Bands**: 20-period SMA, 2 standard deviations
- **ATR**: 14-period
- **Stochastic**: 14, 3, 3 with 20/80 levels

## Threading and Concurrency

- **Rate Limiter**: Thread-safe token bucket using `threading.Lock`
- **Connection Status**: Protected with `_status_lock` for thread-safe access
- **Max Workers**: 4 concurrent threads for parallel data fetching
- **Database Session**: Thread-safe SQLAlchemy session factory

## Error Handling Strategy

1. **Connection Errors**: Automatic retry with exponential backoff
2. **Rate Limiting**: Wait and retry mechanism
3. **Data Errors**: Graceful degradation, continue with available data
4. **Server Errors (5xx)**: Retry up to 3 times with backoff
5. **Unexpected Errors**: Log and continue loop, pause 5 seconds

## Security Considerations

- API credentials stored in `.env` file (not version controlled)
- Database with `check_same_thread=False` for multi-threaded access
- SSL/TLS for OANDA API communication
- No hardcoded credentials in source code
- Sensitive data cleared on shutdown

## Performance Optimizations

- **Rate Limiting**: Token bucket algorithm prevents API overuse
- **Connection Pooling**: SQLAlchemy session pooling
- **Caching**: Market metadata cached in memory
- **Lazy Loading**: Indicators calculated on-demand
- **Batch Operations**: Process multiple markets simultaneously

## Future Enhancement Points

1. **Dashboard Module**: Real-time terminal UI with market overview
2. **Technical Analyzer**: Full indicator calculation engine
3. **Pattern Recognition**: Advanced chart pattern detection
4. **Alert System**: Notification triggers for signals
5. **Backtesting Engine**: Historical performance analysis
6. **Trading Integration**: Live order placement capability
7. **ML Models**: Machine learning signal generation
8. **WebUI**: Browser-based interface

## Environment Setup

```
.env file variables:
- OANDA_API_KEY: Your API token
- OANDA_ACCOUNT_ID: Your account ID
- OANDA_ENVIRONMENT: 'practice' or 'live'
- UPDATE_INTERVAL: Seconds between updates (default: 10)
- LOG_LEVEL: DEBUG, INFO, WARNING, ERROR (default: INFO)
```

## Logging

- **File Logs**: `logs/screener_YYYYMMDD.log`
- **Console Output**: Real-time status and data
- **Format**: Timestamp, logger name, level, message
- **Rotation**: Daily with 10MB file size limit and 5 backups
