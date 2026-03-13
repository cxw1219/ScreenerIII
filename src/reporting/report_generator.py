"""
Report Generation Module for ScreenerIII

Provides comprehensive report generation capabilities including daily, weekly,
and monthly performance reports, HTML rendering, CSV export, data aggregation,
and automated scheduled reporting with optional email delivery.

Classes:
    - ReportGenerator: Main report engine with template-based generation
    - HTMLReportBuilder: Professional HTML report rendering with CSS styling
    - CSVExporter: Data export to CSV with custom column selection
    - PerformanceReportData: Report data aggregation and metric calculation
    - ScheduledReporter: Automated report scheduling and delivery

Author: ScreenerIII
License: MIT
"""

import csv
import io
import os
import json
import base64
import logging
import hashlib
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from enum import Enum
from pathlib import Path
from typing import (
    Any, Callable, Dict, List, Optional, Sequence, Tuple, Union
)

try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.mime.base import MIMEBase
    from email import encoders
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & small data holders
# ---------------------------------------------------------------------------

class ReportFrequency(Enum):
    """Frequency at which a report is generated."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class OutputFormat(Enum):
    """Supported report output formats."""
    HTML = "html"
    CSV = "csv"
    JSON = "json"
    TEXT = "text"


@dataclass
class ReportMetadata:
    """Metadata attached to every generated report."""
    report_id: str
    title: str
    frequency: ReportFrequency
    generated_at: datetime
    start_date: date
    end_date: date
    output_format: OutputFormat
    file_path: Optional[str] = None
    checksum: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize metadata to a plain dictionary."""
        return {
            "report_id": self.report_id,
            "title": self.title,
            "frequency": self.frequency.value,
            "generated_at": self.generated_at.isoformat(),
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "output_format": self.output_format.value,
            "file_path": self.file_path,
            "checksum": self.checksum,
        }


@dataclass
class EmailConfig:
    """Configuration for email delivery of reports."""
    smtp_host: str = "localhost"
    smtp_port: int = 587
    use_tls: bool = True
    username: str = ""
    password: str = ""
    from_address: str = ""
    to_addresses: List[str] = field(default_factory=list)
    subject_prefix: str = "[ScreenerIII]"


# ---------------------------------------------------------------------------
# PerformanceReportData
# ---------------------------------------------------------------------------

class PerformanceReportData:
    """Aggregates raw trading data into report-ready metrics and summaries.

    This class takes trade records, position snapshots, and price data, then
    computes daily, weekly, and monthly return series together with risk
    metrics, top/bottom performers, and trade statistics.

    Parameters
    ----------
    trades : pd.DataFrame
        DataFrame with columns: instrument, entry_time, exit_time,
        entry_price, exit_price, direction, quantity, pnl.
    positions : pd.DataFrame, optional
        Open-position snapshot with columns: instrument, direction,
        quantity, entry_price, current_price, unrealized_pnl.
    equity_curve : pd.Series, optional
        Time-indexed series of portfolio equity values.
    signals : pd.DataFrame, optional
        Signal history with columns: timestamp, instrument, signal_type,
        strength.
    """

    def __init__(
        self,
        trades: pd.DataFrame,
        positions: Optional[pd.DataFrame] = None,
        equity_curve: Optional[pd.Series] = None,
        signals: Optional[pd.DataFrame] = None,
    ) -> None:
        self.trades = trades.copy() if trades is not None else pd.DataFrame()
        self.positions = positions.copy() if positions is not None else pd.DataFrame()
        self.equity_curve = equity_curve.copy() if equity_curve is not None else pd.Series(dtype=float)
        self.signals = signals.copy() if signals is not None else pd.DataFrame()
        logger.info("PerformanceReportData initialized with %d trades", len(self.trades))

    # -- return aggregation ---------------------------------------------------

    def daily_returns(self) -> pd.Series:
        """Compute daily percentage returns from the equity curve.

        Returns
        -------
        pd.Series
            Daily returns indexed by date.
        """
        if self.equity_curve.empty:
            logger.warning("Equity curve is empty; returning empty daily returns")
            return pd.Series(dtype=float)
        returns = self.equity_curve.pct_change().dropna()
        returns.index = pd.to_datetime(returns.index)
        logger.debug("Computed %d daily return observations", len(returns))
        return returns

    def weekly_returns(self) -> pd.Series:
        """Aggregate daily returns into weekly returns.

        Returns
        -------
        pd.Series
            Weekly returns indexed by the last day of each week.
        """
        daily = self.daily_returns()
        if daily.empty:
            return pd.Series(dtype=float)
        weekly = (1 + daily).resample("W").prod() - 1
        logger.debug("Aggregated into %d weekly return observations", len(weekly))
        return weekly

    def monthly_returns(self) -> pd.Series:
        """Aggregate daily returns into monthly returns.

        Returns
        -------
        pd.Series
            Monthly returns indexed by the last day of each month.
        """
        daily = self.daily_returns()
        if daily.empty:
            return pd.Series(dtype=float)
        monthly = (1 + daily).resample("ME").prod() - 1
        logger.debug("Aggregated into %d monthly return observations", len(monthly))
        return monthly

    # -- rolling metrics ------------------------------------------------------

    def rolling_sharpe(self, window: int = 252, risk_free_rate: float = 0.0) -> pd.Series:
        """Compute rolling annualized Sharpe ratio.

        Parameters
        ----------
        window : int
            Look-back window in trading days.
        risk_free_rate : float
            Annualized risk-free rate.

        Returns
        -------
        pd.Series
            Rolling Sharpe ratio.
        """
        daily = self.daily_returns()
        if len(daily) < window:
            logger.warning("Not enough data for rolling Sharpe (need %d, have %d)", window, len(daily))
            return pd.Series(dtype=float)
        excess = daily - risk_free_rate / 252
        rolling_mean = excess.rolling(window).mean()
        rolling_std = excess.rolling(window).std()
        sharpe = (rolling_mean / rolling_std) * np.sqrt(252)
        return sharpe.dropna()

    def rolling_max_drawdown(self, window: int = 252) -> pd.Series:
        """Compute rolling maximum drawdown over a look-back window.

        Parameters
        ----------
        window : int
            Look-back window in trading days.

        Returns
        -------
        pd.Series
            Rolling maximum drawdown (negative values).
        """
        if self.equity_curve.empty or len(self.equity_curve) < window:
            return pd.Series(dtype=float)
        rolling_max = self.equity_curve.rolling(window, min_periods=1).max()
        drawdown = (self.equity_curve - rolling_max) / rolling_max
        return drawdown

    # -- top / bottom performers ----------------------------------------------

    def top_performers(self, n: int = 5) -> pd.DataFrame:
        """Return the top *n* instruments ranked by total P&L.

        Parameters
        ----------
        n : int
            Number of instruments to return.

        Returns
        -------
        pd.DataFrame
            Columns: instrument, total_pnl, trade_count, win_rate.
        """
        return self._ranked_performers(ascending=False, n=n)

    def bottom_performers(self, n: int = 5) -> pd.DataFrame:
        """Return the bottom *n* instruments ranked by total P&L.

        Parameters
        ----------
        n : int
            Number of instruments to return.

        Returns
        -------
        pd.DataFrame
            Columns: instrument, total_pnl, trade_count, win_rate.
        """
        return self._ranked_performers(ascending=True, n=n)

    def _ranked_performers(self, ascending: bool, n: int) -> pd.DataFrame:
        """Internal helper to rank instruments by P&L."""
        if self.trades.empty or "pnl" not in self.trades.columns:
            return pd.DataFrame(columns=["instrument", "total_pnl", "trade_count", "win_rate"])

        grouped = self.trades.groupby("instrument")["pnl"]
        summary = pd.DataFrame({
            "total_pnl": grouped.sum(),
            "trade_count": grouped.count(),
            "win_rate": grouped.apply(lambda x: (x > 0).mean() if len(x) > 0 else 0.0),
        })
        summary = summary.sort_values("total_pnl", ascending=ascending).head(n)
        summary = summary.reset_index()
        return summary

    # -- trade statistics -----------------------------------------------------

    def trade_statistics(self) -> Dict[str, Any]:
        """Compute summary statistics across all trades.

        Returns
        -------
        dict
            Keys include total_trades, winning_trades, losing_trades,
            win_rate, avg_win, avg_loss, profit_factor, expectancy,
            max_win, max_loss, avg_holding_period.
        """
        if self.trades.empty or "pnl" not in self.trades.columns:
            logger.warning("No trade data available for statistics")
            return {}

        pnl = self.trades["pnl"]
        wins = pnl[pnl > 0]
        losses = pnl[pnl <= 0]

        total = len(pnl)
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = win_count / total if total > 0 else 0.0
        avg_win = float(wins.mean()) if len(wins) > 0 else 0.0
        avg_loss = float(losses.mean()) if len(losses) > 0 else 0.0
        gross_profit = float(wins.sum()) if len(wins) > 0 else 0.0
        gross_loss = abs(float(losses.sum())) if len(losses) > 0 else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else float("inf")
        expectancy = float(pnl.mean())

        holding = None
        if {"entry_time", "exit_time"}.issubset(self.trades.columns):
            entry = pd.to_datetime(self.trades["entry_time"])
            exit_ = pd.to_datetime(self.trades["exit_time"])
            holding = (exit_ - entry).mean()

        stats: Dict[str, Any] = {
            "total_trades": total,
            "winning_trades": win_count,
            "losing_trades": loss_count,
            "win_rate": round(win_rate, 4),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 4),
            "expectancy": round(expectancy, 2),
            "max_win": round(float(pnl.max()), 2),
            "max_loss": round(float(pnl.min()), 2),
            "total_pnl": round(float(pnl.sum()), 2),
        }
        if holding is not None:
            stats["avg_holding_period"] = str(holding)

        logger.info("Trade statistics computed: %d trades, %.2f%% win rate", total, win_rate * 100)
        return stats

    # -- risk metrics ---------------------------------------------------------

    def risk_metrics(self, risk_free_rate: float = 0.0) -> Dict[str, Any]:
        """Compute portfolio-level risk metrics.

        Parameters
        ----------
        risk_free_rate : float
            Annualized risk-free rate for Sharpe calculation.

        Returns
        -------
        dict
            Keys include annualized_return, annualized_volatility,
            sharpe_ratio, sortino_ratio, max_drawdown, calmar_ratio,
            var_95, cvar_95.
        """
        daily = self.daily_returns()
        if daily.empty:
            logger.warning("No equity data for risk metrics")
            return {}

        ann_return = float(daily.mean() * 252)
        ann_vol = float(daily.std() * np.sqrt(252))
        sharpe = (ann_return - risk_free_rate) / ann_vol if ann_vol != 0 else 0.0

        # Sortino
        downside = daily[daily < 0]
        down_std = float(downside.std() * np.sqrt(252)) if len(downside) > 0 else 0.0
        sortino = (ann_return - risk_free_rate) / down_std if down_std != 0 else 0.0

        # Max drawdown
        cum = (1 + daily).cumprod()
        peak = cum.cummax()
        dd = ((cum - peak) / peak)
        max_dd = float(dd.min())

        calmar = ann_return / abs(max_dd) if max_dd != 0 else 0.0

        # VaR / CVaR
        var_95 = float(np.percentile(daily, 5))
        cvar_95 = float(daily[daily <= var_95].mean()) if len(daily[daily <= var_95]) > 0 else var_95

        metrics = {
            "annualized_return": round(ann_return, 4),
            "annualized_volatility": round(ann_vol, 4),
            "sharpe_ratio": round(sharpe, 4),
            "sortino_ratio": round(sortino, 4),
            "max_drawdown": round(max_dd, 4),
            "calmar_ratio": round(calmar, 4),
            "var_95": round(var_95, 6),
            "cvar_95": round(cvar_95, 6),
        }
        logger.info("Risk metrics computed: Sharpe=%.2f, MaxDD=%.2f%%", sharpe, max_dd * 100)
        return metrics

    # -- market commentary template -------------------------------------------

    def market_commentary(self) -> str:
        """Generate a short templated market commentary paragraph.

        Returns
        -------
        str
            Human-readable market commentary.
        """
        stats = self.trade_statistics()
        risk = self.risk_metrics()
        if not stats or not risk:
            return "Insufficient data to generate market commentary."

        total_pnl = stats.get("total_pnl", 0)
        pnl_word = "gain" if total_pnl >= 0 else "loss"
        win_rate = stats.get("win_rate", 0) * 100
        sharpe = risk.get("sharpe_ratio", 0)
        max_dd = risk.get("max_drawdown", 0) * 100

        commentary = (
            f"During the reporting period the portfolio recorded a net {pnl_word} "
            f"of ${abs(total_pnl):,.2f} across {stats.get('total_trades', 0)} trades. "
            f"The win rate stood at {win_rate:.1f}% with a profit factor of "
            f"{stats.get('profit_factor', 0):.2f}. On a risk-adjusted basis the "
            f"annualized Sharpe ratio was {sharpe:.2f} while the maximum drawdown "
            f"reached {max_dd:.1f}%. "
        )
        if sharpe >= 1.5:
            commentary += "Risk-adjusted returns were strong."
        elif sharpe >= 0.5:
            commentary += "Risk-adjusted returns were moderate."
        else:
            commentary += "Risk-adjusted returns were below expectations."

        return commentary


# ---------------------------------------------------------------------------
# CSVExporter
# ---------------------------------------------------------------------------

class CSVExporter:
    """Export DataFrames and report data to CSV files.

    Supports trade history, performance metrics, positions, signal history,
    and custom column selection.

    Parameters
    ----------
    output_dir : str
        Directory where CSV files will be written.
    delimiter : str
        Column delimiter (default comma).
    """

    def __init__(self, output_dir: str = "reports/csv", delimiter: str = ",") -> None:
        self.output_dir = output_dir
        self.delimiter = delimiter
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info("CSVExporter initialized, output_dir=%s", self.output_dir)

    # -- public helpers -------------------------------------------------------

    def export_trade_history(
        self,
        trades: pd.DataFrame,
        filename: str = "trade_history.csv",
        columns: Optional[List[str]] = None,
    ) -> str:
        """Export trade history to CSV.

        Parameters
        ----------
        trades : pd.DataFrame
            Trade records.
        filename : str
            Output file name.
        columns : list of str, optional
            Subset of columns to include.  When *None*, all columns
            are exported.

        Returns
        -------
        str
            Absolute path to the written CSV file.
        """
        return self._export_dataframe(trades, filename, columns)

    def export_performance_metrics(
        self,
        metrics: Dict[str, Any],
        filename: str = "performance_metrics.csv",
    ) -> str:
        """Export a metrics dictionary as a two-column CSV (metric, value).

        Parameters
        ----------
        metrics : dict
            Metric name -> value mapping.
        filename : str
            Output file name.

        Returns
        -------
        str
            Absolute path to the written CSV file.
        """
        df = pd.DataFrame(list(metrics.items()), columns=["metric", "value"])
        return self._export_dataframe(df, filename)

    def export_position_history(
        self,
        positions: pd.DataFrame,
        filename: str = "position_history.csv",
        columns: Optional[List[str]] = None,
    ) -> str:
        """Export position snapshot to CSV.

        Parameters
        ----------
        positions : pd.DataFrame
            Position data.
        filename : str
            Output file name.
        columns : list of str, optional
            Subset of columns to include.

        Returns
        -------
        str
            Absolute path to the written CSV file.
        """
        return self._export_dataframe(positions, filename, columns)

    def export_signal_history(
        self,
        signals: pd.DataFrame,
        filename: str = "signal_history.csv",
        columns: Optional[List[str]] = None,
    ) -> str:
        """Export signal history to CSV.

        Parameters
        ----------
        signals : pd.DataFrame
            Signal records.
        filename : str
            Output file name.
        columns : list of str, optional
            Subset of columns to include.

        Returns
        -------
        str
            Absolute path to the written CSV file.
        """
        return self._export_dataframe(signals, filename, columns)

    def export_custom(
        self,
        data: pd.DataFrame,
        filename: str,
        columns: Optional[List[str]] = None,
    ) -> str:
        """Export an arbitrary DataFrame to CSV with optional column selection.

        Parameters
        ----------
        data : pd.DataFrame
            Any DataFrame.
        filename : str
            Output file name.
        columns : list of str, optional
            Subset of columns to include.

        Returns
        -------
        str
            Absolute path to the written CSV file.
        """
        return self._export_dataframe(data, filename, columns)

    # -- internal -------------------------------------------------------------

    def _export_dataframe(
        self,
        df: pd.DataFrame,
        filename: str,
        columns: Optional[List[str]] = None,
    ) -> str:
        """Write a DataFrame to a CSV file.

        Parameters
        ----------
        df : pd.DataFrame
            Source data.
        filename : str
            File name (relative to *output_dir*).
        columns : list of str, optional
            If provided, only these columns are exported.

        Returns
        -------
        str
            Absolute path to the file that was written.
        """
        if columns:
            available = [c for c in columns if c in df.columns]
            if len(available) < len(columns):
                missing = set(columns) - set(available)
                logger.warning("Requested columns not found in data: %s", missing)
            df = df[available]

        path = os.path.join(self.output_dir, filename)
        df.to_csv(path, index=False, sep=self.delimiter)
        logger.info("Exported %d rows to %s", len(df), path)
        return os.path.abspath(path)


# ---------------------------------------------------------------------------
# HTMLReportBuilder
# ---------------------------------------------------------------------------

class HTMLReportBuilder:
    """Generates professional, self-contained HTML reports.

    Features include responsive CSS, color-coded P&L tables, base64-embedded
    chart images, and collapsible sections.

    Parameters
    ----------
    title : str
        Report title displayed in the header.
    """

    # Base CSS shared across all reports
    _BASE_CSS = """
        :root {
            --clr-bg: #f8f9fa;
            --clr-card: #ffffff;
            --clr-primary: #1a237e;
            --clr-accent: #0d47a1;
            --clr-green: #2e7d32;
            --clr-red: #c62828;
            --clr-border: #dee2e6;
            --clr-text: #212529;
            --clr-muted: #6c757d;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: var(--clr-bg);
            color: var(--clr-text);
            line-height: 1.6;
            padding: 20px;
        }
        .container { max-width: 1100px; margin: 0 auto; }
        header {
            background: linear-gradient(135deg, var(--clr-primary), var(--clr-accent));
            color: #fff; padding: 28px 32px; border-radius: 8px;
            margin-bottom: 24px;
        }
        header h1 { font-size: 1.8rem; font-weight: 600; }
        header .subtitle { opacity: 0.85; font-size: 0.95rem; margin-top: 4px; }
        .card {
            background: var(--clr-card); border: 1px solid var(--clr-border);
            border-radius: 8px; padding: 24px; margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }
        .card h2 {
            font-size: 1.15rem; color: var(--clr-primary);
            margin-bottom: 16px; border-bottom: 2px solid var(--clr-primary);
            padding-bottom: 6px;
        }
        table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
        th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--clr-border); }
        th { background: var(--clr-bg); font-weight: 600; }
        tr:hover { background: #f1f3f5; }
        .positive { color: var(--clr-green); font-weight: 600; }
        .negative { color: var(--clr-red); font-weight: 600; }
        .metric-grid {
            display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 14px;
        }
        .metric-box {
            background: var(--clr-bg); border-radius: 6px; padding: 14px 16px;
            border-left: 4px solid var(--clr-accent);
        }
        .metric-box .label { font-size: 0.8rem; color: var(--clr-muted); text-transform: uppercase; }
        .metric-box .value { font-size: 1.3rem; font-weight: 700; margin-top: 2px; }
        .chart-container { text-align: center; margin: 16px 0; }
        .chart-container img { max-width: 100%; height: auto; border-radius: 4px; }
        details { margin-bottom: 12px; }
        details summary {
            cursor: pointer; padding: 10px 14px; background: var(--clr-bg);
            border: 1px solid var(--clr-border); border-radius: 6px;
            font-weight: 600; font-size: 0.95rem;
        }
        details[open] summary { border-radius: 6px 6px 0 0; }
        details .detail-body {
            border: 1px solid var(--clr-border); border-top: none;
            border-radius: 0 0 6px 6px; padding: 16px;
        }
        footer {
            text-align: center; font-size: 0.8rem; color: var(--clr-muted);
            margin-top: 30px; padding: 12px;
        }
        @media (max-width: 600px) {
            body { padding: 10px; }
            header { padding: 18px; }
            .metric-grid { grid-template-columns: 1fr; }
        }
    """

    def __init__(self, title: str = "ScreenerIII Performance Report") -> None:
        self.title = title
        self._sections: List[str] = []
        logger.debug("HTMLReportBuilder created with title '%s'", title)

    # -- public API -----------------------------------------------------------

    def add_metric_grid(self, metrics: Dict[str, Any], section_title: str = "Key Metrics") -> None:
        """Add a grid of metric boxes.

        Parameters
        ----------
        metrics : dict
            Metric label -> display value.
        section_title : str
            Heading above the grid.
        """
        boxes = []
        for label, value in metrics.items():
            css_class = ""
            if isinstance(value, (int, float)):
                css_class = "positive" if value >= 0 else "negative"
            boxes.append(
                f'<div class="metric-box">'
                f'<div class="label">{_html_escape(str(label))}</div>'
                f'<div class="value {css_class}">{_html_escape(str(value))}</div>'
                f'</div>'
            )
        html = (
            f'<div class="card"><h2>{_html_escape(section_title)}</h2>'
            f'<div class="metric-grid">{"".join(boxes)}</div></div>'
        )
        self._sections.append(html)
        logger.debug("Added metric grid section '%s' with %d items", section_title, len(metrics))

    def add_table(
        self,
        df: pd.DataFrame,
        section_title: str = "Data",
        pnl_column: Optional[str] = None,
        max_rows: int = 200,
    ) -> None:
        """Add a styled table from a DataFrame.

        Parameters
        ----------
        df : pd.DataFrame
            Data to render.
        section_title : str
            Heading above the table.
        pnl_column : str, optional
            Column name whose values should be color-coded green/red.
        max_rows : int
            Maximum rows rendered to prevent giant HTML files.
        """
        if df.empty:
            self._sections.append(
                f'<div class="card"><h2>{_html_escape(section_title)}</h2>'
                f'<p>No data available.</p></div>'
            )
            return

        display_df = df.head(max_rows)
        header_cells = "".join(f"<th>{_html_escape(str(c))}</th>" for c in display_df.columns)
        rows = []
        for _, row in display_df.iterrows():
            cells = []
            for col in display_df.columns:
                val = row[col]
                css = ""
                if col == pnl_column and isinstance(val, (int, float)):
                    css = ' class="positive"' if val >= 0 else ' class="negative"'
                cells.append(f"<td{css}>{_html_escape(str(val))}</td>")
            rows.append(f"<tr>{''.join(cells)}</tr>")

        truncation_notice = ""
        if len(df) > max_rows:
            truncation_notice = f'<p style="color:var(--clr-muted);font-size:0.85rem;">Showing {max_rows} of {len(df)} rows.</p>'

        html = (
            f'<div class="card"><h2>{_html_escape(section_title)}</h2>'
            f'<table><thead><tr>{header_cells}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>'
            f'{truncation_notice}</div>'
        )
        self._sections.append(html)
        logger.debug("Added table section '%s' with %d rows", section_title, len(display_df))

    def add_chart(self, image_bytes: bytes, section_title: str = "Chart", alt_text: str = "Chart") -> None:
        """Embed a chart image as base64.

        Parameters
        ----------
        image_bytes : bytes
            PNG image content.
        section_title : str
            Heading above the chart.
        alt_text : str
            Alt text for the image element.
        """
        encoded = base64.b64encode(image_bytes).decode("ascii")
        html = (
            f'<div class="card"><h2>{_html_escape(section_title)}</h2>'
            f'<div class="chart-container">'
            f'<img src="data:image/png;base64,{encoded}" alt="{_html_escape(alt_text)}" />'
            f'</div></div>'
        )
        self._sections.append(html)
        logger.debug("Embedded chart section '%s' (%d bytes)", section_title, len(image_bytes))

    def add_collapsible_section(self, title: str, body_html: str) -> None:
        """Add an interactive collapsible (details/summary) section.

        Parameters
        ----------
        title : str
            Summary line (always visible).
        body_html : str
            HTML content revealed when the section is expanded.
        """
        html = (
            f'<details><summary>{_html_escape(title)}</summary>'
            f'<div class="detail-body">{body_html}</div></details>'
        )
        self._sections.append(html)

    def add_text(self, text: str, section_title: str = "") -> None:
        """Add a plain-text paragraph wrapped in a card.

        Parameters
        ----------
        text : str
            Text content (HTML-escaped internally).
        section_title : str
            Optional heading.
        """
        heading = f'<h2>{_html_escape(section_title)}</h2>' if section_title else ""
        html = f'<div class="card">{heading}<p>{_html_escape(text)}</p></div>'
        self._sections.append(html)

    def add_raw_html(self, html: str) -> None:
        """Inject arbitrary HTML into the report (use carefully).

        Parameters
        ----------
        html : str
            Raw HTML string.
        """
        self._sections.append(html)

    # -- rendering ------------------------------------------------------------

    def render(self, subtitle: str = "") -> str:
        """Build the full standalone HTML document.

        Parameters
        ----------
        subtitle : str
            Subtitle shown under the report title in the header.

        Returns
        -------
        str
            Complete HTML document.
        """
        subtitle_html = f'<div class="subtitle">{_html_escape(subtitle)}</div>' if subtitle else ""
        body_sections = "\n".join(self._sections)
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        html = (
            "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
            '<meta charset="UTF-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            f"<title>{_html_escape(self.title)}</title>\n"
            f"<style>{self._BASE_CSS}</style>\n"
            "</head>\n<body>\n"
            '<div class="container">\n'
            f"<header><h1>{_html_escape(self.title)}</h1>{subtitle_html}</header>\n"
            f"{body_sections}\n"
            f'<footer>Generated by ScreenerIII &mdash; {now}</footer>\n'
            "</div>\n</body>\n</html>"
        )
        logger.info("Rendered HTML report, %d sections, %d bytes", len(self._sections), len(html))
        return html

    def save(self, path: str, subtitle: str = "") -> str:
        """Render and write the HTML report to a file.

        Parameters
        ----------
        path : str
            Destination file path.
        subtitle : str
            Subtitle for the header.

        Returns
        -------
        str
            Absolute path to the saved file.
        """
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        content = self.render(subtitle)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        logger.info("HTML report saved to %s", path)
        return os.path.abspath(path)

    def reset(self) -> None:
        """Clear all sections so the builder can be reused."""
        self._sections.clear()


# ---------------------------------------------------------------------------
# ReportGenerator
# ---------------------------------------------------------------------------

class ReportGenerator:
    """Main report engine that orchestrates data aggregation, rendering,
    and export across multiple output formats.

    Parameters
    ----------
    output_dir : str
        Root directory for generated report files.
    default_format : OutputFormat
        Default output format when not specified per report.
    """

    def __init__(
        self,
        output_dir: str = "reports",
        default_format: OutputFormat = OutputFormat.HTML,
    ) -> None:
        self.output_dir = output_dir
        self.default_format = default_format
        self._csv_exporter = CSVExporter(os.path.join(output_dir, "csv"))
        self._report_history: List[ReportMetadata] = []
        os.makedirs(output_dir, exist_ok=True)
        logger.info("ReportGenerator initialized, output_dir=%s", output_dir)

    # -- daily report ---------------------------------------------------------

    def daily_report(
        self,
        report_data: PerformanceReportData,
        report_date: Optional[date] = None,
        output_format: Optional[OutputFormat] = None,
    ) -> ReportMetadata:
        """Generate a daily performance report.

        Parameters
        ----------
        report_data : PerformanceReportData
            Aggregated performance data for the day.
        report_date : date, optional
            The trading day.  Defaults to today.
        output_format : OutputFormat, optional
            Override the default output format.

        Returns
        -------
        ReportMetadata
            Metadata about the generated report file.
        """
        report_date = report_date or date.today()
        fmt = output_format or self.default_format
        title = f"Daily Performance Report - {report_date.isoformat()}"
        logger.info("Generating daily report for %s", report_date)

        content = self._build_report_content(
            report_data, title, report_date, report_date, fmt,
        )
        return self._finalize_report(
            content, title, ReportFrequency.DAILY, report_date, report_date, fmt,
        )

    # -- weekly report --------------------------------------------------------

    def weekly_report(
        self,
        report_data: PerformanceReportData,
        week_ending: Optional[date] = None,
        output_format: Optional[OutputFormat] = None,
    ) -> ReportMetadata:
        """Generate a weekly summary report.

        Parameters
        ----------
        report_data : PerformanceReportData
            Aggregated performance data for the week.
        week_ending : date, optional
            Last day of the reporting week (defaults to today).
        output_format : OutputFormat, optional
            Override the default output format.

        Returns
        -------
        ReportMetadata
            Metadata about the generated report file.
        """
        week_ending = week_ending or date.today()
        week_start = week_ending - timedelta(days=6)
        fmt = output_format or self.default_format
        title = f"Weekly Summary - {week_start.isoformat()} to {week_ending.isoformat()}"
        logger.info("Generating weekly report for %s - %s", week_start, week_ending)

        content = self._build_report_content(
            report_data, title, week_start, week_ending, fmt,
        )
        return self._finalize_report(
            content, title, ReportFrequency.WEEKLY, week_start, week_ending, fmt,
        )

    # -- monthly report -------------------------------------------------------

    def monthly_report(
        self,
        report_data: PerformanceReportData,
        year: Optional[int] = None,
        month: Optional[int] = None,
        output_format: Optional[OutputFormat] = None,
    ) -> ReportMetadata:
        """Generate a detailed monthly report.

        Parameters
        ----------
        report_data : PerformanceReportData
            Aggregated performance data for the month.
        year : int, optional
            Report year (defaults to current year).
        month : int, optional
            Report month 1-12 (defaults to current month).
        output_format : OutputFormat, optional
            Override the default output format.

        Returns
        -------
        ReportMetadata
            Metadata about the generated report file.
        """
        today = date.today()
        year = year or today.year
        month = month or today.month
        month_start = date(year, month, 1)
        # last day of month
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)

        fmt = output_format or self.default_format
        title = f"Monthly Report - {month_start.strftime('%B %Y')}"
        logger.info("Generating monthly report for %s", month_start.strftime("%B %Y"))

        content = self._build_report_content(
            report_data, title, month_start, month_end, fmt,
        )
        return self._finalize_report(
            content, title, ReportFrequency.MONTHLY, month_start, month_end, fmt,
        )

    # -- custom range report --------------------------------------------------

    def custom_report(
        self,
        report_data: PerformanceReportData,
        start_date: date,
        end_date: date,
        title: Optional[str] = None,
        output_format: Optional[OutputFormat] = None,
    ) -> ReportMetadata:
        """Generate a report for an arbitrary date range.

        Parameters
        ----------
        report_data : PerformanceReportData
            Performance data covering the range.
        start_date : date
            First day of the range.
        end_date : date
            Last day of the range.
        title : str, optional
            Report title override.
        output_format : OutputFormat, optional
            Override the default output format.

        Returns
        -------
        ReportMetadata
            Metadata about the generated report file.
        """
        fmt = output_format or self.default_format
        title = title or f"Custom Report - {start_date.isoformat()} to {end_date.isoformat()}"
        logger.info("Generating custom report for %s - %s", start_date, end_date)

        content = self._build_report_content(report_data, title, start_date, end_date, fmt)
        return self._finalize_report(
            content, title, ReportFrequency.CUSTOM, start_date, end_date, fmt,
        )

    # -- template-based generation --------------------------------------------

    def generate_from_template(
        self,
        report_data: PerformanceReportData,
        template: str,
        variables: Optional[Dict[str, str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> ReportMetadata:
        """Generate a report by filling a user-supplied HTML template.

        The template may contain ``{{variable_name}}`` placeholders which are
        replaced with values from *variables*, plus the following built-in
        tokens:

        - ``{{title}}``, ``{{generated_at}}``, ``{{start_date}}``,
          ``{{end_date}}``, ``{{trade_stats_table}}``,
          ``{{risk_metrics_table}}``, ``{{commentary}}``,
          ``{{top_performers_table}}``, ``{{bottom_performers_table}}``.

        Parameters
        ----------
        report_data : PerformanceReportData
            Performance data.
        template : str
            HTML template string with ``{{...}}`` placeholders.
        variables : dict, optional
            Additional variable substitutions.
        start_date : date, optional
            Reporting period start.
        end_date : date, optional
            Reporting period end.

        Returns
        -------
        ReportMetadata
            Metadata about the generated report file.
        """
        start_date = start_date or date.today()
        end_date = end_date or date.today()
        variables = variables or {}

        stats = report_data.trade_statistics()
        risk = report_data.risk_metrics()

        built_in: Dict[str, str] = {
            "title": "ScreenerIII Report",
            "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "trade_stats_table": self._dict_to_html_table(stats),
            "risk_metrics_table": self._dict_to_html_table(risk),
            "commentary": report_data.market_commentary(),
            "top_performers_table": report_data.top_performers().to_html(
                index=False, classes="table", border=0
            ) if not report_data.top_performers().empty else "<p>No data</p>",
            "bottom_performers_table": report_data.bottom_performers().to_html(
                index=False, classes="table", border=0
            ) if not report_data.bottom_performers().empty else "<p>No data</p>",
        }
        built_in.update(variables)

        rendered = template
        for key, value in built_in.items():
            rendered = rendered.replace("{{" + key + "}}", str(value))

        title = built_in.get("title", "ScreenerIII Report")
        return self._finalize_report(
            rendered, title, ReportFrequency.CUSTOM, start_date, end_date, OutputFormat.HTML,
        )

    # -- report history -------------------------------------------------------

    @property
    def report_history(self) -> List[ReportMetadata]:
        """Return a copy of the report generation history."""
        return list(self._report_history)

    # -- private helpers ------------------------------------------------------

    def _build_report_content(
        self,
        data: PerformanceReportData,
        title: str,
        start_date: date,
        end_date: date,
        fmt: OutputFormat,
    ) -> str:
        """Dispatch to the correct renderer based on output format."""
        if fmt == OutputFormat.HTML:
            return self._build_html(data, title, start_date, end_date)
        elif fmt == OutputFormat.CSV:
            return self._build_csv(data)
        elif fmt == OutputFormat.JSON:
            return self._build_json(data)
        else:
            return self._build_text(data, title, start_date, end_date)

    def _build_html(
        self,
        data: PerformanceReportData,
        title: str,
        start_date: date,
        end_date: date,
    ) -> str:
        builder = HTMLReportBuilder(title)
        subtitle = f"{start_date.isoformat()} to {end_date.isoformat()}"

        # Key metrics grid
        stats = data.trade_statistics()
        risk = data.risk_metrics()
        summary_metrics: Dict[str, Any] = {}
        if stats:
            summary_metrics["Total P&L"] = f"${stats.get('total_pnl', 0):,.2f}"
            summary_metrics["Total Trades"] = stats.get("total_trades", 0)
            summary_metrics["Win Rate"] = f"{stats.get('win_rate', 0) * 100:.1f}%"
            summary_metrics["Profit Factor"] = stats.get("profit_factor", 0)
        if risk:
            summary_metrics["Sharpe Ratio"] = risk.get("sharpe_ratio", 0)
            summary_metrics["Max Drawdown"] = f"{risk.get('max_drawdown', 0) * 100:.1f}%"
            summary_metrics["Ann. Return"] = f"{risk.get('annualized_return', 0) * 100:.1f}%"
            summary_metrics["Ann. Volatility"] = f"{risk.get('annualized_volatility', 0) * 100:.1f}%"
        if summary_metrics:
            builder.add_metric_grid(summary_metrics)

        # Trade statistics (collapsible)
        if stats:
            builder.add_collapsible_section(
                "Trade Statistics", self._dict_to_html_table(stats),
            )

        # Risk metrics (collapsible)
        if risk:
            builder.add_collapsible_section(
                "Risk Metrics", self._dict_to_html_table(risk),
            )

        # Top / bottom performers
        top = data.top_performers()
        if not top.empty:
            builder.add_table(top, "Top Performers", pnl_column="total_pnl")
        bottom = data.bottom_performers()
        if not bottom.empty:
            builder.add_table(bottom, "Bottom Performers", pnl_column="total_pnl")

        # Recent trades
        if not data.trades.empty:
            recent = data.trades.tail(20)
            pnl_col = "pnl" if "pnl" in recent.columns else None
            builder.add_table(recent, "Recent Trades", pnl_column=pnl_col)

        # Open positions
        if not data.positions.empty:
            pnl_col = "unrealized_pnl" if "unrealized_pnl" in data.positions.columns else None
            builder.add_table(data.positions, "Open Positions", pnl_column=pnl_col)

        # Commentary
        commentary = data.market_commentary()
        builder.add_text(commentary, "Market Commentary")

        return builder.render(subtitle)

    def _build_csv(self, data: PerformanceReportData) -> str:
        """Build a combined CSV of trade stats and risk metrics."""
        buf = io.StringIO()
        writer = csv.writer(buf)
        stats = data.trade_statistics()
        risk = data.risk_metrics()
        writer.writerow(["Category", "Metric", "Value"])
        for k, v in stats.items():
            writer.writerow(["trade_statistics", k, v])
        for k, v in risk.items():
            writer.writerow(["risk_metrics", k, v])
        return buf.getvalue()

    def _build_json(self, data: PerformanceReportData) -> str:
        """Build a JSON representation of report data."""
        payload = {
            "trade_statistics": data.trade_statistics(),
            "risk_metrics": data.risk_metrics(),
            "commentary": data.market_commentary(),
        }
        top = data.top_performers()
        bottom = data.bottom_performers()
        if not top.empty:
            payload["top_performers"] = top.to_dict(orient="records")
        if not bottom.empty:
            payload["bottom_performers"] = bottom.to_dict(orient="records")
        return json.dumps(payload, indent=2, default=str)

    def _build_text(
        self,
        data: PerformanceReportData,
        title: str,
        start_date: date,
        end_date: date,
    ) -> str:
        """Build a plain-text report."""
        lines = [
            "=" * 70,
            title.center(70),
            f"{start_date.isoformat()} to {end_date.isoformat()}".center(70),
            "=" * 70,
            "",
        ]
        stats = data.trade_statistics()
        if stats:
            lines.append("TRADE STATISTICS")
            lines.append("-" * 40)
            for k, v in stats.items():
                lines.append(f"  {k:<28} {v}")
            lines.append("")

        risk = data.risk_metrics()
        if risk:
            lines.append("RISK METRICS")
            lines.append("-" * 40)
            for k, v in risk.items():
                lines.append(f"  {k:<28} {v}")
            lines.append("")

        commentary = data.market_commentary()
        lines.append("COMMENTARY")
        lines.append("-" * 40)
        lines.append(f"  {commentary}")
        lines.append("")
        lines.append(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append("=" * 70)
        return "\n".join(lines)

    def _finalize_report(
        self,
        content: str,
        title: str,
        frequency: ReportFrequency,
        start_date: date,
        end_date: date,
        fmt: OutputFormat,
    ) -> ReportMetadata:
        """Write report content to disk and record metadata."""
        ext_map = {
            OutputFormat.HTML: "html",
            OutputFormat.CSV: "csv",
            OutputFormat.JSON: "json",
            OutputFormat.TEXT: "txt",
        }
        ext = ext_map.get(fmt, "txt")
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{frequency.value}_{start_date.isoformat()}_{timestamp}.{ext}"
        subdir = os.path.join(self.output_dir, frequency.value)
        os.makedirs(subdir, exist_ok=True)
        filepath = os.path.join(subdir, filename)

        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(content)

        checksum = hashlib.md5(content.encode("utf-8")).hexdigest()
        report_id = f"{frequency.value}_{timestamp}_{checksum[:8]}"

        meta = ReportMetadata(
            report_id=report_id,
            title=title,
            frequency=frequency,
            generated_at=datetime.utcnow(),
            start_date=start_date,
            end_date=end_date,
            output_format=fmt,
            file_path=os.path.abspath(filepath),
            checksum=checksum,
        )
        self._report_history.append(meta)
        logger.info("Report saved: %s (%s)", meta.report_id, filepath)
        return meta

    @staticmethod
    def _dict_to_html_table(d: Dict[str, Any]) -> str:
        """Render a dict as a two-column HTML table."""
        rows = []
        for k, v in d.items():
            css = ""
            if isinstance(v, (int, float)):
                css = ' class="positive"' if v >= 0 else ' class="negative"'
            rows.append(f"<tr><td>{_html_escape(str(k))}</td><td{css}>{_html_escape(str(v))}</td></tr>")
        return f'<table><tbody>{"".join(rows)}</tbody></table>'


# ---------------------------------------------------------------------------
# ScheduledReporter
# ---------------------------------------------------------------------------

class ScheduledReporter:
    """Automated report scheduling with optional email delivery.

    Runs reports on a background timer thread.  Designed to trigger:
    - Daily reports shortly after market close
    - Weekly reports on Friday
    - Monthly reports on the last trading day of the month

    Parameters
    ----------
    generator : ReportGenerator
        The report generator instance to delegate to.
    data_provider : callable
        A zero-argument callable that returns a fresh
        :class:`PerformanceReportData` instance when invoked.
    email_config : EmailConfig, optional
        SMTP configuration for email delivery.
    """

    def __init__(
        self,
        generator: ReportGenerator,
        data_provider: Callable[[], PerformanceReportData],
        email_config: Optional[EmailConfig] = None,
    ) -> None:
        self.generator = generator
        self.data_provider = data_provider
        self.email_config = email_config

        self._schedules: Dict[ReportFrequency, Dict[str, Any]] = {}
        self._timers: Dict[ReportFrequency, threading.Timer] = {}
        self._running = False
        self._lock = threading.Lock()
        self._history: List[Dict[str, Any]] = []

        logger.info("ScheduledReporter initialized")

    # -- scheduling configuration ---------------------------------------------

    def schedule_daily(self, hour: int = 17, minute: int = 0) -> None:
        """Schedule a daily report.

        Parameters
        ----------
        hour : int
            Hour of day (0-23) to trigger the report.
        minute : int
            Minute of hour (0-59).
        """
        self._schedules[ReportFrequency.DAILY] = {
            "hour": hour,
            "minute": minute,
            "output_format": OutputFormat.HTML,
        }
        logger.info("Daily report scheduled at %02d:%02d", hour, minute)

    def schedule_weekly(
        self,
        weekday: int = 4,
        hour: int = 17,
        minute: int = 0,
    ) -> None:
        """Schedule a weekly report.

        Parameters
        ----------
        weekday : int
            ISO weekday (0=Monday, 4=Friday).
        hour : int
            Hour of day.
        minute : int
            Minute of hour.
        """
        self._schedules[ReportFrequency.WEEKLY] = {
            "weekday": weekday,
            "hour": hour,
            "minute": minute,
            "output_format": OutputFormat.HTML,
        }
        logger.info("Weekly report scheduled: weekday=%d at %02d:%02d", weekday, hour, minute)

    def schedule_monthly(self, hour: int = 17, minute: int = 0) -> None:
        """Schedule a monthly report on the last trading day of the month.

        Parameters
        ----------
        hour : int
            Hour of day.
        minute : int
            Minute of hour.
        """
        self._schedules[ReportFrequency.MONTHLY] = {
            "hour": hour,
            "minute": minute,
            "output_format": OutputFormat.HTML,
        }
        logger.info("Monthly report scheduled at %02d:%02d on last trading day", hour, minute)

    # -- start / stop ---------------------------------------------------------

    def start(self) -> None:
        """Begin the scheduling loop for all configured report frequencies."""
        with self._lock:
            if self._running:
                logger.warning("ScheduledReporter is already running")
                return
            self._running = True

        for freq in self._schedules:
            self._schedule_next(freq)
        logger.info("ScheduledReporter started with %d schedule(s)", len(self._schedules))

    def stop(self) -> None:
        """Cancel all pending timers and stop the scheduler."""
        with self._lock:
            self._running = False
        for freq, timer in self._timers.items():
            timer.cancel()
            logger.debug("Cancelled timer for %s", freq.value)
        self._timers.clear()
        logger.info("ScheduledReporter stopped")

    # -- manual trigger -------------------------------------------------------

    def run_now(self, frequency: ReportFrequency) -> Optional[ReportMetadata]:
        """Immediately generate a report of the given frequency.

        Parameters
        ----------
        frequency : ReportFrequency
            Which report to generate.

        Returns
        -------
        ReportMetadata or None
            Metadata of the generated report, or *None* on failure.
        """
        logger.info("Manual trigger for %s report", frequency.value)
        return self._generate_report(frequency)

    # -- history --------------------------------------------------------------

    @property
    def history(self) -> List[Dict[str, Any]]:
        """Return the scheduled-report execution history."""
        return list(self._history)

    # -- internal scheduling logic --------------------------------------------

    def _schedule_next(self, frequency: ReportFrequency) -> None:
        """Compute seconds until the next trigger and set a timer."""
        if not self._running:
            return

        delay = self._seconds_until_next(frequency)
        timer = threading.Timer(delay, self._timer_callback, args=(frequency,))
        timer.daemon = True
        timer.start()
        self._timers[frequency] = timer
        logger.debug("Next %s report in %.0f seconds", frequency.value, delay)

    def _timer_callback(self, frequency: ReportFrequency) -> None:
        """Called when a timer fires."""
        if not self._running:
            return
        meta = self._generate_report(frequency)
        if meta and self.email_config:
            self._send_email(meta)
        # Re-schedule
        self._schedule_next(frequency)

    def _generate_report(self, frequency: ReportFrequency) -> Optional[ReportMetadata]:
        """Generate the appropriate report and record history."""
        try:
            data = self.data_provider()
            cfg = self._schedules.get(frequency, {})
            fmt = cfg.get("output_format", OutputFormat.HTML)

            if frequency == ReportFrequency.DAILY:
                meta = self.generator.daily_report(data, output_format=fmt)
            elif frequency == ReportFrequency.WEEKLY:
                meta = self.generator.weekly_report(data, output_format=fmt)
            elif frequency == ReportFrequency.MONTHLY:
                meta = self.generator.monthly_report(data, output_format=fmt)
            else:
                meta = self.generator.daily_report(data, output_format=fmt)

            self._history.append({
                "frequency": frequency.value,
                "generated_at": datetime.utcnow().isoformat(),
                "report_id": meta.report_id,
                "file_path": meta.file_path,
                "status": "success",
            })
            logger.info("Scheduled %s report generated: %s", frequency.value, meta.report_id)
            return meta

        except Exception as exc:
            logger.error("Failed to generate scheduled %s report: %s", frequency.value, exc)
            self._history.append({
                "frequency": frequency.value,
                "generated_at": datetime.utcnow().isoformat(),
                "report_id": None,
                "file_path": None,
                "status": f"error: {exc}",
            })
            return None

    def _seconds_until_next(self, frequency: ReportFrequency) -> float:
        """Return seconds until the next scheduled trigger for *frequency*."""
        now = datetime.now()
        cfg = self._schedules.get(frequency, {})
        target_hour = cfg.get("hour", 17)
        target_minute = cfg.get("minute", 0)

        if frequency == ReportFrequency.DAILY:
            target = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return (target - now).total_seconds()

        elif frequency == ReportFrequency.WEEKLY:
            target_weekday = cfg.get("weekday", 4)
            days_ahead = (target_weekday - now.weekday()) % 7
            target = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
            target += timedelta(days=days_ahead)
            if target <= now:
                target += timedelta(weeks=1)
            return (target - now).total_seconds()

        elif frequency == ReportFrequency.MONTHLY:
            # Next occurrence on the last weekday of the current/next month
            target = self._last_trading_day(now.year, now.month)
            target = target.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
            if target <= now:
                # Move to next month
                if now.month == 12:
                    target = self._last_trading_day(now.year + 1, 1)
                else:
                    target = self._last_trading_day(now.year, now.month + 1)
                target = target.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
            return (target - now).total_seconds()

        # Fallback: one hour
        return 3600.0

    @staticmethod
    def _last_trading_day(year: int, month: int) -> datetime:
        """Return the last weekday (Mon-Fri) of the given month as a datetime."""
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        last_day = next_month - timedelta(days=1)
        # Roll back to Friday if weekend
        while last_day.weekday() >= 5:
            last_day -= timedelta(days=1)
        return last_day

    # -- email delivery -------------------------------------------------------

    def _send_email(self, meta: ReportMetadata) -> bool:
        """Send the generated report as an email attachment.

        Parameters
        ----------
        meta : ReportMetadata
            Report whose file should be attached.

        Returns
        -------
        bool
            True if the email was sent successfully.
        """
        if not EMAIL_AVAILABLE:
            logger.warning("Email delivery requested but smtplib is not available")
            return False

        if not self.email_config or not self.email_config.to_addresses:
            logger.warning("Email configuration is incomplete; skipping delivery")
            return False

        cfg = self.email_config
        subject = f"{cfg.subject_prefix} {meta.title}"

        msg = MIMEMultipart()
        msg["From"] = cfg.from_address
        msg["To"] = ", ".join(cfg.to_addresses)
        msg["Subject"] = subject

        body = (
            f"Report: {meta.title}\n"
            f"Generated: {meta.generated_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"Period: {meta.start_date.isoformat()} to {meta.end_date.isoformat()}\n"
            f"Format: {meta.output_format.value}\n"
        )
        msg.attach(MIMEText(body, "plain"))

        # Attach report file
        if meta.file_path and os.path.isfile(meta.file_path):
            try:
                with open(meta.file_path, "rb") as fh:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(fh.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={os.path.basename(meta.file_path)}",
                )
                msg.attach(part)
            except OSError as exc:
                logger.error("Failed to attach report file: %s", exc)

        try:
            if cfg.use_tls:
                server = smtplib.SMTP(cfg.smtp_host, cfg.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP(cfg.smtp_host, cfg.smtp_port)
            if cfg.username:
                server.login(cfg.username, cfg.password)
            server.sendmail(cfg.from_address, cfg.to_addresses, msg.as_string())
            server.quit()
            logger.info("Report email sent to %s", cfg.to_addresses)
            return True
        except Exception as exc:
            logger.error("Failed to send report email: %s", exc)
            return False


# ---------------------------------------------------------------------------
# Module-level helper
# ---------------------------------------------------------------------------

def _html_escape(text: str) -> str:
    """Minimal HTML escaping for user-supplied text."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )
