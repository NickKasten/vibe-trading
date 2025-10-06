"""
Tests for execute_trade() with simulate=False (real Alpaca API path).
Tests the untested code path for actual API calls and TRADING_MODE handling.
"""

import pytest
from unittest.mock import patch, MagicMock
import requests
from datetime import datetime, timezone
from backend.app.services.broker.paper import (
    execute_trade,
    OrderValidationError,
    get_order_status,
    validate_api_credentials,
    validate_order_inputs
)


class TestExecuteTradeSimulateFalse:
    """Test suite for execute_trade() with simulate=False - untested code path."""

    @patch('backend.app.services.broker.paper.requests.post')
    @patch('backend.app.services.broker.paper.validate_api_credentials')
    def test_execute_trade_real_api_success(self, mock_validate_creds, mock_requests_post):
        """Test execute_trade with simulate=False successfully calls Alpaca API."""
        # Setup mocks
        mock_validate_creds.return_value = (True, '')

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'real_order_12345',
            'status': 'filled',
            'filled_avg_price': '152.50',
            'created_at': '2024-01-15T10:30:00Z',
            'symbol': 'AAPL',
            'qty': 10,
            'side': 'buy'
        }
        mock_requests_post.return_value = mock_response

        # Execute trade with simulate=False
        result = execute_trade(10, symbol='AAPL', side='buy', simulate=False)

        # Verify API was called with correct parameters
        mock_requests_post.assert_called_once()
        call_args = mock_requests_post.call_args

        # Check URL
        assert call_args[0][0] == "https://paper-api.alpaca.markets/v2/orders"

        # Check request body
        request_body = call_args[1]['json']
        assert request_body['symbol'] == 'AAPL'
        assert request_body['qty'] == 10
        assert request_body['side'] == 'buy'
        assert request_body['type'] == 'market'
        assert request_body['time_in_force'] == 'day'

        # Verify result
        assert result['symbol'] == 'AAPL'
        assert result['quantity'] == 10
        assert result['side'] == 'buy'
        assert result['order_id'] == 'real_order_12345'
        assert result['simulated'] is False
        assert 'price' in result

    @patch('backend.app.services.broker.paper.requests.post')
    @patch('backend.app.services.broker.paper.validate_api_credentials')
    def test_execute_trade_real_api_201_response(self, mock_validate_creds, mock_requests_post):
        """Test execute_trade handles 201 Created response (alternative success code)."""
        mock_validate_creds.return_value = (True, '')

        mock_response = MagicMock()
        mock_response.status_code = 201  # Alternative success code
        mock_response.json.return_value = {
            'id': 'order_201_test',
            'status': 'accepted',
            'created_at': '2024-01-15T10:30:00Z'
        }
        mock_requests_post.return_value = mock_response

        result = execute_trade(5, symbol='MSFT', side='sell', simulate=False)

        assert result is not None
        assert result['order_id'] == 'order_201_test'
        assert result['simulated'] is False

    @patch('backend.app.services.broker.paper.requests.post')
    @patch('backend.app.services.broker.paper.validate_api_credentials')
    def test_execute_trade_real_api_failure_4xx(self, mock_validate_creds, mock_requests_post):
        """Test execute_trade handles 400-level API errors."""
        mock_validate_creds.return_value = (True, '')

        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.text = "Unprocessable Entity: Invalid order"
        mock_requests_post.return_value = mock_response

        # Should raise OrderValidationError
        with pytest.raises(OrderValidationError) as exc_info:
            execute_trade(10, symbol='INVALID', side='buy', simulate=False)

        assert "Failed to place order" in str(exc_info.value)

    @patch('backend.app.services.broker.paper.requests.post')
    @patch('backend.app.services.broker.paper.validate_api_credentials')
    def test_execute_trade_real_api_timeout(self, mock_validate_creds, mock_requests_post):
        """Test execute_trade handles timeout errors."""
        mock_validate_creds.return_value = (True, '')

        # Simulate timeout
        mock_requests_post.side_effect = requests.Timeout("Request timed out")

        # Should raise OrderValidationError with timeout message
        with pytest.raises(OrderValidationError) as exc_info:
            execute_trade(10, symbol='AAPL', side='buy', simulate=False)

        assert "timed out" in str(exc_info.value).lower()

    @patch('backend.app.services.broker.paper.requests.post')
    @patch('backend.app.services.broker.paper.validate_api_credentials')
    def test_execute_trade_real_api_network_error(self, mock_validate_creds, mock_requests_post):
        """Test execute_trade handles network errors."""
        mock_validate_creds.return_value = (True, '')

        # Simulate network error
        mock_requests_post.side_effect = requests.RequestException("Network unreachable")

        with pytest.raises(OrderValidationError) as exc_info:
            execute_trade(10, symbol='AAPL', side='buy', simulate=False)

        assert "Network error" in str(exc_info.value)

    @patch('backend.app.services.broker.paper.requests.post')
    @patch('backend.app.services.broker.paper.validate_api_credentials')
    def test_execute_trade_real_api_missing_filled_price(self, mock_validate_creds, mock_requests_post):
        """Test execute_trade handles orders with missing filled_avg_price."""
        mock_validate_creds.return_value = (True, '')

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'order_no_price',
            'status': 'accepted',
            'created_at': '2024-01-15T10:30:00Z'
            # No filled_avg_price or limit_price
        }
        mock_requests_post.return_value = mock_response

        result = execute_trade(10, symbol='AAPL', side='buy', simulate=False)

        # Should use simulated fallback price
        assert result is not None
        assert 'price' in result
        assert isinstance(result['price'], float)
        assert result['price'] > 0

    @patch('backend.app.services.broker.paper.requests.post')
    @patch('backend.app.services.broker.paper.validate_api_credentials')
    def test_execute_trade_real_api_includes_timeout_param(self, mock_validate_creds, mock_requests_post):
        """Test that API request includes timeout parameter."""
        mock_validate_creds.return_value = (True, '')

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'test_order',
            'status': 'filled',
            'created_at': '2024-01-15T10:30:00Z'
        }
        mock_requests_post.return_value = mock_response

        execute_trade(10, symbol='AAPL', side='buy', simulate=False)

        # Verify timeout was set
        call_kwargs = mock_requests_post.call_args[1]
        assert 'timeout' in call_kwargs
        assert call_kwargs['timeout'] == 10


class TestOrderValidation:
    """Test order validation logic."""

    def test_validate_order_inputs_valid(self):
        """Test validation passes for valid inputs."""
        is_valid, error = validate_order_inputs(10, 'AAPL', 'buy')
        assert is_valid is True
        assert error == ''

    def test_validate_order_inputs_invalid_position_size_zero(self):
        """Test validation fails for zero position size."""
        is_valid, error = validate_order_inputs(0, 'AAPL', 'buy')
        assert is_valid is False
        assert "positive integer" in error

    def test_validate_order_inputs_invalid_position_size_negative(self):
        """Test validation fails for negative position size."""
        is_valid, error = validate_order_inputs(-5, 'AAPL', 'buy')
        assert is_valid is False
        assert "positive integer" in error

    def test_validate_order_inputs_invalid_symbol_empty(self):
        """Test validation fails for empty symbol."""
        is_valid, error = validate_order_inputs(10, '', 'buy')
        assert is_valid is False
        assert "Invalid symbol" in error

    def test_validate_order_inputs_invalid_side(self):
        """Test validation fails for invalid side."""
        is_valid, error = validate_order_inputs(10, 'AAPL', 'hold')
        assert is_valid is False
        assert "Invalid order side" in error

    def test_validate_order_inputs_oversized_position(self):
        """Test validation fails for unrealistic position sizes."""
        is_valid, error = validate_order_inputs(15000, 'AAPL', 'buy')
        assert is_valid is False
        assert "exceeds reasonable limit" in error

    def test_validate_api_credentials_missing(self):
        """Test API credential validation fails when missing."""
        with patch('backend.app.services.broker.paper.ALPACA_API_KEY', None):
            is_valid, error = validate_api_credentials()
            assert is_valid is False
            assert "Missing API credentials" in error

    def test_validate_api_credentials_present(self):
        """Test API credential validation passes when present."""
        with patch('backend.app.services.broker.paper.ALPACA_API_KEY', 'test_key'), \
             patch('backend.app.services.broker.paper.ALPACA_SECRET_KEY', 'test_secret'):
            is_valid, error = validate_api_credentials()
            assert is_valid is True
            assert error == ''


class TestGetOrderStatus:
    """Test get_order_status() function - untested code path."""

    @patch('backend.app.services.broker.paper.requests.get')
    def test_get_order_status_success(self, mock_requests_get):
        """Test successful order status retrieval."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'order_123',
            'status': 'filled',
            'filled_qty': 10
        }
        mock_requests_get.return_value = mock_response

        result = get_order_status('order_123')

        assert result is not None
        assert result['id'] == 'order_123'
        assert result['status'] == 'filled'
        mock_requests_get.assert_called_once()

    @patch('backend.app.services.broker.paper.requests.get')
    def test_get_order_status_not_found(self, mock_requests_get):
        """Test order status returns None for 404."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Order not found"
        mock_requests_get.return_value = mock_response

        result = get_order_status('invalid_order')

        assert result is None

    @patch('backend.app.services.broker.paper.requests.get')
    def test_get_order_status_exception(self, mock_requests_get):
        """Test order status handles exceptions gracefully."""
        mock_requests_get.side_effect = Exception("Network error")

        result = get_order_status('order_123')

        assert result is None


class TestSimulateTrue:
    """Test execute_trade with simulate=True path (existing but verify coverage)."""

    @patch('backend.app.services.broker.paper.validate_api_credentials')
    def test_execute_trade_simulate_true_bypass_api(self, mock_validate_creds):
        """Test that simulate=True bypasses API calls entirely."""
        mock_validate_creds.return_value = (True, '')

        # No need to mock requests - it shouldn't be called
        with patch('backend.app.services.broker.paper.requests.post') as mock_post:
            result = execute_trade(10, symbol='AAPL', side='buy', simulate=True)

            # Verify API was NOT called
            mock_post.assert_not_called()

            # Verify simulated trade
            assert result is not None
            assert result['simulated'] is True
            assert result['symbol'] == 'AAPL'
            assert result['quantity'] == 10
            assert 'order_id' in result

    @patch('backend.app.services.broker.paper.validate_api_credentials')
    def test_execute_trade_simulate_true_validation_still_runs(self, mock_validate_creds):
        """Test that validation runs even in simulate mode."""
        mock_validate_creds.return_value = (False, 'Missing API credentials')

        # Should still raise validation error even in simulate mode
        with pytest.raises(OrderValidationError):
            execute_trade(10, symbol='AAPL', side='buy', simulate=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
