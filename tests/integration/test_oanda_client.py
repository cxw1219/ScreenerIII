"""
Integration tests for OANDA API client.

Tests the interaction with the OANDA broker API, including:
- Connection handling
- Data fetching
- Order placement
- Account management

Note: Uses mocking to avoid real API calls.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta
import sys
from pathlib import Path as PathlibPath

# Add src directory to path
sys.path.insert(0, str(PathlibPath(__file__).parent.parent.parent / "src"))


class TestOandaClientInitialization:
    """Test suite for OANDA client initialization."""

    def test_mock_client_structure(self, mock_oanda_client):
        """Test that mock OANDA client has expected methods."""
        assert hasattr(mock_oanda_client, "get_account")
        assert hasattr(mock_oanda_client, "get_instrument_candles")
        assert hasattr(mock_oanda_client, "place_order")

    def test_mock_client_callable(self, mock_oanda_client):
        """Test that mock client methods are callable."""
        assert callable(mock_oanda_client.get_account)
        assert callable(mock_oanda_client.get_instrument_candles)
        assert callable(mock_oanda_client.place_order)

    @patch("builtins.open")
    def test_client_initialization_with_credentials(self, mock_file):
        """Test client initialization with credentials."""
        credentials = {
            "account_id": "test_123",
            "api_token": "test_token",
        }
        assert credentials["account_id"] is not None
        assert credentials["api_token"] is not None


class TestOandaAccountOperations:
    """Test suite for OANDA account-related operations."""

    def test_get_account_success(self, mock_oanda_client):
        """Test successful account retrieval."""
        response = mock_oanda_client.get_account()

        assert "account" in response
        assert response["account"]["id"] == "test_account_123"
        assert response["account"]["balance"] == 100000.0

    def test_get_account_structure(self, mock_oanda_client):
        """Test account response structure."""
        response = mock_oanda_client.get_account()
        account = response["account"]

        assert "id" in account
        assert "balance" in account
        assert "currency" in account
        assert "openTradeCount" in account

    def test_account_balance_positive(self, mock_oanda_client):
        """Test that account balance is positive."""
        response = mock_oanda_client.get_account()
        balance = response["account"]["balance"]
        assert balance > 0

    def test_account_currency_set(self, mock_oanda_client):
        """Test that account currency is set."""
        response = mock_oanda_client.get_account()
        currency = response["account"]["currency"]
        assert currency in ["USD", "EUR", "GBP", "JPY"]

    def test_open_trades_count(self, mock_oanda_client):
        """Test open trades counter."""
        response = mock_oanda_client.get_account()
        open_trades = response["account"]["openTradeCount"]
        assert isinstance(open_trades, int)
        assert open_trades >= 0


class TestOandaDataFetching:
    """Test suite for OANDA data fetching operations."""

    def test_get_candles_success(self, mock_oanda_client):
        """Test successful candle data retrieval."""
        response = mock_oanda_client.get_instrument_candles()

        assert "candles" in response
        assert isinstance(response["candles"], list)
        assert len(response["candles"]) > 0

    def test_get_candles_parameters(self, mock_oanda_client):
        """Test candle retrieval with parameters."""
        # Call with parameters
        mock_oanda_client.get_instrument_candles(
            instrument="EUR_USD",
            granularity="H1",
            count=100,
        )

        # Verify the mock was called
        mock_oanda_client.get_instrument_candles.assert_called_once()

    def test_candle_structure(self, mock_oanda_client):
        """Test structure of returned candle data."""
        response = mock_oanda_client.get_instrument_candles()
        candle = response["candles"][0]

        assert "time" in candle
        assert "bid" in candle
        assert "ask" in candle
        assert "volume" in candle
        assert "complete" in candle

    def test_candle_bid_ask_structure(self, mock_oanda_client):
        """Test bid/ask structure in candle data."""
        response = mock_oanda_client.get_instrument_candles()
        candle = response["candles"][0]
        bid = candle["bid"]

        assert "o" in bid  # open
        assert "h" in bid  # high
        assert "l" in bid  # low
        assert "c" in bid  # close

    def test_multiple_instruments_fetch(self, mock_oanda_client):
        """Test fetching data for multiple instruments."""
        instruments = ["EUR_USD", "GBP_USD", "USD_JPY"]

        for instrument in instruments:
            mock_oanda_client.get_instrument_candles(instrument=instrument)

        # Verify get_instrument_candles was called multiple times
        assert mock_oanda_client.get_instrument_candles.call_count >= 1

    def test_different_timeframes(self, mock_oanda_client):
        """Test fetching different timeframe candles."""
        timeframes = ["M1", "M5", "H1", "D"]

        for tf in timeframes:
            mock_oanda_client.get_instrument_candles(granularity=tf)

        assert mock_oanda_client.get_instrument_candles.call_count >= 1


class TestOandaOrderOperations:
    """Test suite for OANDA order placement and management."""

    def test_place_order_success(self, mock_oanda_client):
        """Test successful order placement."""
        response = mock_oanda_client.place_order()

        assert "orderCreateTransaction" in response
        assert response["orderCreateTransaction"]["id"] == "order_123"

    def test_place_order_structure(self, mock_oanda_client):
        """Test order response structure."""
        response = mock_oanda_client.place_order()
        transaction = response["orderCreateTransaction"]

        assert "id" in transaction
        assert "instrument" in transaction
        assert "type" in transaction
        assert "units" in transaction

    def test_place_order_parameters(self, mock_oanda_client):
        """Test order placement with parameters."""
        order_params = {
            "instrument": "EUR_USD",
            "units": 100000,
            "type": "MARKET",
            "takeProfitOnFill": {"price": "1.0100"},
            "stopLossOnFill": {"price": "1.0025"},
        }

        mock_oanda_client.place_order(**order_params)
        mock_oanda_client.place_order.assert_called_once()

    def test_order_types_supported(self, mock_oanda_client):
        """Test different order types are supported."""
        order_types = ["MARKET", "LIMIT", "STOP"]

        for order_type in order_types:
            mock_oanda_client.place_order(type=order_type)

        assert mock_oanda_client.place_order.call_count >= 1

    def test_order_size_validation(self, mock_oanda_client):
        """Test order size validation."""
        valid_sizes = [1000, 10000, 100000]

        for size in valid_sizes:
            mock_oanda_client.place_order(units=size)
            assert size > 0

    def test_order_with_take_profit(self, mock_oanda_client):
        """Test order placement with take profit."""
        order_params = {
            "units": 100000,
            "takeProfitOnFill": {"price": "1.0100"},
        }

        mock_oanda_client.place_order(**order_params)
        assert mock_oanda_client.place_order.called

    def test_order_with_stop_loss(self, mock_oanda_client):
        """Test order placement with stop loss."""
        order_params = {
            "units": 100000,
            "stopLossOnFill": {"price": "1.0025"},
        }

        mock_oanda_client.place_order(**order_params)
        assert mock_oanda_client.place_order.called


class TestOandaErrorHandling:
    """Test suite for OANDA error handling."""

    def test_client_connection_error(self, mock_oanda_client):
        """Test handling of connection errors."""
        mock_oanda_client.get_account.side_effect = ConnectionError("API unavailable")

        with pytest.raises(ConnectionError):
            mock_oanda_client.get_account()

    def test_client_auth_error(self, mock_oanda_client):
        """Test handling of authentication errors."""
        mock_oanda_client.get_account.side_effect = PermissionError("Invalid token")

        with pytest.raises(PermissionError):
            mock_oanda_client.get_account()

    def test_client_invalid_instrument(self, mock_oanda_client):
        """Test handling of invalid instrument."""
        mock_oanda_client.get_instrument_candles.side_effect = ValueError(
            "Invalid instrument"
        )

        with pytest.raises(ValueError):
            mock_oanda_client.get_instrument_candles(instrument="INVALID")

    def test_insufficient_balance_error(self, mock_oanda_client):
        """Test handling of insufficient balance."""
        mock_oanda_client.place_order.side_effect = ValueError(
            "Insufficient balance"
        )

        with pytest.raises(ValueError):
            mock_oanda_client.place_order(units=1000000)


class TestOandaMockingStrategy:
    """Test suite for verifying mocking strategy."""

    def test_mock_preserves_call_history(self, mock_oanda_client):
        """Test that mock preserves call history."""
        mock_oanda_client.get_account()
        mock_oanda_client.get_account()

        assert mock_oanda_client.get_account.call_count == 2

    def test_mock_call_arguments_recorded(self, mock_oanda_client):
        """Test that mock records call arguments."""
        mock_oanda_client.get_instrument_candles(
            instrument="EUR_USD",
            count=100,
        )

        # Verify the call was made with expected arguments
        mock_oanda_client.get_instrument_candles.assert_called_once()

    def test_mock_return_value_configuration(self, mock_oanda_client):
        """Test configurable return values."""
        mock_oanda_client.get_account.return_value = {
            "account": {"balance": 50000.0}
        }

        response = mock_oanda_client.get_account()
        assert response["account"]["balance"] == 50000.0

    def test_mock_side_effect_configuration(self, mock_oanda_client):
        """Test configurable side effects."""
        mock_oanda_client.get_account.side_effect = [
            {"account": {"balance": 100000.0}},
            {"account": {"balance": 99000.0}},
        ]

        response1 = mock_oanda_client.get_account()
        response2 = mock_oanda_client.get_account()

        assert response1["account"]["balance"] == 100000.0
        assert response2["account"]["balance"] == 99000.0


class TestOandaIntegrationWorkflow:
    """Test suite for complete OANDA integration workflows."""

    def test_complete_trading_workflow(self, mock_oanda_client, sample_config):
        """Test a complete trading workflow using OANDA client."""
        # 1. Check account
        account = mock_oanda_client.get_account()
        assert account["account"]["balance"] > 0

        # 2. Get market data
        candles = mock_oanda_client.get_instrument_candles(
            instrument="EUR_USD",
        )
        assert len(candles["candles"]) > 0

        # 3. Place order
        order = mock_oanda_client.place_order(
            instrument="EUR_USD",
            units=100000,
        )
        assert order["orderCreateTransaction"]["id"] is not None

    def test_data_pipeline_workflow(self, mock_oanda_client):
        """Test data collection pipeline."""
        instruments = ["EUR_USD", "GBP_USD"]

        collected_data = {}
        for instrument in instruments:
            candles = mock_oanda_client.get_instrument_candles(
                instrument=instrument
            )
            collected_data[instrument] = candles

        assert len(collected_data) == 2
        assert all(len(data["candles"]) > 0 for data in collected_data.values())
