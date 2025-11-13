# Paper Trading Module

A comprehensive, realistic paper trading simulator for testing trading strategies without risking real capital.

## Quick Start

```python
from src.trading import (
    PaperTradingAccount,
    PaperTrader,
    Direction,
    OrderType
)
from datetime import datetime

# Create account with $10,000
account = PaperTradingAccount(
    starting_capital=10000.0,
    max_position_size=0.2,
    commission_percent=0.1
)

# Create trader
trader = PaperTrader(account=account)

# Update prices
trader.update_prices({
    'EUR/USD': {'bid': 1.1000, 'ask': 1.1002, 'mid': 1.1001}
}, datetime.now())

# Place market order
order = trader.place_order(
    instrument='EUR/USD',
    direction=Direction.LONG,
    size=10000,
    order_type=OrderType.MARKET,
    stop_loss=1.0950,
    take_profit=1.1100,
    leverage=10.0
)

# Check account status
summary = account.get_account_summary()
print(f"Equity: ${summary['equity']:,.2f}")
print(f"P&L: {summary['total_pnl_percent']:.2f}%")
```

## Features

### Execution Simulation
- ✓ Bid/ask spread modeling
- ✓ Configurable slippage (0-2 pips)
- ✓ Commission tracking (fixed + percentage)
- ✓ Market impact simulation
- ✓ Partial fill support

### Order Types
- ✓ MARKET - Immediate execution
- ✓ LIMIT - Execute at price or better
- ✓ STOP - Trigger at stop price
- ✓ STOP_LIMIT - Combined stop and limit

### Risk Management
- ✓ Position size limits
- ✓ Maximum concurrent positions
- ✓ Daily loss limits
- ✓ Maximum drawdown limits
- ✓ Leverage support (up to 50:1)
- ✓ Margin calculations

### Position Management
- ✓ Real-time P&L tracking
- ✓ Automatic SL/TP execution
- ✓ Position modification
- ✓ MAE/MFE tracking

### Performance Analytics
- ✓ Win rate, profit factor
- ✓ Sharpe & Sortino ratios
- ✓ Maximum drawdown
- ✓ Equity curve generation
- ✓ Trade journal with CSV/JSON export

## Files

- `paper_trading.py` - Main module (1,547 lines)
- `__init__.py` - Package exports
- `README.md` - This file

## Examples

- `/examples/paper_trading_demo.py` - Comprehensive demo (618 lines)
- `/examples/signal_integration_demo.py` - Signal integration (396 lines)

## Documentation

See `/docs/PAPER_TRADING.md` for complete documentation (534 lines)

## Key Classes

### PaperTradingAccount
Manages account capital, margin, and risk limits.

```python
account = PaperTradingAccount(
    starting_capital=10000.0,
    max_position_size=0.2,      # 20% per position
    max_positions=5,
    max_daily_loss=0.05,        # 5% daily loss limit
    max_drawdown=0.20,          # 20% max drawdown
    commission_percent=0.1,
    default_leverage=10.0
)
```

### PaperTrader
Main trading engine for order execution and position management.

```python
trader = PaperTrader(
    account=account,
    default_slippage_pips=1.0,
    spread_pips={'EUR/USD': 2.0},
    enable_partial_fills=False
)
```

### TradeJournal
Records and analyzes all trades.

```python
journal = TradeJournal(filepath="trades.json")
journal.record_trade(position)
journal.save()
stats = journal.get_statistics()
```

## Integration with SignalGenerator

```python
from src.analysis.signals import SignalGenerator

# Generate signal
signal = SignalGenerator(data).generate_signal()

# Calculate position size
size = trader.calculate_position_size(
    instrument='EUR/USD',
    direction=Direction.LONG,
    risk_percent=2.0,
    entry_price=signal.entry_price,
    stop_loss=signal.stop_loss
)

# Execute trade
trader.place_order(
    instrument='EUR/USD',
    direction=Direction.LONG,
    size=size,
    order_type=OrderType.MARKET,
    stop_loss=signal.stop_loss,
    take_profit=signal.target_1
)
```

## Running Examples

```bash
# Basic demo
python examples/paper_trading_demo.py

# Signal integration demo
python examples/signal_integration_demo.py
```

## Testing

All components include comprehensive error handling and logging:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

## Performance Metrics

The system calculates:
- **Win Rate**: Percentage of winning trades
- **Profit Factor**: Gross profit / gross loss
- **Sharpe Ratio**: Risk-adjusted returns
- **Sortino Ratio**: Downside risk-adjusted returns
- **Max Drawdown**: Peak-to-trough decline
- **MAE/MFE**: Maximum adverse/favorable excursion

## License

MIT License - Part of ScreenerIII project
