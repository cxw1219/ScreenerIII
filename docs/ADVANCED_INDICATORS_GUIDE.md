# Advanced Technical Indicators Guide

## Overview

The `AdvancedIndicators` class in `/home/user/ScreenerIII/src/analysis/advanced_indicators.py` provides sophisticated technical analysis tools for professional trading and market analysis. This module extends the basic indicators with advanced techniques used by institutional traders.

## Features Implemented

### 1. Ichimoku Cloud (一目均衡表)

A comprehensive Japanese indicator showing support/resistance, trend direction, and momentum.

**Components:**
- **Tenkan-sen (Conversion Line)**: 9-period midpoint - fast signal line
- **Kijun-sen (Base Line)**: 26-period midpoint - slow signal line
- **Senkou Span A (Leading Span A)**: Average of Tenkan and Kijun, projected 26 periods forward
- **Senkou Span B (Leading Span B)**: 52-period midpoint, projected 26 periods forward
- **Chikou Span (Lagging Span)**: Current close projected 26 periods backward

**Signal Generation:**
- Price vs Cloud position (above/below/in cloud)
- TK Cross (Tenkan crossing Kijun)
- Cloud color (green when Span A > Span B)
- Cloud thickness (volatility measure)
- Lagging span confirmation

**Usage:**
```python
from src.analysis.advanced_indicators import AdvancedIndicators

# Initialize with OHLCV data
adv_ind = AdvancedIndicators(data)

# Calculate Ichimoku components
ichimoku = adv_ind.calculate_ichimoku()

# Generate trading signals
signals = adv_ind.generate_ichimoku_signals(ichimoku)
print(f"Trend: {signals.trend.value}")
print(f"Price vs Cloud: {signals.price_vs_cloud}")
print(f"Strength: {signals.strength:.1f}%")
print(f"Cloud Color: {signals.cloud_color}")
```

### 2. Volume Profile

Distribution of traded volume across price levels, identifying key support/resistance areas.

**Features:**
- **POC (Point of Control)**: Price level with highest volume
- **Value Area**: Price range containing 70% of volume
- **HVN (High Volume Nodes)**: Strong support/resistance levels
- **LVN (Low Volume Nodes)**: Weak areas, potential breakout zones
- **Volume Delta**: Net buying/selling pressure

**Usage:**
```python
# Calculate volume profile
vp = adv_ind.calculate_volume_profile(num_bins=50, value_area_pct=0.70)

print(f"POC: ${vp.poc:.2f}")
print(f"Value Area: ${vp.value_area_low:.2f} - ${vp.value_area_high:.2f}")
print(f"Volume Delta: {vp.volume_delta:,.0f}")
print(f"HVN Levels: {vp.hvn_levels}")
print(f"LVN Levels: {vp.lvn_levels}")

# Access detailed profile
profile_df = vp.profile  # Contains price_level, volume, percentage
```

### 3. Market Profile (TPO - Time Price Opportunity)

Time-based price distribution showing where market spent most time.

**Components:**
- **POC**: Price with most time spent
- **Value Area**: 70% of time distribution
- **Initial Balance**: Range during first trading hours
- **TPO Count**: Time periods at each price level

**Usage:**
```python
# Calculate market profile
mp = adv_ind.calculate_market_profile(
    num_bins=50,
    value_area_pct=0.70,
    initial_balance_hours=2
)

print(f"POC: ${mp.poc:.2f}")
print(f"Value Area: ${mp.value_area_low:.2f} - ${mp.value_area_high:.2f}")
print(f"Initial Balance: ${mp.initial_balance_low:.2f} - ${mp.initial_balance_high:.2f}")

# Access TPO profile
tpo_profile = mp.profile  # Contains price_level, tpo_count, percentage
```

### 4. Order Flow Indicators

Institutional-level order flow analysis for detecting smart money activity.

**Indicators:**
- **Delta**: Buy volume - Sell volume per bar
- **Cumulative Delta**: Running total of delta (trend of buying/selling)
- **Bid/Ask Imbalance**: Ratio of buying to selling pressure
- **Absorption Detection**: Large orders being filled without price movement

**Usage:**
```python
# Calculate order flow
of = adv_ind.calculate_order_flow(absorption_threshold=2.0)

print(f"Current Delta: {of.delta.iloc[-1]:,.0f}")
print(f"Cumulative Delta: {of.cumulative_delta.iloc[-1]:,.0f}")
print(f"Imbalance Ratio: {of.imbalance_ratio.iloc[-1]:.2f}")

# Check for absorption
if of.absorption_detected.iloc[-1]:
    print("Absorption detected - large orders being filled!")

# Add to DataFrame
data['delta'] = of.delta
data['cum_delta'] = of.cumulative_delta
```

### 5. Advanced Volatility Indicators

#### Keltner Channels
ATR-based channels around EMA, superior to Bollinger Bands for trending markets.

```python
keltner = adv_ind.calculate_keltner_channels(
    ema_period=20,
    atr_period=10,
    atr_multiplier=2.0
)

# Use for breakout trading
current_price = data['close'].iloc[-1]
if current_price > keltner['keltner_upper'].iloc[-1]:
    print("Breakout above upper channel!")
```

#### Donchian Channels
Highest high and lowest low over period - classic breakout indicator.

```python
donchian = adv_ind.calculate_donchian_channels(period=20)

# Turtle Trading System uses 20-period Donchian
if data['close'].iloc[-1] > donchian['donchian_upper'].iloc[-1]:
    print("Turtle Buy Signal!")
```

#### Advanced ADX
Enhanced ADX with trend strength classification.

```python
adx = adv_ind.calculate_adx_refined(period=14)

print(f"ADX: {adx['ADX'].iloc[-1]:.2f}")
print(f"Trend Strength: {adx['trend_strength'].iloc[-1]}")  # weak/moderate/strong

# Directional movement
if adx['PLUS_DI'].iloc[-1] > adx['MINUS_DI'].iloc[-1]:
    print("Upward directional movement")
```

#### Chaikin Volatility
Rate of change of trading range - identifies volatility expansions/contractions.

```python
chaikin = adv_ind.calculate_chaikin_volatility(ema_period=10, roc_period=10)

if chaikin.iloc[-1] > 0:
    print("Volatility expanding")
else:
    print("Volatility contracting")
```

### 6. Elliott Wave Detection (Simplified)

Automated detection of Elliott Wave patterns using pivot analysis and Fibonacci relationships.

**Features:**
- Impulse wave detection (1-2-3-4-5)
- Corrective wave detection (A-B-C)
- Fibonacci relationship analysis
- Confidence scoring

**Usage:**
```python
# Detect Elliott Waves
waves = adv_ind.detect_elliott_waves(
    min_wave_size=0.02,  # 2% minimum
    max_wave_size=0.5    # 50% maximum
)

print(f"Wave Type: {waves['wave_type'].value}")
print(f"Confidence: {waves['confidence']:.1f}%")
print(f"Pivots Detected: {len(waves['pivots'])}")

# Check Fibonacci relationships
for rel in waves['fibonacci_relationships']:
    if rel['match']:
        print(f"Wave {rel['wave_a']} to {rel['wave_b']}: "
              f"Ratio {rel['ratio']:.3f} matches Fib {rel['fibonacci']}")
```

### 7. Advanced Momentum Oscillators

#### Williams %R
Fast momentum indicator, inverse of Stochastic. Range: -100 to 0.

```python
williams = adv_ind.calculate_williams_r(period=14)

if williams.iloc[-1] > -20:
    print("Overbought - above -20")
elif williams.iloc[-1] < -80:
    print("Oversold - below -80")
```

#### Ultimate Oscillator
Multi-timeframe momentum oscillator reducing false signals.

```python
ultosc = adv_ind.calculate_ultimate_oscillator(
    period1=7,   # Short
    period2=14,  # Medium
    period3=28   # Long
)

if ultosc.iloc[-1] > 70:
    print("Overbought")
elif ultosc.iloc[-1] < 30:
    print("Oversold")
```

#### Money Flow Index (MFI)
Volume-weighted RSI - "RSI with volume".

```python
mfi = adv_ind.calculate_mfi(period=14)

if mfi.iloc[-1] > 80:
    print("Strong overbought with volume confirmation")
elif mfi.iloc[-1] < 20:
    print("Strong oversold with volume confirmation")
```

#### Rate of Change (ROC)
Momentum indicator showing percentage price change.

```python
roc = adv_ind.calculate_roc(period=10)

if roc.iloc[-1] > 0:
    print(f"Positive momentum: +{roc.iloc[-1]:.2f}%")
else:
    print(f"Negative momentum: {roc.iloc[-1]:.2f}%")
```

## Complete Integration Example

```python
import pandas as pd
from src.analysis.advanced_indicators import AdvancedIndicators

# Load your OHLCV data
data = pd.read_csv('price_data.csv')  # Must have: open, high, low, close, volume

# Initialize
adv_ind = AdvancedIndicators(data)

# Calculate all indicators at once
all_indicators = adv_ind.calculate_all_advanced_indicators()

# Now you have a DataFrame with all original data plus:
# - Ichimoku components (tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b, chikou_span)
# - Keltner Channels (keltner_upper, keltner_middle, keltner_lower)
# - Donchian Channels (donchian_upper, donchian_middle, donchian_lower)
# - Advanced ADX (ADX, PLUS_DI, MINUS_DI, DI_diff)
# - Chaikin Volatility (chaikin_volatility)
# - Momentum Oscillators (williams_r, ultimate_oscillator, mfi, roc)
# - Order Flow (delta, cumulative_delta, imbalance_ratio, absorption)

print(f"Original columns: {len(data.columns)}")
print(f"With indicators: {len(all_indicators.columns)}")
print(f"New indicators: {len(all_indicators.columns) - len(data.columns)}")

# Access specific indicators
latest = all_indicators.iloc[-1]
print(f"Latest Ichimoku Tenkan: {latest['tenkan_sen']:.2f}")
print(f"Latest Williams %R: {latest['williams_r']:.2f}")
print(f"Latest MFI: {latest['mfi']:.2f}")
```

## Visualization Support

The module includes helpers for visualization:

```python
# Get formatted data for plotting
viz_data = adv_ind.get_visualization_data('ichimoku')
# Returns: dates, price, and all Ichimoku components

viz_data = adv_ind.get_visualization_data('volume_profile')
# Returns: profile DataFrame, POC, Value Area, HVN/LVN levels

viz_data = adv_ind.get_visualization_data('market_profile')
# Returns: TPO profile, POC, Value Area, Initial Balance

viz_data = adv_ind.get_visualization_data('keltner')
# Returns: dates, price, upper/middle/lower channels

viz_data = adv_ind.get_visualization_data('donchian')
# Returns: dates, price, upper/middle/lower channels
```

## Trading Strategy Examples

### 1. Ichimoku Cloud Breakout
```python
ichimoku = adv_ind.calculate_ichimoku()
signals = adv_ind.generate_ichimoku_signals(ichimoku)

if (signals.price_vs_cloud == 'above' and
    signals.cloud_color == 'green' and
    signals.tk_cross == 'bullish' and
    signals.lagging_span_confirmation):
    print("STRONG BUY SIGNAL")
```

### 2. Volume Profile Support/Resistance
```python
vp = adv_ind.calculate_volume_profile()
current_price = data['close'].iloc[-1]

# Trading at POC - high probability bounce
if abs(current_price - vp.poc) / current_price < 0.005:  # Within 0.5%
    print("Price at POC - expect support/resistance")

# Price at LVN - potential quick move through area
if any(abs(current_price - lvn) / current_price < 0.005 for lvn in vp.lvn_levels):
    print("Price at LVN - low resistance area, potential breakout")
```

### 3. Order Flow Divergence
```python
of = adv_ind.calculate_order_flow()

# Price making new highs but cumulative delta declining
if (data['close'].iloc[-1] > data['close'].iloc[-20:].max() and
    of.cumulative_delta.iloc[-1] < of.cumulative_delta.iloc[-20]):
    print("BEARISH DIVERGENCE - Smart money selling into rally")
```

### 4. Multi-Indicator Confluence
```python
# Combine multiple indicators for high-probability setups
ichimoku = adv_ind.calculate_ichimoku()
signals = adv_ind.generate_ichimoku_signals(ichimoku)
mfi = adv_ind.calculate_mfi()
williams = adv_ind.calculate_williams_r()
adx = adv_ind.calculate_adx_refined()

# Strong trending buy setup
if (signals.trend.value == 'bullish' and
    adx['trend_strength'].iloc[-1] == 'strong' and
    mfi.iloc[-1] < 30 and
    williams.iloc[-1] < -80):
    print("HIGH PROBABILITY BUY SETUP")
    print("- Strong uptrend confirmed (Ichimoku + ADX)")
    print("- Oversold conditions (MFI + Williams)")
```

## Performance Considerations

1. **Data Requirements:**
   - Minimum 52 bars for Ichimoku (for Senkou Span B)
   - More data = better Elliott Wave detection
   - Volume data required for Volume Profile and Order Flow

2. **Calculation Speed:**
   - Ichimoku: Fast
   - Volume Profile: Moderate (depends on num_bins)
   - Market Profile: Moderate
   - Elliott Wave: Slower (complex pattern detection)
   - All others: Fast (TA-Lib optimized)

3. **Memory Usage:**
   - Volume/Market Profile stores histogram data
   - Elliott Wave stores pivot and wave data
   - Use calculate_all_advanced_indicators() carefully with large datasets

## Data Requirements

### Minimum Required Columns
```python
required = ['open', 'high', 'low', 'close', 'volume']
```

### Optional for Enhanced Order Flow
```python
optional = ['buy_volume', 'sell_volume']  # For accurate delta calculation
```

### DataFrame Format
```python
data = pd.DataFrame({
    'open': [...],
    'high': [...],
    'low': [...],
    'close': [...],
    'volume': [...],
    # Optional:
    'buy_volume': [...],
    'sell_volume': [...]
}, index=pd.DatetimeIndex([...]))
```

## Error Handling

All methods include comprehensive error handling:

```python
try:
    ichimoku = adv_ind.calculate_ichimoku()
except ValueError as e:
    # Insufficient data or invalid parameters
    print(f"Configuration error: {e}")
except Exception as e:
    # Calculation error
    print(f"Calculation error: {e}")
```

## Integration with Basic Indicators

Combine with the basic TechnicalIndicators class:

```python
from src.analysis.indicators import TechnicalIndicators
from src.analysis.advanced_indicators import AdvancedIndicators

# Basic indicators
basic = TechnicalIndicators(data)
rsi = basic.calculate_rsi()
macd = basic.calculate_macd()
bollinger = basic.calculate_bollinger_bands()

# Advanced indicators
advanced = AdvancedIndicators(data)
ichimoku = advanced.calculate_ichimoku()
vp = advanced.calculate_volume_profile()
mfi = advanced.calculate_mfi()

# Combine for comprehensive analysis
if (rsi.iloc[-1] < 30 and  # Basic RSI oversold
    mfi.iloc[-1] < 20 and  # Advanced MFI oversold
    data['close'].iloc[-1] < vp.value_area_low):  # Below value area
    print("STRONG OVERSOLD SIGNAL from multiple indicators")
```

## Technical Details

### Ichimoku Cloud Color
- **Green (Bullish)**: Senkou Span A > Senkou Span B
- **Red (Bearish)**: Senkou Span A < Senkou Span B

### Volume Profile Calculation
Uses histogram method with configurable bins. Each bar's volume is distributed across the price range it touched.

### Market Profile (TPO) Calculation
Each time period adds one TPO count to all price levels touched. The POC is the price level with the most TPO counts.

### Elliott Wave Algorithm
1. Find pivot points (local extrema)
2. Identify waves between pivots
3. Check for impulse/corrective patterns
4. Calculate Fibonacci relationships
5. Score pattern confidence

## References and Further Reading

- **Ichimoku**: "Ichimoku Charts" by Nicole Elliott
- **Volume Profile**: "Mind Over Markets" by James Dalton
- **Market Profile**: "Markets in Profile" by James Dalton
- **Order Flow**: "A Complete Guide to Volume Price Analysis" by Anna Coulling
- **Elliott Wave**: "Elliott Wave Principle" by Frost & Prechter

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
1. Check the docstrings in the source code
2. Review the example_usage() function in advanced_indicators.py
3. Run the test suite: `python test_advanced_indicators.py`

---

**Created**: 2025-11-13
**Version**: 1.0.0
**Module**: /home/user/ScreenerIII/src/analysis/advanced_indicators.py
