"""
Example integration of ScreenerIII monitoring system with the main application.

This example demonstrates how to integrate the monitoring, health checking,
and performance tracking capabilities into your screener application.
"""

import time
import logging
import threading
from typing import Optional

# Import monitoring components
from src.core.monitoring import (
    get_metrics_collector,
    get_health_checker,
    get_performance_monitor,
    get_prometheus_exporter
)
from src.core.logger import get_logger


class MonitoredScreener:
    """
    Example wrapper around ScreenerIII that includes monitoring.

    This class demonstrates best practices for integrating monitoring
    into your trading screener application.
    """

    def __init__(self, check_interval: float = 10.0, health_check_interval: float = 60.0):
        """
        Initialize the monitored screener.

        Args:
            check_interval: Interval between main loop iterations (seconds)
            health_check_interval: Interval between health checks (seconds)
        """
        self.logger = get_logger(__name__)
        self.check_interval = check_interval
        self.health_check_interval = health_check_interval

        # Initialize monitoring components
        self.metrics = get_metrics_collector()
        self.health_checker = get_health_checker()
        self.monitor = get_performance_monitor()
        self.exporter = get_prometheus_exporter(port=8000)

        # State
        self.running = False
        self.last_health_check = 0

    def start(self) -> None:
        """Start the screener with monitoring."""
        try:
            # Start Prometheus exporter
            self.exporter.start()
            self.logger.info("Prometheus exporter started on port 8000")

            # Start health check thread
            health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
            health_thread.start()

            self.running = True
            self.logger.info("Monitored screener started")

        except Exception as e:
            self.logger.error(f"Failed to start screener: {e}", exc_info=True)
            raise

    def stop(self) -> None:
        """Stop the screener."""
        self.running = False
        self.logger.info("Monitored screener stopped")

    def run_loop(self) -> None:
        """Run the main screener loop with monitoring."""
        self.start()

        try:
            while self.running:
                try:
                    loop_start = time.time()

                    # Track overall loop execution
                    with self.monitor.track_operation('screener_main_loop'):
                        # Update system metrics
                        self.metrics.update_system_metrics()

                        # Run screener analysis
                        self._run_analysis()

                    # Record loop execution time
                    loop_duration = time.time() - loop_start
                    self.monitor.record_loop_execution(loop_duration)

                    if loop_duration > 1.0:
                        self.logger.warning(
                            f"Slow loop iteration: {loop_duration:.2f}s "
                            f"(threshold: 1.0s)"
                        )

                    # Sleep until next iteration
                    remaining_time = self.check_interval - loop_duration
                    if remaining_time > 0:
                        time.sleep(remaining_time)

                except Exception as e:
                    self.logger.error(f"Error in main loop: {e}", exc_info=True)
                    time.sleep(self.check_interval)

        except KeyboardInterrupt:
            self.logger.info("Screener interrupted by user")
        finally:
            self.stop()

    def _run_analysis(self) -> None:
        """Run the actual screener analysis with monitoring."""
        # Fetch market data
        with self.monitor.track_operation('fetch_market_data'):
            market_data = self._fetch_market_data()

        if not market_data:
            self.logger.warning("No market data retrieved")
            return

        # Analyze data
        with self.monitor.track_operation('analyze_market_data'):
            signals = self._analyze_data(market_data)

        # Process signals
        with self.monitor.track_operation('process_signals'):
            for signal in signals:
                self._process_signal(signal)

        # Update positions
        with self.monitor.track_operation('update_positions'):
            positions = self._get_positions()
            self.metrics.set_active_positions(len(positions))

    def _fetch_market_data(self) -> Optional[dict]:
        """Fetch market data with monitoring."""
        try:
            api_start = time.time()

            # Simulate API call
            # In real implementation, this would call OANDA API
            time.sleep(0.1)  # Simulate API latency
            data = {
                'EURUSD': {'bid': 1.0850, 'ask': 1.0851},
                'GBPUSD': {'bid': 1.2650, 'ask': 1.2651},
            }

            # Record metrics
            latency = time.time() - api_start
            self.metrics.record_api_call(latency=latency, success=True)

            # Update prices
            for symbol, price_data in data.items():
                mid_price = (price_data['bid'] + price_data['ask']) / 2
                self.metrics.set_current_price(symbol, mid_price)

            return data

        except Exception as e:
            self.logger.error(f"Error fetching market data: {e}")
            self.metrics.record_api_call(latency=0.0, success=False)
            return None

    def _analyze_data(self, market_data: dict) -> list:
        """Analyze market data and generate signals with monitoring."""
        signals = []

        try:
            for symbol, prices in market_data.items():
                # Simulate signal generation
                # In real implementation, this would run your strategy
                confidence = 0.75  # Simulated confidence

                if confidence > 0.6:
                    signal = {
                        'symbol': symbol,
                        'type': 'BUY' if True else 'SELL',
                        'confidence': confidence,
                        'price': prices['bid']
                    }
                    signals.append(signal)

                    # Record signal metrics
                    self.metrics.record_signal(
                        signal_type=signal['type'],
                        confidence=confidence
                    )

            return signals

        except Exception as e:
            self.logger.error(f"Error analyzing data: {e}")
            return []

    def _process_signal(self, signal: dict) -> None:
        """Process a signal with monitoring."""
        try:
            # Simulate trade execution
            # In real implementation, this would submit orders
            time.sleep(0.05)  # Simulate execution latency

            self.metrics.record_trade(status='OPENED')
            self.logger.info(
                f"Signal processed: {signal['type']} {signal['symbol']} "
                f"@ {signal['price']} (confidence: {signal['confidence']:.2%})"
            )

        except Exception as e:
            self.logger.error(f"Error processing signal: {e}")
            self.metrics.record_trade(status='FAILED')

    def _get_positions(self) -> list:
        """Get current positions."""
        # Simulate fetching positions
        return []

    def _health_check_loop(self) -> None:
        """Background thread for periodic health checks."""
        while self.running:
            try:
                time.sleep(self.health_check_interval)

                if not self.running:
                    break

                # Perform health check
                health_status = self.health_checker.get_health_status()

                # Log health status
                overall = health_status['overall_status']
                self.logger.info(f"Health check: {overall}")

                # Log component details
                for component, info in health_status['components'].items():
                    if info['status'] != 'HEALTHY':
                        self.logger.warning(
                            f"  {component}: {info['status']} - {info['message']}"
                        )

            except Exception as e:
                self.logger.error(f"Error in health check thread: {e}", exc_info=True)

    def print_stats(self) -> None:
        """Print operation statistics."""
        stats = self.monitor.get_operation_stats()

        if not stats:
            print("No operation statistics available")
            return

        print("\n" + "=" * 60)
        print("Operation Performance Statistics")
        print("=" * 60)

        for op_name in sorted(stats.keys()):
            op_stats = stats[op_name]
            print(f"\n{op_name}:")
            print(f"  Count:    {op_stats['count']:>6}")
            print(f"  Min:      {op_stats['min']:>6.3f}s")
            print(f"  Max:      {op_stats['max']:>6.3f}s")
            print(f"  Average:  {op_stats['avg']:>6.3f}s")

        print("\n" + "=" * 60 + "\n")


def main():
    """Main entry point demonstrating monitoring integration."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = get_logger(__name__)
    logger.info("Starting ScreenerIII with monitoring")

    # Create and run monitored screener
    screener = MonitoredScreener(
        check_interval=10.0,
        health_check_interval=30.0
    )

    try:
        screener.run_loop()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        screener.stop()
    finally:
        # Print final statistics
        screener.print_stats()
        logger.info("ScreenerIII monitoring example completed")


if __name__ == '__main__':
    main()
