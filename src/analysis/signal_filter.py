"""
Signal Filtering and Ranking System

This module provides comprehensive signal filtering, ranking, and aggregation capabilities
for trading signals. It allows filtering signals by various criteria, ranking them by
multiple factors, and aggregating signals across timeframes.

Features:
- Multi-criteria signal filtering
- Composite scoring and ranking
- Signal aggregation across timeframes
- Conflict detection and resolution
- Signal correlation analysis
- Sector/category analysis

Author: ScreenerIII
License: MIT
"""

from typing import Dict, List, Optional, Tuple, Callable, Union, Any
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from enum import Enum
import logging
import pandas as pd
import numpy as np
from collections import defaultdict

from .signals import TradingSignal, SignalType

# Configure logging
logger = logging.getLogger(__name__)


class RankingMethod(Enum):
    """Enumeration of ranking methods."""
    CONFIDENCE = "confidence"
    RISK_REWARD = "risk_reward"
    COMPOSITE = "composite"
    TREND_ALIGNMENT = "trend_alignment"
    VOLUME = "volume"


class MarketSession(Enum):
    """Enumeration of market trading sessions."""
    ASIAN = "asian"
    EUROPEAN = "european"
    AMERICAN = "american"
    ALL = "all"


class TimeFrame(Enum):
    """Enumeration of timeframes."""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"
    MN1 = "1mo"


@dataclass
class FilterConfig:
    """
    Configuration for signal filtering.

    Attributes:
        min_confidence: Minimum confidence score (0-100)
        min_risk_reward: Minimum risk/reward ratio
        allowed_signal_types: List of allowed signal types
        allowed_instruments: List of allowed instruments/symbols
        blocked_instruments: List of blocked instruments/symbols
        max_signals_per_update: Maximum number of signals to return
        require_trend_alignment: Require signals to align with trend
        min_trend_strength: Minimum trend strength (ADX)
        allowed_timeframes: List of allowed timeframes
        trading_hours_only: Filter signals to trading hours only
        market_sessions: List of allowed market sessions
        exclude_conflicting: Exclude signals with conflicts
        min_volume_confirmation: Minimum volume confirmation score
        custom_filters: List of custom filter functions

    Examples:
        >>> config = FilterConfig(
        ...     min_confidence=70.0,
        ...     min_risk_reward=2.0,
        ...     allowed_signal_types=[SignalType.STRONG_BUY, SignalType.STRONG_SELL]
        ... )
        >>> filtered = apply_filters(signals, config)
    """
    min_confidence: float = 60.0
    min_risk_reward: float = 1.5
    allowed_signal_types: Optional[List[SignalType]] = None
    allowed_instruments: Optional[List[str]] = None
    blocked_instruments: Optional[List[str]] = None
    max_signals_per_update: int = 10
    require_trend_alignment: bool = True
    min_trend_strength: float = 20.0
    allowed_timeframes: Optional[List[TimeFrame]] = None
    trading_hours_only: bool = False
    market_sessions: Optional[List[MarketSession]] = None
    exclude_conflicting: bool = True
    min_volume_confirmation: float = 0.0
    custom_filters: List[Callable[[Dict], bool]] = field(default_factory=list)

    def __post_init__(self):
        """Validate configuration values."""
        if not 0 <= self.min_confidence <= 100:
            raise ValueError(f"min_confidence must be between 0 and 100, got {self.min_confidence}")

        if self.min_risk_reward < 0:
            raise ValueError(f"min_risk_reward must be >= 0, got {self.min_risk_reward}")

        if self.max_signals_per_update < 1:
            raise ValueError(f"max_signals_per_update must be >= 1, got {self.max_signals_per_update}")

        if not 0 <= self.min_trend_strength <= 100:
            raise ValueError(f"min_trend_strength must be between 0 and 100, got {self.min_trend_strength}")


@dataclass
class EnrichedSignal:
    """
    Enhanced signal with additional metadata for filtering and ranking.

    Attributes:
        signal: Original TradingSignal
        instrument: Instrument/symbol name
        timeframe: Signal timeframe
        trend_alignment: Trend alignment score (0-100)
        volume_confirmation: Volume confirmation score (0-100)
        composite_score: Calculated composite score
        market_session: Market session when signal was generated
        sector: Market sector/category
        metadata: Additional metadata
    """
    signal: TradingSignal
    instrument: str
    timeframe: TimeFrame = TimeFrame.H1
    trend_alignment: float = 0.0
    volume_confirmation: float = 0.0
    composite_score: float = 0.0
    market_session: MarketSession = MarketSession.ALL
    sector: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'signal': self.signal.to_dict(),
            'instrument': self.instrument,
            'timeframe': self.timeframe.value,
            'trend_alignment': round(self.trend_alignment, 2),
            'volume_confirmation': round(self.volume_confirmation, 2),
            'composite_score': round(self.composite_score, 2),
            'market_session': self.market_session.value,
            'sector': self.sector,
            'metadata': self.metadata
        }


class SignalFilter:
    """
    Filter signals based on various criteria.

    This class provides comprehensive filtering capabilities including
    confidence thresholds, risk/reward ratios, instrument filtering,
    timeframe filtering, and custom filter functions.

    Examples:
        >>> filter_obj = SignalFilter(config)
        >>> filtered = filter_obj.filter_signals(signals)
        >>> print(f"Filtered {len(filtered)} signals from {len(signals)}")
    """

    def __init__(self, config: FilterConfig):
        """
        Initialize SignalFilter.

        Args:
            config: Filter configuration
        """
        self.config = config
        self.filter_stats = {
            'total_processed': 0,
            'passed': 0,
            'failed_confidence': 0,
            'failed_risk_reward': 0,
            'failed_signal_type': 0,
            'failed_instrument': 0,
            'failed_timeframe': 0,
            'failed_trend': 0,
            'failed_custom': 0
        }
        logger.info(f"Initialized SignalFilter with config: {config}")

    def filter_signals(self, signals: List[EnrichedSignal]) -> List[EnrichedSignal]:
        """
        Apply all filters to signal list.

        Args:
            signals: List of enriched signals

        Returns:
            List of filtered signals

        Examples:
            >>> signals = [signal1, signal2, signal3]
            >>> filtered = filter_obj.filter_signals(signals)
        """
        self.filter_stats['total_processed'] += len(signals)
        filtered = signals.copy()

        # Apply confidence filter
        filtered = self._filter_by_confidence(filtered)

        # Apply risk/reward filter
        filtered = self._filter_by_risk_reward(filtered)

        # Apply signal type filter
        filtered = self._filter_by_signal_type(filtered)

        # Apply instrument filter
        filtered = self._filter_by_instrument(filtered)

        # Apply timeframe filter
        filtered = self._filter_by_timeframe(filtered)

        # Apply trend alignment filter
        if self.config.require_trend_alignment:
            filtered = self._filter_by_trend_alignment(filtered)

        # Apply trading hours filter
        if self.config.trading_hours_only:
            filtered = self._filter_by_trading_hours(filtered)

        # Apply market session filter
        if self.config.market_sessions:
            filtered = self._filter_by_market_session(filtered)

        # Apply volume confirmation filter
        if self.config.min_volume_confirmation > 0:
            filtered = self._filter_by_volume(filtered)

        # Apply custom filters
        for custom_filter in self.config.custom_filters:
            filtered = self._apply_custom_filter(filtered, custom_filter)

        # Apply max signals limit
        if len(filtered) > self.config.max_signals_per_update:
            # Sort by composite score and take top N
            filtered = sorted(filtered, key=lambda x: x.composite_score, reverse=True)
            filtered = filtered[:self.config.max_signals_per_update]

        self.filter_stats['passed'] += len(filtered)

        logger.info(f"Filtered {len(signals)} signals -> {len(filtered)} signals passed")
        return filtered

    def _filter_by_confidence(self, signals: List[EnrichedSignal]) -> List[EnrichedSignal]:
        """Filter by minimum confidence score."""
        before = len(signals)
        filtered = [s for s in signals if s.signal.confidence >= self.config.min_confidence]
        self.filter_stats['failed_confidence'] += (before - len(filtered))
        return filtered

    def _filter_by_risk_reward(self, signals: List[EnrichedSignal]) -> List[EnrichedSignal]:
        """Filter by minimum risk/reward ratio."""
        before = len(signals)
        filtered = [s for s in signals if s.signal.risk_reward_ratio >= self.config.min_risk_reward]
        self.filter_stats['failed_risk_reward'] += (before - len(filtered))
        return filtered

    def _filter_by_signal_type(self, signals: List[EnrichedSignal]) -> List[EnrichedSignal]:
        """Filter by allowed signal types."""
        if not self.config.allowed_signal_types:
            return signals

        before = len(signals)
        filtered = [s for s in signals if s.signal.signal_type in self.config.allowed_signal_types]
        self.filter_stats['failed_signal_type'] += (before - len(filtered))
        return filtered

    def _filter_by_instrument(self, signals: List[EnrichedSignal]) -> List[EnrichedSignal]:
        """Filter by allowed/blocked instruments."""
        filtered = signals

        if self.config.blocked_instruments:
            before = len(filtered)
            filtered = [s for s in filtered if s.instrument not in self.config.blocked_instruments]
            self.filter_stats['failed_instrument'] += (before - len(filtered))

        if self.config.allowed_instruments:
            before = len(filtered)
            filtered = [s for s in filtered if s.instrument in self.config.allowed_instruments]
            self.filter_stats['failed_instrument'] += (before - len(filtered))

        return filtered

    def _filter_by_timeframe(self, signals: List[EnrichedSignal]) -> List[EnrichedSignal]:
        """Filter by allowed timeframes."""
        if not self.config.allowed_timeframes:
            return signals

        before = len(signals)
        filtered = [s for s in signals if s.timeframe in self.config.allowed_timeframes]
        self.filter_stats['failed_timeframe'] += (before - len(filtered))
        return filtered

    def _filter_by_trend_alignment(self, signals: List[EnrichedSignal]) -> List[EnrichedSignal]:
        """Filter by trend alignment strength."""
        before = len(signals)
        filtered = [s for s in signals if s.trend_alignment >= self.config.min_trend_strength]
        self.filter_stats['failed_trend'] += (before - len(filtered))
        return filtered

    def _filter_by_trading_hours(self, signals: List[EnrichedSignal]) -> List[EnrichedSignal]:
        """Filter signals to trading hours only (09:30-16:00 EST)."""
        filtered = []
        for signal in signals:
            if signal.signal.timestamp:
                hour = signal.signal.timestamp.hour
                # Trading hours: 9:30 AM - 4:00 PM
                if 9 <= hour < 16 or (hour == 9 and signal.signal.timestamp.minute >= 30):
                    filtered.append(signal)
        return filtered

    def _filter_by_market_session(self, signals: List[EnrichedSignal]) -> List[EnrichedSignal]:
        """Filter by market session."""
        filtered = [s for s in signals if s.market_session in self.config.market_sessions]
        return filtered

    def _filter_by_volume(self, signals: List[EnrichedSignal]) -> List[EnrichedSignal]:
        """Filter by volume confirmation."""
        filtered = [s for s in signals if s.volume_confirmation >= self.config.min_volume_confirmation]
        return filtered

    def _apply_custom_filter(self, signals: List[EnrichedSignal],
                            filter_func: Callable[[Dict], bool]) -> List[EnrichedSignal]:
        """Apply custom filter function."""
        before = len(signals)
        filtered = []
        for signal in signals:
            try:
                if filter_func(signal.to_dict()):
                    filtered.append(signal)
            except Exception as e:
                logger.warning(f"Custom filter failed for signal: {e}")
                continue

        self.filter_stats['failed_custom'] += (before - len(filtered))
        return filtered

    def get_filter_stats(self) -> Dict[str, int]:
        """Get filter statistics."""
        return self.filter_stats.copy()

    def reset_stats(self):
        """Reset filter statistics."""
        for key in self.filter_stats:
            self.filter_stats[key] = 0


class SignalRanker:
    """
    Rank signals by various criteria.

    This class provides multiple ranking methods including confidence score,
    risk/reward ratio, and composite scoring with weighted factors.

    Examples:
        >>> ranker = SignalRanker()
        >>> ranked = ranker.rank_signals(signals, RankingMethod.COMPOSITE)
        >>> top_signals = ranked[:5]  # Get top 5 signals
    """

    # Default weights for composite scoring
    DEFAULT_WEIGHTS = {
        'confidence': 0.40,
        'risk_reward': 0.30,
        'trend_alignment': 0.15,
        'volume_confirmation': 0.15
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize SignalRanker.

        Args:
            weights: Custom weights for composite scoring (must sum to 1.0)
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()

        # Validate weights
        if abs(sum(self.weights.values()) - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {sum(self.weights.values())}")

        logger.info(f"Initialized SignalRanker with weights: {self.weights}")

    def rank_signals(self, signals: List[EnrichedSignal],
                    method: RankingMethod = RankingMethod.COMPOSITE,
                    descending: bool = True) -> List[EnrichedSignal]:
        """
        Rank signals by specified method.

        Args:
            signals: List of enriched signals
            method: Ranking method to use
            descending: Sort in descending order (best first)

        Returns:
            Ranked list of signals

        Examples:
            >>> ranked = ranker.rank_signals(signals, RankingMethod.CONFIDENCE)
            >>> print(f"Best signal: {ranked[0].instrument}")
        """
        if not signals:
            return []

        # Calculate composite scores if using composite method
        if method == RankingMethod.COMPOSITE:
            signals = self._calculate_composite_scores(signals)

        # Sort by selected method
        if method == RankingMethod.CONFIDENCE:
            key_func = lambda x: x.signal.confidence
        elif method == RankingMethod.RISK_REWARD:
            key_func = lambda x: x.signal.risk_reward_ratio
        elif method == RankingMethod.COMPOSITE:
            key_func = lambda x: x.composite_score
        elif method == RankingMethod.TREND_ALIGNMENT:
            key_func = lambda x: x.trend_alignment
        elif method == RankingMethod.VOLUME:
            key_func = lambda x: x.volume_confirmation
        else:
            logger.warning(f"Unknown ranking method: {method}, using confidence")
            key_func = lambda x: x.signal.confidence

        ranked = sorted(signals, key=key_func, reverse=descending)

        logger.info(f"Ranked {len(signals)} signals by {method.value}")
        return ranked

    def _calculate_composite_scores(self, signals: List[EnrichedSignal]) -> List[EnrichedSignal]:
        """
        Calculate composite scores for all signals.

        Args:
            signals: List of enriched signals

        Returns:
            Signals with updated composite scores
        """
        for signal in signals:
            signal.composite_score = calculate_composite_score(
                signal,
                self.weights
            )
        return signals

    def get_top_signals(self, signals: List[EnrichedSignal], n: int,
                       method: RankingMethod = RankingMethod.COMPOSITE) -> List[EnrichedSignal]:
        """
        Get top N signals.

        Args:
            signals: List of enriched signals
            n: Number of top signals to return
            method: Ranking method

        Returns:
            Top N signals

        Examples:
            >>> top_5 = ranker.get_top_signals(signals, 5)
        """
        ranked = self.rank_signals(signals, method, descending=True)
        return ranked[:n]

    def get_bottom_signals(self, signals: List[EnrichedSignal], n: int,
                          method: RankingMethod = RankingMethod.COMPOSITE) -> List[EnrichedSignal]:
        """
        Get bottom N signals (worst signals).

        Args:
            signals: List of enriched signals
            n: Number of bottom signals to return
            method: Ranking method

        Returns:
            Bottom N signals
        """
        ranked = self.rank_signals(signals, method, descending=False)
        return ranked[:n]


class SignalAggregator:
    """
    Aggregate signals across timeframes and detect confluence.

    This class combines signals from multiple timeframes, detects when
    multiple indicators agree (confluence), and identifies divergences.

    Examples:
        >>> aggregator = SignalAggregator()
        >>> aggregated = aggregator.aggregate_signals(signals_by_timeframe)
        >>> confluence = aggregator.detect_confluence(signals)
    """

    # Timeframe weights (higher timeframe = higher weight)
    TIMEFRAME_WEIGHTS = {
        TimeFrame.M1: 1,
        TimeFrame.M5: 2,
        TimeFrame.M15: 3,
        TimeFrame.M30: 4,
        TimeFrame.H1: 5,
        TimeFrame.H4: 7,
        TimeFrame.D1: 10,
        TimeFrame.W1: 15,
        TimeFrame.MN1: 20
    }

    def __init__(self, timeframe_weights: Optional[Dict[TimeFrame, float]] = None):
        """
        Initialize SignalAggregator.

        Args:
            timeframe_weights: Custom timeframe weights
        """
        self.timeframe_weights = timeframe_weights or self.TIMEFRAME_WEIGHTS.copy()
        logger.info("Initialized SignalAggregator")

    def aggregate_signals(self, signals_by_timeframe: Dict[TimeFrame, List[EnrichedSignal]],
                         instrument: str) -> Dict[str, Any]:
        """
        Aggregate signals across timeframes for a single instrument.

        Args:
            signals_by_timeframe: Dict mapping timeframes to signal lists
            instrument: Instrument to aggregate

        Returns:
            Aggregated signal analysis

        Examples:
            >>> signals_by_tf = {
            ...     TimeFrame.H1: [signal_h1],
            ...     TimeFrame.H4: [signal_h4],
            ...     TimeFrame.D1: [signal_d1]
            ... }
            >>> result = aggregator.aggregate_signals(signals_by_tf, "EUR_USD")
        """
        aggregated = {
            'instrument': instrument,
            'timeframes': {},
            'weighted_direction': 0.0,
            'confluence_score': 0.0,
            'has_divergence': False,
            'recommendation': SignalType.HOLD
        }

        total_weight = 0.0
        weighted_score = 0.0

        signal_types = []

        for timeframe, signals in signals_by_timeframe.items():
            # Filter signals for this instrument
            instrument_signals = [s for s in signals if s.instrument == instrument]

            if not instrument_signals:
                continue

            # Take the best signal for this timeframe
            best_signal = max(instrument_signals, key=lambda x: x.signal.confidence)

            # Get timeframe weight
            weight = self.timeframe_weights.get(timeframe, 1.0)
            total_weight += weight

            # Calculate weighted direction score
            direction_score = self._get_direction_score(best_signal.signal.signal_type)
            weighted_score += direction_score * weight * (best_signal.signal.confidence / 100)

            signal_types.append(best_signal.signal.signal_type)

            aggregated['timeframes'][timeframe.value] = {
                'signal_type': best_signal.signal.signal_type.value,
                'confidence': best_signal.signal.confidence,
                'weight': weight
            }

        # Calculate weighted direction
        if total_weight > 0:
            aggregated['weighted_direction'] = weighted_score / total_weight

        # Calculate confluence score (how much signals agree)
        aggregated['confluence_score'] = self._calculate_confluence_score(signal_types)

        # Detect divergences
        aggregated['has_divergence'] = self._has_divergence(signal_types)

        # Determine recommendation
        aggregated['recommendation'] = self._get_recommendation(
            aggregated['weighted_direction'],
            aggregated['confluence_score']
        )

        logger.debug(f"Aggregated signals for {instrument}: {aggregated['recommendation'].value}")
        return aggregated

    def detect_confluence(self, signals: List[EnrichedSignal],
                         min_confluence: int = 2) -> List[Dict[str, Any]]:
        """
        Detect signal confluence (multiple signals agreeing).

        Args:
            signals: List of enriched signals
            min_confluence: Minimum number of agreeing signals

        Returns:
            List of confluence detections

        Examples:
            >>> confluence = aggregator.detect_confluence(signals, min_confluence=3)
            >>> for conf in confluence:
            ...     print(f"{conf['instrument']}: {conf['count']} signals agree")
        """
        # Group signals by instrument and signal type
        confluence_map = defaultdict(lambda: defaultdict(list))

        for signal in signals:
            signal_type = signal.signal.signal_type
            if signal_type not in [SignalType.HOLD, SignalType.NO_SIGNAL]:
                confluence_map[signal.instrument][signal_type].append(signal)

        # Find confluences
        confluences = []
        for instrument, signal_types in confluence_map.items():
            for signal_type, agreeing_signals in signal_types.items():
                if len(agreeing_signals) >= min_confluence:
                    avg_confidence = np.mean([s.signal.confidence for s in agreeing_signals])
                    timeframes = [s.timeframe.value for s in agreeing_signals]

                    confluences.append({
                        'instrument': instrument,
                        'signal_type': signal_type.value,
                        'count': len(agreeing_signals),
                        'avg_confidence': float(avg_confidence),
                        'timeframes': timeframes,
                        'signals': agreeing_signals
                    })

        # Sort by count and confidence
        confluences.sort(key=lambda x: (x['count'], x['avg_confidence']), reverse=True)

        logger.info(f"Detected {len(confluences)} confluences (min={min_confluence})")
        return confluences

    def detect_divergences(self, signals: List[EnrichedSignal]) -> List[Dict[str, Any]]:
        """
        Detect timeframe divergences (different signals across timeframes).

        Args:
            signals: List of enriched signals

        Returns:
            List of divergence detections

        Examples:
            >>> divergences = aggregator.detect_divergences(signals)
        """
        # Group signals by instrument
        signals_by_instrument = defaultdict(list)
        for signal in signals:
            signals_by_instrument[signal.instrument].append(signal)

        divergences = []

        for instrument, inst_signals in signals_by_instrument.items():
            # Get signals from different timeframes
            if len(inst_signals) < 2:
                continue

            # Check for opposing signals
            has_buy = any(s.signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]
                         for s in inst_signals)
            has_sell = any(s.signal.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]
                          for s in inst_signals)

            if has_buy and has_sell:
                buy_signals = [s for s in inst_signals
                              if s.signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]]
                sell_signals = [s for s in inst_signals
                               if s.signal.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]]

                divergences.append({
                    'instrument': instrument,
                    'type': 'opposing_signals',
                    'buy_timeframes': [s.timeframe.value for s in buy_signals],
                    'sell_timeframes': [s.timeframe.value for s in sell_signals],
                    'buy_signals': buy_signals,
                    'sell_signals': sell_signals
                })

        logger.info(f"Detected {len(divergences)} divergences")
        return divergences

    def _get_direction_score(self, signal_type: SignalType) -> float:
        """Convert signal type to direction score (-1 to 1)."""
        if signal_type == SignalType.STRONG_BUY:
            return 1.0
        elif signal_type == SignalType.BUY:
            return 0.5
        elif signal_type == SignalType.STRONG_SELL:
            return -1.0
        elif signal_type == SignalType.SELL:
            return -0.5
        else:
            return 0.0

    def _calculate_confluence_score(self, signal_types: List[SignalType]) -> float:
        """Calculate how much signals agree (0-100)."""
        if len(signal_types) < 2:
            return 0.0

        # Count bullish vs bearish
        bullish = sum(1 for st in signal_types
                     if st in [SignalType.BUY, SignalType.STRONG_BUY])
        bearish = sum(1 for st in signal_types
                     if st in [SignalType.SELL, SignalType.STRONG_SELL])
        total = bullish + bearish

        if total == 0:
            return 0.0

        # High confluence = most signals agree
        max_agreement = max(bullish, bearish)
        confluence = (max_agreement / total) * 100

        return float(confluence)

    def _has_divergence(self, signal_types: List[SignalType]) -> bool:
        """Check if there's a divergence in signals."""
        has_buy = any(st in [SignalType.BUY, SignalType.STRONG_BUY] for st in signal_types)
        has_sell = any(st in [SignalType.SELL, SignalType.STRONG_SELL] for st in signal_types)
        return has_buy and has_sell

    def _get_recommendation(self, weighted_direction: float,
                          confluence_score: float) -> SignalType:
        """Get final recommendation based on weighted direction and confluence."""
        # Require high confluence for strong signals
        if confluence_score < 50:
            return SignalType.HOLD

        if weighted_direction > 0.6 and confluence_score >= 70:
            return SignalType.STRONG_BUY
        elif weighted_direction > 0.3:
            return SignalType.BUY
        elif weighted_direction < -0.6 and confluence_score >= 70:
            return SignalType.STRONG_SELL
        elif weighted_direction < -0.3:
            return SignalType.SELL
        else:
            return SignalType.HOLD


class SignalCorrelationAnalyzer:
    """
    Analyze correlations between signals across instruments and sectors.

    This class detects market-wide moves, sector trends, and divergences
    between related instruments.

    Examples:
        >>> analyzer = SignalCorrelationAnalyzer()
        >>> market_wide = analyzer.detect_market_wide_signals(signals)
        >>> sector_analysis = analyzer.analyze_by_sector(signals)
    """

    def __init__(self):
        """Initialize SignalCorrelationAnalyzer."""
        logger.info("Initialized SignalCorrelationAnalyzer")

    def detect_market_wide_signals(self, signals: List[EnrichedSignal],
                                   min_instruments: int = 5,
                                   min_agreement: float = 0.7) -> Dict[str, Any]:
        """
        Detect market-wide moves (multiple instruments showing same signal).

        Args:
            signals: List of enriched signals
            min_instruments: Minimum instruments for market-wide signal
            min_agreement: Minimum agreement ratio (0-1)

        Returns:
            Market-wide signal analysis

        Examples:
            >>> market = analyzer.detect_market_wide_signals(signals, min_instruments=10)
            >>> if market['detected']:
            ...     print(f"Market-wide {market['direction']} detected")
        """
        # Count signals by type
        signal_counts = defaultdict(int)
        instruments_by_type = defaultdict(set)

        for signal in signals:
            signal_type = signal.signal.signal_type
            if signal_type not in [SignalType.HOLD, SignalType.NO_SIGNAL]:
                signal_counts[signal_type] += 1
                instruments_by_type[signal_type].add(signal.instrument)

        # Check for market-wide signal
        total_instruments = len(set(s.instrument for s in signals))

        market_wide = {
            'detected': False,
            'direction': None,
            'instrument_count': 0,
            'agreement_ratio': 0.0,
            'instruments': []
        }

        for signal_type, count in signal_counts.items():
            agreement_ratio = count / len(signals) if signals else 0
            instrument_count = len(instruments_by_type[signal_type])

            if (instrument_count >= min_instruments and
                agreement_ratio >= min_agreement):
                market_wide['detected'] = True
                market_wide['direction'] = signal_type.value
                market_wide['instrument_count'] = instrument_count
                market_wide['agreement_ratio'] = float(agreement_ratio)
                market_wide['instruments'] = list(instruments_by_type[signal_type])
                break

        if market_wide['detected']:
            logger.info(f"Market-wide signal detected: {market_wide['direction']}")

        return market_wide

    def analyze_by_sector(self, signals: List[EnrichedSignal]) -> Dict[str, Dict[str, Any]]:
        """
        Analyze signals by sector/category.

        Args:
            signals: List of enriched signals

        Returns:
            Dict mapping sectors to analysis

        Examples:
            >>> sector_analysis = analyzer.analyze_by_sector(signals)
            >>> for sector, analysis in sector_analysis.items():
            ...     print(f"{sector}: {analysis['trend']}")
        """
        # Group signals by sector
        signals_by_sector = defaultdict(list)

        for signal in signals:
            sector = signal.sector or 'unknown'
            signals_by_sector[sector].append(signal)

        # Analyze each sector
        sector_analysis = {}

        for sector, sector_signals in signals_by_sector.items():
            # Count signal types
            bullish = sum(1 for s in sector_signals
                         if s.signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY])
            bearish = sum(1 for s in sector_signals
                         if s.signal.signal_type in [SignalType.SELL, SignalType.STRONG_SELL])
            total = len(sector_signals)

            # Determine sector trend
            if bullish > bearish * 1.5:
                trend = 'bullish'
            elif bearish > bullish * 1.5:
                trend = 'bearish'
            else:
                trend = 'mixed'

            # Average confidence
            avg_confidence = np.mean([s.signal.confidence for s in sector_signals])

            sector_analysis[sector] = {
                'trend': trend,
                'bullish_count': bullish,
                'bearish_count': bearish,
                'total_count': total,
                'bullish_ratio': bullish / total if total > 0 else 0,
                'bearish_ratio': bearish / total if total > 0 else 0,
                'avg_confidence': float(avg_confidence),
                'instruments': [s.instrument for s in sector_signals]
            }

        logger.info(f"Analyzed {len(sector_analysis)} sectors")
        return sector_analysis

    def detect_related_divergences(self, signals: List[EnrichedSignal],
                                   related_pairs: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        """
        Detect divergences between related instruments.

        Args:
            signals: List of enriched signals
            related_pairs: List of related instrument pairs

        Returns:
            List of divergence detections

        Examples:
            >>> related = [("EUR_USD", "GBP_USD"), ("GOLD", "SILVER")]
            >>> divergences = analyzer.detect_related_divergences(signals, related)
        """
        # Create instrument signal map
        signal_map = {}
        for signal in signals:
            if signal.instrument not in signal_map:
                signal_map[signal.instrument] = signal
            elif signal.signal.confidence > signal_map[signal.instrument].signal.confidence:
                signal_map[signal.instrument] = signal

        divergences = []

        for inst1, inst2 in related_pairs:
            if inst1 in signal_map and inst2 in signal_map:
                sig1 = signal_map[inst1]
                sig2 = signal_map[inst2]

                # Check for opposing signals
                type1 = sig1.signal.signal_type
                type2 = sig2.signal.signal_type

                is_divergent = False

                if (type1 in [SignalType.BUY, SignalType.STRONG_BUY] and
                    type2 in [SignalType.SELL, SignalType.STRONG_SELL]):
                    is_divergent = True
                elif (type1 in [SignalType.SELL, SignalType.STRONG_SELL] and
                      type2 in [SignalType.BUY, SignalType.STRONG_BUY]):
                    is_divergent = True

                if is_divergent:
                    divergences.append({
                        'instrument_1': inst1,
                        'instrument_2': inst2,
                        'signal_1': type1.value,
                        'signal_2': type2.value,
                        'confidence_1': sig1.signal.confidence,
                        'confidence_2': sig2.signal.confidence
                    })

        logger.info(f"Detected {len(divergences)} related divergences")
        return divergences


# Utility Functions

def calculate_composite_score(signal: EnrichedSignal,
                             weights: Optional[Dict[str, float]] = None) -> float:
    """
    Calculate composite score for a signal.

    Args:
        signal: Enriched signal
        weights: Custom weights for scoring factors

    Returns:
        Composite score (0-100)

    Examples:
        >>> score = calculate_composite_score(signal)
        >>> print(f"Composite score: {score:.2f}")
    """
    if weights is None:
        weights = SignalRanker.DEFAULT_WEIGHTS

    # Normalize risk/reward to 0-100 scale (cap at 5:1)
    rr_normalized = min(signal.signal.risk_reward_ratio / 5.0, 1.0) * 100

    # Calculate weighted score
    score = (
        weights['confidence'] * signal.signal.confidence +
        weights['risk_reward'] * rr_normalized +
        weights['trend_alignment'] * signal.trend_alignment +
        weights['volume_confirmation'] * signal.volume_confirmation
    )

    return float(score)


def apply_filters(signals: List[EnrichedSignal], config: FilterConfig) -> List[EnrichedSignal]:
    """
    Apply filters to signal list.

    Args:
        signals: List of enriched signals
        config: Filter configuration

    Returns:
        Filtered signals

    Examples:
        >>> config = FilterConfig(min_confidence=70.0, min_risk_reward=2.0)
        >>> filtered = apply_filters(signals, config)
    """
    filter_obj = SignalFilter(config)
    return filter_obj.filter_signals(signals)


def rank_signals(signals: List[EnrichedSignal],
                method: RankingMethod = RankingMethod.COMPOSITE,
                descending: bool = True) -> List[EnrichedSignal]:
    """
    Rank and sort signals.

    Args:
        signals: List of enriched signals
        method: Ranking method
        descending: Sort descending (best first)

    Returns:
        Ranked signals

    Examples:
        >>> ranked = rank_signals(signals, RankingMethod.CONFIDENCE)
        >>> print(f"Best signal: {ranked[0].instrument}")
    """
    ranker = SignalRanker()
    return ranker.rank_signals(signals, method, descending)


def get_top_signals(signals: List[EnrichedSignal], n: int,
                   method: RankingMethod = RankingMethod.COMPOSITE) -> List[EnrichedSignal]:
    """
    Get top N signals.

    Args:
        signals: List of enriched signals
        n: Number of signals to return
        method: Ranking method

    Returns:
        Top N signals

    Examples:
        >>> top_5 = get_top_signals(signals, 5)
    """
    ranker = SignalRanker()
    return ranker.get_top_signals(signals, n, method)


def detect_signal_conflicts(signals: List[EnrichedSignal]) -> List[Dict[str, Any]]:
    """
    Detect conflicting signals (opposing signals for same instrument).

    Args:
        signals: List of enriched signals

    Returns:
        List of conflicts

    Examples:
        >>> conflicts = detect_signal_conflicts(signals)
        >>> for conflict in conflicts:
        ...     print(f"Conflict in {conflict['instrument']}")
    """
    # Group by instrument
    signals_by_instrument = defaultdict(list)
    for signal in signals:
        signals_by_instrument[signal.instrument].append(signal)

    conflicts = []

    for instrument, inst_signals in signals_by_instrument.items():
        # Check for opposing signals
        has_buy = any(s.signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]
                     for s in inst_signals)
        has_sell = any(s.signal.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]
                      for s in inst_signals)

        if has_buy and has_sell:
            buy_signals = [s for s in inst_signals
                          if s.signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]]
            sell_signals = [s for s in inst_signals
                           if s.signal.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]]

            conflicts.append({
                'instrument': instrument,
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'buy_count': len(buy_signals),
                'sell_count': len(sell_signals)
            })

    logger.info(f"Detected {len(conflicts)} signal conflicts")
    return conflicts


def deduplicate_signals(signals: List[EnrichedSignal],
                       key: str = 'instrument') -> List[EnrichedSignal]:
    """
    Remove duplicate signals, keeping the best one.

    Args:
        signals: List of enriched signals
        key: Deduplication key ('instrument', 'timeframe', or 'both')

    Returns:
        Deduplicated signals

    Examples:
        >>> unique = deduplicate_signals(signals, key='instrument')
    """
    seen = {}
    deduplicated = []

    for signal in signals:
        if key == 'instrument':
            key_value = signal.instrument
        elif key == 'timeframe':
            key_value = signal.timeframe
        elif key == 'both':
            key_value = (signal.instrument, signal.timeframe)
        else:
            raise ValueError(f"Invalid key: {key}")

        # Keep signal with highest confidence
        if key_value not in seen:
            seen[key_value] = signal
            deduplicated.append(signal)
        elif signal.signal.confidence > seen[key_value].signal.confidence:
            # Replace with higher confidence signal
            deduplicated.remove(seen[key_value])
            seen[key_value] = signal
            deduplicated.append(signal)

    logger.info(f"Deduplicated {len(signals)} -> {len(deduplicated)} signals")
    return deduplicated
