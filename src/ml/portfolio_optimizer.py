"""
Portfolio Optimization Engine

Comprehensive portfolio optimization module for commodity trading, implementing
Modern Portfolio Theory, risk parity, dynamic allocation, correlation analysis,
and advanced position sizing techniques.

Classes:
    - PortfolioOptimizer: Mean-variance optimization with Markowitz framework
    - RiskParityAllocator: Equal risk contribution allocation
    - DynamicAllocator: Volatility and regime-aware allocation
    - CorrelationAnalyzer: Rolling correlation and PCA factor analysis
    - PositionSizer: Kelly criterion and risk-based position sizing

Author: ScreenerIII
License: MIT
"""

from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import warnings

import numpy as np
import pandas as pd

# Optional scipy imports
try:
    from scipy.optimize import minimize, LinearConstraint
    from scipy.linalg import sqrtm
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    minimize = None
    LinearConstraint = None
    sqrtm = None

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes and enums
# ---------------------------------------------------------------------------

class OptimizationObjective(Enum):
    """Supported portfolio optimization objectives."""
    MIN_VARIANCE = "min_variance"
    MAX_SHARPE = "max_sharpe"
    RISK_PARITY = "risk_parity"
    MAX_RETURN = "max_return"
    TARGET_RISK = "target_risk"
    TARGET_RETURN = "target_return"


@dataclass
class PortfolioResult:
    """Result of a portfolio optimization run."""
    weights: Dict[str, float]
    expected_return: float
    volatility: float
    sharpe_ratio: float
    objective: str
    risk_contributions: Optional[Dict[str, float]] = None
    metadata: Dict = field(default_factory=dict)

    def summary(self) -> str:
        """Return a human-readable summary."""
        lines = [
            f"Objective: {self.objective}",
            f"Expected Return: {self.expected_return:.4%}",
            f"Volatility:      {self.volatility:.4%}",
            f"Sharpe Ratio:    {self.sharpe_ratio:.4f}",
            "Weights:",
        ]
        for asset, w in sorted(self.weights.items(), key=lambda x: -x[1]):
            lines.append(f"  {asset:>20s}: {w:>8.4%}")
        return "\n".join(lines)


@dataclass
class PortfolioConstraints:
    """Constraints for portfolio optimization."""
    min_weight: float = 0.0
    max_weight: float = 1.0
    sector_limits: Optional[Dict[str, float]] = None
    asset_sectors: Optional[Dict[str, str]] = None
    max_total_short: float = 0.0
    target_return: Optional[float] = None
    target_risk: Optional[float] = None


# ---------------------------------------------------------------------------
# PortfolioOptimizer
# ---------------------------------------------------------------------------

class PortfolioOptimizer:
    """Modern Portfolio Theory implementation.

    Provides mean-variance optimization (Markowitz), efficient frontier
    calculation, minimum variance and maximum Sharpe ratio portfolios,
    risk parity allocation, and Black-Litterman model support.

    Args:
        returns: DataFrame of asset returns (each column is an asset).
        risk_free_rate: Annualized risk-free rate (default 0.02).
        frequency: Number of periods per year for annualization (252 for daily).
    """

    def __init__(
        self,
        returns: pd.DataFrame,
        risk_free_rate: float = 0.02,
        frequency: int = 252,
    ) -> None:
        if not SCIPY_AVAILABLE:
            raise ImportError("scipy is required for PortfolioOptimizer")

        self.returns = returns.dropna()
        self.assets: List[str] = list(returns.columns)
        self.n_assets: int = len(self.assets)
        self.risk_free_rate = risk_free_rate
        self.frequency = frequency

        # Annualized statistics
        self.mean_returns: np.ndarray = self.returns.mean().values * frequency
        self.cov_matrix: np.ndarray = self.returns.cov().values * frequency

        logger.info(
            "PortfolioOptimizer initialized with %d assets, %d observations",
            self.n_assets, len(self.returns),
        )

    # ---- helpers -----------------------------------------------------------

    def _portfolio_return(self, weights: np.ndarray) -> float:
        return float(weights @ self.mean_returns)

    def _portfolio_volatility(self, weights: np.ndarray) -> float:
        return float(np.sqrt(weights @ self.cov_matrix @ weights))

    def _neg_sharpe(self, weights: np.ndarray) -> float:
        ret = self._portfolio_return(weights)
        vol = self._portfolio_volatility(weights)
        if vol < 1e-10:
            return 0.0
        return -(ret - self.risk_free_rate) / vol

    def _build_constraints(
        self, constraints: Optional[PortfolioConstraints] = None
    ) -> Tuple[List[dict], List[Tuple[float, float]]]:
        """Build scipy constraints and bounds from PortfolioConstraints."""
        cons = constraints or PortfolioConstraints()

        # Weight bounds per asset
        bounds = [(cons.min_weight, cons.max_weight)] * self.n_assets

        # Weights must sum to 1
        eq_constraints: List[dict] = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
        ]

        # Sector constraints
        if cons.sector_limits and cons.asset_sectors:
            for sector, limit in cons.sector_limits.items():
                indices = [
                    i for i, a in enumerate(self.assets)
                    if cons.asset_sectors.get(a) == sector
                ]
                if indices:
                    eq_constraints.append({
                        "type": "ineq",
                        "fun": lambda w, idx=indices, lim=limit: lim - sum(
                            w[j] for j in idx
                        ),
                    })

        # Target return constraint
        if cons.target_return is not None:
            eq_constraints.append({
                "type": "eq",
                "fun": lambda w, tr=cons.target_return: (
                    self._portfolio_return(w) - tr
                ),
            })

        return eq_constraints, bounds

    def _optimize(
        self,
        objective_fn,
        constraints: Optional[PortfolioConstraints] = None,
        objective_name: str = "custom",
    ) -> PortfolioResult:
        """Run the optimizer with given objective function."""
        cons_list, bounds = self._build_constraints(constraints)
        w0 = np.ones(self.n_assets) / self.n_assets

        result = minimize(
            objective_fn,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=cons_list,
            options={"maxiter": 1000, "ftol": 1e-12},
        )

        if not result.success:
            logger.warning("Optimization did not converge: %s", result.message)

        weights = result.x
        ret = self._portfolio_return(weights)
        vol = self._portfolio_volatility(weights)
        sharpe = (ret - self.risk_free_rate) / vol if vol > 1e-10 else 0.0

        # Risk contributions
        rc = self._risk_contributions(weights)
        rc_dict = {a: float(rc[i]) for i, a in enumerate(self.assets)}

        weight_dict = {a: float(weights[i]) for i, a in enumerate(self.assets)}

        logger.info(
            "Optimization [%s] complete: return=%.4f, vol=%.4f, sharpe=%.4f",
            objective_name, ret, vol, sharpe,
        )

        return PortfolioResult(
            weights=weight_dict,
            expected_return=ret,
            volatility=vol,
            sharpe_ratio=sharpe,
            objective=objective_name,
            risk_contributions=rc_dict,
        )

    def _risk_contributions(self, weights: np.ndarray) -> np.ndarray:
        """Calculate percentage risk contribution per asset."""
        port_vol = self._portfolio_volatility(weights)
        if port_vol < 1e-10:
            return np.zeros(self.n_assets)
        marginal = self.cov_matrix @ weights
        contrib = weights * marginal / port_vol
        total = np.sum(contrib)
        if abs(total) < 1e-10:
            return np.zeros(self.n_assets)
        return contrib / total

    # ---- public methods ----------------------------------------------------

    def minimum_variance(
        self, constraints: Optional[PortfolioConstraints] = None
    ) -> PortfolioResult:
        """Find the minimum variance portfolio.

        Args:
            constraints: Optional weight / sector constraints.

        Returns:
            PortfolioResult with optimal weights.
        """
        logger.info("Computing minimum variance portfolio")
        return self._optimize(
            lambda w: self._portfolio_volatility(w),
            constraints,
            objective_name=OptimizationObjective.MIN_VARIANCE.value,
        )

    def maximum_sharpe(
        self, constraints: Optional[PortfolioConstraints] = None
    ) -> PortfolioResult:
        """Find the maximum Sharpe ratio (tangency) portfolio.

        Args:
            constraints: Optional weight / sector constraints.

        Returns:
            PortfolioResult with optimal weights.
        """
        logger.info("Computing maximum Sharpe ratio portfolio")
        return self._optimize(
            self._neg_sharpe,
            constraints,
            objective_name=OptimizationObjective.MAX_SHARPE.value,
        )

    def target_return(
        self,
        target: float,
        constraints: Optional[PortfolioConstraints] = None,
    ) -> PortfolioResult:
        """Find the minimum-variance portfolio for a target return.

        Args:
            target: Desired annualized return.
            constraints: Optional additional constraints.

        Returns:
            PortfolioResult with optimal weights.
        """
        logger.info("Computing target return portfolio: %.4f", target)
        cons = constraints or PortfolioConstraints()
        cons.target_return = target
        return self._optimize(
            lambda w: self._portfolio_volatility(w),
            cons,
            objective_name=OptimizationObjective.TARGET_RETURN.value,
        )

    def target_risk(
        self,
        target_vol: float,
        constraints: Optional[PortfolioConstraints] = None,
    ) -> PortfolioResult:
        """Find the maximum-return portfolio for a target volatility.

        Args:
            target_vol: Desired annualized volatility.
            constraints: Optional additional constraints.

        Returns:
            PortfolioResult with optimal weights.
        """
        logger.info("Computing target risk portfolio: vol=%.4f", target_vol)
        cons = constraints or PortfolioConstraints()
        cons.target_risk = target_vol

        cons_list, bounds = self._build_constraints(cons)
        cons_list.append({
            "type": "eq",
            "fun": lambda w, tv=target_vol: self._portfolio_volatility(w) - tv,
        })

        w0 = np.ones(self.n_assets) / self.n_assets
        result = minimize(
            lambda w: -self._portfolio_return(w),
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=cons_list,
            options={"maxiter": 1000, "ftol": 1e-12},
        )

        weights = result.x
        ret = self._portfolio_return(weights)
        vol = self._portfolio_volatility(weights)
        sharpe = (ret - self.risk_free_rate) / vol if vol > 1e-10 else 0.0
        rc = self._risk_contributions(weights)

        return PortfolioResult(
            weights={a: float(weights[i]) for i, a in enumerate(self.assets)},
            expected_return=ret,
            volatility=vol,
            sharpe_ratio=sharpe,
            objective=OptimizationObjective.TARGET_RISK.value,
            risk_contributions={a: float(rc[i]) for i, a in enumerate(self.assets)},
        )

    def efficient_frontier(
        self,
        n_points: int = 50,
        constraints: Optional[PortfolioConstraints] = None,
    ) -> pd.DataFrame:
        """Calculate the efficient frontier.

        Args:
            n_points: Number of points along the frontier.
            constraints: Optional weight / sector constraints.

        Returns:
            DataFrame with columns [return, volatility, sharpe, weights].
        """
        logger.info("Computing efficient frontier with %d points", n_points)

        min_var = self.minimum_variance(constraints)
        max_ret_cons = constraints or PortfolioConstraints()
        cons_list, bounds = self._build_constraints(max_ret_cons)
        w0 = np.ones(self.n_assets) / self.n_assets
        max_ret_result = minimize(
            lambda w: -self._portfolio_return(w),
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=cons_list,
        )
        max_ret = self._portfolio_return(max_ret_result.x)

        target_returns = np.linspace(min_var.expected_return, max_ret, n_points)
        frontier: List[Dict] = []

        for tr in target_returns:
            try:
                result = self.target_return(tr, constraints)
                frontier.append({
                    "return": result.expected_return,
                    "volatility": result.volatility,
                    "sharpe": result.sharpe_ratio,
                    "weights": result.weights,
                })
            except Exception as exc:
                logger.debug("Frontier point failed at return=%.4f: %s", tr, exc)

        logger.info("Efficient frontier computed: %d valid points", len(frontier))
        return pd.DataFrame(frontier)

    def risk_parity(
        self, constraints: Optional[PortfolioConstraints] = None
    ) -> PortfolioResult:
        """Find the risk parity (equal risk contribution) portfolio.

        Each asset contributes equally to total portfolio risk.

        Args:
            constraints: Optional weight constraints.

        Returns:
            PortfolioResult with risk-parity weights.
        """
        logger.info("Computing risk parity portfolio")
        target_rc = 1.0 / self.n_assets

        def objective(weights: np.ndarray) -> float:
            rc = self._risk_contributions(weights)
            return float(np.sum((rc - target_rc) ** 2))

        return self._optimize(
            objective,
            constraints,
            objective_name=OptimizationObjective.RISK_PARITY.value,
        )

    def black_litterman(
        self,
        views: Dict[str, float],
        view_confidences: Optional[Dict[str, float]] = None,
        tau: float = 0.05,
        market_caps: Optional[Dict[str, float]] = None,
        constraints: Optional[PortfolioConstraints] = None,
    ) -> PortfolioResult:
        """Black-Litterman model for views-based allocation.

        Blends equilibrium returns with investor views weighted by confidence.

        Args:
            views: Dict mapping asset name to expected excess return view.
            view_confidences: Confidence in each view (0-1). Defaults to 0.5.
            tau: Uncertainty scalar on the covariance matrix. Default 0.05.
            market_caps: Market capitalizations for equilibrium weights.
                         If None, equal weights are assumed.
            constraints: Optional weight constraints for final optimization.

        Returns:
            PortfolioResult with Black-Litterman adjusted weights.
        """
        logger.info("Computing Black-Litterman allocation with %d views", len(views))

        # Equilibrium weights
        if market_caps:
            total_cap = sum(market_caps.values())
            eq_weights = np.array([
                market_caps.get(a, total_cap / self.n_assets) / total_cap
                for a in self.assets
            ])
        else:
            eq_weights = np.ones(self.n_assets) / self.n_assets

        # Implied equilibrium excess returns: pi = delta * Sigma * w_eq
        delta = (self.mean_returns @ eq_weights - self.risk_free_rate) / (
            eq_weights @ self.cov_matrix @ eq_weights
        )
        if abs(delta) < 1e-10:
            delta = 2.5  # market risk aversion default
        pi = delta * self.cov_matrix @ eq_weights

        # Build view matrices
        view_assets = [a for a in views if a in self.assets]
        k = len(view_assets)
        if k == 0:
            logger.warning("No valid views provided; returning equilibrium portfolio")
            self.mean_returns = pi
            return self.maximum_sharpe(constraints)

        P = np.zeros((k, self.n_assets))
        q = np.zeros(k)
        for i, asset in enumerate(view_assets):
            idx = self.assets.index(asset)
            P[i, idx] = 1.0
            q[i] = views[asset]

        # Confidence matrix (Omega)
        confs = view_confidences or {}
        omega_diag = []
        for asset in view_assets:
            c = confs.get(asset, 0.5)
            c = max(min(c, 0.999), 0.001)
            # Scale uncertainty inversely with confidence
            omega_diag.append((1.0 - c) / c * (P @ (tau * self.cov_matrix) @ P.T).diagonal().mean())
        Omega = np.diag(omega_diag)

        # Posterior expected returns
        tau_sigma = tau * self.cov_matrix
        inv_tau_sigma = np.linalg.inv(tau_sigma)
        inv_omega = np.linalg.inv(Omega)

        posterior_cov = np.linalg.inv(inv_tau_sigma + P.T @ inv_omega @ P)
        posterior_mean = posterior_cov @ (inv_tau_sigma @ pi + P.T @ inv_omega @ q)

        # Save the BL-adjusted returns and optimize
        original_means = self.mean_returns.copy()
        self.mean_returns = posterior_mean

        try:
            result = self.maximum_sharpe(constraints)
            result.objective = "black_litterman"
            result.metadata["views"] = views
            result.metadata["tau"] = tau
        finally:
            self.mean_returns = original_means

        logger.info("Black-Litterman optimization complete")
        return result


# ---------------------------------------------------------------------------
# RiskParityAllocator
# ---------------------------------------------------------------------------

class RiskParityAllocator:
    """Equal risk contribution portfolio allocator.

    Ensures each asset contributes equally to total portfolio risk,
    providing inherent diversification regardless of expected returns.

    Args:
        returns: DataFrame of asset returns.
        risk_budgets: Optional per-asset risk budget (must sum to 1).
        frequency: Periods per year for annualization.
    """

    def __init__(
        self,
        returns: pd.DataFrame,
        risk_budgets: Optional[Dict[str, float]] = None,
        frequency: int = 252,
    ) -> None:
        if not SCIPY_AVAILABLE:
            raise ImportError("scipy is required for RiskParityAllocator")

        self.returns = returns.dropna()
        self.assets: List[str] = list(returns.columns)
        self.n_assets = len(self.assets)
        self.frequency = frequency
        self.cov_matrix: np.ndarray = self.returns.cov().values * frequency

        if risk_budgets:
            self.risk_budgets = np.array([
                risk_budgets.get(a, 1.0 / self.n_assets) for a in self.assets
            ])
            self.risk_budgets /= self.risk_budgets.sum()
        else:
            self.risk_budgets = np.ones(self.n_assets) / self.n_assets

        logger.info(
            "RiskParityAllocator initialized with %d assets", self.n_assets
        )

    def _risk_contributions(self, weights: np.ndarray) -> np.ndarray:
        """Compute fractional risk contributions."""
        port_vol = np.sqrt(weights @ self.cov_matrix @ weights)
        if port_vol < 1e-10:
            return np.zeros(self.n_assets)
        marginal = self.cov_matrix @ weights
        contrib = weights * marginal / port_vol
        return contrib / np.sum(contrib)

    def allocate(self) -> PortfolioResult:
        """Compute risk parity weights.

        Returns:
            PortfolioResult with weights that equalize risk contributions
            according to the specified risk budgets.
        """
        logger.info("Computing risk parity allocation")

        def objective(log_w: np.ndarray) -> float:
            w = np.exp(log_w)
            w /= w.sum()
            rc = self._risk_contributions(w)
            return float(np.sum((rc - self.risk_budgets) ** 2))

        # Optimize in log-space to ensure positivity
        x0 = np.zeros(self.n_assets)
        result = minimize(objective, x0, method="BFGS", options={"maxiter": 1000})

        weights = np.exp(result.x)
        weights /= weights.sum()

        ann_returns = self.returns.mean().values * self.frequency
        ret = float(weights @ ann_returns)
        vol = float(np.sqrt(weights @ self.cov_matrix @ weights))
        rc = self._risk_contributions(weights)

        logger.info("Risk parity allocation complete: vol=%.4f", vol)

        return PortfolioResult(
            weights={a: float(weights[i]) for i, a in enumerate(self.assets)},
            expected_return=ret,
            volatility=vol,
            sharpe_ratio=ret / vol if vol > 1e-10 else 0.0,
            objective="risk_parity",
            risk_contributions={a: float(rc[i]) for i, a in enumerate(self.assets)},
        )

    def inverse_volatility(self) -> PortfolioResult:
        """Compute inverse volatility weighted portfolio.

        Allocates weights inversely proportional to each asset's volatility,
        a simpler approximation of risk parity.

        Returns:
            PortfolioResult with inverse-volatility weights.
        """
        logger.info("Computing inverse volatility weights")
        vols = np.sqrt(np.diag(self.cov_matrix))
        inv_vol = 1.0 / np.maximum(vols, 1e-10)
        weights = inv_vol / inv_vol.sum()

        ann_returns = self.returns.mean().values * self.frequency
        ret = float(weights @ ann_returns)
        vol = float(np.sqrt(weights @ self.cov_matrix @ weights))
        rc = self._risk_contributions(weights)

        return PortfolioResult(
            weights={a: float(weights[i]) for i, a in enumerate(self.assets)},
            expected_return=ret,
            volatility=vol,
            sharpe_ratio=ret / vol if vol > 1e-10 else 0.0,
            objective="inverse_volatility",
            risk_contributions={a: float(rc[i]) for i, a in enumerate(self.assets)},
        )

    def risk_contribution_analysis(
        self, weights: Optional[Dict[str, float]] = None
    ) -> pd.DataFrame:
        """Analyze risk contributions for given or equal weights.

        Args:
            weights: Portfolio weights. If None, uses equal weights.

        Returns:
            DataFrame with columns [asset, weight, risk_contribution,
            marginal_risk, volatility].
        """
        if weights:
            w = np.array([weights.get(a, 0.0) for a in self.assets])
        else:
            w = np.ones(self.n_assets) / self.n_assets

        port_vol = np.sqrt(w @ self.cov_matrix @ w)
        marginal = self.cov_matrix @ w / port_vol if port_vol > 1e-10 else np.zeros(self.n_assets)
        contrib = w * marginal
        pct_contrib = contrib / port_vol if port_vol > 1e-10 else np.zeros(self.n_assets)
        asset_vols = np.sqrt(np.diag(self.cov_matrix))

        return pd.DataFrame({
            "asset": self.assets,
            "weight": w,
            "risk_contribution": pct_contrib,
            "marginal_risk": marginal,
            "volatility": asset_vols,
        })

    def rebalance_needed(
        self,
        current_weights: Dict[str, float],
        threshold: float = 0.05,
    ) -> Tuple[bool, Dict[str, float]]:
        """Check if rebalancing is needed based on risk contribution drift.

        Args:
            current_weights: Current portfolio weights.
            threshold: Maximum allowed deviation from target risk budget.

        Returns:
            Tuple of (rebalance_needed, deviations_dict).
        """
        w = np.array([current_weights.get(a, 0.0) for a in self.assets])
        rc = self._risk_contributions(w)
        deviations = rc - self.risk_budgets

        dev_dict = {a: float(deviations[i]) for i, a in enumerate(self.assets)}
        needs_rebalance = bool(np.max(np.abs(deviations)) > threshold)

        if needs_rebalance:
            logger.info(
                "Rebalance triggered: max deviation=%.4f (threshold=%.4f)",
                np.max(np.abs(deviations)), threshold,
            )

        return needs_rebalance, dev_dict


# ---------------------------------------------------------------------------
# DynamicAllocator
# ---------------------------------------------------------------------------

class DynamicAllocator:
    """Volatility-based and regime-aware dynamic allocation engine.

    Adjusts portfolio weights based on realized volatility, momentum signals,
    and estimated market regimes.

    Args:
        returns: DataFrame of asset returns.
        target_vol: Annualized target portfolio volatility (e.g., 0.10).
        frequency: Periods per year.
        lookback: Lookback window for volatility estimation.
    """

    def __init__(
        self,
        returns: pd.DataFrame,
        target_vol: float = 0.10,
        frequency: int = 252,
        lookback: int = 60,
    ) -> None:
        self.returns = returns.dropna()
        self.assets: List[str] = list(returns.columns)
        self.n_assets = len(self.assets)
        self.target_vol = target_vol
        self.frequency = frequency
        self.lookback = lookback

        logger.info(
            "DynamicAllocator initialized: target_vol=%.2f%%, lookback=%d",
            target_vol * 100, lookback,
        )

    def volatility_targeting(
        self,
        base_weights: Optional[Dict[str, float]] = None,
        max_leverage: float = 2.0,
        min_leverage: float = 0.0,
    ) -> Dict[str, float]:
        """Scale portfolio weights to target a specific volatility level.

        Uses recent realized volatility to scale position sizes up or down
        so that the portfolio's expected volatility matches the target.

        Args:
            base_weights: Unscaled portfolio weights. Defaults to equal weight.
            max_leverage: Maximum portfolio leverage allowed.
            min_leverage: Minimum leverage (0 = fully in cash).

        Returns:
            Dict of volatility-scaled asset weights.
        """
        logger.info("Computing volatility-targeted allocation")

        if base_weights:
            w = np.array([base_weights.get(a, 0.0) for a in self.assets])
        else:
            w = np.ones(self.n_assets) / self.n_assets

        # Realized vol from recent window
        recent = self.returns.iloc[-self.lookback:]
        cov = recent.cov().values * self.frequency
        realized_vol = float(np.sqrt(w @ cov @ w))

        if realized_vol < 1e-10:
            logger.warning("Realized volatility near zero; returning base weights")
            return {a: float(w[i]) for i, a in enumerate(self.assets)}

        # Scale factor
        scale = self.target_vol / realized_vol
        scale = np.clip(scale, min_leverage, max_leverage)

        scaled = w * scale
        result = {a: float(scaled[i]) for i, a in enumerate(self.assets)}

        logger.info(
            "Vol targeting: realized=%.4f, target=%.4f, scale=%.2f",
            realized_vol, self.target_vol, scale,
        )
        return result

    def momentum_allocation(
        self,
        momentum_window: int = 120,
        top_n: Optional[int] = None,
        weight_by_momentum: bool = True,
    ) -> Dict[str, float]:
        """Allocate to assets based on momentum (trailing return).

        Ranks assets by their trailing return and allocates to the top
        performers, optionally weighting by momentum magnitude.

        Args:
            momentum_window: Lookback period for momentum calculation.
            top_n: Number of top assets to hold. Defaults to n_assets // 2.
            weight_by_momentum: If True, weight proportional to momentum.
                                If False, equal weight among selected.

        Returns:
            Dict of momentum-based asset weights.
        """
        logger.info("Computing momentum-based allocation (window=%d)", momentum_window)

        if top_n is None:
            top_n = max(1, self.n_assets // 2)

        # Trailing cumulative return as momentum score
        window_data = self.returns.iloc[-momentum_window:]
        cum_returns = (1 + window_data).prod() - 1
        rankings = cum_returns.sort_values(ascending=False)

        selected = rankings.head(top_n)

        if weight_by_momentum:
            # Only weight by positive momentum
            positive = selected.clip(lower=0)
            total = positive.sum()
            if total < 1e-10:
                # Fall back to equal weight
                weights = {a: 1.0 / top_n for a in selected.index}
            else:
                weights = {a: float(v / total) for a, v in positive.items()}
        else:
            weights = {a: 1.0 / top_n for a in selected.index}

        # Zero out non-selected assets
        full_weights = {a: weights.get(a, 0.0) for a in self.assets}

        logger.info("Momentum allocation: selected %d assets", len(selected))
        return full_weights

    def mean_reversion_signals(
        self,
        z_window: int = 20,
        z_threshold: float = 1.5,
    ) -> Dict[str, float]:
        """Generate mean-reversion allocation signals.

        Uses z-score of recent returns relative to a rolling mean. Assets
        trading below their mean are overweighted, and above are underweighted.

        Args:
            z_window: Window for z-score calculation.
            z_threshold: Z-score threshold for signal generation.

        Returns:
            Dict of asset weights adjusted for mean reversion.
        """
        logger.info("Computing mean reversion signals (window=%d)", z_window)

        prices = (1 + self.returns).cumprod()
        rolling_mean = prices.rolling(z_window).mean()
        rolling_std = prices.rolling(z_window).std()

        latest_price = prices.iloc[-1]
        latest_mean = rolling_mean.iloc[-1]
        latest_std = rolling_std.iloc[-1]

        z_scores = (latest_price - latest_mean) / latest_std.replace(0, np.nan)
        z_scores = z_scores.fillna(0)

        # Invert z-scores: negative z means buy signal (below mean)
        raw_signal = -z_scores.clip(lower=-z_threshold, upper=z_threshold)
        # Shift to positive and normalize
        shifted = raw_signal - raw_signal.min() + 0.01
        weights = shifted / shifted.sum()

        result = {a: float(weights[a]) for a in self.assets}
        logger.info("Mean reversion signals computed")
        return result

    def regime_aware_allocation(
        self,
        vol_threshold_high: float = 0.25,
        vol_threshold_low: float = 0.12,
        trend_window: int = 60,
    ) -> Tuple[str, Dict[str, float]]:
        """Regime-aware allocation based on volatility and trend regimes.

        Detects three regimes:
        - low_vol_trending: Favour momentum / concentrated positions
        - high_vol_trending: Reduce exposure, favour momentum with lower weight
        - high_vol_mean_revert: Favour mean reversion, diversified

        Args:
            vol_threshold_high: Threshold for high-vol regime.
            vol_threshold_low: Threshold for low-vol regime.
            trend_window: Window for trend detection.

        Returns:
            Tuple of (regime_name, weights_dict).
        """
        logger.info("Computing regime-aware allocation")

        # Portfolio equal-weight volatility
        recent = self.returns.iloc[-self.lookback:]
        eq_w = np.ones(self.n_assets) / self.n_assets
        cov = recent.cov().values * self.frequency
        realized_vol = float(np.sqrt(eq_w @ cov @ eq_w))

        # Trend strength: average directional movement
        cum_ret = (1 + self.returns.iloc[-trend_window:]).prod() - 1
        avg_abs_return = cum_ret.abs().mean()
        avg_return = cum_ret.mean()
        is_trending = abs(avg_return) > 0.3 * avg_abs_return

        # Classify regime
        if realized_vol < vol_threshold_low:
            regime = "low_vol_trending"
        elif realized_vol > vol_threshold_high and is_trending:
            regime = "high_vol_trending"
        elif realized_vol > vol_threshold_high:
            regime = "high_vol_mean_revert"
        else:
            regime = "normal"

        logger.info(
            "Detected regime: %s (vol=%.4f, trending=%s)",
            regime, realized_vol, is_trending,
        )

        # Allocate based on regime
        if regime == "low_vol_trending":
            weights = self.momentum_allocation(top_n=max(1, self.n_assets // 3))
        elif regime == "high_vol_trending":
            mom = self.momentum_allocation()
            vol_target = self.volatility_targeting(
                base_weights=mom, max_leverage=1.0
            )
            weights = vol_target
        elif regime == "high_vol_mean_revert":
            weights = self.mean_reversion_signals()
        else:
            # Normal regime: blend momentum and inverse vol
            mom = self.momentum_allocation(weight_by_momentum=False)
            weights = {a: float(mom.get(a, 0.0)) for a in self.assets}

        return regime, weights


# ---------------------------------------------------------------------------
# CorrelationAnalyzer
# ---------------------------------------------------------------------------

class CorrelationAnalyzer:
    """Asset correlation analysis and factor decomposition.

    Provides rolling correlation matrices, diversification metrics,
    correlation breakdown detection, and PCA-based factor analysis.

    Args:
        returns: DataFrame of asset returns.
        frequency: Periods per year for annualization.
    """

    def __init__(
        self,
        returns: pd.DataFrame,
        frequency: int = 252,
    ) -> None:
        self.returns = returns.dropna()
        self.assets: List[str] = list(returns.columns)
        self.n_assets = len(self.assets)
        self.frequency = frequency

        logger.info(
            "CorrelationAnalyzer initialized with %d assets, %d observations",
            self.n_assets, len(self.returns),
        )

    def correlation_matrix(
        self, window: Optional[int] = None
    ) -> pd.DataFrame:
        """Compute the correlation matrix over a given window.

        Args:
            window: Lookback window. If None, uses all data.

        Returns:
            Correlation matrix as a DataFrame.
        """
        data = self.returns.iloc[-window:] if window else self.returns
        return data.corr()

    def rolling_correlations(
        self,
        window: int = 60,
        pairs: Optional[List[Tuple[str, str]]] = None,
    ) -> pd.DataFrame:
        """Compute rolling pairwise correlations.

        Args:
            window: Rolling window size.
            pairs: Specific asset pairs. If None, computes all unique pairs.

        Returns:
            DataFrame with a column per pair, indexed by date.
        """
        logger.info("Computing rolling correlations (window=%d)", window)

        if pairs is None:
            pairs = [
                (self.assets[i], self.assets[j])
                for i in range(self.n_assets)
                for j in range(i + 1, self.n_assets)
            ]

        result = pd.DataFrame(index=self.returns.index)
        for a1, a2 in pairs:
            if a1 not in self.returns.columns or a2 not in self.returns.columns:
                logger.warning("Skipping pair (%s, %s): asset not found", a1, a2)
                continue
            col_name = f"{a1}__{a2}"
            result[col_name] = (
                self.returns[a1]
                .rolling(window)
                .corr(self.returns[a2])
            )

        return result.dropna()

    def heatmap_data(
        self, window: Optional[int] = None
    ) -> Dict[str, Union[pd.DataFrame, List[str]]]:
        """Generate data suitable for a correlation heatmap visualization.

        Args:
            window: Lookback window for correlation calculation.

        Returns:
            Dict with 'matrix', 'labels', and 'values' keys.
        """
        corr = self.correlation_matrix(window)
        return {
            "matrix": corr,
            "labels": list(corr.columns),
            "values": corr.values.tolist(),
        }

    def diversification_ratio(
        self, weights: Optional[Dict[str, float]] = None
    ) -> float:
        """Calculate the portfolio diversification ratio.

        DR = weighted average of individual volatilities / portfolio volatility.
        A DR > 1 indicates diversification benefit.

        Args:
            weights: Portfolio weights. Defaults to equal weight.

        Returns:
            Diversification ratio (float >= 1.0 for long-only portfolios).
        """
        if weights:
            w = np.array([weights.get(a, 0.0) for a in self.assets])
        else:
            w = np.ones(self.n_assets) / self.n_assets

        cov = self.returns.cov().values * self.frequency
        vols = np.sqrt(np.diag(cov))

        weighted_avg_vol = float(w @ vols)
        port_vol = float(np.sqrt(w @ cov @ w))

        if port_vol < 1e-10:
            return 1.0

        dr = weighted_avg_vol / port_vol
        logger.info("Diversification ratio: %.4f", dr)
        return dr

    def correlation_breakdown_detection(
        self,
        window: int = 60,
        baseline_window: int = 252,
        threshold: float = 0.3,
    ) -> pd.DataFrame:
        """Detect periods where correlations deviate significantly from baseline.

        Compares recent rolling correlation to a longer baseline period.
        Breakdowns often occur during market stress.

        Args:
            window: Short-term rolling window.
            baseline_window: Longer-term baseline window.
            threshold: Minimum absolute change to flag as breakdown.

        Returns:
            DataFrame with pair, baseline_corr, recent_corr, change columns.
        """
        logger.info("Running correlation breakdown detection")

        if len(self.returns) < baseline_window:
            logger.warning("Insufficient data for baseline (need %d)", baseline_window)
            return pd.DataFrame()

        baseline_corr = self.returns.iloc[-baseline_window:].corr()
        recent_corr = self.returns.iloc[-window:].corr()

        breakdowns = []
        for i in range(self.n_assets):
            for j in range(i + 1, self.n_assets):
                a1, a2 = self.assets[i], self.assets[j]
                bc = baseline_corr.iloc[i, j]
                rc = recent_corr.iloc[i, j]
                change = rc - bc
                if abs(change) >= threshold:
                    breakdowns.append({
                        "pair": f"{a1}__{a2}",
                        "baseline_corr": bc,
                        "recent_corr": rc,
                        "change": change,
                        "abs_change": abs(change),
                    })

        df = pd.DataFrame(breakdowns)
        if not df.empty:
            df = df.sort_values("abs_change", ascending=False).reset_index(drop=True)
            logger.info("Detected %d correlation breakdowns", len(df))
        else:
            logger.info("No correlation breakdowns detected")
        return df

    def pca_analysis(
        self, n_components: Optional[int] = None
    ) -> Dict[str, Union[np.ndarray, pd.DataFrame, float]]:
        """Perform PCA factor analysis on asset returns.

        Decomposes the return covariance into principal components to
        identify the dominant risk factors driving portfolio returns.

        Args:
            n_components: Number of components to retain. Defaults to all.

        Returns:
            Dict with keys:
                - eigenvalues: Array of eigenvalues (variance explained).
                - eigenvectors: Array of eigenvectors (loadings).
                - explained_variance_ratio: Fraction of variance per component.
                - cumulative_variance: Cumulative explained variance.
                - loadings: DataFrame of factor loadings per asset.
        """
        logger.info("Performing PCA factor analysis")

        cov = self.returns.cov().values
        eigenvalues, eigenvectors = np.linalg.eigh(cov)

        # Sort descending
        idx = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]

        total_var = eigenvalues.sum()
        explained_ratio = eigenvalues / total_var if total_var > 0 else eigenvalues
        cumulative = np.cumsum(explained_ratio)

        n = n_components or self.n_assets
        n = min(n, self.n_assets)

        loadings = pd.DataFrame(
            eigenvectors[:, :n],
            index=self.assets,
            columns=[f"PC{i+1}" for i in range(n)],
        )

        logger.info(
            "PCA: top %d components explain %.2f%% of variance",
            n, cumulative[n - 1] * 100,
        )

        return {
            "eigenvalues": eigenvalues[:n],
            "eigenvectors": eigenvectors[:, :n],
            "explained_variance_ratio": explained_ratio[:n],
            "cumulative_variance": cumulative[:n],
            "loadings": loadings,
        }


# ---------------------------------------------------------------------------
# PositionSizer
# ---------------------------------------------------------------------------

class PositionSizer:
    """Advanced position sizing algorithms.

    Provides Kelly criterion, fractional Kelly, fixed fractional,
    optimal-f, ATR-based, and volatility-adjusted sizing methods.

    Args:
        account_value: Total account equity.
        risk_per_trade: Maximum fraction of account to risk per trade (default 2%).
        frequency: Periods per year for annualization.
    """

    def __init__(
        self,
        account_value: float,
        risk_per_trade: float = 0.02,
        frequency: int = 252,
    ) -> None:
        self.account_value = account_value
        self.risk_per_trade = risk_per_trade
        self.frequency = frequency

        logger.info(
            "PositionSizer initialized: account=%.2f, risk_per_trade=%.2f%%",
            account_value, risk_per_trade * 100,
        )

    def kelly_criterion(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
    ) -> Dict[str, float]:
        """Full Kelly criterion position sizing.

        Calculates the theoretically optimal fraction of capital to wager
        based on win rate and win/loss ratio.

        Args:
            win_rate: Probability of a winning trade (0-1).
            avg_win: Average winning trade return (positive).
            avg_loss: Average losing trade return (positive value, applied as loss).

        Returns:
            Dict with kelly_fraction, position_size, and dollar_amount.
        """
        if avg_loss <= 0:
            logger.warning("avg_loss must be positive; returning zero size")
            return {"kelly_fraction": 0.0, "position_size": 0.0, "dollar_amount": 0.0}

        win_loss_ratio = avg_win / avg_loss
        kelly_f = win_rate - (1 - win_rate) / win_loss_ratio

        kelly_f = max(kelly_f, 0.0)

        dollar_amount = self.account_value * kelly_f

        logger.info(
            "Kelly criterion: f=%.4f, position=$%.2f", kelly_f, dollar_amount
        )

        return {
            "kelly_fraction": kelly_f,
            "position_size": kelly_f,
            "dollar_amount": dollar_amount,
        }

    def fractional_kelly(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        fraction: float = 0.5,
    ) -> Dict[str, float]:
        """Fractional Kelly position sizing.

        Uses a fraction of the full Kelly size to reduce variance at the
        cost of slightly reduced long-term growth rate.

        Args:
            win_rate: Probability of a winning trade (0-1).
            avg_win: Average winning trade return.
            avg_loss: Average losing trade return (positive).
            fraction: Fraction of Kelly to use (default 0.5 = half Kelly).

        Returns:
            Dict with kelly_fraction, fractional_kelly, position_size, dollar_amount.
        """
        full_kelly = self.kelly_criterion(win_rate, avg_win, avg_loss)
        frac_kelly = full_kelly["kelly_fraction"] * fraction
        dollar_amount = self.account_value * frac_kelly

        logger.info(
            "Fractional Kelly (%.0f%%): f=%.4f, position=$%.2f",
            fraction * 100, frac_kelly, dollar_amount,
        )

        return {
            "kelly_fraction": full_kelly["kelly_fraction"],
            "fractional_kelly": frac_kelly,
            "position_size": frac_kelly,
            "dollar_amount": dollar_amount,
        }

    def fixed_fractional(
        self,
        entry_price: float,
        stop_loss_price: float,
    ) -> Dict[str, float]:
        """Fixed fractional position sizing.

        Calculates position size so that the dollar risk per trade
        equals a fixed fraction of account equity.

        Args:
            entry_price: Trade entry price.
            stop_loss_price: Stop loss price.

        Returns:
            Dict with risk_amount, position_size, shares, and dollar_amount.
        """
        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share < 1e-10:
            logger.warning("Entry and stop are the same; returning zero size")
            return {
                "risk_amount": 0.0,
                "position_size": 0.0,
                "shares": 0.0,
                "dollar_amount": 0.0,
            }

        risk_amount = self.account_value * self.risk_per_trade
        shares = risk_amount / risk_per_share
        dollar_amount = shares * entry_price

        logger.info(
            "Fixed fractional: risk=$%.2f, shares=%.2f, position=$%.2f",
            risk_amount, shares, dollar_amount,
        )

        return {
            "risk_amount": risk_amount,
            "position_size": dollar_amount / self.account_value,
            "shares": shares,
            "dollar_amount": dollar_amount,
        }

    def optimal_f(
        self,
        trade_returns: List[float],
    ) -> Dict[str, float]:
        """Optimal-f position sizing (Ralph Vince method).

        Finds the fraction of capital that maximizes the terminal wealth
        relative (TWR) over a series of historical trades.

        Args:
            trade_returns: List of historical trade P&L (positive and negative).

        Returns:
            Dict with optimal_f, twr (terminal wealth relative), and dollar_amount.
        """
        if not trade_returns:
            logger.warning("No trade returns provided")
            return {"optimal_f": 0.0, "twr": 1.0, "dollar_amount": 0.0}

        trades = np.array(trade_returns)
        max_loss = abs(min(trades))
        if max_loss < 1e-10:
            logger.warning("No losing trades; optimal_f undefined")
            return {"optimal_f": 1.0, "twr": 1.0, "dollar_amount": self.account_value}

        best_f = 0.0
        best_twr = 1.0

        for f_candidate in np.arange(0.01, 1.01, 0.01):
            hpr = 1 + f_candidate * (trades / max_loss)
            if np.any(hpr <= 0):
                continue
            twr = float(np.prod(hpr))
            if twr > best_twr:
                best_twr = twr
                best_f = f_candidate

        dollar_amount = self.account_value * best_f

        logger.info(
            "Optimal f: f=%.4f, TWR=%.4f, position=$%.2f",
            best_f, best_twr, dollar_amount,
        )

        return {
            "optimal_f": best_f,
            "twr": best_twr,
            "position_size": best_f,
            "dollar_amount": dollar_amount,
        }

    def atr_based(
        self,
        entry_price: float,
        atr: float,
        atr_multiplier: float = 2.0,
    ) -> Dict[str, float]:
        """ATR-based position sizing.

        Uses Average True Range to set a volatility-adjusted stop distance,
        then sizes the position so that the risk equals the account risk fraction.

        Args:
            entry_price: Trade entry price.
            atr: Current Average True Range value.
            atr_multiplier: Multiple of ATR for stop distance (default 2.0).

        Returns:
            Dict with stop_distance, risk_amount, shares, dollar_amount.
        """
        stop_distance = atr * atr_multiplier

        if stop_distance < 1e-10:
            logger.warning("ATR-based stop distance near zero; returning zero size")
            return {
                "stop_distance": 0.0,
                "risk_amount": 0.0,
                "shares": 0.0,
                "dollar_amount": 0.0,
            }

        risk_amount = self.account_value * self.risk_per_trade
        shares = risk_amount / stop_distance
        dollar_amount = shares * entry_price

        logger.info(
            "ATR-based sizing: ATR=%.4f, stop=%.4f, shares=%.2f, position=$%.2f",
            atr, stop_distance, shares, dollar_amount,
        )

        return {
            "stop_distance": stop_distance,
            "risk_amount": risk_amount,
            "shares": shares,
            "dollar_amount": dollar_amount,
            "position_size": dollar_amount / self.account_value,
        }

    def volatility_adjusted(
        self,
        asset_returns: pd.Series,
        target_vol: float = 0.10,
        lookback: int = 30,
        entry_price: float = 1.0,
    ) -> Dict[str, float]:
        """Volatility-adjusted position sizing.

        Scales the position so that the asset's contribution to portfolio
        volatility matches a per-asset target.

        Args:
            asset_returns: Series of asset returns.
            target_vol: Target annualized volatility per position.
            lookback: Window for volatility estimation.
            entry_price: Current asset price (for share calculation).

        Returns:
            Dict with realized_vol, target_weight, shares, dollar_amount.
        """
        recent = asset_returns.iloc[-lookback:]
        realized_vol = float(recent.std() * np.sqrt(self.frequency))

        if realized_vol < 1e-10:
            logger.warning("Near-zero realized vol; returning zero size")
            return {
                "realized_vol": 0.0,
                "target_weight": 0.0,
                "shares": 0.0,
                "dollar_amount": 0.0,
            }

        target_weight = target_vol / realized_vol
        target_weight = min(target_weight, 1.0)  # Cap at 100%

        dollar_amount = self.account_value * target_weight
        shares = dollar_amount / entry_price if entry_price > 0 else 0.0

        logger.info(
            "Vol-adjusted sizing: realized_vol=%.4f, weight=%.4f, position=$%.2f",
            realized_vol, target_weight, dollar_amount,
        )

        return {
            "realized_vol": realized_vol,
            "target_weight": target_weight,
            "shares": shares,
            "dollar_amount": dollar_amount,
            "position_size": target_weight,
        }

    def composite_size(
        self,
        methods: Dict[str, Dict[str, float]],
        weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """Combine multiple sizing methods into a composite recommendation.

        Takes results from multiple sizing methods and produces a weighted
        average position size.

        Args:
            methods: Dict mapping method name to its result dict
                     (each must contain 'position_size').
            weights: Weights for each method. Defaults to equal weight.

        Returns:
            Dict with composite position_size and dollar_amount.
        """
        if not methods:
            return {"position_size": 0.0, "dollar_amount": 0.0}

        if weights is None:
            weights = {m: 1.0 / len(methods) for m in methods}

        total_weight = sum(weights.values())
        composite = 0.0
        for method_name, result in methods.items():
            w = weights.get(method_name, 0.0) / total_weight
            size = result.get("position_size", 0.0)
            composite += w * size

        dollar_amount = self.account_value * composite

        logger.info(
            "Composite sizing: position=%.4f, dollar=$%.2f",
            composite, dollar_amount,
        )

        return {
            "position_size": composite,
            "dollar_amount": dollar_amount,
            "method_contributions": {
                m: weights.get(m, 0.0) / total_weight * methods[m].get("position_size", 0.0)
                for m in methods
            },
        }
