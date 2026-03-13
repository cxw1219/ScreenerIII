"""
ML-Based Pattern Recognition Module

This module provides machine learning-based pattern recognition for commodity
trading analysis, including chart pattern detection, anomaly detection,
market regime classification, and candlestick pattern classification.

Classes:
    MLPatternDetector: ML-based chart pattern detection using sliding windows
    AnomalyDetector: Statistical and ML-based anomaly detection
    RegimeDetector: Market regime classification (trending/ranging, bull/bear)
    CandlestickClassifier: ML-based candlestick pattern classification

Author: ScreenerIII
License: MIT
"""

from typing import Dict, List, Optional, Tuple, Union
from enum import Enum
from dataclasses import dataclass, field
from collections import deque
import logging
import warnings

import numpy as np
import pandas as pd

# Optional ML dependencies
try:
    from sklearn.ensemble import (
        RandomForestClassifier,
        IsolationForest,
        GradientBoostingClassifier,
    )
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.model_selection import cross_val_score
    from sklearn.metrics import classification_report
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    warnings.warn(
        "scikit-learn not available. ML-based pattern recognition will be limited."
    )

try:
    from scipy.signal import argrelextrema
    from scipy.stats import zscore as scipy_zscore
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    warnings.warn(
        "SciPy not available. Some statistical methods will use fallbacks."
    )

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & data classes
# ---------------------------------------------------------------------------

class PatternType(Enum):
    """Enumeration of detectable chart patterns."""
    HEAD_AND_SHOULDERS = "head_and_shoulders"
    INVERSE_HEAD_AND_SHOULDERS = "inverse_head_and_shoulders"
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    ASCENDING_TRIANGLE = "ascending_triangle"
    DESCENDING_TRIANGLE = "descending_triangle"
    SYMMETRIC_TRIANGLE = "symmetric_triangle"
    RISING_WEDGE = "rising_wedge"
    FALLING_WEDGE = "falling_wedge"
    BULL_FLAG = "bull_flag"
    BEAR_FLAG = "bear_flag"
    ASCENDING_CHANNEL = "ascending_channel"
    DESCENDING_CHANNEL = "descending_channel"
    HORIZONTAL_CHANNEL = "horizontal_channel"


class RegimeType(Enum):
    """Market regime classifications."""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    QUIET = "quiet"


class AnomalyType(Enum):
    """Types of detected anomalies."""
    PRICE_SPIKE = "price_spike"
    VOLUME_SPIKE = "volume_spike"
    PRICE_GAP = "price_gap"
    VOLATILITY_SHIFT = "volatility_shift"
    MULTIVARIATE = "multivariate"


@dataclass
class PatternResult:
    """Result of a pattern detection scan."""
    pattern_type: PatternType
    confidence: float
    start_index: int
    end_index: int
    direction: str  # 'bullish', 'bearish', or 'neutral'
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "pattern": self.pattern_type.value,
            "confidence": round(self.confidence, 4),
            "start": self.start_index,
            "end": self.end_index,
            "direction": self.direction,
            "metadata": self.metadata,
        }


@dataclass
class AnomalyResult:
    """Result of an anomaly detection scan."""
    anomaly_type: AnomalyType
    severity: float
    index: int
    description: str
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "type": self.anomaly_type.value,
            "severity": round(self.severity, 4),
            "index": self.index,
            "description": self.description,
            "metadata": self.metadata,
        }


@dataclass
class RegimeResult:
    """Result of a regime detection scan."""
    regime: RegimeType
    confidence: float
    start_index: int
    end_index: int
    volatility_level: str  # 'low', 'medium', 'high'
    trend_strength: float
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "regime": self.regime.value,
            "confidence": round(self.confidence, 4),
            "start": self.start_index,
            "end": self.end_index,
            "volatility": self.volatility_level,
            "trend_strength": round(self.trend_strength, 4),
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _validate_ohlcv(df: pd.DataFrame, require_volume: bool = False) -> None:
    """Validate that a DataFrame contains the required OHLCV columns.

    Args:
        df: DataFrame to validate.
        require_volume: If True, the 'volume' column must be present.

    Raises:
        ValueError: If required columns are missing.
    """
    required = ["open", "high", "low", "close"]
    if require_volume:
        required.append("volume")
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _compute_zscore(series: np.ndarray) -> np.ndarray:
    """Compute Z-scores, falling back to manual calculation if SciPy is absent.

    Args:
        series: 1-D numeric array.

    Returns:
        Array of Z-scores (same length as input).
    """
    if SCIPY_AVAILABLE:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return scipy_zscore(series, nan_policy="omit")
    std = np.nanstd(series)
    if std == 0:
        return np.zeros_like(series, dtype=float)
    return (series - np.nanmean(series)) / std


def _find_local_extrema(
    series: np.ndarray, order: int = 5
) -> Tuple[np.ndarray, np.ndarray]:
    """Find local maxima and minima indices.

    Args:
        series: 1-D price array.
        order: Number of points on each side to compare.

    Returns:
        Tuple of (maxima_indices, minima_indices).
    """
    if SCIPY_AVAILABLE:
        maxima = argrelextrema(series, np.greater, order=order)[0]
        minima = argrelextrema(series, np.less, order=order)[0]
        return maxima, minima

    # Manual fallback
    maxima: List[int] = []
    minima: List[int] = []
    for i in range(order, len(series) - order):
        window = series[i - order: i + order + 1]
        if series[i] == np.max(window):
            maxima.append(i)
        if series[i] == np.min(window):
            minima.append(i)
    return np.array(maxima, dtype=int), np.array(minima, dtype=int)


def _linear_regression_slope(y: np.ndarray) -> float:
    """Return the slope of a simple OLS regression over *y*.

    Args:
        y: 1-D numeric array.

    Returns:
        Slope as a float.
    """
    n = len(y)
    if n < 2:
        return 0.0
    x = np.arange(n, dtype=float)
    x_mean = x.mean()
    y_mean = y.mean()
    denom = np.sum((x - x_mean) ** 2)
    if denom == 0:
        return 0.0
    return float(np.sum((x - x_mean) * (y - y_mean)) / denom)


# ===================================================================
# MLPatternDetector
# ===================================================================

class MLPatternDetector:
    """ML-based chart pattern detection using sliding windows.

    This detector extracts features from price windows (normalized prices,
    volume profiles, slopes) and uses a Random-Forest classifier to label
    each window as one of the supported chart patterns.

    Attributes:
        window_sizes: List of window lengths (in bars) to scan.
        min_confidence: Minimum probability to report a pattern.
        model: The underlying classifier (fitted or None).
        scaler: StandardScaler used for feature normalisation.
        label_encoder: Maps pattern names to integer labels.
    """

    # Default window sizes that capture patterns across timeframes
    DEFAULT_WINDOW_SIZES: List[int] = [20, 40, 60, 80]

    def __init__(
        self,
        window_sizes: Optional[List[int]] = None,
        min_confidence: float = 0.60,
        n_estimators: int = 200,
    ) -> None:
        """Initialise the pattern detector.

        Args:
            window_sizes: Sliding-window lengths to use for scanning.
            min_confidence: Confidence threshold below which patterns are
                discarded.
            n_estimators: Number of trees for the Random-Forest classifier.

        Raises:
            RuntimeError: If scikit-learn is not installed.
        """
        if not SKLEARN_AVAILABLE:
            raise RuntimeError(
                "scikit-learn is required for MLPatternDetector. "
                "Install it with: pip install scikit-learn"
            )

        self.window_sizes = window_sizes or self.DEFAULT_WINDOW_SIZES
        self.min_confidence = min_confidence
        self.n_estimators = n_estimators

        self.model: Optional[RandomForestClassifier] = None
        self.scaler: StandardScaler = StandardScaler()
        self.label_encoder: LabelEncoder = LabelEncoder()
        self._is_fitted: bool = False
        self._feature_names: List[str] = []

        logger.info(
            "MLPatternDetector initialised (windows=%s, min_conf=%.2f)",
            self.window_sizes,
            self.min_confidence,
        )

    # ------------------------------------------------------------------
    # Feature extraction
    # ------------------------------------------------------------------

    def extract_features(
        self, window: pd.DataFrame
    ) -> np.ndarray:
        """Extract a fixed-length feature vector from a price window.

        Features include:
        - Normalised close prices (resampled to 20 points)
        - Normalised high/low envelope widths
        - Normalised volume profile (if available)
        - Statistical moments (mean, std, skew, kurtosis of returns)
        - Slope of first half / second half
        - Max drawdown and max run-up within the window
        - Ratio of upper/lower shadows (aggregate)

        Args:
            window: DataFrame slice with OHLCV columns.

        Returns:
            1-D numpy feature vector.
        """
        close = window["close"].values.astype(float)
        high = window["high"].values.astype(float)
        low = window["low"].values.astype(float)
        open_ = window["open"].values.astype(float)

        has_volume = "volume" in window.columns
        volume = (
            window["volume"].values.astype(float) if has_volume
            else np.ones(len(close))
        )

        n = len(close)
        features: List[float] = []

        # --- Normalised resampled close (20 points) ---
        norm_close = (close - close[0]) / (close.std() + 1e-10)
        indices = np.linspace(0, n - 1, 20).astype(int)
        features.extend(norm_close[indices].tolist())

        # --- Envelope width (high - low) normalised ---
        envelope = (high - low) / (close.mean() + 1e-10)
        env_resampled = envelope[indices]
        features.extend(env_resampled.tolist())

        # --- Volume profile (normalised, resampled to 10 pts) ---
        vol_norm = volume / (volume.mean() + 1e-10)
        vol_idx = np.linspace(0, n - 1, 10).astype(int)
        features.extend(vol_norm[vol_idx].tolist())

        # --- Returns statistics ---
        returns = np.diff(close) / (close[:-1] + 1e-10)
        features.append(float(np.mean(returns)))
        features.append(float(np.std(returns)))
        features.append(float(pd.Series(returns).skew()) if n > 3 else 0.0)
        features.append(float(pd.Series(returns).kurtosis()) if n > 4 else 0.0)

        # --- Half-window slopes ---
        mid = n // 2
        features.append(_linear_regression_slope(close[:mid]))
        features.append(_linear_regression_slope(close[mid:]))

        # --- Max drawdown & run-up ---
        cum_max = np.maximum.accumulate(close)
        drawdowns = (close - cum_max) / (cum_max + 1e-10)
        features.append(float(np.min(drawdowns)))

        cum_min = np.minimum.accumulate(close)
        run_ups = (close - cum_min) / (cum_min + 1e-10)
        features.append(float(np.max(run_ups)))

        # --- Shadow ratios ---
        body = np.abs(close - open_)
        upper_shadow = high - np.maximum(close, open_)
        lower_shadow = np.minimum(close, open_) - low
        total_range = high - low + 1e-10
        features.append(float(np.mean(upper_shadow / total_range)))
        features.append(float(np.mean(lower_shadow / total_range)))
        features.append(float(np.mean(body / total_range)))

        # --- Extrema counts ---
        maxima, minima = _find_local_extrema(close, order=max(2, n // 10))
        features.append(float(len(maxima)))
        features.append(float(len(minima)))

        # --- High / low slope ---
        features.append(_linear_regression_slope(high))
        features.append(_linear_regression_slope(low))

        return np.array(features, dtype=float)

    # ------------------------------------------------------------------
    # Synthetic training data
    # ------------------------------------------------------------------

    def _generate_synthetic_pattern(
        self, pattern: PatternType, length: int = 60
    ) -> pd.DataFrame:
        """Generate a single synthetic OHLCV window for a given pattern.

        This is used to bootstrap a training set when no labelled data is
        available.

        Args:
            pattern: The chart pattern to simulate.
            length: Number of bars in the window.

        Returns:
            DataFrame with OHLCV columns.
        """
        t = np.linspace(0, 1, length)
        noise = np.random.normal(0, 0.005, length)
        base_price = 100.0

        if pattern == PatternType.HEAD_AND_SHOULDERS:
            close = base_price + 5 * np.sin(np.pi * t) * (1 + 0.5 * np.sin(3 * np.pi * t))
        elif pattern == PatternType.INVERSE_HEAD_AND_SHOULDERS:
            close = base_price - 5 * np.sin(np.pi * t) * (1 + 0.5 * np.sin(3 * np.pi * t))
        elif pattern == PatternType.DOUBLE_TOP:
            close = base_price + 4 * np.sin(2 * np.pi * t) * np.sin(np.pi * t)
        elif pattern == PatternType.DOUBLE_BOTTOM:
            close = base_price - 4 * np.sin(2 * np.pi * t) * np.sin(np.pi * t)
        elif pattern == PatternType.ASCENDING_TRIANGLE:
            close = base_price + 3 * t + 1.5 * np.sin(6 * np.pi * t) * (1 - t)
        elif pattern == PatternType.DESCENDING_TRIANGLE:
            close = base_price - 3 * t + 1.5 * np.sin(6 * np.pi * t) * (1 - t)
        elif pattern == PatternType.SYMMETRIC_TRIANGLE:
            close = base_price + 3 * np.sin(6 * np.pi * t) * (1 - t)
        elif pattern == PatternType.RISING_WEDGE:
            close = base_price + 4 * t + 1.0 * np.sin(8 * np.pi * t) * (1 - 0.8 * t)
        elif pattern == PatternType.FALLING_WEDGE:
            close = base_price - 4 * t + 1.0 * np.sin(8 * np.pi * t) * (1 - 0.8 * t)
        elif pattern == PatternType.BULL_FLAG:
            pole = base_price + 6 * np.clip(t * 3, 0, 1)
            flag = -1.5 * (t - 0.33) * np.where(t > 0.33, 1, 0)
            close = pole + flag
        elif pattern == PatternType.BEAR_FLAG:
            pole = base_price - 6 * np.clip(t * 3, 0, 1)
            flag = 1.5 * (t - 0.33) * np.where(t > 0.33, 1, 0)
            close = pole + flag
        elif pattern == PatternType.ASCENDING_CHANNEL:
            close = base_price + 5 * t + 1.5 * np.sin(6 * np.pi * t)
        elif pattern == PatternType.DESCENDING_CHANNEL:
            close = base_price - 5 * t + 1.5 * np.sin(6 * np.pi * t)
        elif pattern == PatternType.HORIZONTAL_CHANNEL:
            close = base_price + 2 * np.sin(6 * np.pi * t)
        else:
            close = base_price + noise * 100

        close = close + noise * base_price

        spread = np.abs(noise * base_price) + 0.3
        high = close + spread
        low = close - spread
        open_ = close + np.random.normal(0, 0.15, length)
        volume = np.random.lognormal(mean=10, sigma=0.5, size=length)

        return pd.DataFrame({
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        })

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def fit(
        self,
        labelled_data: Optional[List[Tuple[pd.DataFrame, str]]] = None,
        samples_per_pattern: int = 200,
    ) -> "MLPatternDetector":
        """Train the pattern classifier.

        If *labelled_data* is provided it must be a list of
        ``(window_df, pattern_name)`` tuples.  Otherwise synthetic data is
        generated automatically.

        Args:
            labelled_data: Optional pre-labelled training windows.
            samples_per_pattern: Number of synthetic samples per pattern
                when labelled_data is None.

        Returns:
            self (for method chaining).
        """
        logger.info("Training MLPatternDetector ...")

        X_all: List[np.ndarray] = []
        y_all: List[str] = []

        if labelled_data is not None:
            for window_df, label in labelled_data:
                try:
                    feat = self.extract_features(window_df)
                    X_all.append(feat)
                    y_all.append(label)
                except Exception as exc:
                    logger.warning("Skipping bad training sample: %s", exc)
        else:
            for pattern in PatternType:
                for _ in range(samples_per_pattern):
                    length = np.random.choice([40, 60, 80])
                    synth = self._generate_synthetic_pattern(pattern, length)
                    feat = self.extract_features(synth)
                    X_all.append(feat)
                    y_all.append(pattern.value)

        X = np.array(X_all)
        y = np.array(y_all)

        # Handle NaN/Inf
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)

        self.label_encoder.fit(y)
        y_encoded = self.label_encoder.transform(y)

        self.model = RandomForestClassifier(
            n_estimators=self.n_estimators,
            max_depth=12,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )
        self.model.fit(X_scaled, y_encoded)
        self._is_fitted = True
        self._feature_names = [f"f{i}" for i in range(X.shape[1])]

        logger.info(
            "MLPatternDetector trained on %d samples (%d patterns)",
            len(X),
            len(self.label_encoder.classes_),
        )
        return self

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect(
        self,
        df: pd.DataFrame,
        timeframe: str = "default",
    ) -> List[PatternResult]:
        """Scan a price DataFrame for chart patterns.

        A sliding window of each configured size is moved across *df* and
        classified by the trained model.  Only results exceeding
        ``min_confidence`` are returned.

        Args:
            df: OHLCV DataFrame to scan.
            timeframe: Label for the timeframe (informational only).

        Returns:
            List of detected PatternResult objects sorted by confidence
            (descending).

        Raises:
            RuntimeError: If the model has not been fitted yet.
        """
        if not self._is_fitted:
            raise RuntimeError(
                "Model is not fitted. Call fit() before detect()."
            )

        _validate_ohlcv(df)
        results: List[PatternResult] = []

        for win_size in self.window_sizes:
            if len(df) < win_size:
                continue

            step = max(1, win_size // 4)
            for start in range(0, len(df) - win_size + 1, step):
                end = start + win_size
                window = df.iloc[start:end]

                try:
                    feat = self.extract_features(window)
                    feat = np.nan_to_num(feat, nan=0.0, posinf=0.0, neginf=0.0)
                    feat_scaled = self.scaler.transform(feat.reshape(1, -1))

                    proba = self.model.predict_proba(feat_scaled)[0]
                    best_idx = int(np.argmax(proba))
                    best_conf = float(proba[best_idx])

                    if best_conf < self.min_confidence:
                        continue

                    pattern_name = self.label_encoder.inverse_transform(
                        [best_idx]
                    )[0]
                    pattern_type = PatternType(pattern_name)

                    direction = self._infer_direction(pattern_type)

                    results.append(PatternResult(
                        pattern_type=pattern_type,
                        confidence=best_conf,
                        start_index=start,
                        end_index=end - 1,
                        direction=direction,
                        metadata={
                            "timeframe": timeframe,
                            "window_size": win_size,
                        },
                    ))
                except Exception as exc:
                    logger.debug("Feature extraction failed at %d: %s", start, exc)

        # De-duplicate overlapping detections (keep highest confidence)
        results = self._deduplicate(results)
        results.sort(key=lambda r: r.confidence, reverse=True)

        logger.info(
            "Detected %d pattern(s) in %d bars (timeframe=%s)",
            len(results),
            len(df),
            timeframe,
        )
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_direction(pattern: PatternType) -> str:
        """Return the directional bias implied by a pattern type."""
        bullish = {
            PatternType.INVERSE_HEAD_AND_SHOULDERS,
            PatternType.DOUBLE_BOTTOM,
            PatternType.ASCENDING_TRIANGLE,
            PatternType.FALLING_WEDGE,
            PatternType.BULL_FLAG,
            PatternType.ASCENDING_CHANNEL,
        }
        bearish = {
            PatternType.HEAD_AND_SHOULDERS,
            PatternType.DOUBLE_TOP,
            PatternType.DESCENDING_TRIANGLE,
            PatternType.RISING_WEDGE,
            PatternType.BEAR_FLAG,
            PatternType.DESCENDING_CHANNEL,
        }
        if pattern in bullish:
            return "bullish"
        if pattern in bearish:
            return "bearish"
        return "neutral"

    @staticmethod
    def _deduplicate(
        results: List[PatternResult], overlap_threshold: float = 0.5
    ) -> List[PatternResult]:
        """Remove overlapping pattern detections, keeping highest confidence."""
        if not results:
            return results

        results.sort(key=lambda r: r.confidence, reverse=True)
        kept: List[PatternResult] = []
        for candidate in results:
            dominated = False
            for existing in kept:
                overlap_start = max(candidate.start_index, existing.start_index)
                overlap_end = min(candidate.end_index, existing.end_index)
                if overlap_end > overlap_start:
                    overlap_len = overlap_end - overlap_start
                    candidate_len = candidate.end_index - candidate.start_index
                    if candidate_len > 0 and overlap_len / candidate_len > overlap_threshold:
                        dominated = True
                        break
            if not dominated:
                kept.append(candidate)
        return kept


# ===================================================================
# AnomalyDetector
# ===================================================================

class AnomalyDetector:
    """Detect unusual price and volume behaviour in market data.

    Detection methods:
    - Z-score based outlier detection on returns and volume.
    - IQR-based outlier detection.
    - Isolation Forest for multivariate anomalies.
    - Explicit price-gap detection.
    - Volatility regime shift detection.

    Attributes:
        zscore_threshold: Number of standard deviations to flag as anomaly.
        iqr_multiplier: IQR multiplier for outlier fencing.
        contamination: Expected fraction of anomalies (Isolation Forest).
        lookback: Rolling window for volatility calculations.
    """

    def __init__(
        self,
        zscore_threshold: float = 3.0,
        iqr_multiplier: float = 1.5,
        contamination: float = 0.05,
        lookback: int = 20,
    ) -> None:
        """Initialise the anomaly detector.

        Args:
            zscore_threshold: Z-score cutoff for statistical anomalies.
            iqr_multiplier: Multiplier for IQR fencing.
            contamination: Expected proportion of outliers for Isolation Forest.
            lookback: Number of bars for rolling statistics.
        """
        self.zscore_threshold = zscore_threshold
        self.iqr_multiplier = iqr_multiplier
        self.contamination = contamination
        self.lookback = lookback

        self._iso_forest: Optional["IsolationForest"] = None

        logger.info(
            "AnomalyDetector initialised (z=%.1f, iqr=%.1f, contamination=%.2f)",
            zscore_threshold,
            iqr_multiplier,
            contamination,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_all(self, df: pd.DataFrame) -> List[AnomalyResult]:
        """Run all anomaly detection methods and merge results.

        Args:
            df: OHLCV DataFrame.

        Returns:
            Sorted list of AnomalyResult (highest severity first).
        """
        _validate_ohlcv(df)
        results: List[AnomalyResult] = []

        results.extend(self.detect_zscore_anomalies(df))
        results.extend(self.detect_iqr_anomalies(df))
        results.extend(self.detect_price_gaps(df))

        if "volume" in df.columns:
            results.extend(self.detect_volume_spikes(df))

        results.extend(self.detect_volatility_shifts(df))

        if SKLEARN_AVAILABLE:
            results.extend(self.detect_isolation_forest(df))

        # De-duplicate by index (keep highest severity)
        seen: Dict[int, AnomalyResult] = {}
        for r in results:
            if r.index not in seen or r.severity > seen[r.index].severity:
                seen[r.index] = r
        results = sorted(seen.values(), key=lambda r: r.severity, reverse=True)

        logger.info("Total anomalies detected: %d", len(results))
        return results

    # ------------------------------------------------------------------
    # Z-score
    # ------------------------------------------------------------------

    def detect_zscore_anomalies(self, df: pd.DataFrame) -> List[AnomalyResult]:
        """Detect anomalies based on Z-scores of returns.

        Args:
            df: OHLCV DataFrame.

        Returns:
            List of AnomalyResult for bars exceeding the Z-score threshold.
        """
        _validate_ohlcv(df)
        close = df["close"].values.astype(float)
        returns = np.diff(close) / (close[:-1] + 1e-10)

        zscores = _compute_zscore(returns)
        results: List[AnomalyResult] = []

        for i, z in enumerate(zscores):
            if np.isnan(z):
                continue
            abs_z = abs(z)
            if abs_z >= self.zscore_threshold:
                results.append(AnomalyResult(
                    anomaly_type=AnomalyType.PRICE_SPIKE,
                    severity=float(abs_z / self.zscore_threshold),
                    index=i + 1,  # offset because returns are diffed
                    description=(
                        f"Return Z-score {z:.2f} exceeds threshold "
                        f"({self.zscore_threshold})"
                    ),
                    metadata={"zscore": float(z), "return": float(returns[i])},
                ))

        logger.debug("Z-score anomalies found: %d", len(results))
        return results

    # ------------------------------------------------------------------
    # IQR
    # ------------------------------------------------------------------

    def detect_iqr_anomalies(self, df: pd.DataFrame) -> List[AnomalyResult]:
        """Detect outliers using the interquartile-range method.

        Args:
            df: OHLCV DataFrame.

        Returns:
            List of AnomalyResult.
        """
        _validate_ohlcv(df)
        close = df["close"].values.astype(float)
        returns = np.diff(close) / (close[:-1] + 1e-10)

        q1, q3 = np.nanpercentile(returns, [25, 75])
        iqr = q3 - q1
        lower_fence = q1 - self.iqr_multiplier * iqr
        upper_fence = q3 + self.iqr_multiplier * iqr

        results: List[AnomalyResult] = []
        for i, ret in enumerate(returns):
            if ret < lower_fence or ret > upper_fence:
                distance = max(abs(ret - lower_fence), abs(ret - upper_fence))
                severity = distance / (iqr + 1e-10)
                results.append(AnomalyResult(
                    anomaly_type=AnomalyType.PRICE_SPIKE,
                    severity=float(severity),
                    index=i + 1,
                    description=(
                        f"Return {ret:.4f} outside IQR fences "
                        f"[{lower_fence:.4f}, {upper_fence:.4f}]"
                    ),
                    metadata={"return": float(ret), "iqr": float(iqr)},
                ))

        logger.debug("IQR anomalies found: %d", len(results))
        return results

    # ------------------------------------------------------------------
    # Volume spikes
    # ------------------------------------------------------------------

    def detect_volume_spikes(
        self, df: pd.DataFrame, multiplier: float = 3.0
    ) -> List[AnomalyResult]:
        """Detect volume spikes relative to a rolling mean.

        Args:
            df: OHLCV DataFrame with a 'volume' column.
            multiplier: How many times the rolling mean qualifies as a spike.

        Returns:
            List of AnomalyResult.
        """
        if "volume" not in df.columns:
            logger.warning("No volume column; skipping volume spike detection.")
            return []

        volume = df["volume"].values.astype(float)
        results: List[AnomalyResult] = []

        for i in range(self.lookback, len(volume)):
            window_mean = np.mean(volume[i - self.lookback: i])
            if window_mean <= 0:
                continue
            ratio = volume[i] / window_mean
            if ratio >= multiplier:
                results.append(AnomalyResult(
                    anomaly_type=AnomalyType.VOLUME_SPIKE,
                    severity=float(ratio / multiplier),
                    index=i,
                    description=(
                        f"Volume {volume[i]:.0f} is {ratio:.1f}x the "
                        f"{self.lookback}-bar average"
                    ),
                    metadata={"volume": float(volume[i]), "ratio": float(ratio)},
                ))

        logger.debug("Volume spikes found: %d", len(results))
        return results

    # ------------------------------------------------------------------
    # Price gaps
    # ------------------------------------------------------------------

    def detect_price_gaps(
        self, df: pd.DataFrame, min_gap_pct: float = 0.02
    ) -> List[AnomalyResult]:
        """Detect price gaps between consecutive bars.

        A gap occurs when the current bar's low is above the previous bar's
        high (gap up) or the current bar's high is below the previous bar's
        low (gap down).

        Args:
            df: OHLCV DataFrame.
            min_gap_pct: Minimum gap size as a fraction of the previous close.

        Returns:
            List of AnomalyResult.
        """
        _validate_ohlcv(df)
        high = df["high"].values.astype(float)
        low = df["low"].values.astype(float)
        close = df["close"].values.astype(float)

        results: List[AnomalyResult] = []

        for i in range(1, len(df)):
            prev_close = close[i - 1]
            if prev_close <= 0:
                continue

            # Gap up
            if low[i] > high[i - 1]:
                gap_pct = (low[i] - high[i - 1]) / prev_close
                if gap_pct >= min_gap_pct:
                    results.append(AnomalyResult(
                        anomaly_type=AnomalyType.PRICE_GAP,
                        severity=float(gap_pct / min_gap_pct),
                        index=i,
                        description=f"Gap up of {gap_pct * 100:.2f}%",
                        metadata={"gap_pct": float(gap_pct), "direction": "up"},
                    ))

            # Gap down
            if high[i] < low[i - 1]:
                gap_pct = (low[i - 1] - high[i]) / prev_close
                if gap_pct >= min_gap_pct:
                    results.append(AnomalyResult(
                        anomaly_type=AnomalyType.PRICE_GAP,
                        severity=float(gap_pct / min_gap_pct),
                        index=i,
                        description=f"Gap down of {gap_pct * 100:.2f}%",
                        metadata={"gap_pct": float(gap_pct), "direction": "down"},
                    ))

        logger.debug("Price gaps found: %d", len(results))
        return results

    # ------------------------------------------------------------------
    # Volatility shifts
    # ------------------------------------------------------------------

    def detect_volatility_shifts(
        self, df: pd.DataFrame, shift_threshold: float = 2.0
    ) -> List[AnomalyResult]:
        """Detect significant changes in realised volatility.

        Compares the current rolling volatility to a longer-term baseline.

        Args:
            df: OHLCV DataFrame.
            shift_threshold: Ratio of short-term to long-term vol to flag.

        Returns:
            List of AnomalyResult.
        """
        _validate_ohlcv(df)
        close = df["close"].values.astype(float)
        returns = np.diff(close) / (close[:-1] + 1e-10)

        short_window = self.lookback
        long_window = short_window * 3
        results: List[AnomalyResult] = []

        if len(returns) < long_window:
            return results

        for i in range(long_window, len(returns)):
            short_vol = np.std(returns[i - short_window: i])
            long_vol = np.std(returns[i - long_window: i])

            if long_vol <= 0:
                continue

            ratio = short_vol / long_vol
            if ratio >= shift_threshold or ratio <= 1.0 / shift_threshold:
                results.append(AnomalyResult(
                    anomaly_type=AnomalyType.VOLATILITY_SHIFT,
                    severity=float(max(ratio, 1.0 / ratio)),
                    index=i + 1,
                    description=(
                        f"Volatility ratio {ratio:.2f} "
                        f"(short={short_vol:.4f}, long={long_vol:.4f})"
                    ),
                    metadata={
                        "short_vol": float(short_vol),
                        "long_vol": float(long_vol),
                        "ratio": float(ratio),
                    },
                ))

        logger.debug("Volatility shifts found: %d", len(results))
        return results

    # ------------------------------------------------------------------
    # Isolation Forest
    # ------------------------------------------------------------------

    def detect_isolation_forest(self, df: pd.DataFrame) -> List[AnomalyResult]:
        """Use Isolation Forest for multivariate anomaly detection.

        Features used: returns, rolling volatility, volume ratio (if
        available), and high-low range ratio.

        Args:
            df: OHLCV DataFrame.

        Returns:
            List of AnomalyResult for points flagged as anomalies.

        Raises:
            RuntimeError: If scikit-learn is not installed.
        """
        if not SKLEARN_AVAILABLE:
            raise RuntimeError("scikit-learn required for Isolation Forest.")

        _validate_ohlcv(df)
        close = df["close"].values.astype(float)
        high = df["high"].values.astype(float)
        low = df["low"].values.astype(float)

        n = len(close)
        if n < self.lookback + 2:
            return []

        returns = np.diff(close) / (close[:-1] + 1e-10)

        # Build feature matrix (aligned to returns index)
        feat_list: List[np.ndarray] = [returns]

        # Rolling volatility
        roll_vol = pd.Series(returns).rolling(self.lookback, min_periods=1).std().values
        feat_list.append(roll_vol)

        # Range ratio
        hl_range = (high[1:] - low[1:]) / (close[1:] + 1e-10)
        feat_list.append(hl_range)

        # Volume ratio
        if "volume" in df.columns:
            volume = df["volume"].values.astype(float)
            vol_mean = pd.Series(volume).rolling(self.lookback, min_periods=1).mean().values
            vol_ratio = volume[1:] / (vol_mean[1:] + 1e-10)
            feat_list.append(vol_ratio)

        X = np.column_stack(feat_list)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        iso = IsolationForest(
            contamination=self.contamination,
            random_state=42,
            n_jobs=-1,
        )
        labels = iso.fit_predict(X)
        scores = iso.decision_function(X)

        results: List[AnomalyResult] = []
        for i, (label, score) in enumerate(zip(labels, scores)):
            if label == -1:
                results.append(AnomalyResult(
                    anomaly_type=AnomalyType.MULTIVARIATE,
                    severity=float(-score + 0.5),  # shift so higher = more anomalous
                    index=i + 1,
                    description=(
                        f"Isolation Forest anomaly (score={score:.4f})"
                    ),
                    metadata={"iso_score": float(score)},
                ))

        logger.debug("Isolation Forest anomalies: %d", len(results))
        return results


# ===================================================================
# RegimeDetector
# ===================================================================

class RegimeDetector:
    """Market regime classification: trending/ranging, bull/bear/neutral,
    and volatility regime (low/medium/high).

    Uses a combination of trend indicators, volatility measures, and a
    Hidden-Markov-Model-inspired state-transition approach to classify
    market regimes over rolling windows.

    Attributes:
        lookback: Window size for regime estimation.
        n_regimes: Number of hidden states for HMM-inspired detection.
        trend_threshold: ADX-like threshold to separate trending from ranging.
    """

    def __init__(
        self,
        lookback: int = 60,
        n_regimes: int = 3,
        trend_threshold: float = 0.02,
    ) -> None:
        """Initialise the regime detector.

        Args:
            lookback: Number of bars for rolling regime estimation.
            n_regimes: Number of latent states for HMM-style clustering.
            trend_threshold: Annualised-return threshold for trend classification.
        """
        self.lookback = lookback
        self.n_regimes = n_regimes
        self.trend_threshold = trend_threshold

        self._transition_matrix: Optional[np.ndarray] = None
        self._state_labels: Optional[Dict[int, RegimeType]] = None

        logger.info(
            "RegimeDetector initialised (lookback=%d, n_regimes=%d)",
            lookback,
            n_regimes,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, df: pd.DataFrame) -> List[RegimeResult]:
        """Classify market regimes across the entire DataFrame.

        Produces one RegimeResult per non-overlapping window of size
        ``lookback``.

        Args:
            df: OHLCV DataFrame.

        Returns:
            List of RegimeResult objects in chronological order.
        """
        _validate_ohlcv(df)
        results: List[RegimeResult] = []

        if len(df) < self.lookback:
            logger.warning(
                "Insufficient data (%d bars) for regime detection "
                "(need >= %d).",
                len(df),
                self.lookback,
            )
            return results

        for start in range(0, len(df) - self.lookback + 1, self.lookback // 2):
            end = start + self.lookback
            window = df.iloc[start:end]
            regime_result = self._classify_window(window, start, end - 1)
            results.append(regime_result)

        # Estimate transition probabilities
        if len(results) >= 2:
            self._estimate_transitions(results)

        logger.info("Regimes detected: %d segments", len(results))
        return results

    def detect_current(self, df: pd.DataFrame) -> RegimeResult:
        """Classify the regime of the most recent *lookback* bars.

        Args:
            df: OHLCV DataFrame (must have >= lookback rows).

        Returns:
            A single RegimeResult for the latest window.

        Raises:
            ValueError: If the DataFrame is too short.
        """
        _validate_ohlcv(df)
        if len(df) < self.lookback:
            raise ValueError(
                f"Need at least {self.lookback} bars, got {len(df)}."
            )

        window = df.iloc[-self.lookback:]
        start = len(df) - self.lookback
        end = len(df) - 1
        return self._classify_window(window, start, end)

    def get_transition_probabilities(self) -> Optional[Dict[str, Dict[str, float]]]:
        """Return estimated regime transition probabilities.

        Returns:
            Nested dict mapping ``{from_regime: {to_regime: probability}}``
            or None if transitions have not been estimated yet.
        """
        if self._transition_matrix is None or self._state_labels is None:
            return None

        n = self._transition_matrix.shape[0]
        result: Dict[str, Dict[str, float]] = {}
        regimes = [self._state_labels.get(i, RegimeType.RANGING) for i in range(n)]

        for i in range(n):
            from_name = regimes[i].value
            result[from_name] = {}
            for j in range(n):
                to_name = regimes[j].value
                result[from_name][to_name] = float(self._transition_matrix[i, j])

        return result

    # ------------------------------------------------------------------
    # HMM-inspired state detection
    # ------------------------------------------------------------------

    def fit_hmm_states(self, df: pd.DataFrame) -> np.ndarray:
        """Assign HMM-inspired hidden states using K-Means clustering on
        rolling feature vectors (return, volatility, volume-trend).

        This is a simplified approach that captures regime-like behaviour
        without a full HMM library dependency.

        Args:
            df: OHLCV DataFrame.

        Returns:
            Array of integer state labels (one per bar, after lookback warm-up).

        Raises:
            RuntimeError: If scikit-learn is not available.
        """
        if not SKLEARN_AVAILABLE:
            raise RuntimeError("scikit-learn required for HMM-style detection.")

        _validate_ohlcv(df)
        close = df["close"].values.astype(float)
        returns = np.diff(close) / (close[:-1] + 1e-10)

        if len(returns) < self.lookback:
            return np.array([], dtype=int)

        # Build rolling features
        roll_ret = pd.Series(returns).rolling(self.lookback, min_periods=1).mean().values
        roll_vol = pd.Series(returns).rolling(self.lookback, min_periods=1).std().values
        roll_skew = pd.Series(returns).rolling(self.lookback, min_periods=1).skew().values

        X = np.column_stack([roll_ret, roll_vol, roll_skew])
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        kmeans = KMeans(
            n_clusters=self.n_regimes,
            random_state=42,
            n_init=10,
        )
        states = kmeans.fit_predict(X_scaled)

        # Map cluster centres to regime types
        centres = kmeans.cluster_centers_
        self._state_labels = {}
        for idx in range(self.n_regimes):
            mean_ret = centres[idx, 0]
            mean_vol = centres[idx, 1]

            if mean_ret > 0.001 and mean_vol < 0.5:
                self._state_labels[idx] = RegimeType.TRENDING_UP
            elif mean_ret < -0.001 and mean_vol < 0.5:
                self._state_labels[idx] = RegimeType.TRENDING_DOWN
            elif mean_vol > 0.5:
                self._state_labels[idx] = RegimeType.VOLATILE
            else:
                self._state_labels[idx] = RegimeType.RANGING

        logger.info(
            "HMM-style states fitted: %s",
            {k: v.value for k, v in self._state_labels.items()},
        )
        return states

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _classify_window(
        self, window: pd.DataFrame, start: int, end: int
    ) -> RegimeResult:
        """Classify a single price window into a market regime.

        Args:
            window: Slice of OHLCV data.
            start: Start index in the original DataFrame.
            end: End index in the original DataFrame.

        Returns:
            RegimeResult describing the detected regime.
        """
        close = window["close"].values.astype(float)
        returns = np.diff(close) / (close[:-1] + 1e-10)

        # Trend metrics
        mean_return = float(np.mean(returns))
        slope = _linear_regression_slope(close)
        slope_normalised = slope / (close.mean() + 1e-10)

        # Volatility
        volatility = float(np.std(returns))
        vol_percentiles = [0.005, 0.015]  # thresholds for low/medium/high

        if volatility < vol_percentiles[0]:
            vol_level = "low"
        elif volatility < vol_percentiles[1]:
            vol_level = "medium"
        else:
            vol_level = "high"

        # Trend strength (R-squared of linear fit)
        n = len(close)
        x = np.arange(n, dtype=float)
        predicted = slope * x + (close.mean() - slope * x.mean())
        ss_res = np.sum((close - predicted) ** 2)
        ss_tot = np.sum((close - close.mean()) ** 2)
        r_squared = 1.0 - ss_res / (ss_tot + 1e-10)
        trend_strength = max(0.0, min(1.0, r_squared))

        # Regime classification
        if trend_strength > 0.6 and slope_normalised > self.trend_threshold:
            regime = RegimeType.TRENDING_UP
            confidence = trend_strength
        elif trend_strength > 0.6 and slope_normalised < -self.trend_threshold:
            regime = RegimeType.TRENDING_DOWN
            confidence = trend_strength
        elif vol_level == "high":
            regime = RegimeType.VOLATILE
            confidence = min(1.0, volatility / vol_percentiles[1])
        elif vol_level == "low" and trend_strength < 0.3:
            regime = RegimeType.QUIET
            confidence = 1.0 - trend_strength
        else:
            regime = RegimeType.RANGING
            confidence = 1.0 - trend_strength

        return RegimeResult(
            regime=regime,
            confidence=float(confidence),
            start_index=start,
            end_index=end,
            volatility_level=vol_level,
            trend_strength=float(trend_strength),
            metadata={
                "mean_return": float(mean_return),
                "slope": float(slope_normalised),
                "volatility": float(volatility),
            },
        )

    def _estimate_transitions(self, results: List[RegimeResult]) -> None:
        """Estimate regime transition probabilities from a sequence of results.

        Args:
            results: Chronological list of RegimeResult objects.
        """
        regime_values = list({r.regime for r in results})
        idx_map = {r: i for i, r in enumerate(regime_values)}
        n = len(regime_values)
        counts = np.zeros((n, n), dtype=float)

        for i in range(len(results) - 1):
            from_idx = idx_map[results[i].regime]
            to_idx = idx_map[results[i + 1].regime]
            counts[from_idx, to_idx] += 1

        row_sums = counts.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1
        self._transition_matrix = counts / row_sums
        self._state_labels = {i: r for r, i in idx_map.items()}

        logger.debug("Transition matrix estimated: %s", self._transition_matrix)


# ===================================================================
# CandlestickClassifier
# ===================================================================

class CandlestickClassifier:
    """ML-based candlestick pattern classification.

    Extracts geometric features from individual or small groups of candles
    and classifies them into named candlestick patterns using a
    Gradient-Boosting classifier.

    Supported patterns (multi-class):
    - Doji, Hammer, Inverted Hammer, Shooting Star
    - Engulfing (bullish/bearish), Harami (bullish/bearish)
    - Morning Star, Evening Star
    - Three White Soldiers, Three Black Crows
    - Spinning Top, Marubozu

    Attributes:
        model: GradientBoostingClassifier (fitted or None).
        scaler: StandardScaler for feature normalisation.
        label_encoder: Maps pattern names to integers.
        accuracy_history: Tracks rolling prediction accuracy.
    """

    PATTERN_NAMES: List[str] = [
        "doji",
        "hammer",
        "inverted_hammer",
        "shooting_star",
        "bullish_engulfing",
        "bearish_engulfing",
        "bullish_harami",
        "bearish_harami",
        "morning_star",
        "evening_star",
        "three_white_soldiers",
        "three_black_crows",
        "spinning_top",
        "marubozu_bull",
        "marubozu_bear",
        "no_pattern",
    ]

    def __init__(
        self,
        n_estimators: int = 150,
        min_confidence: float = 0.50,
        accuracy_window: int = 100,
    ) -> None:
        """Initialise the candlestick classifier.

        Args:
            n_estimators: Number of boosting stages.
            min_confidence: Confidence threshold for reporting a pattern.
            accuracy_window: Rolling window length for accuracy tracking.

        Raises:
            RuntimeError: If scikit-learn is not installed.
        """
        if not SKLEARN_AVAILABLE:
            raise RuntimeError(
                "scikit-learn is required for CandlestickClassifier."
            )

        self.n_estimators = n_estimators
        self.min_confidence = min_confidence
        self.accuracy_window = accuracy_window

        self.model: Optional[GradientBoostingClassifier] = None
        self.scaler: StandardScaler = StandardScaler()
        self.label_encoder: LabelEncoder = LabelEncoder()
        self._is_fitted: bool = False

        # Rolling accuracy tracker: deque of (predicted_correct: bool)
        self._accuracy_history: deque = deque(maxlen=accuracy_window)

        logger.info(
            "CandlestickClassifier initialised (n_est=%d, min_conf=%.2f)",
            n_estimators,
            min_confidence,
        )

    # ------------------------------------------------------------------
    # Feature extraction
    # ------------------------------------------------------------------

    def extract_candle_features(
        self, df: pd.DataFrame, index: int, context: int = 3
    ) -> np.ndarray:
        """Extract features from a candle and its neighbours.

        Features per candle:
        - body_ratio: |close - open| / (high - low)
        - upper_shadow_ratio: (high - max(open,close)) / (high - low)
        - lower_shadow_ratio: (min(open,close) - low) / (high - low)
        - direction: +1 bullish, -1 bearish
        - body_size_vs_avg: body size relative to recent average
        - range_vs_avg: bar range relative to recent average

        Additionally, relative features between consecutive candles
        within the context window.

        Args:
            df: OHLCV DataFrame.
            index: The bar index to classify.
            context: Number of preceding bars to include.

        Returns:
            1-D feature vector.
        """
        features: List[float] = []
        start = max(0, index - context + 1)
        end = index + 1
        subset = df.iloc[start:end]

        open_ = subset["open"].values.astype(float)
        high = subset["high"].values.astype(float)
        low = subset["low"].values.astype(float)
        close = subset["close"].values.astype(float)

        for k in range(len(subset)):
            total_range = high[k] - low[k]
            if total_range <= 0:
                total_range = 1e-10

            body = abs(close[k] - open_[k])
            upper_shadow = high[k] - max(close[k], open_[k])
            lower_shadow = min(close[k], open_[k]) - low[k]

            features.append(body / total_range)                # body ratio
            features.append(upper_shadow / total_range)        # upper shadow
            features.append(lower_shadow / total_range)        # lower shadow
            features.append(1.0 if close[k] >= open_[k] else -1.0)  # direction

        # Pad if fewer than `context` candles are available
        expected_per_candle = 4
        needed = context * expected_per_candle
        while len(features) < needed:
            features.insert(0, 0.0)

        # Relative features between consecutive candles in context
        for k in range(1, len(subset)):
            prev_body = abs(close[k - 1] - open_[k - 1])
            curr_body = abs(close[k] - open_[k])
            features.append(curr_body / (prev_body + 1e-10))  # body ratio change

            prev_range = high[k - 1] - low[k - 1]
            curr_range = high[k] - low[k]
            features.append(curr_range / (prev_range + 1e-10))  # range ratio

            # Gap between candles
            gap = open_[k] - close[k - 1]
            features.append(gap / (prev_range + 1e-10))

        # Pad relative features
        rel_per_pair = 3
        needed_rel = (context - 1) * rel_per_pair
        while len(features) < needed + needed_rel:
            features.insert(needed, 0.0)

        # Volume feature (if available)
        if "volume" in df.columns:
            vol = df["volume"].values.astype(float)
            avg_vol = np.mean(vol[max(0, index - 20): index + 1])
            features.append(vol[index] / (avg_vol + 1e-10))
        else:
            features.append(1.0)

        return np.array(features, dtype=float)

    # ------------------------------------------------------------------
    # Synthetic data generation
    # ------------------------------------------------------------------

    def _generate_synthetic_candle(
        self, pattern_name: str
    ) -> pd.DataFrame:
        """Create a synthetic 3-candle DataFrame exhibiting *pattern_name*.

        Args:
            pattern_name: One of PATTERN_NAMES.

        Returns:
            3-row OHLCV DataFrame.
        """
        base = 100.0
        noise = lambda: np.random.uniform(-0.2, 0.2)

        if pattern_name == "doji":
            rows = [
                {"open": base, "high": base + 1, "low": base - 1, "close": base - 0.5},
                {"open": base, "high": base + 1.5, "low": base - 1.5, "close": base + 0.02 + noise()},
                {"open": base, "high": base + 1, "low": base - 1, "close": base + 0.5},
            ]
        elif pattern_name == "hammer":
            rows = [
                {"open": base, "high": base + 0.5, "low": base - 2, "close": base - 1},
                {"open": base - 1, "high": base - 0.8, "low": base - 3.5, "close": base - 0.9 + noise()},
                {"open": base - 1, "high": base, "low": base - 1.5, "close": base},
            ]
        elif pattern_name == "inverted_hammer":
            rows = [
                {"open": base, "high": base + 0.5, "low": base - 1.5, "close": base - 1},
                {"open": base - 1, "high": base + 1.5, "low": base - 1.2, "close": base - 0.9 + noise()},
                {"open": base - 1, "high": base, "low": base - 1.5, "close": base},
            ]
        elif pattern_name == "shooting_star":
            rows = [
                {"open": base, "high": base + 1.5, "low": base - 0.5, "close": base + 1},
                {"open": base + 1, "high": base + 3.5, "low": base + 0.8, "close": base + 1.1 + noise()},
                {"open": base + 1, "high": base + 1.5, "low": base, "close": base},
            ]
        elif pattern_name == "bullish_engulfing":
            rows = [
                {"open": base, "high": base + 0.5, "low": base - 1, "close": base - 0.5},
                {"open": base - 1, "high": base - 0.5, "low": base - 1.5, "close": base - 0.8},
                {"open": base - 1.5, "high": base + 0.5, "low": base - 1.8, "close": base + 0.3 + noise()},
            ]
        elif pattern_name == "bearish_engulfing":
            rows = [
                {"open": base, "high": base + 1, "low": base - 0.5, "close": base + 0.5},
                {"open": base + 0.5, "high": base + 1.2, "low": base + 0.3, "close": base + 0.8},
                {"open": base + 1.5, "high": base + 1.8, "low": base - 0.5, "close": base - 0.3 + noise()},
            ]
        elif pattern_name == "bullish_harami":
            rows = [
                {"open": base, "high": base + 0.5, "low": base - 1.5, "close": base - 1},
                {"open": base - 0.5, "high": base + 1, "low": base - 2, "close": base - 1.5},
                {"open": base - 1.2, "high": base - 0.8, "low": base - 1.3, "close": base - 0.9 + noise()},
            ]
        elif pattern_name == "bearish_harami":
            rows = [
                {"open": base - 1, "high": base + 1, "low": base - 1.5, "close": base + 0.5},
                {"open": base, "high": base + 2, "low": base - 0.5, "close": base + 1.5},
                {"open": base + 1.2, "high": base + 1.3, "low": base + 0.8, "close": base + 0.9 + noise()},
            ]
        elif pattern_name == "morning_star":
            rows = [
                {"open": base, "high": base + 0.5, "low": base - 2, "close": base - 1.5},
                {"open": base - 1.8, "high": base - 1.5, "low": base - 2.2, "close": base - 1.7 + noise()},
                {"open": base - 1.5, "high": base + 0.5, "low": base - 1.8, "close": base + 0.3},
            ]
        elif pattern_name == "evening_star":
            rows = [
                {"open": base, "high": base + 2, "low": base - 0.5, "close": base + 1.5},
                {"open": base + 1.8, "high": base + 2.2, "low": base + 1.5, "close": base + 1.7 + noise()},
                {"open": base + 1.5, "high": base + 1.8, "low": base - 0.5, "close": base - 0.3},
            ]
        elif pattern_name == "three_white_soldiers":
            rows = [
                {"open": base, "high": base + 1.5, "low": base - 0.2, "close": base + 1.2 + noise()},
                {"open": base + 1.2, "high": base + 2.8, "low": base + 1, "close": base + 2.5 + noise()},
                {"open": base + 2.5, "high": base + 4, "low": base + 2.3, "close": base + 3.8 + noise()},
            ]
        elif pattern_name == "three_black_crows":
            rows = [
                {"open": base, "high": base + 0.2, "low": base - 1.5, "close": base - 1.2 + noise()},
                {"open": base - 1.2, "high": base - 1, "low": base - 2.8, "close": base - 2.5 + noise()},
                {"open": base - 2.5, "high": base - 2.3, "low": base - 4, "close": base - 3.8 + noise()},
            ]
        elif pattern_name == "spinning_top":
            rows = [
                {"open": base, "high": base + 1, "low": base - 1, "close": base + 0.5},
                {"open": base + 0.1, "high": base + 1.5, "low": base - 1.5, "close": base + 0.15 + noise()},
                {"open": base, "high": base + 1, "low": base - 1, "close": base - 0.3},
            ]
        elif pattern_name == "marubozu_bull":
            rows = [
                {"open": base, "high": base + 0.5, "low": base - 0.5, "close": base + 0.2},
                {"open": base, "high": base + 2.5, "low": base - 0.05, "close": base + 2.45 + noise()},
                {"open": base + 2.5, "high": base + 3, "low": base + 2, "close": base + 2.8},
            ]
        elif pattern_name == "marubozu_bear":
            rows = [
                {"open": base, "high": base + 0.5, "low": base - 0.5, "close": base - 0.2},
                {"open": base, "high": base + 0.05, "low": base - 2.5, "close": base - 2.45 + noise()},
                {"open": base - 2.5, "high": base - 2, "low": base - 3, "close": base - 2.8},
            ]
        else:  # no_pattern
            rows = [
                {"open": base + noise(), "high": base + 0.5, "low": base - 0.5, "close": base + noise()},
                {"open": base + noise(), "high": base + 0.6, "low": base - 0.4, "close": base + noise()},
                {"open": base + noise(), "high": base + 0.4, "low": base - 0.6, "close": base + noise()},
            ]

        for row in rows:
            row["volume"] = float(np.random.lognormal(10, 0.5))
            # Ensure high >= max(open, close) and low <= min(open, close)
            row["high"] = max(row["high"], row["open"], row["close"])
            row["low"] = min(row["low"], row["open"], row["close"])

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def fit(
        self,
        labelled_data: Optional[List[Tuple[pd.DataFrame, str]]] = None,
        samples_per_pattern: int = 300,
    ) -> "CandlestickClassifier":
        """Train the candlestick classifier.

        Args:
            labelled_data: Optional list of ``(candle_df, pattern_name)``
                tuples. Each DataFrame should have 3 rows (the candle +
                2 preceding bars).
            samples_per_pattern: Synthetic samples per pattern when no
                labelled data is supplied.

        Returns:
            self (for method chaining).
        """
        logger.info("Training CandlestickClassifier ...")

        X_all: List[np.ndarray] = []
        y_all: List[str] = []

        if labelled_data is not None:
            for candle_df, label in labelled_data:
                try:
                    feat = self.extract_candle_features(candle_df, len(candle_df) - 1)
                    X_all.append(feat)
                    y_all.append(label)
                except Exception as exc:
                    logger.warning("Skipping bad candle sample: %s", exc)
        else:
            for pat_name in self.PATTERN_NAMES:
                for _ in range(samples_per_pattern):
                    synth = self._generate_synthetic_candle(pat_name)
                    feat = self.extract_candle_features(synth, len(synth) - 1)
                    X_all.append(feat)
                    y_all.append(pat_name)

        X = np.array(X_all)
        y = np.array(y_all)

        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)

        self.label_encoder.fit(y)
        y_encoded = self.label_encoder.transform(y)

        self.model = GradientBoostingClassifier(
            n_estimators=self.n_estimators,
            max_depth=5,
            learning_rate=0.1,
            min_samples_leaf=10,
            random_state=42,
        )
        self.model.fit(X_scaled, y_encoded)
        self._is_fitted = True

        logger.info(
            "CandlestickClassifier trained on %d samples (%d classes)",
            len(X),
            len(self.label_encoder.classes_),
        )
        return self

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def classify(
        self,
        df: pd.DataFrame,
        indices: Optional[List[int]] = None,
    ) -> List[Dict]:
        """Classify candlestick patterns at specified bar indices.

        Args:
            df: OHLCV DataFrame.
            indices: Bar indices to classify. Defaults to all bars with
                enough context (i.e. index >= 2).

        Returns:
            List of dicts with keys: index, pattern, confidence, direction.

        Raises:
            RuntimeError: If the model has not been fitted yet.
        """
        if not self._is_fitted:
            raise RuntimeError(
                "Model not fitted. Call fit() before classify()."
            )
        _validate_ohlcv(df)

        if indices is None:
            indices = list(range(2, len(df)))

        results: List[Dict] = []

        for idx in indices:
            if idx < 0 or idx >= len(df):
                continue

            try:
                feat = self.extract_candle_features(df, idx)
                feat = np.nan_to_num(feat, nan=0.0, posinf=0.0, neginf=0.0)
                feat_scaled = self.scaler.transform(feat.reshape(1, -1))

                proba = self.model.predict_proba(feat_scaled)[0]
                best_idx = int(np.argmax(proba))
                best_conf = float(proba[best_idx])

                if best_conf < self.min_confidence:
                    continue

                pattern_name = self.label_encoder.inverse_transform([best_idx])[0]

                if pattern_name == "no_pattern":
                    continue

                direction = self._pattern_direction(pattern_name)

                results.append({
                    "index": idx,
                    "pattern": pattern_name,
                    "confidence": round(best_conf, 4),
                    "direction": direction,
                })
            except Exception as exc:
                logger.debug("Classification failed at index %d: %s", idx, exc)

        logger.info(
            "Classified %d candlestick pattern(s) across %d bars",
            len(results),
            len(indices),
        )
        return results

    # ------------------------------------------------------------------
    # Accuracy tracking
    # ------------------------------------------------------------------

    def record_outcome(self, predicted: str, actual: str) -> None:
        """Record whether a prediction was correct for accuracy tracking.

        Args:
            predicted: The pattern name that was predicted.
            actual: The actual pattern name (ground truth).
        """
        self._accuracy_history.append(predicted == actual)

    def get_rolling_accuracy(self) -> Optional[float]:
        """Return the rolling accuracy over the last *accuracy_window* predictions.

        Returns:
            Accuracy as a float in [0, 1], or None if no outcomes recorded.
        """
        if not self._accuracy_history:
            return None
        return float(sum(self._accuracy_history) / len(self._accuracy_history))

    def get_accuracy_stats(self) -> Dict[str, Union[float, int, None]]:
        """Return summary statistics on prediction accuracy.

        Returns:
            Dict with keys: accuracy, total_predictions, correct, incorrect.
        """
        total = len(self._accuracy_history)
        if total == 0:
            return {
                "accuracy": None,
                "total_predictions": 0,
                "correct": 0,
                "incorrect": 0,
            }

        correct = sum(self._accuracy_history)
        return {
            "accuracy": round(correct / total, 4),
            "total_predictions": total,
            "correct": correct,
            "incorrect": total - correct,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _pattern_direction(pattern_name: str) -> str:
        """Infer the directional bias of a candlestick pattern.

        Args:
            pattern_name: Name of the pattern.

        Returns:
            'bullish', 'bearish', or 'neutral'.
        """
        bullish = {
            "hammer", "inverted_hammer", "bullish_engulfing",
            "bullish_harami", "morning_star", "three_white_soldiers",
            "marubozu_bull",
        }
        bearish = {
            "shooting_star", "bearish_engulfing", "bearish_harami",
            "evening_star", "three_black_crows", "marubozu_bear",
        }
        if pattern_name in bullish:
            return "bullish"
        if pattern_name in bearish:
            return "bearish"
        return "neutral"
