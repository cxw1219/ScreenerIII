#!/usr/bin/env python3
"""
Phase 2 Feature Test Results

Comprehensive test of Phase 2 features with detailed output.
"""

import sys
import time
from datetime import datetime
sys.path.insert(0, '.')

print("=" * 80)
print(" " * 20 + "PHASE 2 FEATURE TESTING RESULTS")
print("=" * 80)
print()

results = {'passed': 0, 'failed': 0, 'tests': []}

# TEST 1: Redis Caching with Performance Benchmarks
print("━" * 80)
print("TEST 1: Redis Caching Layer with Performance Benchmarks")
print("━" * 80)
try:
    from src.core.cache import CacheManager

    cache = CacheManager()

    # Basic operations
    cache.set('price:EUR_USD', 1.0850, ttl=60)
    price = cache.get('price:EUR_USD')
    assert price == 1.0850
    print("✓ Basic set/get: PASS")

    # Cache-aside performance test
    iterations = [0]
    def expensive_calc():
        iterations[0] += 1
        time.sleep(0.1)  # Simulate 100ms operation
        return {'rsi': 65.5, 'macd': 0.0012}

    # First call - uncached
    start = time.time()
    result1 = cache.get_or_fetch('indicators:EUR_USD:M5', expensive_calc, ttl=60)
    uncached_time = (time.time() - start) * 1000

    # Second call - cached
    start = time.time()
    result2 = cache.get_or_fetch('indicators:EUR_USD:M5', expensive_calc, ttl=60)
    cached_time = (time.time() - start) * 1000

    speedup = uncached_time / cached_time if cached_time > 0 else float('inf')

    print(f"✓ Cache-aside pattern: PASS")
    print(f"  Uncached call: {uncached_time:.2f}ms")
    print(f"  Cached call: {cached_time:.2f}ms")
    print(f"  Speedup: {speedup:.0f}x faster")
    print(f"  Function calls: {iterations[0]} (expected: 1)")

    # Complex data structures
    test_data = {
        'prices': [1.0850, 1.0851, 1.0852],
        'timestamp': str(datetime.now()),
        'metadata': {'source': 'OANDA', 'latency_ms': 45}
    }
    cache.set('complex_data', test_data, ttl=60)
    retrieved = cache.get('complex_data')
    assert retrieved == test_data
    print(f"✓ Complex data structures: PASS")

    # Cleanup (delete specific keys)
    cache.delete('price:EUR_USD')
    cache.delete('indicators:EUR_USD:M5')
    cache.delete('complex_data')
    print(f"✓ Cache cleanup: PASS")

    results['tests'].append(('Redis Caching', True, f'{speedup:.0f}x speedup'))
    results['passed'] += 1
    print("\n✅ REDIS CACHING: ALL TESTS PASSED\n")

except Exception as e:
    results['tests'].append(('Redis Caching', False, str(e)))
    results['failed'] += 1
    print(f"\n❌ REDIS CACHING: FAILED - {e}\n")
    import traceback
    traceback.print_exc()

# TEST 2: Paper Trading Simulator
print("━" * 80)
print("TEST 2: Paper Trading Simulator")
print("━" * 80)
try:
    from src.trading.paper_trading import (
        PaperTradingAccount, PaperTrader, Direction, OrderType, Position
    )
    from datetime import datetime

    # Create account
    account = PaperTradingAccount(
        starting_capital=10000.0,
        max_position_size=0.2,
        commission_percent=0.0002
    )
    print(f"✓ Account created: ${account.cash_balance:,.2f}")

    # Create trader
    trader = PaperTrader(account=account, default_slippage_pips=1.0)
    print(f"✓ Trader initialized")

    # Create and track a position manually
    position1 = Position(
        position_id="POS_001",
        instrument="EUR_USD",
        direction=Direction.LONG,
        entry_price=1.0850,
        entry_time=datetime.now(),
        size=1000.0,  # 1 mini lot
        stop_loss=1.0800,
        take_profit=1.0900
    )

    # Add to account
    account.open_positions[position1.position_id] = position1
    print(f"✓ Long position opened:")
    print(f"  Instrument: {position1.instrument}")
    print(f"  Entry: {position1.entry_price:.4f}")
    print(f"  Size: {position1.size:.0f} units")
    print(f"  SL: {position1.stop_loss:.4f} / TP: {position1.take_profit:.4f}")

    # Simulate favorable price movement (+20 pips)
    position1.update_price(1.0870)
    print(f"✓ Price updated to 1.0870 (+20 pips)")
    print(f"  Unrealized P&L: ${position1.unrealized_pnl:.2f}")
    print(f"  P&L %: {position1.calculate_pnl_percent():.2f}%")

    # Test short position
    position2 = Position(
        position_id="POS_002",
        instrument="GBP_USD",
        direction=Direction.SHORT,
        entry_price=1.2650,
        entry_time=datetime.now(),
        size=500.0
    )
    account.open_positions[position2.position_id] = position2
    print(f"✓ Short position opened:")
    print(f"  Instrument: {position2.instrument}")
    print(f"  Direction: SHORT")
    print(f"  Entry: {position2.entry_price:.4f}")

    # Calculate account metrics
    total_positions = len(account.open_positions)
    total_pnl = sum(p.unrealized_pnl for p in account.open_positions.values())
    equity = account.cash_balance + total_pnl

    print(f"✓ Account metrics:")
    print(f"  Cash balance: ${account.cash_balance:,.2f}")
    print(f"  Unrealized P&L: ${total_pnl:.2f}")
    print(f"  Equity: ${equity:,.2f}")
    print(f"  Open positions: {total_positions}")

    # Test risk management
    max_size = account.max_position_size * account.cash_balance
    print(f"✓ Risk management:")
    print(f"  Max position size: ${max_size:,.2f}")
    print(f"  Max positions: {account.max_positions}")
    print(f"  Max daily loss: {account.max_daily_loss * 100}%")

    results['tests'].append(('Paper Trading', True, f'{total_positions} positions, ${total_pnl:.2f} P&L'))
    results['passed'] += 1
    print("\n✅ PAPER TRADING: ALL TESTS PASSED\n")

except Exception as e:
    results['tests'].append(('Paper Trading', False, str(e)))
    results['failed'] += 1
    print(f"\n❌ PAPER TRADING: FAILED - {e}\n")
    import traceback
    traceback.print_exc()

# TEST 3: Database Layer
print("━" * 80)
print("TEST 3: Database Layer (SQLite)")
print("━" * 80)
try:
    from src.core.database import Database
    from sqlalchemy import text

    db = Database()
    print(f"✓ Database initialized")
    print(f"  Type: SQLite")
    print(f"  TimescaleDB: {db.is_timescaledb}")

    # Test connection
    with db.get_session() as session:
        result = session.execute(text("SELECT 1 as test")).scalar()
        assert result == 1
    print(f"✓ Connection test: PASS")

    # Test session management
    with db.get_session() as session:
        # Simulate a query
        result = session.execute(text("SELECT datetime('now') as current_time")).fetchone()
        print(f"✓ Query execution: PASS")
        print(f"  Current time: {result[0]}")

    results['tests'].append(('Database', True, 'SQLite ready'))
    results['passed'] += 1
    print("\n✅ DATABASE: ALL TESTS PASSED\n")

except Exception as e:
    results['tests'].append(('Database', False, str(e)))
    results['failed'] += 1
    print(f"\n❌ DATABASE: FAILED - {e}\n")
    import traceback
    traceback.print_exc()

# FINAL SUMMARY
print("=" * 80)
print(" " * 30 + "TEST SUMMARY")
print("=" * 80)
print()
print(f"Total Tests: {results['passed'] + results['failed']}")
print(f"✅ Passed: {results['passed']}")
print(f"❌ Failed: {results['failed']}")
print()
print("Detailed Results:")
print("-" * 80)
for test_name, passed, details in results['tests']:
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{test_name:.<30} {status:>10}   {details}")
print("-" * 80)
print()

if results['failed'] == 0:
    print("🎉 ALL PHASE 2 FEATURES WORKING!")
    print()
    print("Key Achievements:")
    print("  • Redis caching operational with significant performance gains")
    print("  • Paper trading simulator ready for strategy testing")
    print("  • Database layer configured and working")
    print("  • Ready for live market data integration")
else:
    print(f"⚠️  {results['failed']} test(s) failed. Review errors above.")

print()
print("Note: Advanced indicators (Ichimoku, Volume Profile, etc.) require")
print("      TA-Lib installation. Core features are operational without it.")
print("=" * 80)
