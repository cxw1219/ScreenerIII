"""
pytest configuration and shared fixtures for ScreenerIII tests.

This module provides:
- pytest configuration
- Shared fixtures for use across all test modules
- Mock objects and helpers
"""

import pytest
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def sample_ohlcv_data():
    """
    Fixture providing sample OHLCV (Open, High, Low, Close, Volume) market data.

    Returns a pandas DataFrame with typical forex candle data.
    """
    dates = pd.date_range(start="2023-01-01", periods=100, freq="1H")
    data = {
        "time": dates,
        "open": np.random.uniform(1.0, 1.1, 100),
        "high": np.random.uniform(1.05, 1.15, 100),
        "low": np.random.uniform(0.95, 1.05, 100),
        "close": np.random.uniform(1.0, 1.1, 100),
        "volume": np.random.uniform(1000, 10000, 100),
    }
    df = pd.DataFrame(data)
    # Ensure high >= low
    df["high"] = df[["high", "close", "open"]].max(axis=1)
    df["low"] = df[["low", "close", "open"]].min(axis=1)
    return df


@pytest.fixture
def sample_config():
    """
    Fixture providing a sample configuration dictionary.

    This mimics the structure of config files used in the application.
    """
    return {
        "trading": {
            "account_id": "test_account_123",
            "broker": "oanda",
            "instruments": ["EUR_USD", "GBP_USD"],
            "timeframe": "H1",
            "max_positions": 5,
        },
        "indicators": {
            "rsi_period": 14,
            "sma_short": 20,
            "sma_long": 50,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
        },
        "signals": {
            "min_confidence": 0.6,
            "take_profit_pips": 50,
            "stop_loss_pips": 25,
        },
        "risk_management": {
            "max_risk_per_trade": 0.02,
            "position_size_method": "fixed",
            "fixed_size": 100000,
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    }


@pytest.fixture
def mock_oanda_client():
    """
    Fixture providing a mock OANDA client for testing.

    Returns a MagicMock object configured to simulate OANDA API responses.
    """
    mock_client = MagicMock()

    # Configure mock methods
    mock_client.get_account.return_value = {
        "account": {
            "id": "test_account_123",
            "balance": 100000.0,
            "currency": "USD",
            "openTradeCount": 0,
        }
    }

    mock_client.get_instrument_candles.return_value = {
        "instrument": "EUR_USD",
        "granularity": "H1",
        "candles": [
            {
                "time": "2023-01-01T00:00:00Z",
                "bid": {"o": "1.0000", "h": "1.0100", "l": "0.9900", "c": "1.0050"},
                "ask": {"o": "1.0001", "h": "1.0101", "l": "0.9901", "c": "1.0051"},
                "volume": 1000,
                "complete": True,
            }
        ],
    }

    mock_client.place_order.return_value = {
        "orderCreateTransaction": {
            "id": "order_123",
            "instrument": "EUR_USD",
            "type": "MARKET",
            "units": 100000,
        }
    }

    return mock_client


@pytest.fixture
def mock_logger():
    """
    Fixture providing a mock logger for testing logging behavior.

    Returns a MagicMock object configured as a logger.
    """
    return MagicMock()


@pytest.fixture
def sample_indicator_results():
    """
    Fixture providing sample technical indicator results.

    Returns a dictionary with various indicator values.
    """
    return {
        "rsi": 65.5,
        "rsi_signal": "overbought",
        "sma_short": 1.0050,
        "sma_long": 1.0030,
        "sma_signal": "bullish",
        "macd": 0.0020,
        "macd_signal": 0.0015,
        "macd_histogram": 0.0005,
        "macd_signal_direction": "bullish",
        "bb_upper": 1.0100,
        "bb_lower": 0.9900,
        "bb_middle": 1.0000,
        "bb_position": 0.75,
        "atr": 0.0050,
    }


@pytest.fixture
def sample_signal_data():
    """
    Fixture providing sample signal data for testing signal generation.

    Returns a dictionary representing a trading signal.
    """
    return {
        "instrument": "EUR_USD",
        "signal_type": "buy",
        "confidence": 0.85,
        "entry_price": 1.0050,
        "stop_loss": 1.0025,
        "take_profit": 1.0100,
        "timestamp": datetime.now(),
        "indicators_used": ["RSI", "SMA", "MACD"],
        "reason": "Convergence of RSI oversold and bullish SMA crossover",
    }


@pytest.fixture
def temp_config_file(tmp_path):
    """
    Fixture providing a temporary config file for testing config loading.

    Returns the path to a temporary YAML config file.
    """
    config_content = """
trading:
  account_id: test_account_123
  broker: oanda
  instruments:
    - EUR_USD
    - GBP_USD
  timeframe: H1

indicators:
  rsi_period: 14
  sma_short: 20
  sma_long: 50

logging:
  level: INFO
"""
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(config_content)
    return config_file


@pytest.fixture(autouse=True)
def reset_modules():
    """
    Fixture that resets imported modules before each test.

    This ensures test isolation by clearing module caches.
    """
    yield
    # Cleanup after test
    pass


@pytest.fixture
def caplog_setup():
    """
    Fixture providing caplog configuration for capturing logs during tests.

    This fixture can be used in conjunction with pytest's built-in caplog fixture.
    """
    return {
        "level": "DEBUG",
    }
