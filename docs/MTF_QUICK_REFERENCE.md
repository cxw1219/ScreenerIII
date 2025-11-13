# Multi-Timeframe Analysis - Quick Reference

## Import Statements

```python
from src.data.oanda_client import OANDAClient
from src.analysis.multi_timeframe import (
    MultiTimeFrameAnalyzer,
    TimeFrame,
    TimeFrameSynchronizer,
    quick_mtf_analysis,
    compare_timeframes
)
```

## 1-Minute Setup

```python
# Initialize client
client = OANDAClient(api_token="xxx", account_id="yyy")

# Quick analysis
signal = quick_mtf_analysis(client, "EUR_USD")

# Check recommendation
print(f"{signal.recommendation}: {signal.confidence_score:.2f}%")
```

## Common Patterns

### Pattern 1: Basic Analysis
```python
analyzer = MultiTimeFrameAnalyzer(oanda_client=client)
mtf_signal = analyzer.analyze_instrument("EUR_USD")

if mtf_signal.recommendation in ['STRONG_BUY', 'BUY']:
    print(f"Long setup: Entry={mtf_signal.get_entry_price()}")
```

### Pattern 2: High-Confidence Filter
```python
if (mtf_signal.confluence_score >= 70 and
    mtf_signal.confidence_score >= 60):
    print("High-probability setup!")
```

### Pattern 3: HTF Bias Check
```python
htf_bias = analyzer.get_higher_timeframe_bias("USD_JPY", TimeFrame.M15)
if htf_bias['direction'] == 'BULLISH':
    print("Trade long on M15")
```

### Pattern 4: Multi-Instrument Scan
```python
instruments = ["EUR_USD", "GBP_USD", "USD_JPY"]
for symbol in instruments:
    signal = analyzer.analyze_instrument(symbol)
    if signal.confluence_score >= 75:
        print(f"{symbol}: {signal.recommendation}")
```

### Pattern 5: Custom Timeframes
```python
analyzer = MultiTimeFrameAnalyzer(
    oanda_client=client,
    default_timeframes=[TimeFrame.H1, TimeFrame.H4, TimeFrame.D]
)
```

## Timeframe Recommendations by Style

| Trading Style | Timeframes | Example |
|--------------|------------|---------|
| Scalping | M1, M5, M15, M30 | `[TimeFrame.M1, TimeFrame.M5, TimeFrame.M15]` |
| Day Trading | M15, M30, H1, H4 | `[TimeFrame.M15, TimeFrame.H1, TimeFrame.H4]` |
| Swing Trading | H1, H4, D | `[TimeFrame.H1, TimeFrame.H4, TimeFrame.D]` |
| Position Trading | H4, D | `[TimeFrame.H4, TimeFrame.D]` |

## Signal Quality Checklist

- [ ] Confluence ≥ 70%
- [ ] Confidence ≥ 60%
- [ ] Dominant timeframe identified
- [ ] Divergences ≤ 1
- [ ] Clear recommendation (not HOLD)
- [ ] Valid entry/stop/target levels

## Key Attributes Quick Access

```python
# Signal information
signal.instrument              # "EUR_USD"
signal.recommendation         # "STRONG_BUY"
signal.overall_direction      # "BULLISH"
signal.confidence_score       # 78.5
signal.confluence_score       # 85.2
signal.dominant_timeframe     # TimeFrame.H4

# Trading levels
signal.get_entry_price()      # 1.08450
signal.get_stop_loss()        # 1.08200
signal.get_targets()          # {'target_1': 1.08950, ...}

# Analysis details
signal.timeframe_signals      # Dict[TimeFrame, TimeFrameSignal]
signal.divergences           # List[Dict]
signal.timestamp             # datetime
```

## Common Methods

```python
# Analysis
mtf_signal = analyzer.analyze_instrument(instrument, timeframes, use_cache)

# Confluence/Divergence
confluence = analyzer.detect_confluence(timeframe_signals)
divergences = analyzer.detect_divergence(timeframe_signals)

# Composite signal
composite = analyzer.calculate_composite_signal(timeframe_signals)

# HTF bias
htf_bias = analyzer.get_higher_timeframe_bias(instrument, reference_tf)

# Data management
analyzer.clear_cache(instrument)  # Clear specific or all cache

# Utilities
comparison_df = compare_timeframes(mtf_signal)
setups = TimeFrameSynchronizer.find_multi_timeframe_setups(mtf_signal)
```

## Performance Tips

1. **Enable Caching**: `use_cache=True` for repeat analysis
2. **Adjust Lookback**: Shorter timeframes need less data
3. **Parallel Workers**: Increase `max_workers` for more instruments
4. **Cache TTL**: Set to 300s (5min) for real-time, 60s for very active
5. **Clear Cache**: Call `clear_cache()` when switching instruments

## Error Handling

```python
try:
    mtf_signal = analyzer.analyze_instrument("EUR_USD")
except Exception as e:
    logger.error(f"Analysis failed: {e}")
    # Handle error
```

## Complete Example

```python
from src.data.oanda_client import OANDAClient
from src.analysis.multi_timeframe import MultiTimeFrameAnalyzer, TimeFrame

# Setup
client = OANDAClient(api_token="xxx", account_id="yyy")
analyzer = MultiTimeFrameAnalyzer(oanda_client=client)

# Analyze
mtf_signal = analyzer.analyze_instrument("EUR_USD")

# Filter
if (mtf_signal.confluence_score >= 70 and
    mtf_signal.confidence_score >= 60 and
    mtf_signal.recommendation in ['STRONG_BUY', 'BUY']):

    # Get levels
    entry = mtf_signal.get_entry_price()
    stop = mtf_signal.get_stop_loss()
    target = mtf_signal.get_targets()['target_1']

    # Calculate position
    risk = abs(entry - stop)
    position_size = (10000 * 0.02) / risk  # 2% risk on $10k

    # Execute trade
    print(f"BUY {position_size:.0f} units at {entry}")
    print(f"Stop: {stop}, Target: {target}")
```

## File Locations

- **Main Module**: `/home/user/ScreenerIII/src/analysis/multi_timeframe.py`
- **Examples**: `/home/user/ScreenerIII/examples/multi_timeframe_example.py`
- **Full Docs**: `/home/user/ScreenerIII/docs/MULTI_TIMEFRAME_ANALYSIS.md`

## Support

See examples file for 6 complete working examples covering all use cases.
