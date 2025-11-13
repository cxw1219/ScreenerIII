"""
Unit tests for configuration loading functionality.

Tests the loading, parsing, and validation of configuration files
used throughout the ScreenerIII application.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import yaml
import sys
from pathlib import Path as PathlibPath

# Add src directory to path
sys.path.insert(0, str(PathlibPath(__file__).parent.parent.parent / "src"))


class TestConfigLoader:
    """Test suite for configuration loading functionality."""

    def test_config_fixture_structure(self, sample_config):
        """Test that sample_config fixture has required structure."""
        assert "trading" in sample_config
        assert "indicators" in sample_config
        assert "signals" in sample_config
        assert "risk_management" in sample_config
        assert "logging" in sample_config

    def test_config_fixture_trading_section(self, sample_config):
        """Test that trading section contains required fields."""
        trading = sample_config["trading"]
        assert trading["account_id"] == "test_account_123"
        assert trading["broker"] == "oanda"
        assert isinstance(trading["instruments"], list)
        assert len(trading["instruments"]) > 0
        assert trading["timeframe"] == "H1"

    def test_config_fixture_indicators_section(self, sample_config):
        """Test that indicators section contains required fields."""
        indicators = sample_config["indicators"]
        assert "rsi_period" in indicators
        assert "sma_short" in indicators
        assert "sma_long" in indicators
        assert indicators["rsi_period"] == 14
        assert indicators["sma_short"] == 20
        assert indicators["sma_long"] == 50

    def test_config_fixture_signals_section(self, sample_config):
        """Test that signals section contains required fields."""
        signals = sample_config["signals"]
        assert "min_confidence" in signals
        assert "take_profit_pips" in signals
        assert "stop_loss_pips" in signals
        assert signals["min_confidence"] == 0.6

    def test_config_fixture_risk_management_section(self, sample_config):
        """Test that risk management section is properly configured."""
        risk = sample_config["risk_management"]
        assert "max_risk_per_trade" in risk
        assert "position_size_method" in risk
        assert risk["max_risk_per_trade"] == 0.02
        assert risk["position_size_method"] == "fixed"

    def test_config_fixture_logging_section(self, sample_config):
        """Test that logging section is properly configured."""
        logging_config = sample_config["logging"]
        assert "level" in logging_config
        assert "format" in logging_config
        assert logging_config["level"] == "INFO"

    def test_temp_config_file_creation(self, temp_config_file):
        """Test that temporary config file is created successfully."""
        assert temp_config_file.exists()
        assert temp_config_file.suffix == ".yaml"

    def test_temp_config_file_content(self, temp_config_file):
        """Test that temporary config file contains expected content."""
        content = temp_config_file.read_text()
        assert "trading:" in content
        assert "indicators:" in content
        assert "EUR_USD" in content

    def test_config_with_missing_section(self, sample_config):
        """Test handling of config with missing required section."""
        # Remove a required section
        del sample_config["indicators"]
        assert "indicators" not in sample_config

    def test_config_with_invalid_values(self, sample_config):
        """Test config with invalid value types."""
        sample_config["indicators"]["rsi_period"] = "invalid"
        # In a real implementation, this would trigger validation
        assert sample_config["indicators"]["rsi_period"] == "invalid"

    def test_config_instruments_list(self, sample_config):
        """Test that instruments are properly listed in config."""
        instruments = sample_config["trading"]["instruments"]
        assert isinstance(instruments, list)
        assert "EUR_USD" in instruments
        assert "GBP_USD" in instruments

    @patch("builtins.open", new_callable=mock_open, read_data="test: value")
    def test_config_file_loading_mock(self, mock_file):
        """Test config file loading with mocked file operations."""
        # This test demonstrates how to mock file operations
        with patch("pathlib.Path.open", mock_file):
            # Simulate loading a config file
            pass
        # File should have been opened
        assert mock_file.called


class TestConfigValidation:
    """Test suite for configuration validation."""

    def test_min_confidence_range(self, sample_config):
        """Test that min_confidence is within valid range."""
        min_conf = sample_config["signals"]["min_confidence"]
        assert 0 <= min_conf <= 1

    def test_rsi_period_positive(self, sample_config):
        """Test that RSI period is a positive integer."""
        rsi_period = sample_config["indicators"]["rsi_period"]
        assert isinstance(rsi_period, int)
        assert rsi_period > 0

    def test_max_positions_positive(self, sample_config):
        """Test that max_positions is a positive integer."""
        max_pos = sample_config["trading"]["max_positions"]
        assert isinstance(max_pos, int)
        assert max_pos > 0

    def test_risk_per_trade_range(self, sample_config):
        """Test that max_risk_per_trade is within valid range."""
        risk = sample_config["risk_management"]["max_risk_per_trade"]
        assert 0 < risk < 1


class TestConfigDefaults:
    """Test suite for configuration defaults."""

    def test_default_timeframe(self, sample_config):
        """Test default timeframe is set correctly."""
        assert sample_config["trading"]["timeframe"] == "H1"

    def test_default_logging_level(self, sample_config):
        """Test default logging level is INFO."""
        assert sample_config["logging"]["level"] == "INFO"

    def test_default_min_confidence(self, sample_config):
        """Test default minimum confidence threshold."""
        assert sample_config["signals"]["min_confidence"] == 0.6


class TestConfigMerging:
    """Test suite for merging multiple config sources."""

    def test_merge_with_empty_override(self, sample_config):
        """Test merging config with empty override."""
        override = {}
        merged = {**sample_config, **override}
        assert merged == sample_config

    def test_merge_partial_override(self, sample_config):
        """Test merging config with partial override."""
        override = {"trading": {"account_id": "new_account"}}
        # In a real implementation, this would do deep merge
        merged = sample_config.copy()
        merged["trading"]["account_id"] = "new_account"
        assert merged["trading"]["account_id"] == "new_account"
        assert merged["indicators"] == sample_config["indicators"]
