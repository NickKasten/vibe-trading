"""
Test suite for the paper broker module to verify real price usage.
Tests the fix for the simulate_fill_price bug where random prices were used.
"""
import pytest
from unittest.mock import patch
from backend.app.services.broker.paper import execute_trade, clear_trade_log, OrderValidationError


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Clear trade log before and after each test"""
    clear_trade_log()
    yield
    clear_trade_log()


@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment variables for testing"""
    monkeypatch.setenv("ALPACA_API_KEY", "test_key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "test_secret")


class TestExecuteTradeWithRealPrice:
    """Test suite for execute_trade with real market prices"""

    def test_simulated_trade_uses_current_price(self, mock_env):
        """Test that simulated trades use the provided current_price"""
        # Given: A real market price for AAPL
        real_price = 178.50
        position_size = 10

        # When: We execute a simulated trade with current_price
        trade_result = execute_trade(
            position_size=position_size,
            symbol="AAPL",
            side="buy",
            simulate=True,
            current_price=real_price
        )

        # Then: The trade should use the exact real price
        assert trade_result is not None
        assert trade_result['price'] == real_price
        assert trade_result['symbol'] == "AAPL"
        assert trade_result['quantity'] == position_size
        assert trade_result['side'] == "buy"
        assert trade_result['status'] == 'completed'
        assert trade_result['simulated'] is True

        # And: Price should NOT be in the old random range (100-110)
        # unless by coincidence, which is tested by exact equality above

    def test_simulated_trade_multiple_prices(self, mock_env):
        """Test that different stocks use their respective real prices"""
        test_cases = [
            ("AAPL", 178.50),
            ("MSFT", 420.75),
            ("GOOGL", 142.30),
            ("TSLA", 250.00),
        ]

        for symbol, real_price in test_cases:
            # Clear log between iterations
            clear_trade_log()

            # When: We execute a simulated trade
            trade_result = execute_trade(
                position_size=5,
                symbol=symbol,
                side="buy",
                simulate=True,
                current_price=real_price
            )

            # Then: Each trade should use its specific real price
            assert trade_result['price'] == real_price, f"Failed for {symbol}"
            assert trade_result['symbol'] == symbol

    def test_simulated_trade_without_current_price_uses_fallback(self, mock_env):
        """Test backward compatibility: without current_price, uses fallback"""
        # When: We execute a simulated trade WITHOUT current_price
        trade_result = execute_trade(
            position_size=10,
            symbol="AAPL",
            side="buy",
            simulate=True
            # Note: current_price NOT provided
        )

        # Then: The trade should use fallback price (random 100-110)
        assert trade_result is not None
        assert 100 <= trade_result['price'] <= 110
        assert trade_result['simulated'] is True

    def test_simulated_sell_trade_uses_current_price(self, mock_env):
        """Test that SELL trades also use real prices"""
        real_price = 225.80

        # When: We execute a simulated SELL trade
        trade_result = execute_trade(
            position_size=15,
            symbol="JNJ",
            side="sell",
            simulate=True,
            current_price=real_price
        )

        # Then: The trade should use the exact real price
        assert trade_result['price'] == real_price
        assert trade_result['side'] == "sell"

    def test_invalid_current_price_raises_error(self, mock_env):
        """Test that invalid current_price values are rejected"""
        invalid_prices = [-10, 0, -0.01, 10001, 99999]

        for invalid_price in invalid_prices:
            with pytest.raises(OrderValidationError, match="Invalid current_price"):
                execute_trade(
                    position_size=10,
                    symbol="AAPL",
                    side="buy",
                    simulate=True,
                    current_price=invalid_price
                )

    def test_edge_case_prices_are_accepted(self, mock_env):
        """Test that edge case but valid prices are accepted"""
        valid_edge_cases = [0.01, 1.00, 9999.99]

        for price in valid_edge_cases:
            clear_trade_log()

            trade_result = execute_trade(
                position_size=1,
                symbol="TEST",
                side="buy",
                simulate=True,
                current_price=price
            )

            assert trade_result['price'] == price

    def test_price_validation_with_realistic_stock_prices(self, mock_env):
        """Test with realistic stock prices from different price ranges"""
        realistic_prices = {
            "AAPL": 178.50,    # Tech stock
            "GOOGL": 142.30,   # Post-split tech
            "BRK.A": 599000,   # Very expensive stock (should fail validation)
            "PENNY": 0.50,     # Penny stock
            "SPY": 450.25,     # ETF
        }

        for symbol, price in realistic_prices.items():
            clear_trade_log()

            if price > 10000:
                # Should fail validation
                with pytest.raises(OrderValidationError):
                    execute_trade(
                        position_size=1,
                        symbol=symbol,
                        side="buy",
                        simulate=True,
                        current_price=price
                    )
            else:
                # Should succeed
                trade_result = execute_trade(
                    position_size=1,
                    symbol=symbol,
                    side="buy",
                    simulate=True,
                    current_price=price
                )
                assert trade_result['price'] == price

    def test_trade_preserves_all_fields(self, mock_env):
        """Test that the trade result contains all required fields"""
        real_price = 155.75

        trade_result = execute_trade(
            position_size=20,
            symbol="UNH",
            side="buy",
            simulate=True,
            current_price=real_price
        )

        # Verify all required fields are present
        required_fields = ['symbol', 'side', 'quantity', 'status', 'order_id',
                          'price', 'timestamp', 'strategy', 'simulated']
        for field in required_fields:
            assert field in trade_result, f"Missing field: {field}"

        # Verify field values
        assert trade_result['symbol'] == "UNH"
        assert trade_result['side'] == "buy"
        assert trade_result['quantity'] == 20
        assert trade_result['status'] == 'completed'
        assert trade_result['price'] == real_price
        assert trade_result['strategy'] == 'SMA_RSI'
        assert trade_result['simulated'] is True
        assert trade_result['order_id'].startswith('sim-')


class TestBackwardCompatibility:
    """Test backward compatibility with existing code"""

    def test_execute_trade_without_current_price_still_works(self, mock_env):
        """Ensure old code without current_price parameter still works"""
        # This simulates old code that doesn't pass current_price
        trade_result = execute_trade(
            position_size=10,
            symbol="AAPL",
            side="buy",
            simulate=True
        )

        assert trade_result is not None
        assert trade_result['symbol'] == "AAPL"
        assert trade_result['simulated'] is True
        # Should use fallback price
        assert 100 <= trade_result['price'] <= 110

    def test_alpaca_mode_ignores_current_price(self, mock_env):
        """Test that non-simulate mode doesn't break with current_price"""
        with patch('backend.app.services.broker.paper.requests.post') as mock_post:
            # Mock successful Alpaca API response
            mock_post.return_value.status_code = 201
            mock_post.return_value.json.return_value = {
                'id': 'alpaca-order-123',
                'status': 'filled',
                'filled_avg_price': 180.50,
                'created_at': '2024-01-01T12:00:00Z'
            }

            # When: We call execute_trade with simulate=False and current_price
            trade_result = execute_trade(
                position_size=10,
                symbol="AAPL",
                side="buy",
                simulate=False,
                current_price=178.50  # This should be ignored in non-simulate mode
            )

            # Then: It should use Alpaca's filled_avg_price
            assert trade_result is not None
            assert trade_result['price'] == 180.50  # From Alpaca, not current_price
            assert trade_result['simulated'] is False


class TestPriceLogging:
    """Test that price usage is properly logged"""

    def test_logs_real_price_usage(self, mock_env, caplog):
        """Test that using real price generates appropriate log"""
        import logging
        caplog.set_level(logging.INFO)

        execute_trade(
            position_size=10,
            symbol="AAPL",
            side="buy",
            simulate=True,
            current_price=175.50
        )

        # Check that log contains message about using real price
        assert "Using real market price for simulation" in caplog.text
        assert "$175.50" in caplog.text

    def test_logs_fallback_warning(self, mock_env, caplog):
        """Test that fallback to random price generates warning"""
        import logging
        caplog.set_level(logging.WARNING)

        execute_trade(
            position_size=10,
            symbol="AAPL",
            side="buy",
            simulate=True
            # No current_price provided
        )

        # Check that log contains warning about fallback
        assert "No current_price provided" in caplog.text
        assert "Using fallback price" in caplog.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
