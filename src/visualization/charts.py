"""
Advanced Charting and Visualization Module

Provides comprehensive charting capabilities for commodity trading analysis,
including candlestick charts, performance visualizations, correlation analysis,
risk metrics displays, and multi-chart dashboards.

Author: ScreenerIII
License: MIT
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from io import BytesIO
import logging
import warnings

import numpy as np
import pandas as pd

# Optional matplotlib import with graceful fallback
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend for server use
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import matplotlib.gridspec as gridspec
    import matplotlib.ticker as mticker
    from matplotlib.patches import FancyArrowPatch
    from matplotlib.colors import LinearSegmentedColormap, Normalize
    from matplotlib.figure import Figure
    MPL_AVAILABLE = True
except ImportError:
    MPL_AVAILABLE = False
    plt = None
    Figure = None

try:
    from scipy.cluster.hierarchy import dendrogram, linkage
    from scipy.spatial.distance import squareform
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

logger = logging.getLogger(__name__)


def _require_matplotlib(func):
    """Decorator that raises ImportError if matplotlib is not available."""
    def wrapper(*args, **kwargs):
        if not MPL_AVAILABLE:
            raise ImportError(
                "matplotlib is required for chart rendering. "
                "Install it with: pip install matplotlib"
            )
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


class ChartStyle(Enum):
    """Available chart visual styles."""
    DEFAULT = "default"
    DARK = "dark"
    MINIMAL = "minimal"
    PRINT = "print"


_STYLE_CONFIG = {
    ChartStyle.DEFAULT: {
        "figure.facecolor": "#ffffff",
        "axes.facecolor": "#f8f9fa",
        "axes.edgecolor": "#cccccc",
        "axes.grid": True,
        "grid.color": "#e0e0e0",
        "grid.alpha": 0.7,
        "text.color": "#333333",
        "axes.labelcolor": "#333333",
        "xtick.color": "#666666",
        "ytick.color": "#666666",
    },
    ChartStyle.DARK: {
        "figure.facecolor": "#1e1e2f",
        "axes.facecolor": "#2a2a3d",
        "axes.edgecolor": "#444466",
        "axes.grid": True,
        "grid.color": "#3a3a5c",
        "grid.alpha": 0.5,
        "text.color": "#e0e0e0",
        "axes.labelcolor": "#cccccc",
        "xtick.color": "#aaaaaa",
        "ytick.color": "#aaaaaa",
    },
    ChartStyle.MINIMAL: {
        "figure.facecolor": "#ffffff",
        "axes.facecolor": "#ffffff",
        "axes.edgecolor": "#dddddd",
        "axes.grid": False,
        "text.color": "#333333",
        "axes.labelcolor": "#333333",
        "xtick.color": "#999999",
        "ytick.color": "#999999",
    },
    ChartStyle.PRINT: {
        "figure.facecolor": "#ffffff",
        "axes.facecolor": "#ffffff",
        "axes.edgecolor": "#000000",
        "axes.grid": True,
        "grid.color": "#cccccc",
        "grid.alpha": 0.4,
        "text.color": "#000000",
        "axes.labelcolor": "#000000",
        "xtick.color": "#000000",
        "ytick.color": "#000000",
    },
}

# Color constants
COLOR_BULL = "#26a69a"
COLOR_BEAR = "#ef5350"
COLOR_BUY_ARROW = "#00c853"
COLOR_SELL_ARROW = "#ff1744"
COLOR_VOLUME_UP = "#26a69a80"
COLOR_VOLUME_DOWN = "#ef535080"
COLOR_SMA = "#1976d2"
COLOR_EMA = "#ff9800"
COLOR_BB_FILL = "#bbdefb40"
COLOR_BB_LINE = "#90caf9"
COLOR_SUPPORT = "#4caf50"
COLOR_RESISTANCE = "#f44336"


@dataclass
class ChartConfig:
    """Configuration for chart rendering."""
    width: float = 14.0
    height: float = 8.0
    dpi: int = 150
    style: ChartStyle = ChartStyle.DEFAULT
    title_fontsize: int = 14
    label_fontsize: int = 10
    tick_fontsize: int = 8
    legend_fontsize: int = 9


class ChartGenerator:
    """
    Main charting engine for financial market visualization.

    Produces OHLC/candlestick charts with optional overlays for technical
    indicators, volume bars, support/resistance levels, and trade signals.
    Supports multi-panel layouts and export to PNG, SVG, and PDF.

    Example::

        gen = ChartGenerator(config=ChartConfig(style=ChartStyle.DARK))
        fig = gen.candlestick(
            df,
            overlays={"sma": [20, 50], "bollinger": 20},
            volume=True,
            signals=signals_df,
        )
        gen.save(fig, "chart.png")
    """

    def __init__(self, config: Optional[ChartConfig] = None):
        """
        Initialize ChartGenerator.

        Args:
            config: Chart configuration. Uses defaults if not provided.
        """
        self.config = config or ChartConfig()
        logger.info("ChartGenerator initialized with style=%s", self.config.style.value)

    def _apply_style(self) -> None:
        """Apply the configured visual style to matplotlib."""
        if MPL_AVAILABLE:
            plt.rcParams.update(_STYLE_CONFIG.get(self.config.style, {}))

    @_require_matplotlib
    def candlestick(
        self,
        df: pd.DataFrame,
        overlays: Optional[Dict[str, Any]] = None,
        volume: bool = True,
        signals: Optional[pd.DataFrame] = None,
        support_levels: Optional[List[float]] = None,
        resistance_levels: Optional[List[float]] = None,
        title: str = "",
    ) -> Figure:
        """
        Create a candlestick chart with optional overlays and panels.

        Args:
            df: DataFrame with columns 'open', 'high', 'low', 'close'
                and optionally 'volume'. Index should be DatetimeIndex.
            overlays: Dict of overlay configs. Supported keys:
                - "sma": list of periods, e.g. [20, 50]
                - "ema": list of periods
                - "bollinger": period (int) for Bollinger Bands
            volume: Whether to include a volume sub-panel.
            signals: DataFrame with columns 'date', 'side' ('buy'/'sell'),
                     and optionally 'price'.
            support_levels: Horizontal price levels to draw as support.
            resistance_levels: Horizontal price levels to draw as resistance.
            title: Chart title.

        Returns:
            matplotlib Figure object.
        """
        self._apply_style()
        overlays = overlays or {}

        n_panels = 1 + int(volume)
        height_ratios = [3, 1] if volume else [1]

        fig, axes = plt.subplots(
            n_panels, 1,
            figsize=(self.config.width, self.config.height),
            dpi=self.config.dpi,
            gridspec_kw={"height_ratios": height_ratios},
            sharex=True,
        )
        if n_panels == 1:
            axes = [axes]

        ax_price = axes[0]
        ax_vol = axes[1] if volume else None

        # --- Candlesticks ---
        self._draw_candlesticks(ax_price, df)

        # --- Overlays ---
        close = df["close"]
        sma_colors = ["#1976d2", "#f57c00", "#7b1fa2", "#388e3c"]
        for i, period in enumerate(overlays.get("sma", [])):
            sma = close.rolling(window=period).mean()
            ax_price.plot(
                df.index, sma,
                linewidth=1.2,
                label=f"SMA {period}",
                color=sma_colors[i % len(sma_colors)],
            )

        ema_colors = ["#ff9800", "#e91e63", "#00bcd4"]
        for i, period in enumerate(overlays.get("ema", [])):
            ema = close.ewm(span=period, adjust=False).mean()
            ax_price.plot(
                df.index, ema,
                linewidth=1.2,
                linestyle="--",
                label=f"EMA {period}",
                color=ema_colors[i % len(ema_colors)],
            )

        bb_period = overlays.get("bollinger")
        if bb_period:
            mid = close.rolling(window=bb_period).mean()
            std = close.rolling(window=bb_period).std()
            upper = mid + 2 * std
            lower = mid - 2 * std
            ax_price.plot(df.index, upper, linewidth=0.8, color=COLOR_BB_LINE, label="BB Upper")
            ax_price.plot(df.index, lower, linewidth=0.8, color=COLOR_BB_LINE, label="BB Lower")
            ax_price.fill_between(df.index, lower, upper, color=COLOR_BB_FILL)

        # --- Support / Resistance ---
        for level in (support_levels or []):
            ax_price.axhline(y=level, color=COLOR_SUPPORT, linewidth=0.9, linestyle="--", alpha=0.7)
        for level in (resistance_levels or []):
            ax_price.axhline(y=level, color=COLOR_RESISTANCE, linewidth=0.9, linestyle="--", alpha=0.7)

        # --- Signals ---
        if signals is not None and not signals.empty:
            self._draw_signals(ax_price, df, signals)

        # --- Volume ---
        if volume and "volume" in df.columns and ax_vol is not None:
            self._draw_volume(ax_vol, df)

        # --- Formatting ---
        ax_price.set_title(title, fontsize=self.config.title_fontsize, fontweight="bold")
        ax_price.set_ylabel("Price", fontsize=self.config.label_fontsize)
        ax_price.legend(fontsize=self.config.legend_fontsize, loc="upper left")
        ax_price.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))

        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        axes[-1].tick_params(axis="x", rotation=30)
        fig.tight_layout()
        logger.info("Candlestick chart created (%d bars)", len(df))
        return fig

    def _draw_candlesticks(self, ax, df: pd.DataFrame) -> None:
        """Render candlestick bodies and wicks on the given axes."""
        up = df["close"] >= df["open"]
        down = ~up
        width = 0.6
        width2 = 0.15

        # Up candles
        ax.bar(df.index[up], (df["close"] - df["open"])[up], width,
               bottom=df["open"][up], color=COLOR_BULL, edgecolor=COLOR_BULL)
        ax.bar(df.index[up], (df["high"] - df["close"])[up], width2,
               bottom=df["close"][up], color=COLOR_BULL)
        ax.bar(df.index[up], (df["open"] - df["low"])[up], width2,
               bottom=df["low"][up], color=COLOR_BULL)

        # Down candles
        ax.bar(df.index[down], (df["close"] - df["open"])[down], width,
               bottom=df["open"][down], color=COLOR_BEAR, edgecolor=COLOR_BEAR)
        ax.bar(df.index[down], (df["high"] - df["open"])[down], width2,
               bottom=df["open"][down], color=COLOR_BEAR)
        ax.bar(df.index[down], (df["close"] - df["low"])[down], width2,
               bottom=df["low"][down], color=COLOR_BEAR)

    def _draw_volume(self, ax, df: pd.DataFrame) -> None:
        """Render color-coded volume bars."""
        up = df["close"] >= df["open"]
        colors = np.where(up, COLOR_VOLUME_UP, COLOR_VOLUME_DOWN)
        ax.bar(df.index, df["volume"], width=0.6, color=colors)
        ax.set_ylabel("Volume", fontsize=self.config.label_fontsize)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda x, _: f"{x / 1e6:.1f}M" if x >= 1e6 else f"{x / 1e3:.0f}K"
        ))

    def _draw_signals(self, ax, df: pd.DataFrame, signals: pd.DataFrame) -> None:
        """Render buy/sell signal markers on the price chart."""
        for _, sig in signals.iterrows():
            date = sig.get("date", sig.name)
            side = sig["side"].lower()
            price = sig.get("price", None)
            if price is None and date in df.index:
                price = df.loc[date, "low" if side == "buy" else "high"]
            if price is None:
                continue

            marker = "^" if side == "buy" else "v"
            color = COLOR_BUY_ARROW if side == "buy" else COLOR_SELL_ARROW
            ax.scatter(date, price, marker=marker, color=color, s=100,
                       zorder=5, edgecolors="white", linewidths=0.5)

    @_require_matplotlib
    def indicator_panel(
        self,
        df: pd.DataFrame,
        indicators: Dict[str, pd.Series],
        title: str = "Indicators",
    ) -> Figure:
        """
        Create a standalone multi-line indicator panel.

        Args:
            df: DataFrame whose index provides the x-axis dates.
            indicators: Mapping of label -> Series to plot.
            title: Chart title.

        Returns:
            matplotlib Figure.
        """
        self._apply_style()
        fig, ax = plt.subplots(figsize=(self.config.width, 4), dpi=self.config.dpi)
        for label, series in indicators.items():
            ax.plot(df.index, series, linewidth=1.2, label=label)
        ax.set_title(title, fontsize=self.config.title_fontsize)
        ax.legend(fontsize=self.config.legend_fontsize)
        fig.tight_layout()
        logger.info("Indicator panel created with %d series", len(indicators))
        return fig

    @staticmethod
    def save(fig, filepath: str, **kwargs) -> None:
        """
        Save a figure to disk.

        Args:
            fig: matplotlib Figure to save.
            filepath: Output path. Extension determines format (png/svg/pdf).
            **kwargs: Extra arguments passed to ``fig.savefig``.
        """
        if not MPL_AVAILABLE:
            raise ImportError("matplotlib is required to save figures.")
        fig.savefig(filepath, bbox_inches="tight", **kwargs)
        plt.close(fig)
        logger.info("Chart saved to %s", filepath)

    def to_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Data-only fallback when matplotlib is unavailable.

        Returns a dictionary of OHLCV data suitable for JSON serialization
        or use with an alternative rendering library.

        Args:
            df: DataFrame with OHLCV data.

        Returns:
            Dictionary with dates, ohlc arrays, and volume.
        """
        result: Dict[str, Any] = {
            "dates": df.index.strftime("%Y-%m-%d").tolist(),
            "open": df["open"].tolist(),
            "high": df["high"].tolist(),
            "low": df["low"].tolist(),
            "close": df["close"].tolist(),
        }
        if "volume" in df.columns:
            result["volume"] = df["volume"].tolist()
        logger.info("Data-only export created (%d rows)", len(df))
        return result


class PerformanceCharts:
    """
    Trading performance visualization suite.

    Generates equity curves, drawdown plots, returns distributions,
    monthly heatmaps, rolling Sharpe ratios, and trade-level scatter plots.

    Example::

        perf = PerformanceCharts()
        fig = perf.equity_curve(equity_series, benchmark=bench_series)
        perf.save(fig, "equity.png")
    """

    def __init__(self, config: Optional[ChartConfig] = None):
        self.config = config or ChartConfig()
        self._gen = ChartGenerator(self.config)
        logger.info("PerformanceCharts initialized")

    @_require_matplotlib
    def equity_curve(
        self,
        equity: pd.Series,
        benchmark: Optional[pd.Series] = None,
        title: str = "Equity Curve",
    ) -> Figure:
        """
        Plot cumulative equity over time.

        Args:
            equity: Series of portfolio values indexed by date.
            benchmark: Optional benchmark series for comparison.
            title: Chart title.

        Returns:
            matplotlib Figure.
        """
        self._gen._apply_style()
        fig, ax = plt.subplots(figsize=(self.config.width, self.config.height),
                               dpi=self.config.dpi)
        ax.plot(equity.index, equity.values, linewidth=1.5, color="#1976d2",
                label="Strategy")
        if benchmark is not None:
            ax.plot(benchmark.index, benchmark.values, linewidth=1.2,
                    color="#9e9e9e", linestyle="--", label="Benchmark")
        ax.fill_between(equity.index, equity.values, alpha=0.08, color="#1976d2")
        ax.set_title(title, fontsize=self.config.title_fontsize, fontweight="bold")
        ax.set_ylabel("Equity", fontsize=self.config.label_fontsize)
        ax.legend(fontsize=self.config.legend_fontsize)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda x, _: f"${x:,.0f}"
        ))
        fig.tight_layout()
        logger.info("Equity curve plotted (%d points)", len(equity))
        return fig

    @_require_matplotlib
    def drawdown(self, equity: pd.Series, title: str = "Drawdown") -> Figure:
        """
        Plot underwater / drawdown curve.

        Args:
            equity: Series of portfolio values indexed by date.
            title: Chart title.

        Returns:
            matplotlib Figure.
        """
        self._gen._apply_style()
        running_max = equity.cummax()
        dd = (equity - running_max) / running_max * 100

        fig, ax = plt.subplots(figsize=(self.config.width, 4), dpi=self.config.dpi)
        ax.fill_between(dd.index, dd.values, 0, color="#ef5350", alpha=0.4)
        ax.plot(dd.index, dd.values, linewidth=0.8, color="#c62828")
        ax.set_title(title, fontsize=self.config.title_fontsize, fontweight="bold")
        ax.set_ylabel("Drawdown (%)", fontsize=self.config.label_fontsize)
        ax.set_ylim(dd.min() * 1.15, 1)
        fig.tight_layout()
        logger.info("Drawdown chart plotted (max dd=%.2f%%)", dd.min())
        return fig

    @_require_matplotlib
    def returns_distribution(
        self,
        returns: pd.Series,
        bins: int = 50,
        title: str = "Returns Distribution",
    ) -> Figure:
        """
        Histogram of period returns with normal distribution overlay.

        Args:
            returns: Series of period returns (e.g. daily).
            bins: Number of histogram bins.
            title: Chart title.

        Returns:
            matplotlib Figure.
        """
        self._gen._apply_style()
        fig, ax = plt.subplots(figsize=(self.config.width, 5), dpi=self.config.dpi)
        ax.hist(returns.dropna(), bins=bins, color="#42a5f5", edgecolor="white",
                alpha=0.8, density=True)

        # Normal overlay
        mu, sigma = returns.mean(), returns.std()
        x = np.linspace(returns.min(), returns.max(), 200)
        pdf = (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
        ax.plot(x, pdf, linewidth=1.5, color="#c62828", label="Normal fit")

        ax.axvline(mu, color="#1b5e20", linestyle="--", linewidth=1, label=f"Mean={mu:.4f}")
        ax.set_title(title, fontsize=self.config.title_fontsize, fontweight="bold")
        ax.set_xlabel("Return", fontsize=self.config.label_fontsize)
        ax.set_ylabel("Density", fontsize=self.config.label_fontsize)
        ax.legend(fontsize=self.config.legend_fontsize)
        fig.tight_layout()
        logger.info("Returns distribution plotted (n=%d, mean=%.4f)", len(returns), mu)
        return fig

    @_require_matplotlib
    def monthly_heatmap(
        self,
        returns: pd.Series,
        title: str = "Monthly Returns (%)",
    ) -> Figure:
        """
        Monthly returns heatmap with year rows and month columns.

        Args:
            returns: Daily returns series with DatetimeIndex.
            title: Chart title.

        Returns:
            matplotlib Figure.
        """
        self._gen._apply_style()
        monthly = returns.resample("ME").apply(lambda x: (1 + x).prod() - 1) * 100
        pivot = pd.DataFrame({
            "year": monthly.index.year,
            "month": monthly.index.month,
            "ret": monthly.values,
        })
        table = pivot.pivot(index="year", columns="month", values="ret")
        # Reindex to ensure all 12 months are present
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        table = table.reindex(columns=range(1, 13))
        table.columns = month_names

        fig, ax = plt.subplots(figsize=(self.config.width, max(3, len(table) * 0.6)),
                               dpi=self.config.dpi)
        cmap = LinearSegmentedColormap.from_list("rg", [COLOR_BEAR, "#ffffff", COLOR_BULL])
        vmax = max(abs(table.min().min()), abs(table.max().max()), 1)
        im = ax.imshow(table.values, cmap=cmap, aspect="auto",
                       vmin=-vmax, vmax=vmax)

        ax.set_xticks(range(len(table.columns)))
        ax.set_xticklabels(table.columns, fontsize=self.config.tick_fontsize)
        ax.set_yticks(range(len(table.index)))
        ax.set_yticklabels(table.index, fontsize=self.config.tick_fontsize)

        for i in range(len(table.index)):
            for j in range(len(table.columns)):
                val = table.iloc[i, j]
                if not np.isnan(val):
                    ax.text(j, i, f"{val:.1f}", ha="center", va="center",
                            fontsize=self.config.tick_fontsize,
                            color="black" if abs(val) < vmax * 0.6 else "white")

        fig.colorbar(im, ax=ax, label="Return (%)", shrink=0.8)
        ax.set_title(title, fontsize=self.config.title_fontsize, fontweight="bold")
        fig.tight_layout()
        logger.info("Monthly heatmap plotted (%d years)", len(table))
        return fig

    @_require_matplotlib
    def rolling_sharpe(
        self,
        returns: pd.Series,
        window: int = 63,
        risk_free_rate: float = 0.0,
        title: str = "Rolling Sharpe Ratio",
    ) -> Figure:
        """
        Plot rolling annualized Sharpe ratio.

        Args:
            returns: Daily returns series.
            window: Rolling window in trading days (default 63 ~ 3 months).
            risk_free_rate: Daily risk-free rate.
            title: Chart title.

        Returns:
            matplotlib Figure.
        """
        self._gen._apply_style()
        excess = returns - risk_free_rate
        rolling_mean = excess.rolling(window).mean()
        rolling_std = excess.rolling(window).std()
        sharpe = (rolling_mean / rolling_std) * np.sqrt(252)

        fig, ax = plt.subplots(figsize=(self.config.width, 4), dpi=self.config.dpi)
        ax.plot(sharpe.index, sharpe.values, linewidth=1.2, color="#1976d2")
        ax.axhline(0, color="#999999", linewidth=0.8, linestyle="--")
        ax.fill_between(sharpe.index, sharpe.values, 0,
                        where=sharpe.values >= 0, color=COLOR_BULL, alpha=0.2)
        ax.fill_between(sharpe.index, sharpe.values, 0,
                        where=sharpe.values < 0, color=COLOR_BEAR, alpha=0.2)
        ax.set_title(title, fontsize=self.config.title_fontsize, fontweight="bold")
        ax.set_ylabel("Sharpe Ratio", fontsize=self.config.label_fontsize)
        fig.tight_layout()
        logger.info("Rolling Sharpe plotted (window=%d)", window)
        return fig

    @_require_matplotlib
    def win_loss_chart(
        self,
        trades: pd.DataFrame,
        title: str = "Win / Loss Distribution",
    ) -> Figure:
        """
        Bar chart of winning vs losing trades.

        Args:
            trades: DataFrame with a 'pnl' column.
            title: Chart title.

        Returns:
            matplotlib Figure.
        """
        self._gen._apply_style()
        wins = trades[trades["pnl"] > 0]["pnl"]
        losses = trades[trades["pnl"] <= 0]["pnl"]

        fig, ax = plt.subplots(figsize=(self.config.width, 5), dpi=self.config.dpi)
        x = range(len(trades))
        colors = [COLOR_BULL if p > 0 else COLOR_BEAR for p in trades["pnl"]]
        ax.bar(x, trades["pnl"], color=colors, edgecolor="white", linewidth=0.3)
        ax.axhline(0, color="#333333", linewidth=0.8)
        ax.set_title(title, fontsize=self.config.title_fontsize, fontweight="bold")
        ax.set_xlabel("Trade #", fontsize=self.config.label_fontsize)
        ax.set_ylabel("P&L", fontsize=self.config.label_fontsize)

        stats_text = (
            f"Wins: {len(wins)}  Losses: {len(losses)}\n"
            f"Avg Win: {wins.mean():.2f}  Avg Loss: {losses.mean():.2f}"
        )
        ax.text(0.02, 0.95, stats_text, transform=ax.transAxes,
                fontsize=self.config.tick_fontsize, verticalalignment="top",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="white", alpha=0.8))
        fig.tight_layout()
        logger.info("Win/loss chart plotted (%d trades)", len(trades))
        return fig

    @_require_matplotlib
    def trade_scatter(
        self,
        trades: pd.DataFrame,
        title: str = "Trade P&L Scatter",
    ) -> Figure:
        """
        Scatter plot of trade P&L vs trade duration or index.

        Args:
            trades: DataFrame with 'pnl' and optionally 'duration_days'.
            title: Chart title.

        Returns:
            matplotlib Figure.
        """
        self._gen._apply_style()
        fig, ax = plt.subplots(figsize=(self.config.width, 5), dpi=self.config.dpi)
        x_vals = trades.get("duration_days", pd.Series(range(len(trades))))
        colors = [COLOR_BULL if p > 0 else COLOR_BEAR for p in trades["pnl"]]
        ax.scatter(x_vals, trades["pnl"], c=colors, s=40, alpha=0.7, edgecolors="white")
        ax.axhline(0, color="#999999", linewidth=0.8, linestyle="--")
        x_label = "Duration (days)" if "duration_days" in trades.columns else "Trade #"
        ax.set_xlabel(x_label, fontsize=self.config.label_fontsize)
        ax.set_ylabel("P&L", fontsize=self.config.label_fontsize)
        ax.set_title(title, fontsize=self.config.title_fontsize, fontweight="bold")
        fig.tight_layout()
        logger.info("Trade scatter plotted (%d trades)", len(trades))
        return fig

    @_require_matplotlib
    def cumulative_pnl(
        self,
        trades: pd.DataFrame,
        title: str = "Cumulative P&L",
    ) -> Figure:
        """
        Cumulative P&L line over trade sequence.

        Args:
            trades: DataFrame with 'pnl' and optionally 'exit_date'.
            title: Chart title.

        Returns:
            matplotlib Figure.
        """
        self._gen._apply_style()
        cum = trades["pnl"].cumsum()
        x_vals = trades.get("exit_date", pd.Series(range(len(trades))))

        fig, ax = plt.subplots(figsize=(self.config.width, 5), dpi=self.config.dpi)
        ax.plot(x_vals, cum.values, linewidth=1.5, color="#1976d2")
        ax.fill_between(x_vals, cum.values, alpha=0.1, color="#1976d2")
        ax.axhline(0, color="#999999", linewidth=0.8, linestyle="--")
        ax.set_title(title, fontsize=self.config.title_fontsize, fontweight="bold")
        ax.set_ylabel("Cumulative P&L", fontsize=self.config.label_fontsize)
        fig.tight_layout()
        logger.info("Cumulative P&L plotted (total=%.2f)", cum.iloc[-1])
        return fig

    def save(self, fig, filepath: str, **kwargs) -> None:
        """Save figure to file. Delegates to ChartGenerator.save."""
        ChartGenerator.save(fig, filepath, **kwargs)

    def to_data(self, equity: pd.Series) -> Dict[str, Any]:
        """
        Data-only fallback for performance metrics.

        Args:
            equity: Equity curve series.

        Returns:
            Dictionary with equity, drawdown, and summary statistics.
        """
        running_max = equity.cummax()
        dd = (equity - running_max) / running_max
        returns = equity.pct_change().dropna()
        return {
            "dates": equity.index.strftime("%Y-%m-%d").tolist(),
            "equity": equity.tolist(),
            "drawdown": dd.tolist(),
            "total_return": float((equity.iloc[-1] / equity.iloc[0]) - 1),
            "max_drawdown": float(dd.min()),
            "sharpe": float(returns.mean() / returns.std() * np.sqrt(252))
            if returns.std() > 0 else 0.0,
        }


class CorrelationVisualizer:
    """
    Correlation analysis charts for multi-asset portfolios.

    Produces correlation matrix heatmaps, rolling correlation time series,
    hierarchical clustering dendrograms, and network graphs.

    Example::

        viz = CorrelationVisualizer()
        fig = viz.correlation_matrix(returns_df)
    """

    def __init__(self, config: Optional[ChartConfig] = None):
        self.config = config or ChartConfig()
        self._gen = ChartGenerator(self.config)
        logger.info("CorrelationVisualizer initialized")

    @_require_matplotlib
    def correlation_matrix(
        self,
        returns: pd.DataFrame,
        method: str = "pearson",
        title: str = "Correlation Matrix",
    ) -> Figure:
        """
        Heatmap of pairwise asset correlations.

        Args:
            returns: DataFrame of asset returns (columns = assets).
            method: Correlation method ('pearson', 'spearman', 'kendall').
            title: Chart title.

        Returns:
            matplotlib Figure.
        """
        self._gen._apply_style()
        corr = returns.corr(method=method)
        n = len(corr)

        fig, ax = plt.subplots(
            figsize=(max(8, n * 0.8), max(6, n * 0.7)),
            dpi=self.config.dpi,
        )
        cmap = LinearSegmentedColormap.from_list("rg", [COLOR_BEAR, "#ffffff", COLOR_BULL])
        im = ax.imshow(corr.values, cmap=cmap, vmin=-1, vmax=1, aspect="auto")

        ax.set_xticks(range(n))
        ax.set_xticklabels(corr.columns, rotation=45, ha="right",
                           fontsize=self.config.tick_fontsize)
        ax.set_yticks(range(n))
        ax.set_yticklabels(corr.index, fontsize=self.config.tick_fontsize)

        for i in range(n):
            for j in range(n):
                val = corr.iloc[i, j]
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        fontsize=self.config.tick_fontsize,
                        color="white" if abs(val) > 0.6 else "black")

        fig.colorbar(im, ax=ax, label="Correlation", shrink=0.8)
        ax.set_title(title, fontsize=self.config.title_fontsize, fontweight="bold")
        fig.tight_layout()
        logger.info("Correlation matrix plotted (%d assets)", n)
        return fig

    @_require_matplotlib
    def rolling_correlation(
        self,
        returns: pd.DataFrame,
        asset_a: str,
        asset_b: str,
        window: int = 63,
        title: Optional[str] = None,
    ) -> Figure:
        """
        Rolling correlation between two assets over time.

        Args:
            returns: DataFrame of asset returns.
            asset_a: Column name of first asset.
            asset_b: Column name of second asset.
            window: Rolling window size in periods.
            title: Chart title (auto-generated if None).

        Returns:
            matplotlib Figure.
        """
        self._gen._apply_style()
        title = title or f"Rolling {window}-day Correlation: {asset_a} vs {asset_b}"
        rolling_corr = returns[asset_a].rolling(window).corr(returns[asset_b])

        fig, ax = plt.subplots(figsize=(self.config.width, 4), dpi=self.config.dpi)
        ax.plot(rolling_corr.index, rolling_corr.values, linewidth=1.2, color="#1976d2")
        ax.axhline(0, color="#999999", linewidth=0.8, linestyle="--")
        ax.axhline(1, color="#cccccc", linewidth=0.5, linestyle=":")
        ax.axhline(-1, color="#cccccc", linewidth=0.5, linestyle=":")
        ax.fill_between(rolling_corr.index, rolling_corr.values, 0,
                        alpha=0.15, color="#1976d2")
        ax.set_ylim(-1.05, 1.05)
        ax.set_title(title, fontsize=self.config.title_fontsize, fontweight="bold")
        ax.set_ylabel("Correlation", fontsize=self.config.label_fontsize)
        fig.tight_layout()
        logger.info("Rolling correlation plotted (%s vs %s, window=%d)",
                     asset_a, asset_b, window)
        return fig

    @_require_matplotlib
    def dendrogram_chart(
        self,
        returns: pd.DataFrame,
        method: str = "ward",
        title: str = "Hierarchical Clustering",
    ) -> Figure:
        """
        Dendrogram for hierarchical clustering of assets.

        Requires scipy. Falls back to an error message if not available.

        Args:
            returns: DataFrame of asset returns.
            method: Linkage method (ward, single, complete, average).
            title: Chart title.

        Returns:
            matplotlib Figure.

        Raises:
            ImportError: If scipy is not installed.
        """
        if not SCIPY_AVAILABLE:
            raise ImportError(
                "scipy is required for dendrogram charts. "
                "Install it with: pip install scipy"
            )
        self._gen._apply_style()
        corr = returns.corr()
        # Convert correlation to distance
        dist = np.clip(1 - corr.values, 0, 2)
        np.fill_diagonal(dist, 0)
        dist = (dist + dist.T) / 2  # ensure symmetry
        condensed = squareform(dist)
        linked = linkage(condensed, method=method)

        fig, ax = plt.subplots(figsize=(self.config.width, 5), dpi=self.config.dpi)
        dendrogram(linked, labels=corr.columns.tolist(), ax=ax,
                   leaf_rotation=45, leaf_font_size=self.config.tick_fontsize)
        ax.set_title(title, fontsize=self.config.title_fontsize, fontweight="bold")
        ax.set_ylabel("Distance", fontsize=self.config.label_fontsize)
        fig.tight_layout()
        logger.info("Dendrogram plotted (%d assets)", len(corr))
        return fig

    @_require_matplotlib
    def network_graph(
        self,
        returns: pd.DataFrame,
        threshold: float = 0.5,
        title: str = "Correlation Network",
    ) -> Figure:
        """
        Network graph where edges represent correlations above threshold.

        Uses a simple spring-layout algorithm (no networkx dependency).

        Args:
            returns: DataFrame of asset returns.
            threshold: Minimum absolute correlation to draw an edge.
            title: Chart title.

        Returns:
            matplotlib Figure.
        """
        self._gen._apply_style()
        corr = returns.corr()
        assets = corr.columns.tolist()
        n = len(assets)

        # Circular layout
        angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
        positions = {a: (np.cos(ang), np.sin(ang)) for a, ang in zip(assets, angles)}

        fig, ax = plt.subplots(figsize=(self.config.height, self.config.height),
                               dpi=self.config.dpi)

        # Draw edges
        for i in range(n):
            for j in range(i + 1, n):
                val = corr.iloc[i, j]
                if abs(val) >= threshold:
                    p1 = positions[assets[i]]
                    p2 = positions[assets[j]]
                    color = COLOR_BULL if val > 0 else COLOR_BEAR
                    ax.plot([p1[0], p2[0]], [p1[1], p2[1]],
                            color=color, linewidth=abs(val) * 3, alpha=0.5)

        # Draw nodes
        for asset, (x, y) in positions.items():
            ax.scatter(x, y, s=300, color="#1976d2", zorder=5, edgecolors="white")
            ax.text(x, y + 0.12, asset, ha="center", va="bottom",
                    fontsize=self.config.tick_fontsize, fontweight="bold")

        ax.set_xlim(-1.5, 1.5)
        ax.set_ylim(-1.5, 1.5)
        ax.set_aspect("equal")
        ax.set_title(title, fontsize=self.config.title_fontsize, fontweight="bold")
        ax.axis("off")
        fig.tight_layout()
        logger.info("Network graph plotted (%d assets, threshold=%.2f)", n, threshold)
        return fig

    def save(self, fig, filepath: str, **kwargs) -> None:
        """Save figure to file."""
        ChartGenerator.save(fig, filepath, **kwargs)

    def to_data(self, returns: pd.DataFrame, method: str = "pearson") -> Dict[str, Any]:
        """
        Data-only fallback: return raw correlation matrix.

        Args:
            returns: DataFrame of asset returns.
            method: Correlation method.

        Returns:
            Dictionary with assets and correlation values.
        """
        corr = returns.corr(method=method)
        return {
            "assets": corr.columns.tolist(),
            "correlation_matrix": corr.values.tolist(),
        }


class RiskVisualizer:
    """
    Risk metrics visualization for portfolio analysis.

    Provides VaR cone charts, risk contribution breakdowns, efficient
    frontier plots, Monte Carlo simulation fans, and stress test impact bars.

    Example::

        risk_viz = RiskVisualizer()
        fig = risk_viz.var_cone(returns, horizon=30)
    """

    def __init__(self, config: Optional[ChartConfig] = None):
        self.config = config or ChartConfig()
        self._gen = ChartGenerator(self.config)
        logger.info("RiskVisualizer initialized")

    @_require_matplotlib
    def var_cone(
        self,
        returns: pd.Series,
        horizon: int = 30,
        confidence_levels: Optional[List[float]] = None,
        initial_value: float = 100.0,
        title: str = "Value-at-Risk Cone",
    ) -> Figure:
        """
        VaR cone chart projecting portfolio value with confidence bands.

        Args:
            returns: Historical daily returns.
            horizon: Projection horizon in days.
            confidence_levels: List of confidence levels (default [0.95, 0.99]).
            initial_value: Starting portfolio value.
            title: Chart title.

        Returns:
            matplotlib Figure.
        """
        self._gen._apply_style()
        confidence_levels = confidence_levels or [0.95, 0.99]
        mu = returns.mean()
        sigma = returns.std()

        days = np.arange(1, horizon + 1)
        expected = initial_value * np.exp(mu * days)

        fig, ax = plt.subplots(figsize=(self.config.width, self.config.height),
                               dpi=self.config.dpi)
        ax.plot(days, expected, linewidth=1.5, color="#1976d2", label="Expected")

        fill_colors = ["#bbdefb", "#90caf9", "#64b5f6"]
        for idx, cl in enumerate(sorted(confidence_levels)):
            from scipy.stats import norm as _norm
            z = _norm.ppf(1 - cl)
            upper = initial_value * np.exp((mu * days) + (z * sigma * np.sqrt(days)))
            lower = initial_value * np.exp((mu * days) - (z * sigma * np.sqrt(days)))
            fc = fill_colors[idx % len(fill_colors)]
            ax.fill_between(days, lower, upper, alpha=0.25, color=fc,
                            label=f"{cl:.0%} CI")

        ax.set_title(title, fontsize=self.config.title_fontsize, fontweight="bold")
        ax.set_xlabel("Days Ahead", fontsize=self.config.label_fontsize)
        ax.set_ylabel("Portfolio Value", fontsize=self.config.label_fontsize)
        ax.legend(fontsize=self.config.legend_fontsize)
        fig.tight_layout()
        logger.info("VaR cone plotted (horizon=%d days)", horizon)
        return fig

    @_require_matplotlib
    def risk_contribution(
        self,
        contributions: Dict[str, float],
        title: str = "Risk Contribution",
    ) -> Figure:
        """
        Pie chart of risk contribution by asset or factor.

        Args:
            contributions: Mapping of label -> contribution percentage.
            title: Chart title.

        Returns:
            matplotlib Figure.
        """
        self._gen._apply_style()
        labels = list(contributions.keys())
        values = list(contributions.values())

        fig, ax = plt.subplots(figsize=(self.config.height, self.config.height),
                               dpi=self.config.dpi)
        colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))
        wedges, texts, autotexts = ax.pie(
            values, labels=labels, autopct="%1.1f%%",
            colors=colors, startangle=90,
            textprops={"fontsize": self.config.tick_fontsize},
        )
        ax.set_title(title, fontsize=self.config.title_fontsize, fontweight="bold")
        fig.tight_layout()
        logger.info("Risk contribution pie plotted (%d components)", len(labels))
        return fig

    @_require_matplotlib
    def efficient_frontier(
        self,
        returns_range: np.ndarray,
        volatility_range: np.ndarray,
        sharpe_ratios: Optional[np.ndarray] = None,
        current_portfolio: Optional[Tuple[float, float]] = None,
        title: str = "Efficient Frontier",
    ) -> Figure:
        """
        Efficient frontier scatter/line plot.

        Args:
            returns_range: Array of expected returns for each portfolio.
            volatility_range: Array of volatilities for each portfolio.
            sharpe_ratios: Optional Sharpe ratios for color coding.
            current_portfolio: Tuple (vol, ret) for the current portfolio marker.
            title: Chart title.

        Returns:
            matplotlib Figure.
        """
        self._gen._apply_style()
        fig, ax = plt.subplots(figsize=(self.config.width, self.config.height),
                               dpi=self.config.dpi)

        if sharpe_ratios is not None:
            sc = ax.scatter(volatility_range, returns_range, c=sharpe_ratios,
                            cmap="viridis", s=10, alpha=0.6)
            fig.colorbar(sc, ax=ax, label="Sharpe Ratio", shrink=0.8)
        else:
            ax.scatter(volatility_range, returns_range, c="#1976d2", s=10, alpha=0.5)

        if current_portfolio is not None:
            ax.scatter(*current_portfolio, c="#ff1744", s=200, marker="*",
                       zorder=5, label="Current Portfolio", edgecolors="white")
            ax.legend(fontsize=self.config.legend_fontsize)

        ax.set_title(title, fontsize=self.config.title_fontsize, fontweight="bold")
        ax.set_xlabel("Volatility (Annualized)", fontsize=self.config.label_fontsize)
        ax.set_ylabel("Expected Return (Annualized)", fontsize=self.config.label_fontsize)
        fig.tight_layout()
        logger.info("Efficient frontier plotted (%d portfolios)", len(returns_range))
        return fig

    @_require_matplotlib
    def monte_carlo_fan(
        self,
        returns: pd.Series,
        n_simulations: int = 500,
        horizon: int = 252,
        initial_value: float = 100.0,
        title: str = "Monte Carlo Simulation",
    ) -> Figure:
        """
        Fan chart from Monte Carlo simulation of future paths.

        Args:
            returns: Historical daily returns for sampling parameters.
            n_simulations: Number of simulated paths.
            horizon: Simulation horizon in trading days.
            initial_value: Starting portfolio value.
            title: Chart title.

        Returns:
            matplotlib Figure.
        """
        self._gen._apply_style()
        mu = returns.mean()
        sigma = returns.std()
        rng = np.random.default_rng(42)

        # Simulate paths using geometric Brownian motion
        simulated = np.zeros((n_simulations, horizon))
        for i in range(n_simulations):
            daily_returns = rng.normal(mu, sigma, horizon)
            simulated[i] = initial_value * np.cumprod(1 + daily_returns)

        percentiles = [5, 25, 50, 75, 95]
        bands = {p: np.percentile(simulated, p, axis=0) for p in percentiles}

        fig, ax = plt.subplots(figsize=(self.config.width, self.config.height),
                               dpi=self.config.dpi)

        days = np.arange(1, horizon + 1)
        ax.fill_between(days, bands[5], bands[95], alpha=0.15, color="#1976d2",
                        label="5th-95th percentile")
        ax.fill_between(days, bands[25], bands[75], alpha=0.3, color="#1976d2",
                        label="25th-75th percentile")
        ax.plot(days, bands[50], linewidth=1.5, color="#1976d2", label="Median")
        ax.axhline(initial_value, color="#999999", linewidth=0.8, linestyle="--")

        ax.set_title(title, fontsize=self.config.title_fontsize, fontweight="bold")
        ax.set_xlabel("Trading Days", fontsize=self.config.label_fontsize)
        ax.set_ylabel("Portfolio Value", fontsize=self.config.label_fontsize)
        ax.legend(fontsize=self.config.legend_fontsize, loc="upper left")
        fig.tight_layout()
        logger.info("Monte Carlo fan plotted (%d sims, %d day horizon)",
                     n_simulations, horizon)
        return fig

    @_require_matplotlib
    def stress_test_impact(
        self,
        scenarios: Dict[str, float],
        title: str = "Stress Test Impact",
    ) -> Figure:
        """
        Horizontal bar chart of portfolio impact under stress scenarios.

        Args:
            scenarios: Mapping of scenario name -> portfolio impact (%).
            title: Chart title.

        Returns:
            matplotlib Figure.
        """
        self._gen._apply_style()
        labels = list(scenarios.keys())
        values = list(scenarios.values())

        fig, ax = plt.subplots(figsize=(self.config.width, max(4, len(labels) * 0.5)),
                               dpi=self.config.dpi)
        colors = [COLOR_BULL if v >= 0 else COLOR_BEAR for v in values]
        bars = ax.barh(labels, values, color=colors, edgecolor="white", height=0.6)

        for bar, val in zip(bars, values):
            x_pos = bar.get_width() + (0.3 if val >= 0 else -0.3)
            ax.text(x_pos, bar.get_y() + bar.get_height() / 2,
                    f"{val:+.1f}%", va="center",
                    fontsize=self.config.tick_fontsize,
                    ha="left" if val >= 0 else "right")

        ax.axvline(0, color="#333333", linewidth=0.8)
        ax.set_title(title, fontsize=self.config.title_fontsize, fontweight="bold")
        ax.set_xlabel("Portfolio Impact (%)", fontsize=self.config.label_fontsize)
        fig.tight_layout()
        logger.info("Stress test chart plotted (%d scenarios)", len(labels))
        return fig

    def save(self, fig, filepath: str, **kwargs) -> None:
        """Save figure to file."""
        ChartGenerator.save(fig, filepath, **kwargs)

    def to_data(
        self,
        returns: pd.Series,
        horizon: int = 30,
    ) -> Dict[str, Any]:
        """
        Data-only fallback for risk metrics.

        Args:
            returns: Daily returns series.
            horizon: Projection horizon.

        Returns:
            Dictionary with VaR estimates and basic risk stats.
        """
        mu = returns.mean()
        sigma = returns.std()
        var_95 = mu - 1.645 * sigma
        var_99 = mu - 2.326 * sigma
        return {
            "daily_var_95": float(var_95),
            "daily_var_99": float(var_99),
            "horizon_days": horizon,
            "annualized_vol": float(sigma * np.sqrt(252)),
            "daily_mean": float(mu),
            "daily_std": float(sigma),
        }


class DashboardGenerator:
    """
    Multi-chart dashboard builder.

    Combines multiple chart types into configurable grid layouts and exports
    them as single images or standalone HTML files.

    Example::

        dash = DashboardGenerator(layout=(2, 2))
        dash.add_chart(gen.candlestick(df), row=0, col=0)
        dash.add_chart(perf.equity_curve(equity), row=0, col=1)
        dash.add_chart(perf.drawdown(equity), row=1, col=0)
        dash.add_chart(risk.stress_test_impact(scenarios), row=1, col=1)
        fig = dash.render(title="Trading Dashboard")
        dash.save(fig, "dashboard.png")
    """

    def __init__(
        self,
        layout: Tuple[int, int] = (2, 2),
        config: Optional[ChartConfig] = None,
    ):
        """
        Initialize DashboardGenerator.

        Args:
            layout: Grid layout as (rows, cols).
            config: Chart configuration.
        """
        self.rows, self.cols = layout
        self.config = config or ChartConfig(width=18, height=12)
        self._panels: Dict[Tuple[int, int], Figure] = {}
        self._panel_titles: Dict[Tuple[int, int], str] = {}
        logger.info("DashboardGenerator initialized with %dx%d layout",
                     self.rows, self.cols)

    def add_chart(
        self,
        fig: Any,
        row: int,
        col: int,
        title: Optional[str] = None,
    ) -> None:
        """
        Add a chart figure to a specific grid position.

        Args:
            fig: matplotlib Figure (from any chart class).
            row: Row index (0-based).
            col: Column index (0-based).
            title: Optional subtitle for this panel.

        Raises:
            ValueError: If row/col is out of bounds.
        """
        if row >= self.rows or col >= self.cols:
            raise ValueError(
                f"Position ({row}, {col}) is out of bounds for "
                f"{self.rows}x{self.cols} layout"
            )
        self._panels[(row, col)] = fig
        if title:
            self._panel_titles[(row, col)] = title
        logger.debug("Chart added at position (%d, %d)", row, col)

    @_require_matplotlib
    def render(self, title: str = "Dashboard", height_ratios: Optional[List[float]] = None) -> Figure:
        """
        Render all added charts into a single dashboard figure.

        Each panel's axes content is re-drawn into the combined figure via
        image compositing for maximum compatibility.

        Args:
            title: Overall dashboard title.
            height_ratios: Optional height ratios for rows.

        Returns:
            matplotlib Figure containing all panels.
        """
        self._apply_style()
        fig = plt.figure(
            figsize=(self.config.width, self.config.height),
            dpi=self.config.dpi,
        )
        gs = gridspec.GridSpec(
            self.rows, self.cols, figure=fig,
            height_ratios=height_ratios or [1] * self.rows,
            hspace=0.35, wspace=0.3,
        )

        for (r, c), panel_fig in self._panels.items():
            ax = fig.add_subplot(gs[r, c])
            # Render panel figure to image buffer and composite
            buf = BytesIO()
            panel_fig.savefig(buf, format="png", bbox_inches="tight", dpi=self.config.dpi)
            buf.seek(0)

            from matplotlib.image import imread as _imread
            img = _imread(buf)
            buf.close()

            ax.imshow(img)
            ax.axis("off")
            if (r, c) in self._panel_titles:
                ax.set_title(self._panel_titles[(r, c)],
                             fontsize=self.config.label_fontsize, fontweight="bold")

        fig.suptitle(title, fontsize=self.config.title_fontsize + 2, fontweight="bold")
        logger.info("Dashboard rendered (%d panels in %dx%d grid)",
                     len(self._panels), self.rows, self.cols)
        return fig

    def _apply_style(self) -> None:
        """Apply configured style."""
        if MPL_AVAILABLE:
            plt.rcParams.update(_STYLE_CONFIG.get(self.config.style, {}))

    def save(self, fig, filepath: str, **kwargs) -> None:
        """Save the dashboard figure to file."""
        ChartGenerator.save(fig, filepath, **kwargs)

    def clear(self) -> None:
        """Remove all panels from the dashboard."""
        for fig in self._panels.values():
            if MPL_AVAILABLE:
                plt.close(fig)
        self._panels.clear()
        self._panel_titles.clear()
        logger.debug("Dashboard panels cleared")

    @_require_matplotlib
    def export_html(self, filepath: str, title: str = "Dashboard") -> None:
        """
        Export the dashboard as a standalone HTML file with embedded images.

        Each panel is embedded as a base64-encoded PNG in an HTML grid.

        Args:
            filepath: Output HTML file path.
            title: HTML page title.
        """
        import base64

        cells_html = []
        for r in range(self.rows):
            for c in range(self.cols):
                panel_fig = self._panels.get((r, c))
                if panel_fig is None:
                    cells_html.append("<div class='cell empty'></div>")
                    continue
                buf = BytesIO()
                panel_fig.savefig(buf, format="png", bbox_inches="tight",
                                  dpi=self.config.dpi)
                buf.seek(0)
                b64 = base64.b64encode(buf.read()).decode("utf-8")
                buf.close()
                sub = self._panel_titles.get((r, c), "")
                cells_html.append(
                    f"<div class='cell'>"
                    f"{'<h3>' + sub + '</h3>' if sub else ''}"
                    f"<img src='data:image/png;base64,{b64}'/>"
                    f"</div>"
                )

        html = f"""<!DOCTYPE html>
<html><head><meta charset='utf-8'><title>{title}</title>
<style>
body {{ font-family: Arial, sans-serif; background: #f5f5f5; margin: 20px; }}
h1 {{ text-align: center; color: #333; }}
.grid {{ display: grid; grid-template-columns: repeat({self.cols}, 1fr);
         gap: 12px; max-width: 1600px; margin: auto; }}
.cell img {{ width: 100%; border-radius: 4px; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }}
.cell h3 {{ text-align: center; margin: 4px 0; color: #555; }}
.cell.empty {{ min-height: 100px; }}
</style></head>
<body><h1>{title}</h1><div class='grid'>
{''.join(cells_html)}
</div></body></html>"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info("Dashboard exported to HTML: %s", filepath)

    def to_data(self) -> Dict[str, Any]:
        """
        Data-only fallback returning panel metadata.

        Returns:
            Dictionary describing the dashboard layout and populated cells.
        """
        return {
            "layout": [self.rows, self.cols],
            "panels": [
                {"row": r, "col": c, "title": self._panel_titles.get((r, c), "")}
                for (r, c) in sorted(self._panels.keys())
            ],
        }
