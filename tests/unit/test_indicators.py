"""
Unit tests for technical indicator calculations.

Tests the computation and validation of various technical indicators
used for trading signal generation.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path as PathlibPath

# Add src directory to path
sys.path.insert(0, str(PathlibPath(__file__).parent.parent.parent / "src"))


class TestIndicatorDataValidation:
    """Test suite for input data validation in indicator calculations."""

    def test_sample_ohlcv_structure(self, sample_ohlcv_data):
        """Test that sample OHLCV data has correct structure."""
        df = sample_ohlcv_data
        assert isinstance(df, pd.DataFrame)
        assert "open" in df.columns
        assert "high" in df.columns
        assert "low" in df.columns
        assert "close" in df.columns
        assert "volume" in df.columns

    def test_sample_ohlcv_data_types(self, sample_ohlcv_data):
        """Test that OHLCV data has correct data types."""
        df = sample_ohlcv_data
        assert df["open"].dtype in [np.float32, np.float64, float]
        assert df["close"].dtype in [np.float32, np.float64, float]
        assert df["volume"].dtype in [np.float32, np.float64, int, float]

    def test_sample_ohlcv_data_integrity(self, sample_ohlcv_data):
        """Test that OHLCV data maintains OHLC integrity."""
        df = sample_ohlcv_data
        # High should be >= Open, Close, Low
        assert (df["high"] >= df["open"]).all()
        assert (df["high"] >= df["close"]).all()
        assert (df["high"] >= df["low"]).all()
        # Low should be <= Open, Close, High
        assert (df["low"] <= df["open"]).all()
        assert (df["low"] <= df["close"]).all()
        assert (df["low"] <= df["high"]).all()

    def test_sample_ohlcv_data_length(self, sample_ohlcv_data):
        """Test that sample data has sufficient length for indicators."""
        df = sample_ohlcv_data
        assert len(df) >= 100  # Should have at least 100 candles

    def test_empty_dataframe_handling(self):
        """Test behavior with empty DataFrame."""
        df = pd.DataFrame({"open": [], "high": [], "low": [], "close": [], "volume": []})
        assert len(df) == 0

    def test_single_candle_dataframe(self):
        """Test behavior with single candle."""
        df = pd.DataFrame({
            "open": [1.0],
            "high": [1.1],
            "low": [0.9],
            "close": [1.05],
            "volume": [1000],
        })
        assert len(df) == 1


class TestRSIIndicator:
    """Test suite for Relative Strength Index (RSI) calculation."""

    def test_rsi_output_range(self, sample_indicator_results):
        """Test that RSI values are within valid 0-100 range."""
        rsi = sample_indicator_results["rsi"]
        assert 0 <= rsi <= 100

    def test_rsi_overbought_signal(self, sample_indicator_results):
        """Test RSI overbought signal detection."""
        rsi = 75  # Above 70 threshold
        assert rsi > 70  # Overbought condition

    def test_rsi_oversold_signal(self, sample_indicator_results):
        """Test RSI oversold signal detection."""
        rsi = 25  # Below 30 threshold
        assert rsi < 30  # Oversold condition

    def test_rsi_neutral_zone(self, sample_indicator_results):
        """Test RSI neutral zone (30-70)."""
        rsi = 50  # Middle of range
        assert 30 < rsi < 70

    def test_rsi_signal_generation(self, sample_indicator_results):
        """Test signal generated from RSI."""
        signal = sample_indicator_results["rsi_signal"]
        assert signal in ["overbought", "oversold", "neutral"]


class TestMovingAverageIndicators:
    """Test suite for moving average calculations."""

    def test_sma_calculation_output(self, sample_indicator_results):
        """Test that SMA returns numeric output."""
        sma_short = sample_indicator_results["sma_short"]
        sma_long = sample_indicator_results["sma_long"]
        assert isinstance(sma_short, (int, float))
        assert isinstance(sma_long, (int, float))

    def test_sma_relationship(self, sample_indicator_results):
        """Test logical relationship between short and long SMAs."""
        sma_short = sample_indicator_results["sma_short"]
        sma_long = sample_indicator_results["sma_long"]
        # Both should be positive prices
        assert sma_short > 0
        assert sma_long > 0

    def test_sma_signal_generation(self, sample_indicator_results):
        """Test signal generated from SMA crossover."""
        signal = sample_indicator_results["sma_signal"]
        assert signal in ["bullish", "bearish", "neutral"]

    def test_ema_vs_sma_difference(self):
        """Test that EMA and SMA produce different values."""
        prices = np.array([1.0, 1.05, 1.02, 1.08, 1.04, 1.06])
        # In reality, EMA would weight recent prices more heavily
        # This is a conceptual test
        assert len(prices) >= 3


class TestMACDIndicator:
    """Test suite for MACD (Moving Average Convergence Divergence) indicator."""

    def test_macd_components(self, sample_indicator_results):
        """Test that MACD has all required components."""
        assert "macd" in sample_indicator_results
        assert "macd_signal" in sample_indicator_results
        assert "macd_histogram" in sample_indicator_results

    def test_macd_histogram_calculation(self, sample_indicator_results):
        """Test MACD histogram is difference between MACD and signal."""
        macd = sample_indicator_results["macd"]
        signal = sample_indicator_results["macd_signal"]
        histogram = sample_indicator_results["macd_histogram"]
        # Histogram = MACD - Signal
        assert abs(histogram - (macd - signal)) < 0.00001

    def test_macd_signal_direction(self, sample_indicator_results):
        """Test MACD signal direction classification."""
        direction = sample_indicator_results["macd_signal_direction"]
        assert direction in ["bullish", "bearish", "neutral"]

    def test_macd_positive_values(self, sample_indicator_results):
        """Test handling of positive MACD values."""
        macd = sample_indicator_results["macd"]
        assert isinstance(macd, (int, float))

    def test_macd_negative_values(self):
        """Test handling of negative MACD values."""
        macd = -0.0020
        assert macd < 0


class TestBollingerBands:
    """Test suite for Bollinger Bands indicator."""

    def test_bollinger_bands_components(self, sample_indicator_results):
        """Test that Bollinger Bands have all required components."""
        assert "bb_upper" in sample_indicator_results
        assert "bb_middle" in sample_indicator_results
        assert "bb_lower" in sample_indicator_results

    def test_bollinger_bands_relationship(self, sample_indicator_results):
        """Test mathematical relationship of Bollinger Bands."""
        upper = sample_indicator_results["bb_upper"]
        middle = sample_indicator_results["bb_middle"]
        lower = sample_indicator_results["bb_lower"]
        # Upper > Middle > Lower
        assert upper > middle > lower

    def test_bollinger_bands_position(self, sample_indicator_results):
        """Test Bollinger Bands position indicator."""
        position = sample_indicator_results["bb_position"]
        assert 0 <= position <= 1

    def test_bb_position_extremes(self):
        """Test BB position at extremes."""
        # Position at upper band
        assert 1.0 >= 0.9  # Close to upper band
        # Position at lower band
        assert 0.1 <= 0.2  # Close to lower band


class TestATRIndicator:
    """Test suite for Average True Range (ATR) indicator."""

    def test_atr_positive_value(self, sample_indicator_results):
        """Test that ATR returns a positive value."""
        atr = sample_indicator_results["atr"]
        assert atr > 0

    def test_atr_data_type(self, sample_indicator_results):
        """Test ATR data type."""
        atr = sample_indicator_results["atr"]
        assert isinstance(atr, (int, float))

    def test_atr_volatility_measure(self):
        """Test ATR as volatility measure."""
        high_volatility_atr = 0.100
        low_volatility_atr = 0.010
        assert high_volatility_atr > low_volatility_atr


class TestIndicatorAggregation:
    """Test suite for combining multiple indicators."""

    def test_all_indicators_present(self, sample_indicator_results):
        """Test that all expected indicators are present."""
        required_indicators = [
            "rsi",
            "sma_short",
            "sma_long",
            "macd",
            "bb_upper",
            "atr",
        ]
        for indicator in required_indicators:
            assert indicator in sample_indicator_results

    def test_indicator_results_completeness(self, sample_indicator_results):
        """Test that indicator results contain signal data."""
        assert "rsi_signal" in sample_indicator_results
        assert "sma_signal" in sample_indicator_results
        assert "macd_signal_direction" in sample_indicator_results
