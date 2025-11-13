"""
Redis Cache System Demo for ScreenerIII

This script demonstrates all the features of the Redis caching layer:
- Basic cache operations (set, get, delete)
- Cache namespaces for different data types
- Batch operations (mget, mset)
- Cache decorators for function caching
- Cache-aside pattern
- Pipeline operations
- Pub/Sub messaging
- Cache statistics and monitoring
- Different serialization strategies
- In-memory fallback when Redis is unavailable
"""

import sys
import time
import logging
from pathlib import Path
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np

from src.core.cache import (
    CacheManager,
    CacheConfig,
    CacheNamespace,
    cached,
    cache_invalidate,
    get_cache,
    init_cache
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# ============================================================================
# Demo Functions
# ============================================================================

def demo_basic_operations():
    """Demonstrate basic cache operations."""
    print("\n" + "="*60)
    print("Demo 1: Basic Cache Operations")
    print("="*60)

    cache = get_cache()

    # Set and get simple values
    print("\n1. Setting and getting simple values...")
    cache.set('user:1', {'name': 'John Doe', 'email': 'john@example.com'}, ttl=60)
    user = cache.get('user:1')
    print(f"   User: {user}")

    # Check if key exists
    exists = cache.exists('user:1')
    print(f"   Key exists: {exists}")

    # Delete key
    print("\n2. Deleting key...")
    cache.delete('user:1')
    exists = cache.exists('user:1')
    print(f"   Key exists after delete: {exists}")

    # Store different data types
    print("\n3. Storing different data types...")
    cache.set('int_value', 42, ttl=60)
    cache.set('float_value', 3.14159, ttl=60)
    cache.set('string_value', 'Hello, Redis!', ttl=60)
    cache.set('list_value', [1, 2, 3, 4, 5], ttl=60)
    cache.set('dict_value', {'a': 1, 'b': 2, 'c': 3}, ttl=60)

    print(f"   Int: {cache.get('int_value')}")
    print(f"   Float: {cache.get('float_value')}")
    print(f"   String: {cache.get('string_value')}")
    print(f"   List: {cache.get('list_value')}")
    print(f"   Dict: {cache.get('dict_value')}")


def demo_namespaces():
    """Demonstrate cache namespaces."""
    print("\n" + "="*60)
    print("Demo 2: Cache Namespaces")
    print("="*60)

    cache = get_cache()

    # Use different namespaces
    print("\n1. Storing data in different namespaces...")

    # Prices namespace (TTL: 15 seconds)
    cache.set('EUR_USD', 1.0950, namespace=CacheNamespace.PRICES)
    cache.set('GBP_USD', 1.2650, namespace=CacheNamespace.PRICES)

    # Indicators namespace (TTL: 30 seconds)
    cache.set('EUR_USD:RSI', 65.5, namespace=CacheNamespace.INDICATORS)
    cache.set('EUR_USD:MACD', 0.0012, namespace=CacheNamespace.INDICATORS)

    # Signals namespace (TTL: 60 seconds)
    cache.set('EUR_USD:signal', {'action': 'BUY', 'confidence': 0.85}, namespace=CacheNamespace.SIGNALS)

    print("   Stored prices, indicators, and signals in separate namespaces")

    # Retrieve from namespaces
    print("\n2. Retrieving from namespaces...")
    price = cache.get('EUR_USD', namespace=CacheNamespace.PRICES)
    rsi = cache.get('EUR_USD:RSI', namespace=CacheNamespace.INDICATORS)
    signal = cache.get('EUR_USD:signal', namespace=CacheNamespace.SIGNALS)

    print(f"   Price: {price}")
    print(f"   RSI: {rsi}")
    print(f"   Signal: {signal}")

    # List keys in namespace
    print("\n3. Listing keys in namespace...")
    price_keys = cache.keys('*', namespace=CacheNamespace.PRICES)
    print(f"   Price keys: {price_keys}")

    # Clear entire namespace
    print("\n4. Clearing namespace...")
    count = cache.clear_namespace(CacheNamespace.PRICES)
    print(f"   Deleted {count} keys from prices namespace")


def demo_pandas_dataframes():
    """Demonstrate caching Pandas DataFrames."""
    print("\n" + "="*60)
    print("Demo 3: Caching Pandas DataFrames")
    print("="*60)

    cache = get_cache()

    # Create sample DataFrame
    print("\n1. Creating and caching DataFrame...")
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='1min'),
        'open': np.random.uniform(1.0, 1.1, 100),
        'high': np.random.uniform(1.05, 1.15, 100),
        'low': np.random.uniform(0.95, 1.05, 100),
        'close': np.random.uniform(1.0, 1.1, 100),
        'volume': np.random.randint(1000, 10000, 100)
    })

    print(f"   Original DataFrame shape: {df.shape}")
    print(f"   First 3 rows:")
    print(df.head(3))

    # Cache DataFrame
    cache.set('EUR_USD:candles:1min', df, ttl=60, namespace=CacheNamespace.CANDLES)
    print("\n   DataFrame cached successfully")

    # Retrieve DataFrame
    print("\n2. Retrieving cached DataFrame...")
    cached_df = cache.get('EUR_USD:candles:1min', namespace=CacheNamespace.CANDLES)

    if isinstance(cached_df, pd.DataFrame):
        print(f"   Retrieved DataFrame shape: {cached_df.shape}")
        print(f"   DataFrames are equal: {df.equals(cached_df)}")
    else:
        print(f"   ERROR: Retrieved object is not a DataFrame: {type(cached_df)}")


def demo_batch_operations():
    """Demonstrate batch operations."""
    print("\n" + "="*60)
    print("Demo 4: Batch Operations")
    print("="*60)

    cache = get_cache()

    # Multiple set operations
    print("\n1. Batch set (mset)...")
    pairs = {
        'EUR_USD': 1.0950,
        'GBP_USD': 1.2650,
        'USD_JPY': 149.50,
        'AUD_USD': 0.6550,
        'USD_CAD': 1.3750
    }

    start_time = time.time()
    cache.mset(pairs, ttl=60, namespace=CacheNamespace.PRICES)
    elapsed = time.time() - start_time

    print(f"   Set {len(pairs)} pairs in {elapsed*1000:.2f}ms")

    # Multiple get operations
    print("\n2. Batch get (mget)...")
    keys = list(pairs.keys())

    start_time = time.time()
    values = cache.mget(keys, namespace=CacheNamespace.PRICES)
    elapsed = time.time() - start_time

    print(f"   Retrieved {len(values)} values in {elapsed*1000:.2f}ms")
    for key, value in zip(keys, values):
        print(f"   {key}: {value}")


def demo_pipeline_operations():
    """Demonstrate pipeline operations."""
    print("\n" + "="*60)
    print("Demo 5: Pipeline Operations")
    print("="*60)

    cache = get_cache()

    print("\n1. Using pipeline for multiple operations...")

    # Execute multiple operations in a pipeline
    with cache.pipeline() as pipe:
        if pipe is not None:
            for i in range(10):
                pipe.set(f'pipeline_key_{i}', f'value_{i}')
                pipe.expire(f'pipeline_key_{i}', 60)

            results = pipe.execute()
            print(f"   Executed {len(results)} operations in pipeline")
        else:
            print("   Pipeline not available (using fallback cache)")

    # Verify values were set
    values = cache.mget([f'pipeline_key_{i}' for i in range(10)])
    print(f"\n2. Retrieved values: {values[:5]}... (showing first 5)")


def demo_cache_decorators():
    """Demonstrate cache decorators."""
    print("\n" + "="*60)
    print("Demo 6: Cache Decorators")
    print("="*60)

    # Function with caching decorator
    @cached(ttl=60, namespace=CacheNamespace.PRICES)
    def fetch_price(symbol: str) -> float:
        """Simulate fetching price from API."""
        print(f"   [API CALL] Fetching price for {symbol}...")
        time.sleep(0.1)  # Simulate API delay
        return np.random.uniform(1.0, 1.5)

    print("\n1. First call (cache miss, will fetch from API)...")
    start_time = time.time()
    price1 = fetch_price('EUR_USD')
    elapsed1 = time.time() - start_time
    print(f"   Price: {price1:.4f}, Time: {elapsed1*1000:.2f}ms")

    print("\n2. Second call (cache hit, no API call)...")
    start_time = time.time()
    price2 = fetch_price('EUR_USD')
    elapsed2 = time.time() - start_time
    print(f"   Price: {price2:.4f}, Time: {elapsed2*1000:.2f}ms")

    print(f"\n3. Speedup: {elapsed1/elapsed2:.2f}x faster")

    # Cache invalidation decorator
    @cache_invalidate('fetch_price:EUR_USD', namespace=CacheNamespace.PRICES)
    def update_price(symbol: str, new_price: float):
        """Update price and invalidate cache."""
        print(f"   Updating {symbol} to {new_price}")

    print("\n4. Invalidating cache...")
    update_price('EUR_USD', 1.1000)

    print("\n5. Third call (cache miss after invalidation)...")
    start_time = time.time()
    price3 = fetch_price('EUR_USD')
    elapsed3 = time.time() - start_time
    print(f"   Price: {price3:.4f}, Time: {elapsed3*1000:.2f}ms")


def demo_cache_aside_pattern():
    """Demonstrate cache-aside pattern."""
    print("\n" + "="*60)
    print("Demo 7: Cache-Aside Pattern")
    print("="*60)

    cache = get_cache()

    def expensive_computation(n: int) -> List[int]:
        """Simulate expensive computation."""
        print(f"   [COMPUTING] Calculating prime numbers up to {n}...")
        time.sleep(0.5)  # Simulate computation time

        primes = []
        for num in range(2, n + 1):
            is_prime = True
            for i in range(2, int(num ** 0.5) + 1):
                if num % i == 0:
                    is_prime = False
                    break
            if is_prime:
                primes.append(num)
        return primes

    print("\n1. First call (cache miss, will compute)...")
    start_time = time.time()
    primes1 = cache.get_or_fetch(
        'primes:1000',
        lambda: expensive_computation(1000),
        ttl=300
    )
    elapsed1 = time.time() - start_time
    print(f"   Found {len(primes1)} primes, Time: {elapsed1*1000:.2f}ms")

    print("\n2. Second call (cache hit, no computation)...")
    start_time = time.time()
    primes2 = cache.get_or_fetch(
        'primes:1000',
        lambda: expensive_computation(1000),
        ttl=300
    )
    elapsed2 = time.time() - start_time
    print(f"   Found {len(primes2)} primes, Time: {elapsed2*1000:.2f}ms")

    print(f"\n3. Speedup: {elapsed1/elapsed2:.2f}x faster")


def demo_pubsub():
    """Demonstrate Pub/Sub messaging."""
    print("\n" + "="*60)
    print("Demo 8: Pub/Sub Messaging")
    print("="*60)

    cache = get_cache()

    if cache._using_fallback:
        print("\n   Pub/Sub not available with fallback cache")
        return

    # Define message handler
    messages_received = []

    def message_handler(channel: str, message: Any):
        """Handle received messages."""
        messages_received.append((channel, message))
        print(f"   [RECEIVED] Channel: {channel}, Message: {message}")

    print("\n1. Subscribing to channels...")
    cache.subscribe(['signals', 'alerts'], message_handler)
    time.sleep(0.5)  # Give time for subscription to establish

    print("\n2. Publishing messages...")
    cache.publish('signals', {'symbol': 'EUR_USD', 'action': 'BUY', 'confidence': 0.85})
    time.sleep(0.2)

    cache.publish('alerts', {'type': 'PRICE_ALERT', 'symbol': 'GBP_USD', 'price': 1.2650})
    time.sleep(0.2)

    cache.publish('signals', {'symbol': 'USD_JPY', 'action': 'SELL', 'confidence': 0.72})
    time.sleep(0.2)

    print(f"\n3. Received {len(messages_received)} messages")


def demo_serialization_strategies():
    """Demonstrate different serialization strategies."""
    print("\n" + "="*60)
    print("Demo 9: Serialization Strategies")
    print("="*60)

    cache = get_cache()

    # Create test data
    test_data = {
        'timestamp': time.time(),
        'prices': [1.0950, 1.0951, 1.0952, 1.0953],
        'volume': 15000,
        'metadata': {'exchange': 'FOREX', 'session': 'NY'}
    }

    print("\n1. Testing JSON serialization...")
    start_time = time.time()
    cache.set('test:json', test_data, ttl=60, serializer='json')
    cached_json = cache.get('test:json', serializer='json')
    elapsed_json = time.time() - start_time
    print(f"   Time: {elapsed_json*1000:.2f}ms")
    print(f"   Data matches: {test_data == cached_json}")

    print("\n2. Testing Pickle serialization...")
    start_time = time.time()
    cache.set('test:pickle', test_data, ttl=60, serializer='pickle')
    cached_pickle = cache.get('test:pickle', serializer='pickle')
    elapsed_pickle = time.time() - start_time
    print(f"   Time: {elapsed_pickle*1000:.2f}ms")
    print(f"   Data matches: {test_data == cached_pickle}")

    print("\n3. Testing MessagePack serialization...")
    try:
        start_time = time.time()
        cache.set('test:msgpack', test_data, ttl=60, serializer='msgpack')
        cached_msgpack = cache.get('test:msgpack', serializer='msgpack')
        elapsed_msgpack = time.time() - start_time
        print(f"   Time: {elapsed_msgpack*1000:.2f}ms")
        print(f"   Data matches: {test_data == cached_msgpack}")
    except ImportError:
        print("   MessagePack not available")


def demo_statistics():
    """Demonstrate cache statistics."""
    print("\n" + "="*60)
    print("Demo 10: Cache Statistics")
    print("="*60)

    cache = get_cache()

    print("\n1. Performing cache operations to generate stats...")

    # Mix of hits and misses
    for i in range(20):
        cache.set(f'stats_key_{i}', i, ttl=60)

    for i in range(30):
        # First 20 will hit, last 10 will miss
        cache.get(f'stats_key_{i}')

    # Get statistics
    print("\n2. Cache statistics:")
    stats = cache.get_stats()

    print(f"   Total Requests: {stats['total_requests']}")
    print(f"   Hits: {stats['hits']}")
    print(f"   Misses: {stats['misses']}")
    print(f"   Sets: {stats['sets']}")
    print(f"   Deletes: {stats['deletes']}")
    print(f"   Errors: {stats['errors']}")
    print(f"   Hit Rate: {stats['hit_rate']*100:.2f}%")
    print(f"   Miss Rate: {stats['miss_rate']*100:.2f}%")
    print(f"   Using Fallback: {stats['using_fallback']}")

    # Namespace statistics
    if stats['namespaces']:
        print("\n3. Namespace statistics:")
        for ns_name, ns_stats in stats['namespaces'].items():
            print(f"   {ns_name}:")
            print(f"     Hits: {ns_stats['hits']}, Misses: {ns_stats['misses']}")
            print(f"     Hit Rate: {ns_stats['hit_rate']*100:.2f}%")

    # Redis memory info (if available)
    if 'redis_memory' in stats:
        print("\n4. Redis memory usage:")
        mem = stats['redis_memory']
        print(f"   Used Memory: {mem['used_memory_human']}")
        print(f"   Peak Memory: {mem['used_memory_peak_human']}")

    if 'total_keys' in stats:
        print(f"\n5. Total keys in cache: {stats['total_keys']}")


def demo_pattern_operations():
    """Demonstrate pattern-based operations."""
    print("\n" + "="*60)
    print("Demo 11: Pattern-Based Operations")
    print("="*60)

    cache = get_cache()

    print("\n1. Creating keys with patterns...")
    # Create keys for different currency pairs
    for pair in ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD']:
        cache.set(f'price:{pair}', np.random.uniform(1.0, 1.5), ttl=60)
        cache.set(f'indicator:{pair}:rsi', np.random.uniform(30, 70), ttl=60)
        cache.set(f'indicator:{pair}:macd', np.random.uniform(-0.01, 0.01), ttl=60)

    print("   Created 12 keys (4 pairs × 3 types)")

    # Find keys by pattern
    print("\n2. Finding keys by pattern...")
    price_keys = cache.keys('price:*')
    print(f"   Price keys: {price_keys}")

    usd_keys = cache.keys('*USD*')
    print(f"   USD-related keys: {len(usd_keys)} keys")

    rsi_keys = cache.keys('*:rsi')
    print(f"   RSI indicator keys: {rsi_keys}")

    # Delete by pattern
    print("\n3. Deleting keys by pattern...")
    deleted = cache.delete_pattern('indicator:EUR_USD:*')
    print(f"   Deleted {deleted} EUR_USD indicator keys")

    remaining = cache.keys('indicator:*')
    print(f"   Remaining indicator keys: {len(remaining)}")


def demo_info():
    """Display cache configuration and info."""
    print("\n" + "="*60)
    print("Demo 12: Cache Information")
    print("="*60)

    cache = get_cache()
    info = cache.get_info()

    print("\n1. Configuration:")
    for key, value in info['config'].items():
        print(f"   {key}: {value}")

    print("\n2. Status:")
    for key, value in info['status'].items():
        print(f"   {key}: {value}")

    print("\n3. Summary:")
    print(f"   Cache is {'working' if not info['status']['using_fallback'] else 'using fallback'}")
    print(f"   Redis available: {info['status']['redis_available']}")
    print(f"   MessagePack available: {info['status']['msgpack_available']}")


def demo_fallback():
    """Demonstrate fallback to in-memory cache."""
    print("\n" + "="*60)
    print("Demo 13: Fallback to In-Memory Cache")
    print("="*60)

    # Create cache with invalid Redis connection
    print("\n1. Creating cache with invalid Redis host...")
    config = CacheConfig(
        redis_host='invalid_host',
        redis_port=9999,
        fallback_to_memory=True
    )

    # This will create a new instance - reset singleton for demo
    CacheManager._instance = None
    fallback_cache = CacheManager(config)

    print(f"   Using fallback: {fallback_cache._using_fallback}")

    # Test operations with fallback
    print("\n2. Testing operations with fallback cache...")
    fallback_cache.set('test_key', 'test_value', ttl=60)
    value = fallback_cache.get('test_key')
    print(f"   Stored and retrieved value: {value}")

    # Clean up
    print("\n3. Restoring original cache manager...")
    CacheManager._instance = None
    get_cache()  # Reinitialize with default config


# ============================================================================
# Main Demo Runner
# ============================================================================

def run_all_demos():
    """Run all cache demos."""
    print("\n")
    print("="*60)
    print(" ScreenerIII Redis Cache System Demo")
    print("="*60)

    demos = [
        demo_basic_operations,
        demo_namespaces,
        demo_pandas_dataframes,
        demo_batch_operations,
        demo_pipeline_operations,
        demo_cache_decorators,
        demo_cache_aside_pattern,
        demo_pubsub,
        demo_serialization_strategies,
        demo_statistics,
        demo_pattern_operations,
        demo_info,
        # demo_fallback,  # Skip by default as it resets singleton
    ]

    for i, demo in enumerate(demos, 1):
        try:
            demo()
        except Exception as e:
            print(f"\n   ERROR in {demo.__name__}: {e}")
            import traceback
            traceback.print_exc()

        # Small delay between demos
        if i < len(demos):
            time.sleep(0.5)

    print("\n" + "="*60)
    print(" Demo Complete!")
    print("="*60)


def interactive_demo():
    """Interactive demo menu."""
    demos = {
        '1': ('Basic Operations', demo_basic_operations),
        '2': ('Cache Namespaces', demo_namespaces),
        '3': ('Pandas DataFrames', demo_pandas_dataframes),
        '4': ('Batch Operations', demo_batch_operations),
        '5': ('Pipeline Operations', demo_pipeline_operations),
        '6': ('Cache Decorators', demo_cache_decorators),
        '7': ('Cache-Aside Pattern', demo_cache_aside_pattern),
        '8': ('Pub/Sub Messaging', demo_pubsub),
        '9': ('Serialization Strategies', demo_serialization_strategies),
        '10': ('Statistics', demo_statistics),
        '11': ('Pattern Operations', demo_pattern_operations),
        '12': ('Cache Information', demo_info),
        '13': ('Fallback Cache', demo_fallback),
    }

    while True:
        print("\n" + "="*60)
        print(" ScreenerIII Cache Demo - Interactive Mode")
        print("="*60)
        print("\nAvailable demos:")

        for key, (name, _) in sorted(demos.items()):
            print(f"  {key}. {name}")

        print("\n  0. Run all demos")
        print("  q. Quit")

        choice = input("\nSelect demo (number or 'q' to quit): ").strip().lower()

        if choice == 'q':
            print("\nGoodbye!")
            break
        elif choice == '0':
            run_all_demos()
        elif choice in demos:
            try:
                _, demo_func = demos[choice]
                demo_func()
            except Exception as e:
                print(f"\nERROR: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("\nInvalid choice. Please try again.")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--all':
        # Run all demos
        run_all_demos()
    else:
        # Interactive mode
        interactive_demo()
