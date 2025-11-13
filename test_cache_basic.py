#!/usr/bin/env python3
"""
Quick test script to verify Redis cache implementation.

This script tests basic cache functionality without requiring Redis to be running
(will use fallback cache if Redis is unavailable).
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.core.cache import (
        get_cache,
        CacheConfig,
        CacheNamespace,
        cached,
        cache_invalidate
    )
    print("✅ Cache module imported successfully")
except ImportError as e:
    print(f"❌ Failed to import cache module: {e}")
    sys.exit(1)

def test_basic_operations():
    """Test basic cache operations."""
    print("\n📝 Testing basic cache operations...")

    cache = get_cache()

    # Test set/get
    cache.set('test_key', 'test_value', ttl=60)
    value = cache.get('test_key')
    assert value == 'test_value', f"Expected 'test_value', got {value}"
    print("   ✅ Set/Get working")

    # Test exists
    assert cache.exists('test_key'), "Key should exist"
    print("   ✅ Exists working")

    # Test delete
    cache.delete('test_key')
    assert not cache.exists('test_key'), "Key should not exist after delete"
    print("   ✅ Delete working")

    return True

def test_namespaces():
    """Test cache namespaces."""
    print("\n📝 Testing cache namespaces...")

    cache = get_cache()

    # Test with namespace
    cache.set('EUR_USD', 1.0950, namespace=CacheNamespace.PRICES)
    price = cache.get('EUR_USD', namespace=CacheNamespace.PRICES)
    assert price == 1.0950, f"Expected 1.0950, got {price}"
    print("   ✅ Namespace working")

    return True

def test_batch_operations():
    """Test batch operations."""
    print("\n📝 Testing batch operations...")

    cache = get_cache()

    # Test mset
    data = {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'}
    cache.mset(data, ttl=60)

    # Test mget
    values = cache.mget(['key1', 'key2', 'key3'])
    assert values == ['value1', 'value2', 'value3'], f"Expected ['value1', 'value2', 'value3'], got {values}"
    print("   ✅ Batch operations working")

    return True

def test_cache_decorator():
    """Test cache decorator."""
    print("\n📝 Testing cache decorator...")

    call_count = [0]

    @cached(ttl=60)
    def expensive_function(x):
        call_count[0] += 1
        return x * 2

    # First call
    result1 = expensive_function(5)
    assert result1 == 10, f"Expected 10, got {result1}"
    assert call_count[0] == 1, f"Expected 1 call, got {call_count[0]}"

    # Second call (should use cache)
    result2 = expensive_function(5)
    assert result2 == 10, f"Expected 10, got {result2}"
    assert call_count[0] == 1, f"Expected 1 call (cached), got {call_count[0]}"

    print("   ✅ Cache decorator working")

    return True

def test_cache_statistics():
    """Test cache statistics."""
    print("\n📝 Testing cache statistics...")

    cache = get_cache()

    # Perform some operations
    cache.set('stat_test', 'value', ttl=60)
    cache.get('stat_test')
    cache.get('nonexistent_key')

    # Get stats
    stats = cache.get_stats()
    assert 'hits' in stats, "Stats should include 'hits'"
    assert 'misses' in stats, "Stats should include 'misses'"
    assert 'hit_rate' in stats, "Stats should include 'hit_rate'"

    print(f"   ✅ Statistics working (Hit rate: {stats['hit_rate']*100:.2f}%)")

    return True

def test_cache_info():
    """Test cache info."""
    print("\n📝 Testing cache info...")

    cache = get_cache()
    info = cache.get_info()

    assert 'config' in info, "Info should include 'config'"
    assert 'status' in info, "Info should include 'status'"
    assert 'stats' in info, "Info should include 'stats'"

    print(f"   ✅ Cache info working (Using fallback: {info['status']['using_fallback']})")

    return True

def main():
    """Run all tests."""
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║           Redis Cache Implementation - Basic Tests            ║")
    print("╚═══════════════════════════════════════════════════════════════╝")

    tests = [
        ("Basic Operations", test_basic_operations),
        ("Namespaces", test_namespaces),
        ("Batch Operations", test_batch_operations),
        ("Cache Decorator", test_cache_decorator),
        ("Statistics", test_cache_statistics),
        ("Cache Info", test_cache_info),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
            failed += 1
            import traceback
            traceback.print_exc()

    print("\n" + "="*65)
    print(f"Tests completed: {passed} passed, {failed} failed")

    if failed == 0:
        print("\n✅ All tests passed! Cache implementation is working correctly.")
        print("\nNote: If Redis is not running, cache is using in-memory fallback.")
        print("To use Redis, run: docker-compose up -d redis")
    else:
        print(f"\n❌ {failed} test(s) failed. Please check the errors above.")
        sys.exit(1)

    print("="*65)

if __name__ == '__main__':
    main()
