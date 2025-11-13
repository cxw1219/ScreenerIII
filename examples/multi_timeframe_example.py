"""
Multi-Timeframe Analysis Example

This example demonstrates how to use the comprehensive multi-timeframe analysis
system in ScreenerIII to analyze instruments across multiple timeframes and
generate high-confidence trading signals.

Features demonstrated:
- Basic multi-timeframe analysis
- Custom timeframe selection
- Confluence and divergence detection
- Higher timeframe bias analysis
- Multi-timeframe setup detection
- Timeframe comparison tables
- Complete trading workflow

Author: ScreenerIII
License: MIT
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.oanda_client import OANDAClient
from src.analysis.multi_timeframe import (
    MultiTimeFrameAnalyzer,
    TimeFrame,
    TimeFrameSynchronizer,
    quick_mtf_analysis,
    compare_timeframes
)
from src.core.config_loader import load_config
import logging


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_1_basic_analysis():
    """Example 1: Basic multi-timeframe analysis with default settings."""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Multi-Timeframe Analysis")
    print("="*80 + "\n")

    # Load configuration
    config = load_config()

    # Initialize OANDA client
    client = OANDAClient(
        api_token=config['oanda']['api_token'],
        account_id=config['oanda']['account_id'],
        environment=config['oanda']['environment']
    )

    # Quick analysis with default timeframes (M15, H1, H4, D)
    instrument = "EUR_USD"
    print(f"Analyzing {instrument} across default timeframes...\n")

    try:
        mtf_signal = quick_mtf_analysis(client, instrument)

        # Display results
        print(f"Instrument: {mtf_signal.instrument}")
        print(f"Overall Direction: {mtf_signal.overall_direction}")
        print(f"Recommendation: {mtf_signal.recommendation}")
        print(f"Confidence Score: {mtf_signal.confidence_score:.2f}%")
        print(f"Confluence Score: {mtf_signal.confluence_score:.2f}%")
        print(f"Dominant Timeframe: {mtf_signal.dominant_timeframe.granularity if mtf_signal.dominant_timeframe else 'None'}")

        # Display individual timeframe signals
        print("\nIndividual Timeframe Signals:")
        print("-" * 80)
        for tf, tf_signal in sorted(mtf_signal.timeframe_signals.items()):
            print(f"{tf.granularity:6} | {tf_signal.signal.signal_type.value:12} | "
                  f"Confidence: {tf_signal.signal.confidence:6.2f}% | "
                  f"Trend: {tf_signal.trend_direction:10} ({tf_signal.trend_strength:.2f})")

        # Display divergences if any
        if mtf_signal.divergences:
            print("\nDivergences Detected:")
            print("-" * 80)
            for div in mtf_signal.divergences:
                print(f"{div['timeframe_1']} vs {div['timeframe_2']}: "
                      f"{div['signal_1']} vs {div['signal_2']} "
                      f"({div['type']} divergence, severity: {div['severity']})")
        else:
            print("\nNo divergences detected - Strong alignment!")

        # Display trading levels
        print("\nTrading Levels:")
        print("-" * 80)
        entry = mtf_signal.get_entry_price()
        stop = mtf_signal.get_stop_loss()
        targets = mtf_signal.get_targets()

        if entry:
            print(f"Entry Price: {entry:.5f}")
            print(f"Stop Loss:   {stop:.5f}")
            print(f"Target 1:    {targets['target_1']:.5f}" if targets['target_1'] else "Target 1: N/A")
            print(f"Target 2:    {targets['target_2']:.5f}" if targets['target_2'] else "Target 2: N/A")
            print(f"Target 3:    {targets['target_3']:.5f}" if targets['target_3'] else "Target 3: N/A")

    except Exception as e:
        logger.error(f"Error in basic analysis: {e}")
        raise


def example_2_custom_timeframes():
    """Example 2: Custom timeframe selection."""
    print("\n" + "="*80)
    print("EXAMPLE 2: Custom Timeframe Selection")
    print("="*80 + "\n")

    config = load_config()
    client = OANDAClient(
        api_token=config['oanda']['api_token'],
        account_id=config['oanda']['account_id'],
        environment=config['oanda']['environment']
    )

    # Create analyzer with custom timeframes
    custom_timeframes = [TimeFrame.M5, TimeFrame.M15, TimeFrame.M30, TimeFrame.H1]

    analyzer = MultiTimeFrameAnalyzer(
        oanda_client=client,
        default_timeframes=custom_timeframes,
        lookback_days=14  # Less historical data needed for shorter timeframes
    )

    instrument = "GBP_USD"
    print(f"Analyzing {instrument} on intraday timeframes: "
          f"{[tf.granularity for tf in custom_timeframes]}\n")

    try:
        mtf_signal = analyzer.analyze_instrument(instrument)

        # Create comparison table
        comparison_df = compare_timeframes(mtf_signal)
        print("Timeframe Comparison:")
        print("-" * 80)
        print(comparison_df.to_string(index=False))

        # Check for strong confluence
        if mtf_signal.confluence_score >= 75:
            print(f"\n*** STRONG CONFLUENCE DETECTED ({mtf_signal.confluence_score:.2f}%) ***")
            print(f"Multiple timeframes agree on {mtf_signal.overall_direction} direction")
            print(f"Recommendation: {mtf_signal.recommendation}")

    except Exception as e:
        logger.error(f"Error in custom timeframe analysis: {e}")
        raise


def example_3_htf_bias():
    """Example 3: Higher timeframe bias analysis."""
    print("\n" + "="*80)
    print("EXAMPLE 3: Higher Timeframe Bias Analysis")
    print("="*80 + "\n")

    config = load_config()
    client = OANDAClient(
        api_token=config['oanda']['api_token'],
        account_id=config['oanda']['account_id'],
        environment=config['oanda']['environment']
    )

    analyzer = MultiTimeFrameAnalyzer(oanda_client=client)

    instrument = "USD_JPY"
    print(f"Analyzing higher timeframe bias for {instrument}...\n")

    try:
        # Get HTF bias relative to M15 (for scalping decisions)
        htf_bias = analyzer.get_higher_timeframe_bias(
            instrument=instrument,
            reference_timeframe=TimeFrame.M15
        )

        print(f"Reference Timeframe: {htf_bias['reference_timeframe']}")
        print(f"Higher Timeframes Analyzed: {', '.join(htf_bias['higher_timeframes'])}")
        print(f"\nHTF Direction: {htf_bias['direction']}")
        print(f"HTF Confidence: {htf_bias['confidence']:.2f}%")
        print(f"HTF Recommendation: {htf_bias['recommendation']}")

        print("\nHTF Signals:")
        for tf, signal in htf_bias['signals'].items():
            print(f"  {tf}: {signal}")

        # Trading advice based on HTF bias
        print("\nTrading Advice:")
        if htf_bias['direction'] == 'BULLISH' and htf_bias['confidence'] >= 60:
            print("  -> Look for LONG entries on M15 pullbacks")
            print("  -> Avoid SHORT positions against HTF trend")
        elif htf_bias['direction'] == 'BEARISH' and htf_bias['confidence'] >= 60:
            print("  -> Look for SHORT entries on M15 pullbacks")
            print("  -> Avoid LONG positions against HTF trend")
        else:
            print("  -> No clear HTF bias - trade with caution")
            print("  -> Consider range-bound strategies")

    except Exception as e:
        logger.error(f"Error in HTF bias analysis: {e}")
        raise


def example_4_mtf_setups():
    """Example 4: Multi-timeframe setup detection."""
    print("\n" + "="*80)
    print("EXAMPLE 4: Multi-Timeframe Setup Detection")
    print("="*80 + "\n")

    config = load_config()
    client = OANDAClient(
        api_token=config['oanda']['api_token'],
        account_id=config['oanda']['account_id'],
        environment=config['oanda']['environment']
    )

    analyzer = MultiTimeFrameAnalyzer(oanda_client=client)
    synchronizer = TimeFrameSynchronizer()

    instrument = "AUD_USD"
    print(f"Looking for multi-timeframe setups on {instrument}...\n")

    try:
        mtf_signal = analyzer.analyze_instrument(instrument)

        # Find trading setups
        setups = synchronizer.find_multi_timeframe_setups(mtf_signal)

        if setups:
            print(f"Found {len(setups)} trading setup(s):\n")
            for i, setup in enumerate(setups, 1):
                print(f"Setup {i}:")
                print(f"  Type: {setup['type']}")
                print(f"  Direction: {setup.get('direction', 'N/A')}")
                print(f"  Description: {setup['description']}")
                if 'htf' in setup:
                    print(f"  HTF: {setup['htf']}")
                if 'ltf' in setup:
                    print(f"  LTF: {setup['ltf']}")
                if 'confidence' in setup:
                    print(f"  Confidence: {setup['confidence']:.2f}%")
                print()
        else:
            print("No specific trading setups detected at this time.")

    except Exception as e:
        logger.error(f"Error in setup detection: {e}")
        raise


def example_5_complete_workflow():
    """Example 5: Complete trading workflow with multiple instruments."""
    print("\n" + "="*80)
    print("EXAMPLE 5: Complete Multi-Timeframe Trading Workflow")
    print("="*80 + "\n")

    config = load_config()
    client = OANDAClient(
        api_token=config['oanda']['api_token'],
        account_id=config['oanda']['account_id'],
        environment=config['oanda']['environment']
    )

    analyzer = MultiTimeFrameAnalyzer(oanda_client=client)
    synchronizer = TimeFrameSynchronizer()

    # Analyze multiple instruments
    instruments = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "EUR_JPY"]

    print(f"Scanning {len(instruments)} instruments for high-probability setups...\n")

    opportunities = []

    for instrument in instruments:
        try:
            print(f"Analyzing {instrument}...", end=" ")
            mtf_signal = analyzer.analyze_instrument(instrument)

            # Filter for high-quality setups
            if mtf_signal.confluence_score >= 70 and \
               mtf_signal.confidence_score >= 60 and \
               mtf_signal.recommendation in ['STRONG_BUY', 'STRONG_SELL', 'BUY', 'SELL']:

                opportunities.append({
                    'instrument': instrument,
                    'signal': mtf_signal,
                    'setups': synchronizer.find_multi_timeframe_setups(mtf_signal)
                })
                print(f"✓ OPPORTUNITY FOUND!")
            else:
                print("✗ No clear setup")

        except Exception as e:
            print(f"✗ Error: {str(e)[:50]}")
            logger.error(f"Error analyzing {instrument}: {e}")

    # Display opportunities
    print("\n" + "="*80)
    print(f"TRADING OPPORTUNITIES ({len(opportunities)} found)")
    print("="*80 + "\n")

    if opportunities:
        for i, opp in enumerate(opportunities, 1):
            signal = opp['signal']
            print(f"{i}. {opp['instrument']}")
            print(f"   Recommendation: {signal.recommendation}")
            print(f"   Direction: {signal.overall_direction}")
            print(f"   Confidence: {signal.confidence_score:.2f}%")
            print(f"   Confluence: {signal.confluence_score:.2f}%")
            print(f"   Dominant TF: {signal.dominant_timeframe.granularity if signal.dominant_timeframe else 'N/A'}")

            entry = signal.get_entry_price()
            stop = signal.get_stop_loss()
            targets = signal.get_targets()

            if entry and stop:
                risk = abs(entry - stop)
                reward = abs(targets['target_1'] - entry) if targets['target_1'] else 0
                rr_ratio = reward / risk if risk > 0 else 0

                print(f"   Entry: {entry:.5f}")
                print(f"   Stop: {stop:.5f}")
                print(f"   Target: {targets['target_1']:.5f}" if targets['target_1'] else "   Target: N/A")
                print(f"   R:R Ratio: {rr_ratio:.2f}:1")

            if opp['setups']:
                print(f"   Setups: {', '.join([s['type'] for s in opp['setups']])}")

            print()
    else:
        print("No high-probability opportunities found at this time.")
        print("Consider widening search criteria or waiting for better setups.")


def example_6_caching_demo():
    """Example 6: Demonstrate caching for performance."""
    print("\n" + "="*80)
    print("EXAMPLE 6: Caching Performance Demonstration")
    print("="*80 + "\n")

    config = load_config()
    client = OANDAClient(
        api_token=config['oanda']['api_token'],
        account_id=config['oanda']['account_id'],
        environment=config['oanda']['environment']
    )

    analyzer = MultiTimeFrameAnalyzer(
        oanda_client=client,
        cache_ttl=300  # 5 minute cache
    )

    instrument = "EUR_USD"

    try:
        import time

        # First analysis (will fetch from API)
        print(f"First analysis of {instrument} (fetching from API)...")
        start = time.time()
        mtf_signal1 = analyzer.analyze_instrument(instrument, use_cache=True)
        elapsed1 = time.time() - start
        print(f"Time: {elapsed1:.2f}s")
        print(f"Result: {mtf_signal1.recommendation} (Confidence: {mtf_signal1.confidence_score:.2f}%)\n")

        # Second analysis (will use cache)
        print(f"Second analysis of {instrument} (using cache)...")
        start = time.time()
        mtf_signal2 = analyzer.analyze_instrument(instrument, use_cache=True)
        elapsed2 = time.time() - start
        print(f"Time: {elapsed2:.2f}s")
        print(f"Result: {mtf_signal2.recommendation} (Confidence: {mtf_signal2.confidence_score:.2f}%)\n")

        # Performance improvement
        speedup = elapsed1 / elapsed2 if elapsed2 > 0 else float('inf')
        print(f"Cache speedup: {speedup:.1f}x faster")

        # Clear cache
        print("\nClearing cache...")
        analyzer.clear_cache(instrument)
        print("Cache cleared.")

    except Exception as e:
        logger.error(f"Error in caching demo: {e}")
        raise


def main():
    """Run all examples."""
    print("\n" + "="*80)
    print("MULTI-TIMEFRAME ANALYSIS EXAMPLES FOR SCREENERIII")
    print("="*80)

    try:
        # Run examples
        example_1_basic_analysis()

        # Uncomment to run other examples:
        # example_2_custom_timeframes()
        # example_3_htf_bias()
        # example_4_mtf_setups()
        # example_5_complete_workflow()
        # example_6_caching_demo()

        print("\n" + "="*80)
        print("Examples completed successfully!")
        print("="*80 + "\n")

    except Exception as e:
        logger.error(f"Error running examples: {e}")
        print(f"\nError: {e}")
        print("\nPlease ensure:")
        print("1. OANDA credentials are properly configured in config.yaml")
        print("2. Internet connection is available")
        print("3. All dependencies are installed")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
