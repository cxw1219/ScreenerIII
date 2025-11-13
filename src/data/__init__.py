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

from .data_sources import (
    # Base Classes
    DataSource,
    DataSourceType,
    DataSourceStatus,
    DataSourceError,
    RateLimitExceeded,
    DataNotAvailable,

    # Data Structures
    InstrumentInfo,
    DataSourceHealth,

    # Data Source Implementations
    OANDADataSource,
    AlphaVantageDataSource,
    PolygonIODataSource,
    YahooFinanceDataSource,

    # Management Classes
    DataSourceManager,
    DataAggregator,
    DataSourceRateLimiter,
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

    # Data Sources - Base Classes
    'DataSource',
    'DataSourceType',
    'DataSourceStatus',
    'DataSourceError',
    'RateLimitExceeded',
    'DataNotAvailable',

    # Data Sources - Data Structures
    'InstrumentInfo',
    'DataSourceHealth',

    # Data Sources - Implementations
    'OANDADataSource',
    'AlphaVantageDataSource',
    'PolygonIODataSource',
    'YahooFinanceDataSource',

    # Data Sources - Management
    'DataSourceManager',
    'DataAggregator',
    'DataSourceRateLimiter',
]


__version__ = '1.0.0'
