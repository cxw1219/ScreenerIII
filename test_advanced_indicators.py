"""
Test script for Advanced Indicators

Quick test to verify all advanced indicators work correctly.
"""

import pandas as pd
import numpy as np
from src.analysis.advanced_indicators import AdvancedIndicators
import sys


def create_sample_data(num_bars: int = 200) -> pd.DataFrame:
    """Create sample OHLCV data for testing."""
    np.random.seed(42)

    dates = pd.date_range(start='2024-01-01', periods=num_bars, freq='1H')

    # Generate realistic price data
    close_prices = 100 + np.cumsum(np.random.randn(num_bars) * 2)

    data = pd.DataFrame({
        'open': close_prices + np.random.randn(num_bars) * 0.5,
        'high': close_prices + abs(np.random.randn(num_bars) * 1.5),
        'low': close_prices - abs(np.random.randn(num_bars) * 1.5),
        'close': close_prices,
        'volume': np.random.randint(1000000, 10000000, num_bars)
    }, index=dates)

    # Ensure high is highest and low is lowest
    data['high'] = data[['open', 'high', 'close']].max(axis=1)
    data['low'] = data[['open', 'low', 'close']].min(axis=1)

    return data


def test_all_indicators():
    """Test all advanced indicators."""
    print("=" * 70)
    print("TESTING ADVANCED INDICATORS")
    print("=" * 70)

    # Create sample data
    print("\n1. Creating sample data...")
    data = create_sample_data(200)
    print(f"   ✓ Created {len(data)} bars of sample data")
    print(f"   Price range: ${data['close'].min():.2f} - ${data['close'].max():.2f}")

    # Initialize
    print("\n2. Initializing AdvancedIndicators...")
    try:
        adv_ind = AdvancedIndicators(data)
        print("   ✓ Successfully initialized")
    except Exception as e:
        print(f"   ✗ Failed: {str(e)}")
        return False

    # Test Ichimoku Cloud
    print("\n3. Testing Ichimoku Cloud...")
    try:
        ichimoku = adv_ind.calculate_ichimoku()
        assert 'tenkan_sen' in ichimoku
        assert 'kijun_sen' in ichimoku
        assert 'senkou_span_a' in ichimoku
        assert 'senkou_span_b' in ichimoku
        assert 'chikou_span' in ichimoku

        signals = adv_ind.generate_ichimoku_signals(ichimoku)
        print(f"   ✓ Ichimoku calculated")
        print(f"     - Trend: {signals.trend.value}")
        print(f"     - Price vs Cloud: {signals.price_vs_cloud}")
        print(f"     - Strength: {signals.strength:.1f}%")
    except Exception as e:
        print(f"   ✗ Failed: {str(e)}")
        return False

    # Test Volume Profile
    print("\n4. Testing Volume Profile...")
    try:
        vp = adv_ind.calculate_volume_profile(num_bins=30)
        assert vp.poc > 0
        assert vp.value_area_high > vp.value_area_low
        assert len(vp.profile) > 0
        print(f"   ✓ Volume Profile calculated")
        print(f"     - POC: ${vp.poc:.2f}")
        print(f"     - Value Area: ${vp.value_area_low:.2f} - ${vp.value_area_high:.2f}")
    except Exception as e:
        print(f"   ✗ Failed: {str(e)}")
        return False

    # Test Market Profile
    print("\n5. Testing Market Profile...")
    try:
        mp = adv_ind.calculate_market_profile(num_bins=30)
        assert mp.poc > 0
        assert mp.value_area_high > mp.value_area_low
        print(f"   ✓ Market Profile calculated")
        print(f"     - POC: ${mp.poc:.2f}")
        print(f"     - Initial Balance: ${mp.initial_balance_low:.2f} - ${mp.initial_balance_high:.2f}")
    except Exception as e:
        print(f"   ✗ Failed: {str(e)}")
        return False

    # Test Order Flow
    print("\n6. Testing Order Flow...")
    try:
        of = adv_ind.calculate_order_flow()
        assert len(of.delta) == len(data)
        assert len(of.cumulative_delta) == len(data)
        print(f"   ✓ Order Flow calculated")
        print(f"     - Current Delta: {of.delta.iloc[-1]:,.0f}")
        print(f"     - Cumulative: {of.cumulative_delta.iloc[-1]:,.0f}")
    except Exception as e:
        print(f"   ✗ Failed: {str(e)}")
        return False

    # Test Keltner Channels
    print("\n7. Testing Keltner Channels...")
    try:
        keltner = adv_ind.calculate_keltner_channels()
        assert 'keltner_upper' in keltner
        assert 'keltner_middle' in keltner
        assert 'keltner_lower' in keltner
        print(f"   ✓ Keltner Channels calculated")
        print(f"     - Upper: ${keltner['keltner_upper'].iloc[-1]:.2f}")
    except Exception as e:
        print(f"   ✗ Failed: {str(e)}")
        return False

    # Test Donchian Channels
    print("\n8. Testing Donchian Channels...")
    try:
        donchian = adv_ind.calculate_donchian_channels()
        assert 'donchian_upper' in donchian
        assert 'donchian_lower' in donchian
        print(f"   ✓ Donchian Channels calculated")
    except Exception as e:
        print(f"   ✗ Failed: {str(e)}")
        return False

    # Test Advanced ADX
    print("\n9. Testing Advanced ADX...")
    try:
        adx = adv_ind.calculate_adx_refined()
        assert 'ADX' in adx
        assert 'PLUS_DI' in adx
        assert 'MINUS_DI' in adx
        print(f"   ✓ Advanced ADX calculated")
        print(f"     - ADX: {adx['ADX'].iloc[-1]:.2f}")
    except Exception as e:
        print(f"   ✗ Failed: {str(e)}")
        return False

    # Test Chaikin Volatility
    print("\n10. Testing Chaikin Volatility...")
    try:
        chaikin = adv_ind.calculate_chaikin_volatility()
        assert len(chaikin) == len(data)
        print(f"   ✓ Chaikin Volatility calculated")
    except Exception as e:
        print(f"   ✗ Failed: {str(e)}")
        return False

    # Test Elliott Wave Detection
    print("\n11. Testing Elliott Wave Detection...")
    try:
        waves = adv_ind.detect_elliott_waves()
        assert 'wave_type' in waves
        assert 'pivots' in waves
        print(f"   ✓ Elliott Wave Detection complete")
        print(f"     - Wave Type: {waves['wave_type'].value}")
        print(f"     - Confidence: {waves['confidence']:.1f}%")
    except Exception as e:
        print(f"   ✗ Failed: {str(e)}")
        return False

    # Test Momentum Oscillators
    print("\n12. Testing Momentum Oscillators...")
    try:
        williams = adv_ind.calculate_williams_r()
        ultosc = adv_ind.calculate_ultimate_oscillator()
        mfi = adv_ind.calculate_mfi()
        roc = adv_ind.calculate_roc()

        assert len(williams) == len(data)
        assert len(ultosc) == len(data)
        assert len(mfi) == len(data)
        assert len(roc) == len(data)

        print(f"   ✓ All momentum oscillators calculated")
        print(f"     - Williams %R: {williams.iloc[-1]:.2f}")
        print(f"     - Ultimate Oscillator: {ultosc.iloc[-1]:.2f}")
        print(f"     - MFI: {mfi.iloc[-1]:.2f}")
        print(f"     - ROC: {roc.iloc[-1]:.2f}%")
    except Exception as e:
        print(f"   ✗ Failed: {str(e)}")
        return False

    # Test Calculate All
    print("\n13. Testing calculate_all_advanced_indicators...")
    try:
        all_indicators = adv_ind.calculate_all_advanced_indicators()
        original_cols = len(data.columns)
        total_cols = len(all_indicators.columns)
        new_cols = total_cols - original_cols

        print(f"   ✓ All indicators calculated")
        print(f"     - Original columns: {original_cols}")
        print(f"     - Total columns: {total_cols}")
        print(f"     - New indicators: {new_cols}")
    except Exception as e:
        print(f"   ✗ Failed: {str(e)}")
        return False

    # Test Visualization Data
    print("\n14. Testing visualization data...")
    try:
        for indicator_type in ['ichimoku', 'volume_profile', 'market_profile', 'keltner', 'donchian']:
            viz_data = adv_ind.get_visualization_data(indicator_type)
            assert 'type' in viz_data
        print(f"   ✓ All visualization data methods working")
    except Exception as e:
        print(f"   ✗ Failed: {str(e)}")
        return False

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    try:
        success = test_all_indicators()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test suite failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
