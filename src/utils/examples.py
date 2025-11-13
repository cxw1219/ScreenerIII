"""
Example usage of utility modules.

This module demonstrates how to use the validators and helpers.
"""

from validators import (
    validate_market_symbol,
    validate_numeric_range,
    validate_api_response,
    ValidationError
)
from helpers import (
    calculate_percentage_change,
    calculate_average,
    get_current_timestamp,
    format_datetime,
    get_current_datetime,
    flatten_dict,
    chunk_list,
    retry,
    timer
)


def example_validators():
    """Demonstrate validator usage."""
    print("=== Validator Examples ===\n")

    # Example 1: Validate market symbols
    try:
        validate_market_symbol("AAPL")
        print("✓ 'AAPL' is a valid symbol")
    except ValidationError as e:
        print(f"✗ Error: {e}")

    try:
        validate_market_symbol("BTC-USD")
        print("✓ 'BTC-USD' is a valid symbol")
    except ValidationError as e:
        print(f"✗ Error: {e}")

    # Example 2: Validate numeric ranges
    try:
        validate_numeric_range(50, min_value=0, max_value=100, field_name="price")
        print("✓ Price 50 is within valid range [0-100]")
    except ValidationError as e:
        print(f"✗ Error: {e}")

    # Example 3: Validate API response
    try:
        api_response = {
            'symbol': 'AAPL',
            'price': 150.25,
            'volume': 1000000
        }
        validate_api_response(
            api_response,
            required_fields=['symbol', 'price'],
            optional_fields=['volume']
        )
        print("✓ API response is valid")
    except ValidationError as e:
        print(f"✗ Error: {e}")

    print()


def example_helpers():
    """Demonstrate helper usage."""
    print("=== Helper Examples ===\n")

    # Example 1: Calculate percentage change
    old_price = 100
    new_price = 150
    change = calculate_percentage_change(old_price, new_price)
    print(f"Price change from {old_price} to {new_price}: {change}%")

    # Example 2: Calculate average
    prices = [100, 105, 110, 108, 112]
    avg = calculate_average(prices)
    print(f"Average price: {avg}")

    # Example 3: Time utilities
    timestamp = get_current_timestamp()
    dt = get_current_datetime()
    formatted = format_datetime(dt)
    print(f"Current timestamp: {timestamp}")
    print(f"Current datetime: {formatted}")

    # Example 4: Flatten nested dictionary
    nested = {
        'user': {
            'name': 'John',
            'profile': {
                'age': 30,
                'city': 'New York'
            }
        }
    }
    flattened = flatten_dict(nested)
    print(f"Flattened dict: {flattened}")

    # Example 5: Chunk list
    symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
    chunks = chunk_list(symbols, 2)
    print(f"Chunked symbols: {chunks}")

    print()


@timer
@retry(max_attempts=3, delay=0.5)
def example_decorators():
    """Demonstrate decorator usage."""
    print("=== Decorator Examples ===\n")
    print("This function uses @timer and @retry decorators")
    print("✓ Function executed successfully")
    return True


if __name__ == '__main__':
    print("\n" + "="*50)
    print("ScreenerIII Utility Modules - Examples")
    print("="*50 + "\n")

    example_validators()
    example_helpers()
    example_decorators()

    print("\n" + "="*50)
    print("All examples completed!")
    print("="*50 + "\n")
