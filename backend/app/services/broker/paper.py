import os
import logging
import requests
from typing import Dict, Optional, Tuple
from datetime import datetime, timezone
import random

logger = logging.getLogger(__name__)

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"

HEADERS = {
    "APCA-API-KEY-ID": ALPACA_API_KEY or "",
    "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY or "",
    "Content-Type": "application/json"
}

# In-memory trade log for simulation
_trade_log = []

def simulate_fill_price(symbol: str) -> float:
    """
    DEPRECATED: Returns a random fill price for the given symbol.

    This function should not be used for new code. Instead, pass the actual
    current_price parameter to execute_trade() to ensure realistic pricing.

    For backward compatibility, returns a random price between 100 and 110.
    """
    logger.warning(f"DEPRECATED: simulate_fill_price() called for {symbol}. Use current_price parameter instead.")
    return round(random.uniform(100, 110), 2)

def record_trade(trade: Dict):
    """
    Record a trade in the in-memory trade log.
    """
    _trade_log.append(trade)

def get_trade_log() -> list:
    """
    Retrieve the current trade log.
    """
    return list(_trade_log)

def clear_trade_log():
    """
    Clear the in-memory trade log.
    """
    _trade_log.clear()

class OrderValidationError(Exception):
    """Custom exception for order validation errors"""
    pass

def validate_order_inputs(position_size: int, symbol: str, side: str) -> Tuple[bool, str]:
    """
    Validate order inputs before execution.
    Returns (is_valid, error_message)
    """
    if not isinstance(position_size, int) or position_size <= 0:
        return False, "Position size must be a positive integer"
    
    if not symbol or not isinstance(symbol, str):
        return False, "Invalid symbol"
    
    if side not in ['buy', 'sell']:
        return False, "Invalid order side. Must be 'buy' or 'sell'"
    
    # Additional validation for realistic position sizes
    if position_size > 10000:  # Prevent massive positions
        return False, f"Position size {position_size} exceeds reasonable limit (10,000 shares)"
    
    return True, ""

def validate_api_credentials() -> Tuple[bool, str]:
    """
    Validate that API credentials are properly configured.
    Returns (is_valid, error_message)
    """
    if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
        return False, "Missing API credentials"
    return True, ""

def execute_trade(position_size: int, symbol: str = "AAPL", side: str = "buy", simulate: bool = True, current_price: Optional[float] = None) -> Optional[Dict]:
    """
    Place a simulated order using the Alpaca paper API or simulate locally.
    Includes comprehensive validation and error handling.

    Args:
        position_size: Number of shares to trade
        symbol: Stock symbol (e.g., "AAPL")
        side: "buy" or "sell"
        simulate: If True, simulates locally; if False, uses Alpaca API
        current_price: Current market price (optional). If not provided in simulate mode,
                      falls back to simulate_fill_price(). Required for accurate simulation.
    """
    # Validate API credentials
    is_valid, error_msg = validate_api_credentials()
    if not is_valid:
        logger.error(f"API validation error: {error_msg}")
        raise OrderValidationError(error_msg)

    # Validate order inputs
    is_valid, error_msg = validate_order_inputs(position_size, symbol, side)
    if not is_valid:
        logger.error(f"Order validation error: {error_msg}")
        raise OrderValidationError(error_msg)

    if simulate:
        # Validate current_price if provided
        if current_price is not None:
            if current_price <= 0 or current_price > 10000:
                logger.warning(f"Invalid current_price {current_price} for {symbol}. Must be between 0 and 10000.")
                raise OrderValidationError(f"Invalid current_price: {current_price}")
            fill_price = current_price
            logger.info(f"Using real market price for simulation: ${fill_price:.2f}")
        else:
            # Fallback to random price (deprecated behavior)
            fill_price = simulate_fill_price(symbol)
            logger.warning(f"No current_price provided for {symbol}. Using fallback price: ${fill_price:.2f}")

        trade = {
            'symbol': symbol,
            'side': side,
            'quantity': position_size,
            'status': 'completed',
            'order_id': f'sim-{random.randint(100000, 999999)}',
            'price': fill_price,  # Fixed: changed from filled_avg_price to price
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'strategy': 'SMA_RSI',  # Added: required field for database
            'simulated': True
        }
        record_trade(trade)
        logger.info(f"Simulated trade: {trade}")
        return trade

    order_data = {
        "symbol": symbol,
        "qty": position_size,
        "side": side,
        "type": "market",
        "time_in_force": "day",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    try:
        response = requests.post(
            f"{ALPACA_BASE_URL}/v2/orders",
            headers=HEADERS,
            json=order_data,
            timeout=10  # Add timeout to prevent hanging
        )
        
        if response.status_code in (200, 201):
            order = response.json()
            # Fallback fill price for real orders
            fill_price = simulate_fill_price(symbol)
            trade = {
                'symbol': symbol,
                'side': side,
                'quantity': position_size,
                'status': order.get('status', 'completed'),
                'order_id': order.get('id'),
                'price': order.get('filled_avg_price') or order.get('limit_price') or fill_price,  # Fixed: map to price field
                'timestamp': order.get('created_at'),
                'strategy': 'SMA_RSI',  # Added: required field for database
                'simulated': False
            }
            record_trade(trade)
            logger.info(f"Order placed successfully: {trade}")
            return trade
        else:
            error_msg = f"Failed to place order: {response.text}"
            logger.error(error_msg)
            raise OrderValidationError(error_msg)
            
    except requests.Timeout:
        error_msg = "Request timed out while placing order"
        logger.error(error_msg)
        raise OrderValidationError(error_msg)
    except requests.RequestException as e:
        error_msg = f"Network error while placing order: {str(e)}"
        logger.error(error_msg)
        raise OrderValidationError(error_msg)
    except OrderValidationError:
        raise
    except Exception as e:
        error_msg = f"Unexpected error executing trade: {str(e)}"
        logger.error(error_msg)
        raise OrderValidationError(error_msg)

def get_order_status(order_id: str) -> Optional[Dict]:
    """
    Get the status of an existing order.
    """
    try:
        response = requests.get(
            f"{ALPACA_BASE_URL}/v2/orders/{order_id}",
            headers=HEADERS,
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get order status: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting order status: {e}")
        return None 