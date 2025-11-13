"""
Data Collection Module

This module provides comprehensive data collection functionality for market data,
including OANDA API integration, data structures, validation, and storage.
"""

from .oanda_client import (
    OANDAClient,
    ConnectionStatus,
    OANDAClientError,
    RateLimitError,
    ConnectionError as OANDAConnectionError,
    RateLimiter
)

from .market_data import (
    Price,
    Candle,
    SpreadData,
    VolumeData,
    PriceType,
    CandleGranularity,
    ValidationError,
    HistoricalDataManager
)

from .storage import (
    StorageManager,
    DatabaseError,
    ConnectionError as StorageConnectionError
)


__all__ = [
    # OANDA Client
    'OANDAClient',
    'ConnectionStatus',
    'OANDAClientError',
    'RateLimitError',
    'OANDAConnectionError',
    'RateLimiter',

    # Market Data
    'Price',
    'Candle',
    'SpreadData',
    'VolumeData',
    'PriceType',
    'CandleGranularity',
    'ValidationError',
    'HistoricalDataManager',

    # Storage
    'StorageManager',
    'DatabaseError',
    'StorageConnectionError',
]


__version__ = '1.0.0'
