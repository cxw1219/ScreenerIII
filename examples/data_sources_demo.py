"""
Alternative Data Sources Demo

This example demonstrates how to use the alternative data source system with
multiple providers, automatic failover, data aggregation, and health monitoring.

Features demonstrated:
1. Setting up multiple data sources
2. Using DataSourceManager for automatic failover
3. Aggregating data from multiple sources
4. Monitoring data source health
5. Handling rate limits and errors
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data import (
    # Data source implementations
    OANDADataSource,
    AlphaVantageDataSource,
    PolygonIODataSource,
    YahooFinanceDataSource,

    # Management classes
    DataSourceManager,
    DataAggregator,

    # Enums and types
    DataSourceType,
    DataSourceStatus,
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_data_sources():
    """
    Set up and configure all available data sources.

    Returns:
        DataSourceManager instance with configured sources
    """
    # Load environment variables
    load_dotenv()

    # Get configuration
    primary_source_name = os.getenv("DATA_SOURCE_PRIMARY", "oanda").lower()
    fallback_enabled = os.getenv("DATA_SOURCE_FALLBACK_ENABLED", "true").lower() == "true"

    # Map source name to enum
    source_type_map = {
        "oanda": DataSourceType.OANDA,
        "alphavantage": DataSourceType.ALPHA_VANTAGE,
        "polygon": DataSourceType.POLYGON,
        "yahoo": DataSourceType.YAHOO_FINANCE
    }

    primary_source = source_type_map.get(primary_source_name, DataSourceType.OANDA)

    # Initialize manager
    manager = DataSourceManager(primary_source=primary_source)
    manager.enable_fallback(fallback_enabled)

    # Initialize OANDA (if configured)
    oanda_token = os.getenv("OANDA_API_TOKEN")
    oanda_account = os.getenv("OANDA_ACCOUNT_ID")
    oanda_env = os.getenv("OANDA_ENVIRONMENT", "practice")

    if oanda_token and oanda_token != "your_api_token_here":
        try:
            oanda_source = OANDADataSource(
                api_token=oanda_token,
                account_id=oanda_account,
                environment=oanda_env
            )
            manager.register_source(DataSourceType.OANDA, oanda_source)
            logger.info("✓ OANDA source registered")
        except Exception as e:
            logger.error(f"✗ Failed to register OANDA: {e}")

    # Initialize Alpha Vantage (if configured)
    alphavantage_key = os.getenv("ALPHAVANTAGE_API_KEY")
    if alphavantage_key and alphavantage_key != "your_alphavantage_api_key_here":
        try:
            av_source = AlphaVantageDataSource(api_key=alphavantage_key)
            manager.register_source(DataSourceType.ALPHA_VANTAGE, av_source)
            logger.info("✓ Alpha Vantage source registered")
        except Exception as e:
            logger.error(f"✗ Failed to register Alpha Vantage: {e}")

    # Initialize Polygon.io (if configured)
    polygon_key = os.getenv("POLYGON_API_KEY")
    if polygon_key and polygon_key != "your_polygon_api_key_here":
        try:
            polygon_source = PolygonIODataSource(api_key=polygon_key)
            manager.register_source(DataSourceType.POLYGON, polygon_source)
            logger.info("✓ Polygon.io source registered")
        except Exception as e:
            logger.error(f"✗ Failed to register Polygon.io: {e}")

    # Initialize Yahoo Finance (always available, no API key required)
    try:
        yahoo_source = YahooFinanceDataSource()
        manager.register_source(DataSourceType.YAHOO_FINANCE, yahoo_source)
        logger.info("✓ Yahoo Finance source registered")
    except Exception as e:
        logger.error(f"✗ Failed to register Yahoo Finance: {e}")

    return manager


def demo_basic_usage(manager: DataSourceManager):
    """Demonstrate basic usage of data sources."""
    print("\n" + "="*70)
    print("DEMO 1: Basic Data Source Usage")
    print("="*70)

    # Test instruments for different sources
    instruments = [
        "EUR_USD",  # Forex pair (OANDA/Alpha Vantage)
        "AAPL",     # Stock (Alpha Vantage/Polygon/Yahoo)
        "GOOGL",    # Stock (Alpha Vantage/Polygon/Yahoo)
    ]

    for instrument in instruments:
        print(f"\n--- Getting price for {instrument} ---")

        # Get current price with automatic fallback
        price = manager.get_current_price(instrument, use_fallback=True)

        if price:
            print(f"Bid: {price.bid:.5f}")
            print(f"Ask: {price.ask:.5f}")
            print(f"Spread: {(price.ask - price.bid):.5f}")
            print(f"Timestamp: {price.timestamp}")
        else:
            print("Failed to get price from any source")


def demo_historical_data(manager: DataSourceManager):
    """Demonstrate fetching historical candle data."""
    print("\n" + "="*70)
    print("DEMO 2: Historical Data Retrieval")
    print("="*70)

    instrument = "EUR_USD"
    timeframe = "1h"
    count = 10

    print(f"\n--- Getting {count} {timeframe} candles for {instrument} ---")

    candles = manager.get_candles(
        instrument=instrument,
        timeframe=timeframe,
        count=count,
        use_fallback=True
    )

    if candles:
        print(f"\nRetrieved {len(candles)} candles:")
        print(f"{'Timestamp':<20} {'Open':<10} {'High':<10} {'Low':<10} {'Close':<10} {'Volume':<10}")
        print("-" * 70)

        for candle in candles[:5]:  # Show first 5
            print(
                f"{candle.timestamp.strftime('%Y-%m-%d %H:%M'):<20} "
                f"{candle.open:<10.5f} {candle.high:<10.5f} "
                f"{candle.low:<10.5f} {candle.close:<10.5f} "
                f"{candle.volume:<10}"
            )

        if len(candles) > 5:
            print(f"... and {len(candles) - 5} more candles")
    else:
        print("Failed to retrieve candles")


def demo_health_monitoring(manager: DataSourceManager):
    """Demonstrate health monitoring of data sources."""
    print("\n" + "="*70)
    print("DEMO 3: Data Source Health Monitoring")
    print("="*70)

    health_status = manager.get_all_health_status()

    print("\nData Source Health Status:")
    print(f"{'Source':<20} {'Status':<15} {'Success':<10} {'Errors':<10} {'Avg Response':<15}")
    print("-" * 70)

    for source_name, health in health_status.items():
        avg_time_ms = health.avg_response_time * 1000
        print(
            f"{source_name:<20} "
            f"{health.status.value:<15} "
            f"{health.success_count:<10} "
            f"{health.error_count:<10} "
            f"{avg_time_ms:<15.2f}ms"
        )

        if health.last_error:
            print(f"  Last error: {health.last_error}")

    # Show available sources
    available = manager.get_available_sources()
    print(f"\nCurrently available sources: {', '.join(s.value for s in available)}")


def demo_data_aggregation(manager: DataSourceManager):
    """Demonstrate data aggregation from multiple sources."""
    print("\n" + "="*70)
    print("DEMO 4: Data Aggregation and Cross-Validation")
    print("="*70)

    # Create aggregator
    aggregator = DataAggregator(
        manager=manager,
        max_divergence_percent=1.0  # 1% max divergence
    )

    # Test with a widely traded instrument
    instrument = "EUR_USD"

    print(f"\n--- Aggregating price data for {instrument} from multiple sources ---")

    result = aggregator.get_aggregated_price(instrument, min_sources=2)

    if result:
        price, metadata = result

        print(f"\nAggregated Price:")
        print(f"  Bid: {price.bid:.5f}")
        print(f"  Ask: {price.ask:.5f}")
        print(f"  Timestamp: {price.timestamp}")

        print(f"\nMetadata:")
        print(f"  Sources used: {metadata['sources_count']}")
        print(f"  Source names: {', '.join(metadata['sources_used'])}")
        print(f"  Max divergence: {metadata['max_divergence_percent']:.3f}%")
        print(f"  Has anomaly: {metadata['has_anomaly']}")

        if metadata['individual_prices']:
            print(f"\n  Individual prices:")
            for price_data in metadata['individual_prices']:
                print(f"    {price_data['source']}: bid={price_data['bid']:.5f}, ask={price_data['ask']:.5f}")
    else:
        print("Failed to aggregate data (insufficient sources)")


def demo_failover(manager: DataSourceManager):
    """Demonstrate automatic failover between sources."""
    print("\n" + "="*70)
    print("DEMO 5: Automatic Failover")
    print("="*70)

    instrument = "AAPL"

    print(f"\nPrimary source: {manager.primary_source.value}")
    print(f"Fallback enabled: {manager.fallback_enabled}")

    # Try getting price with failover
    print(f"\n--- Attempting to get price for {instrument} ---")
    print("(Will try primary source first, then fallback to alternatives)")

    price = manager.get_current_price(instrument, use_fallback=True)

    if price:
        print(f"\n✓ Successfully retrieved price:")
        print(f"  Bid: {price.bid:.2f}")
        print(f"  Ask: {price.ask:.2f}")
    else:
        print("\n✗ Failed to retrieve price from any source")

    # Show which sources could handle this request
    print("\n--- Checking source availability for this instrument ---")
    for source_type, source in manager.sources.items():
        available = source.is_available()
        status = "✓ Available" if available else "✗ Unavailable"
        print(f"  {source_type.value}: {status}")


def demo_rate_limiting(manager: DataSourceManager):
    """Demonstrate rate limiting behavior."""
    print("\n" + "="*70)
    print("DEMO 6: Rate Limiting")
    print("="*70)

    print("\nMaking multiple rapid requests to test rate limiting...")
    print("(Alpha Vantage free tier: 5 calls/minute)")

    instrument = "EUR_USD"

    for i in range(3):
        print(f"\nRequest {i+1}:")
        start_time = datetime.now()

        price = manager.get_current_price(instrument)

        elapsed = (datetime.now() - start_time).total_seconds()

        if price:
            print(f"  ✓ Success (took {elapsed:.2f}s)")
        else:
            print(f"  ✗ Failed or rate limited (took {elapsed:.2f}s)")


def demo_error_handling(manager: DataSourceManager):
    """Demonstrate error handling."""
    print("\n" + "="*70)
    print("DEMO 7: Error Handling")
    print("="*70)

    # Try to get price for invalid instrument
    invalid_instrument = "INVALID_SYMBOL_XYZ"

    print(f"\n--- Attempting to get price for invalid instrument: {invalid_instrument} ---")

    price = manager.get_current_price(invalid_instrument, use_fallback=True)

    if price:
        print(f"Price retrieved: {price.bid}")
    else:
        print("No price available (expected for invalid instrument)")

    # Check health status to see errors
    print("\n--- Checking for errors in health status ---")
    health_status = manager.get_all_health_status()

    for source_name, health in health_status.items():
        if health.error_count > 0:
            print(f"\n{source_name}:")
            print(f"  Errors: {health.error_count}")
            print(f"  Last error: {health.last_error}")


def main():
    """Run all demonstrations."""
    print("\n" + "="*70)
    print("ALTERNATIVE DATA SOURCES DEMONSTRATION")
    print("="*70)

    # Set up data sources
    print("\n--- Setting up data sources ---")
    manager = setup_data_sources()

    if not manager.sources:
        print("\n⚠ No data sources configured!")
        print("Please configure at least one data source in .env file")
        print("See .env.example for configuration options")
        return

    print(f"\n✓ Successfully configured {len(manager.sources)} data source(s)")

    # Run demonstrations
    try:
        demo_basic_usage(manager)
        demo_historical_data(manager)
        demo_health_monitoring(manager)
        demo_data_aggregation(manager)
        demo_failover(manager)
        demo_rate_limiting(manager)
        demo_error_handling(manager)

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed with error: {e}", exc_info=True)

    # Final health check
    print("\n" + "="*70)
    print("FINAL HEALTH CHECK")
    print("="*70)
    demo_health_monitoring(manager)

    print("\n" + "="*70)
    print("DEMO COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
