"""
ML Signal Prediction Module

This module provides machine learning models for predicting signal quality
in commodity trading. It includes feature engineering from raw OHLCV data,
multiple model types with time-series aware cross-validation, online learning,
model persistence, and trading-specific evaluation metrics.

Author: ScreenerIII
License: MIT
"""

from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import os
import warnings
from datetime import datetime

import numpy as np
import pandas as pd

# Optional ML dependencies
try:
    from sklearn.ensemble import (
        RandomForestClassifier,
        GradientBoostingClassifier,
    )
    from sklearn.linear_model import LogisticRegression, SGDClassifier
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import (
        accuracy_score,
        precision_score,
        recall_score,
        f1_score,
        confusion_matrix,
        roc_curve,
        roc_auc_score,
        classification_report,
    )
    from sklearn.utils.class_weight import compute_class_weight

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import joblib

    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums and dataclasses
# ---------------------------------------------------------------------------

class ModelType(Enum):
    """Supported model types for signal prediction."""
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    LOGISTIC_REGRESSION = "logistic_regression"


@dataclass
class PredictionResult:
    """Container for a single prediction output.

    Attributes:
        label: Predicted class label (1 = good signal, 0 = bad signal).
        confidence: Probability of the predicted class.
        probabilities: Full probability vector across all classes.
        features_used: Number of features that went into the prediction.
        timestamp: When the prediction was made.
    """
    label: int
    confidence: float
    probabilities: Dict[int, float]
    features_used: int
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EvaluationResult:
    """Container for model evaluation results.

    Attributes:
        accuracy: Overall accuracy.
        precision: Precision for the positive class.
        recall: Recall for the positive class.
        f1: F1 score for the positive class.
        roc_auc: Area under the ROC curve.
        confusion: Confusion matrix as a nested list.
        roc_data: Dict with 'fpr', 'tpr', 'thresholds' arrays.
        profit_factor: Ratio of gross profit to gross loss from predictions.
        classification_report: Full sklearn classification report string.
        cv_scores: Per-fold scores from cross-validation (if applicable).
    """
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    confusion: List[List[int]]
    roc_data: Dict[str, List[float]]
    profit_factor: float
    classification_report: str
    cv_scores: Optional[List[float]] = None


# ---------------------------------------------------------------------------
# FeatureEngineering
# ---------------------------------------------------------------------------

class FeatureEngineering:
    """Extract ML features from raw OHLCV market data.

    This class computes a broad set of features grouped into:
      - Technical indicator features (RSI, MACD, Bollinger Band width, ATR)
      - Price action features (candle body ratio, gap, momentum)
      - Volume features (relative volume, volume moving-average trend)
      - Volatility features (historical vol, vol ratio)
      - Time features (hour, day of week, month)
      - Lag features (lagged returns, lagged signal counts)

    All methods operate on a DataFrame with at minimum the columns:
    ``open``, ``high``, ``low``, ``close``, ``volume``.
    A ``datetime`` index (or column named ``timestamp``) is expected for
    time-based features.

    Usage::

        fe = FeatureEngineering()
        features_df = fe.build_features(ohlcv_df)
    """

    # Default RSI period
    RSI_PERIOD: int = 14
    # MACD parameters
    MACD_FAST: int = 12
    MACD_SLOW: int = 26
    MACD_SIGNAL: int = 9
    # Bollinger Band parameters
    BB_PERIOD: int = 20
    BB_STD: float = 2.0
    # ATR period
    ATR_PERIOD: int = 14
    # Volume MA period
    VOL_MA_PERIOD: int = 20
    # Historical volatility lookback
    HVOL_PERIOD: int = 20
    # Number of lag periods
    NUM_LAGS: int = 5

    def __init__(
        self,
        rsi_period: int = 14,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        bb_period: int = 20,
        bb_std: float = 2.0,
        atr_period: int = 14,
        vol_ma_period: int = 20,
        hvol_period: int = 20,
        num_lags: int = 5,
    ) -> None:
        """Initialise feature engineering parameters.

        Args:
            rsi_period: Look-back for RSI.
            macd_fast: Fast EMA period for MACD.
            macd_slow: Slow EMA period for MACD.
            macd_signal: Signal line EMA period for MACD.
            bb_period: Look-back for Bollinger Bands.
            bb_std: Standard deviation multiplier for Bollinger Bands.
            atr_period: Look-back for ATR.
            vol_ma_period: Look-back for volume moving average.
            hvol_period: Look-back for historical volatility.
            num_lags: Number of lag periods for lag features.
        """
        self.RSI_PERIOD = rsi_period
        self.MACD_FAST = macd_fast
        self.MACD_SLOW = macd_slow
        self.MACD_SIGNAL = macd_signal
        self.BB_PERIOD = bb_period
        self.BB_STD = bb_std
        self.ATR_PERIOD = atr_period
        self.VOL_MA_PERIOD = vol_ma_period
        self.HVOL_PERIOD = hvol_period
        self.NUM_LAGS = num_lags
        logger.info("FeatureEngineering initialised")

    # -- Technical indicator features ----------------------------------------

    def _compute_rsi(self, close: pd.Series) -> pd.Series:
        """Compute RSI from a close-price series."""
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(span=self.RSI_PERIOD, min_periods=self.RSI_PERIOD).mean()
        avg_loss = loss.ewm(span=self.RSI_PERIOD, min_periods=self.RSI_PERIOD).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return rsi

    def _compute_macd(self, close: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Return MACD line, signal line, and histogram."""
        ema_fast = close.ewm(span=self.MACD_FAST, min_periods=self.MACD_FAST).mean()
        ema_slow = close.ewm(span=self.MACD_SLOW, min_periods=self.MACD_SLOW).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.MACD_SIGNAL, min_periods=self.MACD_SIGNAL).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def _compute_bollinger(self, close: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Return upper band, middle band (SMA), and lower band."""
        middle = close.rolling(window=self.BB_PERIOD).mean()
        std = close.rolling(window=self.BB_PERIOD).std()
        upper = middle + self.BB_STD * std
        lower = middle - self.BB_STD * std
        return upper, middle, lower

    def _compute_atr(self, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        """Compute Average True Range."""
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.ewm(span=self.ATR_PERIOD, min_periods=self.ATR_PERIOD).mean()
        return atr

    def add_technical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicator columns to *df* in-place and return it.

        Features added:
            feat_rsi, feat_macd, feat_macd_signal, feat_macd_hist,
            feat_bb_upper, feat_bb_middle, feat_bb_lower, feat_bb_width,
            feat_bb_pct, feat_atr, feat_atr_pct,
            feat_sma_20, feat_sma_50, feat_ema_12, feat_ema_26,
            feat_sma_cross (SMA20 > SMA50 as int)
        """
        close = df["close"]
        high = df["high"]
        low = df["low"]

        # RSI
        df["feat_rsi"] = self._compute_rsi(close)

        # MACD
        macd_line, sig_line, hist = self._compute_macd(close)
        df["feat_macd"] = macd_line
        df["feat_macd_signal"] = sig_line
        df["feat_macd_hist"] = hist

        # Bollinger Bands
        bb_upper, bb_mid, bb_lower = self._compute_bollinger(close)
        df["feat_bb_upper"] = bb_upper
        df["feat_bb_middle"] = bb_mid
        df["feat_bb_lower"] = bb_lower
        df["feat_bb_width"] = (bb_upper - bb_lower) / bb_mid.replace(0, np.nan)
        df["feat_bb_pct"] = (close - bb_lower) / (bb_upper - bb_lower).replace(0, np.nan)

        # ATR
        atr = self._compute_atr(high, low, close)
        df["feat_atr"] = atr
        df["feat_atr_pct"] = atr / close.replace(0, np.nan)

        # Moving averages
        df["feat_sma_20"] = close.rolling(20).mean()
        df["feat_sma_50"] = close.rolling(50).mean()
        df["feat_ema_12"] = close.ewm(span=12, min_periods=12).mean()
        df["feat_ema_26"] = close.ewm(span=26, min_periods=26).mean()
        df["feat_sma_cross"] = (df["feat_sma_20"] > df["feat_sma_50"]).astype(int)

        logger.debug("Technical indicator features added (%d rows)", len(df))
        return df

    # -- Price action features -----------------------------------------------

    def add_price_action_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add price-action derived features.

        Features added:
            feat_body_ratio, feat_upper_shadow, feat_lower_shadow,
            feat_gap, feat_gap_pct,
            feat_momentum_5, feat_momentum_10, feat_momentum_20,
            feat_roc_5, feat_roc_10,
            feat_high_low_range, feat_close_position
        """
        o, h, l, c = df["open"], df["high"], df["low"], df["close"]
        hl_range = (h - l).replace(0, np.nan)

        # Candle body ratio (body size relative to full range)
        df["feat_body_ratio"] = (c - o).abs() / hl_range
        # Shadow ratios
        upper_shadow = h - pd.concat([o, c], axis=1).max(axis=1)
        lower_shadow = pd.concat([o, c], axis=1).min(axis=1) - l
        df["feat_upper_shadow"] = upper_shadow / hl_range
        df["feat_lower_shadow"] = lower_shadow / hl_range

        # Gaps
        prev_close = c.shift(1)
        df["feat_gap"] = o - prev_close
        df["feat_gap_pct"] = df["feat_gap"] / prev_close.replace(0, np.nan)

        # Momentum (simple price difference)
        for period in (5, 10, 20):
            df[f"feat_momentum_{period}"] = c - c.shift(period)

        # Rate of change
        for period in (5, 10):
            df[f"feat_roc_{period}"] = c.pct_change(periods=period)

        # Intra-bar position of close within high-low range
        df["feat_high_low_range"] = h - l
        df["feat_close_position"] = (c - l) / hl_range

        logger.debug("Price action features added")
        return df

    # -- Volume features -----------------------------------------------------

    def add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volume-derived features.

        Features added:
            feat_vol_ma, feat_rel_volume, feat_vol_trend,
            feat_vol_change, feat_obv, feat_vwap_ratio
        """
        vol = df["volume"].astype(float)
        close = df["close"]

        df["feat_vol_ma"] = vol.rolling(self.VOL_MA_PERIOD).mean()
        df["feat_rel_volume"] = vol / df["feat_vol_ma"].replace(0, np.nan)

        # Volume trend: slope of volume MA (simple diff of MA)
        df["feat_vol_trend"] = df["feat_vol_ma"].diff(5)

        # Volume change
        df["feat_vol_change"] = vol.pct_change()

        # On-balance volume (simplified cumulative)
        direction = np.sign(close.diff())
        df["feat_obv"] = (vol * direction).cumsum()

        # VWAP ratio (rolling approximation)
        typical_price = (df["high"] + df["low"] + close) / 3.0
        cum_tp_vol = (typical_price * vol).rolling(self.VOL_MA_PERIOD).sum()
        cum_vol = vol.rolling(self.VOL_MA_PERIOD).sum()
        rolling_vwap = cum_tp_vol / cum_vol.replace(0, np.nan)
        df["feat_vwap_ratio"] = close / rolling_vwap.replace(0, np.nan)

        logger.debug("Volume features added")
        return df

    # -- Volatility features -------------------------------------------------

    def add_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volatility-derived features.

        Features added:
            feat_hist_vol, feat_hist_vol_short, feat_vol_ratio,
            feat_parkinson_vol, feat_garman_klass_vol
        """
        log_ret = np.log(df["close"] / df["close"].shift(1))

        # Annualised historical volatility (long window)
        df["feat_hist_vol"] = log_ret.rolling(self.HVOL_PERIOD).std() * np.sqrt(252)

        # Short-window volatility
        short_window = max(self.HVOL_PERIOD // 4, 5)
        df["feat_hist_vol_short"] = log_ret.rolling(short_window).std() * np.sqrt(252)

        # Volatility ratio: short / long
        df["feat_vol_ratio"] = (
            df["feat_hist_vol_short"] / df["feat_hist_vol"].replace(0, np.nan)
        )

        # Parkinson volatility estimator
        log_hl = np.log(df["high"] / df["low"].replace(0, np.nan))
        df["feat_parkinson_vol"] = (
            log_hl.pow(2).rolling(self.HVOL_PERIOD).mean() / (4.0 * np.log(2))
        ).apply(np.sqrt) * np.sqrt(252)

        # Garman-Klass volatility estimator
        log_hl2 = log_hl.pow(2)
        log_co = np.log(df["close"] / df["open"].replace(0, np.nan))
        log_co2 = log_co.pow(2)
        gk = 0.5 * log_hl2 - (2.0 * np.log(2) - 1.0) * log_co2
        df["feat_garman_klass_vol"] = (
            gk.rolling(self.HVOL_PERIOD).mean().apply(lambda x: np.sqrt(abs(x)))
            * np.sqrt(252)
        )

        logger.debug("Volatility features added")
        return df

    # -- Time features -------------------------------------------------------

    def add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add calendar/time-based features.

        Expects a DatetimeIndex or a column named ``timestamp``.

        Features added:
            feat_hour, feat_day_of_week, feat_month,
            feat_day_of_month, feat_quarter,
            feat_hour_sin, feat_hour_cos,
            feat_dow_sin, feat_dow_cos
        """
        if isinstance(df.index, pd.DatetimeIndex):
            dt = df.index
        elif "timestamp" in df.columns:
            dt = pd.to_datetime(df["timestamp"])
        else:
            logger.warning("No datetime index or 'timestamp' column found; skipping time features")
            return df

        df["feat_hour"] = dt.hour
        df["feat_day_of_week"] = dt.dayofweek
        df["feat_month"] = dt.month
        df["feat_day_of_month"] = dt.day
        df["feat_quarter"] = dt.quarter

        # Cyclical encoding
        df["feat_hour_sin"] = np.sin(2 * np.pi * dt.hour / 24.0)
        df["feat_hour_cos"] = np.cos(2 * np.pi * dt.hour / 24.0)
        df["feat_dow_sin"] = np.sin(2 * np.pi * dt.dayofweek / 7.0)
        df["feat_dow_cos"] = np.cos(2 * np.pi * dt.dayofweek / 7.0)

        logger.debug("Time features added")
        return df

    # -- Lag features --------------------------------------------------------

    def add_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add lagged return and signal features.

        Features added (for each lag 1..NUM_LAGS):
            feat_return_lag_{i}, feat_vol_lag_{i}
        """
        close = df["close"]
        vol = df["volume"].astype(float)
        for i in range(1, self.NUM_LAGS + 1):
            df[f"feat_return_lag_{i}"] = close.pct_change(i)
            df[f"feat_vol_lag_{i}"] = vol.shift(i)

        logger.debug("Lag features added (lags=1..%d)", self.NUM_LAGS)
        return df

    # -- Master builder ------------------------------------------------------

    def build_features(
        self,
        df: pd.DataFrame,
        include_technical: bool = True,
        include_price_action: bool = True,
        include_volume: bool = True,
        include_volatility: bool = True,
        include_time: bool = True,
        include_lags: bool = True,
        drop_na: bool = True,
    ) -> pd.DataFrame:
        """Build all requested feature groups and return a clean DataFrame.

        Args:
            df: Raw OHLCV DataFrame (``open``, ``high``, ``low``, ``close``, ``volume``).
            include_technical: Add RSI, MACD, BB, ATR features.
            include_price_action: Add candle/momentum features.
            include_volume: Add volume-derived features.
            include_volatility: Add historical-vol features.
            include_time: Add calendar features.
            include_lags: Add lagged return/volume features.
            drop_na: Drop rows with NaN values after feature construction.

        Returns:
            DataFrame with all requested feature columns appended. Rows with
            NaN (warm-up period) are removed when *drop_na* is True.
        """
        required = {"open", "high", "low", "close", "volume"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        result = df.copy()
        logger.info("Building feature set from %d rows", len(result))

        if include_technical:
            result = self.add_technical_features(result)
        if include_price_action:
            result = self.add_price_action_features(result)
        if include_volume:
            result = self.add_volume_features(result)
        if include_volatility:
            result = self.add_volatility_features(result)
        if include_time:
            result = self.add_time_features(result)
        if include_lags:
            result = self.add_lag_features(result)

        feature_cols = [c for c in result.columns if c.startswith("feat_")]
        logger.info("Total features generated: %d", len(feature_cols))

        if drop_na:
            before = len(result)
            result = result.dropna(subset=feature_cols)
            dropped = before - len(result)
            if dropped:
                logger.info("Dropped %d rows with NaN (warm-up period)", dropped)

        return result

    def get_feature_columns(self, df: pd.DataFrame) -> List[str]:
        """Return the list of feature column names present in *df*."""
        return sorted([c for c in df.columns if c.startswith("feat_")])


# ---------------------------------------------------------------------------
# SignalQualityLabeler
# ---------------------------------------------------------------------------

class SignalQualityLabeler:
    """Create binary labels for signal quality based on future price movement.

    A signal is labelled **good** (1) if the price moves favourably by at least
    ``profit_threshold`` percent within ``lookahead`` bars.  Otherwise the
    label is **bad** (0).

    This labeler intentionally looks into the future -- it is used only for
    building training data, never at inference time.

    Usage::

        labeler = SignalQualityLabeler(lookahead=10, profit_threshold=0.5)
        df = labeler.label(df, signal_col="signal_direction")
    """

    def __init__(
        self,
        lookahead: int = 10,
        profit_threshold: float = 0.5,
        loss_threshold: Optional[float] = None,
        label_column: str = "label",
    ) -> None:
        """Initialise the labeler.

        Args:
            lookahead: Number of bars to look ahead for the price outcome.
            profit_threshold: Minimum percentage move (in %) to label a signal
                as *good*.  E.g. 0.5 means 0.5 %.
            loss_threshold: If provided, a signal that loses more than this
                percentage is labelled *bad* regardless of other criteria.
                Defaults to ``-profit_threshold``.
            label_column: Name of the label column to create.
        """
        if lookahead < 1:
            raise ValueError("lookahead must be >= 1")
        self.lookahead = lookahead
        self.profit_threshold = profit_threshold
        self.loss_threshold = loss_threshold if loss_threshold is not None else -profit_threshold
        self.label_column = label_column
        logger.info(
            "SignalQualityLabeler: lookahead=%d, profit_threshold=%.2f%%, "
            "loss_threshold=%.2f%%",
            lookahead,
            profit_threshold,
            self.loss_threshold,
        )

    def label(
        self,
        df: pd.DataFrame,
        signal_col: Optional[str] = None,
        close_col: str = "close",
    ) -> pd.DataFrame:
        """Assign quality labels to each row.

        If *signal_col* is given, labels are only computed for rows where that
        column is non-zero / non-null.  Other rows receive ``NaN`` and should
        be excluded from training.

        Args:
            df: DataFrame containing at minimum *close_col*.
            signal_col: Optional column indicating signal direction (+1 buy,
                -1 sell).  When ``None``, every row is labelled as if a buy
                signal was generated.
            close_col: Column with close prices.

        Returns:
            A copy of *df* with the label column appended.
        """
        result = df.copy()
        close = result[close_col]

        # Maximum favourable excursion within lookahead window
        future_max = close.shift(-1).rolling(window=self.lookahead).max().shift(-self.lookahead + 1)
        future_min = close.shift(-1).rolling(window=self.lookahead).min().shift(-self.lookahead + 1)

        # Default: treat every row as a buy signal
        direction = pd.Series(1, index=result.index)
        if signal_col is not None and signal_col in result.columns:
            direction = result[signal_col].fillna(0).apply(lambda x: 1 if x >= 0 else -1)

        # For buys, favourable move is price going up; for sells, going down
        fav_excursion = np.where(
            direction == 1,
            (future_max - close) / close.replace(0, np.nan) * 100.0,
            (close - future_min) / close.replace(0, np.nan) * 100.0,
        )
        adv_excursion = np.where(
            direction == 1,
            (future_min - close) / close.replace(0, np.nan) * 100.0,
            (close - future_max) / close.replace(0, np.nan) * 100.0,
        )

        fav_series = pd.Series(fav_excursion, index=result.index)
        adv_series = pd.Series(adv_excursion, index=result.index)

        # Label: 1 if favourable excursion exceeds threshold and adverse
        # excursion does not exceed loss threshold first.
        labels = pd.Series(np.nan, index=result.index)
        mask_good = fav_series >= self.profit_threshold
        mask_bad = adv_series <= self.loss_threshold
        labels = np.where(mask_good & ~mask_bad, 1, np.where(mask_bad, 0, np.nan))
        # Rows that are ambiguous (neither clearly good nor bad) default to 0
        labels = np.where(np.isnan(labels), 0, labels)
        labels = pd.Series(labels, index=result.index, dtype=float)

        # Mask out rows without signals if signal_col provided
        if signal_col is not None and signal_col in result.columns:
            no_signal = result[signal_col].isna() | (result[signal_col] == 0)
            labels[no_signal] = np.nan

        # The last ``lookahead`` rows cannot be labelled
        labels.iloc[-self.lookahead:] = np.nan

        result[self.label_column] = labels
        valid_count = labels.notna().sum()
        if valid_count > 0:
            pos_rate = (labels == 1).sum() / valid_count * 100
            logger.info(
                "Labelling complete: %d valid labels (%.1f%% positive)",
                valid_count,
                pos_rate,
            )
        else:
            logger.warning("No valid labels generated")

        return result

    @staticmethod
    def compute_class_weights(labels: pd.Series) -> Dict[int, float]:
        """Compute class weights to handle imbalanced labels.

        Args:
            labels: Series of 0/1 labels (NaN values are ignored).

        Returns:
            Dict mapping class label to weight, suitable for sklearn
            ``class_weight`` parameter.
        """
        if not SKLEARN_AVAILABLE:
            logger.warning("sklearn not available; returning uniform weights")
            return {0: 1.0, 1: 1.0}

        clean = labels.dropna().astype(int)
        classes = np.array(sorted(clean.unique()))
        weights = compute_class_weight("balanced", classes=classes, y=clean.values)
        weight_dict = dict(zip(classes.tolist(), weights.tolist()))
        logger.info("Computed class weights: %s", weight_dict)
        return weight_dict


# ---------------------------------------------------------------------------
# ModelEvaluator
# ---------------------------------------------------------------------------

class ModelEvaluator:
    """Evaluate a trained signal prediction model.

    Provides standard classification metrics as well as trading-specific
    metrics such as profit factor computed from prediction outcomes.

    Usage::

        evaluator = ModelEvaluator()
        result = evaluator.evaluate(y_true, y_pred, y_prob, prices)
    """

    def __init__(self) -> None:
        if not SKLEARN_AVAILABLE:
            raise ImportError(
                "scikit-learn is required for ModelEvaluator. "
                "Install it with: pip install scikit-learn"
            )
        logger.info("ModelEvaluator initialised")

    def evaluate(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_prob: Optional[np.ndarray] = None,
        prices: Optional[pd.Series] = None,
        returns: Optional[pd.Series] = None,
    ) -> EvaluationResult:
        """Run full evaluation suite.

        Args:
            y_true: Ground truth binary labels.
            y_pred: Predicted binary labels.
            y_prob: Predicted probabilities for the positive class (used for
                ROC curve and AUC).
            prices: Close prices aligned with predictions (used for profit
                factor calculation).
            returns: Pre-computed forward returns aligned with predictions.
                If provided, takes precedence over *prices* for profit factor.

        Returns:
            An ``EvaluationResult`` dataclass.
        """
        acc = accuracy_score(y_true, y_pred)
        prec = precision_score(y_true, y_pred, zero_division=0)
        rec = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)

        cm = confusion_matrix(y_true, y_pred).tolist()
        report = classification_report(y_true, y_pred, zero_division=0)

        # ROC curve
        roc_data: Dict[str, List[float]] = {"fpr": [], "tpr": [], "thresholds": []}
        auc_val = 0.0
        if y_prob is not None:
            try:
                fpr, tpr, thresholds = roc_curve(y_true, y_prob)
                roc_data = {
                    "fpr": fpr.tolist(),
                    "tpr": tpr.tolist(),
                    "thresholds": thresholds.tolist(),
                }
                auc_val = roc_auc_score(y_true, y_prob)
            except ValueError as exc:
                logger.warning("Could not compute ROC/AUC: %s", exc)

        # Profit factor
        pf = self._compute_profit_factor(y_true, y_pred, prices, returns)

        logger.info(
            "Evaluation - Acc: %.4f | Prec: %.4f | Rec: %.4f | F1: %.4f | AUC: %.4f | PF: %.2f",
            acc, prec, rec, f1, auc_val, pf,
        )

        return EvaluationResult(
            accuracy=acc,
            precision=prec,
            recall=rec,
            f1=f1,
            roc_auc=auc_val,
            confusion=cm,
            roc_data=roc_data,
            profit_factor=pf,
            classification_report=report,
        )

    def cross_validate(
        self,
        model: Any,
        X: np.ndarray,
        y: np.ndarray,
        n_splits: int = 5,
    ) -> List[float]:
        """Time-series aware cross-validation returning per-fold F1 scores.

        Uses ``TimeSeriesSplit`` so that validation data always comes after
        training data, preventing future-data leakage.

        Args:
            model: A scikit-learn estimator (must support fit/predict).
            X: Feature matrix.
            y: Label vector.
            n_splits: Number of CV folds.

        Returns:
            List of F1 scores, one per fold.
        """
        tscv = TimeSeriesSplit(n_splits=n_splits)
        scores: List[float] = []

        for fold, (train_idx, val_idx) in enumerate(tscv.split(X), 1):
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]

            clone = _clone_model(model)
            clone.fit(X_train, y_train)
            preds = clone.predict(X_val)
            score = f1_score(y_val, preds, zero_division=0)
            scores.append(score)
            logger.debug("CV fold %d/%d: F1=%.4f", fold, n_splits, score)

        logger.info(
            "Cross-validation complete: mean F1=%.4f (+/- %.4f)",
            np.mean(scores),
            np.std(scores),
        )
        return scores

    # -- Private helpers -----------------------------------------------------

    @staticmethod
    def _compute_profit_factor(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        prices: Optional[pd.Series],
        returns: Optional[pd.Series],
    ) -> float:
        """Compute profit factor: gross_profit / gross_loss.

        Returns 0.0 if not enough data or no losses.
        """
        if returns is not None:
            rets = returns.values if isinstance(returns, pd.Series) else np.asarray(returns)
        elif prices is not None:
            price_arr = prices.values if isinstance(prices, pd.Series) else np.asarray(prices)
            rets = np.diff(price_arr, prepend=price_arr[0]) / np.where(
                price_arr == 0, np.nan, price_arr
            )
        else:
            return 0.0

        # Only consider returns where we predicted positive (took the trade)
        pred_mask = np.asarray(y_pred) == 1
        trade_returns = rets[pred_mask]

        gross_profit = trade_returns[trade_returns > 0].sum()
        gross_loss = abs(trade_returns[trade_returns < 0].sum())

        if gross_loss == 0:
            return float(gross_profit > 0) * 999.0  # cap at 999
        return round(gross_profit / gross_loss, 4)


# ---------------------------------------------------------------------------
# SignalPredictor (main model class)
# ---------------------------------------------------------------------------

class SignalPredictor:
    """ML model for predicting whether a trading signal will be profitable.

    Supports Random Forest, Gradient Boosting, and Logistic Regression.
    Provides time-series aware training, online (incremental) updates,
    model persistence, feature importance analysis, and confidence-scored
    predictions.

    Usage::

        predictor = SignalPredictor(model_type=ModelType.GRADIENT_BOOSTING)
        predictor.train(X_train, y_train)
        result = predictor.predict(X_new)
        predictor.save("models/signal_model.joblib")
    """

    # Default hyper-parameters per model type
    _DEFAULT_PARAMS: Dict[ModelType, Dict[str, Any]] = {
        ModelType.RANDOM_FOREST: {
            "n_estimators": 200,
            "max_depth": 10,
            "min_samples_split": 10,
            "min_samples_leaf": 5,
            "random_state": 42,
            "n_jobs": -1,
        },
        ModelType.GRADIENT_BOOSTING: {
            "n_estimators": 200,
            "max_depth": 5,
            "learning_rate": 0.1,
            "subsample": 0.8,
            "min_samples_split": 10,
            "min_samples_leaf": 5,
            "random_state": 42,
        },
        ModelType.LOGISTIC_REGRESSION: {
            "C": 1.0,
            "max_iter": 1000,
            "solver": "lbfgs",
            "random_state": 42,
        },
    }

    def __init__(
        self,
        model_type: ModelType = ModelType.GRADIENT_BOOSTING,
        params: Optional[Dict[str, Any]] = None,
        scale_features: bool = True,
        class_weight: Optional[Union[str, Dict[int, float]]] = "balanced",
    ) -> None:
        """Initialise the predictor.

        Args:
            model_type: Which algorithm to use.
            params: Override default hyper-parameters.  Keys not provided
                fall back to the defaults for the chosen *model_type*.
            scale_features: Whether to standardise features before training
                and prediction.
            class_weight: Class weighting strategy.  ``"balanced"`` lets
                sklearn compute weights automatically.  A dict can supply
                explicit weights.  ``None`` uses uniform weights.
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError(
                "scikit-learn is required for SignalPredictor. "
                "Install it with: pip install scikit-learn"
            )

        self.model_type = model_type
        self.scale_features = scale_features
        self.class_weight = class_weight

        # Merge user params with defaults
        merged_params = dict(self._DEFAULT_PARAMS.get(model_type, {}))
        if params:
            merged_params.update(params)
        self.params = merged_params

        # Build the underlying sklearn model
        self.model = self._build_model(merged_params)

        # Scaler (fitted during training)
        self.scaler: Optional[StandardScaler] = StandardScaler() if scale_features else None

        # Online-learning model (SGD-based logistic for incremental updates)
        self._online_model: Optional[SGDClassifier] = None

        # Book-keeping
        self.feature_names: List[str] = []
        self.is_trained: bool = False
        self.training_timestamp: Optional[datetime] = None
        self.training_samples: int = 0
        self._feature_importances: Optional[np.ndarray] = None

        logger.info(
            "SignalPredictor initialised: model_type=%s, scale=%s, class_weight=%s",
            model_type.value,
            scale_features,
            class_weight,
        )

    # -- Model construction --------------------------------------------------

    def _build_model(self, params: Dict[str, Any]) -> Any:
        """Instantiate the sklearn estimator."""
        cw = self.class_weight
        if self.model_type == ModelType.RANDOM_FOREST:
            return RandomForestClassifier(class_weight=cw, **params)
        elif self.model_type == ModelType.GRADIENT_BOOSTING:
            # GradientBoosting does not support class_weight natively;
            # we handle it via sample_weight in fit().
            return GradientBoostingClassifier(**params)
        elif self.model_type == ModelType.LOGISTIC_REGRESSION:
            return LogisticRegression(class_weight=cw, **params)
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")

    # -- Training ------------------------------------------------------------

    def train(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: Union[pd.Series, np.ndarray],
        feature_names: Optional[List[str]] = None,
        sample_weight: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """Train the model on labelled data.

        Args:
            X: Feature matrix (n_samples, n_features).
            y: Binary label vector (n_samples,).
            feature_names: Optional list of feature names.  If *X* is a
                DataFrame the column names are used automatically.
            sample_weight: Per-sample weights.  For Gradient Boosting with
                imbalanced data, weights are computed automatically when
                ``class_weight`` was set and *sample_weight* is not provided.

        Returns:
            Dict with training metadata (n_samples, n_features, class_distribution).
        """
        X_arr, feature_names = self._prepare_X(X, feature_names)
        y_arr = np.asarray(y).ravel()

        if len(X_arr) != len(y_arr):
            raise ValueError(
                f"X and y length mismatch: {len(X_arr)} vs {len(y_arr)}"
            )

        self.feature_names = feature_names
        logger.info(
            "Training %s on %d samples with %d features",
            self.model_type.value,
            len(X_arr),
            X_arr.shape[1],
        )

        # Scale
        if self.scaler is not None:
            X_arr = self.scaler.fit_transform(X_arr)

        # Compute sample weights for GB if needed
        if (
            sample_weight is None
            and self.model_type == ModelType.GRADIENT_BOOSTING
            and self.class_weight is not None
        ):
            sample_weight = self._compute_sample_weights(y_arr)

        # Fit
        fit_params: Dict[str, Any] = {}
        if sample_weight is not None:
            fit_params["sample_weight"] = sample_weight

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.model.fit(X_arr, y_arr, **fit_params)

        # Feature importances
        self._extract_feature_importances()

        self.is_trained = True
        self.training_timestamp = datetime.utcnow()
        self.training_samples = len(X_arr)

        class_dist = dict(zip(*np.unique(y_arr, return_counts=True)))
        class_dist = {int(k): int(v) for k, v in class_dist.items()}

        meta = {
            "model_type": self.model_type.value,
            "n_samples": len(X_arr),
            "n_features": X_arr.shape[1],
            "class_distribution": class_dist,
            "timestamp": self.training_timestamp.isoformat(),
        }
        logger.info("Training complete: %s", meta)
        return meta

    def train_with_cv(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: Union[pd.Series, np.ndarray],
        n_splits: int = 5,
        feature_names: Optional[List[str]] = None,
    ) -> Tuple[Dict[str, Any], List[float]]:
        """Train with time-series cross-validation and return fold scores.

        The final model is trained on the full dataset after CV evaluation.

        Args:
            X: Feature matrix.
            y: Label vector.
            n_splits: Number of time-series CV folds.
            feature_names: Optional feature name list.

        Returns:
            Tuple of (training metadata dict, list of per-fold F1 scores).
        """
        X_arr, feature_names = self._prepare_X(X, feature_names)
        y_arr = np.asarray(y).ravel()

        logger.info("Running %d-fold time-series CV before full training", n_splits)

        evaluator = ModelEvaluator()
        # CV on unscaled data -- evaluator will handle cloning
        if self.scaler is not None:
            X_scaled = self.scaler.fit_transform(X_arr)
        else:
            X_scaled = X_arr

        cv_scores = evaluator.cross_validate(
            self.model, X_scaled, y_arr, n_splits=n_splits
        )

        # Now train on full data
        meta = self.train(
            X_arr, y_arr, feature_names=feature_names
        )
        meta["cv_scores"] = cv_scores
        meta["cv_mean_f1"] = float(np.mean(cv_scores))
        meta["cv_std_f1"] = float(np.std(cv_scores))

        return meta, cv_scores

    # -- Online learning -----------------------------------------------------

    def partial_fit(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: Union[pd.Series, np.ndarray],
    ) -> None:
        """Incrementally update the model with new data.

        Uses an SGDClassifier (log loss) under the hood because tree-based
        models do not support native incremental learning.  The SGD model
        is trained alongside the main model and blended at prediction time.

        Args:
            X: New feature matrix.
            y: New label vector.
        """
        X_arr, _ = self._prepare_X(X, self.feature_names or None)
        y_arr = np.asarray(y).ravel()

        if self.scaler is not None:
            if not self.is_trained:
                raise RuntimeError("Call train() before partial_fit()")
            X_arr = self.scaler.transform(X_arr)

        if self._online_model is None:
            self._online_model = SGDClassifier(
                loss="log_loss",
                random_state=42,
                warm_start=False,
            )

        classes = np.array([0, 1])
        self._online_model.partial_fit(X_arr, y_arr, classes=classes)
        self.training_samples += len(X_arr)

        logger.info(
            "Incremental update with %d samples (total tracked: %d)",
            len(X_arr),
            self.training_samples,
        )

    # -- Prediction ----------------------------------------------------------

    def predict(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        blend_online: bool = True,
        online_weight: float = 0.3,
    ) -> List[PredictionResult]:
        """Generate predictions with confidence scores.

        Args:
            X: Feature matrix for prediction.
            blend_online: If an online model exists, blend its probabilities
                with the main model's.
            online_weight: Weight assigned to the online model in the blend
                (main model gets ``1 - online_weight``).

        Returns:
            List of ``PredictionResult`` objects, one per input row.
        """
        if not self.is_trained:
            raise RuntimeError("Model has not been trained yet. Call train() first.")

        X_arr, _ = self._prepare_X(X, self.feature_names or None)

        if self.scaler is not None:
            X_arr = self.scaler.transform(X_arr)

        # Main model probabilities
        proba = self.model.predict_proba(X_arr)

        # Blend with online model if available
        if blend_online and self._online_model is not None:
            try:
                online_proba = self._online_model.predict_proba(X_arr)
                proba = (1 - online_weight) * proba + online_weight * online_proba
                logger.debug("Blended online model probabilities (weight=%.2f)", online_weight)
            except Exception as exc:
                logger.warning("Could not blend online model: %s", exc)

        results: List[PredictionResult] = []
        classes = self.model.classes_
        for i in range(len(X_arr)):
            prob_dict = {int(cls): float(proba[i, j]) for j, cls in enumerate(classes)}
            pred_label = int(classes[np.argmax(proba[i])])
            confidence = float(np.max(proba[i]))

            results.append(
                PredictionResult(
                    label=pred_label,
                    confidence=confidence,
                    probabilities=prob_dict,
                    features_used=X_arr.shape[1],
                )
            )

        logger.info("Generated %d predictions", len(results))
        return results

    def predict_single(
        self,
        X: Union[pd.DataFrame, np.ndarray],
    ) -> PredictionResult:
        """Convenience method to predict a single sample.

        Args:
            X: Feature vector (1, n_features) or single-row DataFrame.

        Returns:
            A single ``PredictionResult``.
        """
        results = self.predict(X)
        return results[0]

    # -- Feature importance --------------------------------------------------

    def feature_importance(self, top_n: Optional[int] = None) -> pd.DataFrame:
        """Return feature importances as a sorted DataFrame.

        Args:
            top_n: If provided, return only the top *n* features.

        Returns:
            DataFrame with columns ``feature`` and ``importance``, sorted
            descending by importance.
        """
        if self._feature_importances is None:
            raise RuntimeError("No feature importances available. Train the model first.")

        imp_df = pd.DataFrame({
            "feature": self.feature_names,
            "importance": self._feature_importances,
        }).sort_values("importance", ascending=False).reset_index(drop=True)

        if top_n is not None:
            imp_df = imp_df.head(top_n)

        return imp_df

    def _extract_feature_importances(self) -> None:
        """Extract feature importances from the fitted model."""
        if hasattr(self.model, "feature_importances_"):
            self._feature_importances = self.model.feature_importances_
        elif hasattr(self.model, "coef_"):
            self._feature_importances = np.abs(self.model.coef_).ravel()
        else:
            self._feature_importances = None
            logger.debug("Model does not expose feature importances")

    # -- Persistence ---------------------------------------------------------

    def save(self, filepath: str) -> None:
        """Save the trained model, scaler, and metadata to disk.

        Args:
            filepath: Destination file path (e.g. ``"models/model.joblib"``).

        Raises:
            ImportError: If joblib is not installed.
            RuntimeError: If the model has not been trained.
        """
        if not JOBLIB_AVAILABLE:
            raise ImportError(
                "joblib is required for model persistence. "
                "Install it with: pip install joblib"
            )
        if not self.is_trained:
            raise RuntimeError("Cannot save an untrained model.")

        state = {
            "model": self.model,
            "scaler": self.scaler,
            "online_model": self._online_model,
            "model_type": self.model_type,
            "params": self.params,
            "feature_names": self.feature_names,
            "scale_features": self.scale_features,
            "class_weight": self.class_weight,
            "training_timestamp": self.training_timestamp,
            "training_samples": self.training_samples,
            "feature_importances": self._feature_importances,
        }

        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        joblib.dump(state, filepath)
        logger.info("Model saved to %s", filepath)

    @classmethod
    def load(cls, filepath: str) -> "SignalPredictor":
        """Load a previously saved model from disk.

        Args:
            filepath: Path to the saved model file.

        Returns:
            A fully initialised ``SignalPredictor`` instance.
        """
        if not JOBLIB_AVAILABLE:
            raise ImportError(
                "joblib is required for model persistence. "
                "Install it with: pip install joblib"
            )

        state = joblib.load(filepath)
        logger.info("Loading model from %s", filepath)

        instance = cls(
            model_type=state["model_type"],
            params=state["params"],
            scale_features=state["scale_features"],
            class_weight=state["class_weight"],
        )
        instance.model = state["model"]
        instance.scaler = state["scaler"]
        instance._online_model = state.get("online_model")
        instance.feature_names = state["feature_names"]
        instance.training_timestamp = state["training_timestamp"]
        instance.training_samples = state["training_samples"]
        instance._feature_importances = state.get("feature_importances")
        instance.is_trained = True

        logger.info(
            "Model loaded: type=%s, trained on %d samples at %s",
            instance.model_type.value,
            instance.training_samples,
            instance.training_timestamp,
        )
        return instance

    # -- Summary / repr ------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        """Return a summary dict describing the current model state."""
        info: Dict[str, Any] = {
            "model_type": self.model_type.value,
            "is_trained": self.is_trained,
            "scale_features": self.scale_features,
            "class_weight": str(self.class_weight),
            "n_features": len(self.feature_names),
            "feature_names": self.feature_names,
            "training_samples": self.training_samples,
            "has_online_model": self._online_model is not None,
        }
        if self.training_timestamp:
            info["training_timestamp"] = self.training_timestamp.isoformat()
        return info

    def __repr__(self) -> str:
        status = "trained" if self.is_trained else "untrained"
        return (
            f"SignalPredictor(model_type={self.model_type.value}, "
            f"status={status}, features={len(self.feature_names)}, "
            f"samples={self.training_samples})"
        )

    # -- Internal helpers ----------------------------------------------------

    def _prepare_X(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        feature_names: Optional[List[str]],
    ) -> Tuple[np.ndarray, List[str]]:
        """Convert X to a numpy array and resolve feature names."""
        if isinstance(X, pd.DataFrame):
            names = list(X.columns)
            arr = X.values.astype(np.float64)
        else:
            arr = np.asarray(X, dtype=np.float64)
            if arr.ndim == 1:
                arr = arr.reshape(1, -1)
            names = feature_names or [f"f{i}" for i in range(arr.shape[1])]
        return arr, names

    def _compute_sample_weights(self, y: np.ndarray) -> np.ndarray:
        """Compute per-sample weights from class_weight specification."""
        if isinstance(self.class_weight, dict):
            weight_map = self.class_weight
        elif self.class_weight == "balanced":
            classes = np.unique(y)
            weights = compute_class_weight("balanced", classes=classes, y=y)
            weight_map = dict(zip(classes, weights))
        else:
            return np.ones(len(y))

        return np.array([weight_map.get(int(yi), 1.0) for yi in y])


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _clone_model(model: Any) -> Any:
    """Create a fresh clone of an sklearn estimator.

    Uses sklearn's ``clone`` if available, otherwise falls back to
    re-instantiation via ``get_params()``.
    """
    try:
        from sklearn.base import clone
        return clone(model)
    except ImportError:
        return model.__class__(**model.get_params())


def build_training_pipeline(
    ohlcv_df: pd.DataFrame,
    lookahead: int = 10,
    profit_threshold: float = 0.5,
    signal_col: Optional[str] = None,
    model_type: ModelType = ModelType.GRADIENT_BOOSTING,
    cv_splits: int = 5,
) -> Tuple[SignalPredictor, EvaluationResult]:
    """End-to-end convenience function: feature engineering, labelling,
    training, and evaluation.

    Args:
        ohlcv_df: Raw OHLCV DataFrame.
        lookahead: Bars to look ahead for labelling.
        profit_threshold: Minimum % move threshold for a *good* signal.
        signal_col: Optional signal direction column.
        model_type: Which ML algorithm to use.
        cv_splits: Number of time-series CV folds.

    Returns:
        Tuple of (trained ``SignalPredictor``, ``EvaluationResult``).

    Example::

        predictor, eval_result = build_training_pipeline(df, lookahead=10)
        print(eval_result.f1)
    """
    logger.info("=== Starting training pipeline ===")

    # 1. Feature engineering
    fe = FeatureEngineering()
    featured_df = fe.build_features(ohlcv_df)
    feature_cols = fe.get_feature_columns(featured_df)

    # 2. Labelling
    labeler = SignalQualityLabeler(
        lookahead=lookahead, profit_threshold=profit_threshold
    )
    labelled_df = labeler.label(featured_df, signal_col=signal_col)
    labelled_df = labelled_df.dropna(subset=["label"])

    if len(labelled_df) < 50:
        raise ValueError(
            f"Not enough labelled samples for training: {len(labelled_df)}"
        )

    X = labelled_df[feature_cols]
    y = labelled_df["label"].astype(int)

    # 3. Time-series train/test split (last 20% for testing)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    logger.info("Train set: %d samples | Test set: %d samples", len(X_train), len(X_test))

    # 4. Train with CV
    predictor = SignalPredictor(model_type=model_type)
    meta, cv_scores = predictor.train_with_cv(X_train, y_train, n_splits=cv_splits)

    # 5. Evaluate on held-out test set
    predictions = predictor.predict(X_test)
    y_pred = np.array([p.label for p in predictions])
    y_prob = np.array([p.probabilities.get(1, 0.0) for p in predictions])

    evaluator = ModelEvaluator()
    eval_result = evaluator.evaluate(
        y_true=y_test.values,
        y_pred=y_pred,
        y_prob=y_prob,
        prices=labelled_df["close"].iloc[split_idx:],
    )
    eval_result.cv_scores = cv_scores

    logger.info("=== Training pipeline complete ===")
    return predictor, eval_result
