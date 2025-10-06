"""Unified entry point for the trading bot application.
Supports multiple server modes: api, combined, bot."""
import argparse
import sys
import os
from datetime import datetime

from .services.fetcher import fetch_ohlcv
from bot.strategy.signals import generate_signals
from bot.risk.risk import calculate_position_size
from .services.broker.paper import execute_trade
from .db.supabase import update_trades, update_positions, update_equity, update_signals
from .db.operations import DatabaseOperations
from .core.config import load_config
from .utils.helpers import log_function_call, exponential_backoff, is_market_open, get_time_until_market_open
from .utils.monitoring import monitor
from .db.init_db import init_database
from .core.logging import setup_logging, get_logger
from .core.server import run_api_server, run_combined_server, run_background_bot


def setup_application():
    """Initialize application components."""
    logger = get_logger(__name__)
    try:
        # Load configuration
        settings = load_config()
        logger.info("Configuration loaded successfully")
        
        # Initialize database
        if not init_database():
            logger.error("Failed to initialize database")
            sys.exit(1)
        logger.info("Database initialized successfully")
        
        return settings
    except Exception as e:
        logger.error(f"Application setup failed: {e}", exc_info=True)
        sys.exit(1)


@log_function_call
@exponential_backoff(max_retries=3, base_delay=1)
def run_trading_cycle(symbol: str = "AAPL"):
    logger = get_logger(__name__)
    try:
        # Load configuration
        settings = load_config()
        logger.info("Configuration loaded successfully")

        # Set up database operations client
        db_ops = DatabaseOperations()

        # Fetch OHLCV data
        data = fetch_ohlcv(symbol)
        if data is None or not hasattr(data, 'empty') or data.empty:
            error_msg = "No market data available (all sources failed or returned empty data)"
            logger.info(f"⏭️  Trading cycle skipped: {error_msg}")
            monitor.record_failure(error_msg)
            return

        # Get current equity and open positions from DB first (needed for signal generation)
        current_equity = float(settings["STARTING_EQUITY"])

        # Fetch current positions from database
        current_positions = db_ops.get_positions()
        open_positions = len(current_positions)
        
        # Get current position for this symbol (if any)
        existing_position = None
        existing_position_qty = 0
        for pos in current_positions:
            if pos.symbol == symbol:
                existing_position = pos
                existing_position_qty = pos.quantity
                break
        
        logger.info(f"Current positions: {open_positions}, Existing {symbol} position: {existing_position_qty}")

        # Perform intraday market analysis
        logger.info(f"📊 Starting intraday market analysis for {symbol}")

        # Generate trading signals with position awareness
        signals = generate_signals(data, existing_position=existing_position_qty)
        if not signals:
            logger.info("No signals generated from intraday analysis")
            return

        # Store signals to database
        current_price = float(data['close'].iloc[-1]) if not data.empty else 100.0
        signal_data = {
            'symbol': symbol,
            'signal_type': signals.get('side', 'hold'),
            'strength': float(signals.get('strength', 0.5)),  # Convert numpy types to Python types
            'strategy': 'SMA_RSI',
            'price': current_price
        }
        
        # Log signal details for debugging
        logger.info(f"📈 Analysis result: {signals.get('side').upper()} signal with strength {signals.get('strength'):.3f}")
        if signals.get('used_fallback'):
            logger.info("Used fallback strategy due to insufficient data")
        
        update_signals(signal_data)

        # Calculate position size based on risk
        current_price = data['close'].iloc[-1] if not data.empty else 100.0
        position_size_data = calculate_position_size(signals, current_equity, open_positions, current_price)
        if not position_size_data:
            logger.info(f"📊 Analysis for {symbol} complete: HOLD signal - no trade executed")
            logger.info("Trading cycle completed successfully (hold)")
            logger.info("Next run in approximately 5 minutes")
            monitor.record_success()
            return

        # Extract the actual position size value
        position_size = position_size_data['position_size']
        side = signals.get('side', 'buy')
        
        logger.info(f"Using position size: {position_size} shares for {side.upper()} trade")

        # VALIDATE TRADE BEFORE EXECUTION
        if side == 'sell':
            if not existing_position or existing_position.quantity <= 0:
                logger.warning(f"Cannot SELL {symbol}: No existing position to sell")
                logger.info("Trading cycle completed successfully (invalid sell prevented)")
                monitor.record_success()
                return
            
            if position_size > existing_position.quantity:
                logger.warning(f"Cannot SELL {position_size} shares: Only own {existing_position.quantity} shares")
                # Adjust to sell available quantity
                position_size = int(existing_position.quantity)
                logger.info(f"Adjusted SELL size to {position_size} shares (max available)")
        
        elif side == 'buy':
            # Check if we have enough cash for BUY trade
            required_cash = position_size * current_price
            # Get latest equity info
            equity_history = db_ops.get_equity_history()
            if equity_history:
                available_cash = equity_history[-1].cash
                if available_cash < required_cash:
                    logger.warning(f"Cannot BUY {position_size} shares: Need ${required_cash:.2f}, only have ${available_cash:.2f}")
                    logger.info("Trading cycle completed successfully (insufficient funds prevented)")
                    monitor.record_success()
                    return
        
        # Execute trade based on analysis
        logger.info(f"🎯 Executing trade for {symbol}: {side.upper()} {position_size} shares at ${current_price:.2f}")
        trading_mode = os.getenv("TRADING_MODE", "simulate")
        simulate = (trading_mode == "simulate")
        trade_result = execute_trade(position_size, symbol=symbol, side=side, simulate=simulate, current_price=float(current_price))
        if not trade_result:
            error_msg = "Failed to execute trade"
            logger.error(error_msg)
            monitor.record_failure(error_msg)
            return

        # Update database with trade, positions, and equity
        update_trades(trade_result)
        
        # UPDATE POSITIONS CORRECTLY BASED ON TRADE DIRECTION
        if side == 'buy':
            # BUY: Add to position (or create new position)
            if existing_position:
                # Update existing position with weighted average price
                total_shares = existing_position.quantity + trade_result['quantity']
                total_value = (existing_position.quantity * existing_position.average_entry_price) + (trade_result['quantity'] * trade_result['price'])
                new_avg_price = total_value / total_shares
                
                position_data = {
                    'symbol': trade_result['symbol'],
                    'quantity': total_shares,
                    'average_entry_price': new_avg_price,
                    'current_price': trade_result['price'],
                    'unrealized_pnl': (trade_result['price'] - new_avg_price) * total_shares,
                    'timestamp': trade_result['timestamp']
                }
                logger.info(f"Updating existing position: {total_shares} shares @ ${new_avg_price:.2f} avg")
            else:
                # Create new position
                position_data = {
                    'symbol': trade_result['symbol'],
                    'quantity': trade_result['quantity'],
                    'average_entry_price': trade_result['price'],
                    'current_price': trade_result['price'],
                    'unrealized_pnl': 0.0,
                    'timestamp': trade_result['timestamp']
                }
                logger.info(f"Creating new position: {trade_result['quantity']} shares @ ${trade_result['price']:.2f}")
            
            update_positions(position_data)
            
        elif side == 'sell':
            # SELL: Reduce position (or close completely)
            if existing_position:
                remaining_shares = existing_position.quantity - trade_result['quantity']
                
                if remaining_shares > 0:
                    # Partial sale - keep position with same avg price
                    position_data = {
                        'symbol': trade_result['symbol'],
                        'quantity': remaining_shares,
                        'average_entry_price': existing_position.average_entry_price,
                        'current_price': trade_result['price'],
                        'unrealized_pnl': (trade_result['price'] - existing_position.average_entry_price) * remaining_shares,
                        'timestamp': trade_result['timestamp']
                    }
                    update_positions(position_data)
                    logger.info(f"Reduced position to {remaining_shares} shares @ ${existing_position.average_entry_price:.2f} avg")
                else:
                    # Complete sale - remove position
                    deleted = db_ops.delete_position(trade_result['symbol'])
                    if deleted:
                        logger.info(f"Position closed completely by selling {trade_result['quantity']} shares - removed from database")
                    else:
                        logger.warning(f"Position closed but failed to delete from database for {trade_result['symbol']}")
        
        # CALCULATE EQUITY CORRECTLY
        # Get current cash from previous equity record
        equity_history = db_ops.get_equity_history()
        previous_cash = equity_history[-1].cash if equity_history else current_equity
        
        # Calculate cash change based on trade
        if side == 'buy':
            new_cash = previous_cash - (trade_result['quantity'] * trade_result['price'])
        else:  # sell
            new_cash = previous_cash + (trade_result['quantity'] * trade_result['price'])
        
        # Calculate total portfolio value
        total_position_value = 0
        for pos in db_ops.get_positions():
            total_position_value += pos.quantity * pos.current_price
        
        total_portfolio_value = new_cash + total_position_value

        equity_data = {
            'equity': total_portfolio_value,
            'cash': new_cash,
            'timestamp': trade_result['timestamp']
        }
        update_equity(equity_data)

        logger.info(f"Portfolio update: Cash=${new_cash:.2f}, Positions=${total_position_value:.2f}, Equity=${total_portfolio_value:.2f}")

        logger.info(f"✅ Trade executed successfully for {symbol}")
        logger.info("Next run in approximately 5 minutes")
        monitor.record_success()
    except Exception as e:
        error_msg = f"Error in trading cycle: {e}"
        logger.error(error_msg, exc_info=True)
        monitor.record_failure(error_msg)


def main():
    """Main entry point with support for different server modes."""
    parser = argparse.ArgumentParser(description="Trading Bot - Unified Entry Point")
    parser.add_argument('--mode', type=str, choices=['api', 'combined', 'bot'], 
                       default='bot', help="Server mode: api (API only), combined (API+bot), bot (bot only)")
    parser.add_argument('--symbols', type=str, default=os.environ.get("TRADING_SYMBOLS", "AAPL,MSFT,JNJ,UNH,V"), 
                       help="Comma-separated ticker symbols to trade")
    parser.add_argument('--interval', type=int, default=int(os.environ.get("TRADING_INTERVAL", "300")), 
                       help="Trading cycle interval in seconds")
    parser.add_argument('--max-loops', type=int, default=None, help="Maximum number of cycles (for testing)")
    parser.add_argument('--host', type=str, default="0.0.0.0", help="Host to bind server to")
    parser.add_argument('--port', type=int, default=None, help="Port to bind server to")
    
    # For backward compatibility - if --loop is used, default to bot mode
    parser.add_argument('--loop', action='store_true', help="Run in bot mode (deprecated, use --mode bot)")
    
    args = parser.parse_args()
    
    # Handle backward compatibility
    if args.loop and args.mode == 'bot':
        # --loop was specified, keep bot mode
        pass
    elif args.loop:
        # --loop was specified with different mode, warn and switch
        print("Warning: --loop is deprecated, use --mode bot instead")
        args.mode = 'bot'
    
    # Set default port if not specified
    if args.port is None:
        args.port = int(os.environ.get("PORT", 8000))
    
    # Route to appropriate server mode
    if args.mode == 'api':
        run_api_server(args.host, args.port)
    elif args.mode == 'combined':
        run_combined_server(args.host, args.port)
    elif args.mode == 'bot':
        # For bot mode, use health port for health server
        health_port = args.port if args.port != 8000 else 8080
        run_background_bot(args.symbols, args.interval, args.max_loops, health_port)
    else:
        print(f"Unknown mode: {args.mode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
