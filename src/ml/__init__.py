"""
ML Module - Machine Learning based analysis for ScreenerIII.

Provides pattern recognition, anomaly detection, regime classification,
candlestick pattern classification using ML techniques, portfolio
optimization with modern portfolio theory, and ML-based signal quality
prediction for commodity trading.

Modules:
    - portfolio_optimizer: Portfolio optimization, risk parity, dynamic
      allocation, correlation analysis, and position sizing.
    - signal_predictor: ML models for signal quality prediction, feature
      engineering from OHLCV data, time-series aware training, online
      learning, model persistence, and trading-specific evaluation.
"""

from .portfolio_optimizer import (
    PortfolioOptimizer,
    RiskParityAllocator,
    DynamicAllocator,
    CorrelationAnalyzer,
    PositionSizer,
    PortfolioResult,
    PortfolioConstraints,
    OptimizationObjective,
)

from .signal_predictor import (
    SignalPredictor,
    FeatureEngineering,
    ModelEvaluator,
    SignalQualityLabeler,
    ModelType,
    PredictionResult,
    EvaluationResult,
    build_training_pipeline,
)

__all__ = [
    # Portfolio optimizer
    "PortfolioOptimizer",
    "RiskParityAllocator",
    "DynamicAllocator",
    "CorrelationAnalyzer",
    "PositionSizer",
    "PortfolioResult",
    "PortfolioConstraints",
    "OptimizationObjective",
    # Signal predictor
    "SignalPredictor",
    "FeatureEngineering",
    "ModelEvaluator",
    "SignalQualityLabeler",
    "ModelType",
    "PredictionResult",
    "EvaluationResult",
    "build_training_pipeline",
]
