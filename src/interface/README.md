# Terminal Interface Module

This module provides color-coded terminal display functionality for the ScreenerIII commodity market scanner.

## Features

- **Color-coded output**: Green for bullish/positive, red for bearish/negative, yellow for neutral
- **Formatted tables**: Professional table layout with proper column alignment
- **Commodity grouping**: Markets organized by category (Precious Metals, Energy, Agriculture)
- **Real-time updates**: Clear screen and refresh display logic
- **Comprehensive formatting**: Utilities for prices, percentages, volumes, and more

## Module Structure

```
src/interface/
├── __init__.py      # Package initialization and exports
├── display.py       # Terminal display manager
├── formatter.py     # Data formatting utilities
└── README.md        # This file
```

## Quick Start

### Basic Usage

```python
from src.interface import TerminalDisplay

# Create display instance
display = TerminalDisplay(refresh_rate=10)

# Sample market data
market_data = [
    {
        "symbol": "XAU_USD",
        "price": 2045.50,
        "bid": 2045.25,
        "ask": 2045.75,
        "change_24h": 1.25,
        "signal": "BUY",
        "direction": "LONG",
        "target": 2065.00,
        "stop_loss": 2035.00,
        "risk_reward": 2.5,
        "atr": 12.50,
        "volume": 145000,
        "confidence": 75
    },
    # ... more markets
]

# Display markets
display.display_markets(market_data)
```

### Using Convenience Functions

```python
from src.interface import display_markets

# Quick display without creating instance
display_markets(market_data, refresh_rate=10)
```

## Display Module (display.py)

### TerminalDisplay Class

Main class for managing terminal output.

#### Methods

- `display_markets(market_data)` - Display all markets grouped by category
- `print_title()` - Print main application title
- `print_header(text, color)` - Print formatted header
- `print_subheader(text, color)` - Print formatted subheader
- `display_summary(summary_data)` - Display market statistics summary
- `display_error(message)` - Display error message in red
- `display_warning(message)` - Display warning message in yellow
- `display_info(message)` - Display info message in cyan
- `display_success(message)` - Display success message in green
- `display_loading(message)` - Display loading message
- `display_startup_banner()` - Display startup banner
- `clear_screen()` - Clear terminal screen

#### Color Scheme

- **Green**: Bullish signals, positive changes, BUY signals
- **Red**: Bearish signals, negative changes, SELL signals
- **Yellow**: Neutral signals, HOLD signals, warnings
- **Cyan**: Headers, information messages
- **White**: Regular text

#### Commodity Categories

**Precious Metals**
- Gold (XAU_USD)
- Silver (XAG_USD)
- Platinum (XPT_USD)
- Palladium (XPD_USD)

**Energy**
- Brent Crude (BCO_USD)
- WTI Crude (WTICO_USD)
- Natural Gas (NATGAS_USD)

**Agriculture**
- Corn (CORN_USD)
- Soybeans (SOYBN_USD)
- Wheat (WHEAT_USD)
- Sugar (SUGAR_USD)

## Formatter Module (formatter.py)

### Formatting Functions

#### Price Formatting

```python
from src.interface import format_price

format_price(1234.56789)  # '$1,234.56789'
format_price(1234.56789, decimals=2)  # '$1,234.57'
format_price(1234.56789, currency="€")  # '€1,234.56789'
```

#### Percentage Formatting

```python
from src.interface import format_percentage

format_percentage(5.5)  # '+5.50%'
format_percentage(-2.3)  # '-2.30%'
format_percentage(0.0)  # '0.00%'
format_percentage(5.5, show_sign=False)  # '5.50%'
```

#### Number Formatting

```python
from src.interface import format_number

format_number(1234567.89)  # '1,234,567.89'
format_number(1234.5, decimals=1)  # '1,234.5'
format_number(1234.5, use_commas=False)  # '1234.50'
```

#### Volume Formatting

```python
from src.interface import format_volume

format_volume(1500)  # '1.50K'
format_volume(2500000)  # '2.50M'
format_volume(1500000000)  # '1.50B'
```

#### Other Formatting Functions

```python
from src.interface import (
    format_ratio,
    format_signal,
    format_spread,
    format_confidence,
    format_timestamp
)

# Ratio formatting
format_ratio(2.5)  # '2.50'

# Signal formatting
format_signal('buy')  # 'BUY'

# Spread formatting
format_spread(1.2000, 1.2005)  # '1.20000 / 1.20050'

# Confidence formatting
format_confidence(0.85)  # '85%'
format_confidence(75)  # '75%'

# Timestamp formatting
format_timestamp('2024-01-15 10:30:00')  # '2024-01-15 10:30:00'
```

#### Table Formatting

```python
from src.interface import (
    format_table_row,
    create_separator,
    align_text,
    truncate_text
)

# Table row formatting
columns = ['Name', 'Price', 'Change']
widths = [10, 12, 10]
alignments = ['left', 'right', 'right']
format_table_row(columns, widths, alignments)

# Create separator
create_separator(50)  # '--------------------------------------------------'
create_separator(50, '=')  # '=================================================='

# Text alignment
align_text('Hello', 10, 'left')  # 'Hello     '
align_text('Hello', 10, 'right')  # '     Hello'
align_text('Hello', 10, 'center')  # '  Hello   '

# Text truncation
truncate_text('Long text here', 10)  # 'Long te...'
```

## Market Data Format

The expected format for market data dictionaries:

```python
{
    "symbol": str,          # Market symbol (e.g., "XAU_USD")
    "price": float,         # Current price
    "bid": float,           # Bid price
    "ask": float,           # Ask price
    "change_24h": float,    # 24-hour price change percentage
    "signal": str,          # Trading signal ("BUY", "SELL", "HOLD")
    "direction": str,       # Trade direction ("LONG", "SHORT", "NEUTRAL")
    "target": float,        # Target price
    "stop_loss": float,     # Stop loss price
    "risk_reward": float,   # Risk/reward ratio
    "atr": float,           # Average True Range
    "volume": int,          # Trading volume
    "confidence": float     # Signal confidence (0-100 or 0-1)
}
```

## Summary Data Format

The expected format for summary statistics:

```python
{
    "total_markets": int,      # Total number of markets
    "bullish_count": int,      # Number of bullish signals
    "bearish_count": int,      # Number of bearish signals
    "neutral_count": int,      # Number of neutral signals
    "avg_change": float        # Average 24h change percentage
}
```

## Example Usage

See `/home/user/ScreenerIII/example_display.py` for a complete working example.

## Dependencies

- **colorama**: Cross-platform colored terminal text
- **typing**: Type hints support

## Type Hints

All functions include comprehensive type hints for better IDE support and code documentation.

## Error Handling

All formatting functions gracefully handle:
- `None` values (return "N/A")
- Invalid types (return "N/A")
- Edge cases (empty strings, zero values, etc.)

## Thread Safety

The display module is not thread-safe. If using in a multi-threaded environment, ensure proper synchronization when calling display methods.

## Platform Support

- **Linux**: Full support
- **macOS**: Full support
- **Windows**: Full support (colorama handles Windows console API)

## Performance

The formatting functions are optimized for real-time display and can handle high-frequency updates (10+ updates per second).
