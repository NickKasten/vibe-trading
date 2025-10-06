"""
Integration test for position deletion in complete trade cycles.
Validates that delete_position() is properly called when positions are closed.
"""

import pytest
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timezone
import pandas as pd
from backend.app.main import run_trading_cycle


class TestPositionDeletionIntegration:
    """Integration tests for position deletion in trade cycles."""

    @patch('backend.app.main.load_config')
    @patch('backend.app.main.DatabaseOperations')
    @patch('backend.app.main.fetch_ohlcv')
    @patch('backend.app.main.generate_signals')
    @patch('backend.app.main.calculate_position_size')
    @patch('backend.app.main.execute_trade')
    @patch('backend.app.main.update_trades')
    @patch('backend.app.main.update_positions')
    @patch('backend.app.main.update_equity')
    @patch('backend.app.main.update_signals')
    def test_complete_sell_calls_delete_position(
        self,
        mock_update_signals,
        mock_update_equity,
        mock_update_positions,
        mock_update_trades,
        mock_execute_trade,
        mock_calculate_position_size,
        mock_generate_signals,
        mock_fetch_ohlcv,
        mock_db_ops,
        mock_load_config
    ):
        """Test that selling all shares calls delete_position()."""

        # Setup configuration
        mock_load_config.return_value = {"STARTING_EQUITY": "100000"}

        # Setup database operations
        db_instance = MagicMock()
        mock_db_ops.return_value = db_instance

        # Create existing position with 10 shares
        existing_position = MagicMock()
        existing_position.symbol = 'AAPL'
        existing_position.quantity = 10.0
        existing_position.average_entry_price = 150.00

        db_instance.get_positions.return_value = [existing_position]
        db_instance.get_equity_history.return_value = [MagicMock(cash=50000)]

        # Setup delete_position to return True
        db_instance.delete_position.return_value = True

        # Mock market data
        mock_fetch_ohlcv.return_value = pd.DataFrame({
            'close': [155.0, 156.0, 157.0]
        })

        # Mock SELL signal
        mock_generate_signals.return_value = {
            'side': 'sell',
            'signal': -1,
            'strength': 0.8,
            'used_fallback': False
        }

        # Mock position sizing - sell all 10 shares
        mock_calculate_position_size.return_value = {
            'position_size': 10
        }

        # Mock trade execution - selling 10 shares (complete sale)
        mock_execute_trade.return_value = {
            'symbol': 'AAPL',
            'side': 'sell',
            'quantity': 10,  # Complete sale
            'price': 157.0,
            'timestamp': datetime.now(timezone.utc),
            'order_id': 'test_sell_order_123',
            'strategy': 'SMA_RSI'
        }

        # Run trading cycle
        run_trading_cycle('AAPL')

        # CRITICAL VERIFICATION: delete_position should be called
        db_instance.delete_position.assert_called_once_with('AAPL')

        # Verify update_positions was NOT called (position deleted instead)
        mock_update_positions.assert_not_called()

    @patch('backend.app.main.load_config')
    @patch('backend.app.main.DatabaseOperations')
    @patch('backend.app.main.fetch_ohlcv')
    @patch('backend.app.main.generate_signals')
    @patch('backend.app.main.calculate_position_size')
    @patch('backend.app.main.execute_trade')
    @patch('backend.app.main.update_trades')
    @patch('backend.app.main.update_positions')
    @patch('backend.app.main.update_equity')
    @patch('backend.app.main.update_signals')
    def test_partial_sell_does_not_delete_position(
        self,
        mock_update_signals,
        mock_update_equity,
        mock_update_positions,
        mock_update_trades,
        mock_execute_trade,
        mock_calculate_position_size,
        mock_generate_signals,
        mock_fetch_ohlcv,
        mock_db_ops,
        mock_load_config
    ):
        """Test that partial sell updates position but doesn't delete."""

        # Setup configuration
        mock_load_config.return_value = {"STARTING_EQUITY": "100000"}

        # Setup database operations
        db_instance = MagicMock()
        mock_db_ops.return_value = db_instance

        # Create existing position with 10 shares
        existing_position = MagicMock()
        existing_position.symbol = 'AAPL'
        existing_position.quantity = 10.0
        existing_position.average_entry_price = 150.00

        db_instance.get_positions.return_value = [existing_position]
        db_instance.get_equity_history.return_value = [MagicMock(cash=50000)]

        # Mock market data
        mock_fetch_ohlcv.return_value = pd.DataFrame({
            'close': [155.0, 156.0, 157.0]
        })

        # Mock SELL signal
        mock_generate_signals.return_value = {
            'side': 'sell',
            'signal': -1,
            'strength': 0.6,
            'used_fallback': False
        }

        # Mock position sizing - sell only 5 shares (partial)
        mock_calculate_position_size.return_value = {
            'position_size': 5
        }

        # Mock trade execution - selling 5 shares (partial sale)
        mock_execute_trade.return_value = {
            'symbol': 'AAPL',
            'side': 'sell',
            'quantity': 5,  # Partial sale
            'price': 157.0,
            'timestamp': datetime.now(timezone.utc),
            'order_id': 'test_partial_sell_123',
            'strategy': 'SMA_RSI'
        }

        # Run trading cycle
        run_trading_cycle('AAPL')

        # CRITICAL VERIFICATION: delete_position should NOT be called
        db_instance.delete_position.assert_not_called()

        # Verify update_positions WAS called (position updated, not deleted)
        mock_update_positions.assert_called_once()

        # Verify the position was updated with correct remaining quantity
        call_args = mock_update_positions.call_args[0][0]
        assert call_args['quantity'] == 5.0  # 10 - 5 = 5 remaining
        assert call_args['average_entry_price'] == 150.00  # Unchanged

    @patch('backend.app.main.load_config')
    @patch('backend.app.main.DatabaseOperations')
    @patch('backend.app.main.fetch_ohlcv')
    @patch('backend.app.main.generate_signals')
    @patch('backend.app.main.calculate_position_size')
    @patch('backend.app.main.execute_trade')
    @patch('backend.app.main.update_trades')
    @patch('backend.app.main.update_positions')
    @patch('backend.app.main.update_equity')
    @patch('backend.app.main.update_signals')
    def test_delete_position_failure_logged_but_not_fatal(
        self,
        mock_update_signals,
        mock_update_equity,
        mock_update_positions,
        mock_update_trades,
        mock_execute_trade,
        mock_calculate_position_size,
        mock_generate_signals,
        mock_fetch_ohlcv,
        mock_db_ops,
        mock_load_config
    ):
        """Test that delete_position failure is logged but doesn't crash cycle."""

        # Setup configuration
        mock_load_config.return_value = {"STARTING_EQUITY": "100000"}

        # Setup database operations
        db_instance = MagicMock()
        mock_db_ops.return_value = db_instance

        # Create existing position
        existing_position = MagicMock()
        existing_position.symbol = 'AAPL'
        existing_position.quantity = 10.0
        existing_position.average_entry_price = 150.00

        db_instance.get_positions.return_value = [existing_position]
        db_instance.get_equity_history.return_value = [MagicMock(cash=50000)]

        # Setup delete_position to return False (failure)
        db_instance.delete_position.return_value = False

        # Mock market data
        mock_fetch_ohlcv.return_value = pd.DataFrame({
            'close': [155.0, 156.0, 157.0]
        })

        # Mock SELL signal
        mock_generate_signals.return_value = {
            'side': 'sell',
            'signal': -1,
            'strength': 0.8,
            'used_fallback': False
        }

        # Mock position sizing - sell all shares
        mock_calculate_position_size.return_value = {
            'position_size': 10
        }

        # Mock trade execution
        mock_execute_trade.return_value = {
            'symbol': 'AAPL',
            'side': 'sell',
            'quantity': 10,
            'price': 157.0,
            'timestamp': datetime.now(timezone.utc),
            'order_id': 'test_sell_fail_123',
            'strategy': 'SMA_RSI'
        }

        # Run trading cycle - should NOT raise exception
        run_trading_cycle('AAPL')

        # Verify delete_position was called despite failure
        db_instance.delete_position.assert_called_once_with('AAPL')

        # Verify equity was still updated (trading cycle continued)
        mock_update_equity.assert_called_once()

    @patch('backend.app.main.load_config')
    @patch('backend.app.main.DatabaseOperations')
    @patch('backend.app.main.fetch_ohlcv')
    @patch('backend.app.main.generate_signals')
    @patch('backend.app.main.calculate_position_size')
    @patch('backend.app.main.execute_trade')
    @patch('backend.app.main.update_trades')
    @patch('backend.app.main.update_positions')
    @patch('backend.app.main.update_equity')
    @patch('backend.app.main.update_signals')
    def test_buy_trade_creates_position(
        self,
        mock_update_signals,
        mock_update_equity,
        mock_update_positions,
        mock_update_trades,
        mock_execute_trade,
        mock_calculate_position_size,
        mock_generate_signals,
        mock_fetch_ohlcv,
        mock_db_ops,
        mock_load_config
    ):
        """Test that BUY trade creates/updates position (never deletes)."""

        # Setup configuration
        mock_load_config.return_value = {"STARTING_EQUITY": "100000"}

        # Setup database operations
        db_instance = MagicMock()
        mock_db_ops.return_value = db_instance

        # No existing position
        db_instance.get_positions.return_value = []
        db_instance.get_equity_history.return_value = [MagicMock(cash=50000)]

        # Mock market data
        mock_fetch_ohlcv.return_value = pd.DataFrame({
            'close': [150.0, 151.0, 152.0]
        })

        # Mock BUY signal
        mock_generate_signals.return_value = {
            'side': 'buy',
            'signal': 1,
            'strength': 0.8,
            'used_fallback': False
        }

        # Mock position sizing
        mock_calculate_position_size.return_value = {
            'position_size': 10
        }

        # Mock trade execution
        mock_execute_trade.return_value = {
            'symbol': 'AAPL',
            'side': 'buy',
            'quantity': 10,
            'price': 152.0,
            'timestamp': datetime.now(timezone.utc),
            'order_id': 'test_buy_123',
            'strategy': 'SMA_RSI'
        }

        # Run trading cycle
        run_trading_cycle('AAPL')

        # CRITICAL VERIFICATION: delete_position should NEVER be called for BUY
        db_instance.delete_position.assert_not_called()

        # Verify update_positions WAS called (position created)
        mock_update_positions.assert_called_once()

        # Verify the position was created with correct data
        call_args = mock_update_positions.call_args[0][0]
        assert call_args['symbol'] == 'AAPL'
        assert call_args['quantity'] == 10.0
        assert call_args['average_entry_price'] == 152.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
