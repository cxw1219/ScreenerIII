"""
Pattern Recognition Module

This module provides comprehensive pattern recognition for technical analysis,
including candlestick patterns, chart patterns, and support/resistance levels.

Author: ScreenerIII
License: MIT
"""

from typing import Dict, List, Optional, Tuple, Union
import pandas as pd
import numpy as np
import logging

# Optional dependencies
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    logging.warning("TA-Lib not available. Candlestick patterns will be limited.")

try:
    from scipy.signal import argrelextrema
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logging.warning("SciPy not available. Some pattern detection will be limited.")

# Configure logging
logger = logging.getLogger(__name__)


class PatternRecognition:
    """
    Comprehensive pattern recognition for technical analysis.

    This class provides methods for detecting candlestick patterns, chart patterns,
    and identifying support/resistance levels.
    """

    def __init__(self, data: pd.DataFrame):
        """
        Initialize PatternRecognition with price data.

        Args:
            data: DataFrame with OHLCV data (Open, High, Low, Close, Volume)
                  Required columns: 'open', 'high', 'low', 'close', 'volume'

        Raises:
            ValueError: If required columns are missing from data
        """
        required_columns = ['open', 'high', 'low', 'close']
        missing_columns = [col for col in required_columns if col not in data.columns]

        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        self.data = data.copy()
        logger.info(f"Initialized PatternRecognition with {len(self.data)} data points")

    def detect_candlestick_patterns(self) -> Dict[str, pd.Series]:
        """
        Detect common candlestick patterns using TA-Lib.

        Returns bullish and bearish patterns with their locations in the data.
        Pattern values: 100 (bullish), -100 (bearish), 0 (no pattern)

        Returns:
            Dict[str, pd.Series]: Dictionary of candlestick pattern series

        Raises:
            Exception: If pattern detection fails
        """
        try:
            patterns = {}

            # Extract OHLC data
            open_prices = self.data['open'].values
            high_prices = self.data['high'].values
            low_prices = self.data['low'].values
            close_prices = self.data['close'].values

            # Reversal patterns
            patterns['Hammer'] = pd.Series(
                talib.CDLHAMMER(open_prices, high_prices, low_prices, close_prices),
                index=self.data.index, name='Hammer'
            )

            patterns['Hanging_Man'] = pd.Series(
                talib.CDLHANGINGMAN(open_prices, high_prices, low_prices, close_prices),
                index=self.data.index, name='Hanging_Man'
            )

            patterns['Shooting_Star'] = pd.Series(
                talib.CDLSHOOTINGSTAR(open_prices, high_prices, low_prices, close_prices),
                index=self.data.index, name='Shooting_Star'
            )

            patterns['Inverted_Hammer'] = pd.Series(
                talib.CDLINVERTEDHAMMER(open_prices, high_prices, low_prices, close_prices),
                index=self.data.index, name='Inverted_Hammer'
            )

            patterns['Engulfing'] = pd.Series(
                talib.CDLENGULFING(open_prices, high_prices, low_prices, close_prices),
                index=self.data.index, name='Engulfing'
            )

            patterns['Harami'] = pd.Series(
                talib.CDLHARAMI(open_prices, high_prices, low_prices, close_prices),
                index=self.data.index, name='Harami'
            )

            patterns['Piercing'] = pd.Series(
                talib.CDLPIERCING(open_prices, high_prices, low_prices, close_prices),
                index=self.data.index, name='Piercing'
            )

            patterns['Dark_Cloud_Cover'] = pd.Series(
                talib.CDLDARKCLOUDCOVER(open_prices, high_prices, low_prices, close_prices),
                index=self.data.index, name='Dark_Cloud_Cover'
            )

            patterns['Morning_Star'] = pd.Series(
                talib.CDLMORNINGSTAR(open_prices, high_prices, low_prices, close_prices),
                index=self.data.index, name='Morning_Star'
            )

            patterns['Evening_Star'] = pd.Series(
                talib.CDLEVENINGSTAR(open_prices, high_prices, low_prices, close_prices),
                index=self.data.index, name='Evening_Star'
            )

            patterns['Three_White_Soldiers'] = pd.Series(
                talib.CDL3WHITESOLDIERS(open_prices, high_prices, low_prices, close_prices),
                index=self.data.index, name='Three_White_Soldiers'
            )

            patterns['Three_Black_Crows'] = pd.Series(
                talib.CDL3BLACKCROWS(open_prices, high_prices, low_prices, close_prices),
                index=self.data.index, name='Three_Black_Crows'
            )

            # Continuation patterns
            patterns['Rising_Three'] = pd.Series(
                talib.CDLRISEFALL3METHODS(open_prices, high_prices, low_prices, close_prices),
                index=self.data.index, name='Rising_Three'
            )

            patterns['Doji'] = pd.Series(
                talib.CDLDOJI(open_prices, high_prices, low_prices, close_prices),
                index=self.data.index, name='Doji'
            )

            patterns['Spinning_Top'] = pd.Series(
                talib.CDLSPINNINGTOP(open_prices, high_prices, low_prices, close_prices),
                index=self.data.index, name='Spinning_Top'
            )

            logger.debug(f"Detected {len(patterns)} candlestick pattern types")
            return patterns

        except Exception as e:
            logger.error(f"Error detecting candlestick patterns: {str(e)}")
            raise

    def get_active_patterns(self, lookback: int = 5) -> List[Dict[str, Union[str, int]]]:
        """
        Get currently active candlestick patterns within lookback period.

        Args:
            lookback: Number of recent candles to check (default: 5)

        Returns:
            List of dicts with pattern information {'name', 'signal', 'index', 'strength'}
            signal: 'bullish' or 'bearish'
            strength: 100 for strong patterns, lower for weaker ones

        Raises:
            ValueError: If lookback is invalid
        """
        try:
            if lookback < 1:
                raise ValueError(f"lookback must be >= 1, got {lookback}")

            if len(self.data) < lookback:
                logger.warning(f"Data length ({len(self.data)}) < lookback ({lookback})")
                lookback = len(self.data)

            patterns = self.detect_candlestick_patterns()
            active_patterns = []

            for pattern_name, pattern_series in patterns.items():
                # Check recent candles for pattern
                recent = pattern_series.iloc[-lookback:]

                for idx, value in recent.items():
                    if value != 0:
                        signal = 'bullish' if value > 0 else 'bearish'
                        active_patterns.append({
                            'name': pattern_name,
                            'signal': signal,
                            'index': idx,
                            'strength': abs(int(value))
                        })

            logger.debug(f"Found {len(active_patterns)} active patterns in last {lookback} candles")
            return active_patterns

        except Exception as e:
            logger.error(f"Error getting active patterns: {str(e)}")
            raise

    def detect_support_resistance(self,
                                  window: int = 20,
                                  num_levels: int = 3) -> Dict[str, List[float]]:
        """
        Detect support and resistance levels using local extrema.

        Args:
            window: Window size for detecting local extrema (default: 20)
            num_levels: Number of support/resistance levels to return (default: 3)

        Returns:
            Dict with 'support' and 'resistance' lists of price levels

        Raises:
            ValueError: If parameters are invalid or insufficient data
        """
        try:
            if window < 3:
                raise ValueError(f"window must be >= 3, got {window}")

            if len(self.data) < window * 2:
                raise ValueError(f"Insufficient data. Need at least {window * 2} periods")

            # Find local maxima (resistance)
            highs = self.data['high'].values
            resistance_idx = argrelextrema(highs, np.greater, order=window)[0]
            resistance_levels = highs[resistance_idx]

            # Find local minima (support)
            lows = self.data['low'].values
            support_idx = argrelextrema(lows, np.less, order=window)[0]
            support_levels = lows[support_idx]

            # Cluster levels and select the most significant ones
            current_price = self.data['close'].iloc[-1]

            # For support: get levels below current price
            valid_support = [level for level in support_levels if level < current_price]
            valid_support = sorted(valid_support, reverse=True)[:num_levels]

            # For resistance: get levels above current price
            valid_resistance = [level for level in resistance_levels if level > current_price]
            valid_resistance = sorted(valid_resistance)[:num_levels]

            logger.debug(f"Detected {len(valid_support)} support and {len(valid_resistance)} resistance levels")

            return {
                'support': [float(level) for level in valid_support],
                'resistance': [float(level) for level in valid_resistance],
                'current_price': float(current_price)
            }

        except Exception as e:
            logger.error(f"Error detecting support/resistance: {str(e)}")
            raise

    def detect_trend_lines(self,
                          lookback: int = 50,
                          min_touches: int = 2) -> Dict[str, Optional[Dict[str, float]]]:
        """
        Detect trend lines (support and resistance trend lines).

        Args:
            lookback: Number of candles to analyze (default: 50)
            min_touches: Minimum number of touches required for valid trend line (default: 2)

        Returns:
            Dict with 'uptrend_line' and 'downtrend_line', each containing 'slope' and 'intercept'

        Raises:
            ValueError: If parameters are invalid
        """
        try:
            if lookback < 10:
                raise ValueError(f"lookback must be >= 10, got {lookback}")

            if len(self.data) < lookback:
                lookback = len(self.data)

            recent_data = self.data.iloc[-lookback:].copy()

            # For uptrend line, use lows
            lows = recent_data['low'].values
            low_idx = np.arange(len(lows))

            # Find best fit line for lows (potential uptrend line)
            try:
                uptrend_fit = np.polyfit(low_idx, lows, 1)
                uptrend_line = np.poly1d(uptrend_fit)

                # Count touches (points within 1% of line)
                uptrend_touches = np.sum(np.abs(lows - uptrend_line(low_idx)) / lows < 0.01)

                uptrend_result = {
                    'slope': float(uptrend_fit[0]),
                    'intercept': float(uptrend_fit[1]),
                    'touches': int(uptrend_touches)
                } if uptrend_touches >= min_touches else None
            except Exception:
                uptrend_result = None

            # For downtrend line, use highs
            highs = recent_data['high'].values
            high_idx = np.arange(len(highs))

            # Find best fit line for highs (potential downtrend line)
            try:
                downtrend_fit = np.polyfit(high_idx, highs, 1)
                downtrend_line = np.poly1d(downtrend_fit)

                # Count touches
                downtrend_touches = np.sum(np.abs(highs - downtrend_line(high_idx)) / highs < 0.01)

                downtrend_result = {
                    'slope': float(downtrend_fit[0]),
                    'intercept': float(downtrend_fit[1]),
                    'touches': int(downtrend_touches)
                } if downtrend_touches >= min_touches else None
            except Exception:
                downtrend_result = None

            logger.debug(f"Detected trend lines (uptrend: {uptrend_result is not None}, downtrend: {downtrend_result is not None})")

            return {
                'uptrend_line': uptrend_result,
                'downtrend_line': downtrend_result
            }

        except Exception as e:
            logger.error(f"Error detecting trend lines: {str(e)}")
            raise

    def detect_chart_patterns(self) -> Dict[str, Dict[str, Union[bool, float]]]:
        """
        Detect common chart patterns (Head and Shoulders, Double Top/Bottom, Triangles).

        Returns:
            Dict with pattern names and detection results

        Raises:
            Exception: If pattern detection fails
        """
        try:
            patterns = {
                'head_and_shoulders': self._detect_head_and_shoulders(),
                'double_top': self._detect_double_top(),
                'double_bottom': self._detect_double_bottom(),
                'triangle': self._detect_triangle()
            }

            detected_count = sum(1 for p in patterns.values() if p['detected'])
            logger.debug(f"Chart pattern detection complete. Found {detected_count} patterns")

            return patterns

        except Exception as e:
            logger.error(f"Error detecting chart patterns: {str(e)}")
            raise

    def _detect_head_and_shoulders(self, lookback: int = 50) -> Dict[str, Union[bool, float]]:
        """
        Detect Head and Shoulders pattern.

        Args:
            lookback: Number of candles to analyze

        Returns:
            Dict with 'detected' bool and 'confidence' float
        """
        try:
            if len(self.data) < lookback:
                return {'detected': False, 'confidence': 0.0, 'type': None}

            recent_data = self.data.iloc[-lookback:]
            highs = recent_data['high'].values

            # Find peaks
            peaks_idx = argrelextrema(highs, np.greater, order=5)[0]

            if len(peaks_idx) < 3:
                return {'detected': False, 'confidence': 0.0, 'type': None}

            # Check last 3 peaks for H&S pattern
            if len(peaks_idx) >= 3:
                left_shoulder_idx = peaks_idx[-3]
                head_idx = peaks_idx[-2]
                right_shoulder_idx = peaks_idx[-1]

                left_shoulder = highs[left_shoulder_idx]
                head = highs[head_idx]
                right_shoulder = highs[right_shoulder_idx]

                # H&S criteria: head higher than shoulders, shoulders roughly equal
                if (head > left_shoulder and head > right_shoulder and
                    abs(left_shoulder - right_shoulder) / left_shoulder < 0.03):

                    confidence = 75.0
                    logger.debug("Head and Shoulders pattern detected")
                    return {'detected': True, 'confidence': confidence, 'type': 'bearish'}

            return {'detected': False, 'confidence': 0.0, 'type': None}

        except Exception as e:
            logger.warning(f"Error in H&S detection: {str(e)}")
            return {'detected': False, 'confidence': 0.0, 'type': None}

    def _detect_double_top(self, lookback: int = 50, tolerance: float = 0.02) -> Dict[str, Union[bool, float]]:
        """
        Detect Double Top pattern.

        Args:
            lookback: Number of candles to analyze
            tolerance: Price tolerance for peak matching (2% default)

        Returns:
            Dict with 'detected' bool and 'confidence' float
        """
        try:
            if len(self.data) < lookback:
                return {'detected': False, 'confidence': 0.0, 'type': None}

            recent_data = self.data.iloc[-lookback:]
            highs = recent_data['high'].values

            # Find peaks
            peaks_idx = argrelextrema(highs, np.greater, order=5)[0]

            if len(peaks_idx) < 2:
                return {'detected': False, 'confidence': 0.0, 'type': None}

            # Check last 2 peaks
            peak1_idx = peaks_idx[-2]
            peak2_idx = peaks_idx[-1]

            peak1 = highs[peak1_idx]
            peak2 = highs[peak2_idx]

            # Double top criteria: peaks at similar levels
            if abs(peak1 - peak2) / peak1 < tolerance:
                confidence = 70.0
                logger.debug("Double Top pattern detected")
                return {'detected': True, 'confidence': confidence, 'type': 'bearish'}

            return {'detected': False, 'confidence': 0.0, 'type': None}

        except Exception as e:
            logger.warning(f"Error in Double Top detection: {str(e)}")
            return {'detected': False, 'confidence': 0.0, 'type': None}

    def _detect_double_bottom(self, lookback: int = 50, tolerance: float = 0.02) -> Dict[str, Union[bool, float]]:
        """
        Detect Double Bottom pattern.

        Args:
            lookback: Number of candles to analyze
            tolerance: Price tolerance for trough matching (2% default)

        Returns:
            Dict with 'detected' bool and 'confidence' float
        """
        try:
            if len(self.data) < lookback:
                return {'detected': False, 'confidence': 0.0, 'type': None}

            recent_data = self.data.iloc[-lookback:]
            lows = recent_data['low'].values

            # Find troughs
            troughs_idx = argrelextrema(lows, np.less, order=5)[0]

            if len(troughs_idx) < 2:
                return {'detected': False, 'confidence': 0.0, 'type': None}

            # Check last 2 troughs
            trough1_idx = troughs_idx[-2]
            trough2_idx = troughs_idx[-1]

            trough1 = lows[trough1_idx]
            trough2 = lows[trough2_idx]

            # Double bottom criteria: troughs at similar levels
            if abs(trough1 - trough2) / trough1 < tolerance:
                confidence = 70.0
                logger.debug("Double Bottom pattern detected")
                return {'detected': True, 'confidence': confidence, 'type': 'bullish'}

            return {'detected': False, 'confidence': 0.0, 'type': None}

        except Exception as e:
            logger.warning(f"Error in Double Bottom detection: {str(e)}")
            return {'detected': False, 'confidence': 0.0, 'type': None}

    def _detect_triangle(self, lookback: int = 50) -> Dict[str, Union[bool, float, str]]:
        """
        Detect Triangle patterns (ascending, descending, symmetrical).

        Args:
            lookback: Number of candles to analyze

        Returns:
            Dict with 'detected' bool, 'confidence' float, and 'triangle_type'
        """
        try:
            if len(self.data) < lookback:
                return {'detected': False, 'confidence': 0.0, 'triangle_type': None}

            recent_data = self.data.iloc[-lookback:]

            # Get highs and lows trend
            highs = recent_data['high'].values
            lows = recent_data['low'].values
            idx = np.arange(len(highs))

            # Fit lines to highs and lows
            try:
                high_fit = np.polyfit(idx, highs, 1)
                low_fit = np.polyfit(idx, lows, 1)

                high_slope = high_fit[0]
                low_slope = low_fit[0]

                # Determine triangle type based on slopes
                if abs(high_slope) < 0.01 and low_slope > 0.01:
                    # Ascending triangle: flat top, rising bottom
                    triangle_type = 'ascending'
                    confidence = 65.0
                    detected = True
                elif high_slope < -0.01 and abs(low_slope) < 0.01:
                    # Descending triangle: falling top, flat bottom
                    triangle_type = 'descending'
                    confidence = 65.0
                    detected = True
                elif high_slope < -0.01 and low_slope > 0.01:
                    # Symmetrical triangle: converging lines
                    triangle_type = 'symmetrical'
                    confidence = 60.0
                    detected = True
                else:
                    triangle_type = None
                    confidence = 0.0
                    detected = False

                if detected:
                    logger.debug(f"{triangle_type.capitalize()} Triangle pattern detected")

                return {
                    'detected': detected,
                    'confidence': confidence,
                    'triangle_type': triangle_type
                }

            except Exception:
                return {'detected': False, 'confidence': 0.0, 'triangle_type': None}

        except Exception as e:
            logger.warning(f"Error in Triangle detection: {str(e)}")
            return {'detected': False, 'confidence': 0.0, 'triangle_type': None}


def find_price_gaps(data: pd.DataFrame, min_gap_percent: float = 1.0) -> List[Dict[str, Union[str, float]]]:
    """
    Find price gaps in the data.

    Args:
        data: DataFrame with OHLC data
        min_gap_percent: Minimum gap size as percentage to report (default: 1.0%)

    Returns:
        List of dicts with gap information

    Raises:
        ValueError: If data is insufficient or min_gap_percent is invalid
    """
    try:
        if len(data) < 2:
            raise ValueError("Insufficient data for gap detection. Need at least 2 periods")

        if min_gap_percent <= 0:
            raise ValueError(f"min_gap_percent must be positive, got {min_gap_percent}")

        gaps = []

        for i in range(1, len(data)):
            prev_high = data['high'].iloc[i-1]
            prev_low = data['low'].iloc[i-1]
            curr_high = data['high'].iloc[i]
            curr_low = data['low'].iloc[i]

            # Gap up: current low > previous high
            if curr_low > prev_high:
                gap_size = (curr_low - prev_high) / prev_high * 100
                if gap_size >= min_gap_percent:
                    gaps.append({
                        'type': 'gap_up',
                        'index': data.index[i],
                        'gap_size_percent': float(gap_size),
                        'prev_high': float(prev_high),
                        'curr_low': float(curr_low)
                    })

            # Gap down: current high < previous low
            elif curr_high < prev_low:
                gap_size = (prev_low - curr_high) / prev_low * 100
                if gap_size >= min_gap_percent:
                    gaps.append({
                        'type': 'gap_down',
                        'index': data.index[i],
                        'gap_size_percent': float(gap_size),
                        'prev_low': float(prev_low),
                        'curr_high': float(curr_high)
                    })

        logger.debug(f"Found {len(gaps)} price gaps >= {min_gap_percent}%")
        return gaps

    except Exception as e:
        logger.error(f"Error finding price gaps: {str(e)}")
        raise
