"""
Sample market data fixtures for testing.

This module provides various market data samples and utilities
for use in unit and integration tests throughout ScreenerIII.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple


def create_sample_ohlcv_data(
    start_date: str = "2023-01-01",
    periods: int = 100,
    frequency: str = "1H",
    base_price: float = 1.0,
    volatility: float = 0.01,
    trend: str = "neutral",
) -> pd.DataFrame:
    """
    Create sample OHLCV data for testing.

    Args:
        start_date: Starting date for the data
        periods: Number of candles to generate
        frequency: Frequency of candles (e.g., '1H', 'D', 'M5')
        base_price: Starting price for the data
        volatility: Price volatility (standard deviation)
        trend: 'bullish', 'bearish', or 'neutral'

    Returns:
        DataFrame with columns: time, open, high, low, close, volume
    """
    dates = pd.date_range(start=start_date, periods=periods, freq=frequency)

    # Generate price movement based on trend
    if trend == "bullish":
        drift = 0.0001
    elif trend == "bearish":
        drift = -0.0001
    else:
        drift = 0.0

    # Generate log returns
    returns = np.random.normal(drift, volatility, periods)
    prices = base_price * np.exp(np.cumsum(returns))

    # Create OHLCV data
    data = {
        "time": dates,
        "open": prices,
        "high": prices + np.abs(np.random.normal(0, volatility / 2, periods)),
        "low": prices - np.abs(np.random.normal(0, volatility / 2, periods)),
        "close": prices + np.random.normal(0, volatility / 4, periods),
        "volume": np.random.uniform(1000, 10000, periods),
    }

    df = pd.DataFrame(data)

    # Ensure OHLC integrity
    for i in range(len(df)):
        high = max(df.loc[i, "open"], df.loc[i, "high"], df.loc[i, "close"])
        low = min(df.loc[i, "open"], df.loc[i, "low"], df.loc[i, "close"])
        df.at[i, "high"] = high
        df.at[i, "low"] = low

    return df


def create_sample_candle(
    time: datetime = None,
    open_price: float = 1.0,
    high_price: float = 1.01,
    low_price: float = 0.99,
    close_price: float = 1.005,
    volume: float = 1000,
) -> Dict:
    """
    Create a single sample candle (OHLCV bar).

    Args:
        time: Candle timestamp
        open_price: Opening price
        high_price: Highest price
        low_price: Lowest price
        close_price: Closing price
        volume: Trading volume

    Returns:
        Dictionary representing a single candle
    """
    if time is None:
        time = datetime.now()

    return {
        "time": time.isoformat(),
        "bid": {
            "o": f"{open_price:.4f}",
            "h": f"{high_price:.4f}",
            "l": f"{low_price:.4f}",
            "c": f"{close_price:.4f}",
        },
        "ask": {
            "o": f"{open_price + 0.0001:.4f}",
            "h": f"{high_price + 0.0001:.4f}",
            "l": f"{low_price + 0.0001:.4f}",
            "c": f"{close_price + 0.0001:.4f}",
        },
        "volume": volume,
        "complete": True,
    }


def create_bullish_candles(count: int = 10) -> List[Dict]:
    """
    Create a series of bullish candles (increasing prices).

    Args:
        count: Number of candles to generate

    Returns:
        List of candle dictionaries
    """
    candles = []
    current_price = 1.0
    current_time = datetime.now()

    for i in range(count):
        open_p = current_price
        close_p = current_price + 0.001
        high_p = close_p + 0.0005
        low_p = open_p

        candles.append(
            create_sample_candle(
                time=current_time + timedelta(hours=i),
                open_price=open_p,
                high_price=high_p,
                low_price=low_p,
                close_price=close_p,
            )
        )

        current_price = close_p

    return candles


def create_bearish_candles(count: int = 10) -> List[Dict]:
    """
    Create a series of bearish candles (decreasing prices).

    Args:
        count: Number of candles to generate

    Returns:
        List of candle dictionaries
    """
    candles = []
    current_price = 1.0
    current_time = datetime.now()

    for i in range(count):
        open_p = current_price
        close_p = current_price - 0.001
        high_p = open_p
        low_p = close_p - 0.0005

        candles.append(
            create_sample_candle(
                time=current_time + timedelta(hours=i),
                open_price=open_p,
                high_price=high_p,
                low_price=low_p,
                close_price=close_p,
            )
        )

        current_price = close_p

    return candles


def create_volatile_candles(count: int = 10) -> List[Dict]:
    """
    Create candles with high volatility.

    Args:
        count: Number of candles to generate

    Returns:
        List of candle dictionaries with high volatility
    """
    candles = []
    current_price = 1.0
    current_time = datetime.now()

    for i in range(count):
        price_change = np.random.uniform(-0.005, 0.005)
        open_p = current_price
        close_p = current_price + price_change
        high_p = max(open_p, close_p) + abs(np.random.uniform(0, 0.003))
        low_p = min(open_p, close_p) - abs(np.random.uniform(0, 0.003))

        candles.append(
            create_sample_candle(
                time=current_time + timedelta(hours=i),
                open_price=open_p,
                high_price=high_p,
                low_price=low_p,
                close_price=close_p,
            )
        )

        current_price = close_p

    return candles


def create_rsi_overbought_data() -> pd.DataFrame:
    """
    Create sample data with RSI in overbought territory (>70).

    Returns:
        DataFrame with prices that generate RSI > 70
    """
    # Create uptrend to generate overbought RSI
    base_prices = np.linspace(1.0, 1.05, 50)
    prices = base_prices + np.random.normal(0, 0.0005, 50)

    dates = pd.date_range(start="2023-01-01", periods=50, freq="1H")

    return pd.DataFrame({
        "time": dates,
        "open": prices,
        "high": prices + 0.001,
        "low": prices - 0.001,
        "close": prices + np.random.normal(0, 0.0003, 50),
        "volume": np.random.uniform(1000, 10000, 50),
    })


def create_rsi_oversold_data() -> pd.DataFrame:
    """
    Create sample data with RSI in oversold territory (<30).

    Returns:
        DataFrame with prices that generate RSI < 30
    """
    # Create downtrend to generate oversold RSI
    base_prices = np.linspace(1.05, 1.0, 50)
    prices = base_prices + np.random.normal(0, 0.0005, 50)

    dates = pd.date_range(start="2023-01-01", periods=50, freq="1H")

    return pd.DataFrame({
        "time": dates,
        "open": prices,
        "high": prices + 0.001,
        "low": prices - 0.001,
        "close": prices + np.random.normal(0, 0.0003, 50),
        "volume": np.random.uniform(1000, 10000, 50),
    })


def create_golden_cross_data() -> pd.DataFrame:
    """
    Create sample data with golden cross (SMA 20 crossing above SMA 50).

    Returns:
        DataFrame with data showing golden cross pattern
    """
    dates = pd.date_range(start="2023-01-01", periods=100, freq="1D")

    # Create uptrend with crossover around day 50
    prices = []
    for i in range(100):
        if i < 50:
            price = 1.0 + i * 0.001 + np.random.normal(0, 0.005)
        else:
            price = 1.05 + (i - 50) * 0.0005 + np.random.normal(0, 0.005)
        prices.append(price)

    prices = np.array(prices)

    return pd.DataFrame({
        "time": dates,
        "open": prices,
        "high": prices + 0.01,
        "low": prices - 0.01,
        "close": prices,
        "volume": np.random.uniform(1000, 10000, 100),
    })


def create_death_cross_data() -> pd.DataFrame:
    """
    Create sample data with death cross (SMA 20 crossing below SMA 50).

    Returns:
        DataFrame with data showing death cross pattern
    """
    dates = pd.date_range(start="2023-01-01", periods=100, freq="1D")

    # Create downtrend with crossover around day 50
    prices = []
    for i in range(100):
        if i < 50:
            price = 1.05 - i * 0.001 + np.random.normal(0, 0.005)
        else:
            price = 1.0 - (i - 50) * 0.0005 + np.random.normal(0, 0.005)
        prices.append(price)

    prices = np.array(prices)

    return pd.DataFrame({
        "time": dates,
        "open": prices,
        "high": prices + 0.01,
        "low": prices - 0.01,
        "close": prices,
        "volume": np.random.uniform(1000, 10000, 100),
    })


def create_macd_bullish_divergence() -> pd.DataFrame:
    """
    Create sample data with MACD bullish divergence pattern.

    Returns:
        DataFrame with MACD bullish divergence setup
    """
    dates = pd.date_range(start="2023-01-01", periods=100, freq="1D")

    # Create data with lower lows but MACD making higher lows
    prices = []
    for i in range(100):
        # Prices making lower lows
        base = 1.0 - (i // 20) * 0.01
        price = base - (i % 20) * 0.0005 + np.random.normal(0, 0.005)
        prices.append(price)

    prices = np.array(prices)

    return pd.DataFrame({
        "time": dates,
        "open": prices,
        "high": prices + 0.01,
        "low": prices - 0.01,
        "close": prices,
        "volume": np.random.uniform(1000, 10000, 100),
    })


def create_multiinstrument_data() -> Dict[str, pd.DataFrame]:
    """
    Create sample data for multiple instruments.

    Returns:
        Dictionary mapping instrument names to their DataFrames
    """
    instruments = {
        "EUR_USD": create_sample_ohlcv_data(base_price=1.05, trend="bullish"),
        "GBP_USD": create_sample_ohlcv_data(base_price=1.25, trend="neutral"),
        "USD_JPY": create_sample_ohlcv_data(base_price=130.0, trend="bearish"),
    }

    return instruments


def create_market_microstructure_data() -> pd.DataFrame:
    """
    Create sample data with realistic bid-ask spreads.

    Returns:
        DataFrame with separate bid and ask prices
    """
    dates = pd.date_range(start="2023-01-01", periods=100, freq="1H")
    mid_prices = np.linspace(1.0, 1.02, 100) + np.random.normal(0, 0.001, 100)

    return pd.DataFrame({
        "time": dates,
        "bid_open": mid_prices - 0.00005,
        "bid_high": mid_prices + 0.005 - 0.00005,
        "bid_low": mid_prices - 0.005 - 0.00005,
        "bid_close": mid_prices - 0.00005,
        "ask_open": mid_prices + 0.00005,
        "ask_high": mid_prices + 0.005 + 0.00005,
        "ask_low": mid_prices - 0.005 + 0.00005,
        "ask_close": mid_prices + 0.00005,
        "volume": np.random.uniform(1000, 10000, 100),
    })


# Sample candle sequences for common patterns
SAMPLE_BULLISH_ENGULFING = [
    create_sample_candle(close_price=1.000),  # Small red candle
    create_sample_candle(
        open_price=0.998,
        close_price=1.002,
        high_price=1.003,
        low_price=0.997,
    ),  # Large green candle
]

SAMPLE_BEARISH_ENGULFING = [
    create_sample_candle(
        open_price=1.000,
        close_price=1.002,
        high_price=1.003,
        low_price=0.999,
    ),  # Small green candle
    create_sample_candle(
        open_price=1.002,
        close_price=0.998,
        high_price=1.001,
        low_price=0.997,
    ),  # Large red candle
]

SAMPLE_HAMMER = [
    create_sample_candle(
        open_price=1.005,
        close_price=1.004,
        high_price=1.006,
        low_price=0.995,
    ),  # Hammer pattern: long lower wick, small body
]

SAMPLE_SHOOTING_STAR = [
    create_sample_candle(
        open_price=1.005,
        close_price=1.004,
        high_price=1.015,
        low_price=1.003,
    ),  # Shooting star: long upper wick, small body
]
