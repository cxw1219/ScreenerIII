"""
Trading Module

Provides paper trading simulation and order management functionality.

Author: ScreenerIII
License: MIT
"""

from .paper_trading import (
    # Enums
    Direction,
    OrderType,
    OrderStatus,
    TimeInForce,
    PositionStatus,
    CloseReason,

    # Data classes
    Position,
    Order,

    # Main classes
    PaperTradingAccount,
    PaperTrader,
    TradeJournal
)

__all__ = [
    # Enums
    'Direction',
    'OrderType',
    'OrderStatus',
    'TimeInForce',
    'PositionStatus',
    'CloseReason',

    # Data classes
    'Position',
    'Order',

    # Main classes
    'PaperTradingAccount',
    'PaperTrader',
    'TradeJournal'
]

__version__ = '1.0.0'
