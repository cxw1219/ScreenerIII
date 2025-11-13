# ScreenerIII Backtesting Framework - Implementation Summary

## Overview

A comprehensive, production-ready backtesting framework has been created for ScreenerIII at `/home/user/ScreenerIII/src/analysis/backtesting.py` (1,535 lines, 50KB).

## Files Created

1. **`/home/user/ScreenerIII/src/analysis/backtesting.py`** - Main framework (1,535 lines)
2. **`/home/user/ScreenerIII/src/analysis/backtesting_example.py`** - Example usage (400 lines)
3. **`/home/user/ScreenerIII/src/analysis/__init__.py`** - Updated module exports

## Core Components

### 1. Backtester Class
The main backtesting engine with the following capabilities:

- **Historical Data Loading**
  - Load from TimescaleDB using SQLAlchemy models
  - Load from CSV files with automatic date parsing
  - Support for multiple timeframes and instruments

- **Chronological Replay**
  - Strict chronological processing (no look-ahead bias)
  - Historical data slicing at each timestamp
  - Proper data isolation for each decision point

- **Strategy Execution**
  - Apply trading strategy at each time step
  - Generate signals using SignalGenerator or custom strategies
  - Execute trades based on signals

- **Performance Tracking**
  - Record equity curve throughout backtest
  - Track all trades with detailed information
  - Calculate comprehensive performance metrics

### 2. PortfolioTracker Class
Manages virtual portfolio state including:

- **Cash Management**
  - Track available cash balance
  - Reserve capital for open positions
  - Handle transaction costs

- **Position Sizing**
  - Risk-based position sizing (default: 2% per trade)
  - Signal confidence scaling
  - Maximum capital utilization limits (95%)

- **Entry/Exit Tracking**
  - Open positions with calculated size
  - Close positions with various exit reasons
  - Track Maximum Adverse Excursion (MAE)
  - Track Maximum Favorable Excursion (MFE)

- **Transaction Costs**
  - Commission modeling (default: 0.1%)
  - Slippage modeling (default: 0.05%)
  - Realistic execution costs

### 3. Trade Class
Represents individual trades with:

- **Entry Information**
  - Entry price and timestamp
  - Position size (units)
  - Position side (LONG/SHORT)
  - Stop loss and take profit levels

- **Exit Information**
  - Exit price and timestamp
  - Exit reason (TARGET_HIT, STOP_HIT, SIGNAL_REVERSAL, END_OF_DATA, MANUAL_EXIT)
  - Trade duration in hours

- **P&L Calculation**
  - Gross P&L calculation
  - Commission and slippage deduction
  - P&L percentage calculation
  - Winner/loser classification

- **Trade Analytics**
  - Maximum Adverse Excursion (worst drawdown during trade)
  - Maximum Favorable Excursion (best profit during trade)
  - Signal confidence tracking
  - Serialization to dictionary/JSON

### 4. PerformanceMetrics Class
Comprehensive performance metrics including:

- **Return Metrics**
  - Total return (%)
  - Annualized return (%)
  - Recovery factor (return/max drawdown)
  - Calmar ratio (annualized return/max drawdown)

- **Risk-Adjusted Returns**
  - Sharpe ratio (annualized, 252 trading days)
  - Sortino ratio (downside deviation only)

- **Drawdown Analysis**
  - Maximum drawdown (%)
  - Maximum drawdown duration (bars)

- **Trade Statistics**
  - Total trades, winning trades, losing trades
  - Win rate (%)
  - Profit factor (gross profit/gross loss)
  - Expectancy (average expected profit per trade)

- **Trade Details**
  - Average win/loss ($ and %)
  - Largest win/loss
  - Average trade duration
  - Risk/reward ratio achieved

### 5. Strategy Class (Base)
Abstract base class for implementing trading strategies:

- **Required Methods**
  - `generate_signal()` - Generate trading signals
  - Must be overridden in subclasses

- **Lifecycle Callbacks**
  - `on_trade_opened()` - Called when trade opens
  - `on_trade_closed()` - Called when trade closes
  - `reset_state()` - Reset strategy state

- **State Management**
  - Strategy configuration storage
  - Stateful information tracking
  - Walk-forward compatibility

### 6. SignalStrategy Class
Concrete strategy implementation using existing SignalGenerator:

- Integrates with ScreenerIII's SignalGenerator
- Configurable minimum confidence threshold
- Automatic signal filtering (removes HOLD/NO_SIGNAL)
- Risk percentage configuration
- Ready to use out-of-the-box

### 7. BacktestResults Class
Container for backtest results with:

- **Results Storage**
  - List of all trades
  - Equity curve DataFrame
  - Performance metrics
  - Strategy metadata

- **Metric Calculation**
  - Automatic metrics calculation from trades
  - Equity curve analysis
  - Drawdown computation
  - Statistical analysis

- **Visualization** (requires matplotlib)
  - `plot_equity_curve()` - Equity and drawdown chart
  - `plot_trade_analysis()` - P&L distribution, cumulative P&L, win/loss analysis
  - Customizable save paths
  - High-quality output (300 DPI)

- **Export Functions**
  - `export_trades_csv()` - Export trades to CSV
  - `export_metrics_json()` - Export metrics to JSON
  - `generate_report()` - Generate text report

## Key Features

### 1. Walk-Forward Analysis
```python
results_list = backtester.walk_forward_analysis(
    data=data,
    instrument='EUR_USD',
    train_period=1000,  # bars for training
    test_period=500,    # bars for testing
    step_size=500       # step forward size
)
```

Features:
- Configurable train/test periods
- Adjustable step size (default: test_period)
- Returns list of BacktestResults for each period
- Prevents overfitting through out-of-sample testing

### 2. Parameter Optimization Support
The framework provides hooks for parameter optimization:

- Strategy configuration through `config` dict
- State management for stateful strategies
- Easy parameter testing through loops
- Metric-based optimization (Sharpe, return, etc.)

### 3. Multiple Timeframe Support
- Load data at any timeframe
- Consistent processing across timeframes
- Timeframe-aware signal generation

### 4. Realistic Trade Execution
- Bid/ask spread modeling via slippage
- Commission costs per trade
- Order execution at realistic prices
- Stop loss and take profit hit detection

### 5. Comprehensive Exit Logic
- Target hit detection (intrabar)
- Stop loss hit detection (intrabar)
- Signal reversal exits
- End-of-data position closure
- Manual exit support

## Usage Examples

### Example 1: Simple Backtest
```python
from analysis.backtesting import run_simple_backtest
import pandas as pd

# Load data
data = pd.read_csv('historical_data.csv', index_col='timestamp', parse_dates=True)

# Run backtest
results = run_simple_backtest(
    data=data,
    instrument='EUR_USD',
    initial_capital=10000.0,
    min_confidence=60.0
)

# Analyze results
print(results.generate_report())
results.plot_equity_curve()
results.export_trades_csv('trades.csv')
```

### Example 2: Custom Strategy
```python
from analysis.backtesting import Backtester, Strategy
from analysis.signals import TradingSignal, SignalType

class MyStrategy(Strategy):
    def generate_signal(self, data, timestamp):
        # Your custom logic here
        if len(data) < 50:
            return None

        # Calculate indicators
        sma_20 = data['close'].rolling(20).mean().iloc[-1]
        current_price = data['close'].iloc[-1]

        # Generate signal
        if current_price > sma_20:
            return TradingSignal(
                signal_type=SignalType.BUY,
                confidence=75.0,
                entry_price=current_price,
                stop_loss=current_price * 0.98,
                target_1=current_price * 1.04
            )

        return None

# Create and run
strategy = MyStrategy("My_SMA_Strategy")
backtester = Backtester(strategy, initial_capital=10000.0)
results = backtester.run(data, instrument='EUR_USD')
```

### Example 3: Database Integration
```python
from analysis.backtesting import load_data_from_timescaledb, run_simple_backtest
from datetime import datetime, timedelta

# Load from TimescaleDB
end_date = datetime.now()
start_date = end_date - timedelta(days=90)

data = load_data_from_timescaledb(
    instrument='EUR_USD',
    timeframe='H1',
    start_date=start_date,
    end_date=end_date
)

# Run backtest
results = run_simple_backtest(data, instrument='EUR_USD')
print(results.generate_report())
```

### Example 4: Walk-Forward Analysis
```python
from analysis.backtesting import Backtester, SignalStrategy

strategy = SignalStrategy(min_confidence=60.0)
backtester = Backtester(strategy, initial_capital=10000.0)

results_list = backtester.walk_forward_analysis(
    data=data,
    instrument='EUR_USD',
    train_period=1000,
    test_period=500,
    step_size=500
)

# Aggregate results
avg_return = sum(r.metrics.total_return for r in results_list) / len(results_list)
print(f"Average Return: {avg_return:.2f}%")
```

## Performance Metrics Explained

### Sharpe Ratio
- Measures risk-adjusted return
- Formula: (Mean Return - Risk-Free Rate) / Std Dev of Returns
- Annualized assuming 252 trading days
- Good: > 1.0, Excellent: > 2.0

### Sortino Ratio
- Similar to Sharpe but uses only downside deviation
- Penalizes only negative volatility
- Better measure for strategies with asymmetric returns

### Maximum Drawdown
- Largest peak-to-trough decline
- Expressed as percentage
- Critical risk metric for position sizing

### Profit Factor
- Ratio of gross profit to gross loss
- Values > 1.0 indicate profitable strategy
- Good: > 1.5, Excellent: > 2.0

### Expectancy
- Average expected profit per trade
- Accounts for win rate and average win/loss
- Must be positive for profitable strategy

### Win Rate
- Percentage of winning trades
- Not the only important metric
- Can be low with high profit factor

## Technical Implementation Details

### Type Safety
- Full type hints throughout codebase
- Uses Python 3.7+ typing features
- Dataclasses for structured data

### Error Handling
- Comprehensive try-except blocks
- Informative error messages
- Logging at appropriate levels

### Performance Optimization
- Efficient pandas operations
- Minimal data copying
- Optimized loop structures

### Database Integration
- SQLAlchemy ORM integration
- Support for both SQLite and TimescaleDB
- Efficient query construction
- Session management with context managers

### Extensibility
- Abstract base classes for custom strategies
- Hook methods for lifecycle events
- Configuration through dictionaries
- Easy subclassing and customization

## Dependencies

### Required
- pandas
- numpy
- sqlalchemy
- Python 3.7+

### Optional
- matplotlib (for visualization)
- TimescaleDB (for production database)

## File Structure

```
src/analysis/
├── __init__.py (updated with backtesting exports)
├── backtesting.py (main framework - 1,535 lines)
├── backtesting_example.py (usage examples - 400 lines)
├── indicators.py (existing)
├── patterns.py (existing)
└── signals.py (existing - integrated with backtesting)
```

## Testing the Framework

Run the examples:
```bash
cd /home/user/ScreenerIII
python3 src/analysis/backtesting_example.py
```

This will:
1. Generate sample data
2. Run multiple backtest scenarios
3. Display performance reports
4. Export results to CSV/JSON
5. Generate visualization plots (if matplotlib available)

## Integration with Existing Code

The backtesting framework seamlessly integrates with:

1. **SignalGenerator** - Uses existing signal generation
2. **TechnicalIndicators** - Leverages indicator calculations
3. **PatternRecognition** - Incorporates pattern detection
4. **Database Models** - Reads from MarketData table
5. **Configuration** - Uses existing config system
6. **Logging** - Integrates with ScreenerIII logger

## Future Enhancements

Potential additions (not implemented):

1. Multi-asset portfolio backtesting
2. Options and derivatives support
3. Execution algorithms (TWAP, VWAP)
4. Market impact modeling
5. Leverage and margin calculations
6. Monte Carlo simulation
7. Bootstrap analysis
8. Machine learning integration
9. Real-time paper trading mode
10. Interactive dashboard with Plotly/Dash

## Best Practices

1. **Always use walk-forward analysis** to avoid overfitting
2. **Test on out-of-sample data** separate from development
3. **Include transaction costs** for realistic results
4. **Consider maximum drawdown** in position sizing
5. **Validate against manual calculations** initially
6. **Monitor multiple metrics** not just returns
7. **Test across different market conditions**
8. **Document strategy assumptions**
9. **Version control strategy parameters**
10. **Regular re-optimization** for live strategies

## Conclusion

A complete, production-ready backtesting framework has been implemented with:

- ✅ 1,535 lines of well-documented code
- ✅ Full type hints and error handling
- ✅ Comprehensive performance metrics
- ✅ TimescaleDB integration
- ✅ Walk-forward analysis support
- ✅ Visualization capabilities
- ✅ Export functionality
- ✅ Example usage code
- ✅ Integration with existing ScreenerIII components
- ✅ Extensible architecture for custom strategies

The framework is ready for immediate use in strategy development and testing.
