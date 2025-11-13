"""
Signal Generator Integration Demo

Demonstrates integration between the SignalGenerator and PaperTrader
for automated trading based on technical analysis signals.

Author: ScreenerIII
License: MIT
"""

import sys
from pathlib import Path
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.trading import (
    PaperTradingAccount,
    PaperTrader,
    TradeJournal,
    Direction,
    OrderType,
    CloseReason
)

from src.analysis.signals import SignalGenerator, SignalType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_sample_data(
    symbol: str = "EUR/USD",
    days: int = 100,
    start_price: float = 1.1000
) -> pd.DataFrame:
    """
    Generate sample OHLCV data for testing.

    Args:
        symbol: Trading symbol
        days: Number of days of data
        start_price: Starting price

    Returns:
        DataFrame with OHLCV data
    """
    dates = pd.date_range(end=datetime.now(), periods=days, freq='1H')

    # Generate realistic price movement
    returns = np.random.normal(0.0001, 0.002, len(dates))
    prices = start_price * (1 + returns).cumprod()

    # Generate OHLCV
    data = pd.DataFrame({
        'open': prices * (1 + np.random.uniform(-0.001, 0.001, len(dates))),
        'high': prices * (1 + np.random.uniform(0.0, 0.003, len(dates))),
        'low': prices * (1 + np.random.uniform(-0.003, 0.0, len(dates))),
        'close': prices,
        'volume': np.random.randint(1000, 10000, len(dates))
    }, index=dates)

    # Ensure high is highest and low is lowest
    data['high'] = data[['open', 'high', 'low', 'close']].max(axis=1)
    data['low'] = data[['open', 'high', 'low', 'close']].min(axis=1)

    return data


class AutoTrader:
    """
    Automated trading system integrating signals with paper trading.
    """

    def __init__(
        self,
        account: PaperTradingAccount,
        trader: PaperTrader,
        journal: TradeJournal,
        min_confidence: float = 60.0,
        risk_per_trade: float = 2.0
    ):
        """
        Initialize auto trader.

        Args:
            account: Paper trading account
            trader: Paper trader
            journal: Trade journal
            min_confidence: Minimum signal confidence to trade
            risk_per_trade: Risk percentage per trade
        """
        self.account = account
        self.trader = trader
        self.journal = journal
        self.min_confidence = min_confidence
        self.risk_per_trade = risk_per_trade

        logger.info(f"Initialized AutoTrader (min confidence: {min_confidence}%, risk: {risk_per_trade}%)")

    def process_signal(self, signal, instrument: str, current_data: pd.DataFrame):
        """
        Process a trading signal and execute if criteria met.

        Args:
            signal: TradingSignal object
            instrument: Trading instrument
            current_data: Current market data
        """
        # Check if signal meets minimum confidence
        if signal.confidence < self.min_confidence:
            logger.info(f"Signal confidence {signal.confidence:.1f}% below minimum {self.min_confidence}%")
            return

        # Check if we should trade this signal
        if signal.signal_type in [SignalType.NO_SIGNAL, SignalType.HOLD]:
            logger.info(f"Signal type {signal.signal_type.value} - no action")
            return

        # Determine direction
        if signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
            direction = Direction.LONG
        elif signal.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
            direction = Direction.SHORT
        else:
            logger.warning(f"Unknown signal type: {signal.signal_type}")
            return

        # Calculate position size based on risk
        try:
            position_size = self.trader.calculate_position_size(
                instrument=instrument,
                direction=direction,
                risk_percent=self.risk_per_trade,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                leverage=self.account.default_leverage
            )
        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            return

        # Place order
        logger.info(f"Placing {direction.value} order for {instrument}")
        logger.info(f"  Entry: {signal.entry_price:.5f}")
        logger.info(f"  Stop Loss: {signal.stop_loss:.5f}")
        logger.info(f"  Target: {signal.target_1:.5f}")
        logger.info(f"  Size: {position_size:.2f} units")
        logger.info(f"  Confidence: {signal.confidence:.1f}%")

        order = self.trader.place_order(
            instrument=instrument,
            direction=direction,
            size=position_size,
            order_type=OrderType.MARKET,
            stop_loss=signal.stop_loss,
            take_profit=signal.target_1,
            leverage=self.account.default_leverage,
            metadata={
                'signal_type': signal.signal_type.value,
                'confidence': signal.confidence,
                'risk_reward_ratio': signal.risk_reward_ratio,
                'reasoning': signal.reasoning
            }
        )

        if isinstance(order, str):
            logger.error(f"Order failed: {order}")
        else:
            logger.info(f"Order executed: {order.order_id}")
            logger.info(f"  Filled at: {order.filled_price:.5f}")
            logger.info(f"  Commission: ${order.commission:.2f}")

    def run_backtest(
        self,
        data: pd.DataFrame,
        instrument: str,
        update_interval: int = 1
    ) -> dict:
        """
        Run a backtest on historical data.

        Args:
            data: Historical OHLCV data
            instrument: Trading instrument
            update_interval: Number of periods between signal checks

        Returns:
            Dict with backtest results
        """
        logger.info(f"Starting backtest on {len(data)} periods of {instrument}")

        # Minimum data for signal generation
        min_periods = 50

        for i in range(min_periods, len(data), update_interval):
            current_data = data.iloc[:i].copy()
            current_time = data.index[i]

            # Update market prices
            current_price = current_data['close'].iloc[-1]
            current_high = current_data['high'].iloc[-1]
            current_low = current_data['low'].iloc[-1]

            # Simulate bid/ask from high/low
            spread = (current_high - current_low) * 0.3  # Use 30% of range as spread
            mid = current_price
            bid = mid - spread / 2
            ask = mid + spread / 2

            self.trader.update_prices({
                instrument: {
                    'bid': bid,
                    'ask': ask,
                    'mid': mid
                }
            }, current_time)

            # Check if we should generate new signal
            # Only generate signal if no open positions or every N periods
            if len(self.account.open_positions) == 0 or i % (update_interval * 10) == 0:
                try:
                    # Generate signal
                    signal_gen = SignalGenerator(current_data, risk_percent=self.risk_per_trade)
                    signal = signal_gen.generate_signal()

                    logger.info(f"\n[{current_time}] Signal: {signal.signal_type.value} (confidence: {signal.confidence:.1f}%)")

                    # Process signal
                    self.process_signal(signal, instrument, current_data)

                except Exception as e:
                    logger.error(f"Error generating signal at {current_time}: {str(e)}")

            # Record closed positions
            for position in self.account.closed_positions:
                if position.position_id not in [t.get('position_id') for t in self.journal.trades]:
                    self.journal.record_trade(position)

        # Close any remaining positions
        for pos_id in list(self.account.open_positions.keys()):
            self.trader.close_position(pos_id, CloseReason.TIME_LIMIT)
            last_position = self.account.closed_positions[-1]
            self.journal.record_trade(last_position)

        # Save journal
        self.journal.save()

        # Get results
        account_summary = self.account.get_account_summary()
        performance = self.trader.get_performance_metrics()
        journal_stats = self.journal.get_statistics()

        logger.info(f"\nBacktest complete!")
        logger.info(f"Final Equity: ${account_summary['equity']:.2f}")
        logger.info(f"Total Return: {account_summary['total_pnl_percent']:.2f}%")
        logger.info(f"Total Trades: {performance['total_trades']}")
        logger.info(f"Win Rate: {performance['win_rate']:.2f}%")

        return {
            'account_summary': account_summary,
            'performance': performance,
            'journal_stats': journal_stats
        }


def main():
    """Run signal integration demo."""
    print("\n" + "="*80)
    print("  SIGNAL GENERATOR + PAPER TRADING INTEGRATION DEMO")
    print("="*80 + "\n")

    print("""
This demo shows how to integrate the SignalGenerator with the PaperTrader
for automated trading based on technical analysis signals.

The system will:
1. Generate sample price data
2. Analyze data with SignalGenerator
3. Execute trades based on signals
4. Track performance with TradeJournal
5. Display comprehensive results

Press Enter to start...
    """)

    input()

    # Create account
    account = PaperTradingAccount(
        starting_capital=10000.0,
        max_position_size=0.2,
        max_positions=5,
        max_daily_loss=0.05,
        commission_percent=0.1,
        default_leverage=10.0
    )

    # Create trader
    trader = PaperTrader(
        account=account,
        default_slippage_pips=1.5
    )

    # Create journal
    journal = TradeJournal(filepath="signal_integration_journal.json")

    # Create auto trader
    auto_trader = AutoTrader(
        account=account,
        trader=trader,
        journal=journal,
        min_confidence=55.0,  # Trade signals with 55%+ confidence
        risk_per_trade=2.0    # Risk 2% per trade
    )

    # Generate sample data
    print("\nGenerating sample market data...")
    data = generate_sample_data(symbol="EUR/USD", days=30, start_price=1.1000)
    print(f"Generated {len(data)} periods of data")
    print(f"Date range: {data.index[0]} to {data.index[-1]}")
    print(f"Price range: {data['low'].min():.5f} to {data['high'].max():.5f}")

    # Run backtest
    print("\nRunning automated trading backtest...")
    print("-" * 80)

    results = auto_trader.run_backtest(
        data=data,
        instrument="EUR/USD",
        update_interval=1  # Check for signals every period
    )

    # Display results
    print("\n" + "="*80)
    print("  BACKTEST RESULTS")
    print("="*80 + "\n")

    print("ACCOUNT SUMMARY:")
    print("-" * 80)
    for key, value in results['account_summary'].items():
        print(f"  {key:.<30} {value}")

    print("\nPERFORMANCE METRICS:")
    print("-" * 80)
    for key, value in results['performance'].items():
        print(f"  {key:.<30} {value}")

    # Equity curve
    equity_curve = journal.get_equity_curve()
    if not equity_curve.empty:
        print("\nEQUITY CURVE:")
        print("-" * 80)
        print(equity_curve.tail(10).to_string())

        # Simple visualization
        print("\nEQUITY PROGRESSION:")
        print("-" * 80)
        for idx, row in equity_curve.iterrows():
            pnl = row['cumulative_pnl']
            bar_length = int(abs(pnl) / 50)
            bar = "+" * bar_length if pnl > 0 else "-" * bar_length
            print(f"  {row['close_time'].strftime('%Y-%m-%d %H:%M')} | {bar} ${pnl:>8.2f}")

    print("\n" + "="*80)
    print("  DEMO COMPLETE")
    print("="*80)

    print(f"""
Journal saved to: {journal.filepath}

This integration demonstrates:
- Automatic signal generation from market data
- Risk-based position sizing
- Automated order execution
- Real-time position management
- Comprehensive performance tracking

The system is ready for:
- Live paper trading
- Strategy optimization
- Parameter tuning
- Risk management testing
    """)


if __name__ == "__main__":
    main()
