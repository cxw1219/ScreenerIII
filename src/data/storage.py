"""
Database Storage Operations

This module provides database storage operations for market data using SQLite,
including data persistence, querying, and maintenance operations.
"""

import sqlite3
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json

import pandas as pd

from .market_data import Price, Candle, SpreadData, VolumeData


logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Base exception for database errors."""
    pass


class ConnectionError(DatabaseError):
    """Raised when database connection fails."""
    pass


class StorageManager:
    """
    Database storage manager for market data.

    Handles all database operations including creation, insertion,
    querying, and maintenance of market data in SQLite database.
    """

    def __init__(self, db_path: str = "market_data.db"):
        """
        Initialize storage manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._connection: Optional[sqlite3.Connection] = None
        self._ensure_database()
        logger.info(f"Storage manager initialized with database: {db_path}")

    def _ensure_database(self) -> None:
        """
        Ensure database exists and create tables if needed.

        Raises:
            ConnectionError: If database connection fails
        """
        try:
            conn = self._get_connection()
            self._create_tables(conn)
            conn.commit()
            logger.debug("Database tables verified/created")
        except Exception as e:
            raise ConnectionError(f"Failed to initialize database: {e}")

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get or create database connection.

        Returns:
            SQLite connection object

        Raises:
            ConnectionError: If connection fails
        """
        try:
            if self._connection is None:
                self._connection = sqlite3.connect(
                    self.db_path,
                    check_same_thread=False,
                    timeout=30.0
                )
                self._connection.row_factory = sqlite3.Row
            return self._connection
        except Exception as e:
            raise ConnectionError(f"Failed to connect to database: {e}")

    def _create_tables(self, conn: sqlite3.Connection) -> None:
        """
        Create database tables if they don't exist.

        Args:
            conn: Database connection
        """
        cursor = conn.cursor()

        # Prices table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instrument TEXT NOT NULL,
                bid REAL NOT NULL,
                ask REAL NOT NULL,
                spread REAL NOT NULL,
                mid REAL NOT NULL,
                timestamp TEXT NOT NULL,
                tradeable INTEGER NOT NULL DEFAULT 1,
                liquidity TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(instrument, timestamp)
            )
        """)

        # Candles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instrument TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume INTEGER NOT NULL,
                complete INTEGER NOT NULL DEFAULT 1,
                granularity TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(instrument, timestamp, granularity)
            )
        """)

        # Spreads table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS spreads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instrument TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                spread REAL NOT NULL,
                spread_pips REAL,
                spread_percentage REAL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(instrument, timestamp)
            )
        """)

        # Volumes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS volumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instrument TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                volume INTEGER NOT NULL,
                volume_ma REAL,
                relative_volume REAL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(instrument, timestamp)
            )
        """)

        # Create indexes for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_prices_instrument_timestamp
            ON prices(instrument, timestamp DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_candles_instrument_timestamp
            ON candles(instrument, timestamp DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_spreads_instrument_timestamp
            ON spreads(instrument, timestamp DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_volumes_instrument_timestamp
            ON volumes(instrument, timestamp DESC)
        """)

        logger.debug("Database tables and indexes created/verified")

    def save_price(self, price: Price) -> bool:
        """
        Save a price record to database.

        Args:
            price: Price object to save

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO prices
                (instrument, bid, ask, spread, mid, timestamp, tradeable, liquidity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                price.instrument,
                price.bid,
                price.ask,
                price.spread,
                price.mid,
                price.timestamp.isoformat(),
                1 if price.tradeable else 0,
                json.dumps(price.liquidity) if price.liquidity else None
            ))

            conn.commit()
            logger.debug(f"Saved price for {price.instrument}")
            return True

        except Exception as e:
            logger.error(f"Failed to save price: {e}")
            return False

    def save_prices(self, prices: List[Price]) -> Tuple[int, int]:
        """
        Save multiple price records to database.

        Args:
            prices: List of Price objects to save

        Returns:
            Tuple of (successful_count, failed_count)
        """
        successful = 0
        failed = 0

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            for price in prices:
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO prices
                        (instrument, bid, ask, spread, mid, timestamp, tradeable, liquidity)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        price.instrument,
                        price.bid,
                        price.ask,
                        price.spread,
                        price.mid,
                        price.timestamp.isoformat(),
                        1 if price.tradeable else 0,
                        json.dumps(price.liquidity) if price.liquidity else None
                    ))
                    successful += 1
                except Exception as e:
                    logger.error(f"Failed to save price for {price.instrument}: {e}")
                    failed += 1

            conn.commit()
            logger.info(f"Saved {successful} prices, {failed} failed")
            return successful, failed

        except Exception as e:
            logger.error(f"Failed to save prices: {e}")
            return successful, failed

    def save_candle(self, candle: Candle) -> bool:
        """
        Save a candle record to database.

        Args:
            candle: Candle object to save

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO candles
                (instrument, timestamp, open, high, low, close, volume, complete, granularity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                candle.instrument,
                candle.timestamp.isoformat(),
                candle.open,
                candle.high,
                candle.low,
                candle.close,
                candle.volume,
                1 if candle.complete else 0,
                candle.granularity
            ))

            conn.commit()
            logger.debug(f"Saved candle for {candle.instrument}")
            return True

        except Exception as e:
            logger.error(f"Failed to save candle: {e}")
            return False

    def save_candles(self, candles: List[Candle]) -> Tuple[int, int]:
        """
        Save multiple candle records to database.

        Args:
            candles: List of Candle objects to save

        Returns:
            Tuple of (successful_count, failed_count)
        """
        successful = 0
        failed = 0

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            for candle in candles:
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO candles
                        (instrument, timestamp, open, high, low, close, volume, complete, granularity)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        candle.instrument,
                        candle.timestamp.isoformat(),
                        candle.open,
                        candle.high,
                        candle.low,
                        candle.close,
                        candle.volume,
                        1 if candle.complete else 0,
                        candle.granularity
                    ))
                    successful += 1
                except Exception as e:
                    logger.error(f"Failed to save candle for {candle.instrument}: {e}")
                    failed += 1

            conn.commit()
            logger.info(f"Saved {successful} candles, {failed} failed")
            return successful, failed

        except Exception as e:
            logger.error(f"Failed to save candles: {e}")
            return successful, failed

    def get_latest_price(self, instrument: str) -> Optional[Dict[str, Any]]:
        """
        Get latest price for an instrument.

        Args:
            instrument: Instrument identifier

        Returns:
            Dictionary with price data or None
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM prices
                WHERE instrument = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (instrument,))

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

        except Exception as e:
            logger.error(f"Failed to get latest price: {e}")
            return None

    def get_prices(
        self,
        instrument: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get historical prices for an instrument.

        Args:
            instrument: Instrument identifier
            start_time: Start time filter
            end_time: End time filter
            limit: Maximum number of records to return

        Returns:
            DataFrame with price data
        """
        try:
            conn = self._get_connection()

            query = "SELECT * FROM prices WHERE instrument = ?"
            params = [instrument]

            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())

            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())

            query += " ORDER BY timestamp DESC"

            if limit:
                query += f" LIMIT {limit}"

            df = pd.read_sql_query(query, conn, params=params)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            logger.debug(f"Retrieved {len(df)} prices for {instrument}")
            return df

        except Exception as e:
            logger.error(f"Failed to get prices: {e}")
            return pd.DataFrame()

    def get_candles(
        self,
        instrument: str,
        granularity: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get historical candles for an instrument.

        Args:
            instrument: Instrument identifier
            granularity: Candle granularity filter
            start_time: Start time filter
            end_time: End time filter
            limit: Maximum number of records to return

        Returns:
            DataFrame with candle data
        """
        try:
            conn = self._get_connection()

            query = "SELECT * FROM candles WHERE instrument = ?"
            params = [instrument]

            if granularity:
                query += " AND granularity = ?"
                params.append(granularity)

            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())

            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())

            query += " ORDER BY timestamp DESC"

            if limit:
                query += f" LIMIT {limit}"

            df = pd.read_sql_query(query, conn, params=params)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            logger.debug(f"Retrieved {len(df)} candles for {instrument}")
            return df

        except Exception as e:
            logger.error(f"Failed to get candles: {e}")
            return pd.DataFrame()

    def delete_old_data(
        self,
        table: str,
        days_to_keep: int = 30
    ) -> int:
        """
        Delete old data from specified table.

        Args:
            table: Table name (prices, candles, spreads, volumes)
            days_to_keep: Number of days of data to keep

        Returns:
            Number of rows deleted

        Raises:
            DatabaseError: If table name is invalid
        """
        valid_tables = ['prices', 'candles', 'spreads', 'volumes']
        if table not in valid_tables:
            raise DatabaseError(f"Invalid table name: {table}")

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cutoff_date = datetime.now() - timedelta(days=days_to_keep)

            cursor.execute(f"""
                DELETE FROM {table}
                WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))

            deleted_count = cursor.rowcount
            conn.commit()

            logger.info(
                f"Deleted {deleted_count} old records from {table} "
                f"(older than {days_to_keep} days)"
            )
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete old data: {e}")
            return 0

    def vacuum_database(self) -> bool:
        """
        Vacuum database to reclaim space and optimize performance.

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("VACUUM")
            logger.info("Database vacuumed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to vacuum database: {e}")
            return False

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dictionary with database statistics
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            stats = {
                "database_path": str(self.db_path),
                "database_size_bytes": self.db_path.stat().st_size if self.db_path.exists() else 0,
                "tables": {}
            }

            for table in ['prices', 'candles', 'spreads', 'volumes']:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]

                cursor.execute(f"""
                    SELECT MIN(timestamp), MAX(timestamp)
                    FROM {table}
                """)
                min_ts, max_ts = cursor.fetchone()

                cursor.execute(f"""
                    SELECT COUNT(DISTINCT instrument)
                    FROM {table}
                """)
                unique_instruments = cursor.fetchone()[0]

                stats["tables"][table] = {
                    "row_count": count,
                    "oldest_record": min_ts,
                    "newest_record": max_ts,
                    "unique_instruments": unique_instruments
                }

            return stats

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}

    def get_instruments(self, table: str = "prices") -> List[str]:
        """
        Get list of unique instruments in database.

        Args:
            table: Table to query (default: prices)

        Returns:
            List of instrument identifiers
        """
        valid_tables = ['prices', 'candles', 'spreads', 'volumes']
        if table not in valid_tables:
            raise DatabaseError(f"Invalid table name: {table}")

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(f"""
                SELECT DISTINCT instrument
                FROM {table}
                ORDER BY instrument
            """)

            instruments = [row[0] for row in cursor.fetchall()]
            return instruments

        except Exception as e:
            logger.error(f"Failed to get instruments: {e}")
            return []

    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            try:
                self._connection.close()
                self._connection = None
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def __del__(self):
        """Destructor to ensure connection is closed."""
        self.close()
