"""
Web Dashboard Backend API Module

This module provides a Flask-based REST API for the ScreenerIII commodity trading
scanner platform. It includes endpoints for market data, trading signals, portfolio
management, performance analytics, risk metrics, backtesting, and configuration.

Features:
- Application factory pattern with CORS support
- Standardized JSON response formatting with pagination
- Server-Sent Events (SSE) for real-time price and signal streaming
- Request logging and error handling middleware
- API versioning under /api/v1/
- Minimal HTML dashboard frontend

Author: ScreenerIII
License: MIT
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, Union

# Flask is an optional dependency - provide a clear error message if missing
try:
    from flask import (
        Flask,
        Blueprint,
        Response,
        jsonify,
        request,
        render_template,
        stream_with_context,
    )
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    Flask = None
    Blueprint = None

# Configure logging
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 5000
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500
SSE_HEARTBEAT_INTERVAL = 15  # seconds


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class SortOrder(Enum):
    """Sort order for API list responses."""
    ASC = "asc"
    DESC = "desc"


# ---------------------------------------------------------------------------
# ResponseFormatter
# ---------------------------------------------------------------------------

class ResponseFormatter:
    """
    Standardised API response formatter.

    Provides consistent JSON response envelopes for every endpoint:

    Success::

        {
            "status": "success",
            "data": { ... },
            "meta": { ... }          # optional pagination / timing info
        }

    Error::

        {
            "status": "error",
            "message": "Something went wrong",
            "code": 400
        }

    Paginated::

        {
            "status": "success",
            "data": [ ... ],
            "meta": {
                "page": 1,
                "page_size": 50,
                "total_items": 230,
                "total_pages": 5,
                "has_next": true,
                "has_prev": false
            }
        }
    """

    # -- success helpers ----------------------------------------------------

    @staticmethod
    def success(
        data: Any = None,
        message: Optional[str] = None,
        status_code: int = 200,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], int]:
        """
        Build a success response envelope.

        Args:
            data: Payload to return under ``"data"`` key.
            message: Optional human-readable message.
            status_code: HTTP status code (default 200).
            meta: Optional metadata dict (timing, version, etc.).

        Returns:
            Tuple of (response_body_dict, status_code).
        """
        body: Dict[str, Any] = {"status": "success"}
        if data is not None:
            body["data"] = data
        if message is not None:
            body["message"] = message
        if meta is not None:
            body["meta"] = meta
        return body, status_code

    @staticmethod
    def error(
        message: str,
        status_code: int = 400,
        errors: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[Dict[str, Any], int]:
        """
        Build an error response envelope.

        Args:
            message: Human-readable error description.
            status_code: HTTP status code (default 400).
            errors: Optional list of detailed error dicts.

        Returns:
            Tuple of (response_body_dict, status_code).
        """
        body: Dict[str, Any] = {
            "status": "error",
            "message": message,
            "code": status_code,
        }
        if errors:
            body["errors"] = errors
        return body, status_code

    # -- pagination helpers -------------------------------------------------

    @staticmethod
    def paginate(
        items: List[Any],
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        total_items: Optional[int] = None,
    ) -> Tuple[Dict[str, Any], int]:
        """
        Build a paginated success response.

        When *items* is already the full collection the helper slices it
        automatically.  When the caller has pre-sliced, pass *total_items*
        explicitly so the pagination metadata is correct.

        Args:
            items: The list (or pre-sliced page) of items.
            page: Current page number (1-based).
            page_size: Items per page.
            total_items: Total number of items across all pages.

        Returns:
            Tuple of (response_body_dict, 200).
        """
        page = max(1, page)
        page_size = min(max(1, page_size), MAX_PAGE_SIZE)

        if total_items is None:
            total_items = len(items)
            start = (page - 1) * page_size
            end = start + page_size
            page_items = items[start:end]
        else:
            page_items = items

        total_pages = max(1, (total_items + page_size - 1) // page_size)

        meta = {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

        return ResponseFormatter.success(data=page_items, meta=meta)

    # -- filtering / sorting ------------------------------------------------

    @staticmethod
    def apply_filters(
        items: List[Dict[str, Any]],
        filters: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Apply key-value equality filters to a list of dicts.

        Args:
            items: List of dicts to filter.
            filters: Key/value pairs; items must match **all** to be included.

        Returns:
            Filtered list of dicts.
        """
        if not filters:
            return items

        result: List[Dict[str, Any]] = []
        for item in items:
            match = True
            for key, value in filters.items():
                item_val = item.get(key)
                # Support case-insensitive string comparison
                if isinstance(item_val, str) and isinstance(value, str):
                    if item_val.lower() != value.lower():
                        match = False
                        break
                elif item_val != value:
                    match = False
                    break
            if match:
                result.append(item)
        return result

    @staticmethod
    def apply_sort(
        items: List[Dict[str, Any]],
        sort_by: Optional[str] = None,
        order: SortOrder = SortOrder.ASC,
    ) -> List[Dict[str, Any]]:
        """
        Sort a list of dicts by a given key.

        Args:
            items: List of dicts to sort.
            sort_by: Dict key to sort on.
            order: ``SortOrder.ASC`` or ``SortOrder.DESC``.

        Returns:
            Sorted (shallow-copied) list.
        """
        if not sort_by:
            return items

        reverse = order == SortOrder.DESC
        try:
            return sorted(
                items,
                key=lambda x: (x.get(sort_by) is None, x.get(sort_by)),
                reverse=reverse,
            )
        except TypeError:
            logger.warning("Unable to sort by key '%s'", sort_by)
            return items

    @staticmethod
    def extract_pagination_params() -> Tuple[int, int]:
        """
        Extract ``page`` and ``page_size`` query-string parameters from the
        current Flask request.

        Returns:
            Tuple of (page, page_size) with safe defaults.
        """
        try:
            page = int(request.args.get("page", 1))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(request.args.get("page_size", DEFAULT_PAGE_SIZE))
        except (TypeError, ValueError):
            page_size = DEFAULT_PAGE_SIZE
        return max(1, page), min(max(1, page_size), MAX_PAGE_SIZE)

    @staticmethod
    def extract_sort_params() -> Tuple[Optional[str], SortOrder]:
        """
        Extract ``sort_by`` and ``order`` query-string parameters.

        Returns:
            Tuple of (sort_by, SortOrder).
        """
        sort_by = request.args.get("sort_by")
        order_str = request.args.get("order", "asc").lower()
        order = SortOrder.DESC if order_str == "desc" else SortOrder.ASC
        return sort_by, order

    @staticmethod
    def extract_filters(allowed_keys: List[str]) -> Dict[str, str]:
        """
        Extract filter query-string parameters limited to *allowed_keys*.

        Args:
            allowed_keys: List of keys that are safe to filter on.

        Returns:
            Dict of filter key/value pairs present in the request.
        """
        filters: Dict[str, str] = {}
        for key in allowed_keys:
            val = request.args.get(key)
            if val is not None:
                filters[key] = val
        return filters


# ---------------------------------------------------------------------------
# Demo / stub data generators
# ---------------------------------------------------------------------------

class _DemoData:
    """
    Generates realistic-looking demo data so the API can be exercised without
    a live data feed.  In production these calls would be replaced by service
    layer queries.
    """

    # Commodity futures symbols
    SYMBOLS = [
        {"symbol": "CL", "name": "Crude Oil", "exchange": "NYMEX", "currency": "USD"},
        {"symbol": "GC", "name": "Gold", "exchange": "COMEX", "currency": "USD"},
        {"symbol": "SI", "name": "Silver", "exchange": "COMEX", "currency": "USD"},
        {"symbol": "NG", "name": "Natural Gas", "exchange": "NYMEX", "currency": "USD"},
        {"symbol": "HG", "name": "Copper", "exchange": "COMEX", "currency": "USD"},
        {"symbol": "ZC", "name": "Corn", "exchange": "CBOT", "currency": "USD"},
        {"symbol": "ZS", "name": "Soybeans", "exchange": "CBOT", "currency": "USD"},
        {"symbol": "ZW", "name": "Wheat", "exchange": "CBOT", "currency": "USD"},
        {"symbol": "KC", "name": "Coffee", "exchange": "ICE", "currency": "USD"},
        {"symbol": "CT", "name": "Cotton", "exchange": "ICE", "currency": "USD"},
        {"symbol": "SB", "name": "Sugar", "exchange": "ICE", "currency": "USD"},
        {"symbol": "PL", "name": "Platinum", "exchange": "NYMEX", "currency": "USD"},
    ]

    # Base prices keyed by symbol
    _BASE_PRICES: Dict[str, float] = {
        "CL": 78.45, "GC": 2345.60, "SI": 27.85, "NG": 3.24,
        "HG": 4.12, "ZC": 485.50, "ZS": 1342.75, "ZW": 612.25,
        "KC": 185.30, "CT": 82.15, "SB": 21.45, "PL": 1025.80,
    }

    @classmethod
    def _price_jitter(cls, base: float) -> float:
        """Add small deterministic jitter based on current second."""
        import hashlib
        seed = int(time.time()) % 60
        h = int(hashlib.md5(str(seed).encode()).hexdigest()[:8], 16)
        pct = ((h % 200) - 100) / 10000.0  # +/- 1 %
        return round(base * (1 + pct), 4)

    @classmethod
    def markets(cls) -> List[Dict[str, Any]]:
        """Return list of market snapshots."""
        result = []
        for sym in cls.SYMBOLS:
            base = cls._BASE_PRICES[sym["symbol"]]
            price = cls._price_jitter(base)
            change = round(price - base, 4)
            change_pct = round((change / base) * 100, 4)
            result.append({
                **sym,
                "price": price,
                "change": change,
                "change_pct": change_pct,
                "bid": round(price - 0.02 * abs(price) / 100, 4),
                "ask": round(price + 0.02 * abs(price) / 100, 4),
                "volume": 12000 + int(time.time() % 5000),
                "high": round(price * 1.008, 4),
                "low": round(price * 0.992, 4),
                "updated_at": datetime.utcnow().isoformat() + "Z",
            })
        return result

    @classmethod
    def market_detail(cls, symbol: str) -> Optional[Dict[str, Any]]:
        """Return detailed info for a single market."""
        symbol = symbol.upper()
        entry = next((s for s in cls.SYMBOLS if s["symbol"] == symbol), None)
        if entry is None:
            return None
        base = cls._BASE_PRICES.get(symbol, 100.0)
        price = cls._price_jitter(base)
        return {
            **entry,
            "price": price,
            "change": round(price - base, 4),
            "change_pct": round(((price - base) / base) * 100, 4),
            "bid": round(price - 0.02 * abs(price) / 100, 4),
            "ask": round(price + 0.02 * abs(price) / 100, 4),
            "volume": 12000 + int(time.time() % 5000),
            "high": round(price * 1.008, 4),
            "low": round(price * 0.992, 4),
            "open": round(base * 0.998, 4),
            "prev_close": base,
            "contract_size": 1000,
            "tick_size": 0.01,
            "margin_requirement": 0.05,
            "trading_hours": "Sun-Fri 18:00-17:00 ET",
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }

    @classmethod
    def signals(cls, active_only: bool = True) -> List[Dict[str, Any]]:
        """Return demo trading signals."""
        now = datetime.utcnow()
        all_signals = [
            {
                "id": "sig-001",
                "symbol": "CL",
                "signal_type": "BUY",
                "confidence": 82.5,
                "entry_price": 78.20,
                "stop_loss": 76.50,
                "target_1": 80.00,
                "target_2": 82.50,
                "risk_reward": 2.35,
                "timeframe": "4H",
                "status": "active",
                "created_at": (now - timedelta(hours=2)).isoformat() + "Z",
                "reasoning": ["Bullish engulfing on 4H", "RSI divergence", "Above 200 SMA"],
            },
            {
                "id": "sig-002",
                "symbol": "GC",
                "signal_type": "SELL",
                "confidence": 71.0,
                "entry_price": 2350.00,
                "stop_loss": 2380.00,
                "target_1": 2310.00,
                "target_2": 2280.00,
                "risk_reward": 1.67,
                "timeframe": "1D",
                "status": "active",
                "created_at": (now - timedelta(hours=5)).isoformat() + "Z",
                "reasoning": ["Double top pattern", "Bearish MACD crossover"],
            },
            {
                "id": "sig-003",
                "symbol": "NG",
                "signal_type": "BUY",
                "confidence": 65.0,
                "entry_price": 3.18,
                "stop_loss": 3.05,
                "target_1": 3.40,
                "target_2": None,
                "risk_reward": 1.69,
                "timeframe": "1H",
                "status": "active",
                "created_at": (now - timedelta(minutes=45)).isoformat() + "Z",
                "reasoning": ["Hammer candle at support", "Oversold RSI"],
            },
            {
                "id": "sig-004",
                "symbol": "SI",
                "signal_type": "BUY",
                "confidence": 88.0,
                "entry_price": 27.50,
                "stop_loss": 26.80,
                "target_1": 28.50,
                "target_2": 29.20,
                "risk_reward": 2.14,
                "timeframe": "1D",
                "status": "closed",
                "closed_at": (now - timedelta(hours=12)).isoformat() + "Z",
                "created_at": (now - timedelta(days=2)).isoformat() + "Z",
                "result": "target_1_hit",
                "pnl": 1.00,
                "reasoning": ["Breakout above resistance", "Volume surge"],
            },
            {
                "id": "sig-005",
                "symbol": "ZC",
                "signal_type": "SELL",
                "confidence": 60.0,
                "entry_price": 490.00,
                "stop_loss": 500.00,
                "target_1": 475.00,
                "target_2": None,
                "risk_reward": 1.50,
                "timeframe": "4H",
                "status": "closed",
                "closed_at": (now - timedelta(days=1)).isoformat() + "Z",
                "created_at": (now - timedelta(days=3)).isoformat() + "Z",
                "result": "stopped_out",
                "pnl": -10.00,
                "reasoning": ["Bearish flag pattern"],
            },
        ]
        if active_only:
            return [s for s in all_signals if s["status"] == "active"]
        return all_signals

    @classmethod
    def portfolio(cls) -> Dict[str, Any]:
        """Return portfolio summary."""
        return {
            "account_balance": 100000.00,
            "equity": 102350.75,
            "unrealized_pnl": 2350.75,
            "realized_pnl": 4820.00,
            "margin_used": 15200.00,
            "margin_available": 87150.75,
            "margin_level_pct": 673.36,
            "open_positions_count": 3,
            "total_trades": 47,
            "win_rate": 63.8,
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }

    @classmethod
    def positions(cls) -> List[Dict[str, Any]]:
        """Return open positions."""
        now = datetime.utcnow()
        return [
            {
                "id": "pos-001",
                "symbol": "CL",
                "direction": "LONG",
                "quantity": 2,
                "entry_price": 77.80,
                "current_price": 78.45,
                "unrealized_pnl": 1300.00,
                "stop_loss": 76.50,
                "take_profit": 80.00,
                "margin": 7800.00,
                "opened_at": (now - timedelta(hours=6)).isoformat() + "Z",
            },
            {
                "id": "pos-002",
                "symbol": "GC",
                "direction": "SHORT",
                "quantity": 1,
                "entry_price": 2360.00,
                "current_price": 2345.60,
                "unrealized_pnl": 1440.00,
                "stop_loss": 2380.00,
                "take_profit": 2310.00,
                "margin": 4720.00,
                "opened_at": (now - timedelta(hours=18)).isoformat() + "Z",
            },
            {
                "id": "pos-003",
                "symbol": "NG",
                "direction": "LONG",
                "quantity": 5,
                "entry_price": 3.20,
                "current_price": 3.24,
                "unrealized_pnl": -389.25,
                "stop_loss": 3.05,
                "take_profit": 3.45,
                "margin": 2680.00,
                "opened_at": (now - timedelta(hours=1)).isoformat() + "Z",
            },
        ]

    @classmethod
    def trade_history(cls) -> List[Dict[str, Any]]:
        """Return recent closed trades."""
        now = datetime.utcnow()
        return [
            {
                "id": "trade-040",
                "symbol": "SI",
                "direction": "LONG",
                "quantity": 3,
                "entry_price": 27.50,
                "exit_price": 28.50,
                "pnl": 3000.00,
                "pnl_pct": 3.64,
                "close_reason": "TAKE_PROFIT",
                "opened_at": (now - timedelta(days=2)).isoformat() + "Z",
                "closed_at": (now - timedelta(hours=12)).isoformat() + "Z",
            },
            {
                "id": "trade-039",
                "symbol": "ZC",
                "direction": "SHORT",
                "quantity": 2,
                "entry_price": 490.00,
                "exit_price": 500.00,
                "pnl": -2000.00,
                "pnl_pct": -2.04,
                "close_reason": "STOP_LOSS",
                "opened_at": (now - timedelta(days=3)).isoformat() + "Z",
                "closed_at": (now - timedelta(days=1)).isoformat() + "Z",
            },
            {
                "id": "trade-038",
                "symbol": "CL",
                "direction": "LONG",
                "quantity": 1,
                "entry_price": 76.20,
                "exit_price": 78.10,
                "pnl": 1900.00,
                "pnl_pct": 2.49,
                "close_reason": "TAKE_PROFIT",
                "opened_at": (now - timedelta(days=5)).isoformat() + "Z",
                "closed_at": (now - timedelta(days=3)).isoformat() + "Z",
            },
            {
                "id": "trade-037",
                "symbol": "KC",
                "direction": "LONG",
                "quantity": 2,
                "entry_price": 180.50,
                "exit_price": 185.80,
                "pnl": 1060.00,
                "pnl_pct": 2.94,
                "close_reason": "MANUAL",
                "opened_at": (now - timedelta(days=7)).isoformat() + "Z",
                "closed_at": (now - timedelta(days=5)).isoformat() + "Z",
            },
            {
                "id": "trade-036",
                "symbol": "HG",
                "direction": "SHORT",
                "quantity": 3,
                "entry_price": 4.18,
                "exit_price": 4.10,
                "pnl": 600.00,
                "pnl_pct": 1.91,
                "close_reason": "TAKE_PROFIT",
                "opened_at": (now - timedelta(days=8)).isoformat() + "Z",
                "closed_at": (now - timedelta(days=6)).isoformat() + "Z",
            },
        ]

    @classmethod
    def performance(cls) -> Dict[str, Any]:
        """Return performance metrics."""
        return {
            "total_return": 4.82,
            "total_return_pct": 4.82,
            "annualized_return": 28.5,
            "sharpe_ratio": 1.85,
            "sortino_ratio": 2.42,
            "max_drawdown": -3.2,
            "max_drawdown_duration_days": 4,
            "win_rate": 63.8,
            "profit_factor": 2.15,
            "avg_win": 1580.00,
            "avg_loss": -735.00,
            "best_trade": 3200.00,
            "worst_trade": -1800.00,
            "avg_holding_period_hours": 36.5,
            "total_trades": 47,
            "winning_trades": 30,
            "losing_trades": 17,
            "consecutive_wins": 5,
            "consecutive_losses": 2,
            "expectancy": 478.30,
            "period_start": (datetime.utcnow() - timedelta(days=60)).isoformat() + "Z",
            "period_end": datetime.utcnow().isoformat() + "Z",
        }

    @classmethod
    def equity_curve(cls) -> List[Dict[str, Any]]:
        """Return equity curve data points."""
        now = datetime.utcnow()
        base = 100000.0
        curve = []
        # Simulate 60 days of equity values
        import hashlib
        for i in range(60):
            day = now - timedelta(days=59 - i)
            h = int(hashlib.md5(f"eq-{i}".encode()).hexdigest()[:8], 16)
            daily_return = ((h % 200) - 80) / 10000.0  # slight upward bias
            base = round(base * (1 + daily_return), 2)
            curve.append({
                "date": day.strftime("%Y-%m-%d"),
                "equity": base,
                "drawdown_pct": round(min(0, (base - 102500) / 102500 * 100), 4),
            })
        return curve

    @classmethod
    def risk_metrics(cls) -> Dict[str, Any]:
        """Return risk metrics."""
        return {
            "portfolio_var_95": -2150.00,
            "portfolio_var_99": -3420.00,
            "portfolio_cvar_95": -2780.00,
            "beta": 0.45,
            "correlation_sp500": 0.32,
            "current_exposure": 15200.00,
            "max_allowed_exposure": 50000.00,
            "exposure_utilization_pct": 30.4,
            "position_concentration": {
                "CL": 51.3,
                "GC": 31.1,
                "NG": 17.6,
            },
            "risk_per_trade_pct": 2.0,
            "max_daily_loss": -3000.00,
            "current_daily_pnl": 1245.50,
            "margin_call_level": 50.0,
            "current_margin_level": 673.36,
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }

    @classmethod
    def config(cls) -> Dict[str, Any]:
        """Return current configuration."""
        return {
            "trading": {
                "max_positions": 10,
                "max_risk_per_trade_pct": 2.0,
                "max_daily_loss": 3000.00,
                "default_leverage": 10,
                "allowed_instruments": ["CL", "GC", "SI", "NG", "HG", "ZC", "ZS", "ZW"],
                "trading_hours": "auto",
            },
            "signals": {
                "min_confidence": 60.0,
                "min_risk_reward": 1.5,
                "timeframes": ["1H", "4H", "1D"],
                "strategies_enabled": [
                    "trend_following",
                    "mean_reversion",
                    "breakout",
                ],
            },
            "risk": {
                "max_portfolio_exposure_pct": 50.0,
                "max_correlation_between_positions": 0.7,
                "stop_loss_required": True,
                "max_position_size_pct": 20.0,
            },
            "notifications": {
                "email_enabled": False,
                "slack_enabled": False,
                "signal_alerts": True,
                "risk_alerts": True,
            },
            "data": {
                "provider": "oanda",
                "update_interval_seconds": 5,
                "history_days": 365,
            },
        }


# ---------------------------------------------------------------------------
# CORS helper (lightweight, no extension needed)
# ---------------------------------------------------------------------------

def _add_cors_headers(response: Response) -> Response:
    """
    Attach permissive CORS headers to every response.

    In production you would restrict ``Access-Control-Allow-Origin`` to your
    actual frontend domain.
    """
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Request-ID"
    response.headers["Access-Control-Max-Age"] = "86400"
    return response


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------

def _sse_event(data: Any, event: Optional[str] = None, event_id: Optional[str] = None) -> str:
    """
    Format a single Server-Sent Event frame.

    Args:
        data: JSON-serialisable payload.
        event: Optional event name (``event:`` field).
        event_id: Optional event id (``id:`` field).

    Returns:
        Formatted SSE string ending with double newline.
    """
    lines: List[str] = []
    if event_id:
        lines.append(f"id: {event_id}")
    if event:
        lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data)}")
    lines.append("")  # blank line terminates the event
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Blueprint factory
# ---------------------------------------------------------------------------

def _create_api_blueprint() -> Blueprint:
    """
    Create and return the ``/api/v1`` Flask Blueprint with all endpoint
    handlers registered.

    Returns:
        Configured Flask ``Blueprint`` instance.
    """
    api = Blueprint("api_v1", __name__, url_prefix=API_PREFIX)
    fmt = ResponseFormatter

    # -- Health -------------------------------------------------------------

    @api.route("/health", methods=["GET"])
    def health() -> Response:
        """Health-check endpoint returning service status."""
        data = {
            "service": "ScreenerIII",
            "version": "0.1.0",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "uptime_seconds": round(time.time() - _app_start_time, 2),
        }
        body, code = fmt.success(data=data)
        return jsonify(body), code

    # -- Markets ------------------------------------------------------------

    @api.route("/markets", methods=["GET"])
    def list_markets() -> Response:
        """
        List all tracked markets with current price snapshots.

        Query parameters:
            exchange (str): Filter by exchange.
            sort_by  (str): Field to sort on.
            order    (str): ``asc`` or ``desc``.
            page     (int): Page number.
            page_size(int): Items per page.
        """
        logger.debug("Fetching market list")
        markets = _DemoData.markets()

        # Filtering
        filters = fmt.extract_filters(["exchange", "currency"])
        markets = fmt.apply_filters(markets, filters)

        # Sorting
        sort_by, order = fmt.extract_sort_params()
        markets = fmt.apply_sort(markets, sort_by, order)

        # Pagination
        page, page_size = fmt.extract_pagination_params()
        body, code = fmt.paginate(markets, page, page_size)
        return jsonify(body), code

    @api.route("/markets/<symbol>", methods=["GET"])
    def get_market(symbol: str) -> Response:
        """Return detailed market data for *symbol*."""
        logger.debug("Fetching market detail for %s", symbol)
        detail = _DemoData.market_detail(symbol)
        if detail is None:
            body, code = fmt.error(f"Market '{symbol.upper()}' not found", 404)
            return jsonify(body), code
        body, code = fmt.success(data=detail)
        return jsonify(body), code

    # -- Signals ------------------------------------------------------------

    @api.route("/signals", methods=["GET"])
    def active_signals() -> Response:
        """
        Return currently active trading signals.

        Query parameters:
            symbol      (str): Filter by symbol.
            signal_type (str): Filter by BUY/SELL.
            timeframe   (str): Filter by timeframe.
            sort_by     (str): Field to sort on.
            order       (str): ``asc`` or ``desc``.
            page        (int): Page number.
            page_size   (int): Items per page.
        """
        logger.debug("Fetching active signals")
        signals = _DemoData.signals(active_only=True)

        filters = fmt.extract_filters(["symbol", "signal_type", "timeframe"])
        signals = fmt.apply_filters(signals, filters)

        sort_by, order = fmt.extract_sort_params()
        signals = fmt.apply_sort(signals, sort_by, order)

        page, page_size = fmt.extract_pagination_params()
        body, code = fmt.paginate(signals, page, page_size)
        return jsonify(body), code

    @api.route("/signals/history", methods=["GET"])
    def signal_history() -> Response:
        """
        Return full signal history (active + closed).

        Supports the same query parameters as ``/signals``.
        """
        logger.debug("Fetching signal history")
        signals = _DemoData.signals(active_only=False)

        filters = fmt.extract_filters(["symbol", "signal_type", "timeframe", "status"])
        signals = fmt.apply_filters(signals, filters)

        sort_by, order = fmt.extract_sort_params()
        signals = fmt.apply_sort(signals, sort_by, order)

        page, page_size = fmt.extract_pagination_params()
        body, code = fmt.paginate(signals, page, page_size)
        return jsonify(body), code

    # -- Portfolio ----------------------------------------------------------

    @api.route("/portfolio", methods=["GET"])
    def portfolio_summary() -> Response:
        """Return portfolio summary with account balances and statistics."""
        logger.debug("Fetching portfolio summary")
        data = _DemoData.portfolio()
        body, code = fmt.success(data=data)
        return jsonify(body), code

    @api.route("/portfolio/positions", methods=["GET"])
    def portfolio_positions() -> Response:
        """
        Return open positions.

        Query parameters:
            symbol    (str): Filter by symbol.
            direction (str): Filter by LONG/SHORT.
            sort_by   (str): Field to sort on.
            order     (str): ``asc`` or ``desc``.
        """
        logger.debug("Fetching open positions")
        positions = _DemoData.positions()

        filters = fmt.extract_filters(["symbol", "direction"])
        positions = fmt.apply_filters(positions, filters)

        sort_by, order = fmt.extract_sort_params()
        positions = fmt.apply_sort(positions, sort_by, order)

        page, page_size = fmt.extract_pagination_params()
        body, code = fmt.paginate(positions, page, page_size)
        return jsonify(body), code

    @api.route("/portfolio/history", methods=["GET"])
    def trade_history() -> Response:
        """
        Return closed trade history.

        Query parameters:
            symbol       (str): Filter by symbol.
            direction    (str): Filter by LONG/SHORT.
            close_reason (str): Filter by close reason.
            sort_by      (str): Field to sort on.
            order        (str): ``asc`` or ``desc``.
            page         (int): Page number.
            page_size    (int): Items per page.
        """
        logger.debug("Fetching trade history")
        trades = _DemoData.trade_history()

        filters = fmt.extract_filters(["symbol", "direction", "close_reason"])
        trades = fmt.apply_filters(trades, filters)

        sort_by, order = fmt.extract_sort_params()
        trades = fmt.apply_sort(trades, sort_by, order)

        page, page_size = fmt.extract_pagination_params()
        body, code = fmt.paginate(trades, page, page_size)
        return jsonify(body), code

    # -- Performance --------------------------------------------------------

    @api.route("/performance", methods=["GET"])
    def performance_metrics() -> Response:
        """Return performance metrics including Sharpe, Sortino, drawdown, etc."""
        logger.debug("Fetching performance metrics")
        data = _DemoData.performance()
        body, code = fmt.success(data=data)
        return jsonify(body), code

    @api.route("/performance/equity", methods=["GET"])
    def equity_curve() -> Response:
        """
        Return equity curve data points.

        Query parameters:
            days (int): Number of trailing days to include (default 60).
        """
        logger.debug("Fetching equity curve")
        curve = _DemoData.equity_curve()
        try:
            days = int(request.args.get("days", 60))
        except (TypeError, ValueError):
            days = 60
        days = min(max(1, days), 365)
        # Trim to requested window
        curve = curve[-days:]
        body, code = fmt.success(data=curve, meta={"days": days, "points": len(curve)})
        return jsonify(body), code

    # -- Risk ---------------------------------------------------------------

    @api.route("/risk", methods=["GET"])
    def risk_metrics() -> Response:
        """Return current risk metrics (VaR, exposure, margin levels, etc.)."""
        logger.debug("Fetching risk metrics")
        data = _DemoData.risk_metrics()
        body, code = fmt.success(data=data)
        return jsonify(body), code

    # -- Backtest -----------------------------------------------------------

    @api.route("/backtest", methods=["POST"])
    def run_backtest() -> Response:
        """
        Run a backtest.

        Expects a JSON body with:
            symbol    (str):  Instrument symbol (required).
            strategy  (str):  Strategy name (required).
            start_date(str):  ISO date string (optional).
            end_date  (str):  ISO date string (optional).
            params    (dict): Strategy-specific parameters (optional).
        """
        logger.info("Backtest request received")
        payload = request.get_json(silent=True)
        if not payload:
            body, code = fmt.error("Request body must be valid JSON", 400)
            return jsonify(body), code

        symbol = payload.get("symbol")
        strategy = payload.get("strategy")
        if not symbol or not strategy:
            body, code = fmt.error("'symbol' and 'strategy' are required fields", 400)
            return jsonify(body), code

        start_date = payload.get("start_date", (datetime.utcnow() - timedelta(days=180)).strftime("%Y-%m-%d"))
        end_date = payload.get("end_date", datetime.utcnow().strftime("%Y-%m-%d"))
        params = payload.get("params", {})

        # In production this would delegate to the backtesting engine.
        # Here we return a plausible stub result.
        result = {
            "backtest_id": str(uuid.uuid4())[:8],
            "symbol": symbol.upper(),
            "strategy": strategy,
            "start_date": start_date,
            "end_date": end_date,
            "params": params,
            "results": {
                "total_return_pct": 12.45,
                "sharpe_ratio": 1.62,
                "max_drawdown_pct": -5.8,
                "win_rate": 58.3,
                "total_trades": 84,
                "profit_factor": 1.85,
                "avg_trade_pnl": 148.21,
                "avg_holding_period_hours": 28.4,
            },
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat() + "Z",
        }

        logger.info(
            "Backtest completed: %s on %s (%s -> %s)",
            strategy, symbol, start_date, end_date,
        )
        body, code = fmt.success(data=result, status_code=201)
        return jsonify(body), code

    # -- Configuration ------------------------------------------------------

    @api.route("/config", methods=["GET"])
    def get_config() -> Response:
        """Return current application configuration."""
        logger.debug("Fetching configuration")
        data = _DemoData.config()
        body, code = fmt.success(data=data)
        return jsonify(body), code

    @api.route("/config", methods=["PUT"])
    def update_config() -> Response:
        """
        Update application configuration.

        Expects a JSON body with one or more top-level config sections
        (``trading``, ``signals``, ``risk``, ``notifications``, ``data``).
        Only provided keys are updated; others remain unchanged.
        """
        logger.info("Configuration update request received")
        payload = request.get_json(silent=True)
        if not payload:
            body, code = fmt.error("Request body must be valid JSON", 400)
            return jsonify(body), code

        current = _DemoData.config()

        valid_sections = set(current.keys())
        invalid = set(payload.keys()) - valid_sections
        if invalid:
            body, code = fmt.error(
                f"Invalid config sections: {', '.join(sorted(invalid))}. "
                f"Valid sections: {', '.join(sorted(valid_sections))}",
                400,
            )
            return jsonify(body), code

        # Merge (shallow per section)
        for section, values in payload.items():
            if isinstance(values, dict) and isinstance(current.get(section), dict):
                current[section].update(values)
            else:
                current[section] = values

        logger.info("Configuration updated: sections=%s", list(payload.keys()))
        body, code = fmt.success(data=current, message="Configuration updated")
        return jsonify(body), code

    # -- SSE streams --------------------------------------------------------

    @api.route("/stream/prices", methods=["GET"])
    def stream_prices() -> Response:
        """
        Server-Sent Events stream of price updates.

        Sends a JSON price snapshot every ~2 seconds and a heartbeat comment
        every 15 seconds.  Clients can filter with ``?symbols=CL,GC``.
        """
        logger.info("SSE price stream opened")
        requested = request.args.get("symbols", "")
        symbols_filter = [s.strip().upper() for s in requested.split(",") if s.strip()] or None

        def generate() -> Generator[str, None, None]:
            last_heartbeat = time.time()
            seq = 0
            try:
                while True:
                    markets = _DemoData.markets()
                    if symbols_filter:
                        markets = [m for m in markets if m["symbol"] in symbols_filter]
                    seq += 1
                    yield _sse_event(
                        data={"prices": markets, "seq": seq},
                        event="price_update",
                        event_id=str(seq),
                    )

                    now = time.time()
                    if now - last_heartbeat >= SSE_HEARTBEAT_INTERVAL:
                        yield ": heartbeat\n\n"
                        last_heartbeat = now

                    time.sleep(2)
            except GeneratorExit:
                logger.info("SSE price stream closed by client")

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    @api.route("/stream/signals", methods=["GET"])
    def stream_signals() -> Response:
        """
        Server-Sent Events stream of trading signals.

        Sends the current active signals every ~5 seconds.
        """
        logger.info("SSE signal stream opened")

        def generate() -> Generator[str, None, None]:
            last_heartbeat = time.time()
            seq = 0
            try:
                while True:
                    signals = _DemoData.signals(active_only=True)
                    seq += 1
                    yield _sse_event(
                        data={"signals": signals, "seq": seq},
                        event="signal_update",
                        event_id=str(seq),
                    )

                    now = time.time()
                    if now - last_heartbeat >= SSE_HEARTBEAT_INTERVAL:
                        yield ": heartbeat\n\n"
                        last_heartbeat = now

                    time.sleep(5)
            except GeneratorExit:
                logger.info("SSE signal stream closed by client")

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    return api


# ---------------------------------------------------------------------------
# Module-level timestamp for uptime calculation
# ---------------------------------------------------------------------------

_app_start_time: float = time.time()


# ---------------------------------------------------------------------------
# ScreenerApp - application factory
# ---------------------------------------------------------------------------

class ScreenerApp:
    """
    Flask application factory for the ScreenerIII web dashboard.

    Usage::

        app_wrapper = ScreenerApp()
        flask_app = app_wrapper.app          # the raw Flask instance
        app_wrapper.run(host="0.0.0.0", port=5000, debug=True)

    Or using the factory function::

        flask_app = create_app()
        flask_app.run()

    The class takes care of:
    - Registering the ``/api/v1/`` blueprint
    - CORS headers on every response (including ``OPTIONS`` pre-flight)
    - Centralised JSON error handlers for common HTTP errors
    - Per-request logging with timing and request IDs
    - A minimal HTML dashboard served at ``/``
    """

    def __init__(
        self,
        name: Optional[str] = None,
        debug: bool = False,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialise the ScreenerApp.

        Args:
            name: Flask application name (defaults to module name).
            debug: Enable Flask debug mode.
            config: Optional dict of Flask config overrides.

        Raises:
            ImportError: If Flask is not installed.
        """
        if not FLASK_AVAILABLE:
            raise ImportError(
                "Flask is required for the ScreenerIII web dashboard. "
                "Install it with:  pip install flask"
            )

        global _app_start_time
        _app_start_time = time.time()

        self._debug = debug
        template_dir = str(Path(__file__).resolve().parent / "templates")
        self.app: Flask = Flask(
            name or __name__,
            template_folder=template_dir,
        )
        self.app.config["JSON_SORT_KEYS"] = False

        if config:
            self.app.config.update(config)

        self._register_error_handlers()
        self._register_middleware()
        self._register_blueprints()
        self._register_root_routes()

        logger.info(
            "ScreenerApp initialised (debug=%s, template_dir=%s)",
            debug, template_dir,
        )

    # -- internal setup methods ---------------------------------------------

    def _register_blueprints(self) -> None:
        """Register API v1 blueprint."""
        api_bp = _create_api_blueprint()
        self.app.register_blueprint(api_bp)
        logger.debug("Registered API v1 blueprint at %s", API_PREFIX)

    def _register_error_handlers(self) -> None:
        """Register JSON error handlers for common HTTP error codes."""
        fmt = ResponseFormatter

        @self.app.errorhandler(400)
        def bad_request(exc: Exception) -> Response:
            body, code = fmt.error(str(exc), 400)
            return jsonify(body), code

        @self.app.errorhandler(404)
        def not_found(exc: Exception) -> Response:
            body, code = fmt.error("The requested resource was not found", 404)
            return jsonify(body), code

        @self.app.errorhandler(405)
        def method_not_allowed(exc: Exception) -> Response:
            body, code = fmt.error("Method not allowed", 405)
            return jsonify(body), code

        @self.app.errorhandler(500)
        def internal_error(exc: Exception) -> Response:
            logger.exception("Internal server error: %s", exc)
            body, code = fmt.error("Internal server error", 500)
            return jsonify(body), code

        @self.app.errorhandler(422)
        def unprocessable(exc: Exception) -> Response:
            body, code = fmt.error("Unprocessable entity", 422)
            return jsonify(body), code

        @self.app.errorhandler(429)
        def rate_limited(exc: Exception) -> Response:
            body, code = fmt.error("Too many requests. Please slow down.", 429)
            return jsonify(body), code

    def _register_middleware(self) -> None:
        """Register before/after request hooks for logging and CORS."""

        @self.app.before_request
        def before_request_hook() -> Optional[Response]:
            """Attach a request ID and start timer; handle OPTIONS pre-flight."""
            request.environ["REQUEST_ID"] = request.headers.get(
                "X-Request-ID", str(uuid.uuid4())[:8]
            )
            request.environ["REQUEST_START"] = time.time()

            # Fast-path for CORS pre-flight requests
            if request.method == "OPTIONS":
                resp = Response("", status=204)
                return _add_cors_headers(resp)

            logger.info(
                "[%s] %s %s (from %s)",
                request.environ["REQUEST_ID"],
                request.method,
                request.path,
                request.remote_addr,
            )
            return None

        @self.app.after_request
        def after_request_hook(response: Response) -> Response:
            """Add CORS headers, timing, and log the response."""
            _add_cors_headers(response)

            elapsed = time.time() - request.environ.get("REQUEST_START", time.time())
            response.headers["X-Request-ID"] = request.environ.get("REQUEST_ID", "")
            response.headers["X-Response-Time"] = f"{elapsed:.4f}s"

            logger.info(
                "[%s] %s %s -> %s (%.4fs)",
                request.environ.get("REQUEST_ID", "?"),
                request.method,
                request.path,
                response.status_code,
                elapsed,
            )
            return response

    def _register_root_routes(self) -> None:
        """Register the root ``/`` route that serves the HTML dashboard."""

        @self.app.route("/")
        def index() -> str:
            """Serve the main dashboard page."""
            return render_template("index.html")

        @self.app.route("/favicon.ico")
        def favicon() -> Response:
            """Return empty favicon to avoid 404 noise in logs."""
            return Response("", status=204)

    # -- public API ---------------------------------------------------------

    def run(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        debug: Optional[bool] = None,
        **kwargs: Any,
    ) -> None:
        """
        Start the Flask development server.

        Args:
            host: Bind address (default ``0.0.0.0``).
            port: Bind port (default ``5000``).
            debug: Override debug flag; falls back to constructor value.
            **kwargs: Forwarded to ``Flask.run()``.
        """
        if debug is None:
            debug = self._debug
        logger.info("Starting ScreenerIII web server on %s:%d (debug=%s)", host, port, debug)
        self.app.run(host=host, port=port, debug=debug, threaded=True, **kwargs)


# ---------------------------------------------------------------------------
# Module-level factory function
# ---------------------------------------------------------------------------

def create_app(
    debug: bool = False,
    config: Optional[Dict[str, Any]] = None,
) -> Flask:
    """
    Application factory that returns a ready-to-use Flask instance.

    This is the recommended entry point for WSGI servers (gunicorn, etc.)::

        gunicorn "src.web.app:create_app()"

    Args:
        debug: Enable Flask debug mode.
        config: Optional dict of Flask config overrides.

    Returns:
        Configured Flask application.
    """
    wrapper = ScreenerApp(debug=debug, config=config)
    return wrapper.app


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    app_wrapper = ScreenerApp(debug=True)
    app_wrapper.run()
