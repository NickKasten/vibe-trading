from typing import List, Optional
from datetime import datetime
from .client import DatabaseClient
from .models import Trade, Position, Equity, Signal

def to_serializable(data: dict) -> dict:
    """Convert all datetime fields in a dict to ISO format."""
    for k, v in data.items():
        if isinstance(v, datetime):
            data[k] = v.isoformat()
    return data

class DatabaseOperations:
    """Database operations for Supabase."""
    
    def __init__(self):
        self.client = DatabaseClient.get_instance()

    def create_trade(self, trade: Trade) -> Trade:
        """Create a new trade record."""
        data = to_serializable(trade.model_dump(exclude={'id'}))
        result = self.client.table('trades').insert(data).execute()
        return Trade(**result.data[0])

    def get_trades(
        self,
        limit: int = 100,
        offset: int = 0,
        symbol: Optional[str] = None
    ) -> List[Trade]:
        """Get trade history with optional filtering."""
        query = self.client.table('trades').select('*')
        if symbol:
            query = query.eq('symbol', symbol)
        result = query.order('timestamp', desc=True).range(offset, offset+limit-1).execute()
        return [Trade(**trade) for trade in result.data]

    def get_recent_trades(self, symbol: str, days: int = 1) -> List[Trade]:
        """Get recent trades for a symbol within the last N days."""
        from datetime import datetime, timedelta
        cutoff_time = datetime.now() - timedelta(days=days)
        
        query = (
            self.client.table('trades')
            .select('*')
            .eq('symbol', symbol)
            .gte('timestamp', cutoff_time.isoformat())
        )
        result = query.order('timestamp', desc=True).execute()
        return [Trade(**trade) for trade in result.data]

    def update_position(self, position: Position) -> Position:
        """Update or create a position using upsert."""
        data = to_serializable(position.model_dump(exclude={'id'}))
        result = (
            self.client.table('positions')
            .upsert(data, on_conflict='symbol')
            .execute()
        )
        return Position(**result.data[0])

    def get_positions(self) -> List[Position]:
        """Get all current positions."""
        result = self.client.table('positions').select('*').execute()
        return [Position(**pos) for pos in result.data]

    def delete_position(self, symbol: str) -> bool:
        """Delete a position by symbol."""
        try:
            self.client.table('positions').delete().eq('symbol', symbol).execute()
            return True
        except Exception as e:
            # Log error but don't fail the trading cycle
            import logging
            logging.getLogger(__name__).error(f"Failed to delete position for {symbol}: {e}")
            return False

    def record_equity(self, equity: Equity) -> Equity:
        """Record equity curve data point with upsert on timestamp."""
        data = to_serializable(equity.model_dump(exclude={'id'}))
        result = (
            self.client.table('equity')
            .upsert(data, on_conflict='timestamp')
            .execute()
        )
        return Equity(**result.data[0])

    def get_equity_history(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Equity]:
        """Get equity curve history with optional time range."""
        query = self.client.table('equity').select('*')
        if start_time:
            query = query.gte('timestamp', start_time.isoformat())
        if end_time:
            query = query.lte('timestamp', end_time.isoformat())
        result = query.order('timestamp').execute()
        return [Equity(**equity) for equity in result.data]

    def create_signal(self, signal: Signal) -> Signal:
        """Create a new trading signal with upsert on composite key."""
        data = to_serializable(signal.model_dump(exclude={'id'}))
        result = (
            self.client.table('signals')
            .upsert(data, on_conflict='symbol,timestamp,strategy')
            .execute()
        )
        return Signal(**result.data[0])

    def get_latest_signals(
        self,
        symbol: Optional[str] = None,
        limit: int = 10
    ) -> List[Signal]:
        """Get latest trading signals with optional symbol filter."""
        query = self.client.table('signals').select('*')
        if symbol:
            query = query.eq('symbol', symbol)
        result = query.order('timestamp', desc=True).limit(limit).execute()
        return [Signal(**signal) for signal in result.data] 