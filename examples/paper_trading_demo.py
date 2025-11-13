"""
Paper Trading Demo

Comprehensive demonstration of the paper trading simulator functionality.
Shows how to:
- Set up a paper trading account
- Place different types of orders
- Manage positions
- Track performance
- Integrate with signal generators

Author: ScreenerIII
License: MIT
"""

import sys
from pathlib import Path
import logging
from datetime import datetime, timedelta
import random
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.trading import (
    PaperTradingAccount,
    PaperTrader,
    TradeJournal,
    Direction,
    OrderType,
    TimeInForce,
    CloseReason
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_separator(title: str = ""):
    """Print a formatted separator."""
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    else:
        print(f"{'='*80}\n")


def print_dict(data: dict, indent: int = 0):
    """Pretty print a dictionary."""
    for key, value in data.items():
        if isinstance(value, dict):
            print(f"{'  '*indent}{key}:")
            print_dict(value, indent + 1)
        else:
            print(f"{'  '*indent}{key}: {value}")


def simulate_price_update(base_price: float, volatility: float = 0.001) -> dict:
    """
    Simulate realistic price update with bid/ask spread.

    Args:
        base_price: Base price
        volatility: Price volatility factor

    Returns:
        Dict with bid, ask, and mid prices
    """
    # Random price movement
    change = random.gauss(0, volatility) * base_price
    mid = base_price + change

    # Typical forex spread (2 pips)
    spread = 0.0002
    bid = mid - spread / 2
    ask = mid + spread / 2

    return {
        'bid': bid,
        'ask': ask,
        'mid': mid
    }


def demo_basic_trading():
    """Demonstrate basic trading operations."""
    print_separator("DEMO 1: Basic Trading Operations")

    # Create account
    account = PaperTradingAccount(
        starting_capital=10000.0,
        max_position_size=0.2,  # 20% per position
        max_positions=5,
        commission_percent=0.1,  # 0.1% commission
        default_leverage=10.0  # 10:1 leverage for forex
    )

    # Create trader
    trader = PaperTrader(
        account=account,
        default_slippage_pips=1.0,
        spread_pips={'EUR/USD': 2.0, 'GBP/USD': 3.0}
    )

    print("Initial Account Status:")
    print_dict(account.get_account_summary())

    # Set initial prices
    initial_prices = {
        'EUR/USD': {'bid': 1.1000, 'ask': 1.1002, 'mid': 1.1001},
        'GBP/USD': {'bid': 1.2500, 'ask': 1.2503, 'mid': 1.25015}
    }
    trader.update_prices(initial_prices, datetime.now())

    print("\n--- Placing Market Orders ---\n")

    # Place a long position on EUR/USD
    order1 = trader.place_order(
        instrument='EUR/USD',
        direction=Direction.LONG,
        size=10000,  # 10,000 units (0.1 lot)
        order_type=OrderType.MARKET,
        stop_loss=1.0950,
        take_profit=1.1100,
        leverage=10.0,
        metadata={'strategy': 'demo', 'signal': 'bullish'}
    )

    if isinstance(order1, str):
        print(f"Order failed: {order1}")
    else:
        print(f"Order placed successfully: {order1.order_id}")
        print(f"Status: {order1.status.value}")
        print(f"Filled at: {order1.filled_price:.5f}")
        print(f"Commission: ${order1.commission:.2f}")

    # Place a short position on GBP/USD
    order2 = trader.place_order(
        instrument='GBP/USD',
        direction=Direction.SHORT,
        size=5000,  # 5,000 units (0.05 lot)
        order_type=OrderType.MARKET,
        stop_loss=1.2600,
        take_profit=1.2400,
        leverage=10.0,
        metadata={'strategy': 'demo', 'signal': 'bearish'}
    )

    if isinstance(order2, str):
        print(f"\nOrder failed: {order2}")
    else:
        print(f"\nOrder placed successfully: {order2.order_id}")
        print(f"Status: {order2.status.value}")
        print(f"Filled at: {order2.filled_price:.5f}")

    print("\n--- Account Status After Orders ---\n")
    print_dict(account.get_account_summary())

    print("\n--- Open Positions ---\n")
    for pos_id, position in account.open_positions.items():
        print(f"Position: {position.instrument}")
        print(f"  Direction: {position.direction.value}")
        print(f"  Size: {position.size}")
        print(f"  Entry: {position.entry_price:.5f}")
        print(f"  Current: {position.current_price:.5f}")
        print(f"  P&L: ${position.unrealized_pnl:.2f} ({position.calculate_pnl_percent():.2f}%)")
        print(f"  Stop Loss: {position.stop_loss:.5f}")
        print(f"  Take Profit: {position.take_profit:.5f}")
        print()

    return trader, account


def demo_price_updates_and_sl_tp(trader, account):
    """Demonstrate price updates and stop loss/take profit execution."""
    print_separator("DEMO 2: Price Updates & Stop Loss/Take Profit")

    print("Simulating market movements...\n")

    # Simulate 20 price updates
    current_eur = 1.1001
    current_gbp = 1.25015

    for i in range(20):
        # Simulate price movement
        eur_price = simulate_price_update(current_eur, volatility=0.0005)
        gbp_price = simulate_price_update(current_gbp, volatility=0.0006)

        current_eur = eur_price['mid']
        current_gbp = gbp_price['mid']

        # Update prices
        trader.update_prices(
            {
                'EUR/USD': eur_price,
                'GBP/USD': gbp_price
            },
            datetime.now()
        )

        print(f"Update {i+1}:")
        print(f"  EUR/USD: {current_eur:.5f}")
        print(f"  GBP/USD: {current_gbp:.5f}")
        print(f"  Account Equity: ${account.equity:.2f}")
        print(f"  Unrealized P&L: ${account.get_total_unrealized_pnl():.2f}")
        print(f"  Open Positions: {len(account.open_positions)}")
        print()

        # Check if any positions were closed
        if len(account.closed_positions) > 0:
            print("*** Position closed! ***")
            last_closed = account.closed_positions[-1]
            print(f"  Instrument: {last_closed.instrument}")
            print(f"  Reason: {last_closed.close_reason.value}")
            print(f"  P&L: ${last_closed.realized_pnl:.2f}")
            print()
            break

        time.sleep(0.1)  # Small delay for readability

    print("\n--- Final Account Status ---\n")
    print_dict(account.get_account_summary())


def demo_limit_and_stop_orders():
    """Demonstrate limit and stop orders."""
    print_separator("DEMO 3: Limit and Stop Orders")

    # Create fresh account
    account = PaperTradingAccount(
        starting_capital=10000.0,
        commission_percent=0.1
    )

    trader = PaperTrader(account=account)

    # Set initial prices
    trader.update_prices({
        'EUR/USD': {'bid': 1.1000, 'ask': 1.1002, 'mid': 1.1001}
    }, datetime.now())

    print("Placing pending orders...\n")

    # Place a buy limit order (buy when price drops)
    limit_order = trader.place_order(
        instrument='EUR/USD',
        direction=Direction.LONG,
        size=10000,
        order_type=OrderType.LIMIT,
        price=1.0980,  # Buy if price drops to this level
        stop_loss=1.0930,
        take_profit=1.1050,
        leverage=10.0
    )

    print(f"Buy Limit Order: {limit_order.order_id if not isinstance(limit_order, str) else limit_order}")
    print(f"  Target Price: 1.0980")

    # Place a sell stop order (sell if price breaks below)
    stop_order = trader.place_order(
        instrument='EUR/USD',
        direction=Direction.SHORT,
        size=10000,
        order_type=OrderType.STOP,
        price=1.0950,  # Sell if price drops to this level
        stop_loss=1.1000,
        take_profit=1.0850,
        leverage=10.0
    )

    print(f"\nSell Stop Order: {stop_order.order_id if not isinstance(stop_order, str) else stop_order}")
    print(f"  Trigger Price: 1.0950")

    print(f"\nPending Orders: {len(account.pending_orders)}")

    # Simulate price movement to trigger orders
    print("\nSimulating price movement...")

    current_price = 1.1001
    for i in range(30):
        # Gradually move price down
        current_price -= 0.0005 + random.gauss(0, 0.0002)

        prices = simulate_price_update(current_price, volatility=0.0003)
        trader.update_prices({'EUR/USD': prices}, datetime.now())

        print(f"Update {i+1}: EUR/USD = {current_price:.5f}, Pending: {len(account.pending_orders)}, Open: {len(account.open_positions)}")

        if len(account.pending_orders) == 0:
            print("\n*** All orders filled! ***\n")
            break

        time.sleep(0.05)

    print("\n--- Final Status ---\n")
    print(f"Open Positions: {len(account.open_positions)}")
    print(f"Pending Orders: {len(account.pending_orders)}")

    for pos_id, pos in account.open_positions.items():
        print(f"\nPosition: {pos.instrument} {pos.direction.value}")
        print(f"  Entry: {pos.entry_price:.5f}")
        print(f"  Current: {pos.current_price:.5f}")
        print(f"  P&L: ${pos.unrealized_pnl:.2f}")


def demo_risk_based_position_sizing():
    """Demonstrate risk-based position sizing."""
    print_separator("DEMO 4: Risk-Based Position Sizing")

    account = PaperTradingAccount(
        starting_capital=10000.0,
        default_leverage=20.0  # Higher leverage for forex
    )

    trader = PaperTrader(account=account)

    # Set prices
    trader.update_prices({
        'EUR/USD': {'bid': 1.1000, 'ask': 1.1002, 'mid': 1.1001}
    }, datetime.now())

    print("Account Balance: $10,000")
    print("Risk per trade: 2% = $200")
    print("\nScenario: Buy EUR/USD at 1.1001, Stop Loss at 1.0951")
    print("Risk per unit: 1.1001 - 1.0951 = 0.0050\n")

    # Calculate position size
    entry_price = 1.1001
    stop_loss = 1.0951
    risk_percent = 2.0

    position_size = trader.calculate_position_size(
        instrument='EUR/USD',
        direction=Direction.LONG,
        risk_percent=risk_percent,
        entry_price=entry_price,
        stop_loss=stop_loss,
        leverage=20.0
    )

    print(f"Calculated Position Size: {position_size:.2f} units")
    print(f"Position Value: ${position_size * entry_price:.2f}")
    print(f"Margin Required (20:1 leverage): ${(position_size * entry_price) / 20:.2f}")
    print(f"Risk if stopped out: ${position_size * (entry_price - stop_loss):.2f}")

    # Place the order
    print("\nPlacing order with calculated size...")

    order = trader.place_order(
        instrument='EUR/USD',
        direction=Direction.LONG,
        size=position_size,
        order_type=OrderType.MARKET,
        stop_loss=stop_loss,
        take_profit=1.1101,  # 2:1 risk/reward
        leverage=20.0
    )

    if not isinstance(order, str):
        print(f"Order filled at: {order.filled_price:.5f}")
        print(f"Commission: ${order.commission:.2f}")

    print("\n--- Account Status ---\n")
    print_dict(account.get_account_summary())


def demo_performance_tracking():
    """Demonstrate performance tracking and trade journal."""
    print_separator("DEMO 5: Performance Tracking & Trade Journal")

    # Create account and journal
    account = PaperTradingAccount(
        starting_capital=10000.0,
        commission_percent=0.1
    )

    trader = PaperTrader(account=account)
    journal = TradeJournal(filepath="demo_journal.json")

    print("Simulating a series of trades...\n")

    # Simulate 10 trades with random outcomes
    instruments = ['EUR/USD', 'GBP/USD', 'USD/JPY']
    current_prices = {
        'EUR/USD': 1.1000,
        'GBP/USD': 1.2500,
        'USD/JPY': 110.00
    }

    for i in range(10):
        instrument = random.choice(instruments)
        direction = random.choice([Direction.LONG, Direction.SHORT])

        # Set price
        price = current_prices[instrument]
        trader.update_prices({
            instrument: simulate_price_update(price, volatility=0.001)
        }, datetime.now())

        # Calculate stop and target
        if direction == Direction.LONG:
            stop_loss = price * 0.995
            take_profit = price * 1.015
        else:
            stop_loss = price * 1.005
            take_profit = price * 0.985

        # Place order
        order = trader.place_order(
            instrument=instrument,
            direction=direction,
            size=5000,
            order_type=OrderType.MARKET,
            stop_loss=stop_loss,
            take_profit=take_profit,
            leverage=10.0
        )

        if isinstance(order, str):
            print(f"Trade {i+1} failed: {order}")
            continue

        print(f"Trade {i+1}: {direction.value} {instrument} @ {order.filled_price:.5f}")

        # Simulate some price movement
        for _ in range(random.randint(5, 15)):
            movement = random.gauss(0, 0.002)
            new_price = price * (1 + movement)
            current_prices[instrument] = new_price

            trader.update_prices({
                instrument: simulate_price_update(new_price, volatility=0.001)
            }, datetime.now())

            # Check if position closed
            if len(account.open_positions) == 0:
                break

        # Close any remaining position manually
        for pos_id in list(account.open_positions.keys()):
            trader.close_position(pos_id, CloseReason.MANUAL)

        # Record in journal
        if account.closed_positions:
            last_trade = account.closed_positions[-1]
            journal.record_trade(last_trade)
            print(f"  Result: ${last_trade.realized_pnl:.2f} ({last_trade.close_reason.value})")

        print()

    # Save journal
    journal.save()

    print("\n--- Performance Metrics ---\n")
    metrics = trader.get_performance_metrics()
    print_dict(metrics)

    print("\n--- Journal Statistics ---\n")
    stats = journal.get_statistics()
    print_dict(stats)

    print("\n--- Account Summary ---\n")
    print_dict(account.get_account_summary())

    # Generate equity curve
    print("\n--- Equity Curve ---\n")
    equity_curve = journal.get_equity_curve()
    if not equity_curve.empty:
        print(equity_curve.to_string())

    print(f"\nJournal saved to: {journal.filepath}")


def demo_risk_management():
    """Demonstrate risk management features."""
    print_separator("DEMO 6: Risk Management")

    # Create account with strict risk limits
    account = PaperTradingAccount(
        starting_capital=10000.0,
        max_position_size=0.1,  # 10% per position
        max_positions=3,  # Only 3 concurrent positions
        max_daily_loss=0.03,  # 3% daily loss limit
        max_drawdown=0.10,  # 10% max drawdown
        commission_percent=0.1
    )

    trader = PaperTrader(account=account)

    print("Risk Limits:")
    print(f"  Max Position Size: 10% of capital")
    print(f"  Max Concurrent Positions: 3")
    print(f"  Max Daily Loss: 3%")
    print(f"  Max Drawdown: 10%")
    print()

    # Set prices
    trader.update_prices({
        'EUR/USD': {'bid': 1.1000, 'ask': 1.1002, 'mid': 1.1001}
    }, datetime.now())

    print("Test 1: Position Size Limit")
    print("-" * 50)

    # Try to open a position larger than limit
    large_order = trader.place_order(
        instrument='EUR/USD',
        direction=Direction.LONG,
        size=100000,  # Very large size
        order_type=OrderType.MARKET,
        leverage=1.0  # No leverage to hit size limit
    )

    if isinstance(large_order, str):
        print(f"Order rejected (as expected): {large_order}\n")
    else:
        print(f"Order accepted: {large_order.order_id}\n")

    print("Test 2: Maximum Positions Limit")
    print("-" * 50)

    # Open 3 small positions
    for i in range(4):
        order = trader.place_order(
            instrument='EUR/USD',
            direction=Direction.LONG,
            size=5000,
            order_type=OrderType.MARKET,
            leverage=10.0
        )

        if isinstance(order, str):
            print(f"Position {i+1}: Rejected - {order}")
        else:
            print(f"Position {i+1}: Opened successfully")

    print(f"\nOpen Positions: {len(account.open_positions)}")
    print(f"Margin Used: ${account.get_total_margin_used():.2f}")
    print(f"Available Margin: ${account.get_available_margin():.2f}")

    print("\n--- Account Summary ---\n")
    print_dict(account.get_account_summary())


def main():
    """Run all demos."""
    print_separator("PAPER TRADING SIMULATOR - COMPREHENSIVE DEMO")

    print("""
This demo showcases the full functionality of the paper trading simulator:

1. Basic Trading Operations - Market orders, positions, P&L tracking
2. Price Updates & SL/TP - Real-time price updates and automatic SL/TP execution
3. Limit and Stop Orders - Advanced order types
4. Risk-Based Position Sizing - Calculate optimal position sizes
5. Performance Tracking - Metrics, statistics, and trade journal
6. Risk Management - Position limits, daily loss limits, drawdown limits

Press Enter to start the demo...
    """)

    input()

    try:
        # Demo 1: Basic trading
        trader, account = demo_basic_trading()
        input("\nPress Enter for next demo...")

        # Demo 2: Price updates and SL/TP
        demo_price_updates_and_sl_tp(trader, account)
        input("\nPress Enter for next demo...")

        # Demo 3: Limit and stop orders
        demo_limit_and_stop_orders()
        input("\nPress Enter for next demo...")

        # Demo 4: Risk-based position sizing
        demo_risk_based_position_sizing()
        input("\nPress Enter for next demo...")

        # Demo 5: Performance tracking
        demo_performance_tracking()
        input("\nPress Enter for next demo...")

        # Demo 6: Risk management
        demo_risk_management()

        print_separator("DEMO COMPLETE")
        print("""
The paper trading simulator is ready to use!

Key Features:
- Realistic execution with slippage and spreads
- Multiple order types (MARKET, LIMIT, STOP, STOP_LIMIT)
- Comprehensive risk management
- Position tracking and management
- Performance analytics
- Trade journal with export capabilities
- Leverage support (up to 50:1 for forex)
- Integration-ready with signal generators

Check the demo_journal.json file for the trade journal output.
        """)

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        logger.error(f"Demo error: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()
