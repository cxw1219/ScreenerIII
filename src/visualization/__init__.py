"""
Visualization and charting package.

This package provides comprehensive charting and visualization capabilities
for commodity trading analysis, including candlestick charts, performance
dashboards, correlation analysis, and risk metric displays.

Modules:
    - charts: Advanced charting engine with candlestick, performance,
              correlation, risk, and dashboard visualization classes
"""

from .charts import (
    ChartGenerator,
    PerformanceCharts,
    CorrelationVisualizer,
    RiskVisualizer,
    DashboardGenerator,
    ChartConfig,
    ChartStyle,
    MPL_AVAILABLE,
)

__all__ = [
    # Core charting
    "ChartGenerator",
    # Performance visualization
    "PerformanceCharts",
    # Correlation analysis
    "CorrelationVisualizer",
    # Risk visualization
    "RiskVisualizer",
    # Dashboard builder
    "DashboardGenerator",
    # Configuration
    "ChartConfig",
    "ChartStyle",
    # Availability flag
    "MPL_AVAILABLE",
]
