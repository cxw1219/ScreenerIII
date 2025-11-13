"""
Paper Trading Simulator Module

This module provides a comprehensive paper trading system for testing trading strategies
without risking real capital. It includes realistic execution simulation, risk management,
position tracking, and performance analytics.

Features:
- Multi-asset support with leverage
- Realistic execution with slippage and spreads
- Advanced order types (MARKET, LIMIT, STOP, STOP_LIMIT)
- Comprehensive risk management
- Trade journal and performance tracking
- Integration with signal generators

Author: ScreenerIII
License: MIT
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union
import pandas as pd
import numpy as np
import logging
import json
import csv
from pathlib import Path
import uuid

# Configure logging
logger = logging.getLogger(__name__)


class Direction(Enum):
    """Position direction enumeration."""
    LONG = "LONG"
    SHORT = "SHORT"


class OrderType(Enum):
    """Order type enumeration."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class TimeInForce(Enum):
    """Time in force enumeration."""
    GTC = "GTC"  # Good Till Cancelled
    DAY = "DAY"  # Good for the day
    IOC = "IOC"  # Immediate Or Cancel
    FOK = "FOK"  # Fill Or Kill


class PositionStatus(Enum):
    """Position status enumeration."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class CloseReason(Enum):
    """Position close reason enumeration."""
    MANUAL = "MANUAL"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    MARGIN_CALL = "MARGIN_CALL"
    TIME_LIMIT = "TIME_LIMIT"


@dataclass
class Position:
    """
    Represents a trading position.

    Attributes:
        position_id: Unique position identifier
        instrument: Trading instrument symbol
        direction: LONG or SHORT
        entry_price: Entry price
        entry_time: Entry timestamp
        size: Position size in units
        current_price: Current market price
        stop_loss: Stop loss price
        take_profit: Take profit price
        leverage: Leverage used (1.0 = no leverage)
        commission_paid: Total commission paid
        status: Position status
        close_price: Closing price (if closed)
        close_time: Close timestamp (if closed)
        close_reason: Reason for closing
        max_adverse_excursion: Maximum loss during position life
        max_favorable_excursion: Maximum profit during position life
        unrealized_pnl: Current unrealized P&L
        realized_pnl: Realized P&L after closing
    """
    position_id: str
    instrument: str
    direction: Direction
    entry_price: float
    entry_time: datetime
    size: float
    current_price: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    leverage: float = 1.0
    commission_paid: float = 0.0
    status: PositionStatus = PositionStatus.OPEN
    close_price: Optional[float] = None
    close_time: Optional[datetime] = None
    close_reason: Optional[CloseReason] = None
    max_adverse_excursion: float = 0.0
    max_favorable_excursion: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        """Initialize current price to entry price if not set."""
        if self.current_price == 0.0:
            self.current_price = self.entry_price

    def update_price(self, new_price: float) -> None:
        """
        Update current price and recalculate P&L.

        Args:
            new_price: New market price
        """
        self.current_price = new_price
        self.unrealized_pnl = self.calculate_pnl()

        # Update MAE and MFE
        if self.unrealized_pnl < self.max_adverse_excursion:
            self.max_adverse_excursion = self.unrealized_pnl
        if self.unrealized_pnl > self.max_favorable_excursion:
            self.max_favorable_excursion = self.unrealized_pnl

    def calculate_pnl(self) -> float:
        """
        Calculate current P&L.

        Returns:
            float: Profit/Loss amount
        """
        if self.direction == Direction.LONG:
            pnl = (self.current_price - self.entry_price) * self.size
        else:  # SHORT
            pnl = (self.entry_price - self.current_price) * self.size

        return pnl

    def calculate_pnl_percent(self) -> float:
        """
        Calculate P&L as percentage.

        Returns:
            float: P&L percentage
        """
        if self.entry_price == 0:
            return 0.0

        pnl = self.calculate_pnl()
        position_value = self.entry_price * self.size / self.leverage

        return (pnl / position_value) * 100 if position_value > 0 else 0.0

    def get_position_value(self) -> float:
        """
        Calculate current position value.

        Returns:
            float: Position value
        """
        return self.current_price * self.size

    def get_margin_used(self) -> float:
        """
        Calculate margin used for this position.

        Returns:
            float: Margin amount
        """
        return (self.entry_price * self.size) / self.leverage

    def should_close_stop_loss(self) -> bool:
        """
        Check if position should be closed due to stop loss.

        Returns:
            bool: True if stop loss is hit
        """
        if self.stop_loss is None or self.status != PositionStatus.OPEN:
            return False

        if self.direction == Direction.LONG:
            return self.current_price <= self.stop_loss
        else:  # SHORT
            return self.current_price >= self.stop_loss

    def should_close_take_profit(self) -> bool:
        """
        Check if position should be closed due to take profit.

        Returns:
            bool: True if take profit is hit
        """
        if self.take_profit is None or self.status != PositionStatus.OPEN:
            return False

        if self.direction == Direction.LONG:
            return self.current_price >= self.take_profit
        else:  # SHORT
            return self.current_price <= self.take_profit

    def close(self, close_price: float, close_time: datetime, reason: CloseReason) -> None:
        """
        Close the position.

        Args:
            close_price: Closing price
            close_time: Closing timestamp
            reason: Reason for closing
        """
        self.status = PositionStatus.CLOSED
        self.close_price = close_price
        self.close_time = close_time
        self.close_reason = reason
        self.current_price = close_price
        self.realized_pnl = self.calculate_pnl()
        self.unrealized_pnl = 0.0

    def to_dict(self) -> Dict:
        """Convert position to dictionary."""
        return {
            'position_id': self.position_id,
            'instrument': self.instrument,
            'direction': self.direction.value,
            'entry_price': round(self.entry_price, 5),
            'entry_time': self.entry_time.isoformat(),
            'size': round(self.size, 4),
            'current_price': round(self.current_price, 5),
            'stop_loss': round(self.stop_loss, 5) if self.stop_loss else None,
            'take_profit': round(self.take_profit, 5) if self.take_profit else None,
            'leverage': self.leverage,
            'commission_paid': round(self.commission_paid, 2),
            'status': self.status.value,
            'close_price': round(self.close_price, 5) if self.close_price else None,
            'close_time': self.close_time.isoformat() if self.close_time else None,
            'close_reason': self.close_reason.value if self.close_reason else None,
            'max_adverse_excursion': round(self.max_adverse_excursion, 2),
            'max_favorable_excursion': round(self.max_favorable_excursion, 2),
            'unrealized_pnl': round(self.unrealized_pnl, 2),
            'realized_pnl': round(self.realized_pnl, 2),
            'pnl_percent': round(self.calculate_pnl_percent(), 2),
            'position_value': round(self.get_position_value(), 2),
            'margin_used': round(self.get_margin_used(), 2),
            'metadata': self.metadata
        }


@dataclass
class Order:
    """
    Represents a trading order.

    Attributes:
        order_id: Unique order identifier
        instrument: Trading instrument symbol
        direction: LONG or SHORT
        order_type: Order type
        size: Order size in units
        price: Limit/stop price (for limit/stop orders)
        stop_price: Stop price (for stop-limit orders)
        time_in_force: Time in force
        status: Order status
        filled_size: Filled size (for partial fills)
        filled_price: Average filled price
        commission: Commission charged
        create_time: Order creation time
        fill_time: Order fill time
        expiry_time: Order expiry time
        stop_loss: Stop loss for resulting position
        take_profit: Take profit for resulting position
        leverage: Leverage to use
        reason: Rejection/cancellation reason
    """
    order_id: str
    instrument: str
    direction: Direction
    order_type: OrderType
    size: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.GTC
    status: OrderStatus = OrderStatus.PENDING
    filled_size: float = 0.0
    filled_price: float = 0.0
    commission: float = 0.0
    create_time: datetime = field(default_factory=datetime.now)
    fill_time: Optional[datetime] = None
    expiry_time: Optional[datetime] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    leverage: float = 1.0
    reason: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def is_active(self) -> bool:
        """Check if order is active (pending or partially filled)."""
        return self.status in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]

    def is_expired(self, current_time: datetime) -> bool:
        """
        Check if order has expired.

        Args:
            current_time: Current timestamp

        Returns:
            bool: True if expired
        """
        if self.expiry_time is None:
            return False
        return current_time >= self.expiry_time

    def remaining_size(self) -> float:
        """Calculate remaining unfilled size."""
        return self.size - self.filled_size

    def fill(self, size: float, price: float, commission: float, fill_time: datetime) -> None:
        """
        Fill order (fully or partially).

        Args:
            size: Filled size
            price: Fill price
            commission: Commission charged
            fill_time: Fill timestamp
        """
        self.filled_size += size
        self.commission += commission
        self.fill_time = fill_time

        # Update average filled price
        if self.filled_price == 0.0:
            self.filled_price = price
        else:
            # Weighted average
            total_value = (self.filled_price * (self.filled_size - size)) + (price * size)
            self.filled_price = total_value / self.filled_size

        # Update status
        if self.filled_size >= self.size:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIALLY_FILLED

    def cancel(self, reason: str = "User cancelled") -> None:
        """
        Cancel order.

        Args:
            reason: Cancellation reason
        """
        self.status = OrderStatus.CANCELLED
        self.reason = reason

    def reject(self, reason: str) -> None:
        """
        Reject order.

        Args:
            reason: Rejection reason
        """
        self.status = OrderStatus.REJECTED
        self.reason = reason

    def to_dict(self) -> Dict:
        """Convert order to dictionary."""
        return {
            'order_id': self.order_id,
            'instrument': self.instrument,
            'direction': self.direction.value,
            'order_type': self.order_type.value,
            'size': round(self.size, 4),
            'price': round(self.price, 5) if self.price else None,
            'stop_price': round(self.stop_price, 5) if self.stop_price else None,
            'time_in_force': self.time_in_force.value,
            'status': self.status.value,
            'filled_size': round(self.filled_size, 4),
            'filled_price': round(self.filled_price, 5),
            'commission': round(self.commission, 2),
            'create_time': self.create_time.isoformat(),
            'fill_time': self.fill_time.isoformat() if self.fill_time else None,
            'expiry_time': self.expiry_time.isoformat() if self.expiry_time else None,
            'stop_loss': round(self.stop_loss, 5) if self.stop_loss else None,
            'take_profit': round(self.take_profit, 5) if self.take_profit else None,
            'leverage': self.leverage,
            'reason': self.reason,
            'metadata': self.metadata
        }


class PaperTradingAccount:
    """
    Paper trading account with realistic capital tracking.

    Manages account balance, positions, margin, and risk limits.
    """

    def __init__(
        self,
        starting_capital: float = 10000.0,
        max_position_size: float = 0.2,  # 20% of capital per position
        max_positions: int = 10,
        max_daily_loss: float = 0.05,  # 5% daily loss limit
        max_drawdown: float = 0.20,  # 20% max drawdown
        commission_per_trade: float = 0.0,  # Commission per trade
        commission_percent: float = 0.0,  # Commission as % of trade value
        default_leverage: float = 1.0
    ):
        """
        Initialize paper trading account.

        Args:
            starting_capital: Initial capital
            max_position_size: Maximum position size as fraction of capital
            max_positions: Maximum number of concurrent positions
            max_daily_loss: Maximum daily loss as fraction of capital
            max_drawdown: Maximum drawdown as fraction of peak capital
            commission_per_trade: Fixed commission per trade
            commission_percent: Commission as percentage of trade value
            default_leverage: Default leverage for positions

        Raises:
            ValueError: If parameters are invalid
        """
        if starting_capital <= 0:
            raise ValueError(f"starting_capital must be positive, got {starting_capital}")

        if not 0 < max_position_size <= 1:
            raise ValueError(f"max_position_size must be between 0 and 1, got {max_position_size}")

        self.starting_capital = starting_capital
        self.cash_balance = starting_capital
        self.equity = starting_capital
        self.peak_equity = starting_capital

        # Risk limits
        self.max_position_size = max_position_size
        self.max_positions = max_positions
        self.max_daily_loss = max_daily_loss
        self.max_drawdown = max_drawdown

        # Commission
        self.commission_per_trade = commission_per_trade
        self.commission_percent = commission_percent

        # Leverage
        self.default_leverage = default_leverage

        # Positions and orders
        self.open_positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []
        self.pending_orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []

        # Daily tracking
        self.daily_start_equity = starting_capital
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()

        logger.info(f"Initialized paper trading account with ${starting_capital:,.2f}")

    def get_total_margin_used(self) -> float:
        """
        Calculate total margin used by open positions.

        Returns:
            float: Total margin used
        """
        return sum(pos.get_margin_used() for pos in self.open_positions.values())

    def get_available_margin(self) -> float:
        """
        Calculate available margin for new positions.

        Returns:
            float: Available margin
        """
        return self.cash_balance - self.get_total_margin_used()

    def get_total_unrealized_pnl(self) -> float:
        """
        Calculate total unrealized P&L from open positions.

        Returns:
            float: Total unrealized P&L
        """
        return sum(pos.unrealized_pnl for pos in self.open_positions.values())

    def get_total_realized_pnl(self) -> float:
        """
        Calculate total realized P&L from closed positions.

        Returns:
            float: Total realized P&L
        """
        return sum(pos.realized_pnl - pos.commission_paid for pos in self.closed_positions)

    def update_equity(self) -> None:
        """Update account equity based on positions."""
        unrealized_pnl = self.get_total_unrealized_pnl()
        self.equity = self.cash_balance + unrealized_pnl

        # Update peak equity
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity

        # Reset daily tracking if new day
        current_date = datetime.now().date()
        if current_date > self.last_reset_date:
            self.daily_start_equity = self.equity
            self.daily_pnl = 0.0
            self.last_reset_date = current_date

    def get_current_drawdown(self) -> float:
        """
        Calculate current drawdown from peak.

        Returns:
            float: Drawdown percentage
        """
        if self.peak_equity == 0:
            return 0.0
        return ((self.peak_equity - self.equity) / self.peak_equity) * 100

    def get_daily_pnl_percent(self) -> float:
        """
        Calculate daily P&L percentage.

        Returns:
            float: Daily P&L percentage
        """
        if self.daily_start_equity == 0:
            return 0.0
        self.daily_pnl = self.equity - self.daily_start_equity
        return (self.daily_pnl / self.daily_start_equity) * 100

    def can_open_position(self, margin_required: float) -> Tuple[bool, str]:
        """
        Check if new position can be opened.

        Args:
            margin_required: Margin required for new position

        Returns:
            Tuple of (can_open, reason)
        """
        # Check position limit
        if len(self.open_positions) >= self.max_positions:
            return False, f"Maximum positions ({self.max_positions}) reached"

        # Check margin availability
        if margin_required > self.get_available_margin():
            return False, f"Insufficient margin. Required: ${margin_required:,.2f}, Available: ${self.get_available_margin():,.2f}"

        # Check position size limit
        max_allowed = self.equity * self.max_position_size
        if margin_required > max_allowed:
            return False, f"Position size exceeds limit. Maximum: ${max_allowed:,.2f}"

        # Check daily loss limit
        daily_loss_pct = abs(min(0, self.get_daily_pnl_percent()))
        if daily_loss_pct >= self.max_daily_loss * 100:
            return False, f"Daily loss limit reached ({daily_loss_pct:.2f}%)"

        # Check drawdown limit
        drawdown_pct = self.get_current_drawdown()
        if drawdown_pct >= self.max_drawdown * 100:
            return False, f"Maximum drawdown reached ({drawdown_pct:.2f}%)"

        return True, "OK"

    def calculate_commission(self, trade_value: float) -> float:
        """
        Calculate commission for a trade.

        Args:
            trade_value: Trade value

        Returns:
            float: Commission amount
        """
        fixed_commission = self.commission_per_trade
        percent_commission = trade_value * (self.commission_percent / 100)
        return fixed_commission + percent_commission

    def get_account_summary(self) -> Dict:
        """
        Get account summary.

        Returns:
            Dict with account metrics
        """
        self.update_equity()

        return {
            'starting_capital': self.starting_capital,
            'cash_balance': round(self.cash_balance, 2),
            'equity': round(self.equity, 2),
            'peak_equity': round(self.peak_equity, 2),
            'unrealized_pnl': round(self.get_total_unrealized_pnl(), 2),
            'realized_pnl': round(self.get_total_realized_pnl(), 2),
            'total_pnl': round(self.equity - self.starting_capital, 2),
            'total_pnl_percent': round(((self.equity - self.starting_capital) / self.starting_capital) * 100, 2),
            'daily_pnl': round(self.daily_pnl, 2),
            'daily_pnl_percent': round(self.get_daily_pnl_percent(), 2),
            'current_drawdown': round(self.get_current_drawdown(), 2),
            'margin_used': round(self.get_total_margin_used(), 2),
            'available_margin': round(self.get_available_margin(), 2),
            'open_positions': len(self.open_positions),
            'total_trades': len(self.closed_positions),
            'pending_orders': len(self.pending_orders)
        }


class PaperTrader:
    """
    Main paper trading engine.

    Handles order execution, position management, and market simulation.
    """

    def __init__(
        self,
        account: PaperTradingAccount,
        default_slippage_pips: float = 1.0,
        spread_pips: Dict[str, float] = None,
        enable_partial_fills: bool = False,
        market_impact_factor: float = 0.0
    ):
        """
        Initialize paper trader.

        Args:
            account: Paper trading account
            default_slippage_pips: Default slippage in pips
            spread_pips: Spread in pips per instrument
            enable_partial_fills: Enable partial order fills
            market_impact_factor: Market impact factor (0-1)
        """
        self.account = account
        self.default_slippage_pips = default_slippage_pips
        self.spread_pips = spread_pips or {}
        self.enable_partial_fills = enable_partial_fills
        self.market_impact_factor = market_impact_factor

        # Market data
        self.current_prices: Dict[str, Dict[str, float]] = {}
        self.last_update_time: Optional[datetime] = None

        logger.info("Initialized PaperTrader")

    def update_prices(self, market_data: Dict[str, Dict[str, float]], timestamp: datetime = None) -> None:
        """
        Update market prices.

        Args:
            market_data: Dict of {instrument: {'bid': x, 'ask': y, 'mid': z}}
            timestamp: Price timestamp
        """
        self.current_prices = market_data
        self.last_update_time = timestamp or datetime.now()

        # Update all open positions
        for position in self.account.open_positions.values():
            if position.instrument in market_data:
                mid_price = market_data[position.instrument].get('mid',
                           (market_data[position.instrument].get('bid', 0) +
                            market_data[position.instrument].get('ask', 0)) / 2)
                position.update_price(mid_price)

        # Update account equity
        self.account.update_equity()

        # Check stop loss and take profit
        self.check_stop_loss()
        self.check_take_profit()

        # Process pending orders
        self._process_pending_orders()

    def get_execution_price(
        self,
        instrument: str,
        direction: Direction,
        order_type: OrderType,
        size: float,
        limit_price: Optional[float] = None
    ) -> Tuple[float, float]:
        """
        Calculate execution price with slippage and spread.

        Args:
            instrument: Trading instrument
            direction: Order direction
            order_type: Order type
            size: Order size
            limit_price: Limit price (if applicable)

        Returns:
            Tuple of (execution_price, slippage_amount)
        """
        if instrument not in self.current_prices:
            raise ValueError(f"No price data for {instrument}")

        price_data = self.current_prices[instrument]

        # Get base price (bid for shorts, ask for longs)
        if direction == Direction.LONG:
            base_price = price_data.get('ask', price_data.get('mid', 0))
        else:
            base_price = price_data.get('bid', price_data.get('mid', 0))

        # Calculate slippage
        slippage_pips = self.default_slippage_pips

        # Add market impact based on position size
        if self.market_impact_factor > 0:
            impact_pips = size * self.market_impact_factor
            slippage_pips += impact_pips

        # Convert pips to price (assuming 4 decimal places for forex)
        pip_value = 0.0001
        slippage_amount = slippage_pips * pip_value

        # Apply slippage (always against the trader)
        if direction == Direction.LONG:
            execution_price = base_price + slippage_amount
        else:
            execution_price = base_price - slippage_amount

        # For limit orders, ensure execution price doesn't exceed limit
        if order_type == OrderType.LIMIT and limit_price is not None:
            if direction == Direction.LONG:
                execution_price = min(execution_price, limit_price)
            else:
                execution_price = max(execution_price, limit_price)

        return execution_price, slippage_amount

    def calculate_position_size(
        self,
        instrument: str,
        direction: Direction,
        risk_percent: float,
        entry_price: float,
        stop_loss: float,
        leverage: float = None
    ) -> float:
        """
        Calculate position size based on risk.

        Args:
            instrument: Trading instrument
            direction: Position direction
            risk_percent: Risk percentage of account
            entry_price: Entry price
            stop_loss: Stop loss price
            leverage: Leverage to use

        Returns:
            float: Position size in units

        Raises:
            ValueError: If parameters are invalid
        """
        if not 0 < risk_percent <= 100:
            raise ValueError(f"risk_percent must be between 0 and 100, got {risk_percent}")

        if entry_price <= 0:
            raise ValueError(f"entry_price must be positive, got {entry_price}")

        leverage = leverage or self.account.default_leverage

        # Calculate risk amount
        risk_amount = self.account.equity * (risk_percent / 100)

        # Calculate risk per unit
        risk_per_unit = abs(entry_price - stop_loss)

        if risk_per_unit == 0:
            raise ValueError("Stop loss cannot equal entry price")

        # Calculate position size
        position_size = risk_amount / risk_per_unit

        # Apply leverage constraint
        max_position_value = self.account.equity * self.account.max_position_size * leverage
        max_size = max_position_value / entry_price

        position_size = min(position_size, max_size)

        logger.debug(f"Calculated position size: {position_size:.4f} units for {instrument}")

        return position_size

    def place_order(
        self,
        instrument: str,
        direction: Direction,
        size: float,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: TimeInForce = TimeInForce.GTC,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        leverage: Optional[float] = None,
        metadata: Dict = None
    ) -> Union[Order, str]:
        """
        Place a new order.

        Args:
            instrument: Trading instrument
            direction: Order direction
            size: Order size in units
            order_type: Order type
            price: Limit/stop price
            stop_price: Stop price for stop-limit orders
            time_in_force: Time in force
            stop_loss: Stop loss for resulting position
            take_profit: Take profit for resulting position
            leverage: Leverage to use
            metadata: Additional metadata

        Returns:
            Order object or error message string
        """
        try:
            # Validate inputs
            if size <= 0:
                return f"Invalid size: {size}"

            if instrument not in self.current_prices:
                return f"No price data for {instrument}"

            leverage = leverage or self.account.default_leverage

            # Create order
            order = Order(
                order_id=str(uuid.uuid4()),
                instrument=instrument,
                direction=direction,
                order_type=order_type,
                size=size,
                price=price,
                stop_price=stop_price,
                time_in_force=time_in_force,
                stop_loss=stop_loss,
                take_profit=take_profit,
                leverage=leverage,
                metadata=metadata or {}
            )

            # Calculate required margin
            est_price = price if price else self.current_prices[instrument].get('mid', 0)
            margin_required = (est_price * size) / leverage

            # Check if position can be opened
            can_open, reason = self.account.can_open_position(margin_required)
            if not can_open:
                order.reject(reason)
                self.account.order_history.append(order)
                logger.warning(f"Order rejected: {reason}")
                return reason

            # Set expiry time for DAY orders
            if time_in_force == TimeInForce.DAY:
                order.expiry_time = datetime.now() + timedelta(hours=24)

            # Process market orders immediately
            if order_type == OrderType.MARKET:
                self._execute_order(order)
            else:
                # Add to pending orders
                self.account.pending_orders[order.order_id] = order
                logger.info(f"Placed {order_type.value} order {order.order_id} for {instrument}")

            return order

        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            return f"Error placing order: {str(e)}"

    def _execute_order(self, order: Order) -> bool:
        """
        Execute an order.

        Args:
            order: Order to execute

        Returns:
            bool: True if successful
        """
        try:
            # Get execution price
            execution_price, slippage = self.get_execution_price(
                order.instrument,
                order.direction,
                order.order_type,
                order.size,
                order.price
            )

            # Calculate commission
            trade_value = execution_price * order.size
            commission = self.account.calculate_commission(trade_value)

            # Check margin again with actual execution price
            margin_required = (execution_price * order.size) / order.leverage
            can_open, reason = self.account.can_open_position(margin_required)

            if not can_open:
                order.reject(reason)
                self.account.order_history.append(order)
                return False

            # Fill order
            fill_time = self.last_update_time or datetime.now()
            order.fill(order.size, execution_price, commission, fill_time)

            # Create position
            position = Position(
                position_id=str(uuid.uuid4()),
                instrument=order.instrument,
                direction=order.direction,
                entry_price=execution_price,
                entry_time=fill_time,
                size=order.size,
                current_price=execution_price,
                stop_loss=order.stop_loss,
                take_profit=order.take_profit,
                leverage=order.leverage,
                commission_paid=commission,
                metadata=order.metadata
            )

            # Update account
            self.account.cash_balance -= margin_required
            self.account.cash_balance -= commission
            self.account.open_positions[position.position_id] = position
            self.account.order_history.append(order)

            # Remove from pending orders if there
            if order.order_id in self.account.pending_orders:
                del self.account.pending_orders[order.order_id]

            logger.info(f"Executed order {order.order_id}: {order.direction.value} {order.size} {order.instrument} @ {execution_price:.5f}")

            return True

        except Exception as e:
            logger.error(f"Error executing order: {str(e)}")
            order.reject(str(e))
            self.account.order_history.append(order)
            return False

    def _process_pending_orders(self) -> None:
        """Process pending limit and stop orders."""
        current_time = self.last_update_time or datetime.now()
        orders_to_remove = []

        # Iterate over a copy to avoid RuntimeError when dict changes during iteration
        for order_id, order in list(self.account.pending_orders.items()):
            # Check expiry
            if order.is_expired(current_time):
                order.status = OrderStatus.EXPIRED
                order.reason = "Order expired"
                self.account.order_history.append(order)
                orders_to_remove.append(order_id)
                continue

            # Check if order can be filled
            if order.instrument not in self.current_prices:
                continue

            price_data = self.current_prices[order.instrument]
            current_price = price_data.get('mid', 0)

            should_fill = False

            if order.order_type == OrderType.LIMIT:
                # Buy limit: fill if ask <= limit price
                # Sell limit: fill if bid >= limit price
                if order.direction == Direction.LONG:
                    ask_price = price_data.get('ask', current_price)
                    should_fill = ask_price <= order.price
                else:
                    bid_price = price_data.get('bid', current_price)
                    should_fill = bid_price >= order.price

            elif order.order_type == OrderType.STOP:
                # Buy stop: fill if ask >= stop price
                # Sell stop: fill if bid <= stop price
                if order.direction == Direction.LONG:
                    ask_price = price_data.get('ask', current_price)
                    should_fill = ask_price >= order.price
                else:
                    bid_price = price_data.get('bid', current_price)
                    should_fill = bid_price <= order.price

            elif order.order_type == OrderType.STOP_LIMIT:
                # First check if stop is triggered
                if order.direction == Direction.LONG:
                    ask_price = price_data.get('ask', current_price)
                    stop_triggered = ask_price >= order.stop_price
                    if stop_triggered:
                        should_fill = ask_price <= order.price
                else:
                    bid_price = price_data.get('bid', current_price)
                    stop_triggered = bid_price <= order.stop_price
                    if stop_triggered:
                        should_fill = bid_price >= order.price

            # Handle IOC and FOK
            if should_fill:
                if order.time_in_force == TimeInForce.IOC or order.time_in_force == TimeInForce.FOK:
                    # Immediate execution required
                    success = self._execute_order(order)
                    if success or order.time_in_force == TimeInForce.IOC:
                        orders_to_remove.append(order_id)
                    elif order.time_in_force == TimeInForce.FOK:
                        # FOK failed - cancel
                        order.cancel("Fill or Kill failed")
                        self.account.order_history.append(order)
                        orders_to_remove.append(order_id)
                else:
                    # GTC or DAY - execute normally
                    success = self._execute_order(order)
                    if success:
                        orders_to_remove.append(order_id)

        # Remove filled/expired/cancelled orders
        for order_id in orders_to_remove:
            if order_id in self.account.pending_orders:
                del self.account.pending_orders[order_id]

    def close_position(
        self,
        position_id: str,
        reason: CloseReason = CloseReason.MANUAL,
        size: Optional[float] = None
    ) -> Union[bool, str]:
        """
        Close a position.

        Args:
            position_id: Position ID to close
            reason: Reason for closing
            size: Size to close (None = close all)

        Returns:
            True if successful, error message otherwise
        """
        try:
            if position_id not in self.account.open_positions:
                return f"Position {position_id} not found"

            position = self.account.open_positions[position_id]

            if position.instrument not in self.current_prices:
                return f"No price data for {position.instrument}"

            # Get closing price
            price_data = self.current_prices[position.instrument]
            if position.direction == Direction.LONG:
                close_price = price_data.get('bid', price_data.get('mid', 0))
            else:
                close_price = price_data.get('ask', price_data.get('mid', 0))

            # Apply slippage
            slippage_pips = self.default_slippage_pips
            pip_value = 0.0001
            slippage_amount = slippage_pips * pip_value

            if position.direction == Direction.LONG:
                close_price -= slippage_amount
            else:
                close_price += slippage_amount

            close_time = self.last_update_time or datetime.now()

            # Calculate commission
            close_value = close_price * position.size
            commission = self.account.calculate_commission(close_value)

            # Close position
            position.close(close_price, close_time, reason)
            position.commission_paid += commission

            # Update account
            margin_released = position.get_margin_used()
            self.account.cash_balance += margin_released
            self.account.cash_balance += position.realized_pnl
            self.account.cash_balance -= commission

            # Move to closed positions
            self.account.closed_positions.append(position)
            del self.account.open_positions[position_id]

            # Update equity
            self.account.update_equity()

            logger.info(f"Closed position {position_id}: {position.direction.value} {position.instrument}, P&L: ${position.realized_pnl:.2f}")

            return True

        except Exception as e:
            logger.error(f"Error closing position: {str(e)}")
            return f"Error closing position: {str(e)}"

    def modify_position(
        self,
        position_id: str,
        new_stop_loss: Optional[float] = None,
        new_take_profit: Optional[float] = None
    ) -> Union[bool, str]:
        """
        Modify position stop loss and take profit.

        Args:
            position_id: Position ID
            new_stop_loss: New stop loss price
            new_take_profit: New take profit price

        Returns:
            True if successful, error message otherwise
        """
        try:
            if position_id not in self.account.open_positions:
                return f"Position {position_id} not found"

            position = self.account.open_positions[position_id]

            if new_stop_loss is not None:
                position.stop_loss = new_stop_loss
                logger.info(f"Updated stop loss for {position_id} to {new_stop_loss:.5f}")

            if new_take_profit is not None:
                position.take_profit = new_take_profit
                logger.info(f"Updated take profit for {position_id} to {new_take_profit:.5f}")

            return True

        except Exception as e:
            logger.error(f"Error modifying position: {str(e)}")
            return f"Error modifying position: {str(e)}"

    def cancel_order(self, order_id: str, reason: str = "User cancelled") -> Union[bool, str]:
        """
        Cancel a pending order.

        Args:
            order_id: Order ID to cancel
            reason: Cancellation reason

        Returns:
            True if successful, error message otherwise
        """
        try:
            if order_id not in self.account.pending_orders:
                return f"Order {order_id} not found or already filled"

            order = self.account.pending_orders[order_id]
            order.cancel(reason)

            self.account.order_history.append(order)
            del self.account.pending_orders[order_id]

            logger.info(f"Cancelled order {order_id}: {reason}")

            return True

        except Exception as e:
            logger.error(f"Error cancelling order: {str(e)}")
            return f"Error cancelling order: {str(e)}"

    def check_stop_loss(self) -> List[str]:
        """
        Check and execute stop losses.

        Returns:
            List of closed position IDs
        """
        closed_positions = []

        for position_id, position in list(self.account.open_positions.items()):
            if position.should_close_stop_loss():
                result = self.close_position(position_id, CloseReason.STOP_LOSS)
                if result is True:
                    closed_positions.append(position_id)
                    logger.info(f"Stop loss triggered for {position_id}")

        return closed_positions

    def check_take_profit(self) -> List[str]:
        """
        Check and execute take profits.

        Returns:
            List of closed position IDs
        """
        closed_positions = []

        for position_id, position in list(self.account.open_positions.items()):
            if position.should_close_take_profit():
                result = self.close_position(position_id, CloseReason.TAKE_PROFIT)
                if result is True:
                    closed_positions.append(position_id)
                    logger.info(f"Take profit triggered for {position_id}")

        return closed_positions

    def close_all_positions(self, reason: CloseReason = CloseReason.MANUAL) -> int:
        """
        Close all open positions.

        Args:
            reason: Reason for closing

        Returns:
            Number of positions closed
        """
        position_ids = list(self.account.open_positions.keys())
        closed_count = 0

        for position_id in position_ids:
            result = self.close_position(position_id, reason)
            if result is True:
                closed_count += 1

        logger.info(f"Closed {closed_count} positions")
        return closed_count

    def get_performance_metrics(self) -> Dict:
        """
        Calculate comprehensive performance metrics.

        Returns:
            Dict with performance metrics
        """
        if not self.account.closed_positions:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'average_win': 0.0,
                'average_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'average_trade': 0.0,
                'total_pnl': 0.0,
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'max_drawdown': 0.0,
                'max_consecutive_wins': 0,
                'max_consecutive_losses': 0
            }

        # Calculate basic statistics
        trades = self.account.closed_positions
        pnls = [t.realized_pnl - t.commission_paid for t in trades]

        winning_trades = [p for p in pnls if p > 0]
        losing_trades = [p for p in pnls if p < 0]

        win_rate = (len(winning_trades) / len(pnls)) * 100 if pnls else 0

        total_wins = sum(winning_trades) if winning_trades else 0
        total_losses = abs(sum(losing_trades)) if losing_trades else 0

        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

        average_win = np.mean(winning_trades) if winning_trades else 0
        average_loss = np.mean(losing_trades) if losing_trades else 0

        largest_win = max(winning_trades) if winning_trades else 0
        largest_loss = min(losing_trades) if losing_trades else 0

        average_trade = np.mean(pnls) if pnls else 0

        # Calculate consecutive wins/losses
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_wins = 0
        current_losses = 0

        for pnl in pnls:
            if pnl > 0:
                current_wins += 1
                current_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, current_losses)

        # Calculate Sharpe ratio (simplified)
        if len(pnls) > 1:
            returns = np.array(pnls) / self.account.starting_capital
            sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if np.std(returns) > 0 else 0
        else:
            sharpe_ratio = 0

        # Calculate Sortino ratio
        if len(pnls) > 1:
            returns = np.array(pnls) / self.account.starting_capital
            downside_returns = returns[returns < 0]
            if len(downside_returns) > 0:
                downside_std = np.std(downside_returns)
                sortino_ratio = (np.mean(returns) / downside_std) * np.sqrt(252) if downside_std > 0 else 0
            else:
                sortino_ratio = float('inf')
        else:
            sortino_ratio = 0

        return {
            'total_trades': len(pnls),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(win_rate, 2),
            'profit_factor': round(profit_factor, 2) if profit_factor != float('inf') else 'Inf',
            'average_win': round(average_win, 2),
            'average_loss': round(average_loss, 2),
            'largest_win': round(largest_win, 2),
            'largest_loss': round(largest_loss, 2),
            'average_trade': round(average_trade, 2),
            'total_pnl': round(sum(pnls), 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'sortino_ratio': round(sortino_ratio, 2) if sortino_ratio != float('inf') else 'Inf',
            'max_drawdown': round(self.account.get_current_drawdown(), 2),
            'max_consecutive_wins': max_consecutive_wins,
            'max_consecutive_losses': max_consecutive_losses
        }


class TradeJournal:
    """
    Trade journal for recording and analyzing trades.
    """

    def __init__(self, filepath: str = "trade_journal.json"):
        """
        Initialize trade journal.

        Args:
            filepath: Path to journal file
        """
        self.filepath = Path(filepath)
        self.trades: List[Dict] = []

        # Load existing journal if exists
        if self.filepath.exists():
            self.load()

    def record_trade(self, position: Position) -> None:
        """
        Record a closed trade.

        Args:
            position: Closed position
        """
        if position.status != PositionStatus.CLOSED:
            logger.warning(f"Attempting to record open position {position.position_id}")
            return

        trade_record = position.to_dict()
        trade_record['journal_timestamp'] = datetime.now().isoformat()

        self.trades.append(trade_record)
        logger.debug(f"Recorded trade {position.position_id} in journal")

    def get_statistics(self) -> Dict:
        """
        Calculate journal statistics.

        Returns:
            Dict with statistics
        """
        if not self.trades:
            return {'total_trades': 0, 'message': 'No trades recorded'}

        df = pd.DataFrame(self.trades)

        stats = {
            'total_trades': len(df),
            'total_pnl': df['realized_pnl'].sum() - df['commission_paid'].sum(),
            'average_pnl': df['realized_pnl'].mean() - df['commission_paid'].mean(),
            'win_rate': (df['realized_pnl'] > 0).sum() / len(df) * 100,
            'average_win': df[df['realized_pnl'] > 0]['realized_pnl'].mean() if (df['realized_pnl'] > 0).any() else 0,
            'average_loss': df[df['realized_pnl'] < 0]['realized_pnl'].mean() if (df['realized_pnl'] < 0).any() else 0,
            'largest_win': df['realized_pnl'].max(),
            'largest_loss': df['realized_pnl'].min(),
            'total_commission': df['commission_paid'].sum(),
            'average_mae': df['max_adverse_excursion'].mean(),
            'average_mfe': df['max_favorable_excursion'].mean()
        }

        # By instrument
        stats['by_instrument'] = df.groupby('instrument').agg({
            'realized_pnl': ['count', 'sum', 'mean'],
            'commission_paid': 'sum'
        }).to_dict()

        # By direction
        stats['by_direction'] = df.groupby('direction').agg({
            'realized_pnl': ['count', 'sum', 'mean'],
            'commission_paid': 'sum'
        }).to_dict()

        # By close reason
        stats['by_close_reason'] = df.groupby('close_reason').size().to_dict()

        return stats

    def export_to_csv(self, filepath: str = "trades.csv") -> None:
        """
        Export trades to CSV.

        Args:
            filepath: CSV file path
        """
        if not self.trades:
            logger.warning("No trades to export")
            return

        df = pd.DataFrame(self.trades)
        df.to_csv(filepath, index=False)
        logger.info(f"Exported {len(df)} trades to {filepath}")

    def export_to_json(self, filepath: str = None) -> None:
        """
        Export trades to JSON.

        Args:
            filepath: JSON file path (uses self.filepath if None)
        """
        filepath = Path(filepath) if filepath else self.filepath

        with open(filepath, 'w') as f:
            json.dump(self.trades, f, indent=2)

        logger.info(f"Exported {len(self.trades)} trades to {filepath}")

    def save(self) -> None:
        """Save journal to file."""
        self.export_to_json()

    def load(self) -> None:
        """Load journal from file."""
        try:
            with open(self.filepath, 'r') as f:
                self.trades = json.load(f)
            logger.info(f"Loaded {len(self.trades)} trades from {self.filepath}")
        except Exception as e:
            logger.error(f"Error loading journal: {str(e)}")
            self.trades = []

    def get_equity_curve(self) -> pd.DataFrame:
        """
        Generate equity curve.

        Returns:
            DataFrame with cumulative P&L
        """
        if not self.trades:
            return pd.DataFrame()

        df = pd.DataFrame(self.trades)
        df['close_time'] = pd.to_datetime(df['close_time'])
        df = df.sort_values('close_time')
        df['net_pnl'] = df['realized_pnl'] - df['commission_paid']
        df['cumulative_pnl'] = df['net_pnl'].cumsum()

        return df[['close_time', 'net_pnl', 'cumulative_pnl']]

    def filter_trades(
        self,
        instrument: Optional[str] = None,
        direction: Optional[Direction] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_pnl: Optional[float] = None,
        max_pnl: Optional[float] = None
    ) -> List[Dict]:
        """
        Filter trades by criteria.

        Args:
            instrument: Filter by instrument
            direction: Filter by direction
            start_date: Start date
            end_date: End date
            min_pnl: Minimum P&L
            max_pnl: Maximum P&L

        Returns:
            List of filtered trades
        """
        filtered = self.trades

        if instrument:
            filtered = [t for t in filtered if t['instrument'] == instrument]

        if direction:
            filtered = [t for t in filtered if t['direction'] == direction.value]

        if start_date:
            filtered = [t for t in filtered if datetime.fromisoformat(t['close_time']) >= start_date]

        if end_date:
            filtered = [t for t in filtered if datetime.fromisoformat(t['close_time']) <= end_date]

        if min_pnl is not None:
            filtered = [t for t in filtered if t['realized_pnl'] >= min_pnl]

        if max_pnl is not None:
            filtered = [t for t in filtered if t['realized_pnl'] <= max_pnl]

        return filtered
