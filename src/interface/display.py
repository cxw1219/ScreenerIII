"""
Terminal display module for commodity market data.

This module provides color-coded terminal display functionality using colorama,
with formatted tables grouped by commodity categories.
"""

import os
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime
from colorama import init, Fore, Back, Style

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
    align_text
)

# Initialize colorama for cross-platform color support
init(autoreset=True)


class TerminalDisplay:
    """
    Terminal display manager for commodity market data.

    Provides color-coded output with formatted tables grouped by commodity
    categories (Precious Metals, Energy, Agriculture).
    """

    # Commodity groupings
    PRECIOUS_METALS = ["XAU_USD", "XAG_USD", "XPT_USD", "XPD_USD"]
    ENERGY = ["BCO_USD", "WTICO_USD", "NATGAS_USD"]
    AGRICULTURE = ["CORN_USD", "SOYBN_USD", "WHEAT_USD", "SUGAR_USD"]

    # Commodity display names
    DISPLAY_NAMES = {
        "XAU_USD": "Gold",
        "XAG_USD": "Silver",
        "XPT_USD": "Platinum",
        "XPD_USD": "Palladium",
        "BCO_USD": "Brent Crude",
        "WTICO_USD": "WTI Crude",
        "NATGAS_USD": "Natural Gas",
        "CORN_USD": "Corn",
        "SOYBN_USD": "Soybeans",
        "WHEAT_USD": "Wheat",
        "SUGAR_USD": "Sugar"
    }

    # Column widths for table display
    COLUMN_WIDTHS = {
        "symbol": 12,
        "price": 12,
        "spread": 18,
        "change_24h": 10,
        "signal": 8,
        "direction": 10,
        "target": 12,
        "stop": 12,
        "risk_reward": 8,
        "atr": 10,
        "volume": 10,
        "confidence": 10
    }

    def __init__(self, refresh_rate: int = 10):
        """
        Initialize the terminal display.

        Args:
            refresh_rate: Screen refresh rate in seconds (default: 10)
        """
        self.refresh_rate = refresh_rate
        self.last_update: Optional[datetime] = None

    @staticmethod
    def clear_screen() -> None:
        """Clear the terminal screen for refresh."""
        os.system('cls' if os.name == 'nt' else 'clear')

    @staticmethod
    def get_color_for_change(change: Optional[float]) -> str:
        """
        Get color code based on price change value.

        Args:
            change: Price change percentage

        Returns:
            Colorama color code (GREEN for positive, RED for negative, YELLOW for neutral)
        """
        if change is None:
            return Fore.YELLOW

        try:
            change_float = float(change)
            if change_float > 0:
                return Fore.GREEN
            elif change_float < 0:
                return Fore.RED
            else:
                return Fore.YELLOW
        except (ValueError, TypeError):
            return Fore.YELLOW

    @staticmethod
    def get_color_for_signal(signal: Optional[str]) -> str:
        """
        Get color code based on trading signal.

        Args:
            signal: Trading signal (BUY, SELL, HOLD)

        Returns:
            Colorama color code (GREEN for BUY, RED for SELL, YELLOW for HOLD)
        """
        if not signal:
            return Fore.YELLOW

        signal_upper = str(signal).upper()
        if signal_upper == "BUY":
            return Fore.GREEN
        elif signal_upper == "SELL":
            return Fore.RED
        else:
            return Fore.YELLOW

    @staticmethod
    def print_header(text: str, color: str = Fore.CYAN) -> None:
        """
        Print a formatted header with color.

        Args:
            text: Header text
            color: Color code for the header (default: CYAN)
        """
        separator = "=" * len(text)
        print(f"\n{color}{Style.BRIGHT}{separator}")
        print(f"{text}")
        print(f"{separator}{Style.RESET_ALL}\n")

    @staticmethod
    def print_subheader(text: str, color: str = Fore.MAGENTA) -> None:
        """
        Print a formatted subheader with color.

        Args:
            text: Subheader text
            color: Color code for the subheader (default: MAGENTA)
        """
        print(f"\n{color}{Style.BRIGHT}{text}{Style.RESET_ALL}")
        print(f"{color}{'-' * len(text)}{Style.RESET_ALL}")

    def print_title(self) -> None:
        """Print the main application title."""
        title = "COMMODITY MARKET SCANNER - REAL-TIME DATA"
        border = "=" * len(title)

        print(f"\n{Fore.CYAN}{Style.BRIGHT}{border}")
        print(f"{title}")
        print(f"{border}{Style.RESET_ALL}")

        if self.last_update:
            timestamp = self.last_update.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{Fore.WHITE}Last Update: {timestamp}{Style.RESET_ALL}")
        print()

    def print_table_header(self) -> None:
        """Print the table column headers."""
        headers = [
            "Symbol",
            "Price",
            "Spread",
            "24h Change",
            "Signal",
            "Direction",
            "Target",
            "Stop",
            "R/R",
            "ATR",
            "Volume",
            "Conf."
        ]

        widths = [
            self.COLUMN_WIDTHS["symbol"],
            self.COLUMN_WIDTHS["price"],
            self.COLUMN_WIDTHS["spread"],
            self.COLUMN_WIDTHS["change_24h"],
            self.COLUMN_WIDTHS["signal"],
            self.COLUMN_WIDTHS["direction"],
            self.COLUMN_WIDTHS["target"],
            self.COLUMN_WIDTHS["stop"],
            self.COLUMN_WIDTHS["risk_reward"],
            self.COLUMN_WIDTHS["atr"],
            self.COLUMN_WIDTHS["volume"],
            self.COLUMN_WIDTHS["confidence"]
        ]

        alignments = ["left"] + ["right"] * (len(headers) - 1)

        # Print header row
        header_row = format_table_row(headers, widths, alignments)
        print(f"{Fore.WHITE}{Style.BRIGHT}{header_row}{Style.RESET_ALL}")

        # Print separator
        total_width = sum(widths) + len(widths) - 1
        print(f"{Fore.WHITE}{create_separator(total_width)}{Style.RESET_ALL}")

    def format_market_row(self, market_data: Dict[str, Any]) -> str:
        """
        Format a single market data row for display.

        Args:
            market_data: Dictionary containing market data

        Returns:
            Formatted row string with color codes
        """
        # Extract data with defaults
        symbol = market_data.get("symbol", "N/A")
        display_name = self.DISPLAY_NAMES.get(symbol, symbol)
        price = market_data.get("price")
        bid = market_data.get("bid")
        ask = market_data.get("ask")
        change_24h = market_data.get("change_24h")
        signal = market_data.get("signal")
        direction = market_data.get("direction", "N/A")
        target = market_data.get("target")
        stop_loss = market_data.get("stop_loss")
        risk_reward = market_data.get("risk_reward")
        atr = market_data.get("atr")
        volume = market_data.get("volume")
        confidence = market_data.get("confidence")

        # Format columns
        cols = [
            display_name,
            format_price(price, decimals=5),
            format_spread(bid, ask),
            format_percentage(change_24h),
            format_signal(signal),
            str(direction).upper() if direction else "N/A",
            format_price(target, decimals=5),
            format_price(stop_loss, decimals=5),
            format_ratio(risk_reward),
            format_number(atr, decimals=4),
            format_volume(volume),
            format_confidence(confidence)
        ]

        widths = [
            self.COLUMN_WIDTHS["symbol"],
            self.COLUMN_WIDTHS["price"],
            self.COLUMN_WIDTHS["spread"],
            self.COLUMN_WIDTHS["change_24h"],
            self.COLUMN_WIDTHS["signal"],
            self.COLUMN_WIDTHS["direction"],
            self.COLUMN_WIDTHS["target"],
            self.COLUMN_WIDTHS["stop"],
            self.COLUMN_WIDTHS["risk_reward"],
            self.COLUMN_WIDTHS["atr"],
            self.COLUMN_WIDTHS["volume"],
            self.COLUMN_WIDTHS["confidence"]
        ]

        alignments = ["left"] + ["right"] * (len(cols) - 1)

        # Color-code the change column
        change_color = self.get_color_for_change(change_24h)
        signal_color = self.get_color_for_signal(signal)

        # Build the row with colors
        formatted_cols = []
        for i, (col, width, alignment) in enumerate(zip(cols, widths, alignments)):
            aligned_col = align_text(col, width, alignment)

            # Apply colors to specific columns
            if i == 3:  # 24h change column
                formatted_cols.append(f"{change_color}{aligned_col}{Style.RESET_ALL}")
            elif i == 4:  # Signal column
                formatted_cols.append(f"{signal_color}{Style.BRIGHT}{aligned_col}{Style.RESET_ALL}")
            else:
                formatted_cols.append(f"{Fore.WHITE}{aligned_col}{Style.RESET_ALL}")

        return " ".join(formatted_cols)

    def print_category_data(
        self,
        category_name: str,
        symbols: List[str],
        market_data: List[Dict[str, Any]]
    ) -> None:
        """
        Print market data for a specific commodity category.

        Args:
            category_name: Name of the category (e.g., "Precious Metals")
            symbols: List of symbols in this category
            market_data: List of market data dictionaries
        """
        # Filter data for this category
        category_data = [
            data for data in market_data
            if data.get("symbol") in symbols
        ]

        if not category_data:
            return

        # Print category header
        self.print_subheader(category_name)
        self.print_table_header()

        # Print each market row
        for data in category_data:
            row = self.format_market_row(data)
            print(row)

    def display_markets(self, market_data: List[Dict[str, Any]]) -> None:
        """
        Display all market data grouped by category.

        Args:
            market_data: List of market data dictionaries
        """
        self.clear_screen()
        self.last_update = datetime.now()
        self.print_title()

        # Display Precious Metals
        self.print_category_data(
            "PRECIOUS METALS",
            self.PRECIOUS_METALS,
            market_data
        )

        # Display Energy
        self.print_category_data(
            "ENERGY",
            self.ENERGY,
            market_data
        )

        # Display Agriculture
        self.print_category_data(
            "AGRICULTURE",
            self.AGRICULTURE,
            market_data
        )

        # Print footer
        self.print_footer()

    def print_footer(self) -> None:
        """Print footer with refresh information."""
        print(f"\n{Fore.CYAN}{Style.DIM}{'─' * 80}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Refresh Rate: {self.refresh_rate}s | "
              f"{Fore.GREEN}GREEN: Bullish/Positive | "
              f"{Fore.RED}RED: Bearish/Negative | "
              f"{Fore.YELLOW}YELLOW: Neutral{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{Style.DIM}Press Ctrl+C to exit{Style.RESET_ALL}\n")

    def display_error(self, error_message: str) -> None:
        """
        Display an error message.

        Args:
            error_message: Error message to display
        """
        print(f"\n{Fore.RED}{Style.BRIGHT}ERROR: {error_message}{Style.RESET_ALL}\n")

    def display_warning(self, warning_message: str) -> None:
        """
        Display a warning message.

        Args:
            warning_message: Warning message to display
        """
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}WARNING: {warning_message}{Style.RESET_ALL}\n")

    def display_info(self, info_message: str) -> None:
        """
        Display an informational message.

        Args:
            info_message: Info message to display
        """
        print(f"\n{Fore.CYAN}{Style.BRIGHT}INFO: {info_message}{Style.RESET_ALL}\n")

    def display_success(self, success_message: str) -> None:
        """
        Display a success message.

        Args:
            success_message: Success message to display
        """
        print(f"\n{Fore.GREEN}{Style.BRIGHT}SUCCESS: {success_message}{Style.RESET_ALL}\n")

    def display_loading(self, message: str = "Loading market data...") -> None:
        """
        Display a loading message.

        Args:
            message: Loading message to display
        """
        print(f"{Fore.YELLOW}{message}{Style.RESET_ALL}", end="\r")
        sys.stdout.flush()

    def display_summary(self, summary_data: Dict[str, Any]) -> None:
        """
        Display a summary of market statistics.

        Args:
            summary_data: Dictionary containing summary statistics
        """
        self.print_subheader("MARKET SUMMARY")

        total_markets = summary_data.get("total_markets", 0)
        bullish_count = summary_data.get("bullish_count", 0)
        bearish_count = summary_data.get("bearish_count", 0)
        neutral_count = summary_data.get("neutral_count", 0)
        avg_change = summary_data.get("avg_change", 0)

        print(f"{Fore.WHITE}Total Markets: {Style.BRIGHT}{total_markets}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Bullish Signals: {Style.BRIGHT}{bullish_count}{Style.RESET_ALL}")
        print(f"{Fore.RED}Bearish Signals: {Style.BRIGHT}{bearish_count}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Neutral Signals: {Style.BRIGHT}{neutral_count}{Style.RESET_ALL}")

        avg_change_color = self.get_color_for_change(avg_change)
        print(f"{Fore.WHITE}Average 24h Change: "
              f"{avg_change_color}{Style.BRIGHT}{format_percentage(avg_change)}{Style.RESET_ALL}")

    def display_startup_banner(self) -> None:
        """Display startup banner with application information."""
        banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║           SCREENER III - COMMODITY MARKET SCANNER         ║
    ║                                                           ║
    ║              Real-time Technical Analysis                 ║
    ║                   Version 1.0.0                           ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
        """
        print(f"{Fore.CYAN}{Style.BRIGHT}{banner}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Initializing scanner...{Style.RESET_ALL}\n")


# Convenience functions for simple usage
def create_display(refresh_rate: int = 10) -> TerminalDisplay:
    """
    Create and return a TerminalDisplay instance.

    Args:
        refresh_rate: Screen refresh rate in seconds

    Returns:
        TerminalDisplay instance
    """
    return TerminalDisplay(refresh_rate=refresh_rate)


def display_markets(market_data: List[Dict[str, Any]], refresh_rate: int = 10) -> None:
    """
    Display market data using the terminal display.

    Args:
        market_data: List of market data dictionaries
        refresh_rate: Screen refresh rate in seconds
    """
    display = TerminalDisplay(refresh_rate=refresh_rate)
    display.display_markets(market_data)
