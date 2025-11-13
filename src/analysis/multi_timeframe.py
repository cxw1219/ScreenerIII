"""
Multi-Timeframe Analysis System

This module provides comprehensive multi-timeframe analysis capabilities for ScreenerIII,
including parallel data fetching, indicator calculation across timeframes, trend alignment
detection, confluence/divergence analysis, and composite signal generation.

Features:
- Support for multiple timeframes (M1 to Daily)
- Parallel candle data fetching for performance
- Multi-timeframe trend alignment detection
- Confluence and divergence analysis
- Timeframe weighting system (higher timeframe = higher weight)
- Integration with existing SignalGenerator

Author: ScreenerIII
License: MIT
"""

from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import threading

import pandas as pd
import numpy as np

from .signals import SignalGenerator, TradingSignal, SignalType
from .indicators import TechnicalIndicators
from ..data.oanda_client import OANDAClient
from ..data.market_data import CandleGranularity


logger = logging.getLogger(__name__)


class TimeFrame(Enum):
    """
    Supported timeframes with OANDA granularity mapping.

    Each timeframe maps to its OANDA API granularity code and includes
    metadata about the timeframe duration and relative priority.
    """
    M1 = ("M1", 1, 1)       # 1 minute, priority 1 (lowest)
    M5 = ("M5", 5, 2)       # 5 minutes, priority 2
    M15 = ("M15", 15, 3)    # 15 minutes, priority 3
    M30 = ("M30", 30, 4)    # 30 minutes, priority 4
    H1 = ("H1", 60, 5)      # 1 hour, priority 5
    H4 = ("H4", 240, 6)     # 4 hours, priority 6
    D = ("D", 1440, 7)      # 1 day, priority 7 (highest)

    def __init__(self, granularity: str, minutes: int, priority: int):
        """
        Initialize timeframe.

        Args:
            granularity: OANDA granularity code
            minutes: Duration in minutes
            priority: Relative priority (higher = more important)
        """
        self.granularity = granularity
        self.minutes = minutes
        self.priority = priority

    def __lt__(self, other):
        """Compare timeframes by priority."""
        if not isinstance(other, TimeFrame):
            return NotImplemented
        return self.priority < other.priority

    def __le__(self, other):
        """Compare timeframes by priority."""
        if not isinstance(other, TimeFrame):
            return NotImplemented
        return self.priority <= other.priority

    def __gt__(self, other):
        """Compare timeframes by priority."""
        if not isinstance(other, TimeFrame):
            return NotImplemented
        return self.priority > other.priority

    def __ge__(self, other):
        """Compare timeframes by priority."""
        if not isinstance(other, TimeFrame):
            return NotImplemented
        return self.priority >= other.priority

    @classmethod
    def from_string(cls, timeframe_str: str) -> 'TimeFrame':
        """
        Create TimeFrame from string.

        Args:
            timeframe_str: Timeframe string (e.g., "M5", "H1", "D")

        Returns:
            TimeFrame enum value

        Raises:
            ValueError: If timeframe string is invalid
        """
        timeframe_str = timeframe_str.upper()
        for tf in cls:
            if tf.granularity == timeframe_str:
                return tf
        raise ValueError(f"Invalid timeframe: {timeframe_str}")

    def get_candle_count(self, lookback_days: int = 30) -> int:
        """
        Calculate number of candles needed for lookback period.

        Args:
            lookback_days: Number of days to look back

        Returns:
            Number of candles needed
        """
        total_minutes = lookback_days * 24 * 60
        candles = int(total_minutes / self.minutes)
        return min(candles, 5000)  # OANDA limit


@dataclass
class TimeFrameSignal:
    """
    Trading signal for a specific timeframe.

    Attributes:
        timeframe: TimeFrame enum
        signal: Full TradingSignal object
        trend_direction: Detected trend direction
        trend_strength: Trend strength (0-100)
        support_levels: Key support price levels
        resistance_levels: Key resistance price levels
        indicators: Dictionary of key indicator values
        timestamp: Signal generation timestamp
    """
    timeframe: TimeFrame
    signal: TradingSignal
    trend_direction: str  # 'uptrend', 'downtrend', 'sideways'
    trend_strength: float
    support_levels: List[float] = field(default_factory=list)
    resistance_levels: List[float] = field(default_factory=list)
    indicators: Dict[str, float] = field(default_factory=dict)
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timeframe': self.timeframe.granularity,
            'signal': self.signal.to_dict(),
            'trend_direction': self.trend_direction,
            'trend_strength': round(self.trend_strength, 2),
            'support_levels': [round(s, 5) for s in self.support_levels],
            'resistance_levels': [round(r, 5) for r in self.resistance_levels],
            'indicators': {k: round(v, 4) for k, v in self.indicators.items()},
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class MultiTimeFrameSignal:
    """
    Aggregated signal across multiple timeframes.

    Attributes:
        instrument: Instrument identifier
        timeframe_signals: Dictionary of TimeFrameSignal by TimeFrame
        confluence_score: How many timeframes agree (0-100)
        dominant_timeframe: Timeframe with highest priority in agreement
        overall_direction: Aggregated signal direction
        confidence_score: Overall confidence (0-100)
        divergences: List of detected divergences between timeframes
        recommendation: Trading recommendation
        timestamp: Signal generation timestamp
    """
    instrument: str
    timeframe_signals: Dict[TimeFrame, TimeFrameSignal]
    confluence_score: float
    dominant_timeframe: Optional[TimeFrame] = None
    overall_direction: str = "NEUTRAL"
    confidence_score: float = 0.0
    divergences: List[Dict[str, Any]] = field(default_factory=list)
    recommendation: str = "HOLD"
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'instrument': self.instrument,
            'timeframe_signals': {
                tf.granularity: signal.to_dict()
                for tf, signal in self.timeframe_signals.items()
            },
            'confluence_score': round(self.confluence_score, 2),
            'dominant_timeframe': self.dominant_timeframe.granularity if self.dominant_timeframe else None,
            'overall_direction': self.overall_direction,
            'confidence_score': round(self.confidence_score, 2),
            'divergences': self.divergences,
            'recommendation': self.recommendation,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

    def get_entry_price(self) -> Optional[float]:
        """Get recommended entry price from dominant timeframe."""
        if self.dominant_timeframe and self.dominant_timeframe in self.timeframe_signals:
            return self.timeframe_signals[self.dominant_timeframe].signal.entry_price
        return None

    def get_stop_loss(self) -> Optional[float]:
        """Get recommended stop loss from dominant timeframe."""
        if self.dominant_timeframe and self.dominant_timeframe in self.timeframe_signals:
            return self.timeframe_signals[self.dominant_timeframe].signal.stop_loss
        return None

    def get_targets(self) -> Dict[str, Optional[float]]:
        """Get recommended targets from dominant timeframe."""
        if self.dominant_timeframe and self.dominant_timeframe in self.timeframe_signals:
            signal = self.timeframe_signals[self.dominant_timeframe].signal
            return {
                'target_1': signal.target_1,
                'target_2': signal.target_2,
                'target_3': signal.target_3
            }
        return {'target_1': None, 'target_2': None, 'target_3': None}


class MultiTimeFrameAnalyzer:
    """
    Main multi-timeframe analysis engine.

    Fetches candle data across multiple timeframes in parallel, calculates indicators,
    detects trend alignment, and generates comprehensive multi-timeframe signals.

    Features:
    - Parallel data fetching for performance
    - Automatic timeframe prioritization
    - Confluence and divergence detection
    - Composite signal generation with weighting
    - Data caching for efficiency
    """

    # Timeframe weights (higher timeframe = higher weight)
    TIMEFRAME_WEIGHTS = {
        TimeFrame.M1: 0.5,
        TimeFrame.M5: 0.75,
        TimeFrame.M15: 1.0,
        TimeFrame.M30: 1.5,
        TimeFrame.H1: 2.0,
        TimeFrame.H4: 3.0,
        TimeFrame.D: 4.0
    }

    def __init__(
        self,
        oanda_client: OANDAClient,
        default_timeframes: Optional[List[TimeFrame]] = None,
        lookback_days: int = 30,
        max_workers: int = 5,
        cache_ttl: int = 300,
        risk_percent: float = 2.0
    ):
        """
        Initialize MultiTimeFrameAnalyzer.

        Args:
            oanda_client: OANDA API client instance
            default_timeframes: Default timeframes to analyze (defaults to [M15, H1, H4, D])
            lookback_days: Number of days of historical data to fetch
            max_workers: Maximum parallel workers for data fetching
            cache_ttl: Cache time-to-live in seconds
            risk_percent: Risk percentage for signal generation
        """
        self.client = oanda_client
        self.lookback_days = lookback_days
        self.max_workers = max_workers
        self.cache_ttl = cache_ttl
        self.risk_percent = risk_percent

        # Default timeframes
        if default_timeframes is None:
            self.default_timeframes = [TimeFrame.M15, TimeFrame.H1, TimeFrame.H4, TimeFrame.D]
        else:
            self.default_timeframes = sorted(default_timeframes)

        # Cache for candle data
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = threading.Lock()

        logger.info(
            f"Initialized MultiTimeFrameAnalyzer with timeframes: "
            f"{[tf.granularity for tf in self.default_timeframes]}"
        )

    def _get_cache_key(self, instrument: str, timeframe: TimeFrame) -> str:
        """Generate cache key for instrument and timeframe."""
        return f"{instrument}_{timeframe.granularity}"

    def _get_from_cache(self, instrument: str, timeframe: TimeFrame) -> Optional[pd.DataFrame]:
        """
        Get data from cache if available and not expired.

        Args:
            instrument: Instrument identifier
            timeframe: TimeFrame enum

        Returns:
            Cached DataFrame or None
        """
        cache_key = self._get_cache_key(instrument, timeframe)

        with self._cache_lock:
            if cache_key in self._cache:
                cached_data = self._cache[cache_key]
                cache_time = cached_data['timestamp']

                # Check if cache is still valid
                if (datetime.now() - cache_time).total_seconds() < self.cache_ttl:
                    logger.debug(f"Cache hit for {cache_key}")
                    return cached_data['data'].copy()
                else:
                    # Remove expired cache entry
                    del self._cache[cache_key]

        logger.debug(f"Cache miss for {cache_key}")
        return None

    def _save_to_cache(self, instrument: str, timeframe: TimeFrame, data: pd.DataFrame) -> None:
        """
        Save data to cache.

        Args:
            instrument: Instrument identifier
            timeframe: TimeFrame enum
            data: DataFrame to cache
        """
        cache_key = self._get_cache_key(instrument, timeframe)

        with self._cache_lock:
            self._cache[cache_key] = {
                'data': data.copy(),
                'timestamp': datetime.now()
            }
            logger.debug(f"Cached data for {cache_key}")

    def clear_cache(self, instrument: Optional[str] = None) -> None:
        """
        Clear cache for specific instrument or all.

        Args:
            instrument: Instrument to clear cache for (None = all)
        """
        with self._cache_lock:
            if instrument is None:
                self._cache.clear()
                logger.info("Cleared all cache")
            else:
                keys_to_remove = [
                    key for key in self._cache.keys()
                    if key.startswith(f"{instrument}_")
                ]
                for key in keys_to_remove:
                    del self._cache[key]
                logger.info(f"Cleared cache for {instrument}")

    def _fetch_candles_for_timeframe(
        self,
        instrument: str,
        timeframe: TimeFrame,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Fetch candle data for specific timeframe.

        Args:
            instrument: Instrument identifier
            timeframe: TimeFrame enum
            use_cache: Whether to use cached data

        Returns:
            DataFrame with OHLCV data

        Raises:
            Exception: If data fetching fails
        """
        try:
            # Check cache first
            if use_cache:
                cached_data = self._get_from_cache(instrument, timeframe)
                if cached_data is not None:
                    return cached_data

            # Calculate candle count needed
            count = timeframe.get_candle_count(self.lookback_days)

            # Fetch from OANDA
            logger.debug(f"Fetching {count} candles for {instrument} on {timeframe.granularity}")
            response = self.client.get_candles(
                instrument=instrument,
                granularity=timeframe.granularity,
                count=count,
                price="M"  # Midpoint prices
            )

            # Convert to DataFrame
            candles = response.get('candles', [])
            if not candles:
                raise ValueError(f"No candles returned for {instrument} on {timeframe.granularity}")

            data = []
            for candle in candles:
                if candle.get('complete', False):
                    mid = candle['mid']
                    data.append({
                        'timestamp': pd.to_datetime(candle['time']),
                        'open': float(mid['o']),
                        'high': float(mid['h']),
                        'low': float(mid['l']),
                        'close': float(mid['c']),
                        'volume': int(candle.get('volume', 0))
                    })

            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)

            # Save to cache
            if use_cache:
                self._save_to_cache(instrument, timeframe, df)

            logger.debug(f"Fetched {len(df)} candles for {instrument} on {timeframe.granularity}")
            return df

        except Exception as e:
            logger.error(f"Error fetching candles for {instrument} on {timeframe.granularity}: {e}")
            raise

    def fetch_multi_timeframe_data(
        self,
        instrument: str,
        timeframes: Optional[List[TimeFrame]] = None,
        use_cache: bool = True
    ) -> Dict[TimeFrame, pd.DataFrame]:
        """
        Fetch candle data for multiple timeframes in parallel.

        Args:
            instrument: Instrument identifier
            timeframes: List of timeframes to fetch (defaults to default_timeframes)
            use_cache: Whether to use cached data

        Returns:
            Dictionary mapping TimeFrame to DataFrame

        Raises:
            Exception: If any data fetching fails
        """
        if timeframes is None:
            timeframes = self.default_timeframes

        logger.info(f"Fetching multi-timeframe data for {instrument}")

        # Fetch in parallel
        results = {}
        errors = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all fetch tasks
            future_to_tf = {
                executor.submit(
                    self._fetch_candles_for_timeframe,
                    instrument,
                    tf,
                    use_cache
                ): tf
                for tf in timeframes
            }

            # Collect results
            for future in as_completed(future_to_tf):
                tf = future_to_tf[future]
                try:
                    data = future.result()
                    results[tf] = data
                except Exception as e:
                    error_msg = f"Failed to fetch {tf.granularity}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

        if errors:
            raise Exception(f"Errors occurred during data fetching: {'; '.join(errors)}")

        logger.info(f"Successfully fetched data for {len(results)} timeframes")
        return results

    def _analyze_timeframe(
        self,
        instrument: str,
        timeframe: TimeFrame,
        data: pd.DataFrame
    ) -> TimeFrameSignal:
        """
        Analyze single timeframe and generate signal.

        Args:
            instrument: Instrument identifier
            timeframe: TimeFrame enum
            data: OHLCV DataFrame

        Returns:
            TimeFrameSignal object
        """
        try:
            # Generate signal using SignalGenerator
            signal_gen = SignalGenerator(data, risk_percent=self.risk_percent)
            signal = signal_gen.generate_signal()

            # Get trend analysis
            indicators_obj = TechnicalIndicators(data)
            trend = indicators_obj.detect_trend()

            # Calculate key levels (support/resistance)
            support_levels = []
            resistance_levels = []

            # Use recent swing lows/highs as support/resistance
            lookback = min(20, len(data))
            recent_data = data.tail(lookback)

            # Simple swing detection
            lows = recent_data['low'].values
            highs = recent_data['high'].values

            for i in range(2, len(lows) - 2):
                if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
                   lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                    support_levels.append(float(lows[i]))

                if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
                   highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                    resistance_levels.append(float(highs[i]))

            # Keep only unique levels (rounded)
            support_levels = sorted(list(set([round(s, 5) for s in support_levels])))[:3]
            resistance_levels = sorted(list(set([round(r, 5) for r in resistance_levels])))[-3:]

            # Extract key indicator values
            rsi = indicators_obj.calculate_rsi(14)
            macd = indicators_obj.calculate_macd()
            adx = indicators_obj.calculate_adx()

            key_indicators = {
                'rsi': float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0,
                'macd': float(macd['MACD'].iloc[-1]) if not pd.isna(macd['MACD'].iloc[-1]) else 0.0,
                'adx': float(adx['ADX'].iloc[-1]) if not pd.isna(adx['ADX'].iloc[-1]) else 0.0,
                'price': float(data['close'].iloc[-1])
            }

            # Create TimeFrameSignal
            tf_signal = TimeFrameSignal(
                timeframe=timeframe,
                signal=signal,
                trend_direction=trend['direction'],
                trend_strength=trend['strength'],
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                indicators=key_indicators,
                timestamp=datetime.now()
            )

            logger.debug(
                f"Analyzed {timeframe.granularity}: {signal.signal_type.value} "
                f"(confidence: {signal.confidence:.2f})"
            )

            return tf_signal

        except Exception as e:
            logger.error(f"Error analyzing {timeframe.granularity}: {e}")
            raise

    def analyze_instrument(
        self,
        instrument: str,
        timeframes: Optional[List[TimeFrame]] = None,
        use_cache: bool = True
    ) -> MultiTimeFrameSignal:
        """
        Perform comprehensive multi-timeframe analysis on an instrument.

        This is the main entry point for multi-timeframe analysis. It fetches data,
        analyzes each timeframe, detects confluence/divergence, and generates a
        composite signal.

        Args:
            instrument: Instrument identifier (e.g., "EUR_USD")
            timeframes: List of timeframes to analyze (defaults to default_timeframes)
            use_cache: Whether to use cached data

        Returns:
            MultiTimeFrameSignal with complete analysis

        Raises:
            Exception: If analysis fails

        Example:
            >>> analyzer = MultiTimeFrameAnalyzer(oanda_client)
            >>> mtf_signal = analyzer.analyze_instrument("EUR_USD")
            >>> print(f"Recommendation: {mtf_signal.recommendation}")
            >>> print(f"Confidence: {mtf_signal.confidence_score:.2f}%")
        """
        try:
            if timeframes is None:
                timeframes = self.default_timeframes

            logger.info(f"Starting multi-timeframe analysis for {instrument}")

            # Fetch data for all timeframes
            mtf_data = self.fetch_multi_timeframe_data(instrument, timeframes, use_cache)

            # Analyze each timeframe
            timeframe_signals = {}
            for tf, data in mtf_data.items():
                tf_signal = self._analyze_timeframe(instrument, tf, data)
                timeframe_signals[tf] = tf_signal

            # Detect confluence
            confluence_score = self.detect_confluence(timeframe_signals)

            # Detect divergence
            divergences = self.detect_divergence(timeframe_signals)

            # Calculate composite signal
            composite = self.calculate_composite_signal(timeframe_signals)

            # Determine dominant timeframe (highest priority with strong signal)
            dominant_tf = self._get_dominant_timeframe(timeframe_signals)

            # Create MultiTimeFrameSignal
            mtf_signal = MultiTimeFrameSignal(
                instrument=instrument,
                timeframe_signals=timeframe_signals,
                confluence_score=confluence_score,
                dominant_timeframe=dominant_tf,
                overall_direction=composite['direction'],
                confidence_score=composite['confidence'],
                divergences=divergences,
                recommendation=composite['recommendation'],
                timestamp=datetime.now()
            )

            logger.info(
                f"Multi-timeframe analysis complete for {instrument}: "
                f"{mtf_signal.recommendation} (confidence: {mtf_signal.confidence_score:.2f}%)"
            )

            return mtf_signal

        except Exception as e:
            logger.error(f"Error in multi-timeframe analysis for {instrument}: {e}")
            raise

    def detect_confluence(self, signals: Dict[TimeFrame, TimeFrameSignal]) -> float:
        """
        Detect confluence (agreement) across timeframes.

        Confluence occurs when multiple timeframes agree on direction. Higher
        confluence indicates stronger signal validity.

        Args:
            signals: Dictionary of TimeFrameSignal by TimeFrame

        Returns:
            Confluence score (0-100)

        Example:
            >>> confluence = analyzer.detect_confluence(timeframe_signals)
            >>> if confluence > 70:
            >>>     print("Strong confluence detected!")
        """
        if not signals:
            return 0.0

        # Count bullish and bearish signals
        bullish_count = 0
        bearish_count = 0
        total_weight = 0.0
        weighted_bullish = 0.0
        weighted_bearish = 0.0

        for tf, tf_signal in signals.items():
            weight = self.TIMEFRAME_WEIGHTS.get(tf, 1.0)
            total_weight += weight

            signal_type = tf_signal.signal.signal_type

            if signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
                bullish_count += 1
                weighted_bullish += weight
            elif signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
                bearish_count += 1
                weighted_bearish += weight

        # Calculate confluence based on agreement
        total_signals = len(signals)
        max_count = max(bullish_count, bearish_count)

        # Basic confluence (percentage of timeframes agreeing)
        basic_confluence = (max_count / total_signals) * 100

        # Weighted confluence (considering timeframe importance)
        max_weighted = max(weighted_bullish, weighted_bearish)
        weighted_confluence = (max_weighted / total_weight) * 100

        # Combined score (60% weighted, 40% basic)
        confluence_score = (weighted_confluence * 0.6) + (basic_confluence * 0.4)

        logger.debug(
            f"Confluence analysis: {max_count}/{total_signals} agree, "
            f"score: {confluence_score:.2f}%"
        )

        return float(confluence_score)

    def detect_divergence(self, signals: Dict[TimeFrame, TimeFrameSignal]) -> List[Dict[str, Any]]:
        """
        Detect divergences (conflicts) between timeframes.

        Divergences occur when different timeframes disagree on direction,
        which can indicate potential reversals or consolidation.

        Args:
            signals: Dictionary of TimeFrameSignal by TimeFrame

        Returns:
            List of divergence dictionaries with details

        Example:
            >>> divergences = analyzer.detect_divergence(timeframe_signals)
            >>> for div in divergences:
            >>>     print(f"Divergence between {div['tf1']} and {div['tf2']}")
        """
        divergences = []

        # Sort timeframes by priority
        sorted_tfs = sorted(signals.keys())

        # Compare adjacent timeframes
        for i in range(len(sorted_tfs) - 1):
            tf1 = sorted_tfs[i]
            tf2 = sorted_tfs[i + 1]

            signal1 = signals[tf1].signal
            signal2 = signals[tf2].signal

            # Check for directional divergence
            type1 = signal1.signal_type
            type2 = signal2.signal_type

            is_divergent = False
            divergence_type = ""

            if type1 in [SignalType.BUY, SignalType.STRONG_BUY] and \
               type2 in [SignalType.SELL, SignalType.STRONG_SELL]:
                is_divergent = True
                divergence_type = "directional"
            elif type1 in [SignalType.SELL, SignalType.STRONG_SELL] and \
                 type2 in [SignalType.BUY, SignalType.STRONG_BUY]:
                is_divergent = True
                divergence_type = "directional"

            # Check for strength divergence (same direction but different strength)
            elif (type1 in [SignalType.BUY, SignalType.STRONG_BUY] and
                  type2 in [SignalType.BUY, SignalType.STRONG_BUY]) or \
                 (type1 in [SignalType.SELL, SignalType.STRONG_SELL] and
                  type2 in [SignalType.SELL, SignalType.STRONG_SELL]):
                confidence_diff = abs(signal1.confidence - signal2.confidence)
                if confidence_diff > 30:
                    is_divergent = True
                    divergence_type = "strength"

            if is_divergent:
                divergence = {
                    'timeframe_1': tf1.granularity,
                    'timeframe_2': tf2.granularity,
                    'signal_1': type1.value,
                    'signal_2': type2.value,
                    'confidence_1': round(signal1.confidence, 2),
                    'confidence_2': round(signal2.confidence, 2),
                    'type': divergence_type,
                    'severity': 'high' if abs(signal1.confidence - signal2.confidence) > 40 else 'medium'
                }
                divergences.append(divergence)

                logger.debug(
                    f"Divergence detected: {tf1.granularity} ({type1.value}) vs "
                    f"{tf2.granularity} ({type2.value})"
                )

        return divergences

    def calculate_composite_signal(
        self,
        timeframe_signals: Dict[TimeFrame, TimeFrameSignal]
    ) -> Dict[str, Any]:
        """
        Calculate composite signal across all timeframes.

        Aggregates signals from all timeframes using weighted voting to determine
        overall direction, confidence, and recommendation.

        Args:
            timeframe_signals: Dictionary of TimeFrameSignal by TimeFrame

        Returns:
            Dictionary with direction, confidence, and recommendation

        Example:
            >>> composite = analyzer.calculate_composite_signal(timeframe_signals)
            >>> print(f"Direction: {composite['direction']}")
            >>> print(f"Recommendation: {composite['recommendation']}")
        """
        if not timeframe_signals:
            return {
                'direction': 'NEUTRAL',
                'confidence': 0.0,
                'recommendation': 'HOLD'
            }

        # Weighted vote
        bullish_weight = 0.0
        bearish_weight = 0.0
        total_weight = 0.0
        total_confidence = 0.0

        for tf, tf_signal in timeframe_signals.items():
            weight = self.TIMEFRAME_WEIGHTS.get(tf, 1.0)
            confidence = tf_signal.signal.confidence / 100.0  # Normalize to 0-1

            # Weight by both timeframe importance and signal confidence
            effective_weight = weight * confidence
            total_weight += weight
            total_confidence += tf_signal.signal.confidence * weight

            signal_type = tf_signal.signal.signal_type

            if signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
                bullish_weight += effective_weight
            elif signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
                bearish_weight += effective_weight

        # Calculate overall confidence (weighted average)
        if total_weight > 0:
            overall_confidence = total_confidence / total_weight
        else:
            overall_confidence = 0.0

        # Determine direction
        if bullish_weight > bearish_weight:
            direction = "BULLISH"
            directional_strength = (bullish_weight / (bullish_weight + bearish_weight + 0.001)) * 100
        elif bearish_weight > bullish_weight:
            direction = "BEARISH"
            directional_strength = (bearish_weight / (bullish_weight + bearish_weight + 0.001)) * 100
        else:
            direction = "NEUTRAL"
            directional_strength = 50.0

        # Determine recommendation
        if direction == "BULLISH" and overall_confidence >= 60 and directional_strength >= 70:
            recommendation = "STRONG_BUY"
        elif direction == "BULLISH" and overall_confidence >= 50:
            recommendation = "BUY"
        elif direction == "BEARISH" and overall_confidence >= 60 and directional_strength >= 70:
            recommendation = "STRONG_SELL"
        elif direction == "BEARISH" and overall_confidence >= 50:
            recommendation = "SELL"
        else:
            recommendation = "HOLD"

        logger.debug(
            f"Composite signal: {direction} (confidence: {overall_confidence:.2f}%, "
            f"strength: {directional_strength:.2f}%)"
        )

        return {
            'direction': direction,
            'confidence': float(overall_confidence),
            'directional_strength': float(directional_strength),
            'recommendation': recommendation
        }

    def get_higher_timeframe_bias(
        self,
        instrument: str,
        reference_timeframe: TimeFrame = TimeFrame.H1
    ) -> Dict[str, Any]:
        """
        Get higher timeframe bias relative to a reference timeframe.

        This helps determine the overall market direction from a higher perspective,
        useful for aligning trades with the dominant trend.

        Args:
            instrument: Instrument identifier
            reference_timeframe: Reference timeframe (default: H1)

        Returns:
            Dictionary with HTF bias information

        Example:
            >>> htf_bias = analyzer.get_higher_timeframe_bias("EUR_USD", TimeFrame.M15)
            >>> if htf_bias['direction'] == 'BULLISH':
            >>>     print("Trade with the HTF trend")
        """
        try:
            # Get higher timeframes
            htf_list = [tf for tf in self.default_timeframes if tf > reference_timeframe]

            if not htf_list:
                # If no higher timeframes, use daily
                htf_list = [TimeFrame.D]

            logger.info(
                f"Analyzing HTF bias for {instrument} relative to {reference_timeframe.granularity}"
            )

            # Fetch and analyze higher timeframes
            mtf_data = self.fetch_multi_timeframe_data(instrument, htf_list)

            htf_signals = {}
            for tf, data in mtf_data.items():
                tf_signal = self._analyze_timeframe(instrument, tf, data)
                htf_signals[tf] = tf_signal

            # Calculate composite for HTF
            composite = self.calculate_composite_signal(htf_signals)

            return {
                'reference_timeframe': reference_timeframe.granularity,
                'higher_timeframes': [tf.granularity for tf in htf_list],
                'direction': composite['direction'],
                'confidence': composite['confidence'],
                'recommendation': composite['recommendation'],
                'signals': {tf.granularity: sig.signal.signal_type.value
                           for tf, sig in htf_signals.items()}
            }

        except Exception as e:
            logger.error(f"Error getting HTF bias: {e}")
            raise

    def _get_dominant_timeframe(
        self,
        signals: Dict[TimeFrame, TimeFrameSignal]
    ) -> Optional[TimeFrame]:
        """
        Determine the dominant timeframe based on priority and signal strength.

        Args:
            signals: Dictionary of TimeFrameSignal by TimeFrame

        Returns:
            Dominant TimeFrame or None
        """
        if not signals:
            return None

        # Find highest priority timeframe with actionable signal
        sorted_tfs = sorted(signals.keys(), reverse=True)  # Highest priority first

        for tf in sorted_tfs:
            signal = signals[tf].signal
            if signal.signal_type not in [SignalType.HOLD, SignalType.NO_SIGNAL]:
                if signal.confidence >= 50:
                    return tf

        # If no strong signals, return highest timeframe
        return sorted_tfs[0] if sorted_tfs else None


class TimeFrameSynchronizer:
    """
    Synchronizes and aligns data across multiple timeframes.

    Provides utilities for detecting crossover points, multi-timeframe setups,
    and synchronizing signals across different timeframes.
    """

    @staticmethod
    def align_timeframes(
        data_dict: Dict[TimeFrame, pd.DataFrame],
        target_timeframe: TimeFrame
    ) -> Dict[TimeFrame, pd.DataFrame]:
        """
        Align all timeframes to match timestamps of target timeframe.

        Args:
            data_dict: Dictionary of DataFrames by TimeFrame
            target_timeframe: TimeFrame to align to

        Returns:
            Dictionary of aligned DataFrames
        """
        if target_timeframe not in data_dict:
            raise ValueError(f"Target timeframe {target_timeframe.granularity} not in data")

        target_data = data_dict[target_timeframe]
        aligned_data = {target_timeframe: target_data}

        for tf, data in data_dict.items():
            if tf != target_timeframe:
                # Resample or forward-fill to match target timeframe
                aligned = data.reindex(target_data.index, method='ffill')
                aligned_data[tf] = aligned

        return aligned_data

    @staticmethod
    def detect_crossover_points(
        mtf_signals: MultiTimeFrameSignal,
        lookback: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Detect points where multiple timeframes crossed over simultaneously.

        Args:
            mtf_signals: MultiTimeFrameSignal object
            lookback: Number of periods to look back

        Returns:
            List of crossover points
        """
        crossovers = []

        # Implementation would require historical signal data
        # This is a placeholder for future enhancement
        logger.debug("Crossover detection requires historical signal tracking")

        return crossovers

    @staticmethod
    def find_multi_timeframe_setups(
        mtf_signals: MultiTimeFrameSignal,
        setup_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find specific multi-timeframe trading setups.

        Args:
            mtf_signals: MultiTimeFrameSignal object
            setup_types: Types of setups to look for (e.g., 'pullback', 'breakout')

        Returns:
            List of detected setups
        """
        setups = []

        if setup_types is None:
            setup_types = ['trend_alignment', 'pullback', 'breakout']

        # Trend alignment setup
        if 'trend_alignment' in setup_types:
            if mtf_signals.confluence_score >= 70:
                setups.append({
                    'type': 'trend_alignment',
                    'direction': mtf_signals.overall_direction,
                    'confidence': mtf_signals.confidence_score,
                    'description': 'Multiple timeframes aligned in same direction'
                })

        # Pullback setup (HTF trend with LTF pullback)
        if 'pullback' in setup_types:
            signals = mtf_signals.timeframe_signals
            sorted_tfs = sorted(signals.keys(), reverse=True)

            if len(sorted_tfs) >= 2:
                htf = sorted_tfs[0]
                ltf = sorted_tfs[-1]

                htf_signal = signals[htf].signal.signal_type
                ltf_signal = signals[ltf].signal.signal_type

                # HTF bullish, LTF bearish = bullish pullback
                if htf_signal in [SignalType.BUY, SignalType.STRONG_BUY] and \
                   ltf_signal in [SignalType.SELL, SignalType.STRONG_SELL]:
                    setups.append({
                        'type': 'pullback',
                        'direction': 'BULLISH',
                        'htf': htf.granularity,
                        'ltf': ltf.granularity,
                        'description': f'Bullish {htf.granularity} with {ltf.granularity} pullback'
                    })

                # HTF bearish, LTF bullish = bearish pullback
                elif htf_signal in [SignalType.SELL, SignalType.STRONG_SELL] and \
                     ltf_signal in [SignalType.BUY, SignalType.STRONG_BUY]:
                    setups.append({
                        'type': 'pullback',
                        'direction': 'BEARISH',
                        'htf': htf.granularity,
                        'ltf': ltf.granularity,
                        'description': f'Bearish {htf.granularity} with {ltf.granularity} pullback'
                    })

        logger.debug(f"Found {len(setups)} multi-timeframe setups")
        return setups


# Convenience functions for quick analysis

def quick_mtf_analysis(
    oanda_client: OANDAClient,
    instrument: str,
    timeframes: Optional[List[str]] = None
) -> MultiTimeFrameSignal:
    """
    Quick multi-timeframe analysis with default settings.

    Args:
        oanda_client: OANDA API client
        instrument: Instrument to analyze
        timeframes: List of timeframe strings (e.g., ["M15", "H1", "D"])

    Returns:
        MultiTimeFrameSignal

    Example:
        >>> from src.data.oanda_client import OANDAClient
        >>> client = OANDAClient(api_token="xxx", account_id="yyy")
        >>> signal = quick_mtf_analysis(client, "EUR_USD")
        >>> print(signal.recommendation)
    """
    # Convert timeframe strings to TimeFrame enums
    if timeframes is not None:
        tf_list = [TimeFrame.from_string(tf) for tf in timeframes]
    else:
        tf_list = None

    analyzer = MultiTimeFrameAnalyzer(oanda_client, default_timeframes=tf_list)
    return analyzer.analyze_instrument(instrument)


def compare_timeframes(
    mtf_signal: MultiTimeFrameSignal
) -> pd.DataFrame:
    """
    Create comparison table of signals across timeframes.

    Args:
        mtf_signal: MultiTimeFrameSignal object

    Returns:
        DataFrame with timeframe comparison

    Example:
        >>> signal = analyzer.analyze_instrument("EUR_USD")
        >>> comparison = compare_timeframes(signal)
        >>> print(comparison)
    """
    data = []

    for tf, tf_signal in sorted(mtf_signal.timeframe_signals.items()):
        data.append({
            'Timeframe': tf.granularity,
            'Signal': tf_signal.signal.signal_type.value,
            'Confidence': round(tf_signal.signal.confidence, 2),
            'Trend': tf_signal.trend_direction,
            'Trend_Strength': round(tf_signal.trend_strength, 2),
            'RSI': round(tf_signal.indicators.get('rsi', 0), 2),
            'ADX': round(tf_signal.indicators.get('adx', 0), 2)
        })

    df = pd.DataFrame(data)
    return df
