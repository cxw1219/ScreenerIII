"""
Scenario Analysis and Stress Testing Module for ScreenerIII

This module provides comprehensive risk analysis tools including Monte Carlo
simulation, historical stress testing, sensitivity analysis, and walk-forward
strategy validation. Designed for commodity trading portfolios.

Features:
- Monte Carlo simulation with correlated multi-asset support
- Predefined and custom stress test scenarios
- Multi-factor sensitivity analysis with Greeks-like measures
- Walk-forward analysis with overfitting detection

Author: ScreenerIII
License: MIT
"""

import logging
import warnings
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import copy

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    warnings.warn("NumPy not available. Scenario analysis will be disabled.")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    warnings.warn("Pandas not available. Scenario analysis will be disabled.")

try:
    from scipy import stats as scipy_stats
    from scipy.linalg import cholesky
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    warnings.warn("SciPy not available. Some statistical features will be limited.")

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class ScenarioType(Enum):
    """Types of predefined stress scenarios."""
    FINANCIAL_CRISIS_2008 = "2008_financial_crisis"
    COVID_2020 = "covid_2020"
    FLASH_CRASH_2010 = "flash_crash_2010"
    OIL_CRISIS_2014 = "oil_crisis_2014"
    CUSTOM = "custom"


@dataclass
class SimulationResult:
    """Container for Monte Carlo simulation outputs."""
    paths: Optional[Any] = None  # np.ndarray of simulated price paths
    terminal_values: Optional[Any] = None
    expected_return: float = 0.0
    var_95: float = 0.0
    var_99: float = 0.0
    cvar_95: float = 0.0
    cvar_99: float = 0.0
    probability_of_profit: float = 0.0
    probability_of_loss: float = 0.0
    confidence_intervals: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    return_distribution: Optional[Any] = None
    statistics: Dict[str, float] = field(default_factory=dict)


@dataclass
class StressTestResult:
    """Container for stress test outputs."""
    scenario_name: str = ""
    scenario_type: ScenarioType = ScenarioType.CUSTOM
    portfolio_impact: float = 0.0
    portfolio_impact_pct: float = 0.0
    asset_impacts: Dict[str, float] = field(default_factory=dict)
    worst_case_loss: float = 0.0
    estimated_recovery_days: int = 0
    risk_metrics: Dict[str, float] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SensitivityResult:
    """Container for sensitivity analysis outputs."""
    factor_name: str = ""
    base_value: float = 0.0
    sensitivities: Dict[float, float] = field(default_factory=dict)
    delta: float = 0.0
    gamma: float = 0.0
    break_even: Optional[float] = None
    scenario_matrix: Optional[Any] = None  # pd.DataFrame


@dataclass
class WalkForwardResult:
    """Container for walk-forward analysis outputs."""
    in_sample_returns: List[float] = field(default_factory=list)
    out_of_sample_returns: List[float] = field(default_factory=list)
    parameter_stability: Dict[str, float] = field(default_factory=dict)
    overfitting_score: float = 0.0
    robustness_score: float = 0.0
    window_results: List[Dict[str, Any]] = field(default_factory=list)
    is_robust: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Monte Carlo Simulator
# ---------------------------------------------------------------------------

class MonteCarloSimulator:
    """
    Monte Carlo simulation engine for price path generation and risk analysis.

    Supports single-asset Geometric Brownian Motion (GBM) and correlated
    multi-asset simulations via Cholesky decomposition.

    Args:
        n_simulations: Number of simulation paths to generate.
        time_horizon: Number of time steps (trading days) to simulate.
        random_seed: Optional seed for reproducibility.

    Example::

        simulator = MonteCarloSimulator(n_simulations=10000, time_horizon=252)
        result = simulator.simulate_gbm(
            current_price=100.0, drift=0.05, volatility=0.20
        )
        print(f"VaR 95%: {result.var_95:.2f}")
    """

    def __init__(
        self,
        n_simulations: int = 10_000,
        time_horizon: int = 252,
        random_seed: Optional[int] = None,
    ):
        if not NUMPY_AVAILABLE:
            raise ImportError("NumPy is required for Monte Carlo simulation.")

        self.n_simulations = n_simulations
        self.time_horizon = time_horizon
        self.rng = np.random.default_rng(random_seed)
        logger.info(
            "MonteCarloSimulator initialised: %d sims, %d steps",
            n_simulations, time_horizon,
        )

    # -- Single-asset GBM --------------------------------------------------

    def simulate_gbm(
        self,
        current_price: float,
        drift: float,
        volatility: float,
        dt: float = 1.0 / 252,
    ) -> SimulationResult:
        """
        Simulate price paths using Geometric Brownian Motion.

        dS = mu * S * dt + sigma * S * dW

        Args:
            current_price: Current asset price (S_0).
            drift: Annualised expected return (mu).
            volatility: Annualised volatility (sigma).
            dt: Time increment in years (default: 1 trading day).

        Returns:
            SimulationResult with paths, VaR, CVaR, and distribution stats.
        """
        logger.info(
            "Running GBM simulation: price=%.2f, mu=%.4f, sigma=%.4f",
            current_price, drift, volatility,
        )

        # Generate standard normal random draws
        z = self.rng.standard_normal((self.n_simulations, self.time_horizon))

        # Build log-return increments:  (mu - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z
        log_increments = (drift - 0.5 * volatility ** 2) * dt + volatility * np.sqrt(dt) * z

        # Cumulative sum to get log(S_t / S_0), then exponentiate
        log_paths = np.cumsum(log_increments, axis=1)
        # Prepend zero column for t=0
        log_paths = np.hstack([np.zeros((self.n_simulations, 1)), log_paths])
        paths = current_price * np.exp(log_paths)

        terminal_values = paths[:, -1]
        returns = (terminal_values - current_price) / current_price

        result = self._compute_simulation_statistics(
            paths, terminal_values, returns, current_price
        )
        logger.info(
            "GBM simulation complete. E[r]=%.4f, VaR95=%.4f",
            result.expected_return, result.var_95,
        )
        return result

    # -- Correlated multi-asset simulation ----------------------------------

    def simulate_correlated_assets(
        self,
        prices: Dict[str, float],
        drifts: Dict[str, float],
        volatilities: Dict[str, float],
        correlation_matrix: Any,
        dt: float = 1.0 / 252,
    ) -> Dict[str, SimulationResult]:
        """
        Simulate correlated price paths for multiple assets using Cholesky
        decomposition of the correlation matrix.

        Args:
            prices: Mapping of asset name to current price.
            drifts: Mapping of asset name to annualised drift.
            volatilities: Mapping of asset name to annualised volatility.
            correlation_matrix: Square correlation matrix (np.ndarray or list).
                               Order must match the key order of *prices*.
            dt: Time increment in years.

        Returns:
            Dict mapping each asset name to its SimulationResult.
        """
        asset_names = list(prices.keys())
        n_assets = len(asset_names)

        corr = np.asarray(correlation_matrix, dtype=np.float64)
        if corr.shape != (n_assets, n_assets):
            raise ValueError(
                f"Correlation matrix shape {corr.shape} does not match "
                f"{n_assets} assets."
            )

        logger.info(
            "Running correlated simulation for %d assets: %s",
            n_assets, asset_names,
        )

        # Cholesky decomposition: L such that L @ L^T = corr
        if SCIPY_AVAILABLE:
            L = cholesky(corr, lower=True)
        else:
            L = np.linalg.cholesky(corr)

        # Independent normals -> correlated normals
        z_independent = self.rng.standard_normal(
            (self.n_simulations, self.time_horizon, n_assets)
        )
        z_correlated = np.einsum("ij,ntj->nti", L, z_independent)

        results: Dict[str, SimulationResult] = {}
        for idx, name in enumerate(asset_names):
            s0 = prices[name]
            mu = drifts[name]
            sigma = volatilities[name]

            z_asset = z_correlated[:, :, idx]
            log_inc = (mu - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * z_asset
            log_paths = np.cumsum(log_inc, axis=1)
            log_paths = np.hstack([np.zeros((self.n_simulations, 1)), log_paths])
            paths = s0 * np.exp(log_paths)

            terminal = paths[:, -1]
            rets = (terminal - s0) / s0
            results[name] = self._compute_simulation_statistics(
                paths, terminal, rets, s0
            )

        logger.info("Correlated multi-asset simulation complete for %s", asset_names)
        return results

    # -- Path-dependent analysis -------------------------------------------

    def path_dependent_analysis(
        self,
        paths: Any,
        barrier_upper: Optional[float] = None,
        barrier_lower: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Analyse simulated paths for barrier-like or path-dependent features.

        Args:
            paths: np.ndarray of shape (n_simulations, n_steps+1).
            barrier_upper: Upper barrier level.
            barrier_lower: Lower barrier level.

        Returns:
            Dict with probabilities and statistics related to barriers,
            drawdowns, and run-ups.
        """
        logger.debug("Running path-dependent analysis on %d paths", paths.shape[0])

        initial_price = paths[:, 0]
        max_along_path = np.max(paths, axis=1)
        min_along_path = np.min(paths, axis=1)

        # Running max/min for drawdown
        running_max = np.maximum.accumulate(paths, axis=1)
        drawdowns = (running_max - paths) / running_max
        max_drawdown = np.max(drawdowns, axis=1)

        analysis: Dict[str, Any] = {
            "max_drawdown_mean": float(np.mean(max_drawdown)),
            "max_drawdown_median": float(np.median(max_drawdown)),
            "max_drawdown_95th": float(np.percentile(max_drawdown, 95)),
            "avg_path_max": float(np.mean(max_along_path)),
            "avg_path_min": float(np.mean(min_along_path)),
        }

        if barrier_upper is not None:
            hits = np.any(paths >= barrier_upper, axis=1)
            analysis["prob_hit_upper_barrier"] = float(np.mean(hits))
            # Average first passage time (for paths that hit)
            if np.any(hits):
                first_hit = np.argmax(paths[hits] >= barrier_upper, axis=1)
                analysis["avg_first_passage_upper"] = float(np.mean(first_hit))

        if barrier_lower is not None:
            hits = np.any(paths <= barrier_lower, axis=1)
            analysis["prob_hit_lower_barrier"] = float(np.mean(hits))
            if np.any(hits):
                first_hit = np.argmax(paths[hits] <= barrier_lower, axis=1)
                analysis["avg_first_passage_lower"] = float(np.mean(first_hit))

        return analysis

    # -- Internal helpers ---------------------------------------------------

    def _compute_simulation_statistics(
        self,
        paths: Any,
        terminal_values: Any,
        returns: Any,
        initial_price: float,
    ) -> SimulationResult:
        """Compute VaR, CVaR, confidence intervals and other statistics."""
        sorted_returns = np.sort(returns)

        var_95 = float(-np.percentile(returns, 5))
        var_99 = float(-np.percentile(returns, 1))

        idx_95 = int(0.05 * len(sorted_returns))
        idx_99 = int(0.01 * len(sorted_returns))
        cvar_95 = float(-np.mean(sorted_returns[:max(idx_95, 1)]))
        cvar_99 = float(-np.mean(sorted_returns[:max(idx_99, 1)]))

        prob_profit = float(np.mean(returns > 0))
        prob_loss = float(np.mean(returns < 0))

        ci_95 = (
            float(np.percentile(terminal_values, 2.5)),
            float(np.percentile(terminal_values, 97.5)),
        )
        ci_99 = (
            float(np.percentile(terminal_values, 0.5)),
            float(np.percentile(terminal_values, 99.5)),
        )

        skewness = float(np.mean(((returns - np.mean(returns)) / np.std(returns)) ** 3)) if np.std(returns) > 0 else 0.0
        kurtosis = float(np.mean(((returns - np.mean(returns)) / np.std(returns)) ** 4)) if np.std(returns) > 0 else 0.0

        statistics = {
            "mean_return": float(np.mean(returns)),
            "median_return": float(np.median(returns)),
            "std_return": float(np.std(returns)),
            "skewness": skewness,
            "kurtosis": kurtosis,
            "min_return": float(np.min(returns)),
            "max_return": float(np.max(returns)),
            "mean_terminal_price": float(np.mean(terminal_values)),
            "median_terminal_price": float(np.median(terminal_values)),
        }

        return SimulationResult(
            paths=paths,
            terminal_values=terminal_values,
            expected_return=float(np.mean(returns)),
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            cvar_99=cvar_99,
            probability_of_profit=prob_profit,
            probability_of_loss=prob_loss,
            confidence_intervals={"95%": ci_95, "99%": ci_99},
            return_distribution=returns,
            statistics=statistics,
        )


# ---------------------------------------------------------------------------
# Stress Tester
# ---------------------------------------------------------------------------

# Predefined scenario shocks: mapping from ScenarioType to a dict describing
# multiplier shocks applied to price, volatility, and correlation.
_PREDEFINED_SCENARIOS: Dict[ScenarioType, Dict[str, Any]] = {
    ScenarioType.FINANCIAL_CRISIS_2008: {
        "name": "2008 Financial Crisis",
        "description": (
            "Simulates a broad-based financial crisis with severe equity and "
            "commodity sell-offs, spiking volatility, and correlation breakdown."
        ),
        "price_shocks": {
            "equity": -0.55,
            "crude_oil": -0.70,
            "gold": 0.25,
            "natural_gas": -0.40,
            "copper": -0.60,
            "agriculture": -0.30,
            "default": -0.40,
        },
        "volatility_multiplier": 3.0,
        "correlation_shift": 0.30,
        "duration_days": 365,
        "recovery_days_estimate": 900,
    },
    ScenarioType.COVID_2020: {
        "name": "COVID-19 Pandemic",
        "description": (
            "Rapid sell-off across most asset classes driven by pandemic fears, "
            "followed by unprecedented policy response."
        ),
        "price_shocks": {
            "equity": -0.34,
            "crude_oil": -0.65,
            "gold": 0.10,
            "natural_gas": -0.25,
            "copper": -0.25,
            "agriculture": -0.15,
            "default": -0.25,
        },
        "volatility_multiplier": 4.0,
        "correlation_shift": 0.40,
        "duration_days": 35,
        "recovery_days_estimate": 150,
    },
    ScenarioType.FLASH_CRASH_2010: {
        "name": "2010 Flash Crash",
        "description": (
            "Sudden intraday liquidity evaporation causing rapid price drops "
            "and near-instant partial recovery."
        ),
        "price_shocks": {
            "equity": -0.09,
            "crude_oil": -0.08,
            "gold": 0.02,
            "natural_gas": -0.05,
            "copper": -0.07,
            "agriculture": -0.04,
            "default": -0.06,
        },
        "volatility_multiplier": 5.0,
        "correlation_shift": 0.50,
        "duration_days": 1,
        "recovery_days_estimate": 3,
    },
    ScenarioType.OIL_CRISIS_2014: {
        "name": "2014-2016 Oil Price Crash",
        "description": (
            "Prolonged decline in oil prices driven by oversupply, with "
            "contagion into energy-linked commodities and equities."
        ),
        "price_shocks": {
            "equity": -0.12,
            "crude_oil": -0.75,
            "gold": -0.05,
            "natural_gas": -0.50,
            "copper": -0.30,
            "agriculture": -0.10,
            "default": -0.20,
        },
        "volatility_multiplier": 2.0,
        "correlation_shift": 0.15,
        "duration_days": 540,
        "recovery_days_estimate": 1080,
    },
}


class StressTester:
    """
    Historical and hypothetical stress testing engine for portfolios.

    Applies predefined or custom shock scenarios to a portfolio and
    estimates P&L impact, worst-case losses, and recovery timelines.

    Args:
        portfolio: Dict mapping asset name to current position value (signed;
                   negative for short positions).

    Example::

        portfolio = {"crude_oil": 50000, "gold": 30000, "equity": 20000}
        tester = StressTester(portfolio)
        result = tester.run_scenario(ScenarioType.COVID_2020)
        print(f"Portfolio impact: {result.portfolio_impact_pct:.1%}")
    """

    def __init__(self, portfolio: Dict[str, float]):
        if not NUMPY_AVAILABLE:
            raise ImportError("NumPy is required for stress testing.")

        self.portfolio = portfolio
        self.total_value = sum(abs(v) for v in portfolio.values())
        logger.info(
            "StressTester initialised with %d positions, total value %.2f",
            len(portfolio), self.total_value,
        )

    def run_scenario(
        self,
        scenario: Union[ScenarioType, Dict[str, Any]],
    ) -> StressTestResult:
        """
        Run a single stress scenario against the portfolio.

        Args:
            scenario: Either a ScenarioType enum for predefined scenarios,
                      or a dict with keys: name, price_shocks (dict),
                      volatility_multiplier (float), correlation_shift (float),
                      duration_days (int), recovery_days_estimate (int).

        Returns:
            StressTestResult with portfolio impact details.
        """
        if isinstance(scenario, ScenarioType):
            if scenario == ScenarioType.CUSTOM:
                raise ValueError(
                    "Use a dict for custom scenarios, not ScenarioType.CUSTOM."
                )
            config = _PREDEFINED_SCENARIOS[scenario]
            scenario_type = scenario
        else:
            config = scenario
            scenario_type = ScenarioType.CUSTOM

        scenario_name = config.get("name", "Custom Scenario")
        price_shocks = config.get("price_shocks", {})
        vol_mult = config.get("volatility_multiplier", 1.0)
        corr_shift = config.get("correlation_shift", 0.0)
        recovery_est = config.get("recovery_days_estimate", 0)

        logger.info("Running stress scenario: %s", scenario_name)

        asset_impacts: Dict[str, float] = {}
        total_impact = 0.0

        for asset, position_value in self.portfolio.items():
            # Look up shock: try exact match, then default
            shock = price_shocks.get(asset, price_shocks.get("default", 0.0))
            impact = position_value * shock
            asset_impacts[asset] = impact
            total_impact += impact

        portfolio_impact_pct = total_impact / self.total_value if self.total_value else 0.0

        risk_metrics = {
            "volatility_multiplier": vol_mult,
            "correlation_shift": corr_shift,
            "gross_exposure_after_shock": sum(
                abs(v + asset_impacts.get(k, 0)) for k, v in self.portfolio.items()
            ),
            "net_exposure_after_shock": sum(
                v + asset_impacts.get(k, 0) for k, v in self.portfolio.items()
            ),
        }

        result = StressTestResult(
            scenario_name=scenario_name,
            scenario_type=scenario_type,
            portfolio_impact=total_impact,
            portfolio_impact_pct=portfolio_impact_pct,
            asset_impacts=asset_impacts,
            worst_case_loss=total_impact if total_impact < 0 else 0.0,
            estimated_recovery_days=recovery_est,
            risk_metrics=risk_metrics,
            details=config,
        )

        logger.info(
            "Scenario '%s' impact: %.2f (%.2f%%)",
            scenario_name, total_impact, portfolio_impact_pct * 100,
        )
        return result

    def run_all_predefined(self) -> List[StressTestResult]:
        """Run all predefined stress scenarios and return sorted by impact."""
        results = []
        for scenario_type in _PREDEFINED_SCENARIOS:
            try:
                results.append(self.run_scenario(scenario_type))
            except Exception as exc:
                logger.error("Failed scenario %s: %s", scenario_type, exc)
        results.sort(key=lambda r: r.portfolio_impact)
        return results

    def identify_worst_case(
        self,
        custom_scenarios: Optional[List[Dict[str, Any]]] = None,
    ) -> StressTestResult:
        """
        Identify the worst-case scenario from all predefined scenarios and
        any additional custom ones provided.

        Args:
            custom_scenarios: Optional list of custom scenario dicts.

        Returns:
            The StressTestResult with the largest loss.
        """
        results = self.run_all_predefined()
        if custom_scenarios:
            for cs in custom_scenarios:
                results.append(self.run_scenario(cs))
        if not results:
            raise ValueError("No scenarios to evaluate.")

        worst = min(results, key=lambda r: r.portfolio_impact)
        logger.info(
            "Worst-case scenario: '%s' with impact %.2f",
            worst.scenario_name, worst.portfolio_impact,
        )
        return worst

    def multi_factor_stress(
        self,
        price_shock_range: Tuple[float, float] = (-0.50, 0.10),
        volatility_range: Tuple[float, float] = (1.0, 5.0),
        correlation_range: Tuple[float, float] = (0.0, 0.60),
        n_steps: int = 5,
    ) -> List[StressTestResult]:
        """
        Generate a grid of multi-factor stress tests varying price shock,
        volatility multiplier, and correlation shift simultaneously.

        Args:
            price_shock_range: (min, max) uniform price shock to apply.
            volatility_range: (min, max) volatility multiplier.
            correlation_range: (min, max) correlation shift.
            n_steps: Number of steps for each factor.

        Returns:
            List of StressTestResults across the parameter grid.
        """
        price_steps = np.linspace(price_shock_range[0], price_shock_range[1], n_steps)
        vol_steps = np.linspace(volatility_range[0], volatility_range[1], n_steps)
        corr_steps = np.linspace(correlation_range[0], correlation_range[1], n_steps)

        results: List[StressTestResult] = []
        total_combos = n_steps ** 3
        logger.info(
            "Multi-factor stress test: %d combinations across %d factors",
            total_combos, 3,
        )

        for ps in price_steps:
            for vm in vol_steps:
                for cs in corr_steps:
                    custom = {
                        "name": f"MF_ps={ps:.2f}_vm={vm:.1f}_cs={cs:.2f}",
                        "price_shocks": {"default": float(ps)},
                        "volatility_multiplier": float(vm),
                        "correlation_shift": float(cs),
                        "duration_days": 30,
                        "recovery_days_estimate": 0,
                    }
                    results.append(self.run_scenario(custom))

        results.sort(key=lambda r: r.portfolio_impact)
        logger.info(
            "Multi-factor stress test complete. Worst impact: %.2f",
            results[0].portfolio_impact if results else 0,
        )
        return results

    @staticmethod
    def estimate_recovery_time(
        drawdown_pct: float,
        avg_daily_return: float = 0.0004,
        volatility: float = 0.01,
    ) -> int:
        """
        Estimate recovery time in trading days from a given drawdown.

        Uses a simple expected-return model:
            days = -ln(1 + drawdown) / (daily_return - 0.5 * vol^2)

        Args:
            drawdown_pct: Drawdown as a negative fraction (e.g. -0.30 for 30%).
            avg_daily_return: Expected daily log return.
            volatility: Daily volatility.

        Returns:
            Estimated number of trading days to recover.
        """
        if drawdown_pct >= 0:
            return 0
        denominator = avg_daily_return - 0.5 * volatility ** 2
        if denominator <= 0:
            logger.warning("Non-positive drift; recovery may not occur.")
            return 99999
        recovery = -np.log(1.0 + drawdown_pct) / denominator
        return max(1, int(np.ceil(recovery)))


# ---------------------------------------------------------------------------
# Sensitivity Analyzer
# ---------------------------------------------------------------------------

class SensitivityAnalyzer:
    """
    Sensitivity analysis engine providing single-factor, multi-factor, and
    Greeks-like risk measures for a portfolio or strategy.

    The analyzer works by evaluating a user-supplied *valuation function*
    at perturbed inputs and computing finite-difference approximations
    to partial derivatives.

    Args:
        valuation_fn: Callable that takes a dict of factor values and
                      returns a portfolio value (float).
        base_factors: Dict of factor_name -> current value.

    Example::

        def portfolio_value(factors):
            return factors["price"] * 100 - factors["price"] ** 2 * 0.1

        analyzer = SensitivityAnalyzer(
            valuation_fn=portfolio_value,
            base_factors={"price": 50.0},
        )
        result = analyzer.single_factor_sensitivity("price", shocks=[-0.10, -0.05, 0.0, 0.05, 0.10])
        print(f"Delta: {result.delta:.4f}, Gamma: {result.gamma:.4f}")
    """

    def __init__(
        self,
        valuation_fn: Callable[[Dict[str, float]], float],
        base_factors: Dict[str, float],
    ):
        if not NUMPY_AVAILABLE:
            raise ImportError("NumPy is required for sensitivity analysis.")

        self.valuation_fn = valuation_fn
        self.base_factors = dict(base_factors)
        self.base_value = valuation_fn(dict(base_factors))
        logger.info(
            "SensitivityAnalyzer initialised. Base value: %.4f, factors: %s",
            self.base_value, list(base_factors.keys()),
        )

    def single_factor_sensitivity(
        self,
        factor: str,
        shocks: Optional[List[float]] = None,
        n_points: int = 21,
        shock_range: Tuple[float, float] = (-0.20, 0.20),
    ) -> SensitivityResult:
        """
        Compute portfolio sensitivity to a single factor.

        Args:
            factor: Name of the factor to shock.
            shocks: Explicit list of relative shocks (e.g. [-0.10, 0, 0.10]).
                    If None, a uniform grid from *shock_range* is used.
            n_points: Number of grid points when *shocks* is None.
            shock_range: (min_shock, max_shock) as fractions.

        Returns:
            SensitivityResult with delta, gamma, and value at each shock.
        """
        if factor not in self.base_factors:
            raise KeyError(f"Factor '{factor}' not in base_factors.")

        if shocks is None:
            shocks = np.linspace(shock_range[0], shock_range[1], n_points).tolist()

        base_factor_val = self.base_factors[factor]
        sensitivities: Dict[float, float] = {}

        for shock in shocks:
            perturbed = dict(self.base_factors)
            perturbed[factor] = base_factor_val * (1.0 + shock)
            sensitivities[shock] = self.valuation_fn(perturbed)

        # Finite-difference delta and gamma
        delta, gamma = self._compute_greeks(factor, base_factor_val)

        # Break-even: find shock where value crosses zero
        break_even = self._find_break_even(sensitivities)

        result = SensitivityResult(
            factor_name=factor,
            base_value=self.base_value,
            sensitivities=sensitivities,
            delta=delta,
            gamma=gamma,
            break_even=break_even,
        )

        logger.info(
            "Single-factor sensitivity for '%s': delta=%.4f, gamma=%.4f",
            factor, delta, gamma,
        )
        return result

    def multi_factor_sensitivity(
        self,
        factors: List[str],
        shocks: Optional[List[float]] = None,
        n_points: int = 11,
        shock_range: Tuple[float, float] = (-0.20, 0.20),
    ) -> Dict[str, SensitivityResult]:
        """
        Run single-factor sensitivity for multiple factors.

        Args:
            factors: List of factor names to analyse.
            shocks: Shared shock grid (applies to all factors).
            n_points: Grid size if *shocks* is None.
            shock_range: Range for auto-generated grid.

        Returns:
            Dict mapping factor name to its SensitivityResult.
        """
        results: Dict[str, SensitivityResult] = {}
        for f in factors:
            results[f] = self.single_factor_sensitivity(
                f, shocks=shocks, n_points=n_points, shock_range=shock_range,
            )
        return results

    def scenario_matrix(
        self,
        factor_a: str,
        factor_b: str,
        shocks_a: Optional[List[float]] = None,
        shocks_b: Optional[List[float]] = None,
        n_points: int = 11,
        shock_range: Tuple[float, float] = (-0.20, 0.20),
    ) -> Any:
        """
        Build a two-dimensional scenario matrix showing portfolio value
        across a grid of shocks to two factors simultaneously.

        Args:
            factor_a: First factor name (rows).
            factor_b: Second factor name (columns).
            shocks_a: Shocks for factor_a.
            shocks_b: Shocks for factor_b.
            n_points: Grid resolution per factor.
            shock_range: Default shock range.

        Returns:
            pd.DataFrame with factor_a shocks as index, factor_b as columns,
            and portfolio values as entries.
        """
        if not PANDAS_AVAILABLE:
            raise ImportError("Pandas is required for scenario_matrix.")

        if shocks_a is None:
            shocks_a = np.linspace(shock_range[0], shock_range[1], n_points).tolist()
        if shocks_b is None:
            shocks_b = np.linspace(shock_range[0], shock_range[1], n_points).tolist()

        base_a = self.base_factors[factor_a]
        base_b = self.base_factors[factor_b]

        matrix = np.empty((len(shocks_a), len(shocks_b)))
        for i, sa in enumerate(shocks_a):
            for j, sb in enumerate(shocks_b):
                perturbed = dict(self.base_factors)
                perturbed[factor_a] = base_a * (1.0 + sa)
                perturbed[factor_b] = base_b * (1.0 + sb)
                matrix[i, j] = self.valuation_fn(perturbed)

        df = pd.DataFrame(
            matrix,
            index=[f"{s:+.1%}" for s in shocks_a],
            columns=[f"{s:+.1%}" for s in shocks_b],
        )
        df.index.name = factor_a
        df.columns.name = factor_b

        logger.info(
            "Scenario matrix (%s x %s): %d x %d grid",
            factor_a, factor_b, len(shocks_a), len(shocks_b),
        )
        return df

    def compute_all_greeks(self) -> Dict[str, Dict[str, float]]:
        """
        Compute delta and gamma for every factor in the base set.

        Returns:
            Dict[factor_name, {"delta": ..., "gamma": ...}].
        """
        greeks: Dict[str, Dict[str, float]] = {}
        for factor, base_val in self.base_factors.items():
            delta, gamma = self._compute_greeks(factor, base_val)
            greeks[factor] = {"delta": delta, "gamma": gamma}
        logger.info("Computed Greeks for %d factors", len(greeks))
        return greeks

    def break_even_analysis(
        self,
        factor: str,
        search_range: Tuple[float, float] = (-0.50, 0.50),
        precision: int = 200,
    ) -> Optional[float]:
        """
        Find the shock level to *factor* where portfolio value crosses zero.

        Uses a fine grid search and linear interpolation between sign changes.

        Args:
            factor: Factor to shock.
            search_range: Range of relative shocks to search.
            precision: Number of evaluation points.

        Returns:
            The shock fraction at which the portfolio value crosses zero,
            or None if no crossing is found.
        """
        base_val = self.base_factors[factor]
        shock_grid = np.linspace(search_range[0], search_range[1], precision)
        values = []

        for s in shock_grid:
            perturbed = dict(self.base_factors)
            perturbed[factor] = base_val * (1.0 + s)
            values.append(self.valuation_fn(perturbed))

        values = np.array(values)
        sign_changes = np.where(np.diff(np.sign(values)))[0]

        if len(sign_changes) == 0:
            logger.debug("No break-even found for factor '%s'", factor)
            return None

        idx = sign_changes[0]
        # Linear interpolation between idx and idx+1
        s0, s1 = shock_grid[idx], shock_grid[idx + 1]
        v0, v1 = values[idx], values[idx + 1]
        break_even_shock = s0 - v0 * (s1 - s0) / (v1 - v0)

        logger.info(
            "Break-even for '%s': shock = %.4f (price %.4f -> %.4f)",
            factor, break_even_shock, base_val,
            base_val * (1 + break_even_shock),
        )
        return float(break_even_shock)

    # -- Private helpers ----------------------------------------------------

    def _compute_greeks(
        self, factor: str, base_val: float, h_frac: float = 0.01,
    ) -> Tuple[float, float]:
        """Compute delta and gamma via central finite differences."""
        h = base_val * h_frac
        if h == 0:
            return 0.0, 0.0

        up = dict(self.base_factors)
        down = dict(self.base_factors)
        up[factor] = base_val + h
        down[factor] = base_val - h

        v_up = self.valuation_fn(up)
        v_down = self.valuation_fn(down)

        delta = (v_up - v_down) / (2 * h)
        gamma = (v_up - 2 * self.base_value + v_down) / (h ** 2)
        return float(delta), float(gamma)

    @staticmethod
    def _find_break_even(
        sensitivities: Dict[float, float],
    ) -> Optional[float]:
        """Find break-even from a shock->value mapping via sign change."""
        sorted_items = sorted(sensitivities.items())
        for i in range(len(sorted_items) - 1):
            s0, v0 = sorted_items[i]
            s1, v1 = sorted_items[i + 1]
            if v0 * v1 < 0:
                return float(s0 - v0 * (s1 - s0) / (v1 - v0))
        return None


# ---------------------------------------------------------------------------
# Walk-Forward Analyzer
# ---------------------------------------------------------------------------

class WalkForwardAnalyzer:
    """
    Walk-forward analysis engine for validating trading strategies.

    Splits historical data into rolling in-sample (training) and
    out-of-sample (testing) windows, runs a user-supplied strategy
    function on each window, and evaluates parameter stability,
    overfitting risk, and overall robustness.

    Args:
        data: pd.DataFrame with a datetime index and at least a 'close'
              column (or column specified by *price_col*).
        strategy_fn: Callable(training_data, **params) -> Dict with at least
                     "returns" (float or array) and optionally "params" (dict
                     of optimised parameters).
        price_col: Column name for prices.

    Example::

        def my_strategy(data, **params):
            lookback = params.get("lookback", 20)
            ma = data["close"].rolling(lookback).mean()
            signal = (data["close"] > ma).astype(int).shift(1).fillna(0)
            returns = signal * data["close"].pct_change()
            return {
                "returns": returns.sum(),
                "params": {"lookback": lookback},
                "sharpe": returns.mean() / returns.std() * (252 ** 0.5) if returns.std() > 0 else 0,
            }

        analyzer = WalkForwardAnalyzer(price_data, my_strategy)
        result = analyzer.run(
            in_sample_pct=0.70,
            n_windows=6,
            strategy_params={"lookback": 20},
        )
        print(f"Robustness score: {result.robustness_score:.2f}")
    """

    def __init__(
        self,
        data: Any,
        strategy_fn: Callable,
        price_col: str = "close",
    ):
        if not PANDAS_AVAILABLE or not NUMPY_AVAILABLE:
            raise ImportError(
                "Pandas and NumPy are required for walk-forward analysis."
            )

        self.data = data
        self.strategy_fn = strategy_fn
        self.price_col = price_col
        logger.info(
            "WalkForwardAnalyzer initialised: %d rows, column='%s'",
            len(data), price_col,
        )

    def run(
        self,
        in_sample_pct: float = 0.70,
        n_windows: int = 5,
        step_size: Optional[int] = None,
        strategy_params: Optional[Dict[str, Any]] = None,
        optimiser_fn: Optional[Callable] = None,
    ) -> WalkForwardResult:
        """
        Execute the walk-forward analysis.

        Args:
            in_sample_pct: Fraction of each window used for in-sample training.
            n_windows: Number of rolling windows.
            step_size: Number of rows to advance between windows. If None,
                       windows are spaced evenly across the dataset.
            strategy_params: Parameters passed to strategy_fn.
            optimiser_fn: Optional callable(training_data) -> dict of optimised
                          params. When provided, optimised params are used for
                          the out-of-sample evaluation and stability is tracked.

        Returns:
            WalkForwardResult with in/out-of-sample returns, stability, and
            overfitting/robustness scores.
        """
        n_rows = len(self.data)
        if strategy_params is None:
            strategy_params = {}

        # Compute window and step sizes
        window_size = n_rows // n_windows if step_size is None else None
        if step_size is None:
            step_size = max(1, (n_rows - (window_size or n_rows)) // max(n_windows - 1, 1))
            window_size = n_rows // n_windows * 2  # overlapping
            window_size = min(window_size, n_rows)
            step_size = max(1, (n_rows - window_size) // max(n_windows - 1, 1))

        logger.info(
            "Walk-forward: %d windows, window=%d rows, step=%d, IS=%.0f%%",
            n_windows, window_size, step_size, in_sample_pct * 100,
        )

        in_sample_returns: List[float] = []
        out_of_sample_returns: List[float] = []
        window_results: List[Dict[str, Any]] = []
        all_params: List[Dict[str, Any]] = []

        for w in range(n_windows):
            start = w * step_size
            end = min(start + window_size, n_rows)
            if end - start < 10:
                logger.warning("Window %d too small (%d rows), skipping.", w, end - start)
                continue

            window_data = self.data.iloc[start:end].copy()
            split_idx = int(len(window_data) * in_sample_pct)

            train_data = window_data.iloc[:split_idx]
            test_data = window_data.iloc[split_idx:]

            if len(train_data) < 5 or len(test_data) < 2:
                logger.warning("Window %d: insufficient data after split.", w)
                continue

            # In-sample: run strategy (with optional optimisation)
            if optimiser_fn is not None:
                opt_params = optimiser_fn(train_data)
                current_params = {**strategy_params, **opt_params}
            else:
                current_params = dict(strategy_params)

            is_result = self.strategy_fn(train_data, **current_params)
            os_result = self.strategy_fn(test_data, **current_params)

            is_ret = self._extract_return(is_result)
            os_ret = self._extract_return(os_result)

            in_sample_returns.append(is_ret)
            out_of_sample_returns.append(os_ret)

            params_used = is_result.get("params", current_params)
            all_params.append(params_used)

            window_results.append({
                "window": w,
                "start_idx": start,
                "end_idx": end,
                "split_idx": start + split_idx,
                "in_sample_return": is_ret,
                "out_of_sample_return": os_ret,
                "params": params_used,
                "in_sample_sharpe": is_result.get("sharpe", None),
                "out_of_sample_sharpe": os_result.get("sharpe", None),
            })

        # Compute aggregate metrics
        param_stability = self._compute_parameter_stability(all_params)
        overfitting_score = self._compute_overfitting_score(
            in_sample_returns, out_of_sample_returns
        )
        robustness_score = self._compute_robustness_score(
            out_of_sample_returns, overfitting_score
        )

        result = WalkForwardResult(
            in_sample_returns=in_sample_returns,
            out_of_sample_returns=out_of_sample_returns,
            parameter_stability=param_stability,
            overfitting_score=overfitting_score,
            robustness_score=robustness_score,
            window_results=window_results,
            is_robust=robustness_score >= 0.50,
            details={
                "n_windows_evaluated": len(window_results),
                "avg_is_return": float(np.mean(in_sample_returns)) if in_sample_returns else 0.0,
                "avg_os_return": float(np.mean(out_of_sample_returns)) if out_of_sample_returns else 0.0,
                "os_win_rate": float(np.mean([r > 0 for r in out_of_sample_returns])) if out_of_sample_returns else 0.0,
            },
        )

        logger.info(
            "Walk-forward complete. Overfitting=%.2f, Robustness=%.2f, Robust=%s",
            overfitting_score, robustness_score, result.is_robust,
        )
        return result

    def rolling_backtest(
        self,
        window_size: int = 252,
        step_size: int = 21,
        strategy_params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Run a pure rolling-window backtest (no in/out-of-sample split).

        Each window of *window_size* rows is evaluated independently and the
        strategy result is stored.

        Args:
            window_size: Number of rows per window.
            step_size: Number of rows to advance.
            strategy_params: Passed to strategy_fn.

        Returns:
            List of dicts with window metadata and strategy results.
        """
        if strategy_params is None:
            strategy_params = {}

        n_rows = len(self.data)
        results: List[Dict[str, Any]] = []
        start = 0

        while start + window_size <= n_rows:
            window_data = self.data.iloc[start:start + window_size]
            strat_result = self.strategy_fn(window_data, **strategy_params)
            ret = self._extract_return(strat_result)

            results.append({
                "start_idx": start,
                "end_idx": start + window_size,
                "return": ret,
                "sharpe": strat_result.get("sharpe", None),
                "params": strat_result.get("params", strategy_params),
            })
            start += step_size

        logger.info("Rolling backtest: %d windows evaluated.", len(results))
        return results

    # -- Private helpers ----------------------------------------------------

    @staticmethod
    def _extract_return(result: Dict[str, Any]) -> float:
        """Extract a scalar return from a strategy result dict or array."""
        ret = result.get("returns", 0.0)
        if hasattr(ret, "__len__"):
            return float(np.sum(ret))
        return float(ret)

    @staticmethod
    def _compute_parameter_stability(
        all_params: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """
        Compute coefficient of variation for each numeric parameter across
        windows. Lower values indicate more stable parameters.
        """
        if not all_params:
            return {}

        keys = set()
        for p in all_params:
            keys.update(p.keys())

        stability: Dict[str, float] = {}
        for key in keys:
            values = []
            for p in all_params:
                v = p.get(key)
                if isinstance(v, (int, float)):
                    values.append(float(v))
            if len(values) >= 2:
                arr = np.array(values)
                mean = np.mean(arr)
                std = np.std(arr)
                cv = float(std / abs(mean)) if abs(mean) > 1e-12 else float("inf")
                stability[key] = cv

        return stability

    @staticmethod
    def _compute_overfitting_score(
        is_returns: List[float],
        os_returns: List[float],
    ) -> float:
        """
        Compute an overfitting score between 0 (no overfitting) and 1 (severe).

        Based on the ratio of out-of-sample performance degradation relative
        to in-sample performance.
        """
        if not is_returns or not os_returns:
            return 0.0

        avg_is = np.mean(is_returns)
        avg_os = np.mean(os_returns)

        if abs(avg_is) < 1e-12:
            return 0.0

        # Degradation ratio: how much worse is OS vs IS
        degradation = 1.0 - (avg_os / avg_is) if avg_is > 0 else 0.0
        # Clamp to [0, 1]
        return float(np.clip(degradation, 0.0, 1.0))

    @staticmethod
    def _compute_robustness_score(
        os_returns: List[float],
        overfitting_score: float,
    ) -> float:
        """
        Compute a robustness score between 0 (fragile) and 1 (robust).

        Combines out-of-sample consistency, profitability, and overfitting
        penalty.
        """
        if not os_returns:
            return 0.0

        arr = np.array(os_returns)
        # Consistency: fraction of positive out-of-sample windows
        consistency = float(np.mean(arr > 0))
        # Penalise high variability
        if np.mean(np.abs(arr)) > 1e-12:
            stability = 1.0 - min(float(np.std(arr) / np.mean(np.abs(arr))), 1.0)
        else:
            stability = 0.0

        raw = 0.5 * consistency + 0.3 * stability + 0.2 * (1.0 - overfitting_score)
        return float(np.clip(raw, 0.0, 1.0))


# ---------------------------------------------------------------------------
# Convenience / top-level functions
# ---------------------------------------------------------------------------

def quick_monte_carlo(
    price: float,
    drift: float,
    volatility: float,
    days: int = 252,
    n_sims: int = 10_000,
    seed: Optional[int] = None,
) -> SimulationResult:
    """
    Convenience function for a quick single-asset Monte Carlo simulation.

    Args:
        price: Current price.
        drift: Annualised drift (mu).
        volatility: Annualised volatility (sigma).
        days: Number of trading days to simulate.
        n_sims: Number of simulation paths.
        seed: Random seed.

    Returns:
        SimulationResult.
    """
    sim = MonteCarloSimulator(n_simulations=n_sims, time_horizon=days, random_seed=seed)
    return sim.simulate_gbm(price, drift, volatility)


def quick_stress_test(
    portfolio: Dict[str, float],
    scenario: Union[ScenarioType, Dict[str, Any]] = ScenarioType.FINANCIAL_CRISIS_2008,
) -> StressTestResult:
    """
    Convenience function for a quick portfolio stress test.

    Args:
        portfolio: Asset name -> position value.
        scenario: ScenarioType or custom scenario dict.

    Returns:
        StressTestResult.
    """
    tester = StressTester(portfolio)
    return tester.run_scenario(scenario)


def run_full_risk_analysis(
    portfolio: Dict[str, float],
    prices: Dict[str, float],
    drifts: Dict[str, float],
    volatilities: Dict[str, float],
    correlation_matrix: Any,
    n_simulations: int = 10_000,
    time_horizon: int = 252,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Run a comprehensive risk analysis combining Monte Carlo simulation,
    all predefined stress tests, and basic sensitivity analysis.

    Args:
        portfolio: Asset name -> position value (signed).
        prices: Asset name -> current price.
        drifts: Asset name -> annualised drift.
        volatilities: Asset name -> annualised volatility.
        correlation_matrix: Correlation matrix matching key order of *prices*.
        n_simulations: Monte Carlo path count.
        time_horizon: Simulation horizon in trading days.
        seed: Random seed.

    Returns:
        Dict with keys "monte_carlo", "stress_tests", "worst_case",
        and "sensitivity".
    """
    logger.info("Starting full risk analysis for %d assets", len(portfolio))

    # Monte Carlo
    mc = MonteCarloSimulator(
        n_simulations=n_simulations, time_horizon=time_horizon, random_seed=seed,
    )
    mc_results = mc.simulate_correlated_assets(
        prices, drifts, volatilities, correlation_matrix,
    )

    # Stress tests
    tester = StressTester(portfolio)
    stress_results = tester.run_all_predefined()
    worst_case = tester.identify_worst_case()

    # Simple sensitivity: uniform shock across portfolio
    def portfolio_valuation(factors: Dict[str, float]) -> float:
        total = 0.0
        for asset, pos in portfolio.items():
            shock = factors.get(asset, 1.0)
            total += pos * shock
        return total

    base_factors = {asset: 1.0 for asset in portfolio}
    sa = SensitivityAnalyzer(portfolio_valuation, base_factors)
    greeks = sa.compute_all_greeks()

    analysis = {
        "monte_carlo": mc_results,
        "stress_tests": stress_results,
        "worst_case": worst_case,
        "sensitivity": greeks,
    }

    logger.info("Full risk analysis complete.")
    return analysis
