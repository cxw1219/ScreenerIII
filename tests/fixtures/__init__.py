"""
Test fixtures package for ScreenerIII.

This package contains sample data and helper functions for use in tests.
"""

from .sample_data import (
    create_sample_ohlcv_data,
    create_sample_candle,
    create_bullish_candles,
    create_bearish_candles,
    create_volatile_candles,
    create_rsi_overbought_data,
    create_rsi_oversold_data,
    create_golden_cross_data,
    create_death_cross_data,
    create_macd_bullish_divergence,
    create_multiinstrument_data,
    create_market_microstructure_data,
    SAMPLE_BULLISH_ENGULFING,
    SAMPLE_BEARISH_ENGULFING,
    SAMPLE_HAMMER,
    SAMPLE_SHOOTING_STAR,
)

__all__ = [
    "create_sample_ohlcv_data",
    "create_sample_candle",
    "create_bullish_candles",
    "create_bearish_candles",
    "create_volatile_candles",
    "create_rsi_overbought_data",
    "create_rsi_oversold_data",
    "create_golden_cross_data",
    "create_death_cross_data",
    "create_macd_bullish_divergence",
    "create_multiinstrument_data",
    "create_market_microstructure_data",
    "SAMPLE_BULLISH_ENGULFING",
    "SAMPLE_BEARISH_ENGULFING",
    "SAMPLE_HAMMER",
    "SAMPLE_SHOOTING_STAR",
]
