"""
Example usage of the ScreenerIII Backtesting Framework

This script demonstrates how to use the backtesting framework to test
trading strategies on historical data.

Author: ScreenerIII
License: MIT
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.analysis.backtesting import (
    Backtester,
    SignalStrategy,
    Strategy,
    BacktestResults,
    load_data_from_timescaledb,
    run_simple_backtest
)
from src.core.logger import get_logger

logger = get_logger(__name__)


def generate_sample_data(
    days: int = 365,
    start_price: float = 100.0,
    volatility: float = 0.02
) -> pd.DataFrame:
    """
    Generate sample OHLCV data for testing.

    Args:
        days: Number of days of data
        start_price: Starting price
        volatility: Daily volatility

    Returns:
        DataFrame with OHLCV data
    """
    dates = pd.date_range(
        start=datetime.now() - timedelta(days=days),
        periods=days * 24,  # Hourly data
        freq='H'
    )

    # Generate random walk prices
    np.random.seed(42)
    returns = np.random.normal(0, volatility / np.sqrt(24), len(dates))
    prices = start_price * np.exp(np.cumsum(returns))

    # Generate OHLCV
    data = []
    for i in range(len(dates)):
        close = prices[i]
        open_price = close * (1 + np.random.uniform(-0.002, 0.002))
        high = max(open_price, close) * (1 + abs(np.random.uniform(0, 0.005)))
        low = min(open_price, close) * (1 - abs(np.random.uniform(0, 0.005)))
        volume = int(np.random.uniform(1000, 10000))

        data.append({
            'timestamp': dates[i],
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })

    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)

    return df


def example_1_simple_backtest():
    """Example 1: Simple backtest using SignalGenerator strategy."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Simple Backtest with SignalGenerator Strategy")
    print("=" * 80)

    # Generate sample data
    print("\nGenerating sample data...")
    data = generate_sample_data(days=180)
    print(f"Generated {len(data)} hourly bars")

    # Run simple backtest
    print("\nRunning backtest...")
    results = run_simple_backtest(
        data=data,
        instrument='SAMPLE_PAIR',
        initial_capital=10000.0,
        min_confidence=55.0
    )

    # Display report
    print(results.generate_report())

    # Export results
    print("\nExporting results...")
    results.export_trades_csv('backtest_trades.csv')
    results.export_metrics_json('backtest_metrics.json')
    print("Results exported to backtest_trades.csv and backtest_metrics.json")

    # Plot results
    try:
        print("\nGenerating plots...")
        results.plot_equity_curve(save_path='equity_curve.png', show=False)
        results.plot_trade_analysis(save_path='trade_analysis.png', show=False)
        print("Plots saved to equity_curve.png and trade_analysis.png")
    except Exception as e:
        print(f"Could not generate plots: {e}")


def example_2_custom_strategy():
    """Example 2: Backtest with custom strategy."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Custom Strategy - Simple Moving Average Crossover")
    print("=" * 80)

    class SMAStrategy(Strategy):
        """Simple Moving Average crossover strategy."""

        def __init__(self, fast_period: int = 20, slow_period: int = 50):
            super().__init__("SMA_Crossover")
            self.fast_period = fast_period
            self.slow_period = slow_period
            self.state = {'last_signal': None}

        def generate_signal(self, data, timestamp):
            """Generate signal based on SMA crossover."""
            from src.analysis.signals import TradingSignal, SignalType

            if len(data) < self.slow_period:
                return None

            # Calculate SMAs
            fast_sma = data['close'].rolling(window=self.fast_period).mean()
            slow_sma = data['close'].rolling(window=self.slow_period).mean()

            # Get current and previous values
            current_fast = fast_sma.iloc[-1]
            current_slow = slow_sma.iloc[-1]
            prev_fast = fast_sma.iloc[-2]
            prev_slow = slow_sma.iloc[-2]

            # Check for crossover
            signal_type = None

            if prev_fast <= prev_slow and current_fast > current_slow:
                signal_type = SignalType.BUY
            elif prev_fast >= prev_slow and current_fast < current_slow:
                signal_type = SignalType.SELL

            # Prevent duplicate signals
            if signal_type and signal_type == self.state.get('last_signal'):
                return None

            if signal_type is None:
                return None

            # Calculate levels
            current_price = data['close'].iloc[-1]
            atr = data['high'].rolling(14).max() - data['low'].rolling(14).min()
            atr_value = atr.iloc[-1]

            if signal_type == SignalType.BUY:
                stop_loss = current_price - (2 * atr_value)
                target = current_price + (3 * atr_value)
            else:
                stop_loss = current_price + (2 * atr_value)
                target = current_price - (3 * atr_value)

            self.state['last_signal'] = signal_type

            return TradingSignal(
                signal_type=signal_type,
                confidence=70.0,
                entry_price=current_price,
                stop_loss=stop_loss,
                target_1=target,
                reasoning=[f"SMA crossover: {self.fast_period} crossed {self.slow_period}"]
            )

    # Generate sample data
    print("\nGenerating sample data...")
    data = generate_sample_data(days=180)

    # Create custom strategy
    strategy = SMAStrategy(fast_period=20, slow_period=50)

    # Create backtester
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        commission_rate=0.001,
        slippage_rate=0.0005,
        risk_per_trade=0.02
    )

    # Run backtest
    print("\nRunning backtest...")
    results = backtester.run(data, instrument='SAMPLE_PAIR')

    # Display report
    print(results.generate_report())


def example_3_walk_forward():
    """Example 3: Walk-forward analysis."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Walk-Forward Analysis")
    print("=" * 80)

    # Generate longer sample data
    print("\nGenerating sample data...")
    data = generate_sample_data(days=365)
    print(f"Generated {len(data)} hourly bars")

    # Create strategy
    strategy = SignalStrategy(min_confidence=60.0)

    # Create backtester
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0
    )

    # Run walk-forward analysis
    print("\nRunning walk-forward analysis...")
    results_list = backtester.walk_forward_analysis(
        data=data,
        instrument='SAMPLE_PAIR',
        train_period=1000,  # ~41 days training
        test_period=500,    # ~20 days testing
        step_size=500       # Move forward 20 days each iteration
    )

    # Aggregate results
    print(f"\nWalk-Forward Results: {len(results_list)} periods")
    print("-" * 80)

    total_trades = sum(r.metrics.total_trades for r in results_list)
    avg_return = np.mean([r.metrics.total_return for r in results_list])
    avg_sharpe = np.mean([r.metrics.sharpe_ratio for r in results_list])
    avg_win_rate = np.mean([r.metrics.win_rate for r in results_list])

    print(f"Total Trades: {total_trades}")
    print(f"Average Return per Period: {avg_return:.2f}%")
    print(f"Average Sharpe Ratio: {avg_sharpe:.3f}")
    print(f"Average Win Rate: {avg_win_rate:.2f}%")

    # Show individual period results
    print("\nPeriod-by-Period Results:")
    print("-" * 80)
    for i, result in enumerate(results_list, 1):
        print(
            f"Period {i}: "
            f"Trades={result.metrics.total_trades}, "
            f"Return={result.metrics.total_return:.2f}%, "
            f"Sharpe={result.metrics.sharpe_ratio:.2f}, "
            f"Win Rate={result.metrics.win_rate:.1f}%"
        )


def example_4_database_backtest():
    """Example 4: Backtest using data from TimescaleDB."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Backtest with TimescaleDB Data")
    print("=" * 80)

    # Note: This example requires TimescaleDB to be configured and populated
    print("\nAttempting to load data from TimescaleDB...")

    try:
        # Load data from database
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)

        data = load_data_from_timescaledb(
            instrument='EUR_USD',
            timeframe='H1',
            start_date=start_date,
            end_date=end_date
        )

        if data.empty:
            print("No data found in database. Skipping this example.")
            print("Make sure TimescaleDB is configured and has data.")
            return

        print(f"Loaded {len(data)} bars from database")

        # Run backtest
        print("\nRunning backtest...")
        results = run_simple_backtest(
            data=data,
            instrument='EUR_USD',
            initial_capital=10000.0,
            min_confidence=60.0
        )

        # Display report
        print(results.generate_report())

    except Exception as e:
        print(f"Error accessing database: {e}")
        print("Make sure TimescaleDB is configured in config.yaml")


def example_5_parameter_optimization():
    """Example 5: Basic parameter optimization."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Parameter Optimization")
    print("=" * 80)

    # Generate sample data
    print("\nGenerating sample data...")
    data = generate_sample_data(days=180)

    # Test different confidence thresholds
    confidence_levels = [40.0, 50.0, 60.0, 70.0, 80.0]
    results_dict = {}

    print("\nTesting different confidence thresholds...")

    for confidence in confidence_levels:
        strategy = SignalStrategy(
            name=f"SG_Conf{confidence}",
            min_confidence=confidence
        )

        backtester = Backtester(
            strategy=strategy,
            initial_capital=10000.0
        )

        results = backtester.run(data, instrument='SAMPLE_PAIR')
        results_dict[confidence] = results

        print(
            f"Confidence {confidence}%: "
            f"Trades={results.metrics.total_trades}, "
            f"Return={results.metrics.total_return:.2f}%, "
            f"Sharpe={results.metrics.sharpe_ratio:.2f}, "
            f"Win Rate={results.metrics.win_rate:.1f}%"
        )

    # Find best configuration
    best_confidence = max(
        results_dict.keys(),
        key=lambda c: results_dict[c].metrics.sharpe_ratio
    )

    print(f"\nBest Configuration: Confidence={best_confidence}%")
    print(results_dict[best_confidence].generate_report())


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("SCREENERIII BACKTESTING FRAMEWORK - EXAMPLES")
    print("=" * 80)

    examples = [
        ("Simple Backtest", example_1_simple_backtest),
        ("Custom Strategy", example_2_custom_strategy),
        ("Walk-Forward Analysis", example_3_walk_forward),
        ("Database Backtest", example_4_database_backtest),
        ("Parameter Optimization", example_5_parameter_optimization)
    ]

    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"{i}. {name}")

    print("\nRunning all examples...")

    for name, example_func in examples:
        try:
            example_func()
        except Exception as e:
            logger.error(f"Error in {name}: {e}", exc_info=True)
            print(f"\nError in {name}: {e}")

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80)


if __name__ == '__main__':
    main()
