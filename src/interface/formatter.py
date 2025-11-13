"""
Data formatting utilities for terminal display.

This module provides formatting functions for financial data including prices,
percentages, numbers, and table alignment for terminal output.
"""

from typing import Union, Optional, List, Any
from decimal import Decimal


def format_price(
    price: Union[float, int, Decimal, None],
    decimals: int = 5,
    currency: str = "$"
) -> str:
    """
    Format a price value with specified decimal places and currency symbol.

    Args:
        price: The price value to format
        decimals: Number of decimal places (default: 5)
        currency: Currency symbol to prepend (default: "$")

    Returns:
        Formatted price string

    Examples:
        >>> format_price(1234.56789)
        '$1,234.56789'
        >>> format_price(None)
        'N/A'
    """
    if price is None:
        return "N/A"

    try:
        price_float = float(price)
        if decimals == 0:
            return f"{currency}{price_float:,.0f}"
        return f"{currency}{price_float:,.{decimals}f}"
    except (ValueError, TypeError):
        return "N/A"


def format_percentage(
    value: Union[float, int, None],
    decimals: int = 2,
    show_sign: bool = True
) -> str:
    """
    Format a percentage value with sign and decimal places.

    Args:
        value: The percentage value to format (e.g., 5.5 for 5.5%)
        decimals: Number of decimal places (default: 2)
        show_sign: Whether to show + sign for positive values (default: True)

    Returns:
        Formatted percentage string

    Examples:
        >>> format_percentage(5.5)
        '+5.50%'
        >>> format_percentage(-2.3)
        '-2.30%'
        >>> format_percentage(0.0)
        '0.00%'
    """
    if value is None:
        return "N/A"

    try:
        value_float = float(value)
        sign = "+" if value_float > 0 and show_sign else ""
        return f"{sign}{value_float:.{decimals}f}%"
    except (ValueError, TypeError):
        return "N/A"


def format_number(
    value: Union[float, int, None],
    decimals: int = 2,
    use_commas: bool = True
) -> str:
    """
    Format a numeric value with specified decimal places and optional commas.

    Args:
        value: The numeric value to format
        decimals: Number of decimal places (default: 2)
        use_commas: Whether to use comma separators (default: True)

    Returns:
        Formatted number string

    Examples:
        >>> format_number(1234567.89)
        '1,234,567.89'
        >>> format_number(1234.5, decimals=1)
        '1,234.5'
    """
    if value is None:
        return "N/A"

    try:
        value_float = float(value)
        if use_commas:
            return f"{value_float:,.{decimals}f}"
        return f"{value_float:.{decimals}f}"
    except (ValueError, TypeError):
        return "N/A"


def format_volume(volume: Union[int, float, None]) -> str:
    """
    Format volume with K/M/B suffixes for large numbers.

    Args:
        volume: The volume value to format

    Returns:
        Formatted volume string

    Examples:
        >>> format_volume(1500)
        '1.50K'
        >>> format_volume(2500000)
        '2.50M'
        >>> format_volume(1500000000)
        '1.50B'
    """
    if volume is None:
        return "N/A"

    try:
        volume_float = float(volume)

        if volume_float >= 1_000_000_000:
            return f"{volume_float / 1_000_000_000:.2f}B"
        elif volume_float >= 1_000_000:
            return f"{volume_float / 1_000_000:.2f}M"
        elif volume_float >= 1_000:
            return f"{volume_float / 1_000:.2f}K"
        else:
            return f"{volume_float:.0f}"
    except (ValueError, TypeError):
        return "N/A"


def format_ratio(ratio: Union[float, None], decimals: int = 2) -> str:
    """
    Format a ratio value (e.g., risk/reward ratio).

    Args:
        ratio: The ratio value to format
        decimals: Number of decimal places (default: 2)

    Returns:
        Formatted ratio string

    Examples:
        >>> format_ratio(2.5)
        '2.50'
        >>> format_ratio(None)
        'N/A'
    """
    if ratio is None:
        return "N/A"

    try:
        ratio_float = float(ratio)
        return f"{ratio_float:.{decimals}f}"
    except (ValueError, TypeError):
        return "N/A"


def format_signal(signal: Optional[str]) -> str:
    """
    Format a trading signal for display.

    Args:
        signal: The signal string (e.g., 'BUY', 'SELL', 'HOLD')

    Returns:
        Formatted signal string

    Examples:
        >>> format_signal('BUY')
        'BUY'
        >>> format_signal(None)
        'HOLD'
    """
    if not signal:
        return "HOLD"

    return str(signal).upper()


def align_text(
    text: str,
    width: int,
    alignment: str = "left"
) -> str:
    """
    Align text within a specified width.

    Args:
        text: The text to align
        width: The total width for alignment
        alignment: Alignment type ('left', 'right', 'center')

    Returns:
        Aligned text string

    Examples:
        >>> align_text('Hello', 10, 'left')
        'Hello     '
        >>> align_text('Hello', 10, 'right')
        '     Hello'
        >>> align_text('Hello', 10, 'center')
        '  Hello   '
    """
    text = str(text)

    if alignment == "right":
        return text.rjust(width)
    elif alignment == "center":
        return text.center(width)
    else:  # left
        return text.ljust(width)


def create_separator(
    width: int,
    char: str = "-"
) -> str:
    """
    Create a separator line for table formatting.

    Args:
        width: The width of the separator
        char: The character to use for the separator (default: '-')

    Returns:
        Separator string

    Examples:
        >>> create_separator(10)
        '----------'
        >>> create_separator(5, '=')
        '====='
    """
    return char * width


def format_table_row(
    columns: List[Any],
    widths: List[int],
    alignments: Optional[List[str]] = None
) -> str:
    """
    Format a table row with specified column widths and alignments.

    Args:
        columns: List of column values
        widths: List of column widths
        alignments: List of alignment types for each column (default: all left)

    Returns:
        Formatted row string

    Examples:
        >>> format_table_row(['Name', 'Price', 'Change'], [10, 12, 10])
        'Name       Price        Change     '
    """
    if alignments is None:
        alignments = ["left"] * len(columns)

    # Ensure alignments list matches columns length
    while len(alignments) < len(columns):
        alignments.append("left")

    formatted_cols = []
    for col, width, alignment in zip(columns, widths, alignments):
        formatted_cols.append(align_text(str(col), width, alignment))

    return " ".join(formatted_cols)


def format_spread(bid: Optional[float], ask: Optional[float]) -> str:
    """
    Format bid-ask spread for display.

    Args:
        bid: Bid price
        ask: Ask price

    Returns:
        Formatted spread string

    Examples:
        >>> format_spread(1.2000, 1.2005)
        '1.20000 / 1.20050'
    """
    if bid is None or ask is None:
        return "N/A"

    try:
        return f"{float(bid):.5f} / {float(ask):.5f}"
    except (ValueError, TypeError):
        return "N/A"


def format_confidence(confidence: Union[float, int, None]) -> str:
    """
    Format confidence level as a percentage.

    Args:
        confidence: Confidence value (0-100 or 0-1)

    Returns:
        Formatted confidence string

    Examples:
        >>> format_confidence(0.85)
        '85%'
        >>> format_confidence(75)
        '75%'
    """
    if confidence is None:
        return "N/A"

    try:
        conf_float = float(confidence)
        # Convert to percentage if between 0 and 1
        if 0 <= conf_float <= 1:
            conf_float *= 100
        return f"{conf_float:.0f}%"
    except (ValueError, TypeError):
        return "N/A"


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length with optional suffix.

    Args:
        text: The text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add if truncated (default: '...')

    Returns:
        Truncated text string

    Examples:
        >>> truncate_text('Long text here', 10)
        'Long te...'
        >>> truncate_text('Short', 10)
        'Short'
    """
    text = str(text)

    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def format_timestamp(timestamp: Optional[str], time_format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a timestamp string for display.

    Args:
        timestamp: The timestamp to format
        time_format: The desired format string (default: '%Y-%m-%d %H:%M:%S')

    Returns:
        Formatted timestamp string

    Examples:
        >>> format_timestamp('2024-01-15 10:30:00')
        '2024-01-15 10:30:00'
    """
    if not timestamp:
        return "N/A"

    return str(timestamp)
