"""
Risk Analytics Module

Provides comprehensive risk measurement, drawdown analysis, portfolio risk
decomposition, and risk limit monitoring for commodity trading strategies.

Modules:
    - risk_analytics: Core risk metrics, drawdown analysis, portfolio risk
      dashboard, and risk limit management

Author: ScreenerIII
License: MIT
"""

from .risk_analytics import (
    # Enums
    VaRMethod,
    AlertSeverity,

    # Data classes
    VaRResult,
    DrawdownPeriod,
    RiskAlert,

    # Core classes
    RiskAnalytics,
    DrawdownAnalyzer,
    PortfolioRiskDashboard,
    RiskLimitManager,

    # Constants
    TRADING_DAYS_PER_YEAR,
    RISK_FREE_RATE_DEFAULT,
    CONFIDENCE_LEVELS,
    SCIPY_AVAILABLE,
)

__all__ = [
    # Enums
    'VaRMethod',
    'AlertSeverity',

    # Data classes
    'VaRResult',
    'DrawdownPeriod',
    'RiskAlert',

    # Core classes
    'RiskAnalytics',
    'DrawdownAnalyzer',
    'PortfolioRiskDashboard',
    'RiskLimitManager',

    # Constants
    'TRADING_DAYS_PER_YEAR',
    'RISK_FREE_RATE_DEFAULT',
    'CONFIDENCE_LEVELS',
    'SCIPY_AVAILABLE',
]

from .scenario_analysis import (
    # Enums
    ScenarioType,

    # Data classes
    SimulationResult,
    StressTestResult,
    SensitivityResult,
    WalkForwardResult,

    # Core classes
    MonteCarloSimulator,
    StressTester,
    SensitivityAnalyzer,
    WalkForwardAnalyzer,

    # Convenience functions
    quick_monte_carlo,
    quick_stress_test,
    run_full_risk_analysis,
)

__all__ += [
    # Scenario analysis enums
    'ScenarioType',

    # Scenario analysis data classes
    'SimulationResult',
    'StressTestResult',
    'SensitivityResult',
    'WalkForwardResult',

    # Scenario analysis classes
    'MonteCarloSimulator',
    'StressTester',
    'SensitivityAnalyzer',
    'WalkForwardAnalyzer',

    # Convenience functions
    'quick_monte_carlo',
    'quick_stress_test',
    'run_full_risk_analysis',
]

__version__ = '1.1.0'
