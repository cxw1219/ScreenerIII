"""
Unit tests for data formatting module.

Tests formatting functions for prices, percentages, numbers,
and table alignment for terminal output.
"""

import pytest
from decimal import Decimal
import sys
from pathlib import Path as PathlibPath

# Add src directory to path
sys.path.insert(0, str(PathlibPath(__file__).parent.parent.parent / "src"))


class TestPriceFormatting:
    """Test suite for price formatting."""

    def test_format_price_basic(self):
        """Test basic price formatting."""
        from src.interface.formatter import format_price

        result = format_price(1234.56789)

        assert '$' in result
        assert '1,234.56789' in result

    def test_format_price_with_decimals(self):
        """Test price formatting with custom decimals."""
        from src.interface.formatter import format_price

        result = format_price(1234.56789, decimals=2)

        assert '1,234.57' in result

    def test_format_price_with_no_decimals(self):
        """Test price formatting with no decimals."""
        from src.interface.formatter import format_price

        result = format_price(1234.56, decimals=0)

        assert '1,235' in result

    def test_format_price_with_custom_currency(self):
        """Test price formatting with custom currency symbol."""
        from src.interface.formatter import format_price

        result = format_price(1234.56, currency='€')

        assert '€' in result

    def test_format_price_none(self):
        """Test price formatting with None value."""
        from src.interface.formatter import format_price

        result = format_price(None)

        assert result == 'N/A'

    def test_format_price_decimal_type(self):
        """Test price formatting with Decimal type."""
        from src.interface.formatter import format_price

        result = format_price(Decimal('1234.56789'))

        assert '1,234.56789' in result

    def test_format_price_integer(self):
        """Test price formatting with integer."""
        from src.interface.formatter import format_price

        result = format_price(1234)

        assert '1,234.00000' in result


class TestPercentageFormatting:
    """Test suite for percentage formatting."""

    def test_format_percentage_positive(self):
        """Test formatting positive percentage."""
        from src.interface.formatter import format_percentage

        result = format_percentage(5.5)

        assert '+5.50%' == result

    def test_format_percentage_negative(self):
        """Test formatting negative percentage."""
        from src.interface.formatter import format_percentage

        result = format_percentage(-2.3)

        assert '-2.30%' == result

    def test_format_percentage_zero(self):
        """Test formatting zero percentage."""
        from src.interface.formatter import format_percentage

        result = format_percentage(0.0)

        assert '0.00%' == result

    def test_format_percentage_without_sign(self):
        """Test formatting percentage without sign."""
        from src.interface.formatter import format_percentage

        result = format_percentage(5.5, show_sign=False)

        assert result == '5.50%'

    def test_format_percentage_custom_decimals(self):
        """Test formatting percentage with custom decimals."""
        from src.interface.formatter import format_percentage

        result = format_percentage(5.555, decimals=3)

        assert '+5.555%' == result

    def test_format_percentage_none(self):
        """Test formatting None percentage."""
        from src.interface.formatter import format_percentage

        result = format_percentage(None)

        assert result == 'N/A'


class TestNumberFormatting:
    """Test suite for number formatting."""

    def test_format_number_with_commas(self):
        """Test number formatting with commas."""
        from src.interface.formatter import format_number

        result = format_number(1234567.89)

        assert '1,234,567.89' == result

    def test_format_number_without_commas(self):
        """Test number formatting without commas."""
        from src.interface.formatter import format_number

        result = format_number(1234567.89, use_commas=False)

        assert '1234567.89' == result

    def test_format_number_custom_decimals(self):
        """Test number formatting with custom decimals."""
        from src.interface.formatter import format_number

        result = format_number(1234.5, decimals=1)

        assert '1,234.5' == result

    def test_format_number_none(self):
        """Test number formatting with None."""
        from src.interface.formatter import format_number

        result = format_number(None)

        assert result == 'N/A'


class TestVolumeFormatting:
    """Test suite for volume formatting."""

    def test_format_volume_thousands(self):
        """Test volume formatting with K suffix."""
        from src.interface.formatter import format_volume

        result = format_volume(1500)

        assert '1.50K' == result

    def test_format_volume_millions(self):
        """Test volume formatting with M suffix."""
        from src.interface.formatter import format_volume

        result = format_volume(2500000)

        assert '2.50M' == result

    def test_format_volume_billions(self):
        """Test volume formatting with B suffix."""
        from src.interface.formatter import format_volume

        result = format_volume(1500000000)

        assert '1.50B' == result

    def test_format_volume_small(self):
        """Test volume formatting for small numbers."""
        from src.interface.formatter import format_volume

        result = format_volume(500)

        assert '500' == result

    def test_format_volume_none(self):
        """Test volume formatting with None."""
        from src.interface.formatter import format_volume

        result = format_volume(None)

        assert result == 'N/A'


class TestRatioFormatting:
    """Test suite for ratio formatting."""

    def test_format_ratio_basic(self):
        """Test basic ratio formatting."""
        from src.interface.formatter import format_ratio

        result = format_ratio(2.5)

        assert '2.50' == result

    def test_format_ratio_custom_decimals(self):
        """Test ratio formatting with custom decimals."""
        from src.interface.formatter import format_ratio

        result = format_ratio(2.5555, decimals=3)

        assert '2.556' == result

    def test_format_ratio_none(self):
        """Test ratio formatting with None."""
        from src.interface.formatter import format_ratio

        result = format_ratio(None)

        assert result == 'N/A'


class TestSignalFormatting:
    """Test suite for signal formatting."""

    def test_format_signal_buy(self):
        """Test formatting BUY signal."""
        from src.interface.formatter import format_signal

        result = format_signal('BUY')

        assert result == 'BUY'

    def test_format_signal_sell(self):
        """Test formatting SELL signal."""
        from src.interface.formatter import format_signal

        result = format_signal('SELL')

        assert result == 'SELL'

    def test_format_signal_lowercase(self):
        """Test formatting lowercase signal."""
        from src.interface.formatter import format_signal

        result = format_signal('buy')

        assert result == 'BUY'

    def test_format_signal_none(self):
        """Test formatting None signal."""
        from src.interface.formatter import format_signal

        result = format_signal(None)

        assert result == 'HOLD'

    def test_format_signal_empty(self):
        """Test formatting empty signal."""
        from src.interface.formatter import format_signal

        result = format_signal('')

        assert result == 'HOLD'


class TestTextAlignment:
    """Test suite for text alignment."""

    def test_align_text_left(self):
        """Test left text alignment."""
        from src.interface.formatter import align_text

        result = align_text('Hello', 10, 'left')

        assert result == 'Hello     '
        assert len(result) == 10

    def test_align_text_right(self):
        """Test right text alignment."""
        from src.interface.formatter import align_text

        result = align_text('Hello', 10, 'right')

        assert result == '     Hello'
        assert len(result) == 10

    def test_align_text_center(self):
        """Test center text alignment."""
        from src.interface.formatter import align_text

        result = align_text('Hello', 10, 'center')

        assert len(result) == 10
        assert 'Hello' in result

    def test_align_text_default(self):
        """Test default text alignment (left)."""
        from src.interface.formatter import align_text

        result = align_text('Hello', 10)

        assert result == 'Hello     '


class TestSeparatorCreation:
    """Test suite for separator creation."""

    def test_create_separator_default(self):
        """Test creating separator with default character."""
        from src.interface.formatter import create_separator

        result = create_separator(10)

        assert result == '----------'
        assert len(result) == 10

    def test_create_separator_custom_char(self):
        """Test creating separator with custom character."""
        from src.interface.formatter import create_separator

        result = create_separator(5, '=')

        assert result == '====='
        assert len(result) == 5


class TestTableRowFormatting:
    """Test suite for table row formatting."""

    def test_format_table_row_basic(self):
        """Test basic table row formatting."""
        from src.interface.formatter import format_table_row

        result = format_table_row(['Name', 'Price', 'Change'], [10, 12, 10])

        assert isinstance(result, str)
        assert 'Name' in result
        assert 'Price' in result
        assert 'Change' in result

    def test_format_table_row_with_alignments(self):
        """Test table row formatting with alignments."""
        from src.interface.formatter import format_table_row

        result = format_table_row(
            ['Name', 'Price', 'Change'],
            [10, 12, 10],
            ['left', 'right', 'center']
        )

        assert isinstance(result, str)

    def test_format_table_row_default_alignments(self):
        """Test table row formatting with default alignments."""
        from src.interface.formatter import format_table_row

        result = format_table_row(
            ['Name', 'Price'],
            [10, 12]
        )

        assert isinstance(result, str)


class TestSpreadFormatting:
    """Test suite for bid-ask spread formatting."""

    def test_format_spread_basic(self):
        """Test basic spread formatting."""
        from src.interface.formatter import format_spread

        result = format_spread(1.2000, 1.2005)

        assert '1.20000' in result
        assert '1.20050' in result
        assert '/' in result

    def test_format_spread_none_bid(self):
        """Test spread formatting with None bid."""
        from src.interface.formatter import format_spread

        result = format_spread(None, 1.2005)

        assert result == 'N/A'

    def test_format_spread_none_ask(self):
        """Test spread formatting with None ask."""
        from src.interface.formatter import format_spread

        result = format_spread(1.2000, None)

        assert result == 'N/A'


class TestConfidenceFormatting:
    """Test suite for confidence formatting."""

    def test_format_confidence_decimal(self):
        """Test formatting confidence as decimal (0-1)."""
        from src.interface.formatter import format_confidence

        result = format_confidence(0.85)

        assert result == '85%'

    def test_format_confidence_percentage(self):
        """Test formatting confidence as percentage (0-100)."""
        from src.interface.formatter import format_confidence

        result = format_confidence(75)

        assert result == '75%'

    def test_format_confidence_none(self):
        """Test formatting None confidence."""
        from src.interface.formatter import format_confidence

        result = format_confidence(None)

        assert result == 'N/A'

    def test_format_confidence_boundary(self):
        """Test formatting confidence at boundaries."""
        from src.interface.formatter import format_confidence

        result1 = format_confidence(0.0)
        result2 = format_confidence(1.0)

        assert result1 == '0%'
        assert result2 == '100%'


class TestTextTruncation:
    """Test suite for text truncation."""

    def test_truncate_text_long(self):
        """Test truncating long text."""
        from src.interface.formatter import truncate_text

        result = truncate_text('Long text here', 10)

        assert result == 'Long te...'
        assert len(result) == 10

    def test_truncate_text_short(self):
        """Test truncating short text (no truncation)."""
        from src.interface.formatter import truncate_text

        result = truncate_text('Short', 10)

        assert result == 'Short'

    def test_truncate_text_custom_suffix(self):
        """Test truncating with custom suffix."""
        from src.interface.formatter import truncate_text

        result = truncate_text('Long text here', 10, suffix='--')

        assert result.endswith('--')
        assert len(result) == 10


class TestTimestampFormatting:
    """Test suite for timestamp formatting."""

    def test_format_timestamp_basic(self):
        """Test basic timestamp formatting."""
        from src.interface.formatter import format_timestamp

        result = format_timestamp('2024-01-15 10:30:00')

        assert result == '2024-01-15 10:30:00'

    def test_format_timestamp_none(self):
        """Test formatting None timestamp."""
        from src.interface.formatter import format_timestamp

        result = format_timestamp(None)

        assert result == 'N/A'

    def test_format_timestamp_empty(self):
        """Test formatting empty timestamp."""
        from src.interface.formatter import format_timestamp

        result = format_timestamp('')

        assert result == 'N/A'


class TestEdgeCases:
    """Test suite for edge cases and error handling."""

    def test_format_price_invalid_type(self):
        """Test price formatting with invalid type."""
        from src.interface.formatter import format_price

        result = format_price('invalid')

        assert result == 'N/A'

    def test_format_percentage_invalid_type(self):
        """Test percentage formatting with invalid type."""
        from src.interface.formatter import format_percentage

        result = format_percentage('invalid')

        assert result == 'N/A'

    def test_format_number_invalid_type(self):
        """Test number formatting with invalid type."""
        from src.interface.formatter import format_number

        result = format_number('invalid')

        assert result == 'N/A'

    def test_format_volume_invalid_type(self):
        """Test volume formatting with invalid type."""
        from src.interface.formatter import format_volume

        result = format_volume('invalid')

        assert result == 'N/A'

    def test_format_ratio_invalid_type(self):
        """Test ratio formatting with invalid type."""
        from src.interface.formatter import format_ratio

        result = format_ratio('invalid')

        assert result == 'N/A'

    def test_format_confidence_invalid_type(self):
        """Test confidence formatting with invalid type."""
        from src.interface.formatter import format_confidence

        result = format_confidence('invalid')

        assert result == 'N/A'
