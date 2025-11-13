"""
Example: Integrating Redis Cache into ScreenerIII Components

This file shows practical examples of how to integrate the cache system
into existing ScreenerIII components for performance optimization.
"""

import sys
from pathlib import Path
from typing import List, Optional
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.cache import (
    get_cache,
    CacheNamespace,
    cached,
    cache_invalidate
)


# ============================================================================
# Example 1: Market Data Provider with Caching
# ============================================================================

class CachedMarketDataProvider:
    """
    Market data provider with intelligent caching.

    Caches:
    - Price data (15 seconds)
    - Candle data (60 seconds)
    - Last update times to prevent excessive API calls
    """

    def __init__(self):
        self.cache = get_cache()
        self.api_call_count = 0  # For demonstration

    def get_current_price(self, symbol: str) -> float:
        """
        Get current price with caching.

        First checks cache, falls back to API if not found.
        """
        cache_key = f"{symbol}:current"

        # Try cache first
        price = self.cache.get(cache_key, namespace=CacheNamespace.PRICES)

        if price is not None:
            print(f"[CACHE HIT] {symbol} price from cache: {price}")
            return price

        # Cache miss - fetch from API
        print(f"[CACHE MISS] Fetching {symbol} price from API...")
        self.api_call_count += 1
        price = self._fetch_price_from_api(symbol)

        # Store in cache with 15-second TTL
        self.cache.set(cache_key, price, namespace=CacheNamespace.PRICES)

        return price

    def get_candles(
        self,
        symbol: str,
        timeframe: str = '1H',
        count: int = 100
    ) -> pd.DataFrame:
        """
        Get historical candles with caching.

        Cache key includes symbol, timeframe, and count to ensure correct data.
        """
        cache_key = f"{symbol}:{timeframe}:{count}"

        # Try cache first
        df = self.cache.get(cache_key, namespace=CacheNamespace.CANDLES)

        if df is not None and isinstance(df, pd.DataFrame):
            print(f"[CACHE HIT] {symbol} {timeframe} candles from cache ({len(df)} rows)")
            return df

        # Cache miss - fetch from API
        print(f"[CACHE MISS] Fetching {symbol} {timeframe} candles from API...")
        self.api_call_count += 1
        df = self._fetch_candles_from_api(symbol, timeframe, count)

        # Store in cache with 60-second TTL
        self.cache.set(cache_key, df, namespace=CacheNamespace.CANDLES)

        return df

    def batch_get_prices(self, symbols: List[str]) -> dict:
        """
        Get prices for multiple symbols efficiently using batch operations.
        """
        # Try to get all from cache first
        cache_keys = [f"{symbol}:current" for symbol in symbols]
        cached_prices = self.cache.mget(cache_keys, namespace=CacheNamespace.PRICES)

        result = {}
        symbols_to_fetch = []

        # Identify which symbols need fetching
        for symbol, cached_price in zip(symbols, cached_prices):
            if cached_price is not None:
                result[symbol] = cached_price
                print(f"[CACHE HIT] {symbol}")
            else:
                symbols_to_fetch.append(symbol)

        # Fetch missing symbols from API
        if symbols_to_fetch:
            print(f"[CACHE MISS] Fetching {len(symbols_to_fetch)} symbols from API...")
            self.api_call_count += len(symbols_to_fetch)

            fetched_prices = {}
            for symbol in symbols_to_fetch:
                price = self._fetch_price_from_api(symbol)
                fetched_prices[symbol] = price
                result[symbol] = price

            # Store fetched prices in cache (batch operation)
            cache_data = {
                f"{symbol}:current": price
                for symbol, price in fetched_prices.items()
            }
            self.cache.mset(cache_data, namespace=CacheNamespace.PRICES)

        return result

    def invalidate_symbol(self, symbol: str):
        """Invalidate all cached data for a symbol."""
        pattern = f"{symbol}:*"
        deleted = self.cache.delete_pattern(pattern, namespace=CacheNamespace.PRICES)
        deleted += self.cache.delete_pattern(pattern, namespace=CacheNamespace.CANDLES)
        print(f"Invalidated {deleted} cache entries for {symbol}")

    # Simulate API calls
    def _fetch_price_from_api(self, symbol: str) -> float:
        """Simulate API call with delay."""
        time.sleep(0.1)  # Simulate network latency
        return np.random.uniform(1.0, 1.5)

    def _fetch_candles_from_api(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        """Simulate API call with delay."""
        time.sleep(0.2)  # Simulate network latency
        return pd.DataFrame({
            'timestamp': pd.date_range(end=datetime.now(), periods=count, freq='1H'),
            'open': np.random.uniform(1.0, 1.1, count),
            'high': np.random.uniform(1.05, 1.15, count),
            'low': np.random.uniform(0.95, 1.05, count),
            'close': np.random.uniform(1.0, 1.1, count),
            'volume': np.random.randint(1000, 10000, count)
        })


# ============================================================================
# Example 2: Technical Indicator Calculator with Caching
# ============================================================================

class CachedIndicatorCalculator:
    """
    Technical indicator calculator with automatic caching.

    Uses decorators for clean, maintainable code.
    """

    def __init__(self, data_provider: CachedMarketDataProvider):
        self.data_provider = data_provider
        self.cache = get_cache()

    @cached(ttl=30, namespace=CacheNamespace.INDICATORS)
    def calculate_rsi(self, symbol: str, period: int = 14) -> float:
        """
        Calculate RSI with automatic caching.

        Cache key is automatically generated from function name and arguments.
        """
        print(f"[COMPUTING] RSI for {symbol} (period={period})...")

        # Get data (may come from cache)
        df = self.data_provider.get_candles(symbol, '1H', period * 3)

        # Calculate RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi.iloc[-1]

    @cached(ttl=30, namespace=CacheNamespace.INDICATORS)
    def calculate_macd(self, symbol: str, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
        """
        Calculate MACD with automatic caching.

        Returns dictionary with MACD, signal, and histogram.
        """
        print(f"[COMPUTING] MACD for {symbol}...")

        # Get data
        df = self.data_provider.get_candles(symbol, '1H', slow * 3)

        # Calculate MACD
        ema_fast = df['close'].ewm(span=fast).mean()
        ema_slow = df['close'].ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line

        return {
            'macd': macd_line.iloc[-1],
            'signal': signal_line.iloc[-1],
            'histogram': histogram.iloc[-1]
        }

    @cached(ttl=30, namespace=CacheNamespace.INDICATORS)
    def calculate_bollinger_bands(self, symbol: str, period: int = 20, std_dev: int = 2) -> dict:
        """
        Calculate Bollinger Bands with automatic caching.
        """
        print(f"[COMPUTING] Bollinger Bands for {symbol}...")

        # Get data
        df = self.data_provider.get_candles(symbol, '1H', period * 2)

        # Calculate Bollinger Bands
        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)

        return {
            'upper': upper_band.iloc[-1],
            'middle': sma.iloc[-1],
            'lower': lower_band.iloc[-1]
        }

    def get_all_indicators(self, symbol: str) -> dict:
        """
        Get all indicators for a symbol.

        Each indicator is cached separately, so this is efficient even
        if called multiple times.
        """
        return {
            'rsi': self.calculate_rsi(symbol),
            'macd': self.calculate_macd(symbol),
            'bollinger': self.calculate_bollinger_bands(symbol)
        }


# ============================================================================
# Example 3: Signal Generator with Cache Invalidation
# ============================================================================

class CachedSignalGenerator:
    """
    Signal generator with intelligent caching and invalidation.
    """

    def __init__(self, indicator_calculator: CachedIndicatorCalculator):
        self.indicator_calculator = indicator_calculator
        self.cache = get_cache()

    @cached(ttl=60, namespace=CacheNamespace.SIGNALS)
    def generate_signal(self, symbol: str) -> dict:
        """
        Generate trading signal with caching.

        Signal is cached for 60 seconds to avoid excessive computation.
        """
        print(f"[GENERATING] Signal for {symbol}...")

        # Get indicators (may come from cache)
        indicators = self.indicator_calculator.get_all_indicators(symbol)

        # Simple signal logic
        rsi = indicators['rsi']
        macd = indicators['macd']['histogram']

        if rsi < 30 and macd > 0:
            action = 'BUY'
            confidence = 0.85
        elif rsi > 70 and macd < 0:
            action = 'SELL'
            confidence = 0.80
        else:
            action = 'HOLD'
            confidence = 0.50

        return {
            'symbol': symbol,
            'action': action,
            'confidence': confidence,
            'timestamp': time.time(),
            'indicators': indicators
        }

    @cache_invalidate('*', namespace=CacheNamespace.SIGNALS)
    def recalculate_all_signals(self):
        """
        Recalculate all signals by invalidating cache.

        This decorator automatically clears all signals from cache.
        """
        print("Recalculating all signals (cache invalidated)...")
        # Any additional logic here


# ============================================================================
# Example 4: Multi-Timeframe Analyzer with Nested Caching
# ============================================================================

class CachedMTFAnalyzer:
    """
    Multi-timeframe analyzer with hierarchical caching.

    Individual timeframe analyses are cached separately,
    and the combined result is also cached.
    """

    def __init__(self, data_provider: CachedMarketDataProvider):
        self.data_provider = data_provider
        self.cache = get_cache()

    @cached(ttl=120, namespace=CacheNamespace.MTF)
    def analyze_timeframe(self, symbol: str, timeframe: str) -> dict:
        """
        Analyze a single timeframe.

        Each timeframe's analysis is cached independently.
        """
        print(f"[ANALYZING] {symbol} on {timeframe}...")

        # Get candles for timeframe
        df = self.data_provider.get_candles(symbol, timeframe, 100)

        # Simple trend analysis
        sma_20 = df['close'].rolling(window=20).mean().iloc[-1]
        sma_50 = df['close'].rolling(window=50).mean().iloc[-1]
        current_price = df['close'].iloc[-1]

        if current_price > sma_20 > sma_50:
            trend = 'UPTREND'
            strength = 'STRONG'
        elif current_price > sma_20:
            trend = 'UPTREND'
            strength = 'WEAK'
        elif current_price < sma_20 < sma_50:
            trend = 'DOWNTREND'
            strength = 'STRONG'
        elif current_price < sma_20:
            trend = 'DOWNTREND'
            strength = 'WEAK'
        else:
            trend = 'SIDEWAYS'
            strength = 'NEUTRAL'

        return {
            'timeframe': timeframe,
            'trend': trend,
            'strength': strength,
            'current_price': current_price,
            'sma_20': sma_20,
            'sma_50': sma_50
        }

    def analyze_all_timeframes(self, symbol: str, timeframes: List[str]) -> dict:
        """
        Analyze multiple timeframes.

        Uses cache.get_or_fetch for the combined result, with individual
        timeframe analyses also being cached.
        """
        cache_key = f"{symbol}:{':'.join(timeframes)}"

        return self.cache.get_or_fetch(
            key=cache_key,
            fetch_func=lambda: self._compute_mtf_analysis(symbol, timeframes),
            ttl=120,
            namespace=CacheNamespace.MTF
        )

    def _compute_mtf_analysis(self, symbol: str, timeframes: List[str]) -> dict:
        """
        Compute multi-timeframe analysis.

        Each individual timeframe analysis may come from cache.
        """
        print(f"[COMPUTING] MTF analysis for {symbol}...")

        analyses = {}
        for tf in timeframes:
            analyses[tf] = self.analyze_timeframe(symbol, tf)

        # Determine overall trend
        trends = [a['trend'] for a in analyses.values()]
        uptrend_count = trends.count('UPTREND')
        downtrend_count = trends.count('DOWNTREND')

        if uptrend_count > len(timeframes) / 2:
            overall_trend = 'BULLISH'
        elif downtrend_count > len(timeframes) / 2:
            overall_trend = 'BEARISH'
        else:
            overall_trend = 'NEUTRAL'

        return {
            'symbol': symbol,
            'overall_trend': overall_trend,
            'timeframe_analyses': analyses,
            'analyzed_at': time.time()
        }


# ============================================================================
# Demo: Putting It All Together
# ============================================================================

def demo_cache_integration():
    """
    Demonstrate the complete caching integration.
    """
    print("="*70)
    print(" ScreenerIII Cache Integration Demo")
    print("="*70)

    # Initialize components
    data_provider = CachedMarketDataProvider()
    indicator_calc = CachedIndicatorCalculator(data_provider)
    signal_gen = CachedSignalGenerator(indicator_calc)
    mtf_analyzer = CachedMTFAnalyzer(data_provider)

    # Demo 1: Price fetching with cache
    print("\n" + "="*70)
    print("Demo 1: Price Fetching with Cache")
    print("="*70)

    symbol = 'EUR_USD'

    print("\n1. First price fetch (cache miss):")
    start = time.time()
    price1 = data_provider.get_current_price(symbol)
    time1 = time.time() - start
    print(f"   Price: {price1:.4f}, Time: {time1*1000:.2f}ms")

    print("\n2. Second price fetch (cache hit):")
    start = time.time()
    price2 = data_provider.get_current_price(symbol)
    time2 = time.time() - start
    print(f"   Price: {price2:.4f}, Time: {time2*1000:.2f}ms")
    print(f"   Speedup: {time1/time2:.1f}x faster")

    # Demo 2: Batch price fetching
    print("\n" + "="*70)
    print("Demo 2: Batch Price Fetching")
    print("="*70)

    symbols = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD']

    print("\n1. First batch fetch:")
    start = time.time()
    prices1 = data_provider.batch_get_prices(symbols)
    time1 = time.time() - start
    print(f"   Fetched {len(prices1)} prices in {time1*1000:.2f}ms")

    print("\n2. Second batch fetch (all from cache):")
    start = time.time()
    prices2 = data_provider.batch_get_prices(symbols)
    time2 = time.time() - start
    print(f"   Fetched {len(prices2)} prices in {time2*1000:.2f}ms")
    print(f"   Speedup: {time1/time2:.1f}x faster")

    # Demo 3: Indicator calculation with caching
    print("\n" + "="*70)
    print("Demo 3: Indicator Calculation with Caching")
    print("="*70)

    print("\n1. First indicator calculation:")
    start = time.time()
    rsi1 = indicator_calc.calculate_rsi(symbol)
    time1 = time.time() - start
    print(f"   RSI: {rsi1:.2f}, Time: {time1*1000:.2f}ms")

    print("\n2. Second indicator calculation (from cache):")
    start = time.time()
    rsi2 = indicator_calc.calculate_rsi(symbol)
    time2 = time.time() - start
    print(f"   RSI: {rsi2:.2f}, Time: {time2*1000:.2f}ms")
    print(f"   Speedup: {time1/time2:.1f}x faster")

    # Demo 4: Complete signal generation
    print("\n" + "="*70)
    print("Demo 4: Signal Generation with Nested Caching")
    print("="*70)

    print("\n1. First signal generation:")
    start = time.time()
    signal1 = signal_gen.generate_signal(symbol)
    time1 = time.time() - start
    print(f"   Signal: {signal1['action']} (confidence: {signal1['confidence']:.2f})")
    print(f"   Time: {time1*1000:.2f}ms")

    print("\n2. Second signal generation (from cache):")
    start = time.time()
    signal2 = signal_gen.generate_signal(symbol)
    time2 = time.time() - start
    print(f"   Signal: {signal2['action']} (confidence: {signal2['confidence']:.2f})")
    print(f"   Time: {time2*1000:.2f}ms")
    print(f"   Speedup: {time1/time2:.1f}x faster")

    # Demo 5: Multi-timeframe analysis
    print("\n" + "="*70)
    print("Demo 5: Multi-Timeframe Analysis")
    print("="*70)

    timeframes = ['15M', '1H', '4H', '1D']

    print("\n1. First MTF analysis:")
    start = time.time()
    mtf1 = mtf_analyzer.analyze_all_timeframes(symbol, timeframes)
    time1 = time.time() - start
    print(f"   Overall Trend: {mtf1['overall_trend']}")
    print(f"   Time: {time1*1000:.2f}ms")

    print("\n2. Second MTF analysis (from cache):")
    start = time.time()
    mtf2 = mtf_analyzer.analyze_all_timeframes(symbol, timeframes)
    time2 = time.time() - start
    print(f"   Overall Trend: {mtf2['overall_trend']}")
    print(f"   Time: {time2*1000:.2f}ms")
    print(f"   Speedup: {time1/time2:.1f}x faster")

    # Demo 6: Cache statistics
    print("\n" + "="*70)
    print("Demo 6: Cache Statistics")
    print("="*70)

    cache = get_cache()
    stats = cache.get_stats()

    print(f"\n   API Calls Made: {data_provider.api_call_count}")
    print(f"   Cache Hits: {stats['hits']}")
    print(f"   Cache Misses: {stats['misses']}")
    print(f"   Hit Rate: {stats['hit_rate']*100:.2f}%")
    print(f"   Total Keys: {stats.get('total_keys', 'N/A')}")

    if not cache._using_fallback and 'redis_memory' in stats:
        print(f"   Redis Memory: {stats['redis_memory']['used_memory_human']}")

    # Show namespace breakdown
    print("\n   Namespace Statistics:")
    for ns_name, ns_stats in stats['namespaces'].items():
        print(f"     {ns_name}: {ns_stats['hits']} hits, {ns_stats['misses']} misses "
              f"({ns_stats['hit_rate']*100:.2f}% hit rate)")

    print("\n" + "="*70)
    print(" Demo Complete!")
    print("="*70)
    print(f"\nWithout caching, this demo would have made ~{data_provider.api_call_count + stats['hits']} API calls.")
    print(f"With caching, only {data_provider.api_call_count} API calls were needed.")
    print(f"Cache saved {stats['hits']} API calls ({stats['hit_rate']*100:.2f}% reduction)!")


if __name__ == '__main__':
    demo_cache_integration()
