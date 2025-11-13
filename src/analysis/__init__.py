"""
Analysis and screening modules.

This package provides comprehensive technical analysis, pattern recognition,
signal generation, and backtesting capabilities for trading strategies.

Modules:
    - indicators: Technical indicators (RSI, MACD, Bollinger Bands, etc.)
    - patterns: Chart and candlestick pattern recognition
    - signals: Trading signal generation with confidence scoring
    - backtesting: Comprehensive backtesting framework for strategy validation
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
    'run_simple_backtest'
]
