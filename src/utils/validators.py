"""
Validation utilities for ScreenerIII application.

This module provides comprehensive validation functions for input data,
market symbols, numeric ranges, API responses, and configuration settings.
"""

import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def validate_market_symbol(
    symbol: str,
    min_length: int = 1,
    max_length: int = 10,
    allowed_exchanges: Optional[List[str]] = None
) -> bool:
    """
    Validate a market symbol (ticker).

    Args:
        symbol: The stock/crypto symbol to validate
        min_length: Minimum allowed symbol length
        max_length: Maximum allowed symbol length
        allowed_exchanges: Optional list of allowed exchange prefixes (e.g., ['NYSE', 'NASDAQ'])

    Returns:
        bool: True if valid

    Raises:
        ValidationError: If validation fails

    Examples:
        >>> validate_market_symbol('AAPL')
        True
        >>> validate_market_symbol('BTC-USD')
        True
    """
    if not isinstance(symbol, str):
        raise ValidationError(f"Symbol must be a string, got {type(symbol).__name__}")

    if not symbol:
        raise ValidationError("Symbol cannot be empty")

    symbol = symbol.strip().upper()

    if len(symbol) < min_length:
        raise ValidationError(f"Symbol too short: {len(symbol)} < {min_length}")

    if len(symbol) > max_length:
        raise ValidationError(f"Symbol too long: {len(symbol)} > {max_length}")

    # Allow alphanumeric characters, dots, hyphens, and underscores
    if not re.match(r'^[A-Z0-9._-]+$', symbol):
        raise ValidationError(f"Invalid symbol format: {symbol}")

    # Check exchange prefix if specified
    if allowed_exchanges:
        exchange_prefix = symbol.split(':')[0] if ':' in symbol else None
        if exchange_prefix and exchange_prefix not in allowed_exchanges:
            raise ValidationError(f"Exchange {exchange_prefix} not in allowed list")

    logger.debug(f"Successfully validated symbol: {symbol}")
    return True


def validate_numeric_range(
    value: Union[int, float],
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
    field_name: str = "value",
    allow_none: bool = False
) -> bool:
    """
    Validate that a numeric value is within specified range.

    Args:
        value: The numeric value to validate
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive)
        field_name: Name of the field being validated (for error messages)
        allow_none: Whether None values are acceptable

    Returns:
        bool: True if valid

    Raises:
        ValidationError: If validation fails

    Examples:
        >>> validate_numeric_range(50, min_value=0, max_value=100)
        True
        >>> validate_numeric_range(-5, min_value=0, max_value=100)
        ValidationError: value must be >= 0
    """
    if value is None:
        if allow_none:
            return True
        raise ValidationError(f"{field_name} cannot be None")

    if not isinstance(value, (int, float)):
        raise ValidationError(
            f"{field_name} must be numeric, got {type(value).__name__}"
        )

    if min_value is not None and value < min_value:
        raise ValidationError(f"{field_name} must be >= {min_value}, got {value}")

    if max_value is not None and value > max_value:
        raise ValidationError(f"{field_name} must be <= {max_value}, got {value}")

    logger.debug(f"Successfully validated {field_name}: {value}")
    return True


def validate_percentage(
    value: Union[int, float],
    field_name: str = "percentage",
    allow_negative: bool = False
) -> bool:
    """
    Validate a percentage value.

    Args:
        value: The percentage value to validate
        field_name: Name of the field being validated
        allow_negative: Whether negative percentages are allowed

    Returns:
        bool: True if valid

    Raises:
        ValidationError: If validation fails
    """
    min_val = -100 if allow_negative else 0
    return validate_numeric_range(
        value,
        min_value=min_val,
        max_value=100,
        field_name=field_name
    )


def validate_api_response(
    response: Dict[str, Any],
    required_fields: List[str],
    optional_fields: Optional[List[str]] = None,
    response_name: str = "API response"
) -> bool:
    """
    Validate API response structure and required fields.

    Args:
        response: The API response dictionary to validate
        required_fields: List of required field names
        optional_fields: List of optional field names
        response_name: Name of the response type (for error messages)

    Returns:
        bool: True if valid

    Raises:
        ValidationError: If validation fails

    Examples:
        >>> validate_api_response(
        ...     {'symbol': 'AAPL', 'price': 150.0},
        ...     required_fields=['symbol', 'price']
        ... )
        True
    """
    if not isinstance(response, dict):
        raise ValidationError(
            f"{response_name} must be a dictionary, got {type(response).__name__}"
        )

    if not response:
        raise ValidationError(f"{response_name} cannot be empty")

    # Check for required fields
    missing_fields = [field for field in required_fields if field not in response]
    if missing_fields:
        raise ValidationError(
            f"{response_name} missing required fields: {', '.join(missing_fields)}"
        )

    # Check for None values in required fields
    none_fields = [
        field for field in required_fields
        if response.get(field) is None
    ]
    if none_fields:
        raise ValidationError(
            f"{response_name} has None values in required fields: {', '.join(none_fields)}"
        )

    # Log presence of optional fields
    if optional_fields:
        present_optional = [
            field for field in optional_fields
            if field in response and response[field] is not None
        ]
        logger.debug(f"Optional fields present: {present_optional}")

    logger.debug(f"Successfully validated {response_name}")
    return True


def validate_config(
    config: Dict[str, Any],
    required_keys: List[str],
    schema: Optional[Dict[str, type]] = None
) -> bool:
    """
    Validate configuration dictionary.

    Args:
        config: Configuration dictionary to validate
        required_keys: List of required configuration keys
        schema: Optional type schema for validation {key: expected_type}

    Returns:
        bool: True if valid

    Raises:
        ValidationError: If validation fails

    Examples:
        >>> validate_config(
        ...     {'api_key': 'abc123', 'timeout': 30},
        ...     required_keys=['api_key', 'timeout'],
        ...     schema={'api_key': str, 'timeout': int}
        ... )
        True
    """
    if not isinstance(config, dict):
        raise ValidationError(
            f"Config must be a dictionary, got {type(config).__name__}"
        )

    # Check required keys
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        raise ValidationError(
            f"Configuration missing required keys: {', '.join(missing_keys)}"
        )

    # Validate types if schema provided
    if schema:
        for key, expected_type in schema.items():
            if key in config and config[key] is not None:
                actual_value = config[key]
                if not isinstance(actual_value, expected_type):
                    raise ValidationError(
                        f"Config key '{key}' has wrong type: "
                        f"expected {expected_type.__name__}, "
                        f"got {type(actual_value).__name__}"
                    )

    logger.debug("Successfully validated configuration")
    return True


def validate_date_string(
    date_string: str,
    date_format: str = "%Y-%m-%d",
    field_name: str = "date"
) -> bool:
    """
    Validate date string format.

    Args:
        date_string: The date string to validate
        date_format: Expected date format (default: YYYY-MM-DD)
        field_name: Name of the field being validated

    Returns:
        bool: True if valid

    Raises:
        ValidationError: If validation fails

    Examples:
        >>> validate_date_string('2024-01-15')
        True
        >>> validate_date_string('invalid-date')
        ValidationError: Invalid date format
    """
    if not isinstance(date_string, str):
        raise ValidationError(
            f"{field_name} must be a string, got {type(date_string).__name__}"
        )

    try:
        datetime.strptime(date_string, date_format)
        logger.debug(f"Successfully validated {field_name}: {date_string}")
        return True
    except ValueError as e:
        raise ValidationError(
            f"Invalid {field_name} format: {date_string}. "
            f"Expected format: {date_format}. Error: {str(e)}"
        )


def validate_email(email: str) -> bool:
    """
    Validate email address format.

    Args:
        email: Email address to validate

    Returns:
        bool: True if valid

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(email, str):
        raise ValidationError(f"Email must be a string, got {type(email).__name__}")

    email = email.strip()

    if not email:
        raise ValidationError("Email cannot be empty")

    # Basic email regex pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(email_pattern, email):
        raise ValidationError(f"Invalid email format: {email}")

    logger.debug(f"Successfully validated email: {email}")
    return True


def validate_url(
    url: str,
    allowed_schemes: Optional[List[str]] = None,
    require_scheme: bool = True
) -> bool:
    """
    Validate URL format.

    Args:
        url: URL to validate
        allowed_schemes: Optional list of allowed URL schemes (e.g., ['http', 'https'])
        require_scheme: Whether URL must include a scheme

    Returns:
        bool: True if valid

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(url, str):
        raise ValidationError(f"URL must be a string, got {type(url).__name__}")

    url = url.strip()

    if not url:
        raise ValidationError("URL cannot be empty")

    # Basic URL pattern
    url_pattern = r'^(https?://)?([a-zA-Z0-9.-]+)(:[0-9]+)?(/.*)?$'

    if not re.match(url_pattern, url):
        raise ValidationError(f"Invalid URL format: {url}")

    # Check scheme if required
    if require_scheme and not url.startswith(('http://', 'https://')):
        raise ValidationError(f"URL must include scheme (http:// or https://): {url}")

    # Validate allowed schemes
    if allowed_schemes:
        scheme = url.split('://')[0] if '://' in url else None
        if scheme and scheme not in allowed_schemes:
            raise ValidationError(
                f"URL scheme '{scheme}' not in allowed schemes: {allowed_schemes}"
            )

    logger.debug(f"Successfully validated URL: {url}")
    return True


def validate_list_not_empty(
    items: List[Any],
    field_name: str = "list",
    min_length: int = 1,
    max_length: Optional[int] = None
) -> bool:
    """
    Validate that a list meets length requirements.

    Args:
        items: List to validate
        field_name: Name of the field being validated
        min_length: Minimum required list length
        max_length: Maximum allowed list length

    Returns:
        bool: True if valid

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(items, list):
        raise ValidationError(
            f"{field_name} must be a list, got {type(items).__name__}"
        )

    if len(items) < min_length:
        raise ValidationError(
            f"{field_name} must contain at least {min_length} items, got {len(items)}"
        )

    if max_length is not None and len(items) > max_length:
        raise ValidationError(
            f"{field_name} must contain at most {max_length} items, got {len(items)}"
        )

    logger.debug(f"Successfully validated {field_name}: {len(items)} items")
    return True


def validate_file_path(
    file_path: str,
    must_exist: bool = False,
    allowed_extensions: Optional[List[str]] = None
) -> bool:
    """
    Validate file path format and optionally existence.

    Args:
        file_path: File path to validate
        must_exist: Whether file must exist on filesystem
        allowed_extensions: Optional list of allowed file extensions (e.g., ['.csv', '.json'])

    Returns:
        bool: True if valid

    Raises:
        ValidationError: If validation fails
    """
    import os

    if not isinstance(file_path, str):
        raise ValidationError(
            f"File path must be a string, got {type(file_path).__name__}"
        )

    if not file_path.strip():
        raise ValidationError("File path cannot be empty")

    # Check extension if specified
    if allowed_extensions:
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in allowed_extensions:
            raise ValidationError(
                f"File extension '{ext}' not in allowed extensions: {allowed_extensions}"
            )

    # Check existence if required
    if must_exist and not os.path.exists(file_path):
        raise ValidationError(f"File does not exist: {file_path}")

    logger.debug(f"Successfully validated file path: {file_path}")
    return True


def validate_timeframe(
    timeframe: str,
    allowed_timeframes: Optional[List[str]] = None
) -> bool:
    """
    Validate trading timeframe string.

    Args:
        timeframe: Timeframe string (e.g., '1m', '5m', '1h', '1d')
        allowed_timeframes: Optional list of allowed timeframes

    Returns:
        bool: True if valid

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(timeframe, str):
        raise ValidationError(
            f"Timeframe must be a string, got {type(timeframe).__name__}"
        )

    timeframe = timeframe.strip().lower()

    if not timeframe:
        raise ValidationError("Timeframe cannot be empty")

    # Default allowed timeframes if not specified
    if allowed_timeframes is None:
        allowed_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1M']

    if timeframe not in allowed_timeframes:
        raise ValidationError(
            f"Invalid timeframe: {timeframe}. Allowed: {', '.join(allowed_timeframes)}"
        )

    logger.debug(f"Successfully validated timeframe: {timeframe}")
    return True
