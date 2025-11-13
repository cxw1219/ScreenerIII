#!/bin/bash

# ScreenerIII Monitoring Setup Script
# This script helps set up the monitoring system for ScreenerIII

set -e

echo "=========================================="
echo "ScreenerIII Monitoring Setup"
echo "=========================================="
echo ""

# Check if running in the correct directory
if [ ! -f "requirements.txt" ]; then
    echo "Error: This script must be run from the ScreenerIII root directory"
    exit 1
fi

echo "Step 1: Installing Python dependencies..."
pip install prometheus-client>=0.19.0 psutil>=5.9.0
echo "✓ Dependencies installed"
echo ""

echo "Step 2: Checking for Docker (optional for Prometheus/Grafana)..."
if command -v docker &> /dev/null; then
    echo "✓ Docker found"
    echo ""
    read -p "Do you want to start Prometheus and Grafana with Docker? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Starting Docker containers..."
        cd monitoring
        docker-compose up -d
        echo "✓ Prometheus: http://localhost:9090"
        echo "✓ Grafana: http://localhost:3000 (admin/admin)"
        cd ..
    fi
else
    echo "⚠ Docker not found (optional)"
    echo "To use Prometheus and Grafana, install Docker from https://www.docker.com/products/docker-desktop"
    echo ""
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Quick Start Guide:"
echo ""
echo "1. Update your main application to use monitoring:"
echo "   from src.core.monitoring import get_prometheus_exporter"
echo "   exporter = get_prometheus_exporter(port=8000)"
echo "   exporter.start()"
echo ""
echo "2. Record metrics in your code:"
echo "   from src.core.monitoring import get_metrics_collector"
echo "   metrics = get_metrics_collector()"
echo "   metrics.record_api_call(latency=0.5, success=True)"
echo ""
echo "3. View metrics:"
echo "   - Application metrics: http://localhost:8000/metrics"
echo "   - Health status: http://localhost:8000/health"
echo "   - HTML Dashboard: monitoring/dashboard.html"
echo ""
if command -v docker &> /dev/null; then
    echo "4. Grafana (if using Docker):"
    echo "   - URL: http://localhost:3000"
    echo "   - Username: admin"
    echo "   - Password: admin"
    echo "   - Import dashboard: monitoring/grafana-dashboard.json"
    echo ""
fi
echo "For more information, see monitoring/README.md"
echo ""
