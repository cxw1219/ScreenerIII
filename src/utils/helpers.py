"""
Helper utilities for ScreenerIII application.

This module provides common helper functions for time/date operations,
calculations, data transformations, and other utility operations.
"""

import logging
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import json
import hashlib
from functools import wraps
import time

logger = logging.getLogger(__name__)


# ============================================================================
# Time and Date Utilities
# ============================================================================

def get_current_timestamp() -> int:
    """
    Get current Unix timestamp in seconds.

    Returns:
        int: Current timestamp

    Examples:
        >>> ts = get_current_timestamp()
        >>> isinstance(ts, int)
        True
    """
    return int(time.time())


def get_current_datetime(tz: Optional[timezone] = None) -> datetime:
    """
    Get current datetime object.

    Args:
        tz: Timezone (default: UTC)

    Returns:
        datetime: Current datetime
    """
    if tz is None:
        tz = timezone.utc
    return datetime.now(tz)


def timestamp_to_datetime(
    timestamp: Union[int, float],
    tz: Optional[timezone] = None
) -> datetime:
    """
    Convert Unix timestamp to datetime object.

    Args:
        timestamp: Unix timestamp in seconds
        tz: Timezone (default: UTC)

    Returns:
        datetime: Converted datetime

    Examples:
        >>> dt = timestamp_to_datetime(1609459200)
        >>> dt.year
        2021
    """
    if tz is None:
        tz = timezone.utc
    return datetime.fromtimestamp(timestamp, tz=tz)


def datetime_to_timestamp(dt: datetime) -> int:
    """
    Convert datetime object to Unix timestamp.

    Args:
        dt: Datetime object

    Returns:
        int: Unix timestamp in seconds
    """
    return int(dt.timestamp())


def format_datetime(
    dt: datetime,
    format_string: str = "%Y-%m-%d %H:%M:%S"
) -> str:
    """
    Format datetime object as string.

    Args:
        dt: Datetime object
        format_string: Output format string

    Returns:
        str: Formatted datetime string
    """
    return dt.strftime(format_string)


def parse_datetime(
    date_string: str,
    format_string: str = "%Y-%m-%d %H:%M:%S"
) -> datetime:
    """
    Parse datetime string to datetime object.

    Args:
        date_string: Date string to parse
        format_string: Expected format string

    Returns:
        datetime: Parsed datetime object

    Raises:
        ValueError: If parsing fails
    """
    try:
        return datetime.strptime(date_string, format_string)
    except ValueError as e:
        logger.error(f"Failed to parse datetime '{date_string}': {e}")
        raise


def get_date_range(
    start_date: Union[str, datetime],
    end_date: Union[str, datetime],
    date_format: str = "%Y-%m-%d"
) -> List[datetime]:
    """
    Generate list of dates between start and end dates (inclusive).

    Args:
        start_date: Start date (string or datetime)
        end_date: End date (string or datetime)
        date_format: Format string if dates are strings

    Returns:
        List[datetime]: List of datetime objects
    """
    if isinstance(start_date, str):
        start_date = parse_datetime(start_date, date_format)
    if isinstance(end_date, str):
        end_date = parse_datetime(end_date, date_format)

    date_list = []
    current_date = start_date

    while current_date <= end_date:
        date_list.append(current_date)
        current_date += timedelta(days=1)

    return date_list


def days_between(date1: datetime, date2: datetime) -> int:
    """
    Calculate number of days between two dates.

    Args:
        date1: First date
        date2: Second date

    Returns:
        int: Number of days (absolute value)
    """
    return abs((date2 - date1).days)


def add_business_days(start_date: datetime, days: int) -> datetime:
    """
    Add business days to a date (excluding weekends).

    Args:
        start_date: Starting date
        days: Number of business days to add

    Returns:
        datetime: Resulting date
    """
    current_date = start_date
    days_added = 0

    while days_added < days:
        current_date += timedelta(days=1)
        # Skip weekends (5=Saturday, 6=Sunday)
        if current_date.weekday() < 5:
            days_added += 1

    return current_date


# ============================================================================
# Calculation Helpers
# ============================================================================

def calculate_percentage_change(
    old_value: Union[int, float, Decimal],
    new_value: Union[int, float, Decimal],
    precision: int = 2
) -> float:
    """
    Calculate percentage change between two values.

    Args:
        old_value: Original value
        new_value: New value
        precision: Decimal places to round to

    Returns:
        float: Percentage change

    Examples:
        >>> calculate_percentage_change(100, 150)
        50.0
        >>> calculate_percentage_change(100, 75)
        -25.0
    """
    if old_value == 0:
        return 0.0 if new_value == 0 else float('inf')

    change = ((float(new_value) - float(old_value)) / float(old_value)) * 100
    return round(change, precision)


def calculate_average(
    values: List[Union[int, float]],
    precision: int = 2
) -> float:
    """
    Calculate average of a list of values.

    Args:
        values: List of numeric values
        precision: Decimal places to round to

    Returns:
        float: Average value

    Raises:
        ValueError: If list is empty
    """
    if not values:
        raise ValueError("Cannot calculate average of empty list")

    return round(sum(values) / len(values), precision)


def calculate_moving_average(
    values: List[Union[int, float]],
    window: int,
    precision: int = 2
) -> List[float]:
    """
    Calculate moving average of a series.

    Args:
        values: List of numeric values
        window: Window size for moving average
        precision: Decimal places to round to

    Returns:
        List[float]: List of moving averages
    """
    if len(values) < window:
        return []

    moving_averages = []
    for i in range(len(values) - window + 1):
        window_values = values[i:i + window]
        avg = round(sum(window_values) / window, precision)
        moving_averages.append(avg)

    return moving_averages


def safe_divide(
    numerator: Union[int, float],
    denominator: Union[int, float],
    default: Union[int, float] = 0.0
) -> float:
    """
    Safely divide two numbers, returning default on division by zero.

    Args:
        numerator: Numerator value
        denominator: Denominator value
        default: Default value to return if division by zero

    Returns:
        float: Result of division or default
    """
    try:
        if denominator == 0:
            return float(default)
        return float(numerator) / float(denominator)
    except (TypeError, ZeroDivisionError) as e:
        logger.warning(f"Division error: {e}. Returning default: {default}")
        return float(default)


def clamp(
    value: Union[int, float],
    min_value: Union[int, float],
    max_value: Union[int, float]
) -> Union[int, float]:
    """
    Clamp a value between min and max.

    Args:
        value: Value to clamp
        min_value: Minimum allowed value
        max_value: Maximum allowed value

    Returns:
        Clamped value
    """
    return max(min_value, min(value, max_value))


def round_to_precision(
    value: Union[int, float],
    precision: int = 2
) -> float:
    """
    Round a number to specified decimal places.

    Args:
        value: Value to round
        precision: Number of decimal places

    Returns:
        float: Rounded value
    """
    return round(float(value), precision)


def parse_decimal(
    value: Any,
    default: Optional[Decimal] = None
) -> Optional[Decimal]:
    """
    Safely parse value to Decimal.

    Args:
        value: Value to parse
        default: Default value if parsing fails

    Returns:
        Decimal or default value
    """
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as e:
        logger.warning(f"Failed to parse decimal '{value}': {e}")
        return default


# ============================================================================
# Data Transformation Utilities
# ============================================================================

def flatten_dict(
    d: Dict[str, Any],
    parent_key: str = '',
    separator: str = '.'
) -> Dict[str, Any]:
    """
    Flatten nested dictionary.

    Args:
        d: Dictionary to flatten
        parent_key: Parent key for nested items
        separator: Separator between nested keys

    Returns:
        Dict[str, Any]: Flattened dictionary

    Examples:
        >>> flatten_dict({'a': {'b': 1, 'c': 2}})
        {'a.b': 1, 'a.c': 2}
    """
    items = []
    for key, value in d.items():
        new_key = f"{parent_key}{separator}{key}" if parent_key else key

        if isinstance(value, dict):
            items.extend(flatten_dict(value, new_key, separator).items())
        else:
            items.append((new_key, value))

    return dict(items)


def unflatten_dict(
    d: Dict[str, Any],
    separator: str = '.'
) -> Dict[str, Any]:
    """
    Unflatten dictionary with dotted keys.

    Args:
        d: Flattened dictionary
        separator: Separator used in keys

    Returns:
        Dict[str, Any]: Nested dictionary
    """
    result = {}
    for key, value in d.items():
        parts = key.split(separator)
        current = result

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value

    return result


def deep_merge(
    dict1: Dict[str, Any],
    dict2: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Deep merge two dictionaries.

    Args:
        dict1: First dictionary
        dict2: Second dictionary (takes precedence)

    Returns:
        Dict[str, Any]: Merged dictionary
    """
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def filter_dict(
    d: Dict[str, Any],
    keys: List[str],
    exclude: bool = False
) -> Dict[str, Any]:
    """
    Filter dictionary by keys.

    Args:
        d: Dictionary to filter
        keys: List of keys to include or exclude
        exclude: If True, exclude keys instead of including

    Returns:
        Dict[str, Any]: Filtered dictionary
    """
    if exclude:
        return {k: v for k, v in d.items() if k not in keys}
    else:
        return {k: v for k, v in d.items() if k in keys}


def remove_none_values(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove keys with None values from dictionary.

    Args:
        d: Dictionary to clean

    Returns:
        Dict[str, Any]: Dictionary without None values
    """
    return {k: v for k, v in d.items() if v is not None}


def chunk_list(
    items: List[Any],
    chunk_size: int
) -> List[List[Any]]:
    """
    Split list into chunks of specified size.

    Args:
        items: List to split
        chunk_size: Size of each chunk

    Returns:
        List of chunks

    Examples:
        >>> chunk_list([1, 2, 3, 4, 5], 2)
        [[1, 2], [3, 4], [5]]
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def deduplicate_list(
    items: List[Any],
    preserve_order: bool = True
) -> List[Any]:
    """
    Remove duplicates from list.

    Args:
        items: List with potential duplicates
        preserve_order: Whether to preserve original order

    Returns:
        List without duplicates
    """
    if preserve_order:
        seen = set()
        result = []
        for item in items:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result
    else:
        return list(set(items))


# ============================================================================
# String Utilities
# ============================================================================

def truncate_string(
    text: str,
    max_length: int,
    suffix: str = "..."
) -> str:
    """
    Truncate string to maximum length.

    Args:
        text: String to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        str: Truncated string
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters.

    Args:
        filename: Original filename

    Returns:
        str: Sanitized filename
    """
    import re
    # Remove invalid filename characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace spaces with underscores
    sanitized = sanitized.replace(' ', '_')
    return sanitized


def generate_hash(
    data: Union[str, bytes],
    algorithm: str = 'sha256'
) -> str:
    """
    Generate hash of data.

    Args:
        data: Data to hash
        algorithm: Hash algorithm (md5, sha1, sha256, etc.)

    Returns:
        str: Hex digest of hash
    """
    if isinstance(data, str):
        data = data.encode('utf-8')

    hash_obj = hashlib.new(algorithm)
    hash_obj.update(data)
    return hash_obj.hexdigest()


# ============================================================================
# JSON Utilities
# ============================================================================

def safe_json_loads(
    json_string: str,
    default: Any = None
) -> Any:
    """
    Safely parse JSON string.

    Args:
        json_string: JSON string to parse
        default: Default value if parsing fails

    Returns:
        Parsed JSON or default value
    """
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Failed to parse JSON: {e}")
        return default


def safe_json_dumps(
    obj: Any,
    default: str = "{}"
) -> str:
    """
    Safely serialize object to JSON string.

    Args:
        obj: Object to serialize
        default: Default value if serialization fails

    Returns:
        JSON string or default value
    """
    try:
        return json.dumps(obj)
    except (TypeError, ValueError) as e:
        logger.warning(f"Failed to serialize JSON: {e}")
        return default


def pretty_json(obj: Any, indent: int = 2) -> str:
    """
    Format object as pretty-printed JSON.

    Args:
        obj: Object to format
        indent: Indentation level

    Returns:
        str: Pretty-printed JSON string
    """
    return json.dumps(obj, indent=indent, sort_keys=True)


# ============================================================================
# Decorator Utilities
# ============================================================================

def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries (seconds)
        backoff: Backoff multiplier
        exceptions: Tuple of exceptions to catch

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        logger.error(f"Failed after {max_attempts} attempts: {e}")
                        raise

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                        f"Retrying in {current_delay}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff

        return wrapper
    return decorator


def timer(func: Callable) -> Callable:
    """
    Decorator to measure function execution time.

    Args:
        func: Function to measure

    Returns:
        Decorated function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()

        execution_time = end_time - start_time
        logger.debug(f"{func.__name__} executed in {execution_time:.4f}s")

        return result

    return wrapper


def memoize(func: Callable) -> Callable:
    """
    Simple memoization decorator.

    Args:
        func: Function to memoize

    Returns:
        Decorated function
    """
    cache = {}

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Create cache key from args and kwargs
        key = str(args) + str(sorted(kwargs.items()))

        if key not in cache:
            cache[key] = func(*args, **kwargs)

        return cache[key]

    return wrapper


# ============================================================================
# Utility Functions
# ============================================================================

def get_nested_value(
    d: Dict[str, Any],
    key_path: str,
    separator: str = '.',
    default: Any = None
) -> Any:
    """
    Get value from nested dictionary using dot notation.

    Args:
        d: Dictionary to query
        key_path: Dot-separated path to value (e.g., 'user.profile.name')
        separator: Separator character
        default: Default value if key not found

    Returns:
        Value at key path or default

    Examples:
        >>> get_nested_value({'user': {'name': 'John'}}, 'user.name')
        'John'
    """
    keys = key_path.split(separator)
    value = d

    try:
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError):
        return default


def set_nested_value(
    d: Dict[str, Any],
    key_path: str,
    value: Any,
    separator: str = '.'
) -> None:
    """
    Set value in nested dictionary using dot notation.

    Args:
        d: Dictionary to modify
        key_path: Dot-separated path to value
        value: Value to set
        separator: Separator character
    """
    keys = key_path.split(separator)
    current = d

    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]

    current[keys[-1]] = value


def ensure_list(value: Any) -> List[Any]:
    """
    Ensure value is a list.

    Args:
        value: Value to convert

    Returns:
        List containing value(s)
    """
    if value is None:
        return []
    elif isinstance(value, list):
        return value
    else:
        return [value]
