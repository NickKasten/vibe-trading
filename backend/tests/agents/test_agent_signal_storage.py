"""
Signal Storage Agent Tests

This agent validates that signals are correctly stored to and retrieved from the database,
including all technical indicators.

Test Coverage:
- Signal insertion from bot
- Signal retrieval by API
- Freshness filtering (< 15 min)
- Multiple symbol handling
- Technical indicator storage (SMA, RSI)
- Signal validation
"""
import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import patch, MagicMock
import pandas as pd
from backend.app.db.supabase import validate_signal_data, update_signals
from backend.app.main import run_trading_cycle


class TestSignalValidation:
    """Validate signal data validation logic."""

    def test_valid_signal_data_passes_validation(self):
        """Test that valid signal data passes validation."""
        signal_data = {
            'symbol': 'AAPL',
            'signal_type': 'buy',
            'strength': 0.75,
            'strategy': 'SMA_RSI',
            'price': 150.0,
            'sma_20': 148.0,
            'sma_50': 145.0,
            'rsi': 65.0
        }

        assert validate_signal_data(signal_data) is True

    def test_missing_required_field_fails_validation(self):
        """Test that missing required fields fail validation."""
        signal_data = {
            'symbol': 'AAPL',
            # Missing signal_type
            'strength': 0.75,
            'strategy': 'SMA_RSI',
            'price': 150.0
        }

        assert validate_signal_data(signal_data) is False

    def test_invalid_rsi_range_fails_validation(self):
        """Test that RSI outside valid range (0-100) fails validation."""
        signal_data = {
            'symbol': 'AAPL',
            'signal_type': 'buy',
            'strength': 0.75,
            'strategy': 'SMA_RSI',
            'price': 150.0,
            'rsi': 150.0  # Invalid - must be 0-100
        }

        assert validate_signal_data(signal_data) is False

    def test_valid_rsi_passes_validation(self):
        """Test that valid RSI values pass validation."""
        for rsi_value in [0, 30, 50, 70, 100]:
            signal_data = {
                'symbol': 'AAPL',
                'signal_type': 'buy',
                'strength': 0.75,
                'strategy': 'SMA_RSI',
                'price': 150.0,
                'rsi': rsi_value
            }
            assert validate_signal_data(signal_data) is True


class TestSignalStorageFromBot:
    """Validate that the bot correctly stores signals with technical indicators."""

    @patch('backend.app.main.fetch_ohlcv')
    @patch('backend.app.main.update_signals')
    @patch('backend.app.main.DatabaseOperations')
    @patch('backend.app.main.load_config')
    def test_bot_stores_signal_with_technical_indicators(
        self,
        mock_config,
        mock_db_ops,
        mock_update_signals,
        mock_fetch
    ):
        """Test that trading bot stores signals with SMA and RSI values."""
        # Setup mocks
        mock_config.return_value = {
            'STARTING_EQUITY': 100000,
            'TRADING_MODE': 'simulate'
        }

        # Create mock OHLCV data with technical indicators
        mock_data = pd.DataFrame({
            'close': [150.0, 151.0, 152.0],
            'open': [149.0, 150.0, 151.0],
            'high': [152.0, 153.0, 154.0],
            'low': [148.0, 149.0, 150.0],
            'volume': [1000000, 1100000, 1200000],
            'SMA20': [148.0, 148.5, 149.0],
            'SMA50': [145.0, 145.5, 146.0],
            'RSI': [65.0, 66.0, 67.0]
        }, index=pd.date_range(start='2025-01-01', periods=3))

        mock_fetch.return_value = mock_data

        # Mock database operations
        mock_db = MagicMock()
        mock_db.get_positions.return_value = []
        mock_db_ops.return_value = mock_db

        # Mock signal generation to return signal with data
        with patch('backend.app.main.generate_signals') as mock_gen_signals:
            mock_gen_signals.return_value = {
                'side': 'buy',
                'signal': 1,
                'strength': 0.75,
                'data': mock_data
            }

            with patch('backend.app.main.calculate_position_size') as mock_calc_pos:
                mock_calc_pos.return_value = None  # HOLD signal

                # Run trading cycle
                run_trading_cycle("AAPL")

                # Verify update_signals was called
                assert mock_update_signals.called

                # Get the signal data that was passed
                signal_data = mock_update_signals.call_args[0][0]

                # Verify technical indicators are included
                assert 'sma_20' in signal_data
                assert 'sma_50' in signal_data
                assert 'rsi' in signal_data
                assert signal_data['sma_20'] == 149.0  # Latest value
                assert signal_data['sma_50'] == 146.0
                assert signal_data['rsi'] == 67.0


    @patch('backend.app.main.fetch_ohlcv')
    @patch('backend.app.main.update_signals')
    @patch('backend.app.main.DatabaseOperations')
    @patch('backend.app.main.load_config')
    def test_bot_handles_missing_technical_indicators_gracefully(
        self,
        mock_config,
        mock_db_ops,
        mock_update_signals,
        mock_fetch
    ):
        """Test that bot handles data without technical indicators."""
        mock_config.return_value = {
            'STARTING_EQUITY': 100000,
            'TRADING_MODE': 'simulate'
        }

        # Create mock data WITHOUT technical indicators
        mock_data = pd.DataFrame({
            'close': [150.0, 151.0, 152.0],
            'open': [149.0, 150.0, 151.0],
            'high': [152.0, 153.0, 154.0],
            'low': [148.0, 149.0, 150.0],
            'volume': [1000000, 1100000, 1200000]
        }, index=pd.date_range(start='2025-01-01', periods=3))

        mock_fetch.return_value = mock_data

        mock_db = MagicMock()
        mock_db.get_positions.return_value = []
        mock_db_ops.return_value = mock_db

        with patch('backend.app.main.generate_signals') as mock_gen_signals:
            mock_gen_signals.return_value = {
                'side': 'buy',
                'signal': 1,
                'strength': 0.75,
                'data': mock_data
            }

            with patch('backend.app.main.calculate_position_size') as mock_calc_pos:
                mock_calc_pos.return_value = None

                run_trading_cycle("AAPL")

                # Should still call update_signals, just without indicators
                assert mock_update_signals.called
                signal_data = mock_update_signals.call_args[0][0]

                # Should have required fields
                assert 'symbol' in signal_data
                assert 'signal_type' in signal_data
                assert 'strength' in signal_data


class TestSignalRetrieval:
    """Validate signal retrieval from database."""

    @pytest.mark.asyncio
    async def test_api_retrieves_latest_signal_per_symbol(self):
        """Test that API retrieves only the most recent signal for each symbol."""
        from backend.app.api.endpoints.signals import get_signals

        mock_request = MagicMock()

        # Create multiple signals for same symbol at different times
        now = datetime.now(UTC)
        older_signal = {
            'symbol': 'AAPL',
            'signal_type': 'sell',  # Older signal
            'strength': 0.6,
            'price': 149.0,
            'sma_20': 147.0,
            'sma_50': 145.0,
            'rsi': 35.0,
            'created_at': (now - timedelta(minutes=10)).isoformat(),
            'timestamp': (now - timedelta(minutes=10)).isoformat()
        }
        newer_signal = {
            'symbol': 'AAPL',
            'signal_type': 'buy',  # Newer signal - should be returned
            'strength': 0.75,
            'price': 150.0,
            'sma_20': 148.0,
            'sma_50': 145.0,
            'rsi': 65.0,
            'created_at': now.isoformat(),
            'timestamp': now.isoformat()
        }

        with patch('backend.app.db.supabase.get_supabase_client') as mock_supabase:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_gte = MagicMock()
            mock_order = MagicMock()

            mock_client.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.gte.return_value = mock_gte
            mock_gte.order.return_value = mock_order
            mock_order.execute.return_value = MagicMock(data=[older_signal, newer_signal])

            mock_supabase.return_value = mock_client

            result = await get_signals(mock_request, authenticated=True)

            # Should return only the newer signal
            assert 'AAPL' in result['signals']
            assert result['signals']['AAPL']['signal'] == 'BUY'
            assert result['signals']['AAPL']['strength'] == 0.75

    @pytest.mark.asyncio
    async def test_api_filters_stale_signals(self):
        """Test that API only returns signals from last 15 minutes."""
        from backend.app.api.endpoints.signals import get_signals

        mock_request = MagicMock()
        now = datetime.now(UTC)

        # Signal older than 15 minutes - should be filtered out
        stale_signal = {
            'symbol': 'AAPL',
            'signal_type': 'buy',
            'strength': 0.75,
            'price': 150.0,
            'created_at': (now - timedelta(minutes=20)).isoformat(),
            'timestamp': (now - timedelta(minutes=20)).isoformat()
        }

        with patch('backend.app.db.supabase.get_supabase_client') as mock_supabase:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_gte = MagicMock()
            mock_order = MagicMock()

            mock_client.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.gte.return_value = mock_gte
            mock_gte.order.return_value = mock_order

            # Database query should filter by created_at >= 15 minutes ago
            # So this should return empty (stale signal filtered by query)
            mock_order.execute.return_value = MagicMock(data=[])

            mock_supabase.return_value = mock_client

            result = await get_signals(mock_request, authenticated=True)

            # Verify the database query included the time filter
            assert mock_select.gte.called
            # Should return empty signals
            assert result['signals'] == {}

    @pytest.mark.asyncio
    async def test_api_handles_multiple_symbols(self):
        """Test that API correctly handles signals for multiple symbols."""
        from backend.app.api.endpoints.signals import get_signals

        mock_request = MagicMock()
        now = datetime.now(UTC)

        signals = [
            {
                'symbol': 'AAPL',
                'signal_type': 'buy',
                'strength': 0.75,
                'price': 150.0,
                'sma_20': 148.0,
                'sma_50': 145.0,
                'rsi': 65.0,
                'created_at': now.isoformat(),
                'timestamp': now.isoformat()
            },
            {
                'symbol': 'MSFT',
                'signal_type': 'sell',
                'strength': 0.65,
                'price': 300.0,
                'sma_20': 298.0,
                'sma_50': 302.0,
                'rsi': 35.0,
                'created_at': now.isoformat(),
                'timestamp': now.isoformat()
            }
        ]

        with patch('backend.app.db.supabase.get_supabase_client') as mock_supabase:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_gte = MagicMock()
            mock_order = MagicMock()

            mock_client.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.gte.return_value = mock_gte
            mock_gte.order.return_value = mock_order
            mock_order.execute.return_value = MagicMock(data=signals)

            mock_supabase.return_value = mock_client

            result = await get_signals(mock_request, authenticated=True)

            # Should have both symbols
            assert 'AAPL' in result['signals']
            assert 'MSFT' in result['signals']
            assert result['signals']['AAPL']['signal'] == 'BUY'
            assert result['signals']['MSFT']['signal'] == 'SELL'
