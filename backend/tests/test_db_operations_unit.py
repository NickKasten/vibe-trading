"""
Unit tests for database operations - specifically targeting untested code paths.
Tests delete_position() method and error handling.
"""

import pytest
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timezone
from backend.app.db.operations import DatabaseOperations
from backend.app.db.models import Position, Trade, Equity, Signal


class TestDeletePosition:
    """Test suite for delete_position() method - NEW functionality added recently."""

    @patch('backend.app.db.operations.DatabaseClient.get_instance')
    def test_delete_position_success(self, mock_db_client):
        """Test successful position deletion."""
        # Setup mock
        mock_client = MagicMock()
        mock_db_client.return_value = mock_client

        # Setup query chain
        query_mock = MagicMock()
        query_mock.delete.return_value = query_mock
        query_mock.eq.return_value = query_mock
        query_mock.execute.return_value = MagicMock(data=[])

        mock_client.table.return_value = query_mock

        # Test
        db_ops = DatabaseOperations()
        result = db_ops.delete_position('AAPL')

        # Verify
        assert result is True
        mock_client.table.assert_called_once_with('positions')
        query_mock.delete.assert_called_once()
        query_mock.eq.assert_called_once_with('symbol', 'AAPL')
        query_mock.execute.assert_called_once()

    @patch('backend.app.db.operations.DatabaseClient.get_instance')
    def test_delete_position_failure_exception(self, mock_db_client):
        """Test that delete_position handles exceptions gracefully."""
        # Setup mock to raise exception
        mock_client = MagicMock()
        mock_db_client.return_value = mock_client

        query_mock = MagicMock()
        query_mock.delete.return_value = query_mock
        query_mock.eq.return_value = query_mock
        query_mock.execute.side_effect = Exception("Database connection error")

        mock_client.table.return_value = query_mock

        # Test - should not raise exception, should return False
        db_ops = DatabaseOperations()
        result = db_ops.delete_position('AAPL')

        # Verify
        assert result is False

    @patch('backend.app.db.operations.DatabaseClient.get_instance')
    def test_delete_position_empty_symbol(self, mock_db_client):
        """Test delete_position with empty symbol string."""
        # Setup mock
        mock_client = MagicMock()
        mock_db_client.return_value = mock_client

        query_mock = MagicMock()
        query_mock.delete.return_value = query_mock
        query_mock.eq.return_value = query_mock
        query_mock.execute.return_value = MagicMock(data=[])

        mock_client.table.return_value = query_mock

        # Test
        db_ops = DatabaseOperations()
        result = db_ops.delete_position('')

        # Verify - should still attempt deletion
        assert result is True
        query_mock.eq.assert_called_once_with('symbol', '')

    @patch('backend.app.db.operations.DatabaseClient.get_instance')
    def test_delete_position_network_error(self, mock_db_client):
        """Test delete_position handles network errors."""
        # Setup mock to raise network-related exception
        mock_client = MagicMock()
        mock_db_client.return_value = mock_client

        query_mock = MagicMock()
        query_mock.delete.return_value = query_mock
        query_mock.eq.return_value = query_mock
        query_mock.execute.side_effect = ConnectionError("Network unreachable")

        mock_client.table.return_value = query_mock

        # Test
        db_ops = DatabaseOperations()
        result = db_ops.delete_position('TSLA')

        # Verify - should return False without crashing
        assert result is False


class TestDatabaseOperationsErrorHandling:
    """Test error handling in database operations."""

    @patch('backend.app.db.operations.DatabaseClient.get_instance')
    def test_get_positions_exception(self, mock_db_client):
        """Test get_positions error handling."""
        mock_client = MagicMock()
        mock_db_client.return_value = mock_client

        query_mock = MagicMock()
        query_mock.select.return_value = query_mock
        query_mock.execute.side_effect = Exception("Database error")

        mock_client.table.return_value = query_mock

        db_ops = DatabaseOperations()

        # Should raise exception (no error handling in get_positions)
        with pytest.raises(Exception):
            db_ops.get_positions()

    @patch('backend.app.db.operations.DatabaseClient.get_instance')
    def test_get_recent_trades_with_no_results(self, mock_db_client):
        """Test get_recent_trades when no trades exist."""
        mock_client = MagicMock()
        mock_db_client.return_value = mock_client

        query_mock = MagicMock()
        query_mock.select.return_value = query_mock
        query_mock.eq.return_value = query_mock
        query_mock.gte.return_value = query_mock
        query_mock.order.return_value = query_mock
        query_mock.execute.return_value = MagicMock(data=[])

        mock_client.table.return_value = query_mock

        db_ops = DatabaseOperations()
        trades = db_ops.get_recent_trades('AAPL', days=1)

        assert trades == []
        assert isinstance(trades, list)

    @patch('backend.app.db.operations.DatabaseClient.get_instance')
    def test_update_position_upsert_on_conflict(self, mock_db_client):
        """Test that update_position uses upsert with correct conflict resolution."""
        mock_client = MagicMock()
        mock_db_client.return_value = mock_client

        position_data = {
            'symbol': 'AAPL',
            'quantity': 10.0,
            'average_entry_price': 150.0,
            'current_price': 155.0,
            'unrealized_pnl': 50.0,
            'timestamp': datetime.now(timezone.utc)
        }

        query_mock = MagicMock()
        query_mock.upsert.return_value = query_mock
        query_mock.execute.return_value = MagicMock(data=[position_data])

        mock_client.table.return_value = query_mock

        position = Position(**position_data)
        db_ops = DatabaseOperations()
        result = db_ops.update_position(position)

        # Verify upsert was called with on_conflict='symbol'
        query_mock.upsert.assert_called_once()
        call_args = query_mock.upsert.call_args
        assert call_args[1]['on_conflict'] == 'symbol'

        assert result.symbol == 'AAPL'
        assert result.quantity == 10.0


class TestDatabaseOperationsEdgeCases:
    """Test edge cases in database operations."""

    @patch('backend.app.db.operations.DatabaseClient.get_instance')
    def test_get_equity_history_with_time_range(self, mock_db_client):
        """Test get_equity_history with start and end times."""
        mock_client = MagicMock()
        mock_db_client.return_value = mock_client

        start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 31, tzinfo=timezone.utc)

        equity_data = {
            'equity': 100000.0,
            'cash': 50000.0,
            'timestamp': datetime(2024, 1, 15, tzinfo=timezone.utc)
        }

        query_mock = MagicMock()
        query_mock.select.return_value = query_mock
        query_mock.gte.return_value = query_mock
        query_mock.lte.return_value = query_mock
        query_mock.order.return_value = query_mock
        query_mock.execute.return_value = MagicMock(data=[equity_data])

        mock_client.table.return_value = query_mock

        db_ops = DatabaseOperations()
        result = db_ops.get_equity_history(start_time, end_time)

        # Verify both gte and lte were called
        query_mock.gte.assert_called_once()
        query_mock.lte.assert_called_once()
        assert len(result) == 1
        assert result[0].equity == 100000.0

    @patch('backend.app.db.operations.DatabaseClient.get_instance')
    def test_get_trades_with_pagination(self, mock_db_client):
        """Test get_trades pagination functionality."""
        mock_client = MagicMock()
        mock_db_client.return_value = mock_client

        query_mock = MagicMock()
        query_mock.select.return_value = query_mock
        query_mock.eq.return_value = query_mock
        query_mock.order.return_value = query_mock
        query_mock.range.return_value = query_mock
        query_mock.execute.return_value = MagicMock(data=[])

        mock_client.table.return_value = query_mock

        db_ops = DatabaseOperations()
        db_ops.get_trades(limit=50, offset=100, symbol='AAPL')

        # Verify pagination range is correct: offset to offset+limit-1
        query_mock.range.assert_called_once_with(100, 149)  # 100 to 100+50-1

    @patch('backend.app.db.operations.DatabaseClient.get_instance')
    def test_create_signal_with_upsert_composite_key(self, mock_db_client):
        """Test that create_signal uses composite key for upsert."""
        mock_client = MagicMock()
        mock_db_client.return_value = mock_client

        signal_data = {
            'symbol': 'AAPL',
            'signal_type': 'buy',
            'strength': 0.8,
            'strategy': 'SMA_RSI',
            'price': 150.0,
            'timestamp': datetime.now(timezone.utc)
        }

        query_mock = MagicMock()
        query_mock.upsert.return_value = query_mock
        query_mock.execute.return_value = MagicMock(data=[signal_data])

        mock_client.table.return_value = query_mock

        signal = Signal(**signal_data)
        db_ops = DatabaseOperations()
        result = db_ops.create_signal(signal)

        # Verify upsert uses composite key
        query_mock.upsert.assert_called_once()
        call_args = query_mock.upsert.call_args
        assert call_args[1]['on_conflict'] == 'symbol,timestamp,strategy'

        assert result.symbol == 'AAPL'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
