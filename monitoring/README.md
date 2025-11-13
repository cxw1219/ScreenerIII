# ScreenerIII Performance Monitoring System

Comprehensive performance monitoring and health checking system for ScreenerIII trading application.

## Features

### 1. MetricsCollector
Tracks all application metrics using Prometheus client library:

- **API Metrics**
  - `screener_api_calls_total` - Total API calls
  - `screener_api_errors_total` - Total API errors
  - `screener_api_latency_seconds` - API response latency (Histogram)

- **Signal Metrics**
  - `screener_signals_generated_total` - Total signals by type
  - `screener_signal_confidence` - Signal confidence distribution

- **Database Metrics**
  - `screener_database_operations_total` - Total DB operations by type
  - `screener_database_latency_seconds` - DB operation latency

- **Performance Metrics**
  - `screener_loop_duration_seconds` - Main loop execution time
  - `screener_memory_usage_bytes` - Current memory usage
  - `screener_cpu_percent` - Current CPU usage
  - `screener_disk_usage_bytes` - Disk usage by mount point

- **Trade Metrics**
  - `screener_trades_total` - Total trades by status
  - `screener_trade_profit_loss` - Trade profit/loss distribution
  - `screener_active_positions` - Number of active positions
  - `screener_current_price` - Current price by symbol

- **Health Metrics**
  - `screener_api_connectivity` - API health (1=healthy, 0=unhealthy)
  - `screener_database_connectivity` - Database health
  - `screener_health_check_timestamp` - Last health check time

### 2. HealthCheck
Monitors system health across multiple components:

- **API Connectivity** - Tests connection to OANDA API
- **Database Connectivity** - Tests connection to database
- **Disk Space** - Monitors available disk space
- **Memory Usage** - Monitors system memory consumption

Health status levels:
- `HEALTHY` - All systems operating normally
- `DEGRADED` - One or more systems showing warning signs
- `UNHEALTHY` - Critical issues detected

### 3. PerformanceMonitor
Tracks performance metrics and detects degradation:

- Records operation execution times with context manager
- Logs slow operations (configurable threshold, default 1 second)
- Alerts on memory leaks and significant memory increases
- Maintains operation statistics (min, max, avg, count)

### 4. PrometheusExporter
HTTP server for Prometheus scraping:

- Listens on `localhost:8000` by default
- `/metrics` endpoint - Prometheus format metrics
- `/health` endpoint - Health check results

## Installation

### 1. Install Dependencies
```bash
pip install prometheus-client>=0.19.0 psutil>=5.9.0
```

Or add to requirements.txt and install:
```bash
pip install -r requirements.txt
```

### 2. Initialize Monitoring in Your Application

```python
from src.core.monitoring import (
    get_metrics_collector,
    get_health_checker,
    get_performance_monitor,
    get_prometheus_exporter
)

# Initialize components
metrics = get_metrics_collector()
health = get_health_checker()
monitor = get_performance_monitor()
exporter = get_prometheus_exporter(port=8000)

# Start Prometheus HTTP server
exporter.start()
```

## Usage Examples

### Record API Calls
```python
import time
from src.core.monitoring import get_metrics_collector

metrics = get_metrics_collector()

# Record a successful API call
start = time.time()
# ... API call code ...
latency = time.time() - start
metrics.record_api_call(latency=latency, success=True)

# Record a failed API call
metrics.record_api_call(latency=0.5, success=False)
```

### Record Signals
```python
metrics.record_signal(signal_type='BUY', confidence=0.85)
metrics.record_signal(signal_type='SELL', confidence=0.72)
```

### Record Database Operations
```python
metrics.record_database_operation(operation_type='INSERT', latency=0.02)
metrics.record_database_operation(operation_type='SELECT', latency=0.01)
```

### Track Operation Performance
```python
from src.core.monitoring import get_performance_monitor

monitor = get_performance_monitor()

with monitor.track_operation('data_fetch'):
    # Your operation code here
    fetch_market_data()
```

### Update System Metrics
```python
metrics.update_system_metrics()
metrics.set_active_positions(count=5)
metrics.set_current_price(symbol='EURUSD', price=1.0850)
```

### Check System Health
```python
from src.core.monitoring import get_health_checker

health = get_health_checker()
status = health.get_health_status()

print(f"Overall Status: {status['overall_status']}")
for component, info in status['components'].items():
    print(f"{component}: {info['status']} - {info['message']}")
```

### Get Operation Statistics
```python
stats = monitor.get_operation_stats()
for op_name, op_stats in stats.items():
    print(f"{op_name}:")
    print(f"  Min: {op_stats['min']:.3f}s")
    print(f"  Max: {op_stats['max']:.3f}s")
    print(f"  Avg: {op_stats['avg']:.3f}s")
    print(f"  Count: {op_stats['count']}")
```

## Prometheus Configuration

### Setup Prometheus
1. Install Prometheus from https://prometheus.io/download/
2. Copy `prometheus.yml` to your Prometheus installation
3. Update the configuration if needed (targets, scrape intervals, etc.)

### Run Prometheus
```bash
# With custom config
./prometheus --config.file=monitoring/prometheus.yml

# Prometheus will be available at http://localhost:9090
```

### Query Metrics
Once running, visit http://localhost:9090 to query metrics:
- `screener_api_calls_total` - View total API calls
- `rate(screener_api_calls_total[5m])` - API call rate
- `screener_memory_usage_bytes / 1024 / 1024` - Memory in MB
- `rate(screener_signals_generated_total[5m])` - Signal generation rate

## Grafana Integration

### Setup Grafana Dashboard
1. Install Grafana from https://grafana.com/grafana/download
2. Add Prometheus as data source (http://localhost:9090)
3. Import `grafana-dashboard.json`:
   - Go to Dashboards > Import
   - Upload the JSON file
   - Select Prometheus as data source

### Dashboard Panels
The dashboard includes:
- API Call Rate
- API Error Rate
- API Latency (p95, p99)
- Signals Generated Rate
- Main Loop Duration (p95, p99)
- Memory Usage
- CPU Usage
- Active Positions
- Trade Rate
- Database Latency (p95, p99)

## Simple Dashboard

For a quick view without Prometheus/Grafana:

1. Open `dashboard.html` in a web browser
2. Metrics will auto-refresh every 10 seconds
3. Displays real-time system metrics and health status

Note: The HTML dashboard expects the application to be running with metrics exporter on port 8000.

## Configuration

### HealthCheck Thresholds
```python
health = get_health_checker(
    api_timeout=5.0,  # Timeout for API checks (seconds)
    memory_threshold_percent=90.0,  # Memory alert threshold
    disk_threshold_percent=90.0  # Disk alert threshold
)
```

### PerformanceMonitor Thresholds
```python
monitor = get_performance_monitor(
    slow_operation_threshold=1.0,  # Log operations longer than 1s
    memory_increase_threshold=50 * 1024 * 1024  # Alert on 50MB increase
)
```

### PrometheusExporter Configuration
```python
exporter = get_prometheus_exporter(
    port=8000,  # HTTP server port
    host='0.0.0.0'  # Bind to all interfaces
)
exporter.start()
```

## Metrics Endpoints

Once the exporter is started:

### Metrics Endpoint
```
GET http://localhost:8000/metrics
```

Returns all metrics in Prometheus text format.

### Health Endpoint
```
GET http://localhost:8000/health
```

Returns JSON health status:
```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "overall_status": "HEALTHY",
  "components": {
    "api": {
      "status": "HEALTHY",
      "message": "API connectivity healthy"
    },
    "database": {
      "status": "HEALTHY",
      "message": "Database connectivity healthy"
    },
    "disk": {
      "status": "HEALTHY",
      "message": "Disk usage normal: 45.2%"
    },
    "memory": {
      "status": "HEALTHY",
      "message": "Memory usage normal: 62.1% system, 8.3% process"
    }
  }
}
```

## Integration with Main Application

### In main.py or run script:
```python
from src.core.monitoring import (
    get_metrics_collector,
    get_performance_monitor,
    get_prometheus_exporter
)

def main():
    # Initialize monitoring
    metrics = get_metrics_collector()
    monitor = get_performance_monitor()
    exporter = get_prometheus_exporter(port=8000)
    exporter.start()

    # Main loop
    while True:
        loop_start = time.time()

        with monitor.track_operation('screener_loop'):
            # Update system metrics
            metrics.update_system_metrics()

            # Your screener logic here
            # ...

            # Track API calls
            api_start = time.time()
            result = fetch_api_data()
            metrics.record_api_call(
                latency=time.time() - api_start,
                success=True
            )

            # Generate signals
            signals = analyze_data(result)
            for signal in signals:
                metrics.record_signal(
                    signal_type=signal['type'],
                    confidence=signal['confidence']
                )

        # Record loop execution time
        loop_duration = time.time() - loop_start
        monitor.record_loop_execution(loop_duration)

        time.sleep(10)

if __name__ == '__main__':
    main()
```

## Best Practices

1. **Initialize Early** - Start the Prometheus exporter early in application startup
2. **Regular Updates** - Call `metrics.update_system_metrics()` periodically
3. **Contextual Tracking** - Use `track_operation()` context manager for automatic timing
4. **Alert Thresholds** - Adjust thresholds based on your system's characteristics
5. **Retention** - Configure Prometheus retention policy based on your needs
6. **Security** - Consider adding authentication/TLS if exposing metrics publicly

## Troubleshooting

### Port 8000 Already in Use
Change the exporter port:
```python
exporter = get_prometheus_exporter(port=8001)
```

### Metrics Not Appearing
1. Ensure application is running with exporter started
2. Check that application is recording metrics
3. Verify Prometheus can reach `localhost:8000`
4. Check Prometheus logs for scrape errors

### High Memory Usage Alerts
1. Check if there are memory leaks in your code
2. Review operation statistics for slow operations
3. Consider increasing memory threshold if normal for your workload

### Database Connectivity Issues
1. Verify database is running and accessible
2. Check database credentials in environment variables
3. Ensure network connectivity

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Prometheus Python Client](https://github.com/prometheus/client_python)
- [Grafana Documentation](https://grafana.com/docs/)
- [Metric Types](https://prometheus.io/docs/concepts/metric_types/)
