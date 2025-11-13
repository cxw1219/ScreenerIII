# Redis Cache Quick Reference

## Import

```python
from src.core.cache import get_cache, CacheNamespace, cached, cache_invalidate
```

## Basic Operations

```python
cache = get_cache()

# Set
cache.set('key', 'value', ttl=60)

# Get
value = cache.get('key')

# Delete
cache.delete('key')

# Exists
if cache.exists('key'):
    print("Key exists")

# Update expiration
cache.expire('key', 120)
```

## Namespaces

```python
# Available namespaces
CacheNamespace.PRICES      # TTL: 15s
CacheNamespace.CANDLES     # TTL: 60s
CacheNamespace.INDICATORS  # TTL: 30s
CacheNamespace.SIGNALS     # TTL: 60s
CacheNamespace.MTF         # TTL: 120s
CacheNamespace.SESSION     # TTL: 3600s
CacheNamespace.CONFIG      # TTL: 600s
CacheNamespace.METADATA    # TTL: 300s

# Usage
cache.set('EUR_USD', 1.0950, namespace=CacheNamespace.PRICES)
price = cache.get('EUR_USD', namespace=CacheNamespace.PRICES)
```

## Batch Operations

```python
# Set multiple
cache.mset({
    'key1': 'value1',
    'key2': 'value2',
    'key3': 'value3'
}, ttl=60)

# Get multiple
values = cache.mget(['key1', 'key2', 'key3'])
```

## Cache-Aside Pattern

```python
# Automatic fetch and cache
result = cache.get_or_fetch(
    key='expensive_calc',
    fetch_func=lambda: expensive_calculation(),
    ttl=300
)
```

## Decorators

```python
# Cache function results
@cached(ttl=60, namespace=CacheNamespace.PRICES)
def fetch_price(symbol):
    return api.get_price(symbol)

# Invalidate cache
@cache_invalidate('prices:*')
def update_prices():
    # Update logic
    pass

# Custom key function
@cached(ttl=60, key_func=lambda symbol, tf: f"{symbol}_{tf}")
def get_data(symbol, timeframe):
    return data
```

## Pattern Operations

```python
# Find keys
keys = cache.keys('prices:*')

# Delete by pattern
count = cache.delete_pattern('temp:*')

# Clear namespace
cache.clear_namespace(CacheNamespace.PRICES)
```

## Pipeline Operations

```python
with cache.pipeline() as pipe:
    pipe.set('key1', 'value1')
    pipe.set('key2', 'value2')
    pipe.expire('key1', 60)
    results = pipe.execute()
```

## Pub/Sub

```python
# Publish
cache.publish('channel', {'data': 'value'})

# Subscribe
def handler(channel, message):
    print(f"Received: {message}")

cache.subscribe('channel', handler)
```

## Serialization

```python
# JSON (default)
cache.set('data', {'key': 'value'}, serializer='json')

# Pickle (for complex objects)
cache.set('df', dataframe, serializer='pickle')

# MessagePack (for performance)
cache.set('data', large_data, serializer='msgpack')
```

## Statistics

```python
# Get stats
stats = cache.get_stats()
print(f"Hit Rate: {stats['hit_rate']*100:.2f}%")
print(f"Total Keys: {stats['total_keys']}")

# Reset stats
cache.reset_stats()

# Get info
info = cache.get_info()
```

## Pandas DataFrames

```python
import pandas as pd

# Cache DataFrame
df = pd.DataFrame({'data': [1, 2, 3]})
cache.set('my_df', df, ttl=60, namespace=CacheNamespace.CANDLES)

# Retrieve DataFrame
cached_df = cache.get('my_df', namespace=CacheNamespace.CANDLES)
```

## Common Patterns

### Market Data Provider

```python
class MarketDataProvider:
    def __init__(self):
        self.cache = get_cache()

    def get_price(self, symbol):
        return self.cache.get_or_fetch(
            key=f"{symbol}:price",
            fetch_func=lambda: self._fetch_from_api(symbol),
            ttl=15,
            namespace=CacheNamespace.PRICES
        )
```

### Indicator Calculator

```python
class IndicatorCalculator:
    @cached(ttl=30, namespace=CacheNamespace.INDICATORS)
    def calculate_rsi(self, symbol, period=14):
        # Expensive calculation
        return rsi_value
```

### Signal Generator

```python
class SignalGenerator:
    @cached(ttl=60, namespace=CacheNamespace.SIGNALS)
    def generate_signal(self, symbol):
        # Signal logic
        return {'action': 'BUY', 'confidence': 0.85}

    @cache_invalidate('*', namespace=CacheNamespace.SIGNALS)
    def recalculate_all(self):
        # Recalculate logic
        pass
```

## Configuration

### Environment Variables

```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_MAX_CONNECTIONS=50
CACHE_DEFAULT_TTL=60
CACHE_ENABLE_COMPRESSION=true
CACHE_DEFAULT_SERIALIZER=json
```

### Docker Commands

```bash
# Start Redis
docker-compose up -d redis

# Stop Redis
docker-compose stop redis

# View logs
docker-compose logs -f redis

# Redis CLI
docker-compose exec redis redis-cli

# Check status
docker-compose ps redis
```

## Performance Guidelines

### TTL Recommendations

| Data Type | TTL | Namespace |
|-----------|-----|-----------|
| Real-time prices | 10-15s | PRICES |
| 1-minute candles | 60s | CANDLES |
| 1-hour candles | 300s | CANDLES |
| Daily candles | 3600s | CANDLES |
| Technical indicators | 30-60s | INDICATORS |
| Trading signals | 60-300s | SIGNALS |
| MTF analysis | 120-300s | MTF |
| Configuration | 600-3600s | CONFIG |

### When to Use Cache

✅ **Use for:**
- Frequently accessed data
- Expensive computations
- API rate-limited data
- Database queries with joins
- Session data

❌ **Don't cache:**
- Constantly changing data
- Rarely accessed data
- Sensitive information (without encryption)

## Troubleshooting

### Check Redis Connection

```python
cache = get_cache()
if cache._using_fallback:
    print("⚠️  Using fallback (Redis unavailable)")
else:
    print("✅ Redis connected")
```

### Monitor Performance

```python
stats = cache.get_stats()
print(f"Hit Rate: {stats['hit_rate']*100:.2f}%")
print(f"Memory: {stats.get('redis_memory', {}).get('used_memory_human', 'N/A')}")

for ns, ns_stats in stats['namespaces'].items():
    print(f"{ns}: {ns_stats['hit_rate']*100:.2f}%")
```

### Clear Cache

```python
# Clear specific namespace
cache.clear_namespace(CacheNamespace.PRICES)

# Clear by pattern
cache.delete_pattern('temp:*')

# Flush all (⚠️ use with caution)
cache.flush()
```

## Testing

```bash
# Interactive demo
python examples/cache_demo.py

# All demos
python examples/cache_demo.py --all

# Integration example
python examples/cache_integration_example.py
```

## Common Issues

**Issue**: Low hit rate
**Solution**: Increase TTLs, verify consistent key patterns

**Issue**: High memory usage
**Solution**: Reduce TTLs, clear unused namespaces, increase maxmemory

**Issue**: Stale data
**Solution**: Reduce TTLs, implement cache invalidation

**Issue**: Redis unavailable
**Solution**: Cache automatically falls back to in-memory mode

## Resources

- Full Documentation: `docs/CACHE_SYSTEM.md`
- Implementation: `src/core/cache.py`
- Examples: `examples/cache_demo.py`, `examples/cache_integration_example.py`
