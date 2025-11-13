# Backtesting Framework - Quick Start Guide

## Installation Check

Ensure you have the required dependencies:
```bash
pip install pandas numpy sqlalchemy matplotlib
```

## 5-Minute Quick Start

### 1. Simple Backtest with CSV Data

```python
import pandas as pd
from src.analysis.backtesting import run_simple_backtest

# Load your data
data = pd.read_csv('your_data.csv', index_col='timestamp', parse_dates=True)

# Run backtest (one line!)
results = run_simple_backtest(data, instrument='EUR_USD', initial_capital=10000.0)

# View results
print(results.generate_report())
```

### 2. Backtest with TimescaleDB Data

```python
from src.analysis.backtesting import load_data_from_timescaledb, run_simple_backtest
from datetime import datetime, timedelta

# Load data from database
data = load_data_from_timescaledb(
    instrument='EUR_USD',
    timeframe='H1',
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 11, 13)
)

# Run backtest
results = run_simple_backtest(data, instrument='EUR_USD')
print(results.generate_report())
```

### 3. Custom Configuration

```python
from src.analysis.backtesting import Backtester, SignalStrategy

# Create strategy with custom settings
strategy = SignalStrategy(
    name="My_Strategy",
    min_confidence=65.0,  # Only trade signals with 65%+ confidence
    risk_percent=2.0      # Risk 2% per trade
)

# Create backtester with custom costs
backtester = Backtester(
    strategy=strategy,
    initial_capital=10000.0,
    commission_rate=0.001,  # 0.1% commission
    slippage_rate=0.0005,   # 0.05% slippage
    risk_per_trade=0.02     # 2% risk per trade
)

# Run
results = backtester.run(data, instrument='EUR_USD')
```

## Common Tasks

### Export Results

```python
# Export trades to CSV
results.export_trades_csv('my_trades.csv')

# Export metrics to JSON
results.export_metrics_json('my_metrics.json')

# Generate text report
report = results.generate_report()
print(report)
```

### Visualize Results

```python
# Plot equity curve (requires matplotlib)
results.plot_equity_curve(save_path='equity.png', show=True)

# Plot trade analysis
results.plot_trade_analysis(save_path='trades.png', show=True)
```

### Access Specific Metrics

```python
metrics = results.metrics

print(f"Total Return: {metrics.total_return:.2f}%")
print(f"Sharpe Ratio: {metrics.sharpe_ratio:.3f}")
print(f"Max Drawdown: {metrics.max_drawdown:.2f}%")
print(f"Win Rate: {metrics.win_rate:.2f}%")
print(f"Profit Factor: {metrics.profit_factor:.3f}")
print(f"Total Trades: {metrics.total_trades}")
```

### Analyze Individual Trades

```python
# Get all trades
for trade in results.trades:
    print(f"Trade {trade.trade_id}: {trade.side.value}")
    print(f"  Entry: ${trade.entry_price:.4f} @ {trade.entry_time}")
    print(f"  Exit: ${trade.exit_price:.4f} @ {trade.exit_time}")
    print(f"  P&L: ${trade.pnl:.2f} ({trade.pnl_percent:.2f}%)")
    print(f"  Reason: {trade.exit_reason.value}")
    print()

# Get winning trades only
winners = [t for t in results.trades if t.is_winner()]
print(f"Number of winners: {len(winners)}")
```

## Custom Strategy Example

```python
from src.analysis.backtesting import Strategy, Backtester
from src.analysis.signals import TradingSignal, SignalType

class SimpleMAStrategy(Strategy):
    """Moving Average crossover strategy."""

    def __init__(self, fast=20, slow=50):
        super().__init__("MA_Crossover")
        self.fast = fast
        self.slow = slow

    def generate_signal(self, data, timestamp):
        if len(data) < self.slow:
            return None

        # Calculate MAs
        fast_ma = data['close'].rolling(self.fast).mean().iloc[-1]
        slow_ma = data['close'].rolling(self.slow).mean().iloc[-1]
        price = data['close'].iloc[-1]

        # Simple crossover logic
        if fast_ma > slow_ma:
            atr = (data['high'] - data['low']).rolling(14).mean().iloc[-1]
            return TradingSignal(
                signal_type=SignalType.BUY,
                confidence=70.0,
                entry_price=price,
                stop_loss=price - 2*atr,
                target_1=price + 3*atr
            )

        return None

# Use custom strategy
strategy = SimpleMAStrategy(fast=20, slow=50)
backtester = Backtester(strategy, initial_capital=10000.0)
results = backtester.run(data, instrument='EUR_USD')
```

## Walk-Forward Analysis

```python
from src.analysis.backtesting import Backtester, SignalStrategy

strategy = SignalStrategy(min_confidence=60.0)
backtester = Backtester(strategy, initial_capital=10000.0)

# Run walk-forward
results_list = backtester.walk_forward_analysis(
    data=data,
    instrument='EUR_USD',
    train_period=1000,  # Train on 1000 bars
    test_period=500,    # Test on 500 bars
    step_size=500       # Move forward 500 bars
)

# Analyze all periods
for i, result in enumerate(results_list, 1):
    print(f"\nPeriod {i}:")
    print(f"  Return: {result.metrics.total_return:.2f}%")
    print(f"  Sharpe: {result.metrics.sharpe_ratio:.2f}")
    print(f"  Trades: {result.metrics.total_trades}")
```

## Parameter Optimization

```python
from src.analysis.backtesting import Backtester, SignalStrategy

# Test different confidence levels
best_sharpe = -999
best_confidence = None
best_results = None

for confidence in [40, 50, 60, 70, 80]:
    strategy = SignalStrategy(min_confidence=confidence)
    backtester = Backtester(strategy, initial_capital=10000.0)
    results = backtester.run(data, instrument='EUR_USD')

    print(f"Confidence {confidence}%: Sharpe={results.metrics.sharpe_ratio:.2f}")

    if results.metrics.sharpe_ratio > best_sharpe:
        best_sharpe = results.metrics.sharpe_ratio
        best_confidence = confidence
        best_results = results

print(f"\nBest: Confidence={best_confidence}% (Sharpe={best_sharpe:.2f})")
```

## Data Format Requirements

Your CSV/DataFrame must have these columns:
- `timestamp` or datetime index
- `open` - Opening price
- `high` - High price
- `low` - Low price
- `close` - Closing price
- `volume` - Volume

Example CSV:
```csv
timestamp,open,high,low,close,volume
2024-01-01 00:00:00,1.1000,1.1050,1.0950,1.1020,5000
2024-01-01 01:00:00,1.1020,1.1080,1.1000,1.1060,6000
```

## Troubleshooting

### "Insufficient data for signal generation"
- Ensure you have at least 50 bars of data
- Check your data isn't empty: `print(len(data))`

### "No trades generated"
- Lower the `min_confidence` parameter
- Check your data quality
- Verify signal generation: `print(signal)`

### "Matplotlib not available"
- Install: `pip install matplotlib`
- Or disable plotting and use exports instead

### "Database connection failed"
- Check TimescaleDB is running
- Verify connection string in config.yaml
- Test: `from src.core.database import get_db; get_db().test_connection()`

## Performance Tips

1. **Start small**: Test on 100-1000 bars first
2. **Use walk-forward**: More reliable than single backtest
3. **Monitor drawdown**: Keep it under 20-30%
4. **Track all metrics**: Don't just look at returns
5. **Test multiple instruments**: Avoid curve-fitting

## Next Steps

1. Run the examples: `python3 src/analysis/backtesting_example.py`
2. Read the full documentation: `BACKTESTING_FRAMEWORK_SUMMARY.md`
3. Create your own strategy by subclassing `Strategy`
4. Test on your historical data
5. Use walk-forward analysis before live trading

## Quick Reference

| Task | Code |
|------|------|
| Simple backtest | `run_simple_backtest(data, 'EUR_USD')` |
| Load from DB | `load_data_from_timescaledb('EUR_USD', 'H1')` |
| Export trades | `results.export_trades_csv('trades.csv')` |
| Plot equity | `results.plot_equity_curve()` |
| Get metrics | `results.metrics.sharpe_ratio` |
| Walk-forward | `backtester.walk_forward_analysis(...)` |

## Support

For issues or questions:
1. Check the examples in `backtesting_example.py`
2. Review the summary in `BACKTESTING_FRAMEWORK_SUMMARY.md`
3. Examine the source code in `backtesting.py`
4. Enable debug logging: `logger.setLevel(logging.DEBUG)`
