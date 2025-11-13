"""
Technical Indicator Parameters and Configurations
"""

# Moving Averages
MA_SETTINGS = {
    "fast_period": 9,      # Fast MA period
    "medium_period": 21,   # Medium MA period
    "slow_period": 50,     # Slow MA period
    "very_slow_period": 200,  # Very slow MA period
    "type": "EMA"          # MA type: SMA, EMA, WMA, DEMA, TEMA
}

# Exponential Moving Averages (EMA)
EMA_SETTINGS = {
    "short_period": 9,
    "medium_period": 21,
    "long_period": 50,
    "very_long_period": 200
}

# Simple Moving Averages (SMA)
SMA_SETTINGS = {
    "short_period": 10,
    "medium_period": 20,
    "long_period": 50,
    "very_long_period": 200
}

# Relative Strength Index (RSI)
RSI_SETTINGS = {
    "period": 14,           # Standard RSI period
    "overbought": 70,       # Overbought threshold
    "oversold": 30,         # Oversold threshold
    "extreme_overbought": 80,  # Extreme overbought
    "extreme_oversold": 20     # Extreme oversold
}

# Moving Average Convergence Divergence (MACD)
MACD_SETTINGS = {
    "fast_period": 12,      # Fast EMA period
    "slow_period": 26,      # Slow EMA period
    "signal_period": 9,     # Signal line period
    "histogram_threshold": 0  # Threshold for histogram signals
}

# Bollinger Bands
BOLLINGER_SETTINGS = {
    "period": 20,           # Moving average period
    "std_dev": 2.0,         # Number of standard deviations
    "ma_type": "SMA"        # Moving average type
}

# Average True Range (ATR)
ATR_SETTINGS = {
    "period": 14,           # Standard ATR period
    "multiplier": 2.0       # Multiplier for stop loss calculation
}

# Stochastic Oscillator
STOCHASTIC_SETTINGS = {
    "k_period": 14,         # %K period
    "d_period": 3,          # %D period (smoothing)
    "smooth_k": 3,          # %K smoothing
    "overbought": 80,       # Overbought level
    "oversold": 20          # Oversold level
}

# Average Directional Index (ADX)
ADX_SETTINGS = {
    "period": 14,           # ADX period
    "strong_trend": 25,     # Strong trend threshold
    "very_strong_trend": 50  # Very strong trend threshold
}

# Commodity Channel Index (CCI)
CCI_SETTINGS = {
    "period": 20,           # CCI period
    "overbought": 100,      # Overbought level
    "oversold": -100,       # Oversold level
    "extreme_overbought": 200,  # Extreme overbought
    "extreme_oversold": -200    # Extreme oversold
}

# Parabolic SAR
PSAR_SETTINGS = {
    "acceleration": 0.02,   # Acceleration factor
    "maximum": 0.2          # Maximum acceleration
}

# On-Balance Volume (OBV)
OBV_SETTINGS = {
    "signal_period": 10     # Signal line period
}

# Ichimoku Cloud
ICHIMOKU_SETTINGS = {
    "conversion_period": 9,    # Tenkan-sen period
    "base_period": 26,         # Kijun-sen period
    "span_b_period": 52,       # Senkou Span B period
    "displacement": 26         # Chikou Span displacement
}

# Fibonacci Retracement Levels
FIBONACCI_LEVELS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]

# Support and Resistance
SUPPORT_RESISTANCE_SETTINGS = {
    "lookback_period": 50,     # Candles to look back
    "min_touches": 2,          # Minimum touches to confirm level
    "tolerance": 0.001         # Tolerance for level matching (percentage)
}

# Volume Analysis
VOLUME_SETTINGS = {
    "average_period": 20,      # Period for average volume
    "high_volume_multiplier": 1.5,  # High volume threshold
    "low_volume_multiplier": 0.5    # Low volume threshold
}

# Volatility Settings
VOLATILITY_SETTINGS = {
    "period": 20,              # Period for volatility calculation
    "high_volatility_threshold": 1.5,  # High volatility threshold (ATR ratio)
    "low_volatility_threshold": 0.5    # Low volatility threshold (ATR ratio)
}

# Pattern Recognition Settings
PATTERN_SETTINGS = {
    "min_bars": 3,             # Minimum bars for pattern
    "max_bars": 20,            # Maximum bars for pattern
    "tolerance": 0.02          # Pattern matching tolerance (percentage)
}

# Trend Detection
TREND_SETTINGS = {
    "period": 20,              # Period for trend analysis
    "strength_threshold": 0.7   # Trend strength threshold
}

# Signal Weighting (for combined signals)
SIGNAL_WEIGHTS = {
    "trend": 0.30,             # Trend indicators weight
    "momentum": 0.25,          # Momentum indicators weight
    "volatility": 0.15,        # Volatility indicators weight
    "volume": 0.15,            # Volume indicators weight
    "pattern": 0.15            # Pattern recognition weight
}

# Risk Management
RISK_SETTINGS = {
    "default_risk_percent": 1.0,  # Default risk per trade (% of capital)
    "max_risk_percent": 2.0,      # Maximum risk per trade
    "min_risk_reward": 1.5,       # Minimum risk/reward ratio
    "optimal_risk_reward": 2.0,   # Optimal risk/reward ratio
    "stop_loss_atr_multiplier": 2.0,  # Stop loss distance (ATR multiplier)
    "take_profit_atr_multiplier": 4.0  # Take profit distance (ATR multiplier)
}

# Timeframes for multi-timeframe analysis
TIMEFRAMES = {
    "M1": "1 minute",
    "M5": "5 minutes",
    "M15": "15 minutes",
    "M30": "30 minutes",
    "H1": "1 hour",
    "H4": "4 hours",
    "D": "Daily"
}

# Default timeframe
DEFAULT_TIMEFRAME = "M1"

# Indicator combinations for signal generation
SIGNAL_COMBINATIONS = {
    "trend_following": ["MA", "MACD", "ADX"],
    "momentum": ["RSI", "STOCHASTIC", "CCI"],
    "volatility_breakout": ["BOLLINGER", "ATR", "VOLUME"],
    "combined": ["MA", "RSI", "MACD", "BOLLINGER", "ATR"]
}
