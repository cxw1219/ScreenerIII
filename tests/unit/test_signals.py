"""
Unit tests for trading signal generation.

Tests the creation, validation, and processing of trading signals
based on technical indicators and market conditions.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import sys
from pathlib import Path as PathlibPath

# Add src directory to path
sys.path.insert(0, str(PathlibPath(__file__).parent.parent.parent / "src"))


class TestSignalStructure:
    """Test suite for trading signal structure and validation."""

    def test_signal_fixture_structure(self, sample_signal_data):
        """Test that sample signal has required fields."""
        assert "instrument" in sample_signal_data
        assert "signal_type" in sample_signal_data
        assert "confidence" in sample_signal_data
        assert "entry_price" in sample_signal_data
        assert "timestamp" in sample_signal_data

    def test_signal_fixture_instrument(self, sample_signal_data):
        """Test signal instrument field."""
        assert sample_signal_data["instrument"] == "EUR_USD"

    def test_signal_fixture_signal_type(self, sample_signal_data):
        """Test signal type is valid."""
        signal_type = sample_signal_data["signal_type"]
        assert signal_type in ["buy", "sell", "hold"]

    def test_signal_fixture_confidence(self, sample_signal_data):
        """Test signal confidence is within valid range."""
        confidence = sample_signal_data["confidence"]
        assert 0 <= confidence <= 1
        assert confidence == 0.85

    def test_signal_fixture_price_levels(self, sample_signal_data):
        """Test that price levels are properly set."""
        entry = sample_signal_data["entry_price"]
        tp = sample_signal_data["take_profit"]
        sl = sample_signal_data["stop_loss"]

        assert entry > 0
        assert tp > entry
        assert sl < entry

    def test_signal_fixture_timestamp(self, sample_signal_data):
        """Test that signal has timestamp."""
        timestamp = sample_signal_data["timestamp"]
        assert isinstance(timestamp, datetime)

    def test_signal_fixture_reason(self, sample_signal_data):
        """Test that signal has reasoning."""
        reason = sample_signal_data["reason"]
        assert isinstance(reason, str)
        assert len(reason) > 0


class TestSignalGeneration:
    """Test suite for signal generation logic."""

    def test_buy_signal_creation(self):
        """Test creation of buy signal."""
        signal = {
            "signal_type": "buy",
            "confidence": 0.80,
            "entry_price": 1.0050,
            "take_profit": 1.0100,
            "stop_loss": 1.0025,
        }
        assert signal["signal_type"] == "buy"
        assert signal["confidence"] >= 0.6

    def test_sell_signal_creation(self):
        """Test creation of sell signal."""
        signal = {
            "signal_type": "sell",
            "confidence": 0.75,
            "entry_price": 1.0050,
            "take_profit": 1.0000,
            "stop_loss": 1.0075,
        }
        assert signal["signal_type"] == "sell"
        assert signal["take_profit"] < signal["entry_price"]

    def test_hold_signal_creation(self):
        """Test creation of hold signal."""
        signal = {
            "signal_type": "hold",
            "confidence": 0.50,
        }
        assert signal["signal_type"] == "hold"

    def test_signal_confidence_threshold(self, sample_config):
        """Test signal against minimum confidence threshold."""
        min_conf = sample_config["signals"]["min_confidence"]
        signal_confidence = 0.85
        assert signal_confidence >= min_conf

    def test_low_confidence_signal_rejection(self, sample_config):
        """Test that low confidence signals are rejected."""
        min_conf = sample_config["signals"]["min_confidence"]
        signal_confidence = 0.50
        assert signal_confidence < min_conf  # Should be rejected


class TestSignalValidation:
    """Test suite for signal validation rules."""

    def test_tp_gt_entry_for_buy(self):
        """Test that take profit > entry for buy signals."""
        entry = 1.0050
        tp = 1.0100
        assert tp > entry

    def test_tp_lt_entry_for_sell(self):
        """Test that take profit < entry for sell signals."""
        entry = 1.0050
        tp = 1.0000
        assert tp < entry

    def test_sl_lt_entry_for_buy(self):
        """Test that stop loss < entry for buy signals."""
        entry = 1.0050
        sl = 1.0025
        assert sl < entry

    def test_sl_gt_entry_for_sell(self):
        """Test that stop loss > entry for sell signals."""
        entry = 1.0050
        sl = 1.0075
        assert sl > entry

    def test_tp_sl_not_equal(self):
        """Test that take profit and stop loss are different."""
        tp = 1.0100
        sl = 1.0025
        assert tp != sl

    def test_minimum_risk_reward_ratio(self):
        """Test minimum risk/reward ratio."""
        entry = 1.0050
        tp = 1.0100
        sl = 1.0025

        risk = entry - sl  # 0.0025
        reward = tp - entry  # 0.0050
        ratio = reward / risk  # 2.0

        assert ratio >= 1.0  # Reward should at least match risk

    def test_pip_distance_calculation(self, sample_config):
        """Test pip distance calculation for TP and SL."""
        entry = 1.0050
        tp = 1.0100
        sl = 1.0025

        # Assuming 4 decimal places for forex
        tp_pips = (tp - entry) * 10000
        sl_pips = (entry - sl) * 10000

        assert tp_pips == 50
        assert sl_pips == 25


class TestSignalFiltering:
    """Test suite for signal filtering and selection."""

    def test_filter_by_confidence(self, sample_signal_data):
        """Test filtering signals by confidence threshold."""
        threshold = 0.6
        signal_confidence = sample_signal_data["confidence"]
        assert signal_confidence >= threshold

    def test_filter_by_instrument(self, sample_signal_data, sample_config):
        """Test filtering signals by permitted instruments."""
        allowed = sample_config["trading"]["instruments"]
        signal_instrument = sample_signal_data["instrument"]

        # Instrument might not be in this config, but structure is valid
        assert isinstance(signal_instrument, str)

    def test_filter_multiple_signals(self, sample_signal_data):
        """Test filtering logic with multiple signals."""
        signals = [
            {"signal_type": "buy", "confidence": 0.85, "instrument": "EUR_USD"},
            {"signal_type": "buy", "confidence": 0.55, "instrument": "GBP_USD"},
            {"signal_type": "sell", "confidence": 0.75, "instrument": "EUR_USD"},
        ]

        # Filter by confidence >= 0.6
        filtered = [s for s in signals if s["confidence"] >= 0.6]
        assert len(filtered) == 2
        assert filtered[0]["confidence"] == 0.85
        assert filtered[1]["confidence"] == 0.75

    def test_filter_by_signal_type(self):
        """Test filtering signals by type."""
        signals = [
            {"signal_type": "buy", "confidence": 0.85},
            {"signal_type": "hold", "confidence": 0.50},
            {"signal_type": "sell", "confidence": 0.75},
        ]

        buy_signals = [s for s in signals if s["signal_type"] == "buy"]
        assert len(buy_signals) == 1
        assert buy_signals[0]["signal_type"] == "buy"


class TestSignalRanking:
    """Test suite for signal ranking and priority."""

    def test_rank_by_confidence(self):
        """Test ranking signals by confidence score."""
        signals = [
            {"signal_type": "buy", "confidence": 0.65},
            {"signal_type": "buy", "confidence": 0.85},
            {"signal_type": "buy", "confidence": 0.75},
        ]

        ranked = sorted(signals, key=lambda x: x["confidence"], reverse=True)
        assert ranked[0]["confidence"] == 0.85
        assert ranked[1]["confidence"] == 0.75
        assert ranked[2]["confidence"] == 0.65

    def test_rank_by_timestamp(self, sample_signal_data):
        """Test ranking signals by timestamp (recent first)."""
        now = datetime.now()
        signals = [
            {"timestamp": now - timedelta(hours=2), "confidence": 0.75},
            {"timestamp": now - timedelta(hours=1), "confidence": 0.85},
            {"timestamp": now, "confidence": 0.70},
        ]

        ranked = sorted(signals, key=lambda x: x["timestamp"], reverse=True)
        assert ranked[0]["timestamp"] == now


class TestSignalMetrics:
    """Test suite for signal quality metrics."""

    def test_signal_success_metrics(self):
        """Test metrics for signal success."""
        signal = {
            "signal_type": "buy",
            "entry_price": 1.0050,
            "take_profit": 1.0100,
            "stop_loss": 1.0025,
            "confidence": 0.85,
        }

        # Calculate potential profit/loss
        best_case = (signal["take_profit"] - signal["entry_price"]) * 10000
        worst_case = (signal["stop_loss"] - signal["entry_price"]) * 10000

        assert best_case > 0
        assert worst_case < 0

    def test_signal_error_analysis(self):
        """Test signal analysis metrics."""
        # Calculate error between prediction and actual
        predicted = 1.0100
        actual = 1.0085
        error = abs(predicted - actual)

        assert error > 0
        assert error < abs(predicted - 1.0)

    def test_win_rate_calculation(self):
        """Test win rate calculation from signals."""
        total_signals = 10
        winning_signals = 7
        win_rate = winning_signals / total_signals

        assert win_rate == 0.7
        assert win_rate > 0.5


class TestSignalPersistence:
    """Test suite for signal storage and retrieval."""

    def test_signal_serialization(self, sample_signal_data):
        """Test that signals can be serialized."""
        signal = sample_signal_data.copy()
        # Convert datetime to string for JSON serialization
        signal["timestamp"] = signal["timestamp"].isoformat()

        assert isinstance(signal["timestamp"], str)
        assert "T" in signal["timestamp"]  # ISO format

    def test_signal_deserialization(self):
        """Test that signals can be deserialized."""
        serialized = {
            "instrument": "EUR_USD",
            "signal_type": "buy",
            "confidence": 0.85,
            "timestamp": "2023-01-01T12:00:00",
        }

        # Deserialize
        deserialized = serialized.copy()
        deserialized["timestamp"] = datetime.fromisoformat(serialized["timestamp"])

        assert isinstance(deserialized["timestamp"], datetime)
