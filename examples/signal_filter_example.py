"""
Example Usage of Signal Filtering and Ranking System

This example demonstrates how to use the signal_filter module to filter,
rank, and analyze trading signals.

Author: ScreenerIII
"""

import sys
import pandas as pd
from datetime import datetime

# Add project root to path
sys.path.insert(0, '/home/user/ScreenerIII')

from src.analysis.signals import TradingSignal, SignalType
from src.analysis.signal_filter import (
    SignalFilter,
    SignalRanker,
    SignalAggregator,
    SignalCorrelationAnalyzer,
    FilterConfig,
    EnrichedSignal,
    RankingMethod,
    TimeFrame,
    MarketSession,
    apply_filters,
    rank_signals,
    get_top_signals,
    detect_signal_conflicts,
    calculate_composite_score
)


def example_1_basic_filtering():
    """Example 1: Basic signal filtering."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Signal Filtering")
    print("="*60)

    # Create some example signals
    signals = [
        EnrichedSignal(
            signal=TradingSignal(
                signal_type=SignalType.STRONG_BUY,
                confidence=85.0,
                entry_price=1.1000,
                stop_loss=1.0950,
                target_1=1.1100,
                timestamp=pd.Timestamp.now()
            ),
            instrument="EUR_USD",
            timeframe=TimeFrame.H4,
            trend_alignment=80.0,
            volume_confirmation=75.0,
            sector="forex"
        ),
        EnrichedSignal(
            signal=TradingSignal(
                signal_type=SignalType.BUY,
                confidence=65.0,
                entry_price=1.2500,
                stop_loss=1.2450,
                target_1=1.2650,
                timestamp=pd.Timestamp.now()
            ),
            instrument="GBP_USD",
            timeframe=TimeFrame.H1,
            trend_alignment=60.0,
            volume_confirmation=55.0,
            sector="forex"
        ),
        EnrichedSignal(
            signal=TradingSignal(
                signal_type=SignalType.SELL,
                confidence=55.0,
                entry_price=1800.0,
                stop_loss=1820.0,
                target_1=1750.0,
                timestamp=pd.Timestamp.now()
            ),
            instrument="GOLD",
            timeframe=TimeFrame.H4,
            trend_alignment=50.0,
            volume_confirmation=45.0,
            sector="commodities"
        ),
    ]

    # Configure filter
    config = FilterConfig(
        min_confidence=70.0,
        min_risk_reward=1.5,
        allowed_signal_types=[SignalType.STRONG_BUY, SignalType.STRONG_SELL]
    )

    # Apply filters
    filtered = apply_filters(signals, config)

    print(f"\nOriginal signals: {len(signals)}")
    print(f"Filtered signals: {len(filtered)}")
    print("\nFiltered signals:")
    for sig in filtered:
        print(f"  - {sig.instrument}: {sig.signal.signal_type.value} "
              f"(confidence: {sig.signal.confidence:.1f}%, "
              f"R:R: {sig.signal.risk_reward_ratio:.2f})")


def example_2_signal_ranking():
    """Example 2: Signal ranking by different methods."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Signal Ranking")
    print("="*60)

    # Create signals with different characteristics
    signals = [
        EnrichedSignal(
            signal=TradingSignal(
                signal_type=SignalType.BUY,
                confidence=70.0,
                entry_price=1.1000,
                stop_loss=1.0950,
                target_1=1.1150,  # 3:1 R:R
            ),
            instrument="EUR_USD",
            timeframe=TimeFrame.H4,
            trend_alignment=75.0,
            volume_confirmation=80.0
        ),
        EnrichedSignal(
            signal=TradingSignal(
                signal_type=SignalType.STRONG_BUY,
                confidence=90.0,
                entry_price=1.2500,
                stop_loss=1.2450,
                target_1=1.2600,  # 2:1 R:R
            ),
            instrument="GBP_USD",
            timeframe=TimeFrame.H1,
            trend_alignment=85.0,
            volume_confirmation=70.0
        ),
        EnrichedSignal(
            signal=TradingSignal(
                signal_type=SignalType.BUY,
                confidence=80.0,
                entry_price=100.0,
                stop_loss=98.0,
                target_1=110.0,  # 5:1 R:R
            ),
            instrument="OIL",
            timeframe=TimeFrame.D1,
            trend_alignment=90.0,
            volume_confirmation=65.0
        ),
    ]

    # Rank by different methods
    ranker = SignalRanker()

    print("\n1. Ranked by CONFIDENCE:")
    ranked_conf = ranker.rank_signals(signals, RankingMethod.CONFIDENCE)
    for i, sig in enumerate(ranked_conf, 1):
        print(f"   {i}. {sig.instrument}: {sig.signal.confidence:.1f}%")

    print("\n2. Ranked by RISK/REWARD:")
    ranked_rr = ranker.rank_signals(signals, RankingMethod.RISK_REWARD)
    for i, sig in enumerate(ranked_rr, 1):
        print(f"   {i}. {sig.instrument}: {sig.signal.risk_reward_ratio:.2f}:1")

    print("\n3. Ranked by COMPOSITE SCORE:")
    ranked_comp = ranker.rank_signals(signals, RankingMethod.COMPOSITE)
    for i, sig in enumerate(ranked_comp, 1):
        print(f"   {i}. {sig.instrument}: {sig.composite_score:.2f}")

    # Get top 2 signals
    top_2 = get_top_signals(signals, 2, RankingMethod.COMPOSITE)
    print(f"\nTop 2 signals by composite score:")
    for sig in top_2:
        print(f"  - {sig.instrument}: {sig.composite_score:.2f}")


def example_3_signal_aggregation():
    """Example 3: Aggregate signals across timeframes."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Signal Aggregation Across Timeframes")
    print("="*60)

    # Create signals for EUR_USD on different timeframes
    signals_by_timeframe = {
        TimeFrame.H1: [
            EnrichedSignal(
                signal=TradingSignal(
                    signal_type=SignalType.BUY,
                    confidence=70.0,
                    entry_price=1.1000,
                    stop_loss=1.0950,
                    target_1=1.1100
                ),
                instrument="EUR_USD",
                timeframe=TimeFrame.H1
            )
        ],
        TimeFrame.H4: [
            EnrichedSignal(
                signal=TradingSignal(
                    signal_type=SignalType.STRONG_BUY,
                    confidence=85.0,
                    entry_price=1.1000,
                    stop_loss=1.0950,
                    target_1=1.1150
                ),
                instrument="EUR_USD",
                timeframe=TimeFrame.H4
            )
        ],
        TimeFrame.D1: [
            EnrichedSignal(
                signal=TradingSignal(
                    signal_type=SignalType.BUY,
                    confidence=75.0,
                    entry_price=1.1000,
                    stop_loss=1.0950,
                    target_1=1.1200
                ),
                instrument="EUR_USD",
                timeframe=TimeFrame.D1
            )
        ]
    }

    # Aggregate signals
    aggregator = SignalAggregator()
    result = aggregator.aggregate_signals(signals_by_timeframe, "EUR_USD")

    print(f"\nInstrument: {result['instrument']}")
    print(f"Weighted Direction: {result['weighted_direction']:.2f}")
    print(f"Confluence Score: {result['confluence_score']:.2f}%")
    print(f"Has Divergence: {result['has_divergence']}")
    print(f"Recommendation: {result['recommendation'].value}")

    print("\nTimeframe Analysis:")
    for tf, data in result['timeframes'].items():
        print(f"  {tf}: {data['signal_type']} "
              f"(confidence: {data['confidence']:.1f}%, "
              f"weight: {data['weight']})")


def example_4_confluence_detection():
    """Example 4: Detect signal confluence."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Signal Confluence Detection")
    print("="*60)

    # Create multiple signals for same instrument
    signals = [
        EnrichedSignal(
            signal=TradingSignal(
                signal_type=SignalType.BUY,
                confidence=75.0,
                entry_price=1.1000,
                stop_loss=1.0950,
                target_1=1.1100
            ),
            instrument="EUR_USD",
            timeframe=TimeFrame.M15
        ),
        EnrichedSignal(
            signal=TradingSignal(
                signal_type=SignalType.BUY,
                confidence=80.0,
                entry_price=1.1000,
                stop_loss=1.0950,
                target_1=1.1100
            ),
            instrument="EUR_USD",
            timeframe=TimeFrame.H1
        ),
        EnrichedSignal(
            signal=TradingSignal(
                signal_type=SignalType.STRONG_BUY,
                confidence=85.0,
                entry_price=1.1000,
                stop_loss=1.0950,
                target_1=1.1150
            ),
            instrument="EUR_USD",
            timeframe=TimeFrame.H4
        ),
    ]

    # Detect confluence
    aggregator = SignalAggregator()
    confluences = aggregator.detect_confluence(signals, min_confluence=2)

    print(f"\nDetected {len(confluences)} confluence(s)")
    for conf in confluences:
        print(f"\n  Instrument: {conf['instrument']}")
        print(f"  Signal Type: {conf['signal_type']}")
        print(f"  Agreeing Signals: {conf['count']}")
        print(f"  Average Confidence: {conf['avg_confidence']:.1f}%")
        print(f"  Timeframes: {', '.join(conf['timeframes'])}")


def example_5_conflict_detection():
    """Example 5: Detect conflicting signals."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Conflict Detection")
    print("="*60)

    # Create conflicting signals
    signals = [
        EnrichedSignal(
            signal=TradingSignal(
                signal_type=SignalType.BUY,
                confidence=75.0,
                entry_price=1.1000,
                stop_loss=1.0950,
                target_1=1.1100
            ),
            instrument="EUR_USD",
            timeframe=TimeFrame.H1
        ),
        EnrichedSignal(
            signal=TradingSignal(
                signal_type=SignalType.SELL,
                confidence=70.0,
                entry_price=1.1000,
                stop_loss=1.1050,
                target_1=1.0900
            ),
            instrument="EUR_USD",
            timeframe=TimeFrame.M15
        ),
    ]

    # Detect conflicts
    conflicts = detect_signal_conflicts(signals)

    print(f"\nDetected {len(conflicts)} conflict(s)")
    for conflict in conflicts:
        print(f"\n  Instrument: {conflict['instrument']}")
        print(f"  Buy Signals: {conflict['buy_count']}")
        print(f"  Sell Signals: {conflict['sell_count']}")


def example_6_market_wide_analysis():
    """Example 6: Market-wide signal analysis."""
    print("\n" + "="*60)
    print("EXAMPLE 6: Market-Wide Signal Analysis")
    print("="*60)

    # Create signals across multiple instruments (all bearish)
    signals = [
        EnrichedSignal(
            signal=TradingSignal(
                signal_type=SignalType.SELL,
                confidence=75.0,
                entry_price=1.1000,
                stop_loss=1.1050,
                target_1=1.0900
            ),
            instrument="EUR_USD",
            timeframe=TimeFrame.H4
        ),
        EnrichedSignal(
            signal=TradingSignal(
                signal_type=SignalType.STRONG_SELL,
                confidence=85.0,
                entry_price=1.2500,
                stop_loss=1.2550,
                target_1=1.2300
            ),
            instrument="GBP_USD",
            timeframe=TimeFrame.H4
        ),
        EnrichedSignal(
            signal=TradingSignal(
                signal_type=SignalType.SELL,
                confidence=80.0,
                entry_price=0.6500,
                stop_loss=0.6550,
                target_1=0.6400
            ),
            instrument="AUD_USD",
            timeframe=TimeFrame.H4
        ),
    ]

    # Analyze market-wide signals
    analyzer = SignalCorrelationAnalyzer()
    market_wide = analyzer.detect_market_wide_signals(
        signals,
        min_instruments=3,
        min_agreement=0.7
    )

    print(f"\nMarket-Wide Signal Detected: {market_wide['detected']}")
    if market_wide['detected']:
        print(f"Direction: {market_wide['direction']}")
        print(f"Instrument Count: {market_wide['instrument_count']}")
        print(f"Agreement Ratio: {market_wide['agreement_ratio']:.2%}")
        print(f"Instruments: {', '.join(market_wide['instruments'])}")


def example_7_sector_analysis():
    """Example 7: Sector analysis."""
    print("\n" + "="*60)
    print("EXAMPLE 7: Sector Analysis")
    print("="*60)

    # Create signals across different sectors
    signals = [
        EnrichedSignal(
            signal=TradingSignal(
                signal_type=SignalType.BUY,
                confidence=75.0,
                entry_price=1.1000,
                stop_loss=1.0950,
                target_1=1.1100
            ),
            instrument="EUR_USD",
            timeframe=TimeFrame.H4,
            sector="forex"
        ),
        EnrichedSignal(
            signal=TradingSignal(
                signal_type=SignalType.BUY,
                confidence=80.0,
                entry_price=1.2500,
                stop_loss=1.2450,
                target_1=1.2600
            ),
            instrument="GBP_USD",
            timeframe=TimeFrame.H4,
            sector="forex"
        ),
        EnrichedSignal(
            signal=TradingSignal(
                signal_type=SignalType.SELL,
                confidence=70.0,
                entry_price=1800.0,
                stop_loss=1820.0,
                target_1=1750.0
            ),
            instrument="GOLD",
            timeframe=TimeFrame.H4,
            sector="metals"
        ),
    ]

    # Analyze by sector
    analyzer = SignalCorrelationAnalyzer()
    sector_analysis = analyzer.analyze_by_sector(signals)

    print("\nSector Analysis:")
    for sector, data in sector_analysis.items():
        print(f"\n  {sector.upper()}:")
        print(f"    Trend: {data['trend']}")
        print(f"    Bullish: {data['bullish_count']} ({data['bullish_ratio']:.1%})")
        print(f"    Bearish: {data['bearish_count']} ({data['bearish_ratio']:.1%})")
        print(f"    Avg Confidence: {data['avg_confidence']:.1f}%")
        print(f"    Instruments: {', '.join(data['instruments'])}")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("SIGNAL FILTERING AND RANKING SYSTEM - EXAMPLES")
    print("="*60)

    try:
        example_1_basic_filtering()
        example_2_signal_ranking()
        example_3_signal_aggregation()
        example_4_confluence_detection()
        example_5_conflict_detection()
        example_6_market_wide_analysis()
        example_7_sector_analysis()

        print("\n" + "="*60)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
