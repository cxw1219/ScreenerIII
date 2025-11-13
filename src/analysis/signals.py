"""
Signal Generation Module

This module provides comprehensive trading signal generation logic,
including buy/sell signal determination, target/stop level calculation,
risk/reward ratios, and confidence scoring.

Author: ScreenerIII
License: MIT
"""

from typing import Dict, List, Optional, Tuple, Union
import pandas as pd
import numpy as np
import logging
from dataclasses import dataclass
from enum import Enum

from .indicators import TechnicalIndicators
from .patterns import PatternRecognition

# Configure logging
logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Enumeration of signal types."""
    BUY = "BUY"
    SELL = "SELL"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"
    HOLD = "HOLD"
    NO_SIGNAL = "NO_SIGNAL"


@dataclass
class TradingSignal:
    """
    Data class representing a trading signal.

    Attributes:
        signal_type: Type of signal (BUY, SELL, etc.)
        confidence: Signal confidence score (0-100)
        entry_price: Recommended entry price
        stop_loss: Stop loss level
        target_1: First target level
        target_2: Second target level (optional)
        target_3: Third target level (optional)
        risk_reward_ratio: Risk/reward ratio
        reasoning: List of reasons for the signal
        timestamp: Signal generation timestamp
    """
    signal_type: SignalType
    confidence: float
    entry_price: float
    stop_loss: float
    target_1: float
    target_2: Optional[float] = None
    target_3: Optional[float] = None
    risk_reward_ratio: float = 0.0
    reasoning: List[str] = None
    timestamp: Optional[pd.Timestamp] = None

    def __post_init__(self):
        """Validate and compute derived fields."""
        if self.reasoning is None:
            self.reasoning = []

        # Calculate risk/reward ratio
        if self.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
            risk = abs(self.entry_price - self.stop_loss)
            reward = abs(self.target_1 - self.entry_price)
        elif self.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
            risk = abs(self.stop_loss - self.entry_price)
            reward = abs(self.entry_price - self.target_1)
        else:
            risk = 1
            reward = 0

        self.risk_reward_ratio = reward / risk if risk > 0 else 0.0

    def to_dict(self) -> Dict:
        """Convert signal to dictionary."""
        return {
            'signal_type': self.signal_type.value,
            'confidence': round(self.confidence, 2),
            'entry_price': round(self.entry_price, 4),
            'stop_loss': round(self.stop_loss, 4),
            'target_1': round(self.target_1, 4),
            'target_2': round(self.target_2, 4) if self.target_2 else None,
            'target_3': round(self.target_3, 4) if self.target_3 else None,
            'risk_reward_ratio': round(self.risk_reward_ratio, 2),
            'reasoning': self.reasoning,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class SignalGenerator:
    """
    Comprehensive trading signal generator.

    Combines technical indicators, patterns, and market conditions to generate
    trading signals with confidence scores and risk management levels.
    """

    def __init__(self, data: pd.DataFrame, risk_percent: float = 2.0):
        """
        Initialize SignalGenerator.

        Args:
            data: DataFrame with OHLCV data
            risk_percent: Risk percentage per trade (default: 2.0%)

        Raises:
            ValueError: If data is invalid or risk_percent is out of range
        """
        if len(data) < 50:
            raise ValueError(f"Insufficient data for signal generation. Need at least 50 periods, got {len(data)}")

        if not 0.1 <= risk_percent <= 10.0:
            raise ValueError(f"risk_percent must be between 0.1 and 10.0, got {risk_percent}")

        self.data = data.copy()
        self.risk_percent = risk_percent
        self.indicators = TechnicalIndicators(data)
        self.patterns = PatternRecognition(data)

        logger.info(f"Initialized SignalGenerator with {len(data)} data points, risk: {risk_percent}%")

    def generate_signal(self) -> TradingSignal:
        """
        Generate comprehensive trading signal based on all available indicators and patterns.

        Returns:
            TradingSignal: Complete trading signal with all parameters

        Raises:
            Exception: If signal generation fails
        """
        try:
            # Calculate all indicators
            indicators_data = self._calculate_key_indicators()

            # Detect patterns
            patterns_data = self._analyze_patterns()

            # Analyze trend
            trend_data = self.indicators.detect_trend()

            # Score the signal
            signal_score = self._calculate_signal_score(indicators_data, patterns_data, trend_data)

            # Determine signal type
            signal_type = self._determine_signal_type(signal_score)

            # Calculate levels
            current_price = self.data['close'].iloc[-1]
            levels = self._calculate_levels(signal_type, current_price, indicators_data)

            # Compile reasoning
            reasoning = self._compile_reasoning(signal_score, indicators_data, patterns_data, trend_data)

            # Create signal
            signal = TradingSignal(
                signal_type=signal_type,
                confidence=signal_score['total_confidence'],
                entry_price=current_price,
                stop_loss=levels['stop_loss'],
                target_1=levels['target_1'],
                target_2=levels.get('target_2'),
                target_3=levels.get('target_3'),
                reasoning=reasoning,
                timestamp=self.data.index[-1] if hasattr(self.data.index[-1], 'isoformat') else None
            )

            logger.info(f"Generated signal: {signal.signal_type.value} (confidence: {signal.confidence:.2f})")
            return signal

        except Exception as e:
            logger.error(f"Error generating signal: {str(e)}")
            raise

    def _calculate_key_indicators(self) -> Dict:
        """
        Calculate key technical indicators for signal generation.

        Returns:
            Dict with indicator values
        """
        try:
            current_idx = -1

            # RSI
            rsi = self.indicators.calculate_rsi(14)
            rsi_value = rsi.iloc[current_idx] if not pd.isna(rsi.iloc[current_idx]) else 50

            # MACD
            macd = self.indicators.calculate_macd()
            macd_value = macd['MACD'].iloc[current_idx] if not pd.isna(macd['MACD'].iloc[current_idx]) else 0
            macd_signal = macd['MACD_signal'].iloc[current_idx] if not pd.isna(macd['MACD_signal'].iloc[current_idx]) else 0
            macd_histogram = macd['MACD_histogram'].iloc[current_idx] if not pd.isna(macd['MACD_histogram'].iloc[current_idx]) else 0

            # Moving Averages
            mas = self.indicators.calculate_moving_averages([20, 50], 'sma')
            sma_20 = mas['SMA_20'].iloc[current_idx] if not pd.isna(mas['SMA_20'].iloc[current_idx]) else self.data['close'].iloc[current_idx]
            sma_50 = mas['SMA_50'].iloc[current_idx] if not pd.isna(mas['SMA_50'].iloc[current_idx]) else self.data['close'].iloc[current_idx]

            # Bollinger Bands
            bb = self.indicators.calculate_bollinger_bands(20, 2.0)
            bb_upper = bb['BB_upper'].iloc[current_idx]
            bb_lower = bb['BB_lower'].iloc[current_idx]
            bb_middle = bb['BB_middle'].iloc[current_idx]

            # ATR
            atr = self.indicators.calculate_atr(14)
            atr_value = atr.iloc[current_idx] if not pd.isna(atr.iloc[current_idx]) else 0

            # Stochastic
            stoch = self.indicators.calculate_stochastic()
            stoch_k = stoch['STOCH_k'].iloc[current_idx] if not pd.isna(stoch['STOCH_k'].iloc[current_idx]) else 50
            stoch_d = stoch['STOCH_d'].iloc[current_idx] if not pd.isna(stoch['STOCH_d'].iloc[current_idx]) else 50

            # ADX
            adx = self.indicators.calculate_adx()
            adx_value = adx['ADX'].iloc[current_idx] if not pd.isna(adx['ADX'].iloc[current_idx]) else 0
            plus_di = adx['PLUS_DI'].iloc[current_idx] if not pd.isna(adx['PLUS_DI'].iloc[current_idx]) else 0
            minus_di = adx['MINUS_DI'].iloc[current_idx] if not pd.isna(adx['MINUS_DI'].iloc[current_idx]) else 0

            current_price = self.data['close'].iloc[current_idx]

            return {
                'rsi': rsi_value,
                'macd': macd_value,
                'macd_signal': macd_signal,
                'macd_histogram': macd_histogram,
                'sma_20': sma_20,
                'sma_50': sma_50,
                'bb_upper': bb_upper,
                'bb_lower': bb_lower,
                'bb_middle': bb_middle,
                'atr': atr_value,
                'stoch_k': stoch_k,
                'stoch_d': stoch_d,
                'adx': adx_value,
                'plus_di': plus_di,
                'minus_di': minus_di,
                'current_price': current_price
            }

        except Exception as e:
            logger.error(f"Error calculating indicators: {str(e)}")
            raise

    def _analyze_patterns(self) -> Dict:
        """
        Analyze candlestick and chart patterns.

        Returns:
            Dict with pattern analysis
        """
        try:
            # Get active candlestick patterns
            active_patterns = self.patterns.get_active_patterns(lookback=3)

            # Get chart patterns
            chart_patterns = self.patterns.detect_chart_patterns()

            # Get support/resistance
            support_resistance = self.patterns.detect_support_resistance(window=20, num_levels=3)

            return {
                'candlestick_patterns': active_patterns,
                'chart_patterns': chart_patterns,
                'support_resistance': support_resistance
            }

        except Exception as e:
            logger.error(f"Error analyzing patterns: {str(e)}")
            raise

    def _calculate_signal_score(self,
                               indicators: Dict,
                               patterns: Dict,
                               trend: Dict) -> Dict[str, float]:
        """
        Calculate comprehensive signal score.

        Args:
            indicators: Indicator values
            patterns: Pattern analysis
            trend: Trend analysis

        Returns:
            Dict with bullish_score, bearish_score, and total_confidence
        """
        try:
            bullish_score = 0.0
            bearish_score = 0.0

            # RSI scoring (weight: 10)
            if indicators['rsi'] < 30:
                bullish_score += 10  # Oversold
            elif indicators['rsi'] > 70:
                bearish_score += 10  # Overbought
            elif 40 <= indicators['rsi'] <= 60:
                bullish_score += 3  # Neutral zone
                bearish_score += 3

            # MACD scoring (weight: 15)
            if indicators['macd'] > indicators['macd_signal']:
                bullish_score += 10
                if indicators['macd_histogram'] > 0:
                    bullish_score += 5
            else:
                bearish_score += 10
                if indicators['macd_histogram'] < 0:
                    bearish_score += 5

            # Moving Average scoring (weight: 15)
            if indicators['current_price'] > indicators['sma_20'] > indicators['sma_50']:
                bullish_score += 15  # Strong uptrend
            elif indicators['current_price'] < indicators['sma_20'] < indicators['sma_50']:
                bearish_score += 15  # Strong downtrend
            elif indicators['current_price'] > indicators['sma_20']:
                bullish_score += 8
            elif indicators['current_price'] < indicators['sma_20']:
                bearish_score += 8

            # Bollinger Bands scoring (weight: 10)
            bb_position = (indicators['current_price'] - indicators['bb_lower']) / (indicators['bb_upper'] - indicators['bb_lower'])
            if bb_position < 0.2:
                bullish_score += 10  # Near lower band
            elif bb_position > 0.8:
                bearish_score += 10  # Near upper band

            # Stochastic scoring (weight: 10)
            if indicators['stoch_k'] < 20 and indicators['stoch_k'] > indicators['stoch_d']:
                bullish_score += 10  # Oversold and crossing up
            elif indicators['stoch_k'] > 80 and indicators['stoch_k'] < indicators['stoch_d']:
                bearish_score += 10  # Overbought and crossing down

            # ADX and DI scoring (weight: 15)
            if indicators['adx'] > 25:  # Strong trend
                if indicators['plus_di'] > indicators['minus_di']:
                    bullish_score += 15
                else:
                    bearish_score += 15
            elif indicators['adx'] > 20:
                if indicators['plus_di'] > indicators['minus_di']:
                    bullish_score += 8
                else:
                    bearish_score += 8

            # Candlestick pattern scoring (weight: 10)
            for pattern in patterns['candlestick_patterns']:
                if pattern['signal'] == 'bullish':
                    bullish_score += min(pattern['strength'] / 10, 10)
                elif pattern['signal'] == 'bearish':
                    bearish_score += min(pattern['strength'] / 10, 10)

            # Chart pattern scoring (weight: 10)
            for pattern_name, pattern_data in patterns['chart_patterns'].items():
                if pattern_data['detected']:
                    confidence = pattern_data['confidence'] / 10
                    pattern_type = pattern_data.get('type')
                    if pattern_type == 'bullish':
                        bullish_score += confidence
                    elif pattern_type == 'bearish':
                        bearish_score += confidence

            # Trend scoring (weight: 5)
            if trend['direction'] == 'uptrend':
                bullish_score += 5
            elif trend['direction'] == 'downtrend':
                bearish_score += 5

            # Calculate total confidence (0-100 scale)
            total_score = bullish_score + bearish_score
            if total_score > 0:
                bullish_confidence = (bullish_score / total_score) * 100
                bearish_confidence = (bearish_score / total_score) * 100
                total_confidence = abs(bullish_confidence - bearish_confidence)
            else:
                bullish_confidence = 50.0
                bearish_confidence = 50.0
                total_confidence = 0.0

            logger.debug(f"Signal score - Bullish: {bullish_score:.2f}, Bearish: {bearish_score:.2f}, Confidence: {total_confidence:.2f}")

            return {
                'bullish_score': bullish_score,
                'bearish_score': bearish_score,
                'bullish_confidence': bullish_confidence,
                'bearish_confidence': bearish_confidence,
                'total_confidence': total_confidence
            }

        except Exception as e:
            logger.error(f"Error calculating signal score: {str(e)}")
            raise

    def _determine_signal_type(self, signal_score: Dict[str, float]) -> SignalType:
        """
        Determine signal type based on scores.

        Args:
            signal_score: Signal score dictionary

        Returns:
            SignalType: Determined signal type
        """
        try:
            bullish_score = signal_score['bullish_score']
            bearish_score = signal_score['bearish_score']
            confidence = signal_score['total_confidence']

            # Require minimum confidence
            if confidence < 30:
                return SignalType.NO_SIGNAL

            # Determine direction
            if bullish_score > bearish_score:
                if confidence >= 70:
                    return SignalType.STRONG_BUY
                elif confidence >= 50:
                    return SignalType.BUY
                else:
                    return SignalType.HOLD
            elif bearish_score > bullish_score:
                if confidence >= 70:
                    return SignalType.STRONG_SELL
                elif confidence >= 50:
                    return SignalType.SELL
                else:
                    return SignalType.HOLD
            else:
                return SignalType.HOLD

        except Exception as e:
            logger.error(f"Error determining signal type: {str(e)}")
            return SignalType.NO_SIGNAL

    def _calculate_levels(self,
                         signal_type: SignalType,
                         current_price: float,
                         indicators: Dict) -> Dict[str, float]:
        """
        Calculate stop loss and target levels.

        Args:
            signal_type: Type of signal
            current_price: Current market price
            indicators: Indicator values

        Returns:
            Dict with stop_loss, target_1, target_2, target_3
        """
        try:
            atr = indicators['atr']

            if signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
                # Buy signal levels
                stop_loss = current_price - (2 * atr)
                risk = current_price - stop_loss

                # Calculate targets with different risk/reward ratios
                target_1 = current_price + (2 * risk)  # 2:1 RR
                target_2 = current_price + (3 * risk)  # 3:1 RR
                target_3 = current_price + (4 * risk)  # 4:1 RR

                # Alternative: Use Bollinger Bands and support/resistance
                if indicators['bb_upper'] > target_1:
                    target_1 = min(target_1, indicators['bb_upper'] * 0.98)

            elif signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
                # Sell signal levels
                stop_loss = current_price + (2 * atr)
                risk = stop_loss - current_price

                # Calculate targets
                target_1 = current_price - (2 * risk)  # 2:1 RR
                target_2 = current_price - (3 * risk)  # 3:1 RR
                target_3 = current_price - (4 * risk)  # 4:1 RR

                # Alternative: Use Bollinger Bands
                if indicators['bb_lower'] < target_1:
                    target_1 = max(target_1, indicators['bb_lower'] * 1.02)

            else:
                # No signal or hold
                stop_loss = current_price
                target_1 = current_price
                target_2 = current_price
                target_3 = current_price

            return {
                'stop_loss': float(stop_loss),
                'target_1': float(target_1),
                'target_2': float(target_2),
                'target_3': float(target_3)
            }

        except Exception as e:
            logger.error(f"Error calculating levels: {str(e)}")
            raise

    def _compile_reasoning(self,
                          signal_score: Dict,
                          indicators: Dict,
                          patterns: Dict,
                          trend: Dict) -> List[str]:
        """
        Compile reasoning for the signal.

        Args:
            signal_score: Signal scores
            indicators: Indicator values
            patterns: Pattern analysis
            trend: Trend analysis

        Returns:
            List of reasoning strings
        """
        try:
            reasoning = []

            # Trend
            if trend['direction'] == 'uptrend':
                reasoning.append(f"Market in uptrend (ADX: {trend['strength']:.2f})")
            elif trend['direction'] == 'downtrend':
                reasoning.append(f"Market in downtrend (ADX: {trend['strength']:.2f})")
            else:
                reasoning.append(f"Market sideways (ADX: {trend['strength']:.2f})")

            # RSI
            if indicators['rsi'] < 30:
                reasoning.append(f"RSI oversold at {indicators['rsi']:.2f}")
            elif indicators['rsi'] > 70:
                reasoning.append(f"RSI overbought at {indicators['rsi']:.2f}")

            # MACD
            if indicators['macd'] > indicators['macd_signal']:
                reasoning.append("MACD bullish crossover")
            else:
                reasoning.append("MACD bearish crossover")

            # Moving averages
            if indicators['current_price'] > indicators['sma_20'] > indicators['sma_50']:
                reasoning.append("Price above both SMAs (bullish)")
            elif indicators['current_price'] < indicators['sma_20'] < indicators['sma_50']:
                reasoning.append("Price below both SMAs (bearish)")

            # Bollinger Bands
            bb_position = (indicators['current_price'] - indicators['bb_lower']) / (indicators['bb_upper'] - indicators['bb_lower'])
            if bb_position < 0.2:
                reasoning.append("Price near lower Bollinger Band")
            elif bb_position > 0.8:
                reasoning.append("Price near upper Bollinger Band")

            # Patterns
            if patterns['candlestick_patterns']:
                pattern_names = [p['name'] for p in patterns['candlestick_patterns']]
                reasoning.append(f"Candlestick patterns: {', '.join(pattern_names[:3])}")

            # Chart patterns
            detected_chart_patterns = [name for name, data in patterns['chart_patterns'].items() if data['detected']]
            if detected_chart_patterns:
                reasoning.append(f"Chart patterns: {', '.join(detected_chart_patterns)}")

            # Signal strength
            reasoning.append(f"Signal confidence: {signal_score['total_confidence']:.2f}%")

            return reasoning

        except Exception as e:
            logger.error(f"Error compiling reasoning: {str(e)}")
            return ["Error compiling reasoning"]

    def calculate_position_size(self,
                               account_balance: float,
                               entry_price: float,
                               stop_loss: float) -> Dict[str, float]:
        """
        Calculate position size based on risk management.

        Args:
            account_balance: Total account balance
            entry_price: Entry price for the trade
            stop_loss: Stop loss price

        Returns:
            Dict with position_size, risk_amount, and units

        Raises:
            ValueError: If parameters are invalid
        """
        try:
            if account_balance <= 0:
                raise ValueError(f"account_balance must be positive, got {account_balance}")

            if entry_price <= 0:
                raise ValueError(f"entry_price must be positive, got {entry_price}")

            # Calculate risk amount
            risk_amount = account_balance * (self.risk_percent / 100)

            # Calculate risk per unit
            risk_per_unit = abs(entry_price - stop_loss)

            if risk_per_unit == 0:
                raise ValueError("Stop loss cannot equal entry price")

            # Calculate number of units
            units = risk_amount / risk_per_unit

            # Calculate position size (total capital required)
            position_size = units * entry_price

            logger.debug(f"Position size: {units:.2f} units, ${position_size:.2f} total")

            return {
                'position_size': float(position_size),
                'risk_amount': float(risk_amount),
                'units': float(units),
                'risk_per_unit': float(risk_per_unit)
            }

        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            raise

    def backtest_signal(self, forward_periods: int = 20) -> Dict[str, Union[float, bool]]:
        """
        Backtest the signal on historical data.

        Args:
            forward_periods: Number of periods to look forward for validation

        Returns:
            Dict with backtest results

        Raises:
            ValueError: If insufficient data for backtesting
        """
        try:
            if len(self.data) < forward_periods + 1:
                raise ValueError(f"Insufficient data for backtesting. Need {forward_periods + 1} periods")

            # Generate signal on historical data (excluding last forward_periods)
            historical_data = self.data.iloc[:-forward_periods].copy()
            historical_generator = SignalGenerator(historical_data, self.risk_percent)
            signal = historical_generator.generate_signal()

            # Evaluate signal performance on forward data
            forward_data = self.data.iloc[-forward_periods:]

            entry_price = signal.entry_price
            stop_loss = signal.stop_loss
            target_1 = signal.target_1

            hit_target = False
            hit_stop = False
            max_gain = 0.0
            max_loss = 0.0

            for idx, row in forward_data.iterrows():
                high = row['high']
                low = row['low']

                if signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
                    # Check if target hit
                    if high >= target_1:
                        hit_target = True
                        max_gain = (target_1 - entry_price) / entry_price * 100
                        break

                    # Check if stop hit
                    if low <= stop_loss:
                        hit_stop = True
                        max_loss = (stop_loss - entry_price) / entry_price * 100
                        break

                    # Track max gain/loss
                    current_gain = (high - entry_price) / entry_price * 100
                    current_loss = (low - entry_price) / entry_price * 100
                    max_gain = max(max_gain, current_gain)
                    max_loss = min(max_loss, current_loss)

                elif signal.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
                    # Check if target hit
                    if low <= target_1:
                        hit_target = True
                        max_gain = (entry_price - target_1) / entry_price * 100
                        break

                    # Check if stop hit
                    if high >= stop_loss:
                        hit_stop = True
                        max_loss = (entry_price - stop_loss) / entry_price * 100
                        break

                    # Track max gain/loss
                    current_gain = (entry_price - low) / entry_price * 100
                    current_loss = (entry_price - high) / entry_price * 100
                    max_gain = max(max_gain, current_gain)
                    max_loss = min(max_loss, current_loss)

            # Calculate final P&L
            if hit_target:
                result = 'target_hit'
                pnl = max_gain
            elif hit_stop:
                result = 'stop_hit'
                pnl = max_loss
            else:
                result = 'open'
                final_price = forward_data['close'].iloc[-1]
                if signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
                    pnl = (final_price - entry_price) / entry_price * 100
                elif signal.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
                    pnl = (entry_price - final_price) / entry_price * 100
                else:
                    pnl = 0.0

            logger.debug(f"Backtest result: {result}, P&L: {pnl:.2f}%")

            return {
                'result': result,
                'hit_target': hit_target,
                'hit_stop': hit_stop,
                'pnl_percent': float(pnl),
                'max_gain_percent': float(max_gain),
                'max_loss_percent': float(max_loss),
                'signal_type': signal.signal_type.value,
                'signal_confidence': float(signal.confidence)
            }

        except Exception as e:
            logger.error(f"Error in backtesting: {str(e)}")
            raise
