# Signal Filtering and Ranking System - User Guide

## Overview

The signal filtering and ranking system provides comprehensive capabilities for filtering, ranking, and analyzing trading signals. It's designed to help traders identify the highest-quality signals and detect important market patterns.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Components](#core-components)
3. [Filtering Signals](#filtering-signals)
4. [Ranking Signals](#ranking-signals)
5. [Signal Aggregation](#signal-aggregation)
6. [Correlation Analysis](#correlation-analysis)
7. [Advanced Usage](#advanced-usage)
8. [API Reference](#api-reference)

---

## Quick Start

### Basic Filtering Example

```python
from src.analysis.signal_filter import (
    SignalFilter, FilterConfig, EnrichedSignal,
    SignalType, TimeFrame
)

# Configure filter
config = FilterConfig(
    min_confidence=70.0,
    min_risk_reward=2.0,
    allowed_signal_types=[SignalType.STRONG_BUY, SignalType.STRONG_SELL]
)

# Create filter and apply
filter_obj = SignalFilter(config)
filtered_signals = filter_obj.filter_signals(signals)
```

### Basic Ranking Example

```python
from src.analysis.signal_filter import SignalRanker, RankingMethod

# Create ranker
ranker = SignalRanker()

# Rank by composite score
ranked = ranker.rank_signals(signals, RankingMethod.COMPOSITE)

# Get top 5 signals
top_5 = ranker.get_top_signals(signals, 5)
```

---

## Core Components

### 1. FilterConfig

Configuration for signal filtering with extensive customization options.

**Key Parameters:**
- `min_confidence`: Minimum confidence score (0-100)
- `min_risk_reward`: Minimum risk/reward ratio
- `allowed_signal_types`: List of allowed signal types
- `allowed_instruments`: Whitelist of instruments
- `blocked_instruments`: Blacklist of instruments
- `max_signals_per_update`: Maximum signals to return
- `require_trend_alignment`: Require trend alignment
- `trading_hours_only`: Filter to trading hours only
- `exclude_conflicting`: Exclude conflicting signals

**Example:**
```python
config = FilterConfig(
    min_confidence=75.0,
    min_risk_reward=2.5,
    allowed_signal_types=[SignalType.STRONG_BUY, SignalType.STRONG_SELL],
    allowed_instruments=["EUR_USD", "GBP_USD", "GOLD"],
    max_signals_per_update=5,
    require_trend_alignment=True,
    min_trend_strength=25.0
)
```

### 2. EnrichedSignal

Enhanced signal with additional metadata for filtering and ranking.

**Attributes:**
- `signal`: Original TradingSignal object
- `instrument`: Instrument/symbol name
- `timeframe`: Signal timeframe
- `trend_alignment`: Trend alignment score (0-100)
- `volume_confirmation`: Volume confirmation score (0-100)
- `composite_score`: Calculated composite score
- `market_session`: Market session
- `sector`: Market sector/category
- `metadata`: Additional custom metadata

**Example:**
```python
enriched = EnrichedSignal(
    signal=trading_signal,
    instrument="EUR_USD",
    timeframe=TimeFrame.H4,
    trend_alignment=80.0,
    volume_confirmation=75.0,
    sector="forex"
)
```

---

## Filtering Signals

### Available Filters

1. **Confidence Filter**: Filters by minimum confidence score
2. **Risk/Reward Filter**: Filters by minimum R:R ratio
3. **Signal Type Filter**: Filters by allowed signal types
4. **Instrument Filter**: Allows/blocks specific instruments
5. **Timeframe Filter**: Filters by allowed timeframes
6. **Trend Alignment Filter**: Requires minimum trend strength
7. **Trading Hours Filter**: Filters to specific trading hours
8. **Market Session Filter**: Filters by market session
9. **Volume Filter**: Requires minimum volume confirmation
10. **Custom Filters**: Apply custom filter functions

### Filter Chain Example

```python
# Configure comprehensive filter
config = FilterConfig(
    min_confidence=70.0,
    min_risk_reward=2.0,
    allowed_signal_types=[SignalType.STRONG_BUY, SignalType.BUY],
    allowed_instruments=["EUR_USD", "GBP_USD"],
    allowed_timeframes=[TimeFrame.H4, TimeFrame.D1],
    require_trend_alignment=True,
    min_trend_strength=25.0,
    trading_hours_only=True,
    max_signals_per_update=10
)

# Apply filters
filter_obj = SignalFilter(config)
filtered = filter_obj.filter_signals(signals)

# Check filter statistics
stats = filter_obj.get_filter_stats()
print(f"Total processed: {stats['total_processed']}")
print(f"Passed: {stats['passed']}")
print(f"Failed confidence: {stats['failed_confidence']}")
```

### Custom Filter Functions

```python
def custom_atr_filter(signal_dict):
    """Only signals with ATR > 0.001"""
    atr = signal_dict['metadata'].get('atr', 0)
    return atr > 0.001

config = FilterConfig(
    min_confidence=60.0,
    custom_filters=[custom_atr_filter]
)
```

---

## Ranking Signals

### Ranking Methods

1. **CONFIDENCE**: Rank by confidence score
2. **RISK_REWARD**: Rank by risk/reward ratio
3. **COMPOSITE**: Rank by weighted composite score
4. **TREND_ALIGNMENT**: Rank by trend alignment
5. **VOLUME**: Rank by volume confirmation

### Composite Scoring

The composite score combines multiple factors with customizable weights:

**Default Weights:**
- Confidence: 40%
- Risk/Reward: 30%
- Trend Alignment: 15%
- Volume Confirmation: 15%

**Example with Custom Weights:**
```python
custom_weights = {
    'confidence': 0.50,
    'risk_reward': 0.25,
    'trend_alignment': 0.15,
    'volume_confirmation': 0.10
}

ranker = SignalRanker(weights=custom_weights)
ranked = ranker.rank_signals(signals, RankingMethod.COMPOSITE)
```

### Ranking Examples

```python
# Rank by confidence (highest first)
by_confidence = ranker.rank_signals(signals, RankingMethod.CONFIDENCE)

# Rank by risk/reward
by_rr = ranker.rank_signals(signals, RankingMethod.RISK_REWARD)

# Get top 10 by composite score
top_10 = ranker.get_top_signals(signals, 10, RankingMethod.COMPOSITE)

# Get worst 5 signals
worst_5 = ranker.get_bottom_signals(signals, 5, RankingMethod.COMPOSITE)
```

---

## Signal Aggregation

### Timeframe Aggregation

Combine signals across multiple timeframes with weighted analysis:

```python
from src.analysis.signal_filter import SignalAggregator, TimeFrame

# Organize signals by timeframe
signals_by_timeframe = {
    TimeFrame.H1: [signal1_h1, signal2_h1],
    TimeFrame.H4: [signal1_h4],
    TimeFrame.D1: [signal1_d1]
}

# Aggregate for EUR_USD
aggregator = SignalAggregator()
result = aggregator.aggregate_signals(signals_by_timeframe, "EUR_USD")

print(f"Recommendation: {result['recommendation']}")
print(f"Confluence Score: {result['confluence_score']:.2f}%")
print(f"Has Divergence: {result['has_divergence']}")
```

**Result Structure:**
```python
{
    'instrument': 'EUR_USD',
    'timeframes': {
        '1h': {'signal_type': 'BUY', 'confidence': 75.0, 'weight': 5},
        '4h': {'signal_type': 'STRONG_BUY', 'confidence': 85.0, 'weight': 7},
        '1d': {'signal_type': 'BUY', 'confidence': 80.0, 'weight': 10}
    },
    'weighted_direction': 0.75,
    'confluence_score': 85.0,
    'has_divergence': False,
    'recommendation': SignalType.STRONG_BUY
}
```

### Confluence Detection

Detect when multiple signals agree (confluence):

```python
# Detect confluence (min 3 agreeing signals)
confluences = aggregator.detect_confluence(signals, min_confluence=3)

for conf in confluences:
    print(f"{conf['instrument']}: {conf['count']} signals agree")
    print(f"  Signal: {conf['signal_type']}")
    print(f"  Avg Confidence: {conf['avg_confidence']:.1f}%")
    print(f"  Timeframes: {', '.join(conf['timeframes'])}")
```

### Divergence Detection

Detect conflicting signals across timeframes:

```python
# Detect divergences
divergences = aggregator.detect_divergences(signals)

for div in divergences:
    print(f"{div['instrument']}: Divergence detected")
    print(f"  Buy on: {', '.join(div['buy_timeframes'])}")
    print(f"  Sell on: {', '.join(div['sell_timeframes'])}")
```

---

## Correlation Analysis

### Market-Wide Signal Detection

Detect when multiple instruments show the same signal (market-wide moves):

```python
from src.analysis.signal_filter import SignalCorrelationAnalyzer

analyzer = SignalCorrelationAnalyzer()

# Detect market-wide signals
market_wide = analyzer.detect_market_wide_signals(
    signals,
    min_instruments=5,
    min_agreement=0.70
)

if market_wide['detected']:
    print(f"Market-wide {market_wide['direction']} detected!")
    print(f"Instruments: {market_wide['instrument_count']}")
    print(f"Agreement: {market_wide['agreement_ratio']:.1%}")
```

### Sector Analysis

Analyze signals by sector/category:

```python
# Analyze by sector
sector_analysis = analyzer.analyze_by_sector(signals)

for sector, data in sector_analysis.items():
    print(f"\n{sector.upper()}:")
    print(f"  Trend: {data['trend']}")
    print(f"  Bullish: {data['bullish_ratio']:.1%}")
    print(f"  Bearish: {data['bearish_ratio']:.1%}")
    print(f"  Avg Confidence: {data['avg_confidence']:.1f}%")
```

### Related Instrument Divergences

Detect divergences between related instruments:

```python
# Define related pairs
related_pairs = [
    ("EUR_USD", "GBP_USD"),
    ("GOLD", "SILVER"),
    ("OIL_WTI", "OIL_BRENT")
]

# Detect divergences
divergences = analyzer.detect_related_divergences(signals, related_pairs)

for div in divergences:
    print(f"{div['instrument_1']} vs {div['instrument_2']}:")
    print(f"  {div['signal_1']} vs {div['signal_2']}")
```

---

## Advanced Usage

### Complete Workflow Example

```python
from src.analysis.signal_filter import (
    SignalFilter, SignalRanker, SignalAggregator,
    FilterConfig, RankingMethod, TimeFrame
)

# Step 1: Filter signals
config = FilterConfig(
    min_confidence=70.0,
    min_risk_reward=2.0,
    require_trend_alignment=True,
    exclude_conflicting=True
)

filter_obj = SignalFilter(config)
filtered = filter_obj.filter_signals(all_signals)

# Step 2: Rank filtered signals
ranker = SignalRanker()
ranked = ranker.rank_signals(filtered, RankingMethod.COMPOSITE)

# Step 3: Get top signals
top_signals = ranked[:10]

# Step 4: Check for confluence
aggregator = SignalAggregator()
confluences = aggregator.detect_confluence(top_signals, min_confluence=2)

# Step 5: Final selection
final_signals = []
for conf in confluences:
    if conf['avg_confidence'] >= 75.0:
        final_signals.extend(conf['signals'])

print(f"Final signals: {len(final_signals)}")
```

### Performance Monitoring

```python
# Monitor filter performance
stats = filter_obj.get_filter_stats()

print("Filter Performance:")
print(f"  Total: {stats['total_processed']}")
print(f"  Passed: {stats['passed']} ({stats['passed']/stats['total_processed']*100:.1f}%)")
print(f"  Failed confidence: {stats['failed_confidence']}")
print(f"  Failed R:R: {stats['failed_risk_reward']}")
print(f"  Failed trend: {stats['failed_trend']}")

# Reset stats for next run
filter_obj.reset_stats()
```

### Signal Deduplication

```python
from src.analysis.signal_filter import deduplicate_signals

# Remove duplicate signals (keep best per instrument)
unique = deduplicate_signals(signals, key='instrument')

# Remove duplicates per timeframe
unique_tf = deduplicate_signals(signals, key='timeframe')

# Remove duplicates by both instrument and timeframe
unique_both = deduplicate_signals(signals, key='both')
```

---

## API Reference

### Utility Functions

#### apply_filters()
```python
def apply_filters(signals: List[EnrichedSignal],
                 config: FilterConfig) -> List[EnrichedSignal]
```
Apply filters to signal list using configuration.

#### rank_signals()
```python
def rank_signals(signals: List[EnrichedSignal],
                method: RankingMethod = RankingMethod.COMPOSITE,
                descending: bool = True) -> List[EnrichedSignal]
```
Rank and sort signals by specified method.

#### get_top_signals()
```python
def get_top_signals(signals: List[EnrichedSignal],
                   n: int,
                   method: RankingMethod = RankingMethod.COMPOSITE) -> List[EnrichedSignal]
```
Get top N signals by ranking method.

#### detect_signal_conflicts()
```python
def detect_signal_conflicts(signals: List[EnrichedSignal]) -> List[Dict[str, Any]]
```
Detect conflicting signals (opposing signals for same instrument).

#### calculate_composite_score()
```python
def calculate_composite_score(signal: EnrichedSignal,
                             weights: Optional[Dict[str, float]] = None) -> float
```
Calculate composite score for a signal with custom weights.

#### deduplicate_signals()
```python
def deduplicate_signals(signals: List[EnrichedSignal],
                       key: str = 'instrument') -> List[EnrichedSignal]
```
Remove duplicate signals, keeping the best one.

---

## Best Practices

### 1. Filter Configuration

- Start with conservative filters (high confidence, high R:R)
- Gradually relax filters based on market conditions
- Use trend alignment for trending markets
- Disable trend requirement for range-bound markets

### 2. Ranking Strategy

- Use COMPOSITE ranking for balanced approach
- Use CONFIDENCE ranking in volatile markets
- Use RISK_REWARD ranking for conservative trading
- Combine multiple ranking methods for validation

### 3. Signal Aggregation

- Always check for confluence across timeframes
- Higher timeframes should carry more weight
- Be cautious of divergences between timeframes
- Require minimum 2-3 agreeing signals for high confidence

### 4. Correlation Analysis

- Monitor sector trends for broader market context
- Use market-wide signals to confirm overall direction
- Watch for divergences in correlated pairs
- Adjust position sizes based on correlation

### 5. Performance Optimization

- Monitor filter statistics regularly
- Adjust thresholds based on historical performance
- Deduplicate signals to avoid redundancy
- Limit max signals to prevent information overload

---

## Troubleshooting

### Common Issues

**Issue**: Too few signals passing filters
- **Solution**: Lower min_confidence or min_risk_reward thresholds

**Issue**: Conflicting signals
- **Solution**: Enable `exclude_conflicting=True` in FilterConfig

**Issue**: No confluence detected
- **Solution**: Lower `min_confluence` parameter or use more signals

**Issue**: Market-wide signal not detected
- **Solution**: Lower `min_instruments` or `min_agreement` thresholds

---

## Examples

See `/home/user/ScreenerIII/examples/signal_filter_example.py` for comprehensive examples covering:

1. Basic filtering
2. Signal ranking by different methods
3. Timeframe aggregation
4. Confluence detection
5. Conflict detection
6. Market-wide analysis
7. Sector analysis

Run examples:
```bash
cd /home/user/ScreenerIII
python3 examples/signal_filter_example.py
```

---

## License

MIT License - See project LICENSE file for details.

## Author

ScreenerIII Development Team

## Version

1.0.0 - Initial Release
