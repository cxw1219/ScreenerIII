#!/usr/bin/env python
"""
Alert System Demo

This script demonstrates how to use the ScreenerIII alert system
with various alert types and channels.

Usage:
    python examples/alert_system_demo.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.interface.alerts import (
    AlertManager,
    AlertConfig,
    AlertPriority,
    AlertType,
    AlertChannel,
    get_alert_manager,
    send_signal_alert,
    send_price_alert,
    send_risk_alert,
    send_system_alert,
)
from src.core.database import init_db


def demo_basic_alerts():
    """Demonstrate basic alert functionality."""
    print("\n" + "=" * 60)
    print("DEMO 1: Basic Alert Functionality")
    print("=" * 60)

    # Create alert manager with desktop notifications only
    config = AlertConfig(
        enable_desktop=True,
        enable_email=False,
        enable_telegram=False,
    )
    manager = AlertManager(config)

    # Send a simple alert
    print("\n1. Sending basic system alert...")
    success = manager.send_alert(
        subject="System Started",
        message="ScreenerIII trading system has started successfully.",
        priority=AlertPriority.LOW,
        alert_type=AlertType.SYSTEM
    )
    print(f"   Result: {'✓ Sent' if success else '✗ Failed'}")


def demo_signal_alerts():
    """Demonstrate trading signal alerts."""
    print("\n" + "=" * 60)
    print("DEMO 2: Trading Signal Alerts")
    print("=" * 60)

    manager = get_alert_manager()

    # Test different confidence levels
    test_signals = [
        {
            'instrument': 'EUR_USD',
            'timeframe': 'H1',
            'signal_type': 'BUY',
            'confidence': 0.95,
            'entry_price': 1.0850,
            'stop_loss': 1.0820,
            'take_profit': 1.0920,
            'strategy': 'MACD + RSI Confluence',
        },
        {
            'instrument': 'GBP_USD',
            'timeframe': 'H4',
            'signal_type': 'SELL',
            'confidence': 0.82,
            'entry_price': 1.2650,
            'stop_loss': 1.2680,
            'take_profit': 1.2580,
            'strategy': 'EMA Crossover',
        },
        {
            'instrument': 'USD_JPY',
            'timeframe': 'M15',
            'signal_type': 'BUY',
            'confidence': 0.65,  # Below default threshold
            'entry_price': 149.50,
            'strategy': 'Bollinger Bands',
        },
    ]

    for i, signal in enumerate(test_signals, 1):
        print(f"\n{i}. Sending {signal['signal_type']} signal for {signal['instrument']} "
              f"(confidence: {signal['confidence']:.0%})...")

        success = manager.send_signal_alert(**signal)
        print(f"   Result: {'✓ Sent' if success else '✗ Skipped (below threshold)'}")


def demo_price_alerts():
    """Demonstrate price threshold alerts."""
    print("\n" + "=" * 60)
    print("DEMO 3: Price Alerts")
    print("=" * 60)

    manager = get_alert_manager()

    # Test price alerts
    test_prices = [
        {
            'instrument': 'EUR_USD',
            'current_price': 1.0875,
            'threshold': 1.0850,
            'direction': 'above',
        },
        {
            'instrument': 'XAU_USD',
            'current_price': 1945.50,
            'threshold': 1950.00,
            'direction': 'below',
        },
    ]

    for i, price_data in enumerate(test_prices, 1):
        print(f"\n{i}. Sending price alert for {price_data['instrument']} "
              f"({price_data['direction']} {price_data['threshold']})...")

        success = manager.send_price_alert(**price_data)
        print(f"   Result: {'✓ Sent' if success else '✗ Failed'}")


def demo_risk_alerts():
    """Demonstrate risk management alerts."""
    print("\n" + "=" * 60)
    print("DEMO 4: Risk Management Alerts")
    print("=" * 60)

    manager = get_alert_manager()

    # Test risk alerts with different severity levels
    test_risks = [
        {
            'subject': 'Portfolio Drawdown',
            'message': 'Portfolio drawdown has reached 8%. Consider reducing exposure.',
            'severity': 'medium',
        },
        {
            'subject': 'Position Limit Exceeded',
            'message': 'Total open positions (15) exceed the recommended limit of 10.',
            'severity': 'high',
        },
        {
            'subject': 'Margin Call Warning',
            'message': 'CRITICAL: Account margin has fallen below 25%. Close positions immediately!',
            'severity': 'critical',
        },
    ]

    for i, risk_data in enumerate(test_risks, 1):
        print(f"\n{i}. Sending {risk_data['severity'].upper()} risk alert: {risk_data['subject']}...")

        success = manager.send_risk_alert(**risk_data)
        print(f"   Result: {'✓ Sent' if success else '✗ Failed'}")


def demo_system_alerts():
    """Demonstrate system status alerts."""
    print("\n" + "=" * 60)
    print("DEMO 5: System Status Alerts")
    print("=" * 60)

    manager = get_alert_manager()

    # Test system alerts
    test_systems = [
        {
            'subject': 'Database Connection Restored',
            'message': 'Connection to TimescaleDB has been successfully restored after 3 retries.',
            'severity': 'low',
        },
        {
            'subject': 'API Rate Limit Warning',
            'message': 'OANDA API usage is at 85% of hourly limit. Reducing polling frequency.',
            'severity': 'medium',
        },
        {
            'subject': 'Data Feed Interrupted',
            'message': 'Market data feed has been interrupted. Unable to update prices for 5+ minutes.',
            'severity': 'high',
        },
    ]

    for i, system_data in enumerate(test_systems, 1):
        print(f"\n{i}. Sending {system_data['severity'].upper()} system alert: {system_data['subject']}...")

        success = manager.send_system_alert(**system_data)
        print(f"   Result: {'✓ Sent' if success else '✗ Failed'}")


def demo_rate_limiting():
    """Demonstrate rate limiting and deduplication."""
    print("\n" + "=" * 60)
    print("DEMO 6: Rate Limiting & Deduplication")
    print("=" * 60)

    manager = get_alert_manager()

    # Send same alert multiple times
    print("\n1. Sending identical alerts (should be deduplicated)...")

    for i in range(3):
        print(f"\n   Attempt {i+1}:")
        success = manager.send_alert(
            subject="Test Duplicate Alert",
            message="This is a test of the deduplication system.",
            priority=AlertPriority.LOW,
            alert_type=AlertType.SYSTEM,
            instrument="EUR_USD"
        )
        print(f"   Result: {'✓ Sent' if success else '✗ Blocked (duplicate)'}")

    # Force send duplicate
    print("\n2. Force sending duplicate (bypassing deduplication)...")
    success = manager.send_alert(
        subject="Test Duplicate Alert",
        message="This is a test of the deduplication system.",
        priority=AlertPriority.LOW,
        alert_type=AlertType.SYSTEM,
        instrument="EUR_USD",
        force=True
    )
    print(f"   Result: {'✓ Sent (forced)' if success else '✗ Failed'}")


def demo_alert_statistics():
    """Demonstrate alert statistics."""
    print("\n" + "=" * 60)
    print("DEMO 7: Alert Statistics")
    print("=" * 60)

    manager = get_alert_manager()

    # Get statistics
    print("\nFetching alert statistics for the last 24 hours...")
    stats = manager.get_alert_statistics(hours=24)

    print(f"\nTotal Alerts: {stats.get('total_alerts', 0)}")
    print(f"Successful: {stats.get('successful', 0)}")
    print(f"Failed: {stats.get('failed', 0)}")
    print(f"Success Rate: {stats.get('success_rate', 0):.1%}")

    print("\nAlerts by Type:")
    for alert_type, count in stats.get('by_type', {}).items():
        print(f"  - {alert_type}: {count}")

    print("\nAlerts by Priority:")
    for priority, count in stats.get('by_priority', {}).items():
        print(f"  - {priority}: {count}")

    print("\nAlerts by Channel:")
    for channel, count in stats.get('by_channel', {}).items():
        print(f"  - {channel}: {count}")


def demo_convenience_functions():
    """Demonstrate convenience functions."""
    print("\n" + "=" * 60)
    print("DEMO 8: Convenience Functions")
    print("=" * 60)

    print("\n1. Using send_signal_alert() convenience function...")
    success = send_signal_alert(
        instrument="EUR_USD",
        timeframe="D1",
        signal_type="BUY",
        confidence=0.88,
        entry_price=1.0900,
        strategy="Daily Trend Following"
    )
    print(f"   Result: {'✓ Sent' if success else '✗ Failed'}")

    print("\n2. Using send_system_alert() convenience function...")
    success = send_system_alert(
        subject="Demo Complete",
        message="Alert system demonstration completed successfully!",
        severity="low"
    )
    print(f"   Result: {'✓ Sent' if success else '✗ Failed'}")


def main():
    """Run all alert system demos."""
    print("=" * 60)
    print("ScreenerIII Alert System Demo")
    print("=" * 60)

    # Initialize database (creates alert_history table)
    print("\nInitializing database...")
    try:
        db = init_db(setup_timescaledb=False)
        print("✓ Database initialized successfully")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        print("  (Alert history will not be saved, but alerts will still work)")

    # Run demos
    try:
        demo_basic_alerts()
        input("\nPress Enter to continue to signal alerts demo...")

        demo_signal_alerts()
        input("\nPress Enter to continue to price alerts demo...")

        demo_price_alerts()
        input("\nPress Enter to continue to risk alerts demo...")

        demo_risk_alerts()
        input("\nPress Enter to continue to system alerts demo...")

        demo_system_alerts()
        input("\nPress Enter to continue to rate limiting demo...")

        demo_rate_limiting()
        input("\nPress Enter to continue to statistics demo...")

        demo_alert_statistics()
        input("\nPress Enter to continue to convenience functions demo...")

        demo_convenience_functions()

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        print(f"\n\nError during demo: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)
    print("\nTo configure alerts for your environment:")
    print("  1. Copy .env.example to .env")
    print("  2. Update alert configuration variables")
    print("  3. Enable desired channels (email, desktop, telegram)")
    print("  4. Configure channel-specific settings (SMTP, bot tokens, etc.)")
    print("\nSee .env.example for detailed configuration options.")
    print("=" * 60)


if __name__ == '__main__':
    main()
