"""
Redis-based caching layer for ScreenerIII.

This module provides a comprehensive caching system with:
- Redis connection management with automatic reconnection
- Fallback to in-memory cache if Redis is unavailable
- Multiple serialization strategies (JSON, Pickle, MessagePack)
- Cache namespaces for different data types
- Batch operations and pipelines
- Pub/Sub for real-time updates
- Cache decorators for easy function caching
- Cache statistics and monitoring
"""

import json
import pickle
import time
import logging
import functools
import threading
from typing import Any, Optional, Callable, Dict, List, Tuple, Union
from dataclasses import dataclass, field
from datetime import timedelta
from contextlib import contextmanager
from collections import defaultdict
import os

try:
    import redis
    from redis.connection import ConnectionPool
    from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

try:
    import msgpack
    MSGPACK_AVAILABLE = True
except ImportError:
    MSGPACK_AVAILABLE = False

import zlib
import pandas as pd
import numpy as np


logger = logging.getLogger(__name__)


# ============================================================================
# Cache Configuration
# ============================================================================

@dataclass
class CacheConfig:
    """Configuration for cache manager."""

    # Redis connection settings
    redis_host: str = os.getenv('REDIS_HOST', 'localhost')
    redis_port: int = int(os.getenv('REDIS_PORT', '6379'))
    redis_db: int = int(os.getenv('REDIS_DB', '0'))
    redis_password: Optional[str] = os.getenv('REDIS_PASSWORD', None)

    # Connection pool settings
    max_connections: int = int(os.getenv('REDIS_MAX_CONNECTIONS', '50'))
    socket_timeout: int = int(os.getenv('REDIS_SOCKET_TIMEOUT', '5'))
    socket_connect_timeout: int = int(os.getenv('REDIS_CONNECT_TIMEOUT', '5'))
    socket_keepalive: bool = True
    health_check_interval: int = 30

    # Cache behavior
    default_ttl: int = 60  # seconds
    enable_compression: bool = True
    compression_threshold: int = 1024  # bytes
    fallback_to_memory: bool = True

    # Monitoring
    enable_stats: bool = True
    stats_reset_interval: int = 3600  # seconds

    # Serialization
    default_serializer: str = 'json'  # 'json', 'pickle', 'msgpack'


@dataclass
class CacheStats:
    """Statistics for cache operations."""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    total_requests: int = 0
    start_time: float = field(default_factory=time.time)

    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests

    def miss_rate(self) -> float:
        """Calculate cache miss rate."""
        return 1.0 - self.hit_rate()

    def uptime(self) -> float:
        """Get uptime in seconds."""
        return time.time() - self.start_time

    def reset(self):
        """Reset all statistics."""
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.errors = 0
        self.total_requests = 0
        self.start_time = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'sets': self.sets,
            'deletes': self.deletes,
            'errors': self.errors,
            'total_requests': self.total_requests,
            'hit_rate': self.hit_rate(),
            'miss_rate': self.miss_rate(),
            'uptime': self.uptime()
        }


# ============================================================================
# Cache Namespaces
# ============================================================================

class CacheNamespace:
    """Predefined cache namespaces with default TTLs."""

    PRICES = ('prices', 15)           # Real-time price data
    CANDLES = ('candles', 60)         # Historical candles
    INDICATORS = ('indicators', 30)   # Calculated indicators
    SIGNALS = ('signals', 60)         # Trading signals
    MTF = ('mtf', 120)                # Multi-timeframe data
    SESSION = ('session', 3600)       # Session data
    CONFIG = ('config', 600)          # Configuration cache
    METADATA = ('metadata', 300)      # Metadata cache

    @classmethod
    def format_key(cls, namespace: Tuple[str, int], key: str) -> str:
        """Format a cache key with namespace prefix."""
        return f"{namespace[0]}:{key}"

    @classmethod
    def get_ttl(cls, namespace: Tuple[str, int]) -> int:
        """Get TTL for a namespace."""
        return namespace[1]


# ============================================================================
# Serializers
# ============================================================================

class Serializer:
    """Base class for serializers."""

    @staticmethod
    def serialize(data: Any) -> bytes:
        """Serialize data to bytes."""
        raise NotImplementedError

    @staticmethod
    def deserialize(data: bytes) -> Any:
        """Deserialize bytes to data."""
        raise NotImplementedError


class JsonSerializer(Serializer):
    """JSON serializer with NumPy and Pandas support."""

    @staticmethod
    def serialize(data: Any) -> bytes:
        """Serialize data to JSON bytes."""
        def default(obj):
            if isinstance(obj, (np.integer, np.floating)):
                return obj.item()
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, pd.DataFrame):
                return {
                    '__type__': 'DataFrame',
                    'data': obj.to_dict('split')
                }
            elif isinstance(obj, pd.Series):
                return {
                    '__type__': 'Series',
                    'data': obj.to_dict()
                }
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        return json.dumps(data, default=default).encode('utf-8')

    @staticmethod
    def deserialize(data: bytes) -> Any:
        """Deserialize JSON bytes to data."""
        def object_hook(obj):
            if isinstance(obj, dict) and obj.get('__type__') == 'DataFrame':
                df_data = obj['data']
                return pd.DataFrame(
                    df_data['data'],
                    index=df_data['index'],
                    columns=df_data['columns']
                )
            elif isinstance(obj, dict) and obj.get('__type__') == 'Series':
                return pd.Series(obj['data'])
            return obj

        return json.loads(data.decode('utf-8'), object_hook=object_hook)


class PickleSerializer(Serializer):
    """Pickle serializer for complex Python objects."""

    @staticmethod
    def serialize(data: Any) -> bytes:
        """Serialize data using pickle."""
        return pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def deserialize(data: bytes) -> Any:
        """Deserialize pickle data."""
        return pickle.loads(data)


class MsgPackSerializer(Serializer):
    """MessagePack serializer for performance."""

    @staticmethod
    def serialize(data: Any) -> bytes:
        """Serialize data using msgpack."""
        if not MSGPACK_AVAILABLE:
            raise ImportError("msgpack is not installed")

        def default(obj):
            if isinstance(obj, (np.integer, np.floating)):
                return obj.item()
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, (pd.DataFrame, pd.Series)):
                # Fall back to pickle for pandas objects
                return {'__pickle__': pickle.dumps(obj)}
            raise TypeError(f"Object of type {type(obj)} is not msgpack serializable")

        return msgpack.packb(data, default=default, use_bin_type=True)

    @staticmethod
    def deserialize(data: bytes) -> Any:
        """Deserialize msgpack data."""
        if not MSGPACK_AVAILABLE:
            raise ImportError("msgpack is not installed")

        def object_hook(obj):
            if isinstance(obj, dict) and '__pickle__' in obj:
                return pickle.loads(obj['__pickle__'])
            return obj

        return msgpack.unpackb(data, object_hook=object_hook, raw=False)


class SerializerFactory:
    """Factory for creating serializers."""

    _serializers = {
        'json': JsonSerializer,
        'pickle': PickleSerializer,
        'msgpack': MsgPackSerializer
    }

    @classmethod
    def get(cls, name: str) -> Serializer:
        """Get serializer by name."""
        if name not in cls._serializers:
            raise ValueError(f"Unknown serializer: {name}")
        return cls._serializers[name]

    @classmethod
    def register(cls, name: str, serializer: type):
        """Register a custom serializer."""
        cls._serializers[name] = serializer


# ============================================================================
# In-Memory Cache (Fallback)
# ============================================================================

class InMemoryCache:
    """Simple in-memory cache as fallback when Redis is unavailable."""

    def __init__(self, max_size: int = 1000):
        """Initialize in-memory cache."""
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._max_size = max_size
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if expiry == 0 or time.time() < expiry:
                    return value
                else:
                    del self._cache[key]
            return None

    def set(self, key: str, value: Any, ttl: int = 0):
        """Set value in cache with optional TTL."""
        with self._lock:
            # Evict oldest items if cache is full
            if len(self._cache) >= self._max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]

            expiry = time.time() + ttl if ttl > 0 else 0
            self._cache[key] = (value, expiry)

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        return self.get(key) is not None

    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()

    def keys(self, pattern: str = '*') -> List[str]:
        """Get all keys matching pattern."""
        with self._lock:
            if pattern == '*':
                return list(self._cache.keys())
            # Simple pattern matching
            import fnmatch
            return [k for k in self._cache.keys() if fnmatch.fnmatch(k, pattern)]


# ============================================================================
# Cache Manager (Singleton)
# ============================================================================

class CacheManager:
    """
    Singleton cache manager with Redis backend and in-memory fallback.

    Features:
    - Automatic connection management and reconnection
    - Multiple serialization strategies
    - Cache namespaces with default TTLs
    - Batch operations and pipelines
    - Pub/Sub for real-time updates
    - Comprehensive statistics
    - Fallback to in-memory cache
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, config: Optional[CacheConfig] = None):
        """Ensure singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, config: Optional[CacheConfig] = None):
        """Initialize cache manager."""
        if self._initialized:
            return

        self.config = config or CacheConfig()
        self._redis_client: Optional[redis.Redis] = None
        self._connection_pool: Optional[ConnectionPool] = None
        self._fallback_cache = InMemoryCache(max_size=1000)
        self._using_fallback = False
        self._stats = CacheStats()
        self._namespace_stats: Dict[str, CacheStats] = defaultdict(CacheStats)
        self._pubsub_thread = None
        self._initialized = True

        # Initialize Redis connection
        self._connect()

        logger.info(
            f"CacheManager initialized "
            f"(Redis: {not self._using_fallback}, "
            f"Host: {self.config.redis_host}:{self.config.redis_port})"
        )

    def _connect(self) -> bool:
        """Connect to Redis server."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis library not installed, using in-memory fallback")
            self._using_fallback = True
            return False

        try:
            # Create connection pool
            self._connection_pool = ConnectionPool(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                password=self.config.redis_password,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                socket_keepalive=self.config.socket_keepalive,
                health_check_interval=self.config.health_check_interval,
                decode_responses=False  # We handle encoding/decoding
            )

            # Create Redis client
            self._redis_client = redis.Redis(
                connection_pool=self._connection_pool
            )

            # Test connection
            self._redis_client.ping()

            self._using_fallback = False
            logger.info("Successfully connected to Redis")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            if self.config.fallback_to_memory:
                logger.warning("Falling back to in-memory cache")
                self._using_fallback = True
            else:
                raise
            return False

    def _reconnect(self) -> bool:
        """Attempt to reconnect to Redis."""
        logger.info("Attempting to reconnect to Redis...")
        return self._connect()

    def _ensure_connection(self) -> bool:
        """Ensure Redis connection is active."""
        if self._using_fallback:
            return False

        try:
            self._redis_client.ping()
            return True
        except (RedisConnectionError, RedisError):
            logger.warning("Redis connection lost, attempting reconnect...")
            return self._reconnect()

    def _get_serializer(self, serializer: Optional[str] = None) -> Serializer:
        """Get serializer instance."""
        name = serializer or self.config.default_serializer
        return SerializerFactory.get(name)

    def _compress(self, data: bytes) -> bytes:
        """Compress data if it exceeds threshold."""
        if (self.config.enable_compression and
            len(data) > self.config.compression_threshold):
            return zlib.compress(data)
        return data

    def _decompress(self, data: bytes) -> bytes:
        """Decompress data if it was compressed."""
        if self.config.enable_compression:
            try:
                return zlib.decompress(data)
            except zlib.error:
                # Data wasn't compressed
                return data
        return data

    def _update_stats(self, operation: str, namespace: Optional[str] = None):
        """Update cache statistics."""
        if not self.config.enable_stats:
            return

        # Update global stats
        if operation == 'hit':
            self._stats.hits += 1
            self._stats.total_requests += 1
        elif operation == 'miss':
            self._stats.misses += 1
            self._stats.total_requests += 1
        elif operation == 'set':
            self._stats.sets += 1
        elif operation == 'delete':
            self._stats.deletes += 1
        elif operation == 'error':
            self._stats.errors += 1

        # Update namespace stats
        if namespace:
            ns_stats = self._namespace_stats[namespace]
            if operation == 'hit':
                ns_stats.hits += 1
                ns_stats.total_requests += 1
            elif operation == 'miss':
                ns_stats.misses += 1
                ns_stats.total_requests += 1
            elif operation == 'set':
                ns_stats.sets += 1
            elif operation == 'delete':
                ns_stats.deletes += 1
            elif operation == 'error':
                ns_stats.errors += 1

    # ========================================================================
    # Core Cache Operations
    # ========================================================================

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        serializer: Optional[str] = None,
        namespace: Optional[Tuple[str, int]] = None
    ) -> bool:
        """
        Set a value in cache with optional TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None = use default)
            serializer: Serializer to use ('json', 'pickle', 'msgpack')
            namespace: Cache namespace tuple (name, default_ttl)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Apply namespace
            if namespace:
                key = CacheNamespace.format_key(namespace, key)
                ttl = ttl or CacheNamespace.get_ttl(namespace)
                ns_name = namespace[0]
            else:
                ns_name = None

            # Use default TTL if not specified
            if ttl is None:
                ttl = self.config.default_ttl

            # Serialize value
            ser = self._get_serializer(serializer)
            data = ser.serialize(value)

            # Compress if needed
            data = self._compress(data)

            # Store in cache
            if self._using_fallback:
                self._fallback_cache.set(key, data, ttl)
            else:
                if not self._ensure_connection():
                    if self.config.fallback_to_memory:
                        self._fallback_cache.set(key, data, ttl)
                    return False

                if ttl > 0:
                    self._redis_client.setex(key, ttl, data)
                else:
                    self._redis_client.set(key, data)

            self._update_stats('set', ns_name)
            return True

        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            self._update_stats('error', ns_name if namespace else None)
            return False

    def get(
        self,
        key: str,
        serializer: Optional[str] = None,
        namespace: Optional[Tuple[str, int]] = None
    ) -> Optional[Any]:
        """
        Get a value from cache.

        Args:
            key: Cache key
            serializer: Serializer to use ('json', 'pickle', 'msgpack')
            namespace: Cache namespace tuple (name, default_ttl)

        Returns:
            Cached value or None if not found/expired
        """
        try:
            # Apply namespace
            if namespace:
                key = CacheNamespace.format_key(namespace, key)
                ns_name = namespace[0]
            else:
                ns_name = None

            # Get from cache
            if self._using_fallback:
                data = self._fallback_cache.get(key)
            else:
                if not self._ensure_connection():
                    if self.config.fallback_to_memory:
                        data = self._fallback_cache.get(key)
                    else:
                        self._update_stats('miss', ns_name)
                        return None
                else:
                    data = self._redis_client.get(key)

            if data is None:
                self._update_stats('miss', ns_name)
                return None

            # Decompress if needed
            data = self._decompress(data)

            # Deserialize value
            ser = self._get_serializer(serializer)
            value = ser.deserialize(data)

            self._update_stats('hit', ns_name)
            return value

        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            self._update_stats('error', ns_name if namespace else None)
            return None

    def delete(self, key: str, namespace: Optional[Tuple[str, int]] = None) -> bool:
        """
        Delete a key from cache.

        Args:
            key: Cache key
            namespace: Cache namespace tuple (name, default_ttl)

        Returns:
            True if key was deleted, False otherwise
        """
        try:
            # Apply namespace
            if namespace:
                key = CacheNamespace.format_key(namespace, key)
                ns_name = namespace[0]
            else:
                ns_name = None

            # Delete from cache
            if self._using_fallback:
                result = self._fallback_cache.delete(key)
            else:
                if not self._ensure_connection():
                    if self.config.fallback_to_memory:
                        result = self._fallback_cache.delete(key)
                    else:
                        return False
                else:
                    result = self._redis_client.delete(key) > 0

            if result:
                self._update_stats('delete', ns_name)

            return result

        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            self._update_stats('error', ns_name if namespace else None)
            return False

    def exists(self, key: str, namespace: Optional[Tuple[str, int]] = None) -> bool:
        """
        Check if a key exists in cache.

        Args:
            key: Cache key
            namespace: Cache namespace tuple (name, default_ttl)

        Returns:
            True if key exists, False otherwise
        """
        try:
            # Apply namespace
            if namespace:
                key = CacheNamespace.format_key(namespace, key)

            # Check existence
            if self._using_fallback:
                return self._fallback_cache.exists(key)
            else:
                if not self._ensure_connection():
                    if self.config.fallback_to_memory:
                        return self._fallback_cache.exists(key)
                    return False
                return self._redis_client.exists(key) > 0

        except Exception as e:
            logger.error(f"Error checking cache key existence {key}: {e}")
            return False

    def expire(self, key: str, ttl: int, namespace: Optional[Tuple[str, int]] = None) -> bool:
        """
        Update the expiration time of a key.

        Args:
            key: Cache key
            ttl: New time-to-live in seconds
            namespace: Cache namespace tuple (name, default_ttl)

        Returns:
            True if expiration was updated, False otherwise
        """
        try:
            # Apply namespace
            if namespace:
                key = CacheNamespace.format_key(namespace, key)

            # Update expiration
            if self._using_fallback:
                # In-memory cache doesn't support updating expiration
                # Would need to re-set the value
                return False
            else:
                if not self._ensure_connection():
                    return False
                return self._redis_client.expire(key, ttl)

        except Exception as e:
            logger.error(f"Error updating expiration for key {key}: {e}")
            return False

    def get_or_fetch(
        self,
        key: str,
        fetch_func: Callable[[], Any],
        ttl: Optional[int] = None,
        serializer: Optional[str] = None,
        namespace: Optional[Tuple[str, int]] = None
    ) -> Any:
        """
        Get value from cache or fetch if not present (cache-aside pattern).

        Args:
            key: Cache key
            fetch_func: Function to call if cache miss
            ttl: Time-to-live in seconds
            serializer: Serializer to use
            namespace: Cache namespace tuple (name, default_ttl)

        Returns:
            Cached or fetched value
        """
        # Try to get from cache
        value = self.get(key, serializer, namespace)

        if value is not None:
            return value

        # Cache miss - fetch value
        try:
            value = fetch_func()

            # Store in cache
            self.set(key, value, ttl, serializer, namespace)

            return value

        except Exception as e:
            logger.error(f"Error fetching value for key {key}: {e}")
            raise

    # ========================================================================
    # Batch Operations
    # ========================================================================

    def mget(
        self,
        keys: List[str],
        serializer: Optional[str] = None,
        namespace: Optional[Tuple[str, int]] = None
    ) -> List[Optional[Any]]:
        """
        Get multiple values from cache.

        Args:
            keys: List of cache keys
            serializer: Serializer to use
            namespace: Cache namespace tuple (name, default_ttl)

        Returns:
            List of values (None for missing keys)
        """
        if not keys:
            return []

        try:
            # Apply namespace
            if namespace:
                keys = [CacheNamespace.format_key(namespace, k) for k in keys]

            # Get from cache
            if self._using_fallback:
                values = [self._fallback_cache.get(k) for k in keys]
            else:
                if not self._ensure_connection():
                    if self.config.fallback_to_memory:
                        values = [self._fallback_cache.get(k) for k in keys]
                    else:
                        return [None] * len(keys)
                else:
                    values = self._redis_client.mget(keys)

            # Deserialize values
            ser = self._get_serializer(serializer)
            result = []
            for data in values:
                if data is None:
                    result.append(None)
                else:
                    try:
                        data = self._decompress(data)
                        result.append(ser.deserialize(data))
                    except Exception as e:
                        logger.error(f"Error deserializing value: {e}")
                        result.append(None)

            return result

        except Exception as e:
            logger.error(f"Error in mget: {e}")
            return [None] * len(keys)

    def mset(
        self,
        mapping: Dict[str, Any],
        ttl: Optional[int] = None,
        serializer: Optional[str] = None,
        namespace: Optional[Tuple[str, int]] = None
    ) -> bool:
        """
        Set multiple values in cache.

        Args:
            mapping: Dictionary of key-value pairs
            ttl: Time-to-live in seconds (applied to all keys)
            serializer: Serializer to use
            namespace: Cache namespace tuple (name, default_ttl)

        Returns:
            True if successful, False otherwise
        """
        if not mapping:
            return True

        try:
            # Apply namespace and serialize
            ser = self._get_serializer(serializer)
            processed = {}

            for key, value in mapping.items():
                if namespace:
                    key = CacheNamespace.format_key(namespace, key)
                data = ser.serialize(value)
                data = self._compress(data)
                processed[key] = data

            # Set in cache
            if self._using_fallback:
                for key, data in processed.items():
                    self._fallback_cache.set(key, data, ttl or self.config.default_ttl)
            else:
                if not self._ensure_connection():
                    if self.config.fallback_to_memory:
                        for key, data in processed.items():
                            self._fallback_cache.set(key, data, ttl or self.config.default_ttl)
                    return False
                else:
                    # Use pipeline for atomic operation
                    pipe = self._redis_client.pipeline()
                    for key, data in processed.items():
                        if ttl:
                            pipe.setex(key, ttl, data)
                        else:
                            pipe.set(key, data)
                    pipe.execute()

            return True

        except Exception as e:
            logger.error(f"Error in mset: {e}")
            return False

    @contextmanager
    def pipeline(self):
        """
        Context manager for Redis pipeline operations.

        Yields:
            Redis pipeline object

        Example:
            with cache.pipeline() as pipe:
                pipe.set('key1', 'value1')
                pipe.set('key2', 'value2')
                results = pipe.execute()
        """
        if self._using_fallback:
            # Fallback doesn't support pipelines
            yield None
            return

        if not self._ensure_connection():
            yield None
            return

        pipe = self._redis_client.pipeline()
        try:
            yield pipe
        finally:
            pass

    # ========================================================================
    # Pattern-based Operations
    # ========================================================================

    def keys(self, pattern: str = '*', namespace: Optional[Tuple[str, int]] = None) -> List[str]:
        """
        Get all keys matching pattern.

        Args:
            pattern: Key pattern (supports wildcards)
            namespace: Cache namespace tuple (name, default_ttl)

        Returns:
            List of matching keys
        """
        try:
            # Apply namespace
            if namespace:
                pattern = CacheNamespace.format_key(namespace, pattern)

            # Get keys
            if self._using_fallback:
                keys = self._fallback_cache.keys(pattern)
            else:
                if not self._ensure_connection():
                    if self.config.fallback_to_memory:
                        keys = self._fallback_cache.keys(pattern)
                    else:
                        return []
                else:
                    keys = [k.decode('utf-8') if isinstance(k, bytes) else k
                           for k in self._redis_client.keys(pattern)]

            return keys

        except Exception as e:
            logger.error(f"Error getting keys with pattern {pattern}: {e}")
            return []

    def delete_pattern(self, pattern: str, namespace: Optional[Tuple[str, int]] = None) -> int:
        """
        Delete all keys matching pattern.

        Args:
            pattern: Key pattern (supports wildcards)
            namespace: Cache namespace tuple (name, default_ttl)

        Returns:
            Number of keys deleted
        """
        try:
            keys = self.keys(pattern, namespace)

            if not keys:
                return 0

            # Delete keys
            if self._using_fallback:
                count = sum(1 for k in keys if self._fallback_cache.delete(k))
            else:
                if not self._ensure_connection():
                    if self.config.fallback_to_memory:
                        count = sum(1 for k in keys if self._fallback_cache.delete(k))
                    else:
                        return 0
                else:
                    count = self._redis_client.delete(*keys)

            return count

        except Exception as e:
            logger.error(f"Error deleting keys with pattern {pattern}: {e}")
            return 0

    def clear_namespace(self, namespace: Tuple[str, int]) -> int:
        """
        Clear all keys in a namespace.

        Args:
            namespace: Cache namespace tuple (name, default_ttl)

        Returns:
            Number of keys deleted
        """
        pattern = f"{namespace[0]}:*"
        return self.delete_pattern(pattern)

    # ========================================================================
    # Pub/Sub Operations
    # ========================================================================

    def publish(self, channel: str, message: Any, serializer: Optional[str] = None) -> int:
        """
        Publish a message to a channel.

        Args:
            channel: Channel name
            message: Message to publish
            serializer: Serializer to use

        Returns:
            Number of subscribers that received the message
        """
        if self._using_fallback:
            logger.warning("Pub/Sub not supported with fallback cache")
            return 0

        try:
            if not self._ensure_connection():
                return 0

            # Serialize message
            ser = self._get_serializer(serializer)
            data = ser.serialize(message)

            return self._redis_client.publish(channel, data)

        except Exception as e:
            logger.error(f"Error publishing to channel {channel}: {e}")
            return 0

    def subscribe(
        self,
        channels: Union[str, List[str]],
        callback: Callable[[str, Any], None],
        serializer: Optional[str] = None
    ):
        """
        Subscribe to one or more channels.

        Args:
            channels: Channel name or list of channel names
            callback: Function to call when message received (channel, message)
            serializer: Serializer to use for deserializing messages
        """
        if self._using_fallback:
            logger.warning("Pub/Sub not supported with fallback cache")
            return

        if isinstance(channels, str):
            channels = [channels]

        try:
            if not self._ensure_connection():
                return

            pubsub = self._redis_client.pubsub()
            pubsub.subscribe(*channels)

            ser = self._get_serializer(serializer)

            def listener():
                for message in pubsub.listen():
                    if message['type'] == 'message':
                        try:
                            channel = message['channel'].decode('utf-8')
                            data = ser.deserialize(message['data'])
                            callback(channel, data)
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")

            # Start listener thread
            import threading
            thread = threading.Thread(target=listener, daemon=True)
            thread.start()

            logger.info(f"Subscribed to channels: {channels}")

        except Exception as e:
            logger.error(f"Error subscribing to channels: {e}")

    # ========================================================================
    # Statistics and Monitoring
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        stats = self._stats.to_dict()
        stats['using_fallback'] = self._using_fallback
        stats['redis_connected'] = not self._using_fallback

        # Add namespace stats
        namespace_stats = {}
        for ns_name, ns_stats in self._namespace_stats.items():
            namespace_stats[ns_name] = ns_stats.to_dict()
        stats['namespaces'] = namespace_stats

        # Add Redis info if available
        if not self._using_fallback:
            try:
                if self._ensure_connection():
                    info = self._redis_client.info('memory')
                    stats['redis_memory'] = {
                        'used_memory': info.get('used_memory', 0),
                        'used_memory_human': info.get('used_memory_human', 'N/A'),
                        'used_memory_peak': info.get('used_memory_peak', 0),
                        'used_memory_peak_human': info.get('used_memory_peak_human', 'N/A'),
                    }

                    # Get key count
                    stats['total_keys'] = self._redis_client.dbsize()
            except Exception as e:
                logger.error(f"Error getting Redis info: {e}")

        return stats

    def reset_stats(self):
        """Reset all statistics."""
        self._stats.reset()
        self._namespace_stats.clear()
        logger.info("Cache statistics reset")

    def get_info(self) -> Dict[str, Any]:
        """
        Get detailed cache information.

        Returns:
            Dictionary with cache information
        """
        info = {
            'config': {
                'redis_host': self.config.redis_host,
                'redis_port': self.config.redis_port,
                'redis_db': self.config.redis_db,
                'max_connections': self.config.max_connections,
                'default_ttl': self.config.default_ttl,
                'enable_compression': self.config.enable_compression,
                'default_serializer': self.config.default_serializer,
            },
            'status': {
                'using_fallback': self._using_fallback,
                'redis_available': REDIS_AVAILABLE,
                'msgpack_available': MSGPACK_AVAILABLE,
            },
            'stats': self.get_stats()
        }

        return info

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def flush(self) -> bool:
        """
        Flush all cache entries.

        WARNING: This will delete ALL keys in the current database!

        Returns:
            True if successful, False otherwise
        """
        try:
            if self._using_fallback:
                self._fallback_cache.clear()
            else:
                if not self._ensure_connection():
                    if self.config.fallback_to_memory:
                        self._fallback_cache.clear()
                    return False
                self._redis_client.flushdb()

            logger.warning("Cache flushed - all keys deleted")
            return True

        except Exception as e:
            logger.error(f"Error flushing cache: {e}")
            return False

    def close(self):
        """Close cache connections."""
        try:
            if self._connection_pool:
                self._connection_pool.disconnect()
                logger.info("Cache connections closed")
        except Exception as e:
            logger.error(f"Error closing cache connections: {e}")


# ============================================================================
# Cache Decorators
# ============================================================================

def cached(
    ttl: int = 60,
    namespace: Optional[Tuple[str, int]] = None,
    key_func: Optional[Callable] = None,
    serializer: Optional[str] = None
):
    """
    Decorator for caching function results.

    Args:
        ttl: Time-to-live in seconds
        namespace: Cache namespace tuple (name, default_ttl)
        key_func: Function to generate cache key from arguments
        serializer: Serializer to use

    Example:
        @cached(ttl=60, namespace=CacheNamespace.PRICES)
        def get_price(symbol):
            return fetch_price_from_api(symbol)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key: function name + arguments
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)

            # Get cache manager
            cache = CacheManager()

            # Try to get from cache
            value = cache.get(cache_key, serializer, namespace)

            if value is not None:
                return value

            # Cache miss - call function
            value = func(*args, **kwargs)

            # Store in cache
            cache.set(cache_key, value, ttl, serializer, namespace)

            return value

        return wrapper
    return decorator


def cache_invalidate(pattern: str, namespace: Optional[Tuple[str, int]] = None):
    """
    Decorator for invalidating cache entries after function execution.

    Args:
        pattern: Key pattern to invalidate
        namespace: Cache namespace tuple (name, default_ttl)

    Example:
        @cache_invalidate('prices:*')
        def update_prices():
            # Update prices in database
            pass
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Execute function
            result = func(*args, **kwargs)

            # Invalidate cache
            cache = CacheManager()
            count = cache.delete_pattern(pattern, namespace)
            logger.debug(f"Invalidated {count} cache entries matching {pattern}")

            return result

        return wrapper
    return decorator


def cache_aside(
    ttl: int = 60,
    namespace: Optional[Tuple[str, int]] = None,
    key_func: Optional[Callable] = None,
    serializer: Optional[str] = None
):
    """
    Decorator for cache-aside pattern.

    This is an alias for @cached decorator with more explicit naming.

    Args:
        ttl: Time-to-live in seconds
        namespace: Cache namespace tuple (name, default_ttl)
        key_func: Function to generate cache key from arguments
        serializer: Serializer to use
    """
    return cached(ttl=ttl, namespace=namespace, key_func=key_func, serializer=serializer)


# ============================================================================
# Module-level convenience functions
# ============================================================================

# Global cache instance
_cache_instance: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """Get global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheManager()
    return _cache_instance


def init_cache(config: Optional[CacheConfig] = None) -> CacheManager:
    """Initialize global cache instance with config."""
    global _cache_instance
    _cache_instance = CacheManager(config)
    return _cache_instance
