# ScreenerIII Utils Package

Comprehensive utility modules for the ScreenerIII application, providing validation and helper functions with full type hints, error handling, and documentation.

## Modules

### 1. validators.py (516 lines)

Comprehensive validation functions for input data, API responses, and configuration.

#### Key Features:
- **Custom Exception**: `ValidationError` for consistent error handling
- **Market Symbol Validation**: Validates ticker symbols with configurable rules
- **Numeric Range Validation**: Ensures values are within specified bounds
- **API Response Validation**: Validates response structure and required fields
- **Configuration Validation**: Validates config dictionaries with type checking
- **Date/Time Validation**: Validates date strings with custom formats
- **Email & URL Validation**: Validates email addresses and URLs
- **File Path Validation**: Validates file paths with extension checking
- **Timeframe Validation**: Validates trading timeframes (1m, 5m, 1h, etc.)

#### Example Usage:
```python
from src.utils import validate_market_symbol, validate_numeric_range, ValidationError

try:
    validate_market_symbol('AAPL')
    validate_numeric_range(50, min_value=0, max_value=100, field_name='price')
except ValidationError as e:
    print(f"Validation error: {e}")
```

#### Available Validators:
1. `validate_market_symbol()` - Validate stock/crypto symbols
2. `validate_numeric_range()` - Validate numeric values with min/max bounds
3. `validate_percentage()` - Validate percentage values (0-100)
4. `validate_api_response()` - Validate API response structure
5. `validate_config()` - Validate configuration dictionaries
6. `validate_date_string()` - Validate date string formats
7. `validate_email()` - Validate email addresses
8. `validate_url()` - Validate URLs with scheme checking
9. `validate_list_not_empty()` - Validate list length requirements
10. `validate_file_path()` - Validate file paths and extensions
11. `validate_timeframe()` - Validate trading timeframes

---

### 2. helpers.py (836 lines)

Common helper functions for time/date operations, calculations, data transformations, and more.

#### Key Features:

##### Time & Date Utilities (10 functions):
- Get current timestamp and datetime
- Convert between timestamps and datetime objects
- Format and parse datetime strings
- Generate date ranges
- Calculate days between dates
- Add business days (excluding weekends)

##### Calculation Helpers (7 functions):
- Calculate percentage changes
- Calculate averages and moving averages
- Safe division with default values
- Clamp values to ranges
- Round to precision
- Parse decimal values safely

##### Data Transformation Utilities (8 functions):
- Flatten and unflatten nested dictionaries
- Deep merge dictionaries
- Filter dictionaries by keys
- Remove None values
- Chunk lists into smaller pieces
- Deduplicate lists with order preservation

##### String Utilities (3 functions):
- Truncate strings with ellipsis
- Sanitize filenames
- Generate hashes (MD5, SHA256, etc.)

##### JSON Utilities (3 functions):
- Safe JSON parsing and serialization
- Pretty-print JSON with formatting

##### Decorator Utilities (3 functions):
- `@retry` - Retry with exponential backoff
- `@timer` - Measure execution time
- `@memoize` - Cache function results

##### Utility Functions (3 functions):
- Get/set nested dictionary values with dot notation
- Ensure values are lists

#### Example Usage:
```python
from src.utils import (
    calculate_percentage_change,
    calculate_average,
    flatten_dict,
    retry,
    timer
)

# Calculate percentage change
change = calculate_percentage_change(100, 150)  # Returns: 50.0

# Calculate average
prices = [100, 105, 110, 108, 112]
avg = calculate_average(prices)  # Returns: 107.0

# Flatten nested dictionary
nested = {'user': {'name': 'John', 'age': 30}}
flat = flatten_dict(nested)  # Returns: {'user.name': 'John', 'user.age': 30}

# Use decorators
@retry(max_attempts=3, delay=1.0)
@timer
def fetch_data():
    # Function will retry on failure and log execution time
    pass
```

---

### 3. __init__.py (112 lines)

Package initialization file that exports all public functions for easy importing.

#### Example Usage:
```python
# Import specific functions
from src.utils import validate_market_symbol, calculate_percentage_change

# Import all
from src.utils import *

# Import with aliases
from src.utils import ValidationError as VE
```

---

## Installation

The utils package is located at `/home/user/ScreenerIII/src/utils/` and includes:

```
src/utils/
├── __init__.py       # Package initialization with exports
├── validators.py     # Validation functions
├── helpers.py        # Helper functions
├── examples.py       # Usage examples
└── README.md         # This file
```

## Requirements

The modules use only Python standard library:
- `re` - Regular expressions
- `typing` - Type hints
- `datetime` - Date/time operations
- `logging` - Logging functionality
- `json` - JSON operations
- `hashlib` - Hashing functions
- `functools` - Function tools
- `time` - Time operations
- `decimal` - Decimal arithmetic

No external dependencies required!

## Testing

Run the examples script to see the utilities in action:

```bash
cd /home/user/ScreenerIII/src/utils
python3 examples.py
```

## Features

### Comprehensive Error Handling
- Custom `ValidationError` exception
- Detailed error messages with context
- Safe parsing with default values
- Try-except blocks throughout

### Full Type Hints
- All functions have complete type annotations
- Union types for flexible inputs
- Optional parameters clearly marked
- Return types specified

### Extensive Documentation
- Detailed docstrings for all functions
- Parameter descriptions
- Return value documentation
- Usage examples in docstrings
- Raises sections for exceptions

### Logging Support
- Integrated logging throughout
- Debug messages for successful operations
- Warning messages for recoverable errors
- Error messages for failures

## Function Categories

### Validators (12 functions + 1 exception)
All validators return `True` on success or raise `ValidationError` on failure.

### Helpers (36+ functions)
Organized into categories:
- Time/Date: 10 functions
- Calculations: 7 functions
- Data Transformation: 8 functions
- String Operations: 3 functions
- JSON Operations: 3 functions
- Decorators: 3 functions
- Utilities: 3 functions

## Best Practices

1. **Always use validators** before processing external data
2. **Use type hints** when calling functions for better IDE support
3. **Handle ValidationError** exceptions appropriately
4. **Use decorators** (@retry, @timer) for production code
5. **Use safe_* functions** when dealing with untrusted input
6. **Log appropriately** using the logging module

## Example Integration

```python
import logging
from src.utils import (
    validate_market_symbol,
    validate_numeric_range,
    validate_api_response,
    calculate_percentage_change,
    retry,
    timer,
    ValidationError
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

@retry(max_attempts=3, delay=1.0)
@timer
def process_market_data(symbol, price):
    """Process market data with validation and error handling."""
    try:
        # Validate inputs
        validate_market_symbol(symbol)
        validate_numeric_range(price, min_value=0, field_name='price')

        # Process data
        # ... your logic here ...

        return True
    except ValidationError as e:
        logging.error(f"Validation failed: {e}")
        raise
```

## Version

Current version: 1.0.0

## License

Part of the ScreenerIII project.
