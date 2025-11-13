# Alternative Data Sources Guide

## Overview

The ScreenerIII platform now supports multiple market data providers with automatic failover, data aggregation, and comprehensive error handling. This allows you to use alternative data sources beyond OANDA, providing redundancy and access to different markets.

## Supported Data Sources

### 1. OANDA (Primary)
- **Markets**: Forex, CFDs, Commodities
- **Rate Limits**: 120 requests/minute
- **Data Quality**: Excellent for Forex
- **Real-time**: Yes
- **Configuration**: Requires API token and account ID

### 2. Alpha Vantage
- **Markets**: Stocks, Forex, Cryptocurrencies
- **Rate Limits**: 5 calls/minute (free tier), 500 calls/day
- **Data Quality**: Good for stocks, limited for Forex
- **Real-time**: Yes (with delays on free tier)
- **Configuration**: Requires API key (free)

### 3. Polygon.io
- **Markets**: Stocks, Forex, Options, Crypto
- **Rate Limits**: 100+ requests/minute (varies by plan)
- **Data Quality**: Excellent for US stocks
- **Real-time**: Yes
- **Configuration**: Requires API key (paid)

### 4. Yahoo Finance
- **Markets**: Stocks, major Forex pairs, Indices
- **Rate Limits**: No official limits (use responsibly)
- **Data Quality**: Good for stocks, unreliable for Forex
- **Real-time**: Delayed quotes (15-20 minutes)
- **Configuration**: No API key required (free fallback)

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Primary data source (options: oanda, alphavantage, polygon, yahoo)
DATA_SOURCE_PRIMARY=oanda

# Enable automatic fallback
DATA_SOURCE_FALLBACK_ENABLED=true

# Fallback priority order
DATA_SOURCE_PRIORITY=oanda,alphavantage,polygon,yahoo

# API Keys
ALPHAVANTAGE_API_KEY=your_key_here
POLYGON_API_KEY=your_key_here

# OANDA Configuration (if using as primary)
OANDA_API_TOKEN=your_token_here
OANDA_ACCOUNT_ID=your_account_here
OANDA_ENVIRONMENT=practice
```

### Getting API Keys

**Alpha Vantage** (Free):
- Visit: https://www.alphavantage.co/support/#api-key
- Sign up for free account
- Copy API key to `.env`

**Polygon.io** (Paid):
- Visit: https://polygon.io/
- Sign up for paid plan
- Get API key from dashboard

**Yahoo Finance**:
- No API key needed
- Works automatically as fallback

## Usage Examples

### Basic Setup

```python
from src.data import (
    DataSourceManager,
    DataSourceType,
    OANDADataSource,
    AlphaVantageDataSource,
    YahooFinanceDataSource
)

# Create manager with OANDA as primary
manager = DataSourceManager(primary_source=DataSourceType.OANDA)

# Register sources
oanda = OANDADataSource(api_token="...", account_id="...", environment="practice")
manager.register_source(DataSourceType.OANDA, oanda)

av = AlphaVantageDataSource(api_key="...")
manager.register_source(DataSourceType.ALPHA_VANTAGE, av)

yahoo = YahooFinanceDataSource()
manager.register_source(DataSourceType.YAHOO_FINANCE, yahoo)

# Enable automatic failover
manager.enable_fallback(True)
```

### Get Current Price with Automatic Failover

```python
# Will try primary source first, then fallback to alternatives
price = manager.get_current_price("EUR_USD", use_fallback=True)

if price:
    print(f"Bid: {price.bid}, Ask: {price.ask}")
    print(f"Spread: {price.ask - price.bid}")
```

### Get Historical Candles

```python
from datetime import datetime, timedelta

# Get last 100 hourly candles
candles = manager.get_candles(
    instrument="AAPL",
    timeframe="1h",
    count=100,
    use_fallback=True
)

for candle in candles:
    print(f"{candle.timestamp}: O={candle.open} H={candle.high} L={candle.low} C={candle.close}")
```

### Data Aggregation and Cross-Validation

```python
from src.data import DataAggregator

# Create aggregator with 1% max price divergence
aggregator = DataAggregator(manager=manager, max_divergence_percent=1.0)

# Get price from multiple sources and aggregate
result = aggregator.get_aggregated_price("EUR_USD", min_sources=2)

if result:
    price, metadata = result
    print(f"Aggregated price: {price.bid} / {price.ask}")
    print(f"Sources used: {metadata['sources_used']}")
    print(f"Max divergence: {metadata['max_divergence_percent']}%")
    print(f"Has anomaly: {metadata['has_anomaly']}")
```

### Health Monitoring

```python
# Get health status of all sources
health_status = manager.get_all_health_status()

for source_name, health in health_status.items():
    print(f"{source_name}:")
    print(f"  Status: {health.status.value}")
    print(f"  Success rate: {health.success_count}/{health.success_count + health.error_count}")
    print(f"  Avg response time: {health.avg_response_time * 1000:.2f}ms")

    if health.last_error:
        print(f"  Last error: {health.last_error}")
```

### Check Available Sources

```python
# Get list of currently available sources
available = manager.get_available_sources()
print(f"Available: {', '.join(s.value for s in available)}")
```

### Switch Primary Source

```python
# Change primary source dynamically
manager.set_primary_source(DataSourceType.ALPHA_VANTAGE)
```

## Architecture

### Class Hierarchy

```
DataSource (Abstract Base Class)
├── OANDADataSource
├── AlphaVantageDataSource
├── PolygonIODataSource
└── YahooFinanceDataSource

DataSourceManager
└── Manages multiple DataSource instances

DataAggregator
└── Combines data from multiple sources
```

### Key Features

**Rate Limiting**:
- Each source has its own rate limiter
- Token bucket algorithm
- Automatic waiting when limits reached
- Configurable limits per source

**Error Handling**:
- Automatic retry with exponential backoff
- Graceful degradation
- Detailed error logging
- Health tracking

**Failover Logic**:
1. Try primary source first
2. If primary fails, try sources in priority order
3. Return first successful result
4. Track failures for health monitoring

**Data Validation**:
- Candle data validation (OHLC consistency)
- Price divergence detection
- Anomaly detection across sources
- Outlier filtering

## Best Practices

### 1. Use Multiple Sources for Reliability

```python
# Configure at least 2 sources for redundancy
manager.register_source(DataSourceType.OANDA, oanda_source)
manager.register_source(DataSourceType.YAHOO_FINANCE, yahoo_source)
```

### 2. Monitor Health Regularly

```python
# Check health periodically
import time

while True:
    health = manager.get_all_health_status()

    for source, status in health.items():
        if status.error_count > 10:
            print(f"Warning: {source} has {status.error_count} errors")

    time.sleep(60)  # Check every minute
```

### 3. Handle Rate Limits Gracefully

```python
from src.data import RateLimitExceeded

try:
    price = source.get_current_price("EUR_USD")
except RateLimitExceeded:
    # Wait and retry, or use fallback
    price = manager.get_current_price("EUR_USD", use_fallback=True)
```

### 4. Use Aggregation for Critical Decisions

```python
# For important trading decisions, cross-validate with multiple sources
result = aggregator.get_aggregated_price("EUR_USD", min_sources=3)

if result and not result[1]['has_anomaly']:
    # Price is consistent across sources
    price = result[0]
    # Make trading decision
```

### 5. Match Instruments to Appropriate Sources

| Instrument Type | Best Sources |
|----------------|--------------|
| Forex pairs | OANDA, Alpha Vantage |
| US Stocks | Polygon.io, Alpha Vantage, Yahoo |
| Cryptocurrencies | Alpha Vantage |
| International Stocks | Yahoo Finance |

## Timeframe Mappings

Different sources use different timeframe formats:

| Common Format | OANDA | Alpha Vantage | Polygon | Yahoo |
|--------------|-------|---------------|---------|-------|
| 1m | M1 | 1min | 1/minute | 1m |
| 5m | M5 | 5min | 5/minute | 5m |
| 15m | M15 | 15min | 15/minute | 15m |
| 30m | M30 | 30min | 30/minute | 30m |
| 1h | H1 | 60min | 1/hour | 1h |
| 4h | H4 | - | 4/hour | - |
| 1d | D | daily | 1/day | 1d |
| 1w | W | weekly | 1/week | 1wk |

The system automatically converts timeframes to the appropriate format for each source.

## Troubleshooting

### No Data Sources Available

```
⚠ No data sources configured!
```

**Solution**: Configure at least one data source in `.env` file with valid API credentials.

### Rate Limit Exceeded

```
Alpha Vantage rate limit hit
```

**Solution**:
- Wait for rate limit window to reset
- Enable fallback to use alternative sources
- Upgrade to paid plan for higher limits

### Price Divergence Detected

```
Price anomaly detected for EUR_USD: 2.5% divergence
```

**Solution**:
- Check individual source prices
- Investigate which source has anomalous data
- May indicate data quality issue or market event

### Connection Failures

```
Failed to connect to data source
```

**Solution**:
- Check API credentials
- Verify internet connection
- Check source status (may be under maintenance)
- Enable fallback sources

## Performance Considerations

### Response Times

Typical response times (milliseconds):

| Source | Current Price | Historical Data |
|--------|--------------|----------------|
| OANDA | 100-300ms | 200-500ms |
| Alpha Vantage | 200-500ms | 300-800ms |
| Polygon.io | 100-400ms | 200-600ms |
| Yahoo Finance | 500-2000ms | 1000-3000ms |

### Caching

Consider implementing caching for:
- Instrument lists (rarely change)
- Historical data (immutable)
- Recent prices (TTL: 1-5 seconds)

### Optimization Tips

1. **Batch Requests**: When possible, request multiple instruments in one call
2. **Prioritize Fast Sources**: Set faster sources as primary
3. **Cache Aggressively**: Cache frequently requested data
4. **Monitor Usage**: Track API usage to stay within limits

## Running the Demo

```bash
# Install dependencies
pip install -r requirements.txt

# Configure .env file with your API keys
cp .env.example .env
nano .env  # Add your API keys

# Run the demo
python examples/data_sources_demo.py
```

The demo will show:
- Basic price retrieval
- Historical data fetching
- Health monitoring
- Data aggregation
- Automatic failover
- Rate limiting behavior
- Error handling

## Further Reading

- [OANDA API Documentation](https://developer.oanda.com/)
- [Alpha Vantage Documentation](https://www.alphavantage.co/documentation/)
- [Polygon.io Documentation](https://polygon.io/docs/)
- [yfinance Documentation](https://pypi.org/project/yfinance/)

## Support

For issues or questions:
1. Check this documentation
2. Review demo examples
3. Check source health status
4. Review logs for detailed errors
