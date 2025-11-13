# Redis Cache System Documentation

## Overview

The ScreenerIII Redis caching layer provides a comprehensive, production-ready caching solution with automatic fallback to in-memory storage when Redis is unavailable. The system is designed to significantly improve performance for trading data operations while maintaining data consistency.

## Architecture

### Core Components

1. **CacheManager (Singleton)**
   - Manages Redis connections with automatic reconnection
   - Implements connection pooling for optimal performance
   - Provides fallback to in-memory cache when Redis is unavailable
   - Thread-safe operations

2. **Cache Namespaces**
   - `prices:` - Real-time price data (TTL: 15 seconds)
   - `candles:` - Historical OHLCV candles (TTL: 60 seconds)
   - `indicators:` - Technical indicators (RSI, MACD, etc.) (TTL: 30 seconds)
   - `signals:` - Trading signals (TTL: 60 seconds)
   - `mtf:` - Multi-timeframe analysis data (TTL: 120 seconds)
   - `session:` - User session data (TTL: 3600 seconds)
   - `config:` - Configuration cache (TTL: 600 seconds)
   - `metadata:` - Metadata cache (TTL: 300 seconds)

3. **Serialization Strategies**
   - **JSON**: For simple data types and cross-language compatibility
   - **Pickle**: For complex Python objects (DataFrames, custom classes)
   - **MessagePack**: For high-performance serialization

4. **Advanced Features**
   - Batch operations (mget/mset) for efficiency
   - Pipeline support for atomic multi-operation transactions
   - Pub/Sub for real-time event distribution
   - Automatic data compression for large objects
   - Comprehensive statistics and monitoring

## Installation

### Prerequisites

```bash
# Install Redis server (Ubuntu/Debian)
sudo apt-get install redis-server

# Or using Docker (recommended)
docker-compose up -d redis
```

### Python Dependencies

```bash
pip install redis>=5.0.0 hiredis>=2.0.0 msgpack>=1.0.0
```

### Configuration

Add to your `.env` file:

```env
# Redis Connection Settings
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Connection Pool Settings
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_TIMEOUT=5
REDIS_CONNECT_TIMEOUT=5

# Cache Behavior
CACHE_DEFAULT_TTL=60
CACHE_ENABLE_COMPRESSION=true
CACHE_COMPRESSION_THRESHOLD=1024
CACHE_FALLBACK_TO_MEMORY=true
CACHE_DEFAULT_SERIALIZER=json

# Cache Monitoring
CACHE_ENABLE_STATS=true
CACHE_STATS_RESET_INTERVAL=3600
```

## Quick Start

### Basic Usage

```python
from src.core.cache import get_cache, CacheNamespace

# Get cache instance
cache = get_cache()

# Store and retrieve data
cache.set('my_key', {'data': 'value'}, ttl=60)
value = cache.get('my_key')

# Use namespaces
cache.set('EUR_USD', 1.0950, namespace=CacheNamespace.PRICES)
price = cache.get('EUR_USD', namespace=CacheNamespace.PRICES)

# Check if key exists
if cache.exists('my_key'):
    print("Key exists!")

# Delete key
cache.delete('my_key')
```

### Caching Pandas DataFrames

```python
import pandas as pd
from src.core.cache import get_cache, CacheNamespace

cache = get_cache()

# Create DataFrame
df = pd.DataFrame({
    'timestamp': pd.date_range('2024-01-01', periods=100, freq='1min'),
    'close': np.random.uniform(1.0, 1.1, 100)
})

# Cache DataFrame
cache.set('EUR_USD:1min', df, namespace=CacheNamespace.CANDLES)

# Retrieve DataFrame
cached_df = cache.get('EUR_USD:1min', namespace=CacheNamespace.CANDLES)
```

### Using Decorators

```python
from src.core.cache import cached, cache_invalidate, CacheNamespace

# Cache function results
@cached(ttl=60, namespace=CacheNamespace.PRICES)
def fetch_price(symbol: str) -> float:
    """Fetch price from API (cached automatically)."""
    return api.get_price(symbol)

# Invalidate cache after updates
@cache_invalidate('prices:*')
def update_prices():
    """Update prices and clear cache."""
    # Update logic here
    pass

# Usage
price = fetch_price('EUR_USD')  # First call: fetches from API
price = fetch_price('EUR_USD')  # Second call: returns from cache
```

### Cache-Aside Pattern

```python
from src.core.cache import get_cache

cache = get_cache()

# Automatically fetch and cache if not present
def expensive_calculation(param):
    # Expensive operation
    return result

result = cache.get_or_fetch(
    key='calculation:param',
    fetch_func=lambda: expensive_calculation(param),
    ttl=300
)
```

### Batch Operations

```python
from src.core.cache import get_cache, CacheNamespace

cache = get_cache()

# Set multiple values at once
prices = {
    'EUR_USD': 1.0950,
    'GBP_USD': 1.2650,
    'USD_JPY': 149.50
}
cache.mset(prices, ttl=60, namespace=CacheNamespace.PRICES)

# Get multiple values at once
keys = ['EUR_USD', 'GBP_USD', 'USD_JPY']
values = cache.mget(keys, namespace=CacheNamespace.PRICES)
```

### Pipeline Operations

```python
from src.core.cache import get_cache

cache = get_cache()

# Execute multiple operations atomically
with cache.pipeline() as pipe:
    pipe.set('key1', 'value1')
    pipe.set('key2', 'value2')
    pipe.expire('key1', 60)
    results = pipe.execute()
```

### Pub/Sub for Real-Time Updates

```python
from src.core.cache import get_cache

cache = get_cache()

# Publisher
cache.publish('price_updates', {
    'symbol': 'EUR_USD',
    'price': 1.0950,
    'timestamp': time.time()
})

# Subscriber
def handle_price_update(channel, message):
    print(f"Price update: {message}")

cache.subscribe('price_updates', handle_price_update)
```

## Advanced Usage

### Custom Cache Configuration

```python
from src.core.cache import CacheManager, CacheConfig

config = CacheConfig(
    redis_host='localhost',
    redis_port=6379,
    redis_db=1,
    max_connections=100,
    default_ttl=120,
    enable_compression=True,
    compression_threshold=2048,
    default_serializer='msgpack'
)

cache = CacheManager(config)
```

### Pattern-Based Operations

```python
from src.core.cache import get_cache

cache = get_cache()

# Find all keys matching pattern
price_keys = cache.keys('prices:*')
eur_keys = cache.keys('*EUR*')

# Delete all keys matching pattern
deleted_count = cache.delete_pattern('temp:*')

# Clear entire namespace
cache.clear_namespace(CacheNamespace.PRICES)
```

### Cache Statistics

```python
from src.core.cache import get_cache

cache = get_cache()

# Get comprehensive statistics
stats = cache.get_stats()
print(f"Hit Rate: {stats['hit_rate']*100:.2f}%")
print(f"Total Keys: {stats['total_keys']}")
print(f"Redis Memory: {stats['redis_memory']['used_memory_human']}")

# Namespace-specific stats
for ns_name, ns_stats in stats['namespaces'].items():
    print(f"{ns_name}: {ns_stats['hit_rate']*100:.2f}% hit rate")

# Reset statistics
cache.reset_stats()
```

### Different Serializers

```python
from src.core.cache import get_cache

cache = get_cache()

# JSON (default) - good for simple data
cache.set('data1', {'key': 'value'}, serializer='json')

# Pickle - for complex Python objects
cache.set('data2', custom_object, serializer='pickle')

# MessagePack - for performance
cache.set('data3', large_data, serializer='msgpack')
```

## Performance Considerations

### When to Use Cache

✅ **Use cache for:**
- Frequently accessed data (prices, indicators)
- Expensive computations (technical indicators)
- API responses with rate limits
- Database queries with heavy joins
- Session data and user preferences

❌ **Don't cache:**
- Constantly changing data (tick data)
- Large objects that rarely repeat
- Data requiring strong consistency
- Sensitive information without encryption

### TTL Guidelines

- **Real-time prices**: 10-15 seconds
- **Historical candles**: 60-120 seconds (depending on timeframe)
- **Technical indicators**: 30-60 seconds
- **Trading signals**: 60-300 seconds
- **Configuration**: 600-3600 seconds
- **Session data**: 3600-86400 seconds

### Memory Management

Redis is configured with:
- **maxmemory**: 512MB (configurable in docker-compose.yml)
- **maxmemory-policy**: allkeys-lru (evicts least recently used keys)
- **appendonly**: yes (persistence enabled)

Monitor memory usage:
```python
stats = cache.get_stats()
print(stats['redis_memory'])
```

## Integration Examples

### In Trading Strategy

```python
from src.core.cache import cached, CacheNamespace

class TradingStrategy:
    @cached(ttl=30, namespace=CacheNamespace.INDICATORS)
    def calculate_rsi(self, symbol: str, period: int = 14) -> float:
        """Calculate RSI with caching."""
        # Expensive calculation
        return rsi_value

    @cached(ttl=60, namespace=CacheNamespace.SIGNALS)
    def generate_signal(self, symbol: str) -> dict:
        """Generate trading signal with caching."""
        rsi = self.calculate_rsi(symbol)
        # Signal logic
        return {'action': 'BUY', 'confidence': 0.85}
```

### In Data Provider

```python
from src.core.cache import get_cache, CacheNamespace

class MarketDataProvider:
    def __init__(self):
        self.cache = get_cache()

    def get_candles(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        """Get candles with caching."""
        cache_key = f"{symbol}:{timeframe}:{count}"

        # Try cache first
        df = self.cache.get(cache_key, namespace=CacheNamespace.CANDLES)
        if df is not None:
            return df

        # Fetch from API
        df = self._fetch_from_api(symbol, timeframe, count)

        # Cache result
        self.cache.set(cache_key, df, namespace=CacheNamespace.CANDLES)

        return df
```

### In Multi-Timeframe Analysis

```python
from src.core.cache import get_cache, CacheNamespace

class MTFAnalyzer:
    def __init__(self):
        self.cache = get_cache()

    def analyze(self, symbol: str, timeframes: List[str]) -> dict:
        """Multi-timeframe analysis with caching."""
        cache_key = f"{symbol}:{':'.join(timeframes)}"

        return self.cache.get_or_fetch(
            key=cache_key,
            fetch_func=lambda: self._perform_analysis(symbol, timeframes),
            ttl=120,
            namespace=CacheNamespace.MTF
        )
```

## Monitoring and Debugging

### Enable Debug Logging

```python
import logging

logging.getLogger('src.core.cache').setLevel(logging.DEBUG)
```

### Monitor Cache Health

```python
from src.core.cache import get_cache

cache = get_cache()
info = cache.get_info()

print(f"Status: {info['status']}")
print(f"Config: {info['config']}")
print(f"Stats: {info['stats']}")
```

### Check Redis Connection

```python
from src.core.cache import get_cache

cache = get_cache()
if cache._using_fallback:
    print("⚠️  Using fallback cache (Redis unavailable)")
else:
    print("✅ Redis connection active")
```

## Troubleshooting

### Redis Connection Failed

**Problem**: Cache falls back to in-memory mode

**Solutions**:
1. Check Redis is running: `docker-compose ps redis`
2. Verify connection settings in `.env`
3. Check Redis logs: `docker-compose logs redis`
4. Test connection: `redis-cli -h localhost -p 6379 ping`

### High Memory Usage

**Problem**: Redis using too much memory

**Solutions**:
1. Reduce TTLs for less important data
2. Increase maxmemory limit in docker-compose.yml
3. Review keys: `cache.keys('*')`
4. Clear unused namespaces: `cache.clear_namespace(...)`

### Low Hit Rate

**Problem**: Cache not improving performance

**Solutions**:
1. Check TTLs aren't too short
2. Review cache key patterns (ensure consistency)
3. Monitor stats: `cache.get_stats()`
4. Verify data access patterns

### Stale Data

**Problem**: Cache returning old data

**Solutions**:
1. Reduce TTLs for affected namespaces
2. Implement cache invalidation on updates
3. Use Pub/Sub to notify subscribers of changes
4. Clear cache manually: `cache.delete(key)` or `cache.clear_namespace(...)`

## Best Practices

1. **Use Namespaces**: Organize keys logically for easy management
2. **Set Appropriate TTLs**: Balance freshness vs. hit rate
3. **Monitor Statistics**: Track hit rates and adjust strategy
4. **Implement Invalidation**: Clear cache when source data changes
5. **Use Batch Operations**: More efficient than individual calls
6. **Handle Fallback**: Application should work without Redis
7. **Compress Large Data**: Enable compression for DataFrames
8. **Use Decorators**: Simplify caching with `@cached`
9. **Test Both Modes**: Verify functionality with and without Redis
10. **Monitor Memory**: Keep eye on Redis memory usage

## Testing

Run the comprehensive demo:

```bash
# Interactive mode
python examples/cache_demo.py

# Run all demos
python examples/cache_demo.py --all
```

Individual demos available:
1. Basic Operations
2. Cache Namespaces
3. Pandas DataFrames
4. Batch Operations
5. Pipeline Operations
6. Cache Decorators
7. Cache-Aside Pattern
8. Pub/Sub Messaging
9. Serialization Strategies
10. Statistics
11. Pattern Operations
12. Cache Information
13. Fallback Cache

## Docker Setup

Start Redis with Docker Compose:

```bash
# Start Redis only
docker-compose up -d redis

# Check Redis status
docker-compose ps redis

# View Redis logs
docker-compose logs -f redis

# Connect to Redis CLI
docker-compose exec redis redis-cli

# Stop Redis
docker-compose stop redis
```

## API Reference

### CacheManager

```python
class CacheManager:
    # Core operations
    def set(key, value, ttl=None, serializer=None, namespace=None) -> bool
    def get(key, serializer=None, namespace=None) -> Any
    def delete(key, namespace=None) -> bool
    def exists(key, namespace=None) -> bool
    def expire(key, ttl, namespace=None) -> bool

    # Cache-aside pattern
    def get_or_fetch(key, fetch_func, ttl=None, serializer=None, namespace=None) -> Any

    # Batch operations
    def mget(keys, serializer=None, namespace=None) -> List[Any]
    def mset(mapping, ttl=None, serializer=None, namespace=None) -> bool

    # Pattern operations
    def keys(pattern='*', namespace=None) -> List[str]
    def delete_pattern(pattern, namespace=None) -> int
    def clear_namespace(namespace) -> int

    # Pub/Sub
    def publish(channel, message, serializer=None) -> int
    def subscribe(channels, callback, serializer=None)

    # Monitoring
    def get_stats() -> Dict
    def reset_stats()
    def get_info() -> Dict

    # Utility
    def flush() -> bool
    def close()
```

### Decorators

```python
@cached(ttl=60, namespace=None, key_func=None, serializer=None)
@cache_invalidate(pattern, namespace=None)
@cache_aside(ttl=60, namespace=None, key_func=None, serializer=None)
```

## License

Part of ScreenerIII - see main project LICENSE
