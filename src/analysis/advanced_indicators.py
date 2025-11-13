"""
Advanced Technical Indicators Module

This module provides advanced technical indicator calculations including:
- Ichimoku Cloud with full signal generation
- Volume Profile with POC and Value Area
- Market Profile (TPO) analysis
- Order Flow indicators
- Advanced Volatility measures
- Elliott Wave Detection (simplified)
- Advanced Momentum Oscillators

Author: ScreenerIII
License: MIT
"""

from typing import Dict, List, Optional, Tuple, Union
import pandas as pd
import numpy as np
import logging
from dataclasses import dataclass
from enum import Enum

# Optional dependencies
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    logger.warning("TA-Lib not available. Some indicators will be limited.")

try:
    from scipy import signal
    from scipy.stats import norm
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logger.warning("SciPy not available. Some indicators will be limited.")

# Configure logging
logger = logging.getLogger(__name__)


class TrendType(Enum):
    """Trend types for Ichimoku signals"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class WaveType(Enum):
    """Elliott Wave types"""
    IMPULSE = "impulse"
    CORRECTIVE = "corrective"
    UNKNOWN = "unknown"


@dataclass
class IchimokuSignal:
    """Ichimoku Cloud signal data"""
    trend: TrendType
    price_vs_cloud: str  # 'above', 'below', 'in_cloud'
    tk_cross: Optional[str]  # 'bullish', 'bearish', None
    cloud_color: str  # 'green', 'red'
    cloud_thickness: float
    strength: float  # 0-100
    lagging_span_confirmation: bool


@dataclass
class VolumeProfileData:
    """Volume Profile analysis data"""
    poc: float  # Point of Control
    value_area_high: float
    value_area_low: float
    hvn_levels: List[float]  # High Volume Nodes
    lvn_levels: List[float]  # Low Volume Nodes
    volume_delta: float
    profile: pd.DataFrame  # price_level, volume, percentage


@dataclass
class MarketProfileData:
    """Market Profile (TPO) data"""
    poc: float  # Point of Control
    value_area_high: float
    value_area_low: float
    initial_balance_high: float
    initial_balance_low: float
    profile: pd.DataFrame  # price_level, tpo_count, percentage


@dataclass
class OrderFlowData:
    """Order flow analysis data"""
    delta: pd.Series  # buy - sell volume
    cumulative_delta: pd.Series
    imbalance_ratio: pd.Series  # bid/ask imbalance
    absorption_detected: pd.Series  # boolean series


class AdvancedIndicators:
    """
    Advanced technical indicator calculations for sophisticated market analysis.

    This class provides advanced indicators including Ichimoku Cloud, Volume Profile,
    Market Profile, Order Flow analysis, Elliott Wave detection, and advanced
    momentum/volatility oscillators.
    """

    def __init__(self, data: pd.DataFrame):
        """
        Initialize AdvancedIndicators with price data.

        Args:
            data: DataFrame with OHLCV data (Open, High, Low, Close, Volume)
                  Required columns: 'open', 'high', 'low', 'close', 'volume'
                  Optional: 'buy_volume', 'sell_volume' for order flow

        Raises:
            ValueError: If required columns are missing from data
        """
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]

        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        self.data = data.copy()
        logger.info(f"Initialized AdvancedIndicators with {len(self.data)} data points")

    # ==================== ICHIMOKU CLOUD ====================

    def calculate_ichimoku(self,
                          tenkan_period: int = 9,
                          kijun_period: int = 26,
                          senkou_b_period: int = 52,
                          displacement: int = 26) -> Dict[str, pd.Series]:
        """
        Calculate Ichimoku Cloud components.

        The Ichimoku Cloud is a comprehensive indicator that shows support/resistance,
        trend direction, and momentum in one view.

        Components:
        - Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
        - Kijun-sen (Base Line): (26-period high + 26-period low) / 2
        - Senkou Span A (Leading Span A): (Tenkan + Kijun) / 2, projected forward
        - Senkou Span B (Leading Span B): (52-period high + 52-period low) / 2, projected forward
        - Chikou Span (Lagging Span): Current close, projected backward

        Args:
            tenkan_period: Period for Tenkan-sen (default: 9)
            kijun_period: Period for Kijun-sen (default: 26)
            senkou_b_period: Period for Senkou Span B (default: 52)
            displacement: Periods to shift Senkou spans forward (default: 26)

        Returns:
            Dict[str, pd.Series]: Dictionary with all Ichimoku components

        Raises:
            ValueError: If periods are invalid
        """
        try:
            if len(self.data) < senkou_b_period:
                raise ValueError(f"Insufficient data. Need at least {senkou_b_period} periods")

            high = self.data['high']
            low = self.data['low']
            close = self.data['close']

            # Tenkan-sen (Conversion Line)
            tenkan_high = high.rolling(window=tenkan_period).max()
            tenkan_low = low.rolling(window=tenkan_period).min()
            tenkan_sen = (tenkan_high + tenkan_low) / 2

            # Kijun-sen (Base Line)
            kijun_high = high.rolling(window=kijun_period).max()
            kijun_low = low.rolling(window=kijun_period).min()
            kijun_sen = (kijun_high + kijun_low) / 2

            # Senkou Span A (Leading Span A)
            senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(displacement)

            # Senkou Span B (Leading Span B)
            senkou_high = high.rolling(window=senkou_b_period).max()
            senkou_low = low.rolling(window=senkou_b_period).min()
            senkou_span_b = ((senkou_high + senkou_low) / 2).shift(displacement)

            # Chikou Span (Lagging Span)
            chikou_span = close.shift(-displacement)

            logger.debug(f"Calculated Ichimoku Cloud ({tenkan_period},{kijun_period},{senkou_b_period})")

            return {
                'tenkan_sen': tenkan_sen,
                'kijun_sen': kijun_sen,
                'senkou_span_a': senkou_span_a,
                'senkou_span_b': senkou_span_b,
                'chikou_span': chikou_span
            }

        except Exception as e:
            logger.error(f"Error calculating Ichimoku: {str(e)}")
            raise

    def generate_ichimoku_signals(self,
                                 ichimoku: Optional[Dict[str, pd.Series]] = None) -> IchimokuSignal:
        """
        Generate trading signals from Ichimoku Cloud.

        Signal types:
        1. Price vs Cloud: Above (bullish), Below (bearish), In Cloud (neutral)
        2. TK Cross: Tenkan crossing Kijun (bullish/bearish)
        3. Cloud Color: Span A > Span B (green/bullish), else red/bearish
        4. Chikou Span: Above price (confirmation)

        Args:
            ichimoku: Pre-calculated Ichimoku components (optional)

        Returns:
            IchimokuSignal: Signal data with trend, strength, and confirmations
        """
        try:
            if ichimoku is None:
                ichimoku = self.calculate_ichimoku()

            # Get latest values
            close = self.data['close'].iloc[-1]
            tenkan = ichimoku['tenkan_sen'].iloc[-1]
            kijun = ichimoku['kijun_sen'].iloc[-1]
            span_a = ichimoku['senkou_span_a'].iloc[-1]
            span_b = ichimoku['senkou_span_b'].iloc[-1]
            chikou = ichimoku['chikou_span'].iloc[-26] if len(self.data) > 26 else np.nan

            # Price vs Cloud
            cloud_top = max(span_a, span_b)
            cloud_bottom = min(span_a, span_b)

            if close > cloud_top:
                price_vs_cloud = 'above'
            elif close < cloud_bottom:
                price_vs_cloud = 'below'
            else:
                price_vs_cloud = 'in_cloud'

            # TK Cross
            tk_cross = None
            if len(self.data) >= 2:
                prev_tenkan = ichimoku['tenkan_sen'].iloc[-2]
                prev_kijun = ichimoku['kijun_sen'].iloc[-2]

                if tenkan > kijun and prev_tenkan <= prev_kijun:
                    tk_cross = 'bullish'
                elif tenkan < kijun and prev_tenkan >= prev_kijun:
                    tk_cross = 'bearish'

            # Cloud color
            cloud_color = 'green' if span_a > span_b else 'red'

            # Cloud thickness (as percentage of price)
            cloud_thickness = abs(span_a - span_b) / close * 100

            # Lagging span confirmation
            lagging_confirmation = False
            if not np.isnan(chikou):
                price_26_ago = self.data['close'].iloc[-26]
                lagging_confirmation = chikou > price_26_ago

            # Overall trend determination
            bullish_signals = sum([
                price_vs_cloud == 'above',
                tenkan > kijun,
                cloud_color == 'green',
                lagging_confirmation
            ])

            bearish_signals = sum([
                price_vs_cloud == 'below',
                tenkan < kijun,
                cloud_color == 'red',
                not lagging_confirmation
            ])

            if bullish_signals >= 3:
                trend = TrendType.BULLISH
                strength = bullish_signals / 4 * 100
            elif bearish_signals >= 3:
                trend = TrendType.BEARISH
                strength = bearish_signals / 4 * 100
            else:
                trend = TrendType.NEUTRAL
                strength = 50.0

            return IchimokuSignal(
                trend=trend,
                price_vs_cloud=price_vs_cloud,
                tk_cross=tk_cross,
                cloud_color=cloud_color,
                cloud_thickness=cloud_thickness,
                strength=strength,
                lagging_span_confirmation=lagging_confirmation
            )

        except Exception as e:
            logger.error(f"Error generating Ichimoku signals: {str(e)}")
            raise

    # ==================== VOLUME PROFILE ====================

    def calculate_volume_profile(self,
                                num_bins: int = 50,
                                value_area_pct: float = 0.70) -> VolumeProfileData:
        """
        Calculate Volume Profile with POC and Value Area.

        Volume Profile shows the distribution of volume across price levels,
        helping identify key support/resistance and high/low activity areas.

        Args:
            num_bins: Number of price bins for profile (default: 50)
            value_area_pct: Percentage of volume for Value Area (default: 0.70)

        Returns:
            VolumeProfileData: POC, Value Area, HVN/LVN levels, and profile
        """
        try:
            # Create price bins
            price_min = self.data['low'].min()
            price_max = self.data['high'].max()
            bins = np.linspace(price_min, price_max, num_bins + 1)

            # Calculate volume at each price level
            volume_at_price = np.zeros(num_bins)

            for idx, row in self.data.iterrows():
                # Distribute volume across bins that the price touched
                low_bin = np.digitize(row['low'], bins) - 1
                high_bin = np.digitize(row['high'], bins) - 1

                low_bin = max(0, min(low_bin, num_bins - 1))
                high_bin = max(0, min(high_bin, num_bins - 1))

                # Distribute volume evenly across touched bins
                num_touched_bins = high_bin - low_bin + 1
                if num_touched_bins > 0:
                    volume_per_bin = row['volume'] / num_touched_bins
                    for bin_idx in range(low_bin, high_bin + 1):
                        volume_at_price[bin_idx] += volume_per_bin

            # Create profile DataFrame
            price_levels = (bins[:-1] + bins[1:]) / 2  # Midpoint of each bin
            total_volume = volume_at_price.sum()

            profile = pd.DataFrame({
                'price_level': price_levels,
                'volume': volume_at_price,
                'percentage': volume_at_price / total_volume * 100 if total_volume > 0 else 0
            })

            # Point of Control (POC) - price with highest volume
            poc_idx = np.argmax(volume_at_price)
            poc = price_levels[poc_idx]

            # Value Area - 70% of volume around POC
            sorted_indices = np.argsort(volume_at_price)[::-1]
            cumulative_volume = 0
            value_area_indices = []

            for idx in sorted_indices:
                value_area_indices.append(idx)
                cumulative_volume += volume_at_price[idx]
                if cumulative_volume >= total_volume * value_area_pct:
                    break

            value_area_prices = price_levels[value_area_indices]
            value_area_high = value_area_prices.max()
            value_area_low = value_area_prices.min()

            # High Volume Nodes (HVN) - above 75th percentile
            volume_threshold_hvn = np.percentile(volume_at_price, 75)
            hvn_levels = price_levels[volume_at_price >= volume_threshold_hvn].tolist()

            # Low Volume Nodes (LVN) - below 25th percentile
            volume_threshold_lvn = np.percentile(volume_at_price, 25)
            lvn_levels = price_levels[volume_at_price <= volume_threshold_lvn].tolist()

            # Volume Delta (if buy/sell volume available)
            if 'buy_volume' in self.data.columns and 'sell_volume' in self.data.columns:
                volume_delta = (self.data['buy_volume'].sum() - self.data['sell_volume'].sum())
            else:
                # Estimate using price action
                volume_delta = self.data.apply(
                    lambda x: x['volume'] if x['close'] > x['open'] else -x['volume'],
                    axis=1
                ).sum()

            logger.debug(f"Calculated Volume Profile (POC: {poc:.2f}, VA: {value_area_low:.2f}-{value_area_high:.2f})")

            return VolumeProfileData(
                poc=float(poc),
                value_area_high=float(value_area_high),
                value_area_low=float(value_area_low),
                hvn_levels=hvn_levels,
                lvn_levels=lvn_levels,
                volume_delta=float(volume_delta),
                profile=profile
            )

        except Exception as e:
            logger.error(f"Error calculating Volume Profile: {str(e)}")
            raise

    # ==================== MARKET PROFILE (TPO) ====================

    def calculate_market_profile(self,
                                num_bins: int = 50,
                                value_area_pct: float = 0.70,
                                initial_balance_hours: int = 2) -> MarketProfileData:
        """
        Calculate Market Profile (Time Price Opportunity).

        Market Profile organizes price and time data to show where the market
        spent the most time, identifying fair value areas.

        Args:
            num_bins: Number of price bins (default: 50)
            value_area_pct: Percentage for Value Area (default: 0.70)
            initial_balance_hours: Hours for Initial Balance (default: 2)

        Returns:
            MarketProfileData: POC, Value Area, Initial Balance, and TPO profile
        """
        try:
            # Create price bins
            price_min = self.data['low'].min()
            price_max = self.data['high'].max()
            bins = np.linspace(price_min, price_max, num_bins + 1)

            # Calculate TPO (time spent at each price level)
            tpo_at_price = np.zeros(num_bins)

            # For initial balance, use first N periods
            ib_periods = min(initial_balance_hours, len(self.data))
            ib_high = self.data['high'].iloc[:ib_periods].max()
            ib_low = self.data['low'].iloc[:ib_periods].min()

            for idx, row in self.data.iterrows():
                # Each period adds TPO to all price levels it touched
                low_bin = np.digitize(row['low'], bins) - 1
                high_bin = np.digitize(row['high'], bins) - 1

                low_bin = max(0, min(low_bin, num_bins - 1))
                high_bin = max(0, min(high_bin, num_bins - 1))

                # Add 1 TPO count to each touched bin
                for bin_idx in range(low_bin, high_bin + 1):
                    tpo_at_price[bin_idx] += 1

            # Create profile DataFrame
            price_levels = (bins[:-1] + bins[1:]) / 2
            total_tpo = tpo_at_price.sum()

            profile = pd.DataFrame({
                'price_level': price_levels,
                'tpo_count': tpo_at_price,
                'percentage': tpo_at_price / total_tpo * 100 if total_tpo > 0 else 0
            })

            # Point of Control (POC) - price with most TPO
            poc_idx = np.argmax(tpo_at_price)
            poc = price_levels[poc_idx]

            # Value Area - area containing value_area_pct of TPO
            sorted_indices = np.argsort(tpo_at_price)[::-1]
            cumulative_tpo = 0
            value_area_indices = []

            for idx in sorted_indices:
                value_area_indices.append(idx)
                cumulative_tpo += tpo_at_price[idx]
                if cumulative_tpo >= total_tpo * value_area_pct:
                    break

            value_area_prices = price_levels[value_area_indices]
            value_area_high = value_area_prices.max()
            value_area_low = value_area_prices.min()

            logger.debug(f"Calculated Market Profile (POC: {poc:.2f}, IB: {ib_low:.2f}-{ib_high:.2f})")

            return MarketProfileData(
                poc=float(poc),
                value_area_high=float(value_area_high),
                value_area_low=float(value_area_low),
                initial_balance_high=float(ib_high),
                initial_balance_low=float(ib_low),
                profile=profile
            )

        except Exception as e:
            logger.error(f"Error calculating Market Profile: {str(e)}")
            raise

    # ==================== ORDER FLOW INDICATORS ====================

    def calculate_order_flow(self,
                           absorption_threshold: float = 2.0) -> OrderFlowData:
        """
        Calculate Order Flow indicators.

        Order flow analysis shows buying vs selling pressure and potential
        absorption zones where large orders are being filled.

        Args:
            absorption_threshold: Threshold for absorption detection (default: 2.0)

        Returns:
            OrderFlowData: Delta, cumulative delta, imbalance, and absorption signals
        """
        try:
            # Delta (buy volume - sell volume)
            if 'buy_volume' in self.data.columns and 'sell_volume' in self.data.columns:
                delta = self.data['buy_volume'] - self.data['sell_volume']
            else:
                # Estimate delta from price action
                delta = self.data.apply(
                    lambda x: x['volume'] if x['close'] > x['open']
                    else (-x['volume'] if x['close'] < x['open'] else 0),
                    axis=1
                )

            # Cumulative Delta
            cumulative_delta = delta.cumsum()

            # Bid/Ask Imbalance Ratio
            if 'buy_volume' in self.data.columns and 'sell_volume' in self.data.columns:
                # Avoid division by zero
                sell_volume_safe = self.data['sell_volume'].replace(0, 1)
                imbalance_ratio = self.data['buy_volume'] / sell_volume_safe
            else:
                # Estimate imbalance from price and volume
                price_change = self.data['close'] - self.data['open']
                imbalance_ratio = pd.Series(1.0, index=self.data.index)
                imbalance_ratio[price_change > 0] = 1.5
                imbalance_ratio[price_change < 0] = 0.67

            # Absorption Detection
            # Absorption occurs when price doesn't move despite high volume
            absorption = pd.Series(False, index=self.data.index)

            if len(self.data) >= 3:
                # Calculate price movement relative to volume
                price_range = self.data['high'] - self.data['low']
                volume_ma = self.data['volume'].rolling(window=20).mean()

                # High volume, low price movement = potential absorption
                for i in range(2, len(self.data)):
                    if (self.data['volume'].iloc[i] > volume_ma.iloc[i] * absorption_threshold and
                        price_range.iloc[i] < price_range.iloc[i-2:i].mean() * 0.5):
                        absorption.iloc[i] = True

            logger.debug("Calculated Order Flow indicators")

            return OrderFlowData(
                delta=delta,
                cumulative_delta=cumulative_delta,
                imbalance_ratio=imbalance_ratio,
                absorption_detected=absorption
            )

        except Exception as e:
            logger.error(f"Error calculating Order Flow: {str(e)}")
            raise

    # ==================== ADVANCED VOLATILITY ====================

    def calculate_keltner_channels(self,
                                   ema_period: int = 20,
                                   atr_period: int = 10,
                                   atr_multiplier: float = 2.0) -> Dict[str, pd.Series]:
        """
        Calculate Keltner Channels.

        Keltner Channels use ATR to set channel distance from EMA, providing
        a volatility-based envelope around price.

        Args:
            ema_period: Period for middle EMA line (default: 20)
            atr_period: Period for ATR calculation (default: 10)
            atr_multiplier: Multiplier for ATR distance (default: 2.0)

        Returns:
            Dict[str, pd.Series]: Upper, middle, and lower channel lines
        """
        try:
            # Middle line - EMA
            middle = talib.EMA(self.data['close'].values, timeperiod=ema_period)

            # ATR for channel width
            atr = talib.ATR(
                self.data['high'].values,
                self.data['low'].values,
                self.data['close'].values,
                timeperiod=atr_period
            )

            # Upper and Lower channels
            upper = middle + (atr * atr_multiplier)
            lower = middle - (atr * atr_multiplier)

            logger.debug(f"Calculated Keltner Channels ({ema_period}, {atr_period}, {atr_multiplier})")

            return {
                'keltner_upper': pd.Series(upper, index=self.data.index, name='keltner_upper'),
                'keltner_middle': pd.Series(middle, index=self.data.index, name='keltner_middle'),
                'keltner_lower': pd.Series(lower, index=self.data.index, name='keltner_lower')
            }

        except Exception as e:
            logger.error(f"Error calculating Keltner Channels: {str(e)}")
            raise

    def calculate_donchian_channels(self, period: int = 20) -> Dict[str, pd.Series]:
        """
        Calculate Donchian Channels.

        Donchian Channels show the highest high and lowest low over a period,
        often used for breakout trading strategies.

        Args:
            period: Lookback period (default: 20)

        Returns:
            Dict[str, pd.Series]: Upper, middle, and lower channel lines
        """
        try:
            # Upper channel - highest high
            upper = self.data['high'].rolling(window=period).max()

            # Lower channel - lowest low
            lower = self.data['low'].rolling(window=period).min()

            # Middle channel - average of upper and lower
            middle = (upper + lower) / 2

            logger.debug(f"Calculated Donchian Channels (period={period})")

            return {
                'donchian_upper': upper,
                'donchian_middle': middle,
                'donchian_lower': lower
            }

        except Exception as e:
            logger.error(f"Error calculating Donchian Channels: {str(e)}")
            raise

    def calculate_adx_refined(self, period: int = 14) -> Dict[str, pd.Series]:
        """
        Calculate refined ADX with additional analysis.

        Provides ADX with trend classification and strength levels.

        Args:
            period: Period for ADX calculation (default: 14)

        Returns:
            Dict with ADX, +DI, -DI, and trend strength classification
        """
        try:
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

            # Trend strength classification
            trend_strength = pd.Series(index=self.data.index, dtype=str)
            trend_strength[adx < 20] = 'weak'
            trend_strength[(adx >= 20) & (adx < 40)] = 'moderate'
            trend_strength[adx >= 40] = 'strong'

            # Directional Index Difference
            di_diff = plus_di - minus_di

            logger.debug(f"Calculated refined ADX (period={period})")

            return {
                'ADX': pd.Series(adx, index=self.data.index, name='ADX'),
                'PLUS_DI': pd.Series(plus_di, index=self.data.index, name='PLUS_DI'),
                'MINUS_DI': pd.Series(minus_di, index=self.data.index, name='MINUS_DI'),
                'DI_diff': pd.Series(di_diff, index=self.data.index, name='DI_diff'),
                'trend_strength': trend_strength
            }

        except Exception as e:
            logger.error(f"Error calculating refined ADX: {str(e)}")
            raise

    def calculate_chaikin_volatility(self,
                                    ema_period: int = 10,
                                    roc_period: int = 10) -> pd.Series:
        """
        Calculate Chaikin Volatility.

        Chaikin Volatility measures the rate of change of the trading range,
        identifying periods of increasing or decreasing volatility.

        Args:
            ema_period: Period for EMA of high-low range (default: 10)
            roc_period: Period for ROC calculation (default: 10)

        Returns:
            pd.Series: Chaikin Volatility values
        """
        try:
            # High-Low range
            hl_range = self.data['high'] - self.data['low']

            # EMA of the range
            ema_hl = hl_range.ewm(span=ema_period, adjust=False).mean()

            # Rate of change of the EMA
            chaikin_vol = ((ema_hl - ema_hl.shift(roc_period)) / ema_hl.shift(roc_period)) * 100

            logger.debug(f"Calculated Chaikin Volatility ({ema_period}, {roc_period})")

            return chaikin_vol.rename('chaikin_volatility')

        except Exception as e:
            logger.error(f"Error calculating Chaikin Volatility: {str(e)}")
            raise

    # ==================== ELLIOTT WAVE DETECTION ====================

    def detect_elliott_waves(self,
                           min_wave_size: float = 0.02,
                           max_wave_size: float = 0.5) -> Dict[str, Union[List, WaveType]]:
        """
        Detect Elliott Wave patterns (simplified).

        Identifies potential impulse (1-2-3-4-5) and corrective (A-B-C) wave patterns
        using pivot detection and Fibonacci relationships.

        Args:
            min_wave_size: Minimum wave size as fraction of price (default: 0.02 = 2%)
            max_wave_size: Maximum wave size as fraction of price (default: 0.5 = 50%)

        Returns:
            Dict with detected waves, wave type, and Fibonacci relationships
        """
        try:
            # Find pivot points (local maxima and minima)
            pivots = self._find_pivots(window=5)

            if len(pivots) < 5:
                return {
                    'wave_type': WaveType.UNKNOWN,
                    'pivots': pivots,
                    'fibonacci_relationships': [],
                    'confidence': 0.0
                }

            # Analyze wave structure
            waves = []
            for i in range(len(pivots) - 1):
                wave_start = pivots[i]
                wave_end = pivots[i + 1]
                wave_size = abs(wave_end['price'] - wave_start['price'])
                wave_pct = wave_size / wave_start['price']

                if min_wave_size <= wave_pct <= max_wave_size:
                    waves.append({
                        'start_idx': wave_start['index'],
                        'end_idx': wave_end['index'],
                        'start_price': wave_start['price'],
                        'end_price': wave_end['price'],
                        'direction': 'up' if wave_end['price'] > wave_start['price'] else 'down',
                        'size': wave_size,
                        'size_pct': wave_pct
                    })

            # Check for impulse pattern (5 waves)
            if len(waves) >= 5:
                wave_type, confidence = self._check_impulse_pattern(waves[-5:])
            # Check for corrective pattern (3 waves)
            elif len(waves) >= 3:
                wave_type, confidence = self._check_corrective_pattern(waves[-3:])
            else:
                wave_type = WaveType.UNKNOWN
                confidence = 0.0

            # Calculate Fibonacci relationships
            fib_relationships = self._calculate_fibonacci_relationships(waves)

            logger.debug(f"Detected Elliott Waves: {wave_type.value} (confidence: {confidence:.2f})")

            return {
                'wave_type': wave_type,
                'pivots': pivots,
                'waves': waves,
                'fibonacci_relationships': fib_relationships,
                'confidence': confidence
            }

        except Exception as e:
            logger.error(f"Error detecting Elliott Waves: {str(e)}")
            raise

    def _find_pivots(self, window: int = 5) -> List[Dict]:
        """Find pivot points (local extrema) in price data."""
        pivots = []

        for i in range(window, len(self.data) - window):
            # Local maximum
            if all(self.data['high'].iloc[i] >= self.data['high'].iloc[i-window:i].max()) and \
               all(self.data['high'].iloc[i] >= self.data['high'].iloc[i+1:i+window+1].max()):
                pivots.append({
                    'index': i,
                    'price': self.data['high'].iloc[i],
                    'type': 'high'
                })
            # Local minimum
            elif all(self.data['low'].iloc[i] <= self.data['low'].iloc[i-window:i].min()) and \
                 all(self.data['low'].iloc[i] <= self.data['low'].iloc[i+1:i+window+1].min()):
                pivots.append({
                    'index': i,
                    'price': self.data['low'].iloc[i],
                    'type': 'low'
                })

        return pivots

    def _check_impulse_pattern(self, waves: List[Dict]) -> Tuple[WaveType, float]:
        """Check if waves form an impulse pattern (1-2-3-4-5)."""
        if len(waves) < 5:
            return WaveType.UNKNOWN, 0.0

        # Impulse pattern rules:
        # 1. Wave 3 cannot be shortest
        # 2. Wave 2 doesn't retrace more than 100% of wave 1
        # 3. Wave 4 doesn't overlap wave 1
        # 4. Waves 1, 3, 5 move in same direction

        scores = []

        # Check directional consistency
        if (waves[0]['direction'] == waves[2]['direction'] == waves[4]['direction']):
            scores.append(1)
        else:
            scores.append(0)

        # Check wave 3 is not shortest
        wave_sizes = [waves[0]['size'], waves[2]['size'], waves[4]['size']]
        if waves[2]['size'] != min(wave_sizes):
            scores.append(1)
        else:
            scores.append(0)

        # Additional rules can be added here

        confidence = sum(scores) / len(scores) * 100
        wave_type = WaveType.IMPULSE if confidence > 50 else WaveType.UNKNOWN

        return wave_type, confidence

    def _check_corrective_pattern(self, waves: List[Dict]) -> Tuple[WaveType, float]:
        """Check if waves form a corrective pattern (A-B-C)."""
        if len(waves) < 3:
            return WaveType.UNKNOWN, 0.0

        # Simple corrective pattern check
        # A and C move in same direction, B is correction
        if waves[0]['direction'] == waves[2]['direction'] and \
           waves[1]['direction'] != waves[0]['direction']:
            confidence = 70.0
            return WaveType.CORRECTIVE, confidence

        return WaveType.UNKNOWN, 0.0

    def _calculate_fibonacci_relationships(self, waves: List[Dict]) -> List[Dict]:
        """Calculate Fibonacci relationships between waves."""
        relationships = []
        fib_ratios = [0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618, 2.618]

        for i in range(len(waves) - 1):
            ratio = waves[i+1]['size'] / waves[i]['size'] if waves[i]['size'] > 0 else 0

            # Find closest Fibonacci ratio
            closest_fib = min(fib_ratios, key=lambda x: abs(x - ratio))
            difference = abs(ratio - closest_fib)

            if difference < 0.1:  # Within 10% of Fibonacci ratio
                relationships.append({
                    'wave_a': i,
                    'wave_b': i + 1,
                    'ratio': ratio,
                    'fibonacci': closest_fib,
                    'match': True
                })

        return relationships

    # ==================== MOMENTUM OSCILLATORS ====================

    def calculate_williams_r(self, period: int = 14) -> pd.Series:
        """
        Calculate Williams %R.

        Williams %R is a momentum indicator that measures overbought/oversold levels.
        Values range from -100 to 0, with readings above -20 indicating overbought
        and below -80 indicating oversold conditions.

        Args:
            period: Lookback period (default: 14)

        Returns:
            pd.Series: Williams %R values
        """
        try:
            williams_r = talib.WILLR(
                self.data['high'].values,
                self.data['low'].values,
                self.data['close'].values,
                timeperiod=period
            )

            logger.debug(f"Calculated Williams %R (period={period})")

            return pd.Series(williams_r, index=self.data.index, name=f'WILLR_{period}')

        except Exception as e:
            logger.error(f"Error calculating Williams %R: {str(e)}")
            raise

    def calculate_ultimate_oscillator(self,
                                     period1: int = 7,
                                     period2: int = 14,
                                     period3: int = 28) -> pd.Series:
        """
        Calculate Ultimate Oscillator.

        The Ultimate Oscillator uses three timeframes to reduce false signals
        and provide a more comprehensive momentum reading.

        Args:
            period1: Short period (default: 7)
            period2: Medium period (default: 14)
            period3: Long period (default: 28)

        Returns:
            pd.Series: Ultimate Oscillator values (0-100)
        """
        try:
            ultosc = talib.ULTOSC(
                self.data['high'].values,
                self.data['low'].values,
                self.data['close'].values,
                timeperiod1=period1,
                timeperiod2=period2,
                timeperiod3=period3
            )

            logger.debug(f"Calculated Ultimate Oscillator ({period1},{period2},{period3})")

            return pd.Series(ultosc, index=self.data.index, name='ultimate_oscillator')

        except Exception as e:
            logger.error(f"Error calculating Ultimate Oscillator: {str(e)}")
            raise

    def calculate_mfi(self, period: int = 14) -> pd.Series:
        """
        Calculate Money Flow Index (MFI).

        MFI is a momentum indicator that uses volume-weighted price to identify
        overbought/oversold conditions. Often called "volume-weighted RSI".

        Args:
            period: Lookback period (default: 14)

        Returns:
            pd.Series: MFI values (0-100)
        """
        try:
            mfi = talib.MFI(
                self.data['high'].values,
                self.data['low'].values,
                self.data['close'].values,
                self.data['volume'].values,
                timeperiod=period
            )

            logger.debug(f"Calculated MFI (period={period})")

            return pd.Series(mfi, index=self.data.index, name=f'MFI_{period}')

        except Exception as e:
            logger.error(f"Error calculating MFI: {str(e)}")
            raise

    def calculate_roc(self, period: int = 10, column: str = 'close') -> pd.Series:
        """
        Calculate Rate of Change (ROC).

        ROC measures the percentage change in price over a specified period,
        indicating momentum and trend strength.

        Args:
            period: Lookback period (default: 10)
            column: Column to calculate ROC on (default: 'close')

        Returns:
            pd.Series: ROC values (percentage)
        """
        try:
            roc = talib.ROC(self.data[column].values, timeperiod=period)

            logger.debug(f"Calculated ROC (period={period})")

            return pd.Series(roc, index=self.data.index, name=f'ROC_{period}')

        except Exception as e:
            logger.error(f"Error calculating ROC: {str(e)}")
            raise

    # ==================== UTILITY METHODS ====================

    def calculate_all_advanced_indicators(self) -> pd.DataFrame:
        """
        Calculate all advanced indicators and return as DataFrame.

        Returns:
            pd.DataFrame: Original data with all advanced indicators added
        """
        try:
            result = self.data.copy()

            # Ichimoku Cloud
            ichimoku = self.calculate_ichimoku()
            for name, series in ichimoku.items():
                result[name] = series

            # Keltner Channels
            keltner = self.calculate_keltner_channels()
            for name, series in keltner.items():
                result[name] = series

            # Donchian Channels
            donchian = self.calculate_donchian_channels()
            for name, series in donchian.items():
                result[name] = series

            # Advanced ADX
            adx_refined = self.calculate_adx_refined()
            for name, series in adx_refined.items():
                if isinstance(series, pd.Series):
                    result[name] = series

            # Chaikin Volatility
            result['chaikin_volatility'] = self.calculate_chaikin_volatility()

            # Momentum Oscillators
            result['williams_r'] = self.calculate_williams_r()
            result['ultimate_oscillator'] = self.calculate_ultimate_oscillator()
            result['mfi'] = self.calculate_mfi()
            result['roc'] = self.calculate_roc()

            # Order Flow (basic)
            order_flow = self.calculate_order_flow()
            result['delta'] = order_flow.delta
            result['cumulative_delta'] = order_flow.cumulative_delta
            result['imbalance_ratio'] = order_flow.imbalance_ratio
            result['absorption'] = order_flow.absorption_detected

            logger.info(f"Calculated all advanced indicators. Result shape: {result.shape}")
            return result

        except Exception as e:
            logger.error(f"Error calculating all advanced indicators: {str(e)}")
            raise

    def get_visualization_data(self, indicator_type: str) -> Dict:
        """
        Get formatted data for visualization of specific indicators.

        Args:
            indicator_type: Type of indicator ('ichimoku', 'volume_profile',
                          'market_profile', 'keltner', 'donchian')

        Returns:
            Dict: Formatted data ready for plotting
        """
        try:
            if indicator_type == 'ichimoku':
                ichimoku = self.calculate_ichimoku()
                return {
                    'type': 'ichimoku',
                    'data': ichimoku,
                    'price': self.data['close'],
                    'dates': self.data.index
                }

            elif indicator_type == 'volume_profile':
                vp = self.calculate_volume_profile()
                return {
                    'type': 'volume_profile',
                    'profile': vp.profile,
                    'poc': vp.poc,
                    'value_area_high': vp.value_area_high,
                    'value_area_low': vp.value_area_low,
                    'hvn_levels': vp.hvn_levels,
                    'lvn_levels': vp.lvn_levels
                }

            elif indicator_type == 'market_profile':
                mp = self.calculate_market_profile()
                return {
                    'type': 'market_profile',
                    'profile': mp.profile,
                    'poc': mp.poc,
                    'value_area_high': mp.value_area_high,
                    'value_area_low': mp.value_area_low,
                    'initial_balance_high': mp.initial_balance_high,
                    'initial_balance_low': mp.initial_balance_low
                }

            elif indicator_type == 'keltner':
                keltner = self.calculate_keltner_channels()
                return {
                    'type': 'keltner',
                    'data': keltner,
                    'price': self.data['close'],
                    'dates': self.data.index
                }

            elif indicator_type == 'donchian':
                donchian = self.calculate_donchian_channels()
                return {
                    'type': 'donchian',
                    'data': donchian,
                    'price': self.data['close'],
                    'dates': self.data.index
                }

            else:
                raise ValueError(f"Unknown indicator type: {indicator_type}")

        except Exception as e:
            logger.error(f"Error getting visualization data: {str(e)}")
            raise


# ==================== USAGE EXAMPLES ====================

def example_usage():
    """
    Example usage of AdvancedIndicators class.

    Demonstrates how to use various advanced indicators and their features.
    """
    # Create sample data
    import yfinance as yf

    print("=== Advanced Indicators Usage Examples ===\n")

    # Download sample data
    print("1. Loading sample data...")
    ticker = yf.Ticker("AAPL")
    data = ticker.history(period="6mo", interval="1d")
    data.columns = [col.lower() for col in data.columns]

    # Initialize
    adv_indicators = AdvancedIndicators(data)
    print(f"   Loaded {len(data)} bars of data\n")

    # Ichimoku Cloud
    print("2. Calculating Ichimoku Cloud...")
    ichimoku = adv_indicators.calculate_ichimoku()
    print(f"   Tenkan-sen (latest): {ichimoku['tenkan_sen'].iloc[-1]:.2f}")
    print(f"   Kijun-sen (latest): {ichimoku['kijun_sen'].iloc[-1]:.2f}")

    signals = adv_indicators.generate_ichimoku_signals(ichimoku)
    print(f"   Trend: {signals.trend.value}")
    print(f"   Price vs Cloud: {signals.price_vs_cloud}")
    print(f"   Signal Strength: {signals.strength:.1f}%\n")

    # Volume Profile
    print("3. Calculating Volume Profile...")
    vp = adv_indicators.calculate_volume_profile(num_bins=30)
    print(f"   Point of Control (POC): ${vp.poc:.2f}")
    print(f"   Value Area High: ${vp.value_area_high:.2f}")
    print(f"   Value Area Low: ${vp.value_area_low:.2f}")
    print(f"   High Volume Nodes: {len(vp.hvn_levels)} levels")
    print(f"   Low Volume Nodes: {len(vp.lvn_levels)} levels")
    print(f"   Volume Delta: {vp.volume_delta:,.0f}\n")

    # Market Profile
    print("4. Calculating Market Profile...")
    mp = adv_indicators.calculate_market_profile(num_bins=30)
    print(f"   POC: ${mp.poc:.2f}")
    print(f"   Value Area: ${mp.value_area_low:.2f} - ${mp.value_area_high:.2f}")
    print(f"   Initial Balance: ${mp.initial_balance_low:.2f} - ${mp.initial_balance_high:.2f}\n")

    # Order Flow
    print("5. Calculating Order Flow...")
    order_flow = adv_indicators.calculate_order_flow()
    print(f"   Current Delta: {order_flow.delta.iloc[-1]:,.0f}")
    print(f"   Cumulative Delta: {order_flow.cumulative_delta.iloc[-1]:,.0f}")
    print(f"   Imbalance Ratio: {order_flow.imbalance_ratio.iloc[-1]:.2f}")
    print(f"   Absorption Detected (last 5): {order_flow.absorption_detected.iloc[-5:].sum()} bars\n")

    # Keltner Channels
    print("6. Calculating Keltner Channels...")
    keltner = adv_indicators.calculate_keltner_channels()
    current_price = data['close'].iloc[-1]
    print(f"   Current Price: ${current_price:.2f}")
    print(f"   Upper Channel: ${keltner['keltner_upper'].iloc[-1]:.2f}")
    print(f"   Middle Channel: ${keltner['keltner_middle'].iloc[-1]:.2f}")
    print(f"   Lower Channel: ${keltner['keltner_lower'].iloc[-1]:.2f}\n")

    # Donchian Channels
    print("7. Calculating Donchian Channels...")
    donchian = adv_indicators.calculate_donchian_channels(period=20)
    print(f"   Upper Channel (20-day high): ${donchian['donchian_upper'].iloc[-1]:.2f}")
    print(f"   Lower Channel (20-day low): ${donchian['donchian_lower'].iloc[-1]:.2f}\n")

    # Advanced ADX
    print("8. Calculating Advanced ADX...")
    adx = adv_indicators.calculate_adx_refined()
    print(f"   ADX: {adx['ADX'].iloc[-1]:.2f}")
    print(f"   +DI: {adx['PLUS_DI'].iloc[-1]:.2f}")
    print(f"   -DI: {adx['MINUS_DI'].iloc[-1]:.2f}")
    print(f"   Trend Strength: {adx['trend_strength'].iloc[-1]}\n")

    # Chaikin Volatility
    print("9. Calculating Chaikin Volatility...")
    chaikin = adv_indicators.calculate_chaikin_volatility()
    print(f"   Current Volatility: {chaikin.iloc[-1]:.2f}%\n")

    # Elliott Wave Detection
    print("10. Detecting Elliott Waves...")
    waves = adv_indicators.detect_elliott_waves()
    print(f"   Wave Type: {waves['wave_type'].value}")
    print(f"   Confidence: {waves['confidence']:.1f}%")
    print(f"   Detected Pivots: {len(waves['pivots'])}")
    print(f"   Fibonacci Relationships: {len(waves['fibonacci_relationships'])}\n")

    # Momentum Oscillators
    print("11. Calculating Momentum Oscillators...")
    williams = adv_indicators.calculate_williams_r()
    ultosc = adv_indicators.calculate_ultimate_oscillator()
    mfi = adv_indicators.calculate_mfi()
    roc = adv_indicators.calculate_roc()

    print(f"   Williams %R: {williams.iloc[-1]:.2f}")
    print(f"   Ultimate Oscillator: {ultosc.iloc[-1]:.2f}")
    print(f"   Money Flow Index: {mfi.iloc[-1]:.2f}")
    print(f"   Rate of Change: {roc.iloc[-1]:.2f}%\n")

    # Calculate all indicators
    print("12. Calculating all advanced indicators...")
    all_indicators = adv_indicators.calculate_all_advanced_indicators()
    print(f"   Total columns: {len(all_indicators.columns)}")
    print(f"   New indicators added: {len(all_indicators.columns) - len(data.columns)}\n")

    print("=== Examples Complete ===")


if __name__ == "__main__":
    # Run examples if module is executed directly
    try:
        example_usage()
    except Exception as e:
        print(f"Error running examples: {str(e)}")
        import traceback
        traceback.print_exc()
