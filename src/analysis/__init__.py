"""
Analysis and screening modules.

This package provides comprehensive technical analysis, pattern recognition,
signal generation, backtesting capabilities, and multi-timeframe analysis
for trading strategies.

Modules:
    - indicators: Technical indicators (RSI, MACD, Bollinger Bands, etc.)
    - patterns: Chart and candlestick pattern recognition
    - signals: Trading signal generation with confidence scoring
    - backtesting: Comprehensive backtesting framework for strategy validation
    - multi_timeframe: Multi-timeframe analysis and signal confluence detection
"""

from .indicators import TechnicalIndicators
from .patterns import PatternRecognition
from .signals import SignalGenerator, SignalType, TradingSignal
from .backtesting import (
    Backtester,
    Strategy,
    SignalStrategy,
    PortfolioTracker,
    Trade,
    PerformanceMetrics,
    BacktestResults,
    ExitReason,
    PositionSide,
    load_data_from_timescaledb,
    run_simple_backtest
)
from .multi_timeframe import (
    TimeFrame,
    TimeFrameSignal,
    MultiTimeFrameSignal,
    MultiTimeFrameAnalyzer,
    TimeFrameSynchronizer,
    quick_mtf_analysis,
    compare_timeframes
)

__all__ = [
    # Indicators
    'TechnicalIndicators',
    # Patterns
    'PatternRecognition',
    # Signals
    'SignalGenerator',
    'SignalType',
    'TradingSignal',
    # Backtesting
    'Backtester',
    'Strategy',
    'SignalStrategy',
    'PortfolioTracker',
    'Trade',
    'PerformanceMetrics',
    'BacktestResults',
    'ExitReason',
    'PositionSide',
    'load_data_from_timescaledb',
    'run_simple_backtest',
    # Multi-Timeframe Analysis
    'TimeFrame',
    'TimeFrameSignal',
    'MultiTimeFrameSignal',
    'MultiTimeFrameAnalyzer',
    'TimeFrameSynchronizer',
    'quick_mtf_analysis',
    'compare_timeframes'
]
