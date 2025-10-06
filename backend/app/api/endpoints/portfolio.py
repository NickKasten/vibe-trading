from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, Any

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    Limiter = None  # type: ignore
    get_remote_address = None  # type: ignore

from ...db import supabase as supabase_db
from ...core.config import load_config, LEGAL_DISCLAIMER
from ...utils.auth import verify_api_key

router = APIRouter()


class DummyLimiter:  # pragma: no cover - simple fallback
    def limit(self, *_args, **_kwargs):
        def decorator(func):
            return func

        return decorator


limiter = Limiter(key_func=get_remote_address) if Limiter and get_remote_address else DummyLimiter()
rate_limit = limiter.limit


@router.get("/portfolio")
@rate_limit("30/minute")
async def get_portfolio(request: Request, authenticated: bool = Depends(verify_api_key)):
    """
    Get current portfolio state including positions, equity, and P/L.
    """
    try:
        supabase = supabase_db.get_supabase_client()
        
        # Fetch current positions
        positions_response = supabase.table("positions").select("*").execute()
        raw_positions = positions_response.data if positions_response.data else []
        
        # Transform positions to match frontend expectations
        positions = []
        for pos in raw_positions:
            quantity = float(pos.get("quantity", 0))
            current_price = float(pos.get("current_price", 0))
            average_entry_price = float(pos.get("average_entry_price", 0))
            unrealized_pnl = float(pos.get("unrealized_pnl", 0))

            transformed_position = {
                "symbol": pos.get("symbol", ""),
                "quantity": quantity,
                "average_entry_price": average_entry_price,
                "current_price": current_price,
                "market_value": quantity * current_price,
                "unrealized_pl": unrealized_pnl,
                "timestamp": pos.get("timestamp")
            }
            positions.append(transformed_position)
        
        # Fetch current equity
        equity_response = supabase.table("equity").select("*").order("timestamp.desc").limit(1).execute()
        current_equity = equity_response.data[0] if equity_response.data else {"equity": 0, "timestamp": None}
        
        # Calculate total P/L using transformed data
        total_pl = sum(pos["unrealized_pl"] for pos in positions)
        
        return {
            "positions": positions,
            "current_equity": current_equity.get("equity", 0),
            "total_pl": total_pl,
            "timestamp": current_equity.get("timestamp"),
            "data_delay_minutes": 15,  # As per PRD requirement
            "disclaimer": LEGAL_DISCLAIMER
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
