"""
Unit tests for terminal display module.

Tests terminal display functionality including color coding, table formatting,
market grouping, and message display.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import sys
from pathlib import Path as PathlibPath

# Add src directory to path
sys.path.insert(0, str(PathlibPath(__file__).parent.parent.parent / "src"))


@pytest.fixture
def display():
    """Create TerminalDisplay instance."""
    from src.interface.display import TerminalDisplay

    return TerminalDisplay(refresh_rate=10)


@pytest.fixture
def sample_market_data():
    """Create sample market data for display."""
    return [
        {
            'symbol': 'EUR_USD',
            'price': 1.0050,
            'bid': 1.0048,
            'ask': 1.0052,
            'change_24h': 0.15,
            'signal': 'BUY',
            'direction': 'LONG',
            'target': 1.0100,
            'stop_loss': 1.0025,
            'risk_reward': 2.0,
            'atr': 0.0020,
            'volume': 150000,
            'confidence': 0.85
        },
        {
            'symbol': 'XAU_USD',
            'price': 1850.50,
            'bid': 1850.25,
            'ask': 1850.75,
            'change_24h': -0.25,
            'signal': 'SELL',
            'direction': 'SHORT',
            'target': 1845.00,
            'stop_loss': 1855.00,
            'risk_reward': 1.5,
            'atr': 5.50,
            'volume': 50000,
            'confidence': 0.70
        }
    ]


class TestTerminalDisplayInitialization:
    """Test suite for TerminalDisplay initialization."""

    def test_display_creation(self):
        """Test creating TerminalDisplay instance."""
        from src.interface.display import TerminalDisplay

        display = TerminalDisplay()

        assert display is not None

    def test_display_with_custom_refresh_rate(self):
        """Test display with custom refresh rate."""
        from src.interface.display import TerminalDisplay

        display = TerminalDisplay(refresh_rate=5)

        assert display.refresh_rate == 5

    def test_display_initial_last_update(self):
        """Test initial last_update is None."""
        from src.interface.display import TerminalDisplay

        display = TerminalDisplay()

        assert display.last_update is None


class TestColorFunctions:
    """Test suite for color selection functions."""

    def test_get_color_for_positive_change(self, display):
        """Test color for positive price change."""
        from colorama import Fore

        color = display.get_color_for_change(5.0)

        assert color == Fore.GREEN

    def test_get_color_for_negative_change(self, display):
        """Test color for negative price change."""
        from colorama import Fore

        color = display.get_color_for_change(-5.0)

        assert color == Fore.RED

    def test_get_color_for_zero_change(self, display):
        """Test color for zero price change."""
        from colorama import Fore

        color = display.get_color_for_change(0.0)

        assert color == Fore.YELLOW

    def test_get_color_for_none_change(self, display):
        """Test color for None price change."""
        from colorama import Fore

        color = display.get_color_for_change(None)

        assert color == Fore.YELLOW

    def test_get_color_for_buy_signal(self, display):
        """Test color for BUY signal."""
        from colorama import Fore

        color = display.get_color_for_signal('BUY')

        assert color == Fore.GREEN

    def test_get_color_for_sell_signal(self, display):
        """Test color for SELL signal."""
        from colorama import Fore

        color = display.get_color_for_signal('SELL')

        assert color == Fore.RED

    def test_get_color_for_hold_signal(self, display):
        """Test color for HOLD signal."""
        from colorama import Fore

        color = display.get_color_for_signal('HOLD')

        assert color == Fore.YELLOW

    def test_get_color_for_none_signal(self, display):
        """Test color for None signal."""
        from colorama import Fore

        color = display.get_color_for_signal(None)

        assert color == Fore.YELLOW


class TestDisplayFormatting:
    """Test suite for display formatting."""

    def test_format_market_row(self, display, sample_market_data):
        """Test formatting market data row."""
        row = display.format_market_row(sample_market_data[0])

        assert isinstance(row, str)
        assert len(row) > 0

    def test_format_market_row_with_missing_data(self, display):
        """Test formatting row with missing data."""
        incomplete_data = {
            'symbol': 'EUR_USD',
            'price': 1.0050
        }

        row = display.format_market_row(incomplete_data)

        assert isinstance(row, str)
        assert 'N/A' in row

    def test_format_market_row_display_name(self, display):
        """Test that display name is used for known symbols."""
        data = {
            'symbol': 'XAU_USD',
            'price': 1850.50
        }

        row = display.format_market_row(data)

        assert 'Gold' in row or 'XAU_USD' in row


class TestHeaderPrinting:
    """Test suite for header printing."""

    def test_print_header(self, display, capsys):
        """Test printing header."""
        display.print_header("Test Header")

        captured = capsys.readouterr()
        assert "Test Header" in captured.out

    def test_print_subheader(self, display, capsys):
        """Test printing subheader."""
        display.print_subheader("Test Subheader")

        captured = capsys.readouterr()
        assert "Test Subheader" in captured.out

    def test_print_title(self, display, capsys):
        """Test printing title."""
        display.print_title()

        captured = capsys.readouterr()
        assert "COMMODITY MARKET SCANNER" in captured.out

    def test_print_title_with_timestamp(self, display, capsys):
        """Test printing title with last update timestamp."""
        display.last_update = datetime.now()
        display.print_title()

        captured = capsys.readouterr()
        assert "Last Update" in captured.out

    def test_print_table_header(self, display, capsys):
        """Test printing table header."""
        display.print_table_header()

        captured = capsys.readouterr()
        assert "Symbol" in captured.out
        assert "Price" in captured.out


class TestCategoryDisplay:
    """Test suite for category-based display."""

    def test_print_category_data(self, display, sample_market_data, capsys):
        """Test printing category data."""
        display.print_category_data(
            "TEST CATEGORY",
            ['EUR_USD'],
            sample_market_data
        )

        captured = capsys.readouterr()
        assert "TEST CATEGORY" in captured.out

    def test_print_category_data_empty(self, display, capsys):
        """Test printing category with no data."""
        display.print_category_data(
            "EMPTY CATEGORY",
            ['NONEXISTENT'],
            []
        )

        # Should not raise exception

    def test_display_precious_metals_category(self, display):
        """Test precious metals category symbols."""
        assert 'XAU_USD' in display.PRECIOUS_METALS
        assert 'XAG_USD' in display.PRECIOUS_METALS

    def test_display_energy_category(self, display):
        """Test energy category symbols."""
        assert 'WTICO_USD' in display.ENERGY
        assert 'NATGAS_USD' in display.ENERGY

    def test_display_agriculture_category(self, display):
        """Test agriculture category symbols."""
        assert 'CORN_USD' in display.AGRICULTURE
        assert 'WHEAT_USD' in display.AGRICULTURE


class TestMarketDisplay:
    """Test suite for complete market display."""

    @patch('src.interface.display.TerminalDisplay.clear_screen')
    def test_display_markets(self, mock_clear, display, sample_market_data, capsys):
        """Test displaying all markets."""
        display.display_markets(sample_market_data)

        assert mock_clear.called
        assert display.last_update is not None

    @patch('src.interface.display.TerminalDisplay.clear_screen')
    def test_display_markets_updates_timestamp(self, mock_clear, display, sample_market_data):
        """Test that display_markets updates timestamp."""
        before = datetime.now()
        display.display_markets(sample_market_data)
        after = datetime.now()

        assert display.last_update is not None
        assert before <= display.last_update <= after


class TestFooterDisplay:
    """Test suite for footer display."""

    def test_print_footer(self, display, capsys):
        """Test printing footer."""
        display.print_footer()

        captured = capsys.readouterr()
        assert "Refresh Rate" in captured.out
        assert "GREEN: Bullish" in captured.out or "GREEN" in captured.out


class TestMessageDisplay:
    """Test suite for message display methods."""

    def test_display_error(self, display, capsys):
        """Test displaying error message."""
        display.display_error("Test error message")

        captured = capsys.readouterr()
        assert "ERROR" in captured.out
        assert "Test error message" in captured.out

    def test_display_warning(self, display, capsys):
        """Test displaying warning message."""
        display.display_warning("Test warning message")

        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "Test warning message" in captured.out

    def test_display_info(self, display, capsys):
        """Test displaying info message."""
        display.display_info("Test info message")

        captured = capsys.readouterr()
        assert "INFO" in captured.out
        assert "Test info message" in captured.out

    def test_display_success(self, display, capsys):
        """Test displaying success message."""
        display.display_success("Test success message")

        captured = capsys.readouterr()
        assert "SUCCESS" in captured.out
        assert "Test success message" in captured.out

    def test_display_loading(self, display, capsys):
        """Test displaying loading message."""
        display.display_loading("Loading test...")

        captured = capsys.readouterr()
        assert "Loading test..." in captured.out


class TestSummaryDisplay:
    """Test suite for summary display."""

    def test_display_summary(self, display, capsys):
        """Test displaying market summary."""
        summary_data = {
            'total_markets': 10,
            'bullish_count': 4,
            'bearish_count': 3,
            'neutral_count': 3,
            'avg_change': 0.15
        }

        display.display_summary(summary_data)

        captured = capsys.readouterr()
        assert "MARKET SUMMARY" in captured.out
        assert "Total Markets" in captured.out

    def test_display_summary_with_defaults(self, display, capsys):
        """Test displaying summary with missing values."""
        summary_data = {}

        display.display_summary(summary_data)

        # Should not raise exception


class TestStartupBanner:
    """Test suite for startup banner."""

    def test_display_startup_banner(self, display, capsys):
        """Test displaying startup banner."""
        display.display_startup_banner()

        captured = capsys.readouterr()
        assert "SCREENER III" in captured.out
        assert "Version" in captured.out


class TestConvenienceFunctions:
    """Test suite for convenience functions."""

    def test_create_display_function(self):
        """Test create_display convenience function."""
        from src.interface.display import create_display

        display = create_display(refresh_rate=5)

        assert display is not None
        assert display.refresh_rate == 5

    @patch('src.interface.display.TerminalDisplay.display_markets')
    def test_display_markets_function(self, mock_display_markets, sample_market_data):
        """Test display_markets convenience function."""
        from src.interface.display import display_markets

        display_markets(sample_market_data, refresh_rate=10)

        # Should not raise exception


class TestClearScreen:
    """Test suite for clear screen functionality."""

    @patch('os.system')
    def test_clear_screen_unix(self, mock_system):
        """Test clear screen on Unix systems."""
        from src.interface.display import TerminalDisplay

        with patch('os.name', 'posix'):
            TerminalDisplay.clear_screen()
            mock_system.assert_called_with('clear')

    @patch('os.system')
    def test_clear_screen_windows(self, mock_system):
        """Test clear screen on Windows systems."""
        from src.interface.display import TerminalDisplay

        with patch('os.name', 'nt'):
            TerminalDisplay.clear_screen()
            mock_system.assert_called_with('cls')


class TestColumnWidths:
    """Test suite for column width definitions."""

    def test_column_widths_exist(self, display):
        """Test that COLUMN_WIDTHS dictionary exists."""
        assert hasattr(display, 'COLUMN_WIDTHS')
        assert isinstance(display.COLUMN_WIDTHS, dict)

    def test_column_widths_complete(self, display):
        """Test that all required column widths are defined."""
        required_columns = [
            'symbol', 'price', 'spread', 'change_24h',
            'signal', 'direction', 'target', 'stop',
            'risk_reward', 'atr', 'volume', 'confidence'
        ]

        for col in required_columns:
            assert col in display.COLUMN_WIDTHS


class TestDisplayNames:
    """Test suite for display name mappings."""

    def test_display_names_exist(self, display):
        """Test that DISPLAY_NAMES dictionary exists."""
        assert hasattr(display, 'DISPLAY_NAMES')
        assert isinstance(display.DISPLAY_NAMES, dict)

    def test_display_names_for_precious_metals(self, display):
        """Test display names for precious metals."""
        assert display.DISPLAY_NAMES.get('XAU_USD') == 'Gold'
        assert display.DISPLAY_NAMES.get('XAG_USD') == 'Silver'

    def test_display_names_for_energy(self, display):
        """Test display names for energy commodities."""
        assert 'Crude' in display.DISPLAY_NAMES.get('WTICO_USD', '')
        assert 'Natural Gas' == display.DISPLAY_NAMES.get('NATGAS_USD')
