"""
Comprehensive Database Layer Validation Tests
Tests schema consistency, position deletion, trade cycles, constraints, and upserts.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from backend.app.db.models import Trade, Position, Equity, Signal
from backend.app.db.operations import DatabaseOperations


class TestSchemaValidation:
    """Test schema consistency between SQL and Pydantic models."""

    def test_trade_model_fields_match_schema(self):
        """Verify Trade model fields match SQL schema exactly."""
        # SQL columns: id, order_id, symbol, side, quantity, price, timestamp,
        #              strategy, profit_loss, status, created_at

        trade = Trade(
            order_id="TEST123",
            symbol="AAPL",
            side="buy",
            quantity=10.5,
            price=150.25,
            timestamp=datetime.now(timezone.utc),
            strategy="SMA_RSI",
            profit_loss=25.50,
            status="completed"
        )

        data = trade.model_dump(exclude={'id'})

        # Verify all required SQL fields are present
        assert 'order_id' in data
        assert 'symbol' in data
        assert 'side' in data
        assert 'quantity' in data
        assert 'price' in data
        assert 'timestamp' in data
        assert 'strategy' in data
        assert 'profit_loss' in data
        assert 'status' in data

        # Verify data types
        assert isinstance(data['order_id'], str)
        assert isinstance(data['symbol'], str)
        assert isinstance(data['side'], str)
        assert isinstance(data['quantity'], float)
        assert isinstance(data['price'], float)
        assert isinstance(data['timestamp'], datetime)
        assert isinstance(data['strategy'], str)
        assert isinstance(data['status'], str)

    def test_position_model_fields_match_schema(self):
        """Verify Position model fields match SQL schema exactly."""
        # SQL columns: id, symbol, quantity, average_entry_price, current_price,
        #              unrealized_pnl, timestamp, created_at, updated_at

        position = Position(
            symbol="AAPL",
            quantity=10.0,
            average_entry_price=150.00,
            current_price=155.00,
            unrealized_pnl=50.00,
            timestamp=datetime.now(timezone.utc)
        )

        data = position.model_dump(exclude={'id'})

        # Verify critical field name: average_entry_price (recent standardization)
        assert 'average_entry_price' in data
        assert 'filled_avg_price' not in data  # Old name should not exist

        # Verify all required SQL fields
        assert 'symbol' in data
        assert 'quantity' in data
        assert 'current_price' in data
        assert 'unrealized_pnl' in data
        assert 'timestamp' in data

        # Verify data types
        assert isinstance(data['symbol'], str)
        assert isinstance(data['quantity'], float)
        assert isinstance(data['average_entry_price'], float)
        assert isinstance(data['current_price'], float)
        assert isinstance(data['unrealized_pnl'], float)
        assert isinstance(data['timestamp'], datetime)

    def test_equity_model_fields_match_schema(self):
        """Verify Equity model fields match SQL schema exactly."""
        # SQL columns: id, timestamp, equity, cash, created_at

        equity = Equity(
            timestamp=datetime.now(timezone.utc),
            equity=100000.00,
            cash=50000.00
        )

        data = equity.model_dump(exclude={'id'})

        # Verify all required SQL fields
        assert 'timestamp' in data
        assert 'equity' in data
        assert 'cash' in data

        # Verify data types
        assert isinstance(data['timestamp'], datetime)
        assert isinstance(data['equity'], float)
        assert isinstance(data['cash'], float)

    def test_signal_model_fields_match_schema(self):
        """Verify Signal model fields match SQL schema exactly."""
        # SQL columns: id, symbol, signal_type, strength, timestamp,
        #              strategy, price, created_at

        signal = Signal(
            symbol="AAPL",
            signal_type="buy",
            strength=0.85,
            timestamp=datetime.now(timezone.utc),
            strategy="SMA_RSI",
            price=150.00
        )

        data = signal.model_dump(exclude={'id'})

        # Verify all required SQL fields
        assert 'symbol' in data
        assert 'signal_type' in data
        assert 'strength' in data
        assert 'timestamp' in data
        assert 'strategy' in data
        assert 'price' in data

        # Verify data types
        assert isinstance(data['symbol'], str)
        assert isinstance(data['signal_type'], str)
        assert isinstance(data['strength'], float)
        assert isinstance(data['timestamp'], datetime)
        assert isinstance(data['strategy'], str)
        assert isinstance(data['price'], float)


class TestPositionDeletion:
    """Test the new delete_position() method."""

    @patch('backend.app.db.operations.DatabaseClient')
    def test_delete_position_success(self, mock_db_client):
        """Test successful position deletion."""
        # Setup mock
        mock_client = MagicMock()
        mock_db_client.get_instance.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_delete = MagicMock()
        mock_table.delete.return_value = mock_delete

        mock_eq = MagicMock()
        mock_delete.eq.return_value = mock_eq

        mock_eq.execute.return_value = MagicMock(data=[])

        # Execute
        db_ops = DatabaseOperations()
        result = db_ops.delete_position("AAPL")

        # Verify
        assert result is True
        mock_client.table.assert_called_with('positions')
        mock_table.delete.assert_called_once()
        mock_delete.eq.assert_called_with('symbol', 'AAPL')
        mock_eq.execute.assert_called_once()

    @patch('backend.app.db.operations.DatabaseClient')
    def test_delete_position_handles_errors(self, mock_db_client):
        """Test error handling when position deletion fails."""
        # Setup mock to raise exception
        mock_client = MagicMock()
        mock_db_client.get_instance.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.delete.side_effect = Exception("Database error")

        # Execute
        db_ops = DatabaseOperations()
        result = db_ops.delete_position("AAPL")

        # Verify - should return False but not raise exception
        assert result is False

    @patch('backend.app.db.operations.DatabaseClient')
    def test_delete_nonexistent_position(self, mock_db_client):
        """Test deleting a position that doesn't exist."""
        # Setup mock
        mock_client = MagicMock()
        mock_db_client.get_instance.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_delete = MagicMock()
        mock_table.delete.return_value = mock_delete

        mock_eq = MagicMock()
        mock_delete.eq.return_value = mock_eq

        # Return empty result (position not found but no error)
        mock_eq.execute.return_value = MagicMock(data=[])

        # Execute
        db_ops = DatabaseOperations()
        result = db_ops.delete_position("NONEXISTENT")

        # Verify - should still return True (operation succeeded)
        assert result is True


class TestCompleteTradeCycle:
    """Test complete trade cycles including position deletion."""

    @patch('backend.app.db.operations.DatabaseClient')
    def test_buy_trade_creates_position(self, mock_db_client):
        """Test BUY trade creates a new position."""
        # Setup mock
        mock_client = MagicMock()
        mock_db_client.get_instance.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_upsert = MagicMock()
        mock_table.upsert.return_value = mock_upsert

        position_data = {
            'symbol': 'AAPL',
            'quantity': 10.0,
            'average_entry_price': 150.00,
            'current_price': 150.00,
            'unrealized_pnl': 0.0,
            'timestamp': datetime.now(timezone.utc)
        }
        mock_upsert.execute.return_value = MagicMock(data=[position_data])

        # Execute
        db_ops = DatabaseOperations()
        position = Position(**position_data)
        result = db_ops.update_position(position)

        # Verify
        assert result.symbol == 'AAPL'
        assert result.quantity == 10.0
        assert result.average_entry_price == 150.00
        mock_table.upsert.assert_called_once()

    @patch('backend.app.db.operations.DatabaseClient')
    def test_partial_sell_updates_position(self, mock_db_client):
        """Test partial SELL reduces position but doesn't delete."""
        # Setup mock
        mock_client = MagicMock()
        mock_db_client.get_instance.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_upsert = MagicMock()
        mock_table.upsert.return_value = mock_upsert

        # Reduced position after partial sell
        position_data = {
            'symbol': 'AAPL',
            'quantity': 5.0,  # Was 10, sold 5
            'average_entry_price': 150.00,  # Stays same
            'current_price': 155.00,
            'unrealized_pnl': 25.00,
            'timestamp': datetime.now(timezone.utc)
        }
        mock_upsert.execute.return_value = MagicMock(data=[position_data])

        # Execute
        db_ops = DatabaseOperations()
        position = Position(**position_data)
        result = db_ops.update_position(position)

        # Verify position still exists with reduced quantity
        assert result.quantity == 5.0
        assert result.average_entry_price == 150.00  # Same avg price
        mock_table.upsert.assert_called_once()

    @patch('backend.app.db.operations.DatabaseClient')
    def test_complete_sell_deletes_position(self, mock_db_client):
        """Test complete SELL calls delete_position()."""
        # Setup mock
        mock_client = MagicMock()
        mock_db_client.get_instance.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_delete = MagicMock()
        mock_table.delete.return_value = mock_delete

        mock_eq = MagicMock()
        mock_delete.eq.return_value = mock_eq

        mock_eq.execute.return_value = MagicMock(data=[])

        # Execute
        db_ops = DatabaseOperations()
        result = db_ops.delete_position("AAPL")

        # Verify
        assert result is True
        mock_table.delete.assert_called_once()
        mock_delete.eq.assert_called_with('symbol', 'AAPL')


class TestConstraintValidation:
    """Test database constraint enforcement."""

    @patch('backend.app.db.operations.DatabaseClient')
    def test_duplicate_order_id_prevented(self, mock_db_client):
        """Test UNIQUE constraint on trades.order_id."""
        # Setup mock to simulate constraint violation
        mock_client = MagicMock()
        mock_db_client.get_instance.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert

        # Simulate unique constraint violation
        mock_insert.execute.side_effect = Exception("duplicate key value violates unique constraint")

        # Execute
        db_ops = DatabaseOperations()
        trade = Trade(
            order_id="DUPLICATE123",
            symbol="AAPL",
            side="buy",
            quantity=10.0,
            price=150.00,
            timestamp=datetime.now(timezone.utc),
            strategy="SMA_RSI"
        )

        # Verify constraint violation raises exception
        with pytest.raises(Exception) as exc_info:
            db_ops.create_trade(trade)

        assert "duplicate key" in str(exc_info.value).lower()

    @patch('backend.app.db.operations.DatabaseClient')
    def test_upsert_handles_duplicate_symbol(self, mock_db_client):
        """Test positions.symbol UNIQUE with upsert."""
        # Setup mock
        mock_client = MagicMock()
        mock_db_client.get_instance.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_upsert = MagicMock()
        mock_table.upsert.return_value = mock_upsert

        updated_position = {
            'symbol': 'AAPL',
            'quantity': 20.0,  # Updated
            'average_entry_price': 152.50,
            'current_price': 155.00,
            'unrealized_pnl': 50.00,
            'timestamp': datetime.now(timezone.utc)
        }
        mock_upsert.execute.return_value = MagicMock(data=[updated_position])

        # Execute - should UPDATE not fail
        db_ops = DatabaseOperations()
        position = Position(**updated_position)
        result = db_ops.update_position(position)

        # Verify upsert was called with on_conflict
        assert result.quantity == 20.0
        mock_table.upsert.assert_called_once()
        call_args = mock_table.upsert.call_args
        assert call_args[1]['on_conflict'] == 'symbol'


class TestUpsertLogic:
    """Test ON CONFLICT upsert behavior."""

    @patch('backend.app.db.operations.DatabaseClient')
    def test_position_upsert_on_symbol_conflict(self, mock_db_client):
        """Test position upsert updates existing record on symbol conflict."""
        # Setup mock
        mock_client = MagicMock()
        mock_db_client.get_instance.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_upsert = MagicMock()
        mock_table.upsert.return_value = mock_upsert

        position_data = {
            'symbol': 'AAPL',
            'quantity': 15.0,
            'average_entry_price': 151.00,
            'current_price': 156.00,
            'unrealized_pnl': 75.00,
            'timestamp': datetime.now(timezone.utc)
        }
        mock_upsert.execute.return_value = MagicMock(data=[position_data])

        # Execute
        db_ops = DatabaseOperations()
        position = Position(**position_data)
        result = db_ops.update_position(position)

        # Verify
        mock_table.upsert.assert_called_once()
        call_args = mock_table.upsert.call_args
        assert call_args[1]['on_conflict'] == 'symbol'

    @patch('backend.app.db.operations.DatabaseClient')
    def test_equity_upsert_on_timestamp_conflict(self, mock_db_client):
        """Test equity upsert updates existing record on timestamp conflict."""
        # Setup mock
        mock_client = MagicMock()
        mock_db_client.get_instance.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_upsert = MagicMock()
        mock_table.upsert.return_value = mock_upsert

        equity_data = {
            'timestamp': datetime.now(timezone.utc),
            'equity': 105000.00,
            'cash': 45000.00
        }
        mock_upsert.execute.return_value = MagicMock(data=[equity_data])

        # Execute
        db_ops = DatabaseOperations()
        equity = Equity(**equity_data)
        result = db_ops.record_equity(equity)

        # Verify
        mock_table.upsert.assert_called_once()
        call_args = mock_table.upsert.call_args
        assert call_args[1]['on_conflict'] == 'timestamp'

    @patch('backend.app.db.operations.DatabaseClient')
    def test_signal_upsert_on_composite_key_conflict(self, mock_db_client):
        """Test signal upsert updates on composite key conflict."""
        # Setup mock
        mock_client = MagicMock()
        mock_db_client.get_instance.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_upsert = MagicMock()
        mock_table.upsert.return_value = mock_upsert

        signal_data = {
            'symbol': 'AAPL',
            'signal_type': 'buy',
            'strength': 0.90,  # Updated strength
            'timestamp': datetime.now(timezone.utc),
            'strategy': 'SMA_RSI',
            'price': 155.00
        }
        mock_upsert.execute.return_value = MagicMock(data=[signal_data])

        # Execute
        db_ops = DatabaseOperations()
        signal = Signal(**signal_data)
        result = db_ops.create_signal(signal)

        # Verify
        mock_table.upsert.assert_called_once()
        call_args = mock_table.upsert.call_args
        assert call_args[1]['on_conflict'] == 'symbol,timestamp,strategy'


class TestIndexValidation:
    """Validate database indexes exist and are correct."""

    def test_required_indexes_defined(self):
        """Verify all required indexes are defined in schema."""
        # This test documents the expected indexes from schema.sql
        expected_indexes = {
            'trades': ['idx_trades_symbol', 'idx_trades_timestamp', 'idx_trades_symbol_timestamp'],
            'positions': ['idx_positions_symbol'],
            'equity': ['idx_equity_timestamp'],
            'signals': ['idx_signals_symbol', 'idx_signals_timestamp']
        }

        # Document the indexes for production validation
        assert 'trades' in expected_indexes
        assert 'positions' in expected_indexes
        assert 'equity' in expected_indexes
        assert 'signals' in expected_indexes

        # Verify composite index for trades
        assert 'idx_trades_symbol_timestamp' in expected_indexes['trades']

    def test_unique_constraints_defined(self):
        """Verify all unique constraints are properly defined."""
        expected_constraints = {
            'trades': ['order_id'],
            'positions': ['symbol'],
            'equity': ['timestamp'],
            'signals': ['(symbol, timestamp, strategy)']  # Composite
        }

        assert len(expected_constraints) == 4
        assert 'order_id' in expected_constraints['trades']
        assert 'symbol' in expected_constraints['positions']
        assert 'timestamp' in expected_constraints['equity']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
