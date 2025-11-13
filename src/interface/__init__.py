"""
User interface modules for terminal display.

This package provides terminal display functionality with color-coded output,
formatted tables, and data formatting utilities for commodity market data.
"""

from .display import (
    TerminalDisplay,
    create_display,
    display_markets
)

from .formatter import (
    format_price,
    format_percentage,
    format_number,
    format_volume,
    format_ratio,
    format_signal,
    format_spread,
    format_confidence,
    format_table_row,
    create_separator,
    align_text,
    truncate_text,
    format_timestamp
)

__all__ = [
    # Display classes and functions
    "TerminalDisplay",
    "create_display",
    "display_markets",
    # Formatter functions
    "format_price",
    "format_percentage",
    "format_number",
    "format_volume",
    "format_ratio",
    "format_signal",
    "format_spread",
    "format_confidence",
    "format_table_row",
    "create_separator",
    "align_text",
    "truncate_text",
    "format_timestamp",
]
