# ScreenerIII Signal Generation Logic

## Overview

Signal generation in ScreenerIII is a multi-layered process that combines technical analysis indicators, pattern recognition, risk assessment, and market context to generate actionable trading signals. Each signal is assigned a confidence level and validated against risk/reward criteria.

## Signal Types

### Primary Signals

1. **BUY Signal**
   - Indicates uptrend with bullish indicators aligned
   - Generated when: Price is in uptrend AND momentum is positive AND volatility supports entry
   - Entry: At market or limit above current price
   - Target: Calculated using ATR-based take profit multiplier
   - Stop Loss: Calculated using ATR-based stop loss multiplier

2. **SELL Signal**
   - Indicates downtrend with bearish indicators aligned
   - Generated when: Price is in downtrend AND momentum is negative AND volatility supports entry
   - Entry: At market or limit below current price
   - Target: Calculated using ATR-based take profit multiplier
   - Stop Loss: Calculated using ATR-based stop loss multiplier

3. **HOLD Signal**
   - Neutral position, no clear directional bias
   - Generated when: Indicators are mixed OR confidence is below threshold
   - Action: Wait for clearer signal setup

## Indicator-Based Signal Generation

### Trend Indicators (30% Weight)

#### Moving Average Crossover
```
Fast MA (9-period) > Medium MA (21-period) > Slow MA (50-period) = UPTREND
Fast MA (9-period) < Medium MA (21-period) < Slow MA (50-period) = DOWNTREND
Otherwise = No clear trend
```

**Signal Generation**:
- BUY: Fast MA crosses above Medium MA while in uptrend
- SELL: Fast MA crosses below Medium MA while in downtrend
- Confidence: +10% for each MA aligned in correct direction

#### Average Directional Index (ADX)
```
ADX < 25: Weak trend (reduce confidence)
25 < ADX < 50: Strong trend (maintain confidence)
ADX > 50: Very strong trend (increase confidence)
```

**Signal Modifier**:
- ADX > 50: Confidence +20%
- ADX > 25: Confidence +10%
- ADX < 25: Confidence -15% (weak trend environment)

### Momentum Indicators (25% Weight)

#### Relative Strength Index (RSI)
```
Configuration: 14-period
Levels: Oversold (30), Overbought (70)
```

**Signal Rules**:
- BUY when:
  - RSI crosses above 30 (oversold) = Bullish divergence
  - RSI < 50 and price making higher lows = Hidden bullish divergence
  - Confidence: 15-30% depending on level

- SELL when:
  - RSI crosses below 70 (overbought) = Bearish divergence
  - RSI > 50 and price making lower highs = Hidden bearish divergence
  - Confidence: 15-30% depending on level

#### MACD (Moving Average Convergence Divergence)
```
Configuration: Fast 12, Slow 26, Signal 9
```

**Signal Rules**:
- BUY when:
  - MACD line crosses above Signal line = Momentum shift to positive
  - MACD histogram turns positive = Increasing bullish momentum
  - Confidence: 15-25%

- SELL when:
  - MACD line crosses below Signal line = Momentum shift to negative
  - MACD histogram turns negative = Increasing bearish momentum
  - Confidence: 15-25%

#### Stochastic Oscillator
```
Configuration: %K=14, %D=3, Smooth=3
Levels: Oversold (20), Overbought (80)
```

**Signal Rules**:
- BUY when:
  - %K crosses above %D in oversold region (< 20) = Strong reversal
  - %K > 50 and rising = Momentum building
  - Confidence: 10-20%

- SELL when:
  - %K crosses below %D in overbought region (> 80) = Strong reversal
  - %K < 50 and falling = Momentum weakening
  - Confidence: 10-20%

#### Commodity Channel Index (CCI)
```
Configuration: 20-period
Levels: Oversold (-100), Overbought (100)
```

**Signal Rules**:
- BUY when:
  - CCI crosses above -100 (extreme oversold) = Mean reversion
  - CCI crosses above 0 and rising = Positive momentum
  - Confidence: 10-15%

- SELL when:
  - CCI crosses below 100 (extreme overbought) = Mean reversion
  - CCI crosses below 0 and falling = Negative momentum
  - Confidence: 10-15%

### Volatility Indicators (15% Weight)

#### Bollinger Bands
```
Configuration: 20-period SMA, 2 standard deviations
```

**Signal Rules**:
- BUY when:
  - Price bounces off lower band and reverses upward
  - Price breaks above upper band (breakout) = Strong momentum
  - Confidence: 10-20%

- SELL when:
  - Price bounces off upper band and reverses downward
  - Price breaks below lower band (breakout) = Strong momentum
  - Confidence: 10-20%

#### Average True Range (ATR)
```
Configuration: 14-period
```

**Signal Modifier**:
- High volatility (ATR > average + 1 std dev):
  - Reduce confidence by 10%
  - Use wider stop losses and take profits

- Low volatility (ATR < average - 1 std dev):
  - Reduce confidence by 5%
  - Expect smaller moves

**Stop Loss & Take Profit Calculation**:
```
Stop Loss Distance = ATR × Stop Loss Multiplier (2.0)
Take Profit Distance = ATR × Take Profit Multiplier (4.0)

Example (XAU_USD with ATR = 10):
  Stop Loss = 10 × 2.0 = 20 pips
  Take Profit = 10 × 4.0 = 40 pips
  Risk/Reward = 40/20 = 2.0:1
```

### Volume Indicators (15% Weight)

#### Volume Analysis
```
Configuration: 20-period average volume
```

**Signal Rules**:
- BUY when:
  - Price increases with volume > 1.5 × average = Confirmation
  - Confidence: +5%

- SELL when:
  - Price decreases with volume > 1.5 × average = Confirmation
  - Confidence: +5%

- Low volume signals:
  - Volume < 0.5 × average = Reduce confidence by 10%

### Pattern Recognition (15% Weight)

#### Candlestick Patterns

**Bullish Patterns**:
- Hammer: Small body near bottom with long lower wick
- Engulfing: White candle completely engulfs previous black candle
- Confidence: 20%

**Bearish Patterns**:
- Hanging Man: Small body near top with long lower wick
- Engulfing: Black candle completely engulfs previous white candle
- Confidence: 20%

#### Support and Resistance
```
Configuration: 50-candle lookback, minimum 2 touches
```

**Signal Rules**:
- BUY at support level:
  - Price bounces from established support
  - Confidence: +15%

- SELL at resistance level:
  - Price bounces from established resistance
  - Confidence: +15%

- Breakout signals:
  - Price breaks key support/resistance = Strong momentum
  - Confidence: +20%

#### Fibonacci Retracement Levels
```
Levels: 23.6%, 38.2%, 50%, 61.8%, 78.6%
```

**Signal Rules**:
- BUY at Fibonacci support levels (61.8%, 50%, 38.2%)
- SELL at Fibonacci resistance levels
- Confidence: +10% when price bounces from level

## Combined Signal Generation

### Weighted Scoring System

Overall signal confidence is calculated using weighted average:

```
Total Score = (Trend Weight × Trend Score) +
              (Momentum Weight × Momentum Score) +
              (Volatility Weight × Volatility Score) +
              (Volume Weight × Volume Score) +
              (Pattern Weight × Pattern Score)

Where:
  Trend Weight = 0.30
  Momentum Weight = 0.25
  Volatility Weight = 0.15
  Volume Weight = 0.15
  Pattern Weight = 0.15
  Total Weight = 1.00
```

### Signal Confidence Calculation

```
Base Confidence = Weighted Score × 100

Modifiers:
  + Agreement bonus: +5% if all indicators align
  + ADX strength bonus: +0-20% based on ADX value
  - Volatility penalty: -0-15% if volatility is extreme
  - Volume penalty: -0-10% if volume is low

Final Confidence = Base Confidence + Modifiers
Minimum = 0%, Maximum = 100%
```

### Signal Threshold

```
Confidence >= 60% : Generate signal (BUY or SELL)
Confidence < 60% : HOLD signal (no entry)

High Confidence: >= 75% - Aggressive entry size
Medium Confidence: 60-75% - Standard entry size
Low Confidence: < 60% - No entry
```

## Risk/Reward Validation

Each signal is validated against risk/reward criteria:

```
Risk/Reward Ratio = Take Profit Distance / Stop Loss Distance

Minimum Acceptable: 1.5:1
Optimal Ratio: 2.0:1 or higher

Signal Rejection:
  If Risk/Reward < 1.5:1 : Signal rejected (too much risk)

Signal Enhancement:
  If Risk/Reward > 2.5:1 : Confidence +10% (good reward potential)
```

## Trend Validation

Signals are validated against the current trend:

### Strong Trend (ADX > 50)
- BUY signals: Require uptrend confirmation
- SELL signals: Require downtrend confirmation
- Confidence adjustment: +10%

### Moderate Trend (25 < ADX < 50)
- BUY/SELL signals: Normal validation
- Confidence adjustment: 0%

### Weak Trend (ADX < 25)
- BUY/SELL signals: Require stronger confirmation
- Confidence adjustment: -15%
- Consider range-trading strategies instead

## Multi-Timeframe Analysis

Signals are validated across multiple timeframes:

```
Timeframes Used:
  - M1 (1-minute): Short-term signals, quick entries
  - M5 (5-minute): Medium-term context
  - H1 (1-hour): Long-term trend direction

Validation:
  1. Check 1-hour trend (overall direction)
  2. Check 5-minute confirmation
  3. Check 1-minute entry

  If all three align: Confidence +20%
  If one disagrees: Confidence -10%
  If two disagree: Signal rejected
```

## Signal Quality Metrics

### Win Rate Tracking

```
Win Rate = (Winning Trades / Total Trades) × 100%

Evaluation:
  > 55%: Excellent signal quality
  50-55%: Good signal quality
  45-50%: Acceptable signal quality
  < 45%: Poor signal quality, needs refinement
```

### Profit Factor

```
Profit Factor = Gross Profit / Gross Loss

Evaluation:
  > 1.5: Excellent
  1.25-1.5: Good
  1.0-1.25: Acceptable
  < 1.0: Losing strategy
```

### Average Risk/Reward

```
Monitor the actual ratio of realized trades:
  > 2.0: Excellent
  1.5-2.0: Good
  1.0-1.5: Acceptable
  < 1.0: Risk > Reward
```

## Signal Modifications and Context

### Market Session Impact

Different market sessions have different characteristics:

```
Asian Session (21:00-07:00 UTC):
  - Lower volatility, lower volume
  - Reduce confidence by 10%
  - Wider spreads

European Session (07:00-15:00 UTC):
  - Higher volatility, higher volume
  - Confidence unchanged
  - Tighter spreads

US Session (12:00-21:00 UTC):
  - Highest volatility, highest volume
  - Confidence +5%
  - Most active trading
```

### Economic Event Impact

During high-impact economic events (NFP, FOMC, ECB decisions):
- Increase volatility modifier
- Widen stop losses
- Reduce position sizes
- Consider delaying entries

### Holiday and Weekend Effects

- Reduced liquidity on weekends
- Avoid signals during market gaps
- Be cautious after holidays

## Signal Filtering and Refinement

### False Signal Reduction

```
1. Multi-bar confirmation:
   - Wait for 2-3 bars confirming signal direction
   - Reduces false breakouts

2. Confluence validation:
   - Multiple indicators must align
   - Test against support/resistance levels
   - Compare with longer timeframes

3. Volume confirmation:
   - Require volume > average on signal candle
   - Stronger signal if volume increases

4. Pattern confirmation:
   - Only trade recognized patterns
   - Require proper pattern formation
```

### Signal Invalidation

Signals are invalidated when:
```
1. Price breaks the stop loss level
2. Trend reversal occurs (ADX reverses)
3. Pattern breaks before profit target
4. Conflicting signal on higher timeframe
5. Adverse news or economic data
```

## Real-Time Signal Updates

### Update Frequency
```
Signal recalculation: Every new candle close
  - M1 candles: Recalculate every minute
  - Check for new BUY/SELL/HOLD

Alert generation: When signal changes
  - Trigger notification to user
  - Log signal to database
  - Record entry time and price
```

## Signal Output Format

### Console Display
```
[14:35:22] GOLD (XAU_USD)
  Signal: BUY
  Confidence: 78%
  Entry: 2025.60
  Target: 2065.60 (+40.00 pips)
  Stop: 2005.60 (-20.00 pips)
  Risk/Reward: 2.0:1
  Status: ACTIVE
```

### Database Storage
```
Signals Table:
  - symbol: XAU_USD
  - timestamp: 2024-01-15 14:35:22
  - signal_type: BUY
  - confidence: 78
  - entry_price: 2025.60
  - target_price: 2065.60
  - stop_loss: 2005.60
  - risk_reward_ratio: 2.0
  - timeframe: M1
  - indicators: {"RSI": 45, "MACD": "positive", "ADX": 35}
  - valid: true
  - closed: false
  - exit_price: null
  - exit_time: null
  - pnl: null
```

## Performance Optimization

### Signal Caching
```
Cache recent signals for 60 seconds
Prevent duplicate signals on same bar
Update on new bar close only
```

### Indicator Calculation Optimization
```
Pre-calculate common indicators
Store moving averages incrementally
Update volatility measures in-place
Batch processing for multiple markets
```

## Machine Learning Integration (Future)

Planned ML enhancements:
```
1. Feature engineering from indicators
2. Classification model (BUY/SELL/HOLD)
3. Confidence scoring using neural network
4. Pattern recognition with CNN
5. Adaptive model retraining
6. Ensemble methods for robustness
```

## Testing and Validation

### Backtesting
```
Test signals on historical data:
  - Win rate calculation
  - Profit factor analysis
  - Maximum drawdown
  - Sharpe ratio
  - Risk-adjusted returns
```

### Paper Trading
```
Live signal generation without real trades:
  - Validate signal accuracy
  - Test risk management
  - Optimize parameters
  - Build confidence before live trading
```

### Signal Quality Checklist

Before deploying signals to live trading:
- [ ] Win rate > 50%
- [ ] Profit factor > 1.25
- [ ] Risk/reward > 1.5:1
- [ ] Confidence calculation stable
- [ ] No overfitting to historical data
- [ ] Works across multiple markets
- [ ] Handles multiple timeframes correctly
- [ ] Proper error handling and logging
