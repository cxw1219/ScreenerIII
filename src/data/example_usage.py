"""
Example usage of the data collection module.

This script demonstrates how to use the OANDA client, market data structures,
and storage manager to collect and store market data.
"""

import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

from oanda_client import OANDAClient, ConnectionStatus
from market_data import Price, Candle, HistoricalDataManager
from storage import StorageManager


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_basic_usage():
    """Demonstrate basic usage of the data collection module."""
    # Load environment variables
    load_dotenv()

    # Initialize OANDA client
    api_token = os.getenv('OANDA_API_TOKEN', 'your_token_here')
    account_id = os.getenv('OANDA_ACCOUNT_ID', 'your_account_id_here')

    client = OANDAClient(
        api_token=api_token,
        account_id=account_id,
        environment='practice',
        max_retries=3,
        rate_limit_requests=120
    )

    # Test connection
    logger.info("Testing OANDA connection...")
    if client.test_connection():
        logger.info("Connection successful!")
    else:
        logger.error("Connection failed!")
        return

    # Get connection info
    conn_info = client.get_connection_info()
    logger.info(f"Connection status: {conn_info['status']}")

    # Fetch current prices
    logger.info("Fetching current prices...")
    instruments = ["EUR_USD", "GBP_USD", "USD_JPY"]
    response = client.get_current_prices(instruments)

    # Parse prices into Price objects
    prices = []
    for price_data in response.get('prices', []):
        try:
            price = Price.from_oanda_response(price_data)
            prices.append(price)
            logger.info(
                f"{price.instrument}: "
                f"Bid={price.bid:.5f}, Ask={price.ask:.5f}, "
                f"Spread={price.spread:.5f}"
            )
        except Exception as e:
            logger.error(f"Error parsing price: {e}")

    # Initialize storage manager
    storage = StorageManager(db_path='market_data.db')

    # Save prices to database
    logger.info("Saving prices to database...")
    success_count, fail_count = storage.save_prices(prices)
    logger.info(f"Saved {success_count} prices, {fail_count} failed")

    # Fetch historical candles
    logger.info("Fetching historical candles...")
    candles_response = client.get_candles(
        instrument="EUR_USD",
        granularity="H1",
        count=100
    )

    # Parse candles
    candles = []
    for candle_data in candles_response.get('candles', []):
        try:
            candle = Candle.from_oanda_response(
                instrument="EUR_USD",
                data=candle_data,
                price_type="mid",
                granularity="H1"
            )
            candles.append(candle)
        except Exception as e:
            logger.error(f"Error parsing candle: {e}")

    logger.info(f"Fetched {len(candles)} candles")

    # Save candles to database
    logger.info("Saving candles to database...")
    success_count, fail_count = storage.save_candles(candles)
    logger.info(f"Saved {success_count} candles, {fail_count} failed")

    # Use HistoricalDataManager
    hist_manager = HistoricalDataManager()
    hist_manager.add_candles("EUR_USD", candles)

    # Get statistics
    stats = hist_manager.get_statistics("EUR_USD")
    logger.info(f"Historical data statistics: {stats['count']} candles")

    # Query historical data from database
    logger.info("Querying historical data from database...")
    df = storage.get_candles(
        instrument="EUR_USD",
        granularity="H1",
        limit=10
    )
    logger.info(f"Retrieved {len(df)} candles from database")

    # Get database statistics
    db_stats = storage.get_database_stats()
    logger.info(f"Database statistics:")
    for table, stats in db_stats.get('tables', {}).items():
        logger.info(f"  {table}: {stats['row_count']} rows")

    # Close storage
    storage.close()
    logger.info("Example completed successfully!")


def example_error_handling():
    """Demonstrate error handling capabilities."""
    logger.info("Demonstrating error handling...")

    # Test with invalid credentials
    try:
        client = OANDAClient(
            api_token='invalid_token',
            account_id='invalid_account',
            environment='practice'
        )

        # This should fail gracefully
        client.get_current_prices('EUR_USD')

    except Exception as e:
        logger.info(f"Handled error gracefully: {type(e).__name__}")


def example_rate_limiting():
    """Demonstrate rate limiting."""
    from oanda_client import RateLimiter

    logger.info("Demonstrating rate limiting...")

    # Create a rate limiter (5 requests per 10 seconds for demo)
    limiter = RateLimiter(max_requests=5, time_window=10)

    # Make rapid requests
    for i in range(10):
        limiter.wait_if_needed()
        logger.info(f"Request {i+1} allowed")

    logger.info("Rate limiting demonstration complete")


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Data Collection Module - Usage Examples")
    logger.info("=" * 60)

    try:
        # Run basic usage example
        example_basic_usage()

        # Demonstrate error handling
        example_error_handling()

        # Demonstrate rate limiting
        example_rate_limiting()

    except Exception as e:
        logger.error(f"Example failed with error: {e}", exc_info=True)
