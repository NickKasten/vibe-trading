"""
Comprehensive tests for the main trading cycle functionality.
Tests the core trading logic from backend/app/main.py
"""

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime, timezone, timedelta
import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.app.main import run_trading_cycle, setup_application


class TestTradingCycle:
    """Test suite for main trading cycle functionality."""
    
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
    def test_successful_buy_trade_cycle(self, mock_update_signals, mock_update_equity, 
                                       mock_update_positions, mock_update_trades, 
                                       mock_execute_trade, mock_calculate_position_size,
                                       mock_generate_signals, mock_fetch_ohlcv, 
                                       mock_db_ops, mock_load_config):
        """Test complete successful trading cycle with BUY signal."""
        
        # Setup mocks
        mock_load_config.return_value = {"STARTING_EQUITY": "100000"}
        
        # Mock database operations
        db_instance = MagicMock()
        mock_db_ops.return_value = db_instance
        db_instance.get_recent_trades.return_value = []  # No recent trades
        db_instance.get_positions.return_value = []  # No existing positions
        db_instance.get_equity_history.return_value = [MagicMock(cash=50000)]
        
        # Mock market data
        sample_data = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [105, 106, 107],
            'low': [95, 96, 97],
            'close': [102, 103, 104],
            'volume': [1000000, 1100000, 1200000]
        })
        mock_fetch_ohlcv.return_value = sample_data
        
        # Mock trading signals
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
            'price': 104.0,
            'timestamp': datetime.now(timezone.utc),
            'order_id': 'test_order_123',
            'strategy': 'SMA_RSI'
        }
        
        # Run trading cycle
        run_trading_cycle('AAPL')
        
        # Verify all components were called
        mock_fetch_ohlcv.assert_called_once_with('AAPL')
        mock_generate_signals.assert_called_once()
        mock_calculate_position_size.assert_called_once()
        mock_execute_trade.assert_called_once_with(10, symbol='AAPL', side='buy', simulate=True, current_price=104.0)
        mock_update_trades.assert_called_once()
        mock_update_positions.assert_called_once()
        mock_update_equity.assert_called_once()
        mock_update_signals.assert_called_once()
    
    @patch('backend.app.main.update_signals')
    @patch('backend.app.main.update_equity')
    @patch('backend.app.main.update_positions')
    @patch('backend.app.main.update_trades')
    @patch('backend.app.main.execute_trade')
    @patch('backend.app.main.calculate_position_size')
    @patch('backend.app.main.generate_signals')
    @patch('backend.app.main.fetch_ohlcv')
    @patch('backend.app.main.DatabaseOperations')
    @patch('backend.app.main.load_config')
    def test_continues_when_recent_trade_exists(self, mock_load_config, mock_db_ops, mock_fetch_ohlcv,
                                                mock_generate_signals, mock_calculate_position_size,
                                                mock_execute_trade, mock_update_trades,
                                                mock_update_positions, mock_update_equity,
                                                mock_update_signals):
        """Trading cycle should still run even if a trade already occurred today."""

        mock_load_config.return_value = {"STARTING_EQUITY": "100000"}

        mock_trade = MagicMock()
        mock_trade.timestamp = datetime.now(timezone.utc)
        mock_trade.side = 'buy'
        mock_trade.quantity = 5
        mock_trade.price = 100.0

        db_instance = MagicMock()
        mock_db_ops.return_value = db_instance
        db_instance.get_recent_trades.return_value = [mock_trade]
        db_instance.get_positions.return_value = []
        db_instance.get_equity_history.return_value = []

        mock_fetch_ohlcv.return_value = pd.DataFrame({'close': [100, 101, 102]})
        mock_generate_signals.return_value = {'side': 'hold', 'signal': 0, 'strength': 0.4}
        mock_calculate_position_size.return_value = None

        run_trading_cycle('AAPL')

        mock_fetch_ohlcv.assert_called_once_with('AAPL')
        mock_generate_signals.assert_called_once()
        mock_calculate_position_size.assert_called_once()
    
    @patch('backend.app.main.load_config')
    @patch('backend.app.main.DatabaseOperations')
    @patch('backend.app.main.fetch_ohlcv')
    def test_skip_when_no_market_data(self, mock_fetch_ohlcv, mock_db_ops, mock_load_config):
        """Test that trading cycle is skipped when no market data is available."""
        
        # Setup mocks
        mock_load_config.return_value = {"STARTING_EQUITY": "100000"}
        
        db_instance = MagicMock()
        mock_db_ops.return_value = db_instance
        db_instance.get_recent_trades.return_value = []  # No recent trades
        
        # Mock empty market data
        mock_fetch_ohlcv.return_value = None
        
        # Run trading cycle
        run_trading_cycle('AAPL')
        
        # Verify fetch was attempted but cycle stopped
        mock_fetch_ohlcv.assert_called_once_with('AAPL')
    
    @patch('backend.app.main.load_config')
    @patch('backend.app.main.DatabaseOperations')
    @patch('backend.app.main.fetch_ohlcv')
    @patch('backend.app.main.generate_signals')
    def test_skip_when_hold_signal(self, mock_generate_signals, mock_fetch_ohlcv, mock_db_ops, mock_load_config):
        """Test that trading cycle completes but no trade when HOLD signal."""
        
        # Setup mocks
        mock_load_config.return_value = {"STARTING_EQUITY": "100000"}
        
        db_instance = MagicMock()
        mock_db_ops.return_value = db_instance
        db_instance.get_recent_trades.return_value = []
        db_instance.get_positions.return_value = []
        
        # Mock market data
        sample_data = pd.DataFrame({
            'close': [102, 103, 104]
        })
        mock_fetch_ohlcv.return_value = sample_data
        
        # Mock HOLD signal
        mock_generate_signals.return_value = {
            'side': 'hold',
            'signal': 0,
            'strength': 0.3
        }
        
        # Run trading cycle
        run_trading_cycle('AAPL')
        
        # Verify signals were generated but no further action
        mock_generate_signals.assert_called_once()


class TestApplicationSetup:
    """Test application initialization."""
    
    @patch('backend.app.main.load_config')
    @patch('backend.app.main.init_database')
    def test_successful_setup(self, mock_init_db, mock_load_config):
        """Test successful application setup."""
        
        mock_load_config.return_value = {"TEST_MODE": True}
        mock_init_db.return_value = True
        
        result = setup_application()
        
        assert result is not None
        mock_load_config.assert_called_once()
        mock_init_db.assert_called_once()
    
    @patch('backend.app.main.load_config')
    @patch('backend.app.main.init_database')
    def test_setup_fails_on_db_init_error(self, mock_init_db, mock_load_config):
        """Test application setup fails when database initialization fails."""
        
        mock_load_config.return_value = {"TEST_MODE": True}
        mock_init_db.return_value = False  # Database init fails
        
        with pytest.raises(SystemExit):
            setup_application()


class TestPositionManagement:
    """Test position and equity calculations in trading cycle."""
    
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
    def test_sell_validation_prevents_invalid_sell(self, mock_update_signals, mock_update_equity,
                                                   mock_update_positions, mock_update_trades,
                                                   mock_execute_trade, mock_calculate_position_size,
                                                   mock_generate_signals, mock_fetch_ohlcv,
                                                   mock_db_ops, mock_load_config):
        """Test that SELL signal is prevented when no position exists."""
        
        # Setup mocks
        mock_load_config.return_value = {"STARTING_EQUITY": "100000"}
        
        db_instance = MagicMock()
        mock_db_ops.return_value = db_instance
        db_instance.get_recent_trades.return_value = []
        db_instance.get_positions.return_value = []  # No existing positions
        
        # Mock market data
        sample_data = pd.DataFrame({'close': [102, 103, 104]})
        mock_fetch_ohlcv.return_value = sample_data
        
        # Mock SELL signal
        mock_generate_signals.return_value = {
            'side': 'sell',
            'signal': -1,
            'strength': 0.7
        }
        
        mock_calculate_position_size.return_value = {'position_size': 10}
        
        # Run trading cycle
        run_trading_cycle('AAPL')
        
        # Verify that execute_trade was NOT called (invalid sell prevented)
        mock_execute_trade.assert_not_called()
        mock_update_trades.assert_not_called()


class TestErrorHandling:
    """Test error handling in trading cycle."""
    
    @patch('backend.app.main.load_config')
    @patch('backend.app.main.DatabaseOperations')
    @patch('backend.app.main.fetch_ohlcv')
    def test_handles_fetch_exception(self, mock_fetch_ohlcv, mock_db_ops, mock_load_config):
        """Test graceful handling of market data fetch exceptions."""
        
        mock_load_config.return_value = {"STARTING_EQUITY": "100000"}
        
        db_instance = MagicMock()
        mock_db_ops.return_value = db_instance
        db_instance.get_recent_trades.return_value = []
        
        # Mock fetch exception
        mock_fetch_ohlcv.side_effect = Exception("API error")
        
        # Should not raise exception, should handle gracefully
        run_trading_cycle('AAPL')
        
        mock_fetch_ohlcv.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
