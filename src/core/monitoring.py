"""
Performance Monitoring System for ScreenerIII

This module provides comprehensive monitoring capabilities including:
- Prometheus metrics collection
- Health checks for API, database, disk, and memory
- Performance monitoring and alerting
- HTTP endpoint for Prometheus scraping
"""

import os
import psutil
import logging
import time
from typing import Dict, Tuple, Optional
from enum import Enum
from contextlib import contextmanager
from threading import Lock
from datetime import datetime
from pathlib import Path

# Prometheus client imports
from prometheus_client import Counter, Histogram, Gauge, Summary, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import start_http_server

from .logger import get_logger


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


class MetricsCollector:
    """
    Prometheus metrics collector for ScreenerIII.

    Tracks various metrics including API calls, errors, latency,
    signals generated, and system resource usage.
    """

    _instance: Optional['MetricsCollector'] = None
    _lock = Lock()

    def __new__(cls) -> 'MetricsCollector':
        """Implement singleton pattern for metrics collector."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize metrics collector with Prometheus metrics."""
        if hasattr(self, '_initialized'):
            return

        self.logger = get_logger(__name__)
        self.registry = CollectorRegistry()

        # API Metrics
        self.api_calls_total = Counter(
            'screener_api_calls_total',
            'Total number of API calls made',
            registry=self.registry
        )

        self.api_errors_total = Counter(
            'screener_api_errors_total',
            'Total number of API errors',
            registry=self.registry
        )

        self.api_latency_seconds = Histogram(
            'screener_api_latency_seconds',
            'API response latency in seconds',
            buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry
        )

        # Signal Metrics
        self.signals_generated_total = Counter(
            'screener_signals_generated_total',
            'Total number of signals generated',
            labelnames=['signal_type'],
            registry=self.registry
        )

        self.signal_confidence = Summary(
            'screener_signal_confidence',
            'Signal confidence distribution',
            registry=self.registry
        )

        # Database Metrics
        self.database_operations_total = Counter(
            'screener_database_operations_total',
            'Total number of database operations',
            labelnames=['operation_type'],
            registry=self.registry
        )

        self.database_latency_seconds = Histogram(
            'screener_database_latency_seconds',
            'Database operation latency in seconds',
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
            registry=self.registry
        )

        # Performance Metrics
        self.loop_duration_seconds = Histogram(
            'screener_loop_duration_seconds',
            'Main loop execution time in seconds',
            buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
            registry=self.registry
        )

        self.memory_usage_bytes = Gauge(
            'screener_memory_usage_bytes',
            'Current memory usage in bytes',
            registry=self.registry
        )

        self.cpu_percent = Gauge(
            'screener_cpu_percent',
            'Current CPU usage percentage',
            registry=self.registry
        )

        self.disk_usage_bytes = Gauge(
            'screener_disk_usage_bytes',
            'Current disk usage in bytes',
            labelnames=['mount_point'],
            registry=self.registry
        )

        # Trade Performance Metrics
        self.trades_total = Counter(
            'screener_trades_total',
            'Total number of trades',
            labelnames=['status'],
            registry=self.registry
        )

        self.trade_profit_loss = Summary(
            'screener_trade_profit_loss',
            'Trade profit/loss distribution',
            registry=self.registry
        )

        self.active_positions = Gauge(
            'screener_active_positions',
            'Number of active positions',
            registry=self.registry
        )

        self.current_price = Gauge(
            'screener_current_price',
            'Current price of instrument',
            labelnames=['symbol'],
            registry=self.registry
        )

        # Health Metrics
        self.health_check_timestamp = Gauge(
            'screener_health_check_timestamp',
            'Last health check timestamp',
            registry=self.registry
        )

        self.api_connectivity = Gauge(
            'screener_api_connectivity',
            'API connectivity status (1=healthy, 0=unhealthy)',
            registry=self.registry
        )

        self.database_connectivity = Gauge(
            'screener_database_connectivity',
            'Database connectivity status (1=healthy, 0=unhealthy)',
            registry=self.registry
        )

        self._initialized = True
        self.logger.info("MetricsCollector initialized")

    def record_api_call(self, latency: float, success: bool = True) -> None:
        """
        Record an API call metric.

        Args:
            latency: Response time in seconds
            success: Whether the call was successful
        """
        self.api_calls_total.inc()
        self.api_latency_seconds.observe(latency)

        if not success:
            self.api_errors_total.inc()

    def record_signal(self, signal_type: str, confidence: float) -> None:
        """
        Record a signal generation event.

        Args:
            signal_type: Type of signal (e.g., 'BUY', 'SELL')
            confidence: Confidence level (0-1)
        """
        self.signals_generated_total.labels(signal_type=signal_type).inc()
        self.signal_confidence.observe(confidence)

    def record_database_operation(self, operation_type: str, latency: float) -> None:
        """
        Record a database operation metric.

        Args:
            operation_type: Type of operation (e.g., 'INSERT', 'SELECT', 'UPDATE')
            latency: Operation time in seconds
        """
        self.database_operations_total.labels(operation_type=operation_type).inc()
        self.database_latency_seconds.observe(latency)

    def record_loop_execution(self, duration: float) -> None:
        """
        Record main loop execution time.

        Args:
            duration: Loop execution time in seconds
        """
        self.loop_duration_seconds.observe(duration)

    def update_system_metrics(self) -> None:
        """Update system resource metrics (memory, CPU, disk)."""
        try:
            # Memory usage
            process = psutil.Process()
            memory_info = process.memory_info()
            self.memory_usage_bytes.set(memory_info.rss)

            # CPU usage
            cpu_percent = process.cpu_percent(interval=0.1)
            self.cpu_percent.set(cpu_percent)

            # Disk usage
            try:
                disk_usage = psutil.disk_usage('/')
                self.disk_usage_bytes.labels(mount_point='/').set(disk_usage.used)
            except Exception as e:
                self.logger.warning(f"Failed to get disk usage: {e}")

        except Exception as e:
            self.logger.error(f"Error updating system metrics: {e}")

    def record_trade(self, status: str, profit_loss: Optional[float] = None) -> None:
        """
        Record a trade event.

        Args:
            status: Trade status (e.g., 'OPENED', 'CLOSED', 'FAILED')
            profit_loss: Profit/loss value if trade is closed
        """
        self.trades_total.labels(status=status).inc()

        if profit_loss is not None:
            self.trade_profit_loss.observe(profit_loss)

    def set_active_positions(self, count: int) -> None:
        """
        Set the number of active positions.

        Args:
            count: Number of active positions
        """
        self.active_positions.set(count)

    def set_current_price(self, symbol: str, price: float) -> None:
        """
        Set the current price for a symbol.

        Args:
            symbol: Trading symbol (e.g., 'EURUSD')
            price: Current price
        """
        self.current_price.labels(symbol=symbol).set(price)

    def set_api_connectivity(self, healthy: bool) -> None:
        """
        Set API connectivity status.

        Args:
            healthy: True if API is healthy
        """
        self.api_connectivity.set(1 if healthy else 0)

    def set_database_connectivity(self, healthy: bool) -> None:
        """
        Set database connectivity status.

        Args:
            healthy: True if database is healthy
        """
        self.database_connectivity.set(1 if healthy else 0)

    def get_metrics(self) -> bytes:
        """
        Get all metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics as bytes
        """
        return generate_latest(self.registry)

    @contextmanager
    def track_latency(self, metric_type: str):
        """
        Context manager to track operation latency.

        Args:
            metric_type: Type of operation ('api' or 'database')

        Usage:
            with metrics.track_latency('api'):
                # API call code here
        """
        start_time = time.time()
        try:
            yield
        finally:
            latency = time.time() - start_time
            if metric_type == 'api':
                self.api_latency_seconds.observe(latency)
            elif metric_type == 'database':
                self.database_latency_seconds.observe(latency)


class HealthCheck:
    """
    Health checker for ScreenerIII system components.

    Monitors API connectivity, database connectivity, disk space, and memory usage.
    """

    def __init__(self,
                 api_timeout: float = 5.0,
                 memory_threshold_percent: float = 90.0,
                 disk_threshold_percent: float = 90.0):
        """
        Initialize health checker.

        Args:
            api_timeout: Timeout for API connectivity check in seconds
            memory_threshold_percent: Threshold for memory usage percentage
            disk_threshold_percent: Threshold for disk usage percentage
        """
        self.logger = get_logger(__name__)
        self.api_timeout = api_timeout
        self.memory_threshold_percent = memory_threshold_percent
        self.disk_threshold_percent = disk_threshold_percent
        self.metrics = MetricsCollector()
        self.last_check_time: Optional[float] = None

    def check_api_connectivity(self) -> Tuple[bool, str]:
        """
        Check OANDA API connectivity.

        Returns:
            Tuple of (is_healthy, message)
        """
        try:
            from ..data.oanda_client import get_oanda_client

            client = get_oanda_client()
            if client is None:
                return False, "OANDA client not initialized"

            # Try to get account info
            try:
                # This is a simple connectivity test
                response = client.request('GET', '/v3/accounts', timeout=self.api_timeout)

                if response.status_code == 200:
                    self.metrics.set_api_connectivity(True)
                    return True, "API connectivity healthy"
                else:
                    self.metrics.set_api_connectivity(False)
                    return False, f"API returned status code {response.status_code}"
            except Exception as e:
                self.metrics.set_api_connectivity(False)
                return False, f"API connectivity error: {str(e)}"

        except ImportError:
            self.logger.warning("OANDA client not available for health check")
            return True, "OANDA client not available (skipped)"

    def check_database_connectivity(self) -> Tuple[bool, str]:
        """
        Check database connectivity.

        Returns:
            Tuple of (is_healthy, message)
        """
        try:
            from .database import get_db_session

            try:
                session = get_db_session()
                # Try a simple query to test connectivity
                session.execute('SELECT 1')
                session.close()

                self.metrics.set_database_connectivity(True)
                return True, "Database connectivity healthy"
            except Exception as e:
                self.metrics.set_database_connectivity(False)
                return False, f"Database error: {str(e)}"

        except ImportError:
            self.logger.warning("Database module not available for health check")
            return True, "Database module not available (skipped)"

    def check_disk_space(self) -> Tuple[bool, str]:
        """
        Check available disk space.

        Returns:
            Tuple of (is_healthy, message)
        """
        try:
            disk_usage = psutil.disk_usage('/')
            usage_percent = disk_usage.percent

            if usage_percent > self.disk_threshold_percent:
                return False, f"Disk usage critical: {usage_percent:.1f}%"
            elif usage_percent > (self.disk_threshold_percent - 10):
                return True, f"Disk usage high: {usage_percent:.1f}%"
            else:
                return True, f"Disk usage normal: {usage_percent:.1f}%"

        except Exception as e:
            self.logger.error(f"Error checking disk space: {e}")
            return False, f"Disk check error: {str(e)}"

    def check_memory_usage(self) -> Tuple[bool, str]:
        """
        Check available memory.

        Returns:
            Tuple of (is_healthy, message)
        """
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            virtual_memory = psutil.virtual_memory()

            process_memory_percent = (memory_info.rss / virtual_memory.total) * 100
            system_memory_percent = virtual_memory.percent

            if system_memory_percent > self.memory_threshold_percent:
                return False, f"Memory usage critical: {system_memory_percent:.1f}% system"
            elif system_memory_percent > (self.memory_threshold_percent - 10):
                return True, f"Memory usage high: {system_memory_percent:.1f}% system, {process_memory_percent:.1f}% process"
            else:
                return True, f"Memory usage normal: {system_memory_percent:.1f}% system, {process_memory_percent:.1f}% process"

        except Exception as e:
            self.logger.error(f"Error checking memory: {e}")
            return False, f"Memory check error: {str(e)}"

    def get_health_status(self) -> Dict[str, any]:
        """
        Get comprehensive health status of all components.

        Returns:
            Dictionary with health information for all components
        """
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': HealthStatus.HEALTHY.value,
            'components': {}
        }

        # Check each component
        components_to_check = {
            'api': self.check_api_connectivity,
            'database': self.check_database_connectivity,
            'disk': self.check_disk_space,
            'memory': self.check_memory_usage
        }

        degraded_count = 0
        unhealthy_count = 0

        for component_name, check_func in components_to_check.items():
            is_healthy, message = check_func()

            if is_healthy:
                status = HealthStatus.HEALTHY.value
            else:
                status = HealthStatus.UNHEALTHY.value
                unhealthy_count += 1

            health_status['components'][component_name] = {
                'status': status,
                'message': message
            }

        # Determine overall status
        if unhealthy_count > 0:
            health_status['overall_status'] = HealthStatus.UNHEALTHY.value
        elif degraded_count > 0:
            health_status['overall_status'] = HealthStatus.DEGRADED.value
        else:
            health_status['overall_status'] = HealthStatus.HEALTHY.value

        # Update timestamp in metrics
        self.metrics.health_check_timestamp.set(time.time())
        self.last_check_time = time.time()

        return health_status


class PerformanceMonitor:
    """
    Monitor performance metrics and alert on degradation.

    Tracks loop execution times, memory usage, and logs slow operations.
    """

    def __init__(self,
                 slow_operation_threshold: float = 1.0,
                 memory_increase_threshold: float = 50 * 1024 * 1024):
        """
        Initialize performance monitor.

        Args:
            slow_operation_threshold: Threshold for slow operations in seconds
            memory_increase_threshold: Threshold for memory increase in bytes
        """
        self.logger = get_logger(__name__)
        self.metrics = MetricsCollector()
        self.slow_operation_threshold = slow_operation_threshold
        self.memory_increase_threshold = memory_increase_threshold
        self.previous_memory: Optional[int] = None
        self.operation_times: Dict[str, list] = {}

    @contextmanager
    def track_operation(self, operation_name: str, log_level: str = 'DEBUG'):
        """
        Context manager to track and monitor an operation.

        Args:
            operation_name: Name of the operation
            log_level: Logging level for slow operation warnings

        Usage:
            with monitor.track_operation('data_fetch'):
                # Operation code here
        """
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss

        try:
            yield
        finally:
            duration = time.time() - start_time
            end_memory = psutil.Process().memory_info().rss
            memory_delta = end_memory - start_memory

            # Track operation time
            if operation_name not in self.operation_times:
                self.operation_times[operation_name] = []
            self.operation_times[operation_name].append(duration)

            # Keep only last 100 operations
            if len(self.operation_times[operation_name]) > 100:
                self.operation_times[operation_name].pop(0)

            # Log slow operations
            if duration > self.slow_operation_threshold:
                log_func = getattr(self.logger, log_level.lower(), self.logger.debug)
                log_func(
                    f"Slow operation detected: {operation_name} took {duration:.2f}s "
                    f"(threshold: {self.slow_operation_threshold:.2f}s), "
                    f"memory delta: {memory_delta / 1024 / 1024:.2f}MB"
                )

            # Alert on significant memory increase
            if self.previous_memory is not None:
                memory_increase = end_memory - self.previous_memory
                if memory_increase > self.memory_increase_threshold:
                    self.logger.warning(
                        f"Memory increase detected: {memory_increase / 1024 / 1024:.2f}MB "
                        f"(threshold: {self.memory_increase_threshold / 1024 / 1024:.2f}MB) "
                        f"during {operation_name}"
                    )

            self.previous_memory = end_memory

    def record_loop_execution(self, duration: float) -> None:
        """
        Record main loop execution time.

        Args:
            duration: Loop execution time in seconds
        """
        self.metrics.record_loop_execution(duration)

        if duration > self.slow_operation_threshold:
            self.logger.warning(
                f"Slow loop detected: {duration:.2f}s "
                f"(threshold: {self.slow_operation_threshold:.2f}s)"
            )

    def get_operation_stats(self) -> Dict[str, Dict[str, float]]:
        """
        Get statistics for tracked operations.

        Returns:
            Dictionary with min, max, avg times for each operation
        """
        stats = {}

        for operation_name, times in self.operation_times.items():
            if not times:
                continue

            stats[operation_name] = {
                'min': min(times),
                'max': max(times),
                'avg': sum(times) / len(times),
                'count': len(times)
            }

        return stats


class PrometheusExporter:
    """
    HTTP server to export metrics for Prometheus scraping.

    Provides /metrics and /health endpoints.
    """

    def __init__(self,
                 port: int = 8000,
                 host: str = '0.0.0.0'):
        """
        Initialize Prometheus exporter.

        Args:
            port: Port to listen on
            host: Host to bind to
        """
        self.logger = get_logger(__name__)
        self.port = port
        self.host = host
        self.metrics = MetricsCollector()
        self.health_checker = HealthCheck()
        self.server_started = False

    def start(self) -> None:
        """Start the HTTP server for Prometheus scraping."""
        try:
            start_http_server(self.port, addr=self.host, registry=self.metrics.registry)
            self.server_started = True
            self.logger.info(
                f"Prometheus exporter started on {self.host}:{self.port}"
            )
        except Exception as e:
            self.logger.error(f"Failed to start Prometheus exporter: {e}")

    def get_metrics_endpoint(self) -> bytes:
        """
        Get metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics
        """
        return self.metrics.get_metrics()

    def get_health_endpoint(self) -> Dict[str, any]:
        """
        Get health status.

        Returns:
            Health status dictionary
        """
        return self.health_checker.get_health_status()


def get_metrics_collector() -> MetricsCollector:
    """
    Get or create the global metrics collector instance.

    Returns:
        MetricsCollector: The global metrics collector instance
    """
    return MetricsCollector()


def get_health_checker() -> HealthCheck:
    """
    Get a health checker instance.

    Returns:
        HealthCheck: Health checker instance
    """
    return HealthCheck()


def get_performance_monitor() -> PerformanceMonitor:
    """
    Get a performance monitor instance.

    Returns:
        PerformanceMonitor: Performance monitor instance
    """
    return PerformanceMonitor()


def get_prometheus_exporter(port: int = 8000) -> PrometheusExporter:
    """
    Get a Prometheus exporter instance.

    Args:
        port: Port to listen on

    Returns:
        PrometheusExporter: Prometheus exporter instance
    """
    return PrometheusExporter(port=port)


if __name__ == '__main__':
    # Test monitoring system
    import json

    print("Testing Monitoring System...")
    print()

    # Get instances
    metrics = get_metrics_collector()
    health = get_health_checker()
    monitor = get_performance_monitor()
    exporter = get_prometheus_exporter()

    # Simulate some activity
    print("Recording API calls...")
    for _ in range(5):
        metrics.record_api_call(latency=0.5, success=True)
    metrics.record_api_call(latency=0.1, success=False)

    print("Recording signals...")
    metrics.record_signal('BUY', confidence=0.85)
    metrics.record_signal('SELL', confidence=0.72)

    print("Recording database operations...")
    metrics.record_database_operation('INSERT', latency=0.02)
    metrics.record_database_operation('SELECT', latency=0.01)

    print("Recording trades...")
    metrics.record_trade('OPENED')
    metrics.record_trade('CLOSED', profit_loss=150.75)

    # Update system metrics
    print("Updating system metrics...")
    metrics.update_system_metrics()

    # Check health
    print("\nPerforming health checks...")
    health_status = health.get_health_status()
    print(json.dumps(health_status, indent=2))

    print("\nMonitoring test complete!")
