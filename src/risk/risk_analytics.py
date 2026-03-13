"""
Risk Analytics Module

Comprehensive risk measurement, drawdown analysis, portfolio risk decomposition,
and risk limit monitoring for commodity trading strategies.

Classes:
    - RiskAnalytics: Core risk metrics (VaR, CVaR, ratios, drawdown, beta/alpha)
    - DrawdownAnalyzer: Detailed drawdown period analysis and recovery tracking
    - PortfolioRiskDashboard: Aggregate portfolio risk view and decomposition
    - RiskLimitManager: Real-time risk limit monitoring and alerting

Author: ScreenerIII
License: MIT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

# Optional scipy imports
try:
    from scipy import stats as scipy_stats
    from scipy.optimize import minimize as scipy_minimize
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TRADING_DAYS_PER_YEAR = 252
RISK_FREE_RATE_DEFAULT = 0.05  # 5% annualized
CONFIDENCE_LEVELS = (0.90, 0.95, 0.99)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class VaRMethod(Enum):
    """Supported Value-at-Risk calculation methods."""
    HISTORICAL = "historical"
    PARAMETRIC = "parametric"
    MONTE_CARLO = "monte_carlo"


class AlertSeverity(Enum):
    """Risk alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    BREACH = "breach"


@dataclass
class VaRResult:
    """Container for a Value-at-Risk calculation result."""
    method: VaRMethod
    confidence_level: float
    var_value: float
    horizon_days: int
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __repr__(self) -> str:
        return (
            f"VaR({self.method.value}, {self.confidence_level:.0%}): "
            f"{self.var_value:+.4f} over {self.horizon_days}d"
        )


@dataclass
class DrawdownPeriod:
    """Represents a single drawdown episode."""
    start_date: datetime
    end_date: Optional[datetime]
    trough_date: datetime
    depth: float  # maximum peak-to-trough decline (negative value)
    recovery_date: Optional[datetime]
    duration_days: int
    recovery_days: Optional[int]
    peak_value: float
    trough_value: float


@dataclass
class RiskAlert:
    """Risk limit alert."""
    timestamp: datetime
    severity: AlertSeverity
    limit_name: str
    limit_value: float
    current_value: float
    utilisation_pct: float
    message: str


# ---------------------------------------------------------------------------
# RiskAnalytics
# ---------------------------------------------------------------------------

class RiskAnalytics:
    """Core risk metrics calculations for return series.

    Provides Value-at-Risk (Historical, Parametric, Monte Carlo),
    Conditional VaR, maximum drawdown analysis, and standard
    risk-adjusted performance ratios.

    Parameters
    ----------
    returns : pd.Series
        Daily arithmetic returns indexed by date.
    risk_free_rate : float, optional
        Annualized risk-free rate (default 0.05).
    trading_days : int, optional
        Number of trading days per year (default 252).

    Examples
    --------
    >>> import pandas as pd, numpy as np
    >>> returns = pd.Series(np.random.normal(0.0005, 0.01, 500))
    >>> ra = RiskAnalytics(returns)
    >>> ra.sharpe_ratio()
    """

    def __init__(
        self,
        returns: pd.Series,
        risk_free_rate: float = RISK_FREE_RATE_DEFAULT,
        trading_days: int = TRADING_DAYS_PER_YEAR,
    ) -> None:
        if returns.empty:
            raise ValueError("returns series must not be empty")
        self._returns = returns.astype(float).dropna()
        self._risk_free_rate = risk_free_rate
        self._trading_days = trading_days
        self._daily_rf = (1 + risk_free_rate) ** (1 / trading_days) - 1
        logger.info(
            "RiskAnalytics initialised with %d return observations", len(self._returns)
        )

    # -- properties ----------------------------------------------------------

    @property
    def returns(self) -> pd.Series:
        """Underlying daily return series."""
        return self._returns

    @property
    def cumulative_returns(self) -> pd.Series:
        """Cumulative wealth index (starting at 1.0)."""
        return (1 + self._returns).cumprod()

    # -- VaR -----------------------------------------------------------------

    def var_historical(
        self, confidence: float = 0.95, horizon: int = 1
    ) -> VaRResult:
        """Historical (non-parametric) Value-at-Risk.

        Parameters
        ----------
        confidence : float
            Confidence level (e.g. 0.95 for 95%).
        horizon : int
            Holding period in trading days.

        Returns
        -------
        VaRResult
        """
        alpha = 1 - confidence
        if horizon == 1:
            var_val = float(np.percentile(self._returns, alpha * 100))
        else:
            # Use overlapping multi-day returns
            multi = self._returns.rolling(horizon).sum().dropna()
            var_val = float(np.percentile(multi, alpha * 100))
        logger.debug(
            "Historical VaR(%.0f%%, %dd) = %.6f", confidence * 100, horizon, var_val
        )
        return VaRResult(
            method=VaRMethod.HISTORICAL,
            confidence_level=confidence,
            var_value=var_val,
            horizon_days=horizon,
        )

    def var_parametric(
        self, confidence: float = 0.95, horizon: int = 1
    ) -> VaRResult:
        """Parametric (Gaussian) Value-at-Risk.

        Uses the normal distribution assumption.  For multi-day VaR the
        square-root-of-time rule is applied.

        Parameters
        ----------
        confidence : float
            Confidence level.
        horizon : int
            Holding period in trading days.

        Returns
        -------
        VaRResult
        """
        if not SCIPY_AVAILABLE:
            logger.warning("scipy not available; falling back to z-table approximation")
            # Approximate z-scores for common confidence levels
            z_map = {0.90: 1.2816, 0.95: 1.6449, 0.99: 2.3263}
            z = z_map.get(round(confidence, 2), 1.6449)
        else:
            z = scipy_stats.norm.ppf(confidence)

        mu = float(self._returns.mean())
        sigma = float(self._returns.std(ddof=1))
        var_val = -(mu * horizon - z * sigma * np.sqrt(horizon))
        # Return as a loss (negative of portfolio return)
        var_val = -var_val  # keep sign convention: negative = loss
        logger.debug(
            "Parametric VaR(%.0f%%, %dd) = %.6f", confidence * 100, horizon, var_val
        )
        return VaRResult(
            method=VaRMethod.PARAMETRIC,
            confidence_level=confidence,
            var_value=var_val,
            horizon_days=horizon,
        )

    def var_monte_carlo(
        self,
        confidence: float = 0.95,
        horizon: int = 1,
        n_simulations: int = 10_000,
        seed: Optional[int] = None,
    ) -> VaRResult:
        """Monte Carlo Value-at-Risk.

        Simulates future return paths using bootstrapped daily returns
        and computes VaR from the simulated distribution.

        Parameters
        ----------
        confidence : float
            Confidence level.
        horizon : int
            Holding period in trading days.
        n_simulations : int
            Number of simulation paths.
        seed : int, optional
            Random seed for reproducibility.

        Returns
        -------
        VaRResult
        """
        rng = np.random.default_rng(seed)
        sim_returns = rng.choice(
            self._returns.values, size=(n_simulations, horizon), replace=True
        )
        # Compound returns over the horizon
        sim_total = np.prod(1 + sim_returns, axis=1) - 1
        alpha = 1 - confidence
        var_val = float(np.percentile(sim_total, alpha * 100))
        logger.debug(
            "Monte Carlo VaR(%.0f%%, %dd, %d sims) = %.6f",
            confidence * 100, horizon, n_simulations, var_val,
        )
        return VaRResult(
            method=VaRMethod.MONTE_CARLO,
            confidence_level=confidence,
            var_value=var_val,
            horizon_days=horizon,
        )

    def var_all_methods(
        self, confidence: float = 0.95, horizon: int = 1
    ) -> Dict[str, VaRResult]:
        """Compute VaR using all three methods.

        Returns
        -------
        dict
            Mapping of method name to VaRResult.
        """
        return {
            "historical": self.var_historical(confidence, horizon),
            "parametric": self.var_parametric(confidence, horizon),
            "monte_carlo": self.var_monte_carlo(confidence, horizon),
        }

    # -- CVaR / Expected Shortfall -------------------------------------------

    def cvar(
        self, confidence: float = 0.95, horizon: int = 1
    ) -> float:
        """Conditional Value-at-Risk (Expected Shortfall).

        The average loss in the worst ``(1 - confidence)`` fraction of
        scenarios, computed from historical returns.

        Parameters
        ----------
        confidence : float
            Confidence level.
        horizon : int
            Holding period in trading days.

        Returns
        -------
        float
            CVaR value (negative indicates a loss).
        """
        alpha = 1 - confidence
        if horizon == 1:
            data = self._returns
        else:
            data = self._returns.rolling(horizon).sum().dropna()
        cutoff = np.percentile(data, alpha * 100)
        tail = data[data <= cutoff]
        cvar_val = float(tail.mean()) if len(tail) > 0 else float(cutoff)
        logger.debug("CVaR(%.0f%%, %dd) = %.6f", confidence * 100, horizon, cvar_val)
        return cvar_val

    # -- Drawdown helpers ----------------------------------------------------

    def _equity_curve(self) -> pd.Series:
        """Cumulative wealth curve starting at 1."""
        return (1 + self._returns).cumprod()

    def _drawdown_series(self) -> pd.Series:
        """Per-period drawdown from running peak."""
        equity = self._equity_curve()
        peak = equity.cummax()
        return (equity - peak) / peak

    def maximum_drawdown(self) -> float:
        """Maximum peak-to-trough drawdown (negative value).

        Returns
        -------
        float
            Maximum drawdown as a decimal (e.g. -0.25 means 25% decline).
        """
        dd = self._drawdown_series()
        mdd = float(dd.min())
        logger.debug("Maximum drawdown = %.4f", mdd)
        return mdd

    def maximum_drawdown_duration(self) -> int:
        """Duration in observations of the longest drawdown.

        Returns
        -------
        int
            Number of periods from peak to recovery (or end of series).
        """
        dd = self._drawdown_series()
        in_dd = dd < 0
        if not in_dd.any():
            return 0
        groups = (~in_dd).cumsum()
        durations = in_dd.groupby(groups).sum()
        max_dur = int(durations.max())
        logger.debug("Max drawdown duration = %d periods", max_dur)
        return max_dur

    # -- Risk-adjusted ratios ------------------------------------------------

    def sharpe_ratio(self) -> float:
        """Annualized Sharpe ratio.

        Returns
        -------
        float
        """
        excess = self._returns - self._daily_rf
        if excess.std() == 0:
            return 0.0
        sr = float(excess.mean() / excess.std() * np.sqrt(self._trading_days))
        logger.debug("Sharpe ratio = %.4f", sr)
        return sr

    def sortino_ratio(self) -> float:
        """Annualized Sortino ratio (using downside deviation).

        Returns
        -------
        float
        """
        excess = self._returns - self._daily_rf
        downside = excess[excess < 0]
        if len(downside) == 0 or downside.std() == 0:
            return float("inf") if excess.mean() > 0 else 0.0
        dd_std = float(np.sqrt((downside ** 2).mean()))
        sr = float(excess.mean() / dd_std * np.sqrt(self._trading_days))
        logger.debug("Sortino ratio = %.4f", sr)
        return sr

    def calmar_ratio(self) -> float:
        """Calmar ratio = annualized return / |max drawdown|.

        Returns
        -------
        float
        """
        ann_ret = float(self._returns.mean() * self._trading_days)
        mdd = abs(self.maximum_drawdown())
        if mdd == 0:
            return float("inf") if ann_ret > 0 else 0.0
        cr = ann_ret / mdd
        logger.debug("Calmar ratio = %.4f", cr)
        return cr

    def information_ratio(self, benchmark_returns: pd.Series) -> float:
        """Information ratio vs. a benchmark.

        Parameters
        ----------
        benchmark_returns : pd.Series
            Benchmark daily returns aligned to the same dates.

        Returns
        -------
        float
        """
        active = self._returns - benchmark_returns.reindex(self._returns.index).fillna(0)
        te = float(active.std(ddof=1))
        if te == 0:
            return 0.0
        ir = float(active.mean() / te * np.sqrt(self._trading_days))
        logger.debug("Information ratio = %.4f", ir)
        return ir

    # -- Beta / Alpha --------------------------------------------------------

    def beta(self, benchmark_returns: pd.Series) -> float:
        """Portfolio beta relative to a benchmark.

        Parameters
        ----------
        benchmark_returns : pd.Series
            Benchmark daily returns.

        Returns
        -------
        float
        """
        aligned = pd.DataFrame({
            "port": self._returns,
            "bench": benchmark_returns,
        }).dropna()
        if len(aligned) < 2:
            logger.warning("Insufficient overlapping data for beta calculation")
            return 0.0
        cov_matrix = np.cov(aligned["port"], aligned["bench"])
        bench_var = cov_matrix[1, 1]
        if bench_var == 0:
            return 0.0
        b = float(cov_matrix[0, 1] / bench_var)
        logger.debug("Beta = %.4f", b)
        return b

    def alpha(self, benchmark_returns: pd.Series) -> float:
        """Annualized Jensen's alpha.

        Parameters
        ----------
        benchmark_returns : pd.Series
            Benchmark daily returns.

        Returns
        -------
        float
        """
        b = self.beta(benchmark_returns)
        aligned = pd.DataFrame({
            "port": self._returns,
            "bench": benchmark_returns,
        }).dropna()
        port_ann = float(aligned["port"].mean() * self._trading_days)
        bench_ann = float(aligned["bench"].mean() * self._trading_days)
        a = port_ann - (self._risk_free_rate + b * (bench_ann - self._risk_free_rate))
        logger.debug("Alpha = %.4f", a)
        return a

    # -- Tracking error & downside deviation ---------------------------------

    def tracking_error(self, benchmark_returns: pd.Series) -> float:
        """Annualized tracking error.

        Parameters
        ----------
        benchmark_returns : pd.Series
            Benchmark daily returns.

        Returns
        -------
        float
        """
        active = self._returns - benchmark_returns.reindex(self._returns.index).fillna(0)
        te = float(active.std(ddof=1) * np.sqrt(self._trading_days))
        logger.debug("Tracking error = %.4f", te)
        return te

    def downside_deviation(self, mar: Optional[float] = None) -> float:
        """Annualized downside deviation.

        Parameters
        ----------
        mar : float, optional
            Minimum acceptable return per period.  Defaults to the
            daily risk-free rate.

        Returns
        -------
        float
        """
        if mar is None:
            mar = self._daily_rf
        diff = self._returns - mar
        neg = diff.clip(upper=0)
        dd = float(np.sqrt((neg ** 2).mean()) * np.sqrt(self._trading_days))
        logger.debug("Downside deviation = %.4f", dd)
        return dd

    # -- Summary -------------------------------------------------------------

    def summary(self, benchmark_returns: Optional[pd.Series] = None) -> Dict[str, float]:
        """Return a dictionary of all core risk metrics.

        Parameters
        ----------
        benchmark_returns : pd.Series, optional
            If provided, benchmark-relative metrics are included.

        Returns
        -------
        dict
        """
        s: Dict[str, float] = {
            "annualized_return": float(self._returns.mean() * self._trading_days),
            "annualized_volatility": float(
                self._returns.std(ddof=1) * np.sqrt(self._trading_days)
            ),
            "sharpe_ratio": self.sharpe_ratio(),
            "sortino_ratio": self.sortino_ratio(),
            "calmar_ratio": self.calmar_ratio(),
            "max_drawdown": self.maximum_drawdown(),
            "max_drawdown_duration": self.maximum_drawdown_duration(),
            "downside_deviation": self.downside_deviation(),
            "var_95_historical": self.var_historical(0.95).var_value,
            "var_99_historical": self.var_historical(0.99).var_value,
            "cvar_95": self.cvar(0.95),
            "cvar_99": self.cvar(0.99),
            "skewness": float(self._returns.skew()),
            "kurtosis": float(self._returns.kurtosis()),
        }
        if benchmark_returns is not None:
            s["beta"] = self.beta(benchmark_returns)
            s["alpha"] = self.alpha(benchmark_returns)
            s["tracking_error"] = self.tracking_error(benchmark_returns)
            s["information_ratio"] = self.information_ratio(benchmark_returns)
        logger.info("Risk summary computed with %d metrics", len(s))
        return s


# ---------------------------------------------------------------------------
# DrawdownAnalyzer
# ---------------------------------------------------------------------------

class DrawdownAnalyzer:
    """Detailed drawdown analysis and recovery tracking.

    Identifies all drawdown periods in an equity or return series,
    computes underwater curves, and provides duration/recovery statistics.

    Parameters
    ----------
    returns : pd.Series
        Daily arithmetic returns indexed by date.
    initial_equity : float, optional
        Starting equity value for the wealth curve (default 1.0).

    Examples
    --------
    >>> analyzer = DrawdownAnalyzer(returns)
    >>> periods = analyzer.drawdown_periods()
    >>> analyzer.average_drawdown()
    """

    def __init__(
        self, returns: pd.Series, initial_equity: float = 1.0
    ) -> None:
        if returns.empty:
            raise ValueError("returns series must not be empty")
        self._returns = returns.astype(float).dropna()
        self._initial_equity = initial_equity
        self._equity = self._build_equity()
        self._peak = self._equity.cummax()
        self._underwater = (self._equity - self._peak) / self._peak
        self._periods: Optional[List[DrawdownPeriod]] = None
        logger.info(
            "DrawdownAnalyzer initialised with %d observations", len(self._returns)
        )

    # -- internals -----------------------------------------------------------

    def _build_equity(self) -> pd.Series:
        """Build the equity curve from returns."""
        return self._initial_equity * (1 + self._returns).cumprod()

    def _identify_periods(self) -> List[DrawdownPeriod]:
        """Walk through the underwater series and identify distinct drawdown episodes."""
        periods: List[DrawdownPeriod] = []
        in_drawdown = False
        start_idx = None
        trough_idx = None
        trough_val = 0.0
        peak_val = 0.0

        uw = self._underwater
        eq = self._equity
        pk = self._peak

        for i, (idx, val) in enumerate(uw.items()):
            if val < 0 and not in_drawdown:
                # Drawdown begins
                in_drawdown = True
                # Start is the previous peak date (or series start)
                start_idx = uw.index[max(0, i - 1)]
                trough_idx = idx
                trough_val = val
                peak_val = float(pk.iloc[max(0, i - 1)])
            elif val < 0 and in_drawdown:
                if val < trough_val:
                    trough_val = val
                    trough_idx = idx
            elif val >= 0 and in_drawdown:
                # Drawdown recovered
                in_drawdown = False
                recovery_date = idx
                start_dt = self._to_datetime(start_idx)
                trough_dt = self._to_datetime(trough_idx)
                recovery_dt = self._to_datetime(recovery_date)
                end_dt = self._to_datetime(uw.index[i - 1]) if i > 0 else trough_dt
                duration = (recovery_dt - start_dt).days if isinstance(
                    start_dt, datetime
                ) else i
                recovery_d = (recovery_dt - trough_dt).days if isinstance(
                    trough_dt, datetime
                ) else None
                periods.append(DrawdownPeriod(
                    start_date=start_dt,
                    end_date=end_dt,
                    trough_date=trough_dt,
                    depth=trough_val,
                    recovery_date=recovery_dt,
                    duration_days=duration if isinstance(duration, int) else int(duration),
                    recovery_days=recovery_d if recovery_d is None or isinstance(recovery_d, int) else int(recovery_d),
                    peak_value=peak_val,
                    trough_value=float(eq.loc[trough_idx]) if trough_idx in eq.index else peak_val * (1 + trough_val),
                ))

        # Handle ongoing drawdown at end of series
        if in_drawdown and start_idx is not None and trough_idx is not None:
            start_dt = self._to_datetime(start_idx)
            trough_dt = self._to_datetime(trough_idx)
            end_dt = self._to_datetime(uw.index[-1])
            duration = (end_dt - start_dt).days if isinstance(start_dt, datetime) else len(uw)
            periods.append(DrawdownPeriod(
                start_date=start_dt,
                end_date=end_dt,
                trough_date=trough_dt,
                depth=trough_val,
                recovery_date=None,
                duration_days=duration if isinstance(duration, int) else int(duration),
                recovery_days=None,
                peak_value=peak_val,
                trough_value=float(eq.loc[trough_idx]) if trough_idx in eq.index else peak_val * (1 + trough_val),
            ))

        return periods

    @staticmethod
    def _to_datetime(val: Any) -> datetime:
        """Best-effort conversion to datetime."""
        if isinstance(val, datetime):
            return val
        if isinstance(val, pd.Timestamp):
            return val.to_pydatetime()
        try:
            return pd.Timestamp(val).to_pydatetime()
        except Exception:
            return datetime.utcnow()

    # -- public API ----------------------------------------------------------

    @property
    def equity_curve(self) -> pd.Series:
        """Equity (wealth) curve."""
        return self._equity

    @property
    def underwater_curve(self) -> pd.Series:
        """Underwater equity curve (drawdown from running peak at each point)."""
        return self._underwater

    def current_drawdown(self) -> float:
        """Current drawdown from the most recent peak.

        Returns
        -------
        float
            Current drawdown as a decimal (0.0 means at peak).
        """
        val = float(self._underwater.iloc[-1])
        logger.debug("Current drawdown = %.4f", val)
        return val

    def drawdown_periods(self, top_n: Optional[int] = None) -> List[DrawdownPeriod]:
        """Return all identified drawdown periods, sorted by depth.

        Parameters
        ----------
        top_n : int, optional
            If provided, return only the *top_n* deepest drawdowns.

        Returns
        -------
        list of DrawdownPeriod
        """
        if self._periods is None:
            self._periods = self._identify_periods()
        sorted_periods = sorted(self._periods, key=lambda p: p.depth)
        if top_n is not None:
            sorted_periods = sorted_periods[:top_n]
        logger.info("Returning %d drawdown periods", len(sorted_periods))
        return sorted_periods

    def average_drawdown(self) -> float:
        """Average drawdown depth across all identified periods.

        Returns
        -------
        float
        """
        periods = self.drawdown_periods()
        if not periods:
            return 0.0
        avg = float(np.mean([p.depth for p in periods]))
        logger.debug("Average drawdown = %.4f", avg)
        return avg

    def average_drawdown_duration(self) -> float:
        """Average drawdown duration in days.

        Returns
        -------
        float
        """
        periods = self.drawdown_periods()
        if not periods:
            return 0.0
        avg = float(np.mean([p.duration_days for p in periods]))
        logger.debug("Average drawdown duration = %.1f days", avg)
        return avg

    def average_recovery_time(self) -> float:
        """Average recovery time (days) for completed drawdowns.

        Returns
        -------
        float
            NaN if no completed drawdowns exist.
        """
        periods = self.drawdown_periods()
        recovered = [p for p in periods if p.recovery_days is not None]
        if not recovered:
            return float("nan")
        avg = float(np.mean([p.recovery_days for p in recovered]))
        logger.debug("Average recovery time = %.1f days", avg)
        return avg

    def max_drawdown(self) -> float:
        """Maximum drawdown depth.

        Returns
        -------
        float
        """
        return float(self._underwater.min())

    def drawdown_statistics(self) -> Dict[str, float]:
        """Summary statistics for drawdown analysis.

        Returns
        -------
        dict
        """
        periods = self.drawdown_periods()
        depths = [p.depth for p in periods] if periods else [0.0]
        durations = [p.duration_days for p in periods] if periods else [0]
        return {
            "current_drawdown": self.current_drawdown(),
            "max_drawdown": self.max_drawdown(),
            "avg_drawdown": float(np.mean(depths)),
            "median_drawdown": float(np.median(depths)),
            "std_drawdown": float(np.std(depths, ddof=1)) if len(depths) > 1 else 0.0,
            "num_drawdown_periods": len(periods),
            "avg_duration_days": float(np.mean(durations)),
            "max_duration_days": int(np.max(durations)),
            "avg_recovery_days": self.average_recovery_time(),
        }


# ---------------------------------------------------------------------------
# PortfolioRiskDashboard
# ---------------------------------------------------------------------------

class PortfolioRiskDashboard:
    """Aggregate portfolio risk view and decomposition.

    Combines per-instrument return data to produce a portfolio-level
    risk dashboard including heat-map data, concentration metrics,
    and marginal risk contributions.

    Parameters
    ----------
    returns_df : pd.DataFrame
        DataFrame where each column is daily returns for one instrument.
    weights : dict or pd.Series, optional
        Mapping of instrument name to portfolio weight.  If omitted,
        equal weights are assumed.
    risk_free_rate : float, optional
        Annualized risk-free rate (default 0.05).

    Examples
    --------
    >>> dashboard = PortfolioRiskDashboard(returns_df, weights={"CL": 0.4, "GC": 0.6})
    >>> dashboard.risk_summary()
    """

    def __init__(
        self,
        returns_df: pd.DataFrame,
        weights: Optional[Union[Dict[str, float], pd.Series]] = None,
        risk_free_rate: float = RISK_FREE_RATE_DEFAULT,
    ) -> None:
        if returns_df.empty:
            raise ValueError("returns_df must not be empty")
        self._returns = returns_df.astype(float).dropna(how="all")
        self._instruments = list(self._returns.columns)
        self._n = len(self._instruments)

        # Weights
        if weights is None:
            w = np.ones(self._n) / self._n
        elif isinstance(weights, dict):
            w = np.array([weights.get(c, 0.0) for c in self._instruments])
        else:
            w = np.array([weights.get(c, 0.0) for c in self._instruments])
        total_w = w.sum()
        if total_w > 0:
            w = w / total_w
        self._weights = pd.Series(w, index=self._instruments)

        self._risk_free_rate = risk_free_rate
        self._cov: Optional[pd.DataFrame] = None
        self._corr: Optional[pd.DataFrame] = None
        logger.info(
            "PortfolioRiskDashboard initialised with %d instruments", self._n
        )

    # -- lazy computed properties ---------------------------------------------

    @property
    def covariance_matrix(self) -> pd.DataFrame:
        """Annualized covariance matrix."""
        if self._cov is None:
            self._cov = self._returns.cov() * TRADING_DAYS_PER_YEAR
        return self._cov

    @property
    def correlation_matrix(self) -> pd.DataFrame:
        """Correlation matrix of instrument returns."""
        if self._corr is None:
            self._corr = self._returns.corr()
        return self._corr

    @property
    def portfolio_returns(self) -> pd.Series:
        """Weighted portfolio daily returns."""
        return (self._returns * self._weights).sum(axis=1)

    # -- portfolio-level metrics ---------------------------------------------

    def portfolio_volatility(self) -> float:
        """Annualized portfolio volatility.

        Returns
        -------
        float
        """
        w = self._weights.values
        cov = self.covariance_matrix.values
        port_var = float(w @ cov @ w)
        vol = float(np.sqrt(port_var))
        logger.debug("Portfolio volatility = %.4f", vol)
        return vol

    def portfolio_sharpe(self) -> float:
        """Portfolio Sharpe ratio.

        Returns
        -------
        float
        """
        port_ret = float(self.portfolio_returns.mean() * TRADING_DAYS_PER_YEAR)
        vol = self.portfolio_volatility()
        if vol == 0:
            return 0.0
        return (port_ret - self._risk_free_rate) / vol

    # -- heat map / risk contributions ----------------------------------------

    def risk_contribution(self) -> pd.Series:
        """Risk contribution of each instrument to total portfolio volatility.

        Uses the Euler decomposition: RC_i = w_i * (Cov @ w)_i / sigma_p.

        Returns
        -------
        pd.Series
            Risk contribution per instrument (sums to portfolio volatility).
        """
        w = self._weights.values
        cov = self.covariance_matrix.values
        port_vol = self.portfolio_volatility()
        if port_vol == 0:
            return pd.Series(0.0, index=self._instruments)
        marginal = cov @ w
        rc = w * marginal / port_vol
        result = pd.Series(rc, index=self._instruments)
        logger.debug("Risk contributions computed")
        return result

    def percentage_risk_contribution(self) -> pd.Series:
        """Percentage risk contribution per instrument.

        Returns
        -------
        pd.Series
            Each value is the fraction of total portfolio risk.
        """
        rc = self.risk_contribution()
        total = rc.sum()
        if total == 0:
            return pd.Series(0.0, index=self._instruments)
        return rc / total

    def marginal_risk_contribution(self) -> pd.Series:
        """Marginal risk contribution per instrument.

        The derivative of portfolio volatility with respect to weight w_i.

        Returns
        -------
        pd.Series
        """
        w = self._weights.values
        cov = self.covariance_matrix.values
        port_vol = self.portfolio_volatility()
        if port_vol == 0:
            return pd.Series(0.0, index=self._instruments)
        mrc = (cov @ w) / port_vol
        result = pd.Series(mrc, index=self._instruments)
        logger.debug("Marginal risk contributions computed")
        return result

    def heat_map_data(self) -> pd.DataFrame:
        """Portfolio risk heat-map data.

        Returns a DataFrame with columns for weight, volatility,
        risk contribution, and percentage risk contribution per instrument.

        Returns
        -------
        pd.DataFrame
        """
        vols = self._returns.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)
        rc = self.risk_contribution()
        prc = self.percentage_risk_contribution()
        df = pd.DataFrame({
            "weight": self._weights,
            "annualized_vol": vols,
            "risk_contribution": rc,
            "pct_risk_contribution": prc,
        })
        logger.info("Heat map data generated for %d instruments", len(df))
        return df

    # -- concentration risk ---------------------------------------------------

    def herfindahl_index(self) -> float:
        """Herfindahl-Hirschman Index of portfolio weight concentration.

        HHI ranges from 1/N (perfectly diversified) to 1.0 (single position).

        Returns
        -------
        float
        """
        hhi = float((self._weights ** 2).sum())
        logger.debug("Herfindahl index = %.4f", hhi)
        return hhi

    def effective_n(self) -> float:
        """Effective number of independent bets (1 / HHI).

        Returns
        -------
        float
        """
        hhi = self.herfindahl_index()
        return 1.0 / hhi if hhi > 0 else 0.0

    def concentration_risk(self) -> Dict[str, float]:
        """Concentration risk metrics.

        Returns
        -------
        dict
        """
        hhi = self.herfindahl_index()
        return {
            "herfindahl_index": hhi,
            "effective_n": self.effective_n(),
            "max_weight": float(self._weights.max()),
            "max_weight_instrument": str(self._weights.idxmax()),
            "top3_weight": float(self._weights.nlargest(min(3, self._n)).sum()),
        }

    # -- correlation risk -----------------------------------------------------

    def correlation_risk(self) -> Dict[str, Any]:
        """Correlation risk summary.

        Returns
        -------
        dict
            Average, maximum, and minimum pairwise correlations.
        """
        corr = self.correlation_matrix
        # Extract upper triangle (excluding diagonal)
        mask = np.triu(np.ones(corr.shape, dtype=bool), k=1)
        upper = corr.values[mask]
        if len(upper) == 0:
            return {
                "avg_correlation": 0.0,
                "max_correlation": 0.0,
                "min_correlation": 0.0,
                "highly_correlated_pairs": [],
            }
        highly_corr: List[Dict[str, Any]] = []
        for i in range(self._n):
            for j in range(i + 1, self._n):
                c = corr.iloc[i, j]
                if abs(c) > 0.7:
                    highly_corr.append({
                        "pair": (self._instruments[i], self._instruments[j]),
                        "correlation": float(c),
                    })
        return {
            "avg_correlation": float(np.mean(upper)),
            "max_correlation": float(np.max(upper)),
            "min_correlation": float(np.min(upper)),
            "highly_correlated_pairs": highly_corr,
        }

    # -- tail risk ------------------------------------------------------------

    def tail_risk_metrics(self, confidence: float = 0.95) -> Dict[str, float]:
        """Portfolio tail risk metrics.

        Parameters
        ----------
        confidence : float
            Confidence level for VaR/CVaR.

        Returns
        -------
        dict
        """
        port_ret = self.portfolio_returns
        ra = RiskAnalytics(port_ret, risk_free_rate=self._risk_free_rate)
        var_result = ra.var_historical(confidence)
        cvar_val = ra.cvar(confidence)
        return {
            "var": var_result.var_value,
            "cvar": cvar_val,
            "skewness": float(port_ret.skew()),
            "kurtosis": float(port_ret.kurtosis()),
            "worst_day": float(port_ret.min()),
            "best_day": float(port_ret.max()),
            "negative_day_pct": float((port_ret < 0).mean()),
        }

    # -- risk decomposition by sector -----------------------------------------

    def risk_by_sector(
        self, sector_map: Dict[str, str]
    ) -> pd.DataFrame:
        """Decompose portfolio risk by sector / asset class.

        Parameters
        ----------
        sector_map : dict
            Mapping of instrument name to sector label.

        Returns
        -------
        pd.DataFrame
            Per-sector weight, volatility, and risk contribution.
        """
        prc = self.percentage_risk_contribution()
        rows = []
        sectors = set(sector_map.values())
        for sector in sorted(sectors):
            instruments = [k for k, v in sector_map.items() if v == sector and k in self._instruments]
            if not instruments:
                continue
            w = float(self._weights[instruments].sum())
            rc = float(prc[instruments].sum())
            # Sector volatility (sub-portfolio)
            sub_w = self._weights[instruments].values
            sub_cov = self.covariance_matrix.loc[instruments, instruments].values
            if sub_w.sum() > 0:
                norm_w = sub_w / sub_w.sum()
                sec_var = float(norm_w @ sub_cov @ norm_w)
                sec_vol = float(np.sqrt(max(sec_var, 0)))
            else:
                sec_vol = 0.0
            rows.append({
                "sector": sector,
                "weight": w,
                "annualized_vol": sec_vol,
                "pct_risk_contribution": rc,
                "instrument_count": len(instruments),
            })
        df = pd.DataFrame(rows).set_index("sector")
        logger.info("Risk decomposition by sector computed for %d sectors", len(df))
        return df

    # -- full summary ---------------------------------------------------------

    def risk_summary(self) -> Dict[str, Any]:
        """Complete portfolio risk summary.

        Returns
        -------
        dict
        """
        return {
            "portfolio_volatility": self.portfolio_volatility(),
            "portfolio_sharpe": self.portfolio_sharpe(),
            "concentration": self.concentration_risk(),
            "correlation": self.correlation_risk(),
            "tail_risk": self.tail_risk_metrics(),
            "heat_map": self.heat_map_data().to_dict(),
        }


# ---------------------------------------------------------------------------
# RiskLimitManager
# ---------------------------------------------------------------------------

class RiskLimitManager:
    """Real-time risk limit monitoring and alert generation.

    Tracks portfolio and position-level risk limits, computes current
    utilisation, and generates alerts when limits are approached or breached.

    Parameters
    ----------
    config : dict, optional
        Limit configuration.  Keys correspond to limit names, values are
        floats representing the limit thresholds.
    warning_threshold : float, optional
        Fraction of a limit at which a WARNING alert is raised (default 0.8).
    critical_threshold : float, optional
        Fraction of a limit at which a CRITICAL alert is raised (default 0.95).

    Examples
    --------
    >>> manager = RiskLimitManager({
    ...     "daily_loss_pct": 0.02,
    ...     "weekly_loss_pct": 0.05,
    ...     "max_drawdown_pct": 0.10,
    ...     "max_position_pct": 0.25,
    ...     "max_correlation": 0.85,
    ... })
    >>> alerts = manager.check_all(portfolio_state)
    """

    def __init__(
        self,
        config: Optional[Dict[str, float]] = None,
        warning_threshold: float = 0.80,
        critical_threshold: float = 0.95,
    ) -> None:
        self._limits: Dict[str, float] = config or {}
        self._warning_threshold = warning_threshold
        self._critical_threshold = critical_threshold
        self._alert_history: List[RiskAlert] = []
        self._daily_pnl_history: List[Tuple[datetime, float]] = []
        logger.info(
            "RiskLimitManager initialised with %d limits", len(self._limits)
        )

    # -- configuration -------------------------------------------------------

    def set_limit(self, name: str, value: float) -> None:
        """Set or update a single limit.

        Parameters
        ----------
        name : str
            Limit identifier.
        value : float
            Limit threshold value.
        """
        self._limits[name] = value
        logger.info("Limit '%s' set to %.6f", name, value)

    def remove_limit(self, name: str) -> None:
        """Remove a limit.

        Parameters
        ----------
        name : str
            Limit identifier.
        """
        self._limits.pop(name, None)
        logger.info("Limit '%s' removed", name)

    def get_limits(self) -> Dict[str, float]:
        """Return current limit configuration.

        Returns
        -------
        dict
        """
        return dict(self._limits)

    # -- PnL tracking --------------------------------------------------------

    def record_daily_pnl(self, pnl_pct: float, date: Optional[datetime] = None) -> None:
        """Record a daily PnL observation.

        Parameters
        ----------
        pnl_pct : float
            Daily profit/loss as a decimal (e.g. -0.015 = -1.5%).
        date : datetime, optional
            Date of the observation.
        """
        date = date or datetime.utcnow()
        self._daily_pnl_history.append((date, pnl_pct))
        logger.debug("Recorded daily PnL: %.4f on %s", pnl_pct, date.isoformat())

    # -- alert generation helpers --------------------------------------------

    def _make_alert(
        self, limit_name: str, limit_value: float, current_value: float
    ) -> Optional[RiskAlert]:
        """Create an alert if the current value approaches or breaches the limit.

        For loss-type limits the ``current_value`` is assumed to be positive
        when a loss is occurring (absolute value of drawdown / loss).

        Returns
        -------
        RiskAlert or None
        """
        if limit_value == 0:
            return None

        utilisation = abs(current_value) / abs(limit_value)

        if utilisation >= 1.0:
            severity = AlertSeverity.BREACH
        elif utilisation >= self._critical_threshold:
            severity = AlertSeverity.CRITICAL
        elif utilisation >= self._warning_threshold:
            severity = AlertSeverity.WARNING
        else:
            return None

        msg = (
            f"Limit '{limit_name}': {severity.value.upper()} - "
            f"current={current_value:.4f}, limit={limit_value:.4f}, "
            f"utilisation={utilisation:.1%}"
        )
        alert = RiskAlert(
            timestamp=datetime.utcnow(),
            severity=severity,
            limit_name=limit_name,
            limit_value=limit_value,
            current_value=current_value,
            utilisation_pct=utilisation * 100,
            message=msg,
        )
        self._alert_history.append(alert)
        logger.log(
            logging.CRITICAL if severity == AlertSeverity.BREACH else logging.WARNING,
            msg,
        )
        return alert

    # -- individual limit checks ---------------------------------------------

    def check_daily_loss(self, current_daily_loss_pct: float) -> Optional[RiskAlert]:
        """Check whether the daily loss limit has been approached or breached.

        Parameters
        ----------
        current_daily_loss_pct : float
            Today's loss as a positive decimal (e.g. 0.015 = 1.5% loss).

        Returns
        -------
        RiskAlert or None
        """
        limit = self._limits.get("daily_loss_pct")
        if limit is None:
            return None
        return self._make_alert("daily_loss_pct", limit, current_daily_loss_pct)

    def check_weekly_loss(self, current_weekly_loss_pct: float) -> Optional[RiskAlert]:
        """Check the weekly loss limit.

        Parameters
        ----------
        current_weekly_loss_pct : float
            This week's loss as a positive decimal.

        Returns
        -------
        RiskAlert or None
        """
        limit = self._limits.get("weekly_loss_pct")
        if limit is None:
            return None
        return self._make_alert("weekly_loss_pct", limit, current_weekly_loss_pct)

    def check_max_drawdown(self, current_drawdown_pct: float) -> Optional[RiskAlert]:
        """Check the maximum drawdown limit.

        Parameters
        ----------
        current_drawdown_pct : float
            Current drawdown as a positive decimal.

        Returns
        -------
        RiskAlert or None
        """
        limit = self._limits.get("max_drawdown_pct")
        if limit is None:
            return None
        return self._make_alert("max_drawdown_pct", limit, current_drawdown_pct)

    def check_position_size(
        self, position_weights: Dict[str, float]
    ) -> List[RiskAlert]:
        """Check position size limits.

        Parameters
        ----------
        position_weights : dict
            Mapping of instrument to portfolio weight (as a decimal).

        Returns
        -------
        list of RiskAlert
        """
        limit = self._limits.get("max_position_pct")
        if limit is None:
            return []
        alerts: List[RiskAlert] = []
        for instrument, weight in position_weights.items():
            alert = self._make_alert(
                f"max_position_pct[{instrument}]", limit, abs(weight)
            )
            if alert is not None:
                alerts.append(alert)
        return alerts

    def check_correlation(
        self, correlation_matrix: pd.DataFrame
    ) -> List[RiskAlert]:
        """Check for excessive pairwise correlations.

        Parameters
        ----------
        correlation_matrix : pd.DataFrame
            Correlation matrix of instrument returns.

        Returns
        -------
        list of RiskAlert
        """
        limit = self._limits.get("max_correlation")
        if limit is None:
            return []
        alerts: List[RiskAlert] = []
        instruments = correlation_matrix.columns.tolist()
        n = len(instruments)
        for i in range(n):
            for j in range(i + 1, n):
                corr_val = abs(correlation_matrix.iloc[i, j])
                alert = self._make_alert(
                    f"max_correlation[{instruments[i]}/{instruments[j]}]",
                    limit,
                    corr_val,
                )
                if alert is not None:
                    alerts.append(alert)
        return alerts

    # -- aggregate check ------------------------------------------------------

    def check_all(
        self,
        current_daily_loss_pct: float = 0.0,
        current_weekly_loss_pct: float = 0.0,
        current_drawdown_pct: float = 0.0,
        position_weights: Optional[Dict[str, float]] = None,
        correlation_matrix: Optional[pd.DataFrame] = None,
    ) -> List[RiskAlert]:
        """Run all configured limit checks and return any triggered alerts.

        Parameters
        ----------
        current_daily_loss_pct : float
            Today's loss as a positive fraction.
        current_weekly_loss_pct : float
            This week's loss as a positive fraction.
        current_drawdown_pct : float
            Current drawdown as a positive fraction.
        position_weights : dict, optional
            Instrument-level weights.
        correlation_matrix : pd.DataFrame, optional
            Current correlation matrix.

        Returns
        -------
        list of RiskAlert
            All alerts that were triggered.
        """
        alerts: List[RiskAlert] = []

        a = self.check_daily_loss(current_daily_loss_pct)
        if a:
            alerts.append(a)

        a = self.check_weekly_loss(current_weekly_loss_pct)
        if a:
            alerts.append(a)

        a = self.check_max_drawdown(current_drawdown_pct)
        if a:
            alerts.append(a)

        if position_weights:
            alerts.extend(self.check_position_size(position_weights))

        if correlation_matrix is not None:
            alerts.extend(self.check_correlation(correlation_matrix))

        logger.info(
            "Risk limit check complete: %d alert(s) triggered", len(alerts)
        )
        return alerts

    # -- alert history -------------------------------------------------------

    @property
    def alert_history(self) -> List[RiskAlert]:
        """Full history of generated alerts.

        Returns
        -------
        list of RiskAlert
        """
        return list(self._alert_history)

    def alerts_since(self, since: datetime) -> List[RiskAlert]:
        """Return alerts generated on or after a given timestamp.

        Parameters
        ----------
        since : datetime
            Start timestamp.

        Returns
        -------
        list of RiskAlert
        """
        return [a for a in self._alert_history if a.timestamp >= since]

    def alert_summary(self) -> Dict[str, int]:
        """Count of alerts by severity.

        Returns
        -------
        dict
        """
        counts: Dict[str, int] = {s.value: 0 for s in AlertSeverity}
        for a in self._alert_history:
            counts[a.severity.value] += 1
        return counts

    def clear_history(self) -> None:
        """Clear all alert history."""
        self._alert_history.clear()
        logger.info("Alert history cleared")

    # -- limit utilisation dashboard ------------------------------------------

    def utilisation_report(
        self,
        current_daily_loss_pct: float = 0.0,
        current_weekly_loss_pct: float = 0.0,
        current_drawdown_pct: float = 0.0,
        position_weights: Optional[Dict[str, float]] = None,
    ) -> pd.DataFrame:
        """Generate a limit utilisation report.

        Parameters
        ----------
        current_daily_loss_pct : float
            Today's loss.
        current_weekly_loss_pct : float
            This week's loss.
        current_drawdown_pct : float
            Current drawdown.
        position_weights : dict, optional
            Position weights for position-level utilisation.

        Returns
        -------
        pd.DataFrame
            Columns: limit_name, limit_value, current_value, utilisation_pct, status.
        """
        rows: List[Dict[str, Any]] = []

        value_map = {
            "daily_loss_pct": current_daily_loss_pct,
            "weekly_loss_pct": current_weekly_loss_pct,
            "max_drawdown_pct": current_drawdown_pct,
        }

        for name, limit_val in self._limits.items():
            if name in value_map:
                current = value_map[name]
                util = abs(current) / abs(limit_val) * 100 if limit_val != 0 else 0.0
                if util >= 100:
                    status = "BREACH"
                elif util >= self._critical_threshold * 100:
                    status = "CRITICAL"
                elif util >= self._warning_threshold * 100:
                    status = "WARNING"
                else:
                    status = "OK"
                rows.append({
                    "limit_name": name,
                    "limit_value": limit_val,
                    "current_value": current,
                    "utilisation_pct": util,
                    "status": status,
                })
            elif name == "max_position_pct" and position_weights:
                for inst, wt in position_weights.items():
                    util = abs(wt) / abs(limit_val) * 100 if limit_val != 0 else 0.0
                    if util >= 100:
                        status = "BREACH"
                    elif util >= self._critical_threshold * 100:
                        status = "CRITICAL"
                    elif util >= self._warning_threshold * 100:
                        status = "WARNING"
                    else:
                        status = "OK"
                    rows.append({
                        "limit_name": f"max_position_pct[{inst}]",
                        "limit_value": limit_val,
                        "current_value": abs(wt),
                        "utilisation_pct": util,
                        "status": status,
                    })

        df = pd.DataFrame(rows)
        logger.info("Utilisation report generated with %d rows", len(df))
        return df
