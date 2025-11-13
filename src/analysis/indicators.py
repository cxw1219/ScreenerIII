"""
Technical Indicators Module

This module provides comprehensive technical indicator calculations using TA-Lib and ta libraries.
Includes RSI, Moving Averages, Bollinger Bands, MACD, ATR, volume analysis, and trend detection.

Author: ScreenerIII
License: MIT
"""

from typing import Dict, Optional, Tuple, Union
import pandas as pd
import numpy as np
import logging

# Optional dependencies
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    logging.warning("TA-Lib not available. Will use fallback implementations.")

try:
    from ta import trend, volatility, momentum, volume
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False
    logging.warning("ta library not available. Will use fallback implementations.")

# Configure logging
logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """
    Comprehensive technical indicator calculations for financial time series data.

    This class provides methods for calculating various technical indicators used
    in trading and market analysis, including trend indicators, momentum oscillators,
    volatility measures, and volume-based indicators.
    """

    def __init__(self, data: pd.DataFrame):
        """
        Initialize TechnicalIndicators with price data.

        Args:
            data: DataFrame with OHLCV data (Open, High, Low, Close, Volume)
                  Required columns: 'open', 'high', 'low', 'close', 'volume'

        Raises:
            ValueError: If required columns are missing from data
        """
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]

        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        self.data = data.copy()
        logger.info(f"Initialized TechnicalIndicators with {len(self.data)} data points")

    def calculate_rsi(self, period: int = 14, column: str = 'close') -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).

        RSI is a momentum oscillator that measures the speed and magnitude of
        price changes. Values range from 0 to 100, with readings above 70
        indicating overbought conditions and below 30 indicating oversold conditions.

        Args:
            period: Lookback period for RSI calculation (default: 14)
            column: Column name to calculate RSI on (default: 'close')

        Returns:
            pd.Series: RSI values

        Raises:
            ValueError: If column doesn't exist or period is invalid
        """
        try:
            if column not in self.data.columns:
                raise ValueError(f"Column '{column}' not found in data")

            if period < 2:
                raise ValueError(f"Period must be >= 2, got {period}")

            rsi = talib.RSI(self.data[column].values, timeperiod=period)
            logger.debug(f"Calculated RSI with period {period}")
            return pd.Series(rsi, index=self.data.index, name=f'RSI_{period}')

        except Exception as e:
            logger.error(f"Error calculating RSI: {str(e)}")
            raise

    def calculate_moving_averages(self,
                                  periods: list = [20, 50, 200],
                                  ma_type: str = 'sma',
                                  column: str = 'close') -> Dict[str, pd.Series]:
        """
        Calculate multiple moving averages.

        Supports Simple Moving Average (SMA), Exponential Moving Average (EMA),
        and Weighted Moving Average (WMA).

        Args:
            periods: List of periods for moving average calculation
            ma_type: Type of moving average ('sma', 'ema', 'wma')
            column: Column name to calculate MA on (default: 'close')

        Returns:
            Dict[str, pd.Series]: Dictionary of moving average series

        Raises:
            ValueError: If ma_type is invalid or column doesn't exist
        """
        try:
            if column not in self.data.columns:
                raise ValueError(f"Column '{column}' not found in data")

            ma_type = ma_type.lower()
            valid_types = ['sma', 'ema', 'wma']

            if ma_type not in valid_types:
                raise ValueError(f"ma_type must be one of {valid_types}, got '{ma_type}'")

            moving_averages = {}

            for period in periods:
                if ma_type == 'sma':
                    ma = talib.SMA(self.data[column].values, timeperiod=period)
                    name = f'SMA_{period}'
                elif ma_type == 'ema':
                    ma = talib.EMA(self.data[column].values, timeperiod=period)
                    name = f'EMA_{period}'
                elif ma_type == 'wma':
                    ma = talib.WMA(self.data[column].values, timeperiod=period)
                    name = f'WMA_{period}'

                moving_averages[name] = pd.Series(ma, index=self.data.index, name=name)
                logger.debug(f"Calculated {name}")

            return moving_averages

        except Exception as e:
            logger.error(f"Error calculating moving averages: {str(e)}")
            raise

    def calculate_bollinger_bands(self,
                                  period: int = 20,
                                  std_dev: float = 2.0,
                                  column: str = 'close') -> Dict[str, pd.Series]:
        """
        Calculate Bollinger Bands.

        Bollinger Bands consist of a middle band (SMA) and upper/lower bands
        that are standard deviations away from the middle band. They measure
        volatility and provide relative price levels.

        Args:
            period: Period for middle band SMA (default: 20)
            std_dev: Number of standard deviations for bands (default: 2.0)
            column: Column name to calculate bands on (default: 'close')

        Returns:
            Dict[str, pd.Series]: Dictionary with 'upper', 'middle', 'lower' bands

        Raises:
            ValueError: If column doesn't exist or parameters are invalid
        """
        try:
            if column not in self.data.columns:
                raise ValueError(f"Column '{column}' not found in data")

            if period < 2:
                raise ValueError(f"Period must be >= 2, got {period}")

            if std_dev <= 0:
                raise ValueError(f"std_dev must be positive, got {std_dev}")

            upper, middle, lower = talib.BBANDS(
                self.data[column].values,
                timeperiod=period,
                nbdevup=std_dev,
                nbdevdn=std_dev,
                matype=0
            )

            logger.debug(f"Calculated Bollinger Bands (period={period}, std={std_dev})")

            return {
                'BB_upper': pd.Series(upper, index=self.data.index, name='BB_upper'),
                'BB_middle': pd.Series(middle, index=self.data.index, name='BB_middle'),
                'BB_lower': pd.Series(lower, index=self.data.index, name='BB_lower')
            }

        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {str(e)}")
            raise

    def calculate_macd(self,
                       fast_period: int = 12,
                       slow_period: int = 26,
                       signal_period: int = 9,
                       column: str = 'close') -> Dict[str, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence).

        MACD shows the relationship between two moving averages and is used
        to identify trend changes and momentum.

        Args:
            fast_period: Fast EMA period (default: 12)
            slow_period: Slow EMA period (default: 26)
            signal_period: Signal line period (default: 9)
            column: Column name to calculate MACD on (default: 'close')

        Returns:
            Dict[str, pd.Series]: Dictionary with 'macd', 'signal', 'histogram'

        Raises:
            ValueError: If column doesn't exist or parameters are invalid
        """
        try:
            if column not in self.data.columns:
                raise ValueError(f"Column '{column}' not found in data")

            if fast_period >= slow_period:
                raise ValueError("fast_period must be less than slow_period")

            macd_line, signal_line, histogram = talib.MACD(
                self.data[column].values,
                fastperiod=fast_period,
                slowperiod=slow_period,
                signalperiod=signal_period
            )

            logger.debug(f"Calculated MACD ({fast_period},{slow_period},{signal_period})")

            return {
                'MACD': pd.Series(macd_line, index=self.data.index, name='MACD'),
                'MACD_signal': pd.Series(signal_line, index=self.data.index, name='MACD_signal'),
                'MACD_histogram': pd.Series(histogram, index=self.data.index, name='MACD_histogram')
            }

        except Exception as e:
            logger.error(f"Error calculating MACD: {str(e)}")
            raise

    def calculate_atr(self, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range (ATR).

        ATR measures market volatility by decomposing the entire range of price
        movement for a given period. Higher ATR values indicate higher volatility.

        Args:
            period: Lookback period for ATR calculation (default: 14)

        Returns:
            pd.Series: ATR values

        Raises:
            ValueError: If period is invalid
        """
        try:
            if period < 1:
                raise ValueError(f"Period must be >= 1, got {period}")

            atr = talib.ATR(
                self.data['high'].values,
                self.data['low'].values,
                self.data['close'].values,
                timeperiod=period
            )

            logger.debug(f"Calculated ATR with period {period}")
            return pd.Series(atr, index=self.data.index, name=f'ATR_{period}')

        except Exception as e:
            logger.error(f"Error calculating ATR: {str(e)}")
            raise

    def calculate_stochastic(self,
                            fastk_period: int = 14,
                            slowk_period: int = 3,
                            slowd_period: int = 3) -> Dict[str, pd.Series]:
        """
        Calculate Stochastic Oscillator.

        The Stochastic Oscillator compares a closing price to its price range
        over a given period. Values range from 0 to 100.

        Args:
            fastk_period: Fast %K period (default: 14)
            slowk_period: Slow %K period (default: 3)
            slowd_period: Slow %D period (default: 3)

        Returns:
            Dict[str, pd.Series]: Dictionary with 'slowk' and 'slowd'

        Raises:
            ValueError: If parameters are invalid
        """
        try:
            slowk, slowd = talib.STOCH(
                self.data['high'].values,
                self.data['low'].values,
                self.data['close'].values,
                fastk_period=fastk_period,
                slowk_period=slowk_period,
                slowk_matype=0,
                slowd_period=slowd_period,
                slowd_matype=0
            )

            logger.debug(f"Calculated Stochastic ({fastk_period},{slowk_period},{slowd_period})")

            return {
                'STOCH_k': pd.Series(slowk, index=self.data.index, name='STOCH_k'),
                'STOCH_d': pd.Series(slowd, index=self.data.index, name='STOCH_d')
            }

        except Exception as e:
            logger.error(f"Error calculating Stochastic: {str(e)}")
            raise

    def calculate_adx(self, period: int = 14) -> Dict[str, pd.Series]:
        """
        Calculate Average Directional Index (ADX) and related indicators.

        ADX measures trend strength regardless of direction. Values above 25
        indicate a trending market, while below 20 indicate a ranging market.

        Args:
            period: Lookback period for ADX calculation (default: 14)

        Returns:
            Dict[str, pd.Series]: Dictionary with 'ADX', 'PLUS_DI', 'MINUS_DI'

        Raises:
            ValueError: If period is invalid
        """
        try:
            if period < 2:
                raise ValueError(f"Period must be >= 2, got {period}")

            adx = talib.ADX(
                self.data['high'].values,
                self.data['low'].values,
                self.data['close'].values,
                timeperiod=period
            )

            plus_di = talib.PLUS_DI(
                self.data['high'].values,
                self.data['low'].values,
                self.data['close'].values,
                timeperiod=period
            )

            minus_di = talib.MINUS_DI(
                self.data['high'].values,
                self.data['low'].values,
                self.data['close'].values,
                timeperiod=period
            )

            logger.debug(f"Calculated ADX with period {period}")

            return {
                'ADX': pd.Series(adx, index=self.data.index, name='ADX'),
                'PLUS_DI': pd.Series(plus_di, index=self.data.index, name='PLUS_DI'),
                'MINUS_DI': pd.Series(minus_di, index=self.data.index, name='MINUS_DI')
            }

        except Exception as e:
            logger.error(f"Error calculating ADX: {str(e)}")
            raise

    def calculate_volume_indicators(self) -> Dict[str, pd.Series]:
        """
        Calculate volume-based indicators.

        Includes On-Balance Volume (OBV), Volume Weighted Average Price (VWAP),
        and Accumulation/Distribution Line.

        Returns:
            Dict[str, pd.Series]: Dictionary of volume indicators

        Raises:
            Exception: If calculation fails
        """
        try:
            indicators = {}

            # On-Balance Volume
            obv = talib.OBV(self.data['close'].values, self.data['volume'].values)
            indicators['OBV'] = pd.Series(obv, index=self.data.index, name='OBV')

            # Accumulation/Distribution Line
            ad = talib.AD(
                self.data['high'].values,
                self.data['low'].values,
                self.data['close'].values,
                self.data['volume'].values
            )
            indicators['AD'] = pd.Series(ad, index=self.data.index, name='AD')

            # Volume Weighted Average Price (using ta library)
            try:
                vwap_indicator = volume.VolumeWeightedAveragePrice(
                    high=self.data['high'],
                    low=self.data['low'],
                    close=self.data['close'],
                    volume=self.data['volume']
                )
                indicators['VWAP'] = vwap_indicator.volume_weighted_average_price()
            except Exception as vwap_error:
                logger.warning(f"VWAP calculation failed: {vwap_error}")
                # Calculate VWAP manually
                typical_price = (self.data['high'] + self.data['low'] + self.data['close']) / 3
                indicators['VWAP'] = (typical_price * self.data['volume']).cumsum() / self.data['volume'].cumsum()

            # Volume Rate of Change
            volume_roc = talib.ROC(self.data['volume'].values, timeperiod=10)
            indicators['Volume_ROC'] = pd.Series(volume_roc, index=self.data.index, name='Volume_ROC')

            logger.debug("Calculated volume indicators")
            return indicators

        except Exception as e:
            logger.error(f"Error calculating volume indicators: {str(e)}")
            raise

    def detect_trend(self,
                     ma_short_period: int = 20,
                     ma_long_period: int = 50,
                     adx_threshold: float = 25.0) -> Dict[str, Union[str, float]]:
        """
        Detect current market trend using multiple indicators.

        Combines moving average crossovers and ADX to determine trend direction
        and strength.

        Args:
            ma_short_period: Period for short-term moving average (default: 20)
            ma_long_period: Period for long-term moving average (default: 50)
            adx_threshold: ADX threshold for trend confirmation (default: 25.0)

        Returns:
            Dict with 'direction' ('uptrend', 'downtrend', 'sideways'),
            'strength' (ADX value), and 'confidence' (0-100)

        Raises:
            ValueError: If insufficient data for calculation
        """
        try:
            if len(self.data) < max(ma_long_period, 14):
                raise ValueError(f"Insufficient data for trend detection. Need at least {max(ma_long_period, 14)} periods")

            # Calculate moving averages
            ma_short = talib.SMA(self.data['close'].values, timeperiod=ma_short_period)
            ma_long = talib.SMA(self.data['close'].values, timeperiod=ma_long_period)

            # Calculate ADX
            adx = talib.ADX(
                self.data['high'].values,
                self.data['low'].values,
                self.data['close'].values,
                timeperiod=14
            )

            # Get latest values
            latest_short_ma = ma_short[-1]
            latest_long_ma = ma_long[-1]
            latest_adx = adx[-1]
            latest_close = self.data['close'].iloc[-1]

            # Determine trend direction
            if np.isnan(latest_short_ma) or np.isnan(latest_long_ma) or np.isnan(latest_adx):
                return {
                    'direction': 'unknown',
                    'strength': 0.0,
                    'confidence': 0.0
                }

            # Trend logic
            if latest_short_ma > latest_long_ma and latest_close > latest_short_ma:
                direction = 'uptrend'
            elif latest_short_ma < latest_long_ma and latest_close < latest_short_ma:
                direction = 'downtrend'
            else:
                direction = 'sideways'

            # Calculate confidence based on ADX and MA separation
            ma_separation = abs(latest_short_ma - latest_long_ma) / latest_long_ma * 100
            adx_score = min(latest_adx / 50 * 100, 100)  # Normalize ADX to 0-100
            ma_score = min(ma_separation * 10, 100)  # Scale MA separation

            confidence = (adx_score * 0.6 + ma_score * 0.4)  # Weighted confidence

            logger.debug(f"Detected trend: {direction} (strength: {latest_adx:.2f}, confidence: {confidence:.2f})")

            return {
                'direction': direction,
                'strength': float(latest_adx),
                'confidence': float(confidence),
                'ma_short': float(latest_short_ma),
                'ma_long': float(latest_long_ma)
            }

        except Exception as e:
            logger.error(f"Error detecting trend: {str(e)}")
            raise

    def calculate_all_indicators(self) -> pd.DataFrame:
        """
        Calculate all available technical indicators and return as DataFrame.

        Returns:
            pd.DataFrame: Original data with all indicators added as columns

        Raises:
            Exception: If calculation fails
        """
        try:
            result = self.data.copy()

            # RSI
            result['RSI_14'] = self.calculate_rsi(14)

            # Moving Averages
            mas = self.calculate_moving_averages([20, 50, 200], 'sma')
            for name, series in mas.items():
                result[name] = series

            # EMAs
            emas = self.calculate_moving_averages([12, 26], 'ema')
            for name, series in emas.items():
                result[name] = series

            # Bollinger Bands
            bb = self.calculate_bollinger_bands()
            for name, series in bb.items():
                result[name] = series

            # MACD
            macd = self.calculate_macd()
            for name, series in macd.items():
                result[name] = series

            # ATR
            result['ATR_14'] = self.calculate_atr(14)

            # Stochastic
            stoch = self.calculate_stochastic()
            for name, series in stoch.items():
                result[name] = series

            # ADX
            adx = self.calculate_adx()
            for name, series in adx.items():
                result[name] = series

            # Volume indicators
            vol_indicators = self.calculate_volume_indicators()
            for name, series in vol_indicators.items():
                result[name] = series

            logger.info(f"Calculated all indicators. Result shape: {result.shape}")
            return result

        except Exception as e:
            logger.error(f"Error calculating all indicators: {str(e)}")
            raise


def calculate_pivot_points(data: pd.DataFrame,
                          method: str = 'standard') -> Dict[str, float]:
    """
    Calculate pivot points for support and resistance levels.

    Args:
        data: DataFrame with OHLC data
        method: Pivot point calculation method ('standard', 'fibonacci', 'camarilla')

    Returns:
        Dict with pivot point levels (P, R1, R2, R3, S1, S2, S3)

    Raises:
        ValueError: If method is invalid or data is insufficient
    """
    try:
        if len(data) < 1:
            raise ValueError("Insufficient data for pivot point calculation")

        high = data['high'].iloc[-1]
        low = data['low'].iloc[-1]
        close = data['close'].iloc[-1]

        pivot = (high + low + close) / 3

        if method == 'standard':
            r1 = 2 * pivot - low
            r2 = pivot + (high - low)
            r3 = high + 2 * (pivot - low)
            s1 = 2 * pivot - high
            s2 = pivot - (high - low)
            s3 = low - 2 * (high - pivot)

        elif method == 'fibonacci':
            r1 = pivot + 0.382 * (high - low)
            r2 = pivot + 0.618 * (high - low)
            r3 = pivot + 1.000 * (high - low)
            s1 = pivot - 0.382 * (high - low)
            s2 = pivot - 0.618 * (high - low)
            s3 = pivot - 1.000 * (high - low)

        elif method == 'camarilla':
            r1 = close + (high - low) * 1.1 / 12
            r2 = close + (high - low) * 1.1 / 6
            r3 = close + (high - low) * 1.1 / 4
            s1 = close - (high - low) * 1.1 / 12
            s2 = close - (high - low) * 1.1 / 6
            s3 = close - (high - low) * 1.1 / 4

        else:
            raise ValueError(f"Invalid method: {method}. Choose from 'standard', 'fibonacci', 'camarilla'")

        logger.debug(f"Calculated {method} pivot points")

        return {
            'pivot': float(pivot),
            'R1': float(r1),
            'R2': float(r2),
            'R3': float(r3),
            'S1': float(s1),
            'S2': float(s2),
            'S3': float(s3)
        }

    except Exception as e:
        logger.error(f"Error calculating pivot points: {str(e)}")
        raise


def calculate_fibonacci_levels(high: float,
                               low: float,
                               direction: str = 'uptrend') -> Dict[str, float]:
    """
    Calculate Fibonacci retracement levels.

    Args:
        high: High price for the range
        low: Low price for the range
        direction: Trend direction ('uptrend' or 'downtrend')

    Returns:
        Dict with Fibonacci levels (0%, 23.6%, 38.2%, 50%, 61.8%, 78.6%, 100%)

    Raises:
        ValueError: If high <= low or invalid direction
    """
    try:
        if high <= low:
            raise ValueError(f"High ({high}) must be greater than low ({low})")

        if direction not in ['uptrend', 'downtrend']:
            raise ValueError(f"Direction must be 'uptrend' or 'downtrend', got '{direction}'")

        diff = high - low

        levels = {
            '0.0': high if direction == 'uptrend' else low,
            '23.6': high - 0.236 * diff if direction == 'uptrend' else low + 0.236 * diff,
            '38.2': high - 0.382 * diff if direction == 'uptrend' else low + 0.382 * diff,
            '50.0': high - 0.500 * diff if direction == 'uptrend' else low + 0.500 * diff,
            '61.8': high - 0.618 * diff if direction == 'uptrend' else low + 0.618 * diff,
            '78.6': high - 0.786 * diff if direction == 'uptrend' else low + 0.786 * diff,
            '100.0': low if direction == 'uptrend' else high
        }

        logger.debug(f"Calculated Fibonacci levels for {direction}")
        return {k: float(v) for k, v in levels.items()}

    except Exception as e:
        logger.error(f"Error calculating Fibonacci levels: {str(e)}")
        raise
