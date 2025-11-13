# Paper Trading Simulator Documentation

## Overview

The Paper Trading Simulator is a comprehensive, realistic trading simulation system designed for testing trading strategies without risking real capital. It provides accurate execution simulation, risk management, and performance tracking.

## Features

### Core Functionality

1. **Realistic Execution Simulation**
   - Bid/ask spread modeling
   - Slippage simulation (configurable, 0-2 pips typical)
   - Commission tracking (fixed + percentage)
   - Market impact modeling
   - Partial fill support

2. **Advanced Order Types**
   - `MARKET` - Immediate execution at current price
   - `LIMIT` - Execute only at specified price or better
   - `STOP` - Trigger market order when price reached
   - `STOP_LIMIT` - Trigger limit order when stop price reached

3. **Time In Force Options**
   - `GTC` (Good Till Cancelled) - Order stays until filled or cancelled
   - `DAY` - Order expires after 24 hours
   - `IOC` (Immediate Or Cancel) - Fill immediately or cancel
   - `FOK` (Fill Or Kill) - Fill completely immediately or cancel

4. **Risk Management**
   - Position size limits (% of capital)
   - Maximum concurrent positions
   - Daily loss limits
   - Maximum drawdown limits
   - Margin calculations
   - Leverage support (up to 50:1)

5. **Position Management**
   - Real-time P&L tracking
   - Stop loss automation
   - Take profit automation
   - Position modification (SL/TP)
   - Maximum Adverse Excursion (MAE)
   - Maximum Favorable Excursion (MFE)

6. **Performance Analytics**
   - Win rate
   - Profit factor
   - Average win/loss
   - Sharpe ratio
   - Sortino ratio
   - Maximum drawdown
   - Consecutive wins/losses
   - Equity curve generation

7. **Trade Journal**
   - Automatic trade recording
   - Export to CSV/JSON
   - Trade filtering and analysis
   - Statistics by instrument, direction, etc.
   - Equity curve visualization

## Architecture

### Class Hierarchy

```
PaperTradingAccount
    ├── Manages capital, margin, equity
    └── Enforces risk limits

PaperTrader
    ├── Order execution engine
    ├── Market simulation
    ├── Position management
    └── Performance calculation

TradeJournal
    ├── Trade recording
    ├── Statistics calculation
    └── Data export

Position (dataclass)
    └── Individual position tracking

Order (dataclass)
    └── Order lifecycle management
```

### Data Flow

```
Market Data → PaperTrader.update_prices()
                ↓
        Process Pending Orders
                ↓
        Update Position Prices
                ↓
        Check SL/TP Levels
                ↓
        Update Account Equity
```

## Usage Examples

### Basic Setup

```python
from src.trading import (
    PaperTradingAccount,
    PaperTrader,
    Direction,
    OrderType
)

# Create account with $10,000
account = PaperTradingAccount(
    starting_capital=10000.0,
    max_position_size=0.2,  # 20% per position
    max_positions=5,
    commission_percent=0.1
)

# Create trader
trader = PaperTrader(
    account=account,
    default_slippage_pips=1.0
)
```

### Placing Orders

```python
# Market order
order = trader.place_order(
    instrument='EUR/USD',
    direction=Direction.LONG,
    size=10000,
    order_type=OrderType.MARKET,
    stop_loss=1.0950,
    take_profit=1.1100,
    leverage=10.0
)

# Limit order
limit_order = trader.place_order(
    instrument='EUR/USD',
    direction=Direction.LONG,
    size=10000,
    order_type=OrderType.LIMIT,
    price=1.0980,  # Execute only at this price or better
    stop_loss=1.0930,
    take_profit=1.1050
)
```

### Updating Market Prices

```python
from datetime import datetime

# Update with real-time prices
trader.update_prices({
    'EUR/USD': {
        'bid': 1.1000,
        'ask': 1.1002,
        'mid': 1.1001
    },
    'GBP/USD': {
        'bid': 1.2500,
        'ask': 1.2503,
        'mid': 1.25015
    }
}, datetime.now())

# This automatically:
# - Updates position P&L
# - Checks stop losses
# - Checks take profits
# - Processes pending orders
# - Updates account equity
```

### Risk-Based Position Sizing

```python
# Calculate position size based on risk
position_size = trader.calculate_position_size(
    instrument='EUR/USD',
    direction=Direction.LONG,
    risk_percent=2.0,  # Risk 2% of account
    entry_price=1.1001,
    stop_loss=1.0951,
    leverage=20.0
)

print(f"Position size: {position_size} units")
```

### Position Management

```python
# Modify stop loss and take profit
trader.modify_position(
    position_id='abc123',
    new_stop_loss=1.0970,
    new_take_profit=1.1120
)

# Close position manually
trader.close_position(
    position_id='abc123',
    reason=CloseReason.MANUAL
)

# Close all positions
trader.close_all_positions()
```

### Performance Tracking

```python
# Get account summary
summary = account.get_account_summary()
print(f"Equity: ${summary['equity']}")
print(f"Total P&L: {summary['total_pnl_percent']}%")
print(f"Open Positions: {summary['open_positions']}")

# Get performance metrics
metrics = trader.get_performance_metrics()
print(f"Win Rate: {metrics['win_rate']}%")
print(f"Profit Factor: {metrics['profit_factor']}")
print(f"Sharpe Ratio: {metrics['sharpe_ratio']}")
```

### Trade Journal

```python
from src.trading import TradeJournal

# Create journal
journal = TradeJournal(filepath="my_trades.json")

# Record trades (after closing)
for position in account.closed_positions:
    journal.record_trade(position)

# Save to file
journal.save()

# Export to CSV
journal.export_to_csv("trades.csv")

# Get statistics
stats = journal.get_statistics()
print(f"Total Trades: {stats['total_trades']}")
print(f"Win Rate: {stats['win_rate']}%")

# Get equity curve
equity_curve = journal.get_equity_curve()
print(equity_curve)
```

## Integration with Signal Generator

The paper trader integrates seamlessly with the SignalGenerator for automated trading:

```python
from src.analysis.signals import SignalGenerator
from src.trading import PaperTrader, Direction

# Generate signal
signal_gen = SignalGenerator(market_data, risk_percent=2.0)
signal = signal_gen.generate_signal()

# Execute if confidence is high enough
if signal.confidence >= 60.0:
    direction = (Direction.LONG if signal.signal_type in ['BUY', 'STRONG_BUY']
                 else Direction.SHORT)

    # Calculate position size
    size = trader.calculate_position_size(
        instrument='EUR/USD',
        direction=direction,
        risk_percent=2.0,
        entry_price=signal.entry_price,
        stop_loss=signal.stop_loss
    )

    # Place order
    trader.place_order(
        instrument='EUR/USD',
        direction=direction,
        size=size,
        order_type=OrderType.MARKET,
        stop_loss=signal.stop_loss,
        take_profit=signal.target_1,
        metadata={'signal': signal.to_dict()}
    )
```

## Configuration Options

### Account Configuration

- `starting_capital`: Initial capital (default: $10,000)
- `max_position_size`: Max position as fraction of capital (default: 0.2)
- `max_positions`: Maximum concurrent positions (default: 10)
- `max_daily_loss`: Daily loss limit as fraction (default: 0.05)
- `max_drawdown`: Maximum drawdown as fraction (default: 0.20)
- `commission_per_trade`: Fixed commission per trade (default: 0.0)
- `commission_percent`: Commission as % of trade value (default: 0.0)
- `default_leverage`: Default leverage (default: 1.0)

### Trader Configuration

- `default_slippage_pips`: Default slippage in pips (default: 1.0)
- `spread_pips`: Dict of spreads per instrument (default: {})
- `enable_partial_fills`: Enable partial fills (default: False)
- `market_impact_factor`: Market impact factor (default: 0.0)

## Best Practices

### 1. Risk Management

```python
# Always use risk-based position sizing
position_size = trader.calculate_position_size(
    instrument=instrument,
    direction=direction,
    risk_percent=2.0,  # Never risk more than 2% per trade
    entry_price=entry_price,
    stop_loss=stop_loss
)

# Set appropriate account limits
account = PaperTradingAccount(
    max_position_size=0.1,  # 10% max per position
    max_positions=3,        # Limited concurrent positions
    max_daily_loss=0.03     # Stop trading if down 3% in a day
)
```

### 2. Always Use Stop Losses

```python
# Every position should have a stop loss
order = trader.place_order(
    instrument='EUR/USD',
    direction=Direction.LONG,
    size=size,
    stop_loss=entry_price * 0.98,  # 2% stop loss
    take_profit=entry_price * 1.04  # 4% take profit (2:1 RR)
)
```

### 3. Track Everything

```python
# Use the trade journal
journal = TradeJournal()

# Record all trades
for position in account.closed_positions:
    journal.record_trade(position)

# Analyze regularly
stats = journal.get_statistics()
equity_curve = journal.get_equity_curve()
```

### 4. Realistic Simulation

```python
# Configure realistic execution
trader = PaperTrader(
    account=account,
    default_slippage_pips=1.5,  # Realistic slippage
    spread_pips={
        'EUR/USD': 2.0,  # 2 pip spread
        'GBP/USD': 3.0,  # 3 pip spread
    }
)

# Include commissions
account = PaperTradingAccount(
    commission_percent=0.1  # 0.1% commission
)
```

## Performance Metrics Explained

### Win Rate
Percentage of winning trades out of total trades.
```
Win Rate = (Winning Trades / Total Trades) × 100
```

### Profit Factor
Ratio of gross profit to gross loss.
```
Profit Factor = Total Profit / Total Loss
```
- PF > 2.0: Excellent
- PF > 1.5: Good
- PF > 1.0: Profitable
- PF < 1.0: Losing

### Sharpe Ratio
Risk-adjusted return metric.
```
Sharpe = (Mean Return / Std Dev of Returns) × √252
```
- SR > 2.0: Excellent
- SR > 1.0: Good
- SR > 0.5: Acceptable
- SR < 0: Losing

### Sortino Ratio
Like Sharpe but only considers downside volatility.
```
Sortino = (Mean Return / Downside Std Dev) × √252
```

### Maximum Drawdown
Largest peak-to-trough decline.
```
Max DD = (Peak Equity - Trough Equity) / Peak Equity × 100
```

### MAE (Maximum Adverse Excursion)
Largest unrealized loss during position lifetime.
Useful for stop loss placement.

### MFE (Maximum Favorable Excursion)
Largest unrealized profit during position lifetime.
Useful for take profit placement.

## Troubleshooting

### Order Rejected

```python
order = trader.place_order(...)
if isinstance(order, str):
    print(f"Order rejected: {order}")
    # Common reasons:
    # - Insufficient margin
    # - Position size exceeds limit
    # - Max positions reached
    # - Daily loss limit hit
```

### Position Not Closing at SL/TP

```python
# Ensure you're updating prices regularly
trader.update_prices(market_data, timestamp)

# This triggers SL/TP checks
# SL/TP are checked on every price update
```

### Performance Metrics Return Zero

```python
metrics = trader.get_performance_metrics()
# Returns zeros if no closed positions
# Must have at least one closed trade

# Close some positions first
trader.close_all_positions()
```

## Examples

See the following example files:
- `/examples/paper_trading_demo.py` - Comprehensive feature demo
- `/examples/signal_integration_demo.py` - Integration with SignalGenerator

Run demos:
```bash
python examples/paper_trading_demo.py
python examples/signal_integration_demo.py
```

## API Reference

### PaperTradingAccount

#### Methods
- `get_total_margin_used()` - Total margin in use
- `get_available_margin()` - Available margin for new positions
- `get_total_unrealized_pnl()` - Total unrealized P&L
- `get_total_realized_pnl()` - Total realized P&L
- `update_equity()` - Recalculate account equity
- `get_current_drawdown()` - Current drawdown percentage
- `get_daily_pnl_percent()` - Daily P&L percentage
- `can_open_position(margin_required)` - Check if position can be opened
- `get_account_summary()` - Complete account summary

### PaperTrader

#### Methods
- `update_prices(market_data, timestamp)` - Update market prices
- `place_order(...)` - Place new order
- `close_position(position_id, reason)` - Close position
- `modify_position(position_id, new_sl, new_tp)` - Modify SL/TP
- `cancel_order(order_id, reason)` - Cancel pending order
- `check_stop_loss()` - Check and execute stop losses
- `check_take_profit()` - Check and execute take profits
- `close_all_positions(reason)` - Close all open positions
- `get_performance_metrics()` - Calculate performance metrics
- `calculate_position_size(...)` - Risk-based position sizing

### TradeJournal

#### Methods
- `record_trade(position)` - Record closed trade
- `get_statistics()` - Calculate statistics
- `export_to_csv(filepath)` - Export to CSV
- `export_to_json(filepath)` - Export to JSON
- `save()` - Save journal
- `load()` - Load journal
- `get_equity_curve()` - Generate equity curve
- `filter_trades(...)` - Filter trades by criteria

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or contributions, please refer to the main ScreenerIII documentation.
