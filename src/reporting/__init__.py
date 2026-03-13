"""
Reporting Module

Provides comprehensive report generation, HTML rendering, CSV export,
performance data aggregation, and automated scheduled reporting for
the ScreenerIII commodity trading scanner platform.

Author: ScreenerIII
License: MIT
"""

from .report_generator import (
    # Enums
    ReportFrequency,
    OutputFormat,

    # Data classes
    ReportMetadata,
    EmailConfig,

    # Main classes
    PerformanceReportData,
    CSVExporter,
    HTMLReportBuilder,
    ReportGenerator,
    ScheduledReporter,
)

__all__ = [
    # Enums
    'ReportFrequency',
    'OutputFormat',

    # Data classes
    'ReportMetadata',
    'EmailConfig',

    # Main classes
    'PerformanceReportData',
    'CSVExporter',
    'HTMLReportBuilder',
    'ReportGenerator',
    'ScheduledReporter',
]

__version__ = '1.0.0'
