"""
Market Data Structures and Validation

This module provides dataclasses and validation logic for market data,
including prices, spreads, volumes, and historical data management.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, List, Any, Union
from enum import Enum
import logging

import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)


class PriceType(Enum):
    """Price type enumeration."""
    BID = "bid"
    ASK = "ask"
    MID = "mid"


class CandleGranularity(Enum):
    """Candle granularity enumeration."""
    S5 = "S5"    # 5 seconds
    S10 = "S10"  # 10 seconds
    S15 = "S15"  # 15 seconds
    S30 = "S30"  # 30 seconds
    M1 = "M1"    # 1 minute
    M2 = "M2"    # 2 minutes
    M4 = "M4"    # 4 minutes
    M5 = "M5"    # 5 minutes
    M10 = "M10"  # 10 minutes
    M15 = "M15"  # 15 minutes
    M30 = "M30"  # 30 minutes
    H1 = "H1"    # 1 hour
    H2 = "H2"    # 2 hours
    H3 = "H3"    # 3 hours
    H4 = "H4"    # 4 hours
    H6 = "H6"    # 6 hours
    H8 = "H8"    # 8 hours
    H12 = "H12"  # 12 hours
    D = "D"      # 1 day
    W = "W"      # 1 week
    M = "M"      # 1 month


class ValidationError(Exception):
    """Raised when data validation fails."""
    pass


@dataclass
class Price:
    """
    Real-time price data structure.

    Attributes:
        instrument: Instrument identifier (e.g., "EUR_USD")
        bid: Bid price
        ask: Ask price
        timestamp: Price timestamp
        spread: Spread (ask - bid)
        mid: Mid price ((bid + ask) / 2)
        tradeable: Whether instrument is tradeable
        liquidity: Optional liquidity information
    """
    instrument: str
    bid: float
    ask: float
    timestamp: datetime
    spread: Optional[float] = None
    mid: Optional[float] = None
    tradeable: bool = True
    liquidity: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate and compute derived fields."""
        self.validate()

        # Calculate spread if not provided
        if self.spread is None:
            self.spread = self.ask - self.bid

        # Calculate mid price if not provided
        if self.mid is None:
            self.mid = (self.bid + self.ask) / 2.0

    def validate(self) -> None:
        """
        Validate price data.

        Raises:
            ValidationError: If validation fails
        """
        if not self.instrument:
            raise ValidationError("Instrument cannot be empty")

        if self.bid <= 0:
            raise ValidationError(f"Invalid bid price: {self.bid}")

        if self.ask <= 0:
            raise ValidationError(f"Invalid ask price: {self.ask}")

        if self.ask < self.bid:
            raise ValidationError(
                f"Ask price ({self.ask}) cannot be less than bid price ({self.bid})"
            )

        if not isinstance(self.timestamp, datetime):
            raise ValidationError("Timestamp must be a datetime object")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "instrument": self.instrument,
            "bid": self.bid,
            "ask": self.ask,
            "spread": self.spread,
            "mid": self.mid,
            "timestamp": self.timestamp.isoformat(),
            "tradeable": self.tradeable,
            "liquidity": self.liquidity
        }

    @classmethod
    def from_oanda_response(cls, data: Dict[str, Any]) -> 'Price':
        """
        Create Price object from OANDA API response.

        Args:
            data: OANDA price data dictionary

        Returns:
            Price object
        """
        return cls(
            instrument=data.get("instrument", ""),
            bid=float(data.get("bids", [{}])[0].get("price", 0)),
            ask=float(data.get("asks", [{}])[0].get("price", 0)),
            timestamp=datetime.fromisoformat(
                data.get("time", "").replace("Z", "+00:00")
            ),
            tradeable=data.get("tradeable", True),
            liquidity=data.get("liquidity")
        )


@dataclass
class Candle:
    """
    OHLCV candle data structure.

    Attributes:
        instrument: Instrument identifier
        timestamp: Candle timestamp
        open: Opening price
        high: High price
        low: Low price
        close: Closing price
        volume: Trading volume
        complete: Whether candle is complete
        granularity: Candle granularity
    """
    instrument: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    complete: bool = True
    granularity: Optional[str] = None

    def __post_init__(self):
        """Validate candle data."""
        self.validate()

    def validate(self) -> None:
        """
        Validate candle data.

        Raises:
            ValidationError: If validation fails
        """
        if not self.instrument:
            raise ValidationError("Instrument cannot be empty")

        if self.high < self.low:
            raise ValidationError(
                f"High ({self.high}) cannot be less than low ({self.low})"
            )

        if self.high < self.open or self.high < self.close:
            raise ValidationError(
                f"High ({self.high}) must be >= open and close"
            )

        if self.low > self.open or self.low > self.close:
            raise ValidationError(
                f"Low ({self.low}) must be <= open and close"
            )

        if self.volume < 0:
            raise ValidationError(f"Invalid volume: {self.volume}")

        if not isinstance(self.timestamp, datetime):
            raise ValidationError("Timestamp must be a datetime object")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "instrument": self.instrument,
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "complete": self.complete,
            "granularity": self.granularity
        }

    @classmethod
    def from_oanda_response(
        cls,
        instrument: str,
        data: Dict[str, Any],
        price_type: str = "mid",
        granularity: Optional[str] = None
    ) -> 'Candle':
        """
        Create Candle object from OANDA API response.

        Args:
            instrument: Instrument identifier
            data: OANDA candle data dictionary
            price_type: Price type (bid, ask, mid)
            granularity: Candle granularity

        Returns:
            Candle object
        """
        price_data = data.get(price_type, {})

        return cls(
            instrument=instrument,
            timestamp=datetime.fromisoformat(
                data.get("time", "").replace("Z", "+00:00")
            ),
            open=float(price_data.get("o", 0)),
            high=float(price_data.get("h", 0)),
            low=float(price_data.get("l", 0)),
            close=float(price_data.get("c", 0)),
            volume=int(data.get("volume", 0)),
            complete=data.get("complete", True),
            granularity=granularity
        )


@dataclass
class SpreadData:
    """
    Spread data structure.

    Attributes:
        instrument: Instrument identifier
        timestamp: Timestamp
        spread: Spread value (ask - bid)
        spread_pips: Spread in pips
        spread_percentage: Spread as percentage of mid price
    """
    instrument: str
    timestamp: datetime
    spread: float
    spread_pips: Optional[float] = None
    spread_percentage: Optional[float] = None

    def __post_init__(self):
        """Validate spread data."""
        self.validate()

    def validate(self) -> None:
        """
        Validate spread data.

        Raises:
            ValidationError: If validation fails
        """
        if not self.instrument:
            raise ValidationError("Instrument cannot be empty")

        if self.spread < 0:
            raise ValidationError(f"Invalid spread: {self.spread}")

        if not isinstance(self.timestamp, datetime):
            raise ValidationError("Timestamp must be a datetime object")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "instrument": self.instrument,
            "timestamp": self.timestamp.isoformat(),
            "spread": self.spread,
            "spread_pips": self.spread_pips,
            "spread_percentage": self.spread_percentage
        }


@dataclass
class VolumeData:
    """
    Volume data structure.

    Attributes:
        instrument: Instrument identifier
        timestamp: Timestamp
        volume: Trading volume
        volume_ma: Moving average volume (optional)
        relative_volume: Relative volume ratio (optional)
    """
    instrument: str
    timestamp: datetime
    volume: int
    volume_ma: Optional[float] = None
    relative_volume: Optional[float] = None

    def __post_init__(self):
        """Validate volume data."""
        self.validate()

    def validate(self) -> None:
        """
        Validate volume data.

        Raises:
            ValidationError: If validation fails
        """
        if not self.instrument:
            raise ValidationError("Instrument cannot be empty")

        if self.volume < 0:
            raise ValidationError(f"Invalid volume: {self.volume}")

        if not isinstance(self.timestamp, datetime):
            raise ValidationError("Timestamp must be a datetime object")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "instrument": self.instrument,
            "timestamp": self.timestamp.isoformat(),
            "volume": self.volume,
            "volume_ma": self.volume_ma,
            "relative_volume": self.relative_volume
        }


class HistoricalDataManager:
    """
    Manager for historical market data.

    Provides methods for storing, retrieving, and managing historical
    candle data using pandas DataFrames.
    """

    def __init__(self):
        """Initialize historical data manager."""
        self._data: Dict[str, pd.DataFrame] = {}
        logger.debug("Historical data manager initialized")

    def add_candles(
        self,
        instrument: str,
        candles: List[Candle]
    ) -> None:
        """
        Add candles to historical data.

        Args:
            instrument: Instrument identifier
            candles: List of Candle objects
        """
        if not candles:
            logger.warning(f"No candles to add for {instrument}")
            return

        # Convert candles to DataFrame
        df = pd.DataFrame([c.to_dict() for c in candles])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)

        # Merge with existing data
        if instrument in self._data:
            self._data[instrument] = pd.concat(
                [self._data[instrument], df]
            ).sort_index()
            # Remove duplicates, keeping last
            self._data[instrument] = self._data[instrument][
                ~self._data[instrument].index.duplicated(keep='last')
            ]
        else:
            self._data[instrument] = df

        logger.debug(
            f"Added {len(candles)} candles for {instrument}, "
            f"total: {len(self._data[instrument])}"
        )

    def get_candles(
        self,
        instrument: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get historical candles for an instrument.

        Args:
            instrument: Instrument identifier
            start_time: Start time filter
            end_time: End time filter
            limit: Maximum number of candles to return

        Returns:
            DataFrame containing candle data

        Raises:
            KeyError: If instrument not found
        """
        if instrument not in self._data:
            raise KeyError(f"No data found for instrument: {instrument}")

        df = self._data[instrument].copy()

        # Apply time filters
        if start_time is not None:
            df = df[df.index >= start_time]

        if end_time is not None:
            df = df[df.index <= end_time]

        # Apply limit
        if limit is not None:
            df = df.tail(limit)

        return df

    def get_latest_candle(self, instrument: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest candle for an instrument.

        Args:
            instrument: Instrument identifier

        Returns:
            Dictionary with latest candle data or None
        """
        if instrument not in self._data or self._data[instrument].empty:
            return None

        latest = self._data[instrument].iloc[-1]
        return latest.to_dict()

    def has_data(self, instrument: str) -> bool:
        """
        Check if data exists for an instrument.

        Args:
            instrument: Instrument identifier

        Returns:
            True if data exists, False otherwise
        """
        return instrument in self._data and not self._data[instrument].empty

    def get_instruments(self) -> List[str]:
        """
        Get list of instruments with historical data.

        Returns:
            List of instrument identifiers
        """
        return list(self._data.keys())

    def clear(self, instrument: Optional[str] = None) -> None:
        """
        Clear historical data.

        Args:
            instrument: If provided, clear only this instrument,
                       otherwise clear all data
        """
        if instrument:
            if instrument in self._data:
                del self._data[instrument]
                logger.debug(f"Cleared data for {instrument}")
        else:
            self._data.clear()
            logger.debug("Cleared all historical data")

    def get_statistics(self, instrument: str) -> Dict[str, Any]:
        """
        Get statistics for historical data.

        Args:
            instrument: Instrument identifier

        Returns:
            Dictionary with statistics

        Raises:
            KeyError: If instrument not found
        """
        if instrument not in self._data:
            raise KeyError(f"No data found for instrument: {instrument}")

        df = self._data[instrument]

        return {
            "instrument": instrument,
            "count": len(df),
            "start_time": df.index.min().isoformat() if not df.empty else None,
            "end_time": df.index.max().isoformat() if not df.empty else None,
            "price_stats": {
                "open": {
                    "mean": float(df['open'].mean()),
                    "std": float(df['open'].std()),
                    "min": float(df['open'].min()),
                    "max": float(df['open'].max())
                },
                "high": {
                    "mean": float(df['high'].mean()),
                    "std": float(df['high'].std()),
                    "min": float(df['high'].min()),
                    "max": float(df['high'].max())
                },
                "low": {
                    "mean": float(df['low'].mean()),
                    "std": float(df['low'].std()),
                    "min": float(df['low'].min()),
                    "max": float(df['low'].max())
                },
                "close": {
                    "mean": float(df['close'].mean()),
                    "std": float(df['close'].std()),
                    "min": float(df['close'].min()),
                    "max": float(df['close'].max())
                }
            },
            "volume_stats": {
                "total": int(df['volume'].sum()),
                "mean": float(df['volume'].mean()),
                "std": float(df['volume'].std()),
                "min": int(df['volume'].min()),
                "max": int(df['volume'].max())
            }
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Export all data as dictionary.

        Returns:
            Dictionary with all historical data
        """
        return {
            instrument: df.reset_index().to_dict(orient='records')
            for instrument, df in self._data.items()
        }
