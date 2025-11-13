"""
Comprehensive Backtesting Framework for ScreenerIII

This module provides a complete backtesting system for trading strategies,
including historical data replay, portfolio management, performance metrics,
and result analysis.

Features:
- Load data from TimescaleDB or CSV files
- Chronological data replay (no look-ahead bias)
- Virtual portfolio and position tracking
- Comprehensive performance metrics
- Transaction cost modeling
- Walk-forward analysis support
- Parameter optimization hooks
- Multi-timeframe support

Author: ScreenerIII
License: MIT
"""

import logging
from typing import Dict, List, Optional, Tuple, Union, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import json
import warnings

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

# Try to import matplotlib for visualization (optional)
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    warnings.warn("Matplotlib not available. Visualization features will be disabled.")

from ..core.database import get_db, MarketData
from .signals import SignalGenerator, SignalType, TradingSignal

logger = logging.getLogger(__name__)


class ExitReason(Enum):
    """Enumeration of trade exit reasons."""
    TARGET_HIT = "TARGET_HIT"
    STOP_HIT = "STOP_HIT"
    SIGNAL_REVERSAL = "SIGNAL_REVERSAL"
    END_OF_DATA = "END_OF_DATA"
    MANUAL_EXIT = "MANUAL_EXIT"


class PositionSide(Enum):
    """Enumeration of position sides."""
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class Trade:
    """
    Represents an individual trade with entry, exit, and P&L information.

    Attributes:
        trade_id: Unique identifier for the trade
        instrument: Trading instrument
        side: Position side (LONG/SHORT)
        entry_time: Trade entry timestamp
        entry_price: Entry price
        position_size: Number of units/shares
        stop_loss: Stop loss price
        take_profit: Take profit/target price
        exit_time: Trade exit timestamp
        exit_price: Exit price
        exit_reason: Reason for trade exit
        commission: Total commission paid
        slippage: Total slippage cost
        pnl: Profit/loss in currency
        pnl_percent: Profit/loss as percentage
        mae: Maximum Adverse Excursion (worst drawdown during trade)
        mfe: Maximum Favorable Excursion (best profit during trade)
        duration: Trade duration in hours
        signal_confidence: Original signal confidence score
    """
    trade_id: int
    instrument: str
    side: PositionSide
    entry_time: datetime
    entry_price: float
    position_size: float
    stop_loss: float
    take_profit: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[ExitReason] = None
    commission: float = 0.0
    slippage: float = 0.0
    pnl: float = 0.0
    pnl_percent: float = 0.0
    mae: float = 0.0  # Maximum Adverse Excursion
    mfe: float = 0.0  # Maximum Favorable Excursion
    duration: Optional[float] = None
    signal_confidence: float = 0.0

    def calculate_pnl(self) -> None:
        """Calculate profit/loss for the trade."""
        if self.exit_price is None:
            return

        if self.side == PositionSide.LONG:
            gross_pnl = (self.exit_price - self.entry_price) * self.position_size
        else:  # SHORT
            gross_pnl = (self.entry_price - self.exit_price) * self.position_size

        # Subtract costs
        self.pnl = gross_pnl - self.commission - self.slippage
        self.pnl_percent = (self.pnl / (self.entry_price * self.position_size)) * 100

        # Calculate duration
        if self.exit_time and self.entry_time:
            self.duration = (self.exit_time - self.entry_time).total_seconds() / 3600

    def is_winner(self) -> bool:
        """Check if trade was profitable."""
        return self.pnl > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert trade to dictionary."""
        return {
            'trade_id': self.trade_id,
            'instrument': self.instrument,
            'side': self.side.value,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'entry_price': round(self.entry_price, 4),
            'position_size': round(self.position_size, 4),
            'stop_loss': round(self.stop_loss, 4),
            'take_profit': round(self.take_profit, 4),
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'exit_price': round(self.exit_price, 4) if self.exit_price else None,
            'exit_reason': self.exit_reason.value if self.exit_reason else None,
            'commission': round(self.commission, 4),
            'slippage': round(self.slippage, 4),
            'pnl': round(self.pnl, 4),
            'pnl_percent': round(self.pnl_percent, 2),
            'mae': round(self.mae, 4),
            'mfe': round(self.mfe, 4),
            'duration': round(self.duration, 2) if self.duration else None,
            'signal_confidence': round(self.signal_confidence, 2)
        }


@dataclass
class PerformanceMetrics:
    """
    Comprehensive performance metrics for backtest results.

    Attributes:
        total_return: Total return as percentage
        annualized_return: Annualized return as percentage
        sharpe_ratio: Sharpe ratio (risk-adjusted return)
        sortino_ratio: Sortino ratio (downside risk-adjusted return)
        max_drawdown: Maximum drawdown as percentage
        max_drawdown_duration: Maximum drawdown duration in days
        win_rate: Percentage of winning trades
        profit_factor: Ratio of gross profit to gross loss
        avg_win: Average winning trade P&L
        avg_loss: Average losing trade P&L
        avg_win_percent: Average winning trade percentage
        avg_loss_percent: Average losing trade percentage
        largest_win: Largest winning trade P&L
        largest_loss: Largest losing trade P&L
        avg_trade_duration: Average trade duration in hours
        total_trades: Total number of trades
        winning_trades: Number of winning trades
        losing_trades: Number of losing trades
        expectancy: Average expected profit per trade
        risk_reward_ratio: Average risk/reward ratio achieved
        recovery_factor: Ratio of total return to max drawdown
        calmar_ratio: Ratio of annualized return to max drawdown
    """
    total_return: float = 0.0
    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_win_percent: float = 0.0
    avg_loss_percent: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    avg_trade_duration: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    expectancy: float = 0.0
    risk_reward_ratio: float = 0.0
    recovery_factor: float = 0.0
    calmar_ratio: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        """Convert metrics to dictionary."""
        return {
            'total_return': round(self.total_return, 2),
            'annualized_return': round(self.annualized_return, 2),
            'sharpe_ratio': round(self.sharpe_ratio, 3),
            'sortino_ratio': round(self.sortino_ratio, 3),
            'max_drawdown': round(self.max_drawdown, 2),
            'max_drawdown_duration': round(self.max_drawdown_duration, 2),
            'win_rate': round(self.win_rate, 2),
            'profit_factor': round(self.profit_factor, 3),
            'avg_win': round(self.avg_win, 4),
            'avg_loss': round(self.avg_loss, 4),
            'avg_win_percent': round(self.avg_win_percent, 2),
            'avg_loss_percent': round(self.avg_loss_percent, 2),
            'largest_win': round(self.largest_win, 4),
            'largest_loss': round(self.largest_loss, 4),
            'avg_trade_duration': round(self.avg_trade_duration, 2),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'expectancy': round(self.expectancy, 4),
            'risk_reward_ratio': round(self.risk_reward_ratio, 3),
            'recovery_factor': round(self.recovery_factor, 3),
            'calmar_ratio': round(self.calmar_ratio, 3)
        }


class PortfolioTracker:
    """
    Tracks virtual portfolio state including cash balance, positions, and equity.

    Manages position sizing, entry/exit tracking, and transaction costs.
    """

    def __init__(
        self,
        initial_capital: float,
        commission_rate: float = 0.001,
        slippage_rate: float = 0.0005,
        risk_per_trade: float = 0.02
    ):
        """
        Initialize portfolio tracker.

        Args:
            initial_capital: Starting capital
            commission_rate: Commission as decimal (e.g., 0.001 = 0.1%)
            slippage_rate: Slippage as decimal (e.g., 0.0005 = 0.05%)
            risk_per_trade: Risk per trade as decimal (e.g., 0.02 = 2%)
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.risk_per_trade = risk_per_trade

        self.positions: Dict[str, Trade] = {}
        self.equity_history: List[Dict[str, float]] = []
        self.trade_counter = 0

        logger.info(
            f"Portfolio initialized: ${initial_capital:,.2f}, "
            f"commission: {commission_rate*100:.3f}%, "
            f"slippage: {slippage_rate*100:.3f}%, "
            f"risk: {risk_per_trade*100:.1f}%"
        )

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        signal_confidence: float = 1.0
    ) -> float:
        """
        Calculate position size based on risk parameters.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            signal_confidence: Signal confidence (0-1), scales position size

        Returns:
            Position size in units
        """
        # Calculate risk amount
        risk_amount = self.cash * self.risk_per_trade * signal_confidence

        # Calculate risk per unit
        risk_per_unit = abs(entry_price - stop_loss)

        if risk_per_unit == 0:
            logger.warning("Stop loss equals entry price, returning minimal position size")
            return 0.01

        # Calculate position size
        position_size = risk_amount / risk_per_unit

        # Ensure we have enough capital
        required_capital = position_size * entry_price
        if required_capital > self.cash * 0.95:  # Don't use more than 95% of cash
            position_size = (self.cash * 0.95) / entry_price

        return position_size

    def open_position(
        self,
        instrument: str,
        side: PositionSide,
        entry_time: datetime,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        signal_confidence: float = 1.0
    ) -> Optional[Trade]:
        """
        Open a new position.

        Args:
            instrument: Trading instrument
            side: Position side (LONG/SHORT)
            entry_time: Entry timestamp
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            signal_confidence: Signal confidence score

        Returns:
            Trade object if position opened, None otherwise
        """
        # Check if position already exists
        if instrument in self.positions:
            logger.warning(f"Position already exists for {instrument}")
            return None

        # Calculate position size
        position_size = self.calculate_position_size(
            entry_price, stop_loss, signal_confidence
        )

        if position_size <= 0:
            logger.warning(f"Invalid position size: {position_size}")
            return None

        # Calculate costs
        position_value = position_size * entry_price
        commission = position_value * self.commission_rate
        slippage = position_value * self.slippage_rate

        total_cost = position_value + commission + slippage

        # Check if we have enough cash
        if total_cost > self.cash:
            logger.warning(
                f"Insufficient cash: ${self.cash:,.2f} < ${total_cost:,.2f}"
            )
            return None

        # Create trade
        self.trade_counter += 1
        trade = Trade(
            trade_id=self.trade_counter,
            instrument=instrument,
            side=side,
            entry_time=entry_time,
            entry_price=entry_price,
            position_size=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            commission=commission,
            slippage=slippage,
            signal_confidence=signal_confidence
        )

        # Update cash and positions
        self.cash -= total_cost
        self.positions[instrument] = trade

        logger.debug(
            f"Opened {side.value} position: {instrument}, "
            f"size: {position_size:.4f}, price: ${entry_price:.4f}"
        )

        return trade

    def close_position(
        self,
        instrument: str,
        exit_time: datetime,
        exit_price: float,
        exit_reason: ExitReason
    ) -> Optional[Trade]:
        """
        Close an existing position.

        Args:
            instrument: Trading instrument
            exit_time: Exit timestamp
            exit_price: Exit price
            exit_reason: Reason for exit

        Returns:
            Closed Trade object if successful, None otherwise
        """
        if instrument not in self.positions:
            logger.warning(f"No position exists for {instrument}")
            return None

        trade = self.positions[instrument]

        # Update trade with exit information
        trade.exit_time = exit_time
        trade.exit_price = exit_price
        trade.exit_reason = exit_reason

        # Calculate exit costs
        position_value = trade.position_size * exit_price
        exit_commission = position_value * self.commission_rate
        exit_slippage = position_value * self.slippage_rate

        trade.commission += exit_commission
        trade.slippage += exit_slippage

        # Calculate P&L
        trade.calculate_pnl()

        # Update cash
        if trade.side == PositionSide.LONG:
            self.cash += position_value - exit_commission - exit_slippage
        else:  # SHORT
            # For short, we get back the initial value plus profit (or minus loss)
            initial_value = trade.position_size * trade.entry_price
            self.cash += initial_value + trade.pnl

        # Remove from active positions
        del self.positions[instrument]

        logger.debug(
            f"Closed {trade.side.value} position: {instrument}, "
            f"P&L: ${trade.pnl:,.2f} ({trade.pnl_percent:.2f}%), "
            f"reason: {exit_reason.value}"
        )

        return trade

    def update_position_extremes(
        self,
        instrument: str,
        current_price: float
    ) -> None:
        """
        Update MAE and MFE for an open position.

        Args:
            instrument: Trading instrument
            current_price: Current price
        """
        if instrument not in self.positions:
            return

        trade = self.positions[instrument]

        if trade.side == PositionSide.LONG:
            # Calculate current P&L
            current_pnl = (current_price - trade.entry_price) * trade.position_size

            # Update extremes
            if current_pnl < trade.mae:
                trade.mae = current_pnl
            if current_pnl > trade.mfe:
                trade.mfe = current_pnl
        else:  # SHORT
            current_pnl = (trade.entry_price - current_price) * trade.position_size

            if current_pnl < trade.mae:
                trade.mae = current_pnl
            if current_pnl > trade.mfe:
                trade.mfe = current_pnl

    def get_equity(self) -> float:
        """
        Get current total equity (cash + open positions value).

        Returns:
            Current equity
        """
        equity = self.cash

        # Add value of open positions (using entry price as approximation)
        for trade in self.positions.values():
            equity += trade.position_size * trade.entry_price

        return equity

    def record_equity(self, timestamp: datetime) -> None:
        """
        Record current equity for equity curve.

        Args:
            timestamp: Current timestamp
        """
        self.equity_history.append({
            'timestamp': timestamp,
            'equity': self.get_equity(),
            'cash': self.cash,
            'open_positions': len(self.positions)
        })

    def get_equity_curve(self) -> pd.DataFrame:
        """
        Get equity curve as DataFrame.

        Returns:
            DataFrame with timestamp and equity columns
        """
        if not self.equity_history:
            return pd.DataFrame()

        df = pd.DataFrame(self.equity_history)
        df['returns'] = df['equity'].pct_change()
        df['drawdown'] = (df['equity'] / df['equity'].cummax()) - 1

        return df


class Strategy:
    """
    Base class for trading strategies.

    Subclass this to implement custom strategies with specific signal generation logic.
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize strategy.

        Args:
            name: Strategy name
            config: Strategy configuration parameters
        """
        self.name = name
        self.config = config or {}
        self.state: Dict[str, Any] = {}

        logger.info(f"Strategy initialized: {name}")

    def generate_signal(
        self,
        data: pd.DataFrame,
        timestamp: datetime
    ) -> Optional[TradingSignal]:
        """
        Generate trading signal based on current data.

        Args:
            data: Historical price data up to current timestamp
            timestamp: Current timestamp

        Returns:
            TradingSignal if signal generated, None otherwise

        Note:
            This is an abstract method that should be overridden in subclasses.
        """
        raise NotImplementedError("Subclasses must implement generate_signal method")

    def on_trade_opened(self, trade: Trade) -> None:
        """
        Callback when trade is opened.

        Args:
            trade: Opened trade
        """
        pass

    def on_trade_closed(self, trade: Trade) -> None:
        """
        Callback when trade is closed.

        Args:
            trade: Closed trade
        """
        pass

    def reset_state(self) -> None:
        """Reset strategy state (useful for walk-forward analysis)."""
        self.state = {}


class SignalStrategy(Strategy):
    """
    Strategy implementation using SignalGenerator for signal generation.

    This is a concrete implementation that can be used directly with the
    existing SignalGenerator class.
    """

    def __init__(
        self,
        name: str = "SignalGenerator",
        risk_percent: float = 2.0,
        min_confidence: float = 50.0,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize SignalGenerator strategy.

        Args:
            name: Strategy name
            risk_percent: Risk percentage per trade
            min_confidence: Minimum signal confidence to trade
            config: Additional configuration
        """
        super().__init__(name, config)
        self.risk_percent = risk_percent
        self.min_confidence = min_confidence

    def generate_signal(
        self,
        data: pd.DataFrame,
        timestamp: datetime
    ) -> Optional[TradingSignal]:
        """
        Generate signal using SignalGenerator.

        Args:
            data: Historical price data
            timestamp: Current timestamp

        Returns:
            TradingSignal if valid signal generated, None otherwise
        """
        try:
            # Need at least 50 bars for signal generation
            if len(data) < 50:
                return None

            # Create signal generator
            signal_gen = SignalGenerator(data, self.risk_percent)

            # Generate signal
            signal = signal_gen.generate_signal()

            # Filter by confidence
            if signal.confidence < self.min_confidence:
                return None

            # Filter out HOLD and NO_SIGNAL
            if signal.signal_type in [SignalType.HOLD, SignalType.NO_SIGNAL]:
                return None

            return signal

        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return None


@dataclass
class BacktestResults:
    """
    Container for backtest results including trades, metrics, and equity curve.

    Provides methods for result analysis and visualization.
    """
    strategy_name: str
    instrument: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_equity: float
    trades: List[Trade] = field(default_factory=list)
    equity_curve: pd.DataFrame = field(default_factory=pd.DataFrame)
    metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)

    def calculate_metrics(self) -> None:
        """Calculate comprehensive performance metrics from trades and equity curve."""
        if not self.trades:
            logger.warning("No trades to calculate metrics from")
            return

        # Filter completed trades
        completed_trades = [t for t in self.trades if t.exit_time is not None]

        if not completed_trades:
            logger.warning("No completed trades")
            return

        # Basic metrics
        self.metrics.total_trades = len(completed_trades)

        # Separate winners and losers
        winners = [t for t in completed_trades if t.is_winner()]
        losers = [t for t in completed_trades if not t.is_winner()]

        self.metrics.winning_trades = len(winners)
        self.metrics.losing_trades = len(losers)

        # Win rate
        self.metrics.win_rate = (len(winners) / len(completed_trades)) * 100

        # P&L statistics
        if winners:
            self.metrics.avg_win = np.mean([t.pnl for t in winners])
            self.metrics.avg_win_percent = np.mean([t.pnl_percent for t in winners])
            self.metrics.largest_win = max([t.pnl for t in winners])

        if losers:
            self.metrics.avg_loss = np.mean([t.pnl for t in losers])
            self.metrics.avg_loss_percent = np.mean([t.pnl_percent for t in losers])
            self.metrics.largest_loss = min([t.pnl for t in losers])

        # Profit factor
        gross_profit = sum([t.pnl for t in winners]) if winners else 0
        gross_loss = abs(sum([t.pnl for t in losers])) if losers else 0

        if gross_loss > 0:
            self.metrics.profit_factor = gross_profit / gross_loss

        # Expectancy
        self.metrics.expectancy = np.mean([t.pnl for t in completed_trades])

        # Risk/Reward
        if self.metrics.avg_loss != 0:
            self.metrics.risk_reward_ratio = abs(self.metrics.avg_win / self.metrics.avg_loss)

        # Trade duration
        durations = [t.duration for t in completed_trades if t.duration is not None]
        if durations:
            self.metrics.avg_trade_duration = np.mean(durations)

        # Return metrics
        self.metrics.total_return = ((self.final_equity - self.initial_capital) /
                                     self.initial_capital) * 100

        # Calculate annualized return
        if not self.equity_curve.empty:
            days = (self.end_date - self.start_date).days
            if days > 0:
                years = days / 365.25
                self.metrics.annualized_return = (
                    ((self.final_equity / self.initial_capital) ** (1 / years)) - 1
                ) * 100

            # Sharpe ratio (assuming daily returns)
            if 'returns' in self.equity_curve.columns:
                returns = self.equity_curve['returns'].dropna()
                if len(returns) > 0 and returns.std() > 0:
                    # Annualized Sharpe (assuming 252 trading days)
                    self.metrics.sharpe_ratio = (
                        (returns.mean() / returns.std()) * np.sqrt(252)
                    )

                    # Sortino ratio (uses only downside deviation)
                    downside_returns = returns[returns < 0]
                    if len(downside_returns) > 0 and downside_returns.std() > 0:
                        self.metrics.sortino_ratio = (
                            (returns.mean() / downside_returns.std()) * np.sqrt(252)
                        )

            # Maximum drawdown
            if 'drawdown' in self.equity_curve.columns:
                self.metrics.max_drawdown = self.equity_curve['drawdown'].min() * 100

                # Find drawdown duration
                drawdowns = self.equity_curve['drawdown'].values
                in_drawdown = False
                current_dd_start = 0
                max_dd_duration = 0

                for i, dd in enumerate(drawdowns):
                    if dd < 0 and not in_drawdown:
                        in_drawdown = True
                        current_dd_start = i
                    elif dd >= 0 and in_drawdown:
                        in_drawdown = False
                        dd_duration = i - current_dd_start
                        max_dd_duration = max(max_dd_duration, dd_duration)

                # Convert to days (assuming each row is one bar)
                self.metrics.max_drawdown_duration = max_dd_duration

        # Recovery and Calmar ratios
        if self.metrics.max_drawdown != 0:
            self.metrics.recovery_factor = (
                self.metrics.total_return / abs(self.metrics.max_drawdown)
            )
            self.metrics.calmar_ratio = (
                self.metrics.annualized_return / abs(self.metrics.max_drawdown)
            )

        logger.info(
            f"Metrics calculated: {self.metrics.total_trades} trades, "
            f"{self.metrics.win_rate:.2f}% win rate, "
            f"{self.metrics.total_return:.2f}% return"
        )

    def plot_equity_curve(
        self,
        save_path: Optional[str] = None,
        show: bool = True
    ) -> None:
        """
        Plot equity curve with drawdown.

        Args:
            save_path: Path to save plot (optional)
            show: Whether to display plot
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("Matplotlib not available, cannot plot equity curve")
            return

        if self.equity_curve.empty:
            logger.warning("No equity data to plot")
            return

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

        # Equity curve
        ax1.plot(
            self.equity_curve['timestamp'],
            self.equity_curve['equity'],
            label='Equity',
            linewidth=2,
            color='blue'
        )
        ax1.axhline(
            y=self.initial_capital,
            color='gray',
            linestyle='--',
            label='Initial Capital'
        )
        ax1.set_ylabel('Equity ($)', fontsize=12)
        ax1.set_title(
            f'{self.strategy_name} - {self.instrument}\n'
            f'Return: {self.metrics.total_return:.2f}% | '
            f'Sharpe: {self.metrics.sharpe_ratio:.2f} | '
            f'Max DD: {self.metrics.max_drawdown:.2f}%',
            fontsize=14,
            fontweight='bold'
        )
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Drawdown
        ax2.fill_between(
            self.equity_curve['timestamp'],
            self.equity_curve['drawdown'] * 100,
            0,
            color='red',
            alpha=0.3,
            label='Drawdown'
        )
        ax2.set_ylabel('Drawdown (%)', fontsize=12)
        ax2.set_xlabel('Date', fontsize=12)
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # Format x-axis
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Equity curve saved to {save_path}")

        if show:
            plt.show()
        else:
            plt.close()

    def plot_trade_analysis(
        self,
        save_path: Optional[str] = None,
        show: bool = True
    ) -> None:
        """
        Plot trade analysis including P&L distribution and trade timeline.

        Args:
            save_path: Path to save plot (optional)
            show: Whether to display plot
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("Matplotlib not available, cannot plot trade analysis")
            return

        if not self.trades:
            logger.warning("No trades to analyze")
            return

        completed_trades = [t for t in self.trades if t.exit_time is not None]

        if not completed_trades:
            logger.warning("No completed trades to analyze")
            return

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

        # P&L distribution
        pnl_values = [t.pnl for t in completed_trades]
        ax1.hist(pnl_values, bins=30, color='steelblue', edgecolor='black', alpha=0.7)
        ax1.axvline(x=0, color='red', linestyle='--', linewidth=2)
        ax1.set_xlabel('P&L ($)', fontsize=11)
        ax1.set_ylabel('Frequency', fontsize=11)
        ax1.set_title('P&L Distribution', fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3)

        # P&L percentage distribution
        pnl_pct_values = [t.pnl_percent for t in completed_trades]
        ax2.hist(pnl_pct_values, bins=30, color='coral', edgecolor='black', alpha=0.7)
        ax2.axvline(x=0, color='red', linestyle='--', linewidth=2)
        ax2.set_xlabel('P&L (%)', fontsize=11)
        ax2.set_ylabel('Frequency', fontsize=11)
        ax2.set_title('P&L Percentage Distribution', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)

        # Cumulative P&L
        cumulative_pnl = np.cumsum(pnl_values)
        trade_numbers = list(range(1, len(cumulative_pnl) + 1))
        ax3.plot(trade_numbers, cumulative_pnl, linewidth=2, color='green')
        ax3.axhline(y=0, color='gray', linestyle='--')
        ax3.set_xlabel('Trade Number', fontsize=11)
        ax3.set_ylabel('Cumulative P&L ($)', fontsize=11)
        ax3.set_title('Cumulative P&L', fontsize=12, fontweight='bold')
        ax3.grid(True, alpha=0.3)

        # Win/Loss by position side
        long_trades = [t for t in completed_trades if t.side == PositionSide.LONG]
        short_trades = [t for t in completed_trades if t.side == PositionSide.SHORT]

        long_wins = len([t for t in long_trades if t.is_winner()])
        long_losses = len(long_trades) - long_wins
        short_wins = len([t for t in short_trades if t.is_winner()])
        short_losses = len(short_trades) - short_wins

        x = np.arange(2)
        width = 0.35

        ax4.bar(x - width/2, [long_wins, short_wins], width, label='Wins', color='green', alpha=0.7)
        ax4.bar(x + width/2, [long_losses, short_losses], width, label='Losses', color='red', alpha=0.7)
        ax4.set_xlabel('Position Side', fontsize=11)
        ax4.set_ylabel('Number of Trades', fontsize=11)
        ax4.set_title('Wins/Losses by Position Side', fontsize=12, fontweight='bold')
        ax4.set_xticks(x)
        ax4.set_xticklabels(['Long', 'Short'])
        ax4.legend()
        ax4.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Trade analysis saved to {save_path}")

        if show:
            plt.show()
        else:
            plt.close()

    def export_trades_csv(self, filepath: str) -> None:
        """
        Export trades to CSV file.

        Args:
            filepath: Path to CSV file
        """
        if not self.trades:
            logger.warning("No trades to export")
            return

        trades_data = [t.to_dict() for t in self.trades]
        df = pd.DataFrame(trades_data)
        df.to_csv(filepath, index=False)

        logger.info(f"Exported {len(self.trades)} trades to {filepath}")

    def export_metrics_json(self, filepath: str) -> None:
        """
        Export performance metrics to JSON file.

        Args:
            filepath: Path to JSON file
        """
        metrics_dict = {
            'strategy': self.strategy_name,
            'instrument': self.instrument,
            'period': {
                'start': self.start_date.isoformat(),
                'end': self.end_date.isoformat()
            },
            'capital': {
                'initial': self.initial_capital,
                'final': self.final_equity
            },
            'metrics': self.metrics.to_dict()
        }

        with open(filepath, 'w') as f:
            json.dump(metrics_dict, f, indent=2)

        logger.info(f"Exported metrics to {filepath}")

    def generate_report(self) -> str:
        """
        Generate text report of backtest results.

        Returns:
            Formatted report string
        """
        report_lines = [
            "=" * 80,
            f"BACKTEST REPORT: {self.strategy_name}",
            "=" * 80,
            f"\nInstrument: {self.instrument}",
            f"Period: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}",
            f"Initial Capital: ${self.initial_capital:,.2f}",
            f"Final Equity: ${self.final_equity:,.2f}",
            f"\n" + "-" * 80,
            "PERFORMANCE METRICS",
            "-" * 80,
            f"Total Return: {self.metrics.total_return:.2f}%",
            f"Annualized Return: {self.metrics.annualized_return:.2f}%",
            f"Sharpe Ratio: {self.metrics.sharpe_ratio:.3f}",
            f"Sortino Ratio: {self.metrics.sortino_ratio:.3f}",
            f"Max Drawdown: {self.metrics.max_drawdown:.2f}%",
            f"Max Drawdown Duration: {self.metrics.max_drawdown_duration:.0f} bars",
            f"Recovery Factor: {self.metrics.recovery_factor:.3f}",
            f"Calmar Ratio: {self.metrics.calmar_ratio:.3f}",
            f"\n" + "-" * 80,
            "TRADE STATISTICS",
            "-" * 80,
            f"Total Trades: {self.metrics.total_trades}",
            f"Winning Trades: {self.metrics.winning_trades}",
            f"Losing Trades: {self.metrics.losing_trades}",
            f"Win Rate: {self.metrics.win_rate:.2f}%",
            f"Profit Factor: {self.metrics.profit_factor:.3f}",
            f"Expectancy: ${self.metrics.expectancy:.2f}",
            f"Risk/Reward Ratio: {self.metrics.risk_reward_ratio:.3f}",
            f"\n" + "-" * 80,
            "TRADE DETAILS",
            "-" * 80,
            f"Average Win: ${self.metrics.avg_win:.2f} ({self.metrics.avg_win_percent:.2f}%)",
            f"Average Loss: ${self.metrics.avg_loss:.2f} ({self.metrics.avg_loss_percent:.2f}%)",
            f"Largest Win: ${self.metrics.largest_win:.2f}",
            f"Largest Loss: ${self.metrics.largest_loss:.2f}",
            f"Average Trade Duration: {self.metrics.avg_trade_duration:.2f} hours",
            "=" * 80
        ]

        return "\n".join(report_lines)


class Backtester:
    """
    Main backtesting engine for strategy testing and validation.

    Supports:
    - Historical data replay without look-ahead bias
    - Multiple data sources (database, CSV)
    - Transaction cost modeling
    - Walk-forward analysis
    - Parameter optimization
    """

    def __init__(
        self,
        strategy: Strategy,
        initial_capital: float = 10000.0,
        commission_rate: float = 0.001,
        slippage_rate: float = 0.0005,
        risk_per_trade: float = 0.02
    ):
        """
        Initialize backtester.

        Args:
            strategy: Trading strategy to backtest
            initial_capital: Starting capital
            commission_rate: Commission as decimal
            slippage_rate: Slippage as decimal
            risk_per_trade: Risk per trade as decimal
        """
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.risk_per_trade = risk_per_trade

        self.portfolio: Optional[PortfolioTracker] = None
        self.data: Optional[pd.DataFrame] = None

        logger.info(
            f"Backtester initialized with {strategy.name} strategy, "
            f"${initial_capital:,.2f} capital"
        )

    def load_data_from_database(
        self,
        instrument: str,
        timeframe: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Load historical data from TimescaleDB.

        Args:
            instrument: Trading instrument
            timeframe: Timeframe (e.g., 'H1', 'D1')
            start_date: Start date filter
            end_date: End date filter

        Returns:
            DataFrame with OHLCV data
        """
        try:
            db = get_db()

            with db.session_scope() as session:
                query = session.query(MarketData).filter(
                    MarketData.instrument == instrument,
                    MarketData.timeframe == timeframe
                )

                if start_date:
                    query = query.filter(MarketData.timestamp >= start_date)

                if end_date:
                    query = query.filter(MarketData.timestamp <= end_date)

                query = query.order_by(MarketData.timestamp.asc())

                results = query.all()

                if not results:
                    logger.warning(
                        f"No data found for {instrument} {timeframe} "
                        f"between {start_date} and {end_date}"
                    )
                    return pd.DataFrame()

                # Convert to DataFrame
                data = []
                for row in results:
                    data.append({
                        'timestamp': row.timestamp,
                        'open': row.open,
                        'high': row.high,
                        'low': row.low,
                        'close': row.close,
                        'volume': row.volume
                    })

                df = pd.DataFrame(data)
                df.set_index('timestamp', inplace=True)

                logger.info(
                    f"Loaded {len(df)} bars for {instrument} {timeframe} "
                    f"from database"
                )

                return df

        except Exception as e:
            logger.error(f"Error loading data from database: {e}")
            return pd.DataFrame()

    def load_data_from_csv(
        self,
        filepath: str,
        date_column: str = 'timestamp',
        parse_dates: bool = True
    ) -> pd.DataFrame:
        """
        Load historical data from CSV file.

        Args:
            filepath: Path to CSV file
            date_column: Name of date/timestamp column
            parse_dates: Whether to parse dates

        Returns:
            DataFrame with OHLCV data
        """
        try:
            df = pd.read_csv(filepath)

            # Parse dates if requested
            if parse_dates and date_column in df.columns:
                df[date_column] = pd.to_datetime(df[date_column])
                df.set_index(date_column, inplace=True)

            # Ensure required columns exist
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in df.columns]

            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")

            # Sort by date
            df.sort_index(inplace=True)

            logger.info(f"Loaded {len(df)} bars from {filepath}")

            return df

        except Exception as e:
            logger.error(f"Error loading data from CSV: {e}")
            return pd.DataFrame()

    def run(
        self,
        data: pd.DataFrame,
        instrument: str = "UNKNOWN"
    ) -> BacktestResults:
        """
        Run backtest on historical data.

        Args:
            data: Historical OHLCV data with datetime index
            instrument: Instrument name for reporting

        Returns:
            BacktestResults object with trades, metrics, and equity curve
        """
        if data.empty:
            raise ValueError("Cannot run backtest on empty data")

        logger.info(
            f"Starting backtest: {instrument}, "
            f"{len(data)} bars, "
            f"{data.index[0]} to {data.index[-1]}"
        )

        # Reset strategy state
        self.strategy.reset_state()

        # Initialize portfolio
        self.portfolio = PortfolioTracker(
            initial_capital=self.initial_capital,
            commission_rate=self.commission_rate,
            slippage_rate=self.slippage_rate,
            risk_per_trade=self.risk_per_trade
        )

        self.data = data
        trades: List[Trade] = []

        # Iterate through data chronologically
        for i in range(50, len(data)):  # Start at 50 to have enough history
            current_timestamp = data.index[i]
            current_bar = data.iloc[i]

            # Get historical data up to current point (no look-ahead)
            historical_data = data.iloc[:i+1].copy()

            # Record equity
            self.portfolio.record_equity(current_timestamp)

            # Check for position exits first
            if instrument in self.portfolio.positions:
                trade = self.portfolio.positions[instrument]

                # Update MAE/MFE
                self.portfolio.update_position_extremes(
                    instrument,
                    current_bar['close']
                )

                # Check stop loss and take profit
                exit_reason = None
                exit_price = None

                if trade.side == PositionSide.LONG:
                    if current_bar['low'] <= trade.stop_loss:
                        exit_reason = ExitReason.STOP_HIT
                        exit_price = trade.stop_loss
                    elif current_bar['high'] >= trade.take_profit:
                        exit_reason = ExitReason.TARGET_HIT
                        exit_price = trade.take_profit
                else:  # SHORT
                    if current_bar['high'] >= trade.stop_loss:
                        exit_reason = ExitReason.STOP_HIT
                        exit_price = trade.stop_loss
                    elif current_bar['low'] <= trade.take_profit:
                        exit_reason = ExitReason.TARGET_HIT
                        exit_price = trade.take_profit

                # Close position if exit triggered
                if exit_reason:
                    closed_trade = self.portfolio.close_position(
                        instrument,
                        current_timestamp,
                        exit_price,
                        exit_reason
                    )

                    if closed_trade:
                        trades.append(closed_trade)
                        self.strategy.on_trade_closed(closed_trade)

            # Generate new signals if no position open
            if instrument not in self.portfolio.positions:
                signal = self.strategy.generate_signal(
                    historical_data,
                    current_timestamp
                )

                if signal:
                    # Determine position side
                    if signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
                        side = PositionSide.LONG
                    elif signal.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
                        side = PositionSide.SHORT
                    else:
                        continue

                    # Open position
                    trade = self.portfolio.open_position(
                        instrument=instrument,
                        side=side,
                        entry_time=current_timestamp,
                        entry_price=signal.entry_price,
                        stop_loss=signal.stop_loss,
                        take_profit=signal.target_1,
                        signal_confidence=signal.confidence / 100.0
                    )

                    if trade:
                        self.strategy.on_trade_opened(trade)

        # Close any remaining open positions
        for instrument_name in list(self.portfolio.positions.keys()):
            final_bar = data.iloc[-1]
            closed_trade = self.portfolio.close_position(
                instrument_name,
                data.index[-1],
                final_bar['close'],
                ExitReason.END_OF_DATA
            )

            if closed_trade:
                trades.append(closed_trade)
                self.strategy.on_trade_closed(closed_trade)

        # Create results
        results = BacktestResults(
            strategy_name=self.strategy.name,
            instrument=instrument,
            start_date=data.index[0],
            end_date=data.index[-1],
            initial_capital=self.initial_capital,
            final_equity=self.portfolio.get_equity(),
            trades=trades,
            equity_curve=self.portfolio.get_equity_curve()
        )

        # Calculate metrics
        results.calculate_metrics()

        logger.info(
            f"Backtest complete: {len(trades)} trades, "
            f"{results.metrics.total_return:.2f}% return"
        )

        return results

    def walk_forward_analysis(
        self,
        data: pd.DataFrame,
        instrument: str,
        train_period: int,
        test_period: int,
        step_size: Optional[int] = None
    ) -> List[BacktestResults]:
        """
        Perform walk-forward analysis.

        Args:
            data: Historical OHLCV data
            instrument: Instrument name
            train_period: Number of bars for training
            test_period: Number of bars for testing
            step_size: Number of bars to step forward (default: test_period)

        Returns:
            List of BacktestResults for each walk-forward period
        """
        if step_size is None:
            step_size = test_period

        results_list = []
        start_idx = 0

        logger.info(
            f"Starting walk-forward analysis: train={train_period}, "
            f"test={test_period}, step={step_size}"
        )

        while start_idx + train_period + test_period <= len(data):
            # Define periods
            train_start = start_idx
            train_end = start_idx + train_period
            test_start = train_end
            test_end = test_start + test_period

            # Get train and test data
            train_data = data.iloc[train_start:train_end]
            test_data = data.iloc[test_start:test_end]

            logger.info(
                f"Walk-forward iteration: "
                f"train {train_data.index[0]} to {train_data.index[-1]}, "
                f"test {test_data.index[0]} to {test_data.index[-1]}"
            )

            # Run backtest on test period
            # Note: In real walk-forward, you would optimize strategy parameters
            # on train_data and test on test_data
            results = self.run(test_data, instrument)
            results_list.append(results)

            # Step forward
            start_idx += step_size

        logger.info(f"Walk-forward analysis complete: {len(results_list)} periods")

        return results_list


# Utility functions

def load_data_from_timescaledb(
    instrument: str,
    timeframe: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Utility function to load data from TimescaleDB.

    Args:
        instrument: Trading instrument
        timeframe: Timeframe
        start_date: Start date filter
        end_date: End date filter

    Returns:
        DataFrame with OHLCV data
    """
    backtester = Backtester(Strategy("dummy"))
    return backtester.load_data_from_database(
        instrument, timeframe, start_date, end_date
    )


def run_simple_backtest(
    data: pd.DataFrame,
    instrument: str = "UNKNOWN",
    initial_capital: float = 10000.0,
    strategy_name: str = "SignalGenerator",
    min_confidence: float = 50.0
) -> BacktestResults:
    """
    Run a simple backtest with default SignalGenerator strategy.

    Args:
        data: Historical OHLCV data
        instrument: Instrument name
        initial_capital: Starting capital
        strategy_name: Strategy name for reporting
        min_confidence: Minimum signal confidence

    Returns:
        BacktestResults object
    """
    strategy = SignalStrategy(
        name=strategy_name,
        min_confidence=min_confidence
    )

    backtester = Backtester(
        strategy=strategy,
        initial_capital=initial_capital
    )

    return backtester.run(data, instrument)


if __name__ == '__main__':
    # Example usage
    print("Backtesting Framework for ScreenerIII")
    print("=" * 60)
    print("\nThis module provides comprehensive backtesting capabilities.")
    print("\nExample usage:")
    print("""
    from analysis.backtesting import Backtester, SignalStrategy

    # Load data
    data = pd.read_csv('historical_data.csv', index_col='timestamp', parse_dates=True)

    # Create strategy
    strategy = SignalStrategy(min_confidence=60.0)

    # Create backtester
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        commission_rate=0.001,
        slippage_rate=0.0005
    )

    # Run backtest
    results = backtester.run(data, instrument='EUR_USD')

    # Analyze results
    print(results.generate_report())
    results.plot_equity_curve()
    results.plot_trade_analysis()
    results.export_trades_csv('trades.csv')
    results.export_metrics_json('metrics.json')
    """)
