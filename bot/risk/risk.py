import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Risk Management Constants
RISK_PER_TRADE_PCT = 0.02  # 2% of equity at risk per trade
STOP_LOSS_PCT = 0.05       # 5% stop-loss distance
MAX_POSITIONS = 3          # Maximum concurrent positions
MAX_POSITION_PCT = 0.30    # Maximum 30% of equity per position (safety cap)

def validate_buying_power(equity: float, proposed_investment: float, open_positions: int) -> tuple[bool, str]:
    """
    Validate that a proposed investment won't exceed buying power limits.

    Paper trading accounts typically have:
    - 2x buying power intraday (can use up to 2x equity during the day)
    - 1x buying power overnight (must close day within equity)

    With MAX_POSITIONS=3, we need to ensure 3 simultaneous positions don't exceed limits.

    Args:
        equity: Current account equity
        proposed_investment: Dollar amount of proposed position
        open_positions: Number of currently open positions

    Returns:
        (is_valid, error_message)
    """
    # Calculate what total exposure would be with this new position
    # Assuming worst case: all positions are equal size
    total_if_all_max = proposed_investment * MAX_POSITIONS

    # Conservative limit: total positions should not exceed 90% of equity
    # This ensures we stay well within overnight buying power (1x) with buffer
    safe_limit = equity * 0.90

    if total_if_all_max > safe_limit:
        return False, (f"Position would risk exceeding buying power limits. "
                      f"With {MAX_POSITIONS} positions at this size, total exposure "
                      f"would be ${total_if_all_max:,.2f} (>{safe_limit/equity*100:.0f}% of equity)")

    return True, ""

def calculate_position_size(signals: Dict, current_equity: float, open_positions: int, current_price: float) -> Optional[Dict]:
    """
    Calculate position size based on 2% equity per trade, 5% stop-loss, and max 3 open positions.
    Includes a 30% position cap to prevent buying power issues.

    Formula: max_investment = (equity × risk_pct) / stop_loss_pct
    With 2% risk and 5% stop: max_investment = equity × 0.40
    Safety cap applied: min(calculated, equity × 0.30)

    This ensures 3 positions = 90% of equity, safely within buying power limits.

    Args:
        signals: Signal data with direction and strength
        current_equity: Total portfolio equity available
        open_positions: Number of currently open positions
        current_price: Current stock price for position sizing

    Returns:
        Dictionary with position size and metadata, or None if position should not be opened
    """
    logger.info(f"Calculating position size with signals: {signals}, equity: {current_equity}, open positions: {open_positions}, price: {current_price}")

    if not signals or 'signal' not in signals:
        logger.warning("No signals or missing signal key")
        return None

    signal = signals['signal']
    if signal == 0:
        logger.info("No trading signal (signal = 0)")
        return None

    # Check if max positions is exceeded
    if open_positions >= MAX_POSITIONS:
        logger.info(f"Max positions ({MAX_POSITIONS}) exceeded")
        return None

    # Calculate position size using 2% risk formula
    risk_per_trade = current_equity * RISK_PER_TRADE_PCT  # 2% equity per trade

    # Maximum investment from risk formula: risk / stop_loss
    # Example: $100K equity → $2K risk → $40K max (40%)
    formula_max_investment = risk_per_trade / STOP_LOSS_PCT

    # Apply safety cap: limit to 30% of equity to prevent buying power issues
    # With 3 positions: 3 × 30% = 90% total (safe for overnight)
    capped_max_investment = current_equity * MAX_POSITION_PCT

    # Use the smaller of the two
    max_investment = min(formula_max_investment, capped_max_investment)

    # Determine which limit was applied
    cap_applied = max_investment == capped_max_investment

    # Calculate shares based on current stock price
    position_size = int(max_investment / current_price)

    # Check if position size is at least 1 share
    if position_size < 1:
        logger.warning(f"Position size too small: {position_size} shares (stock price ${current_price:.2f} too expensive for account)")
        return None

    # Calculate actual investment amount
    actual_investment = position_size * current_price

    # Validate buying power
    is_valid, error_msg = validate_buying_power(current_equity, actual_investment, open_positions)
    if not is_valid:
        logger.error(f"Buying power validation failed: {error_msg}")
        return None

    # Log detailed calculation
    logger.info(f"Risk calculation: ${risk_per_trade:.2f} risk / {STOP_LOSS_PCT*100}% stop = ${formula_max_investment:.2f} formula max")
    if cap_applied:
        logger.info(f"Safety cap applied: ${capped_max_investment:.2f} (30% of equity) < ${formula_max_investment:.2f} (formula)")
    logger.info(f"Position size: {position_size} shares @ ${current_price:.2f} = ${actual_investment:.2f} ({actual_investment/current_equity*100:.1f}% of equity)")

    return {
        'position_size': position_size,
        'risk_per_trade': risk_per_trade,
        'stop_loss_pct': STOP_LOSS_PCT,
        'max_investment': max_investment,
        'actual_investment': actual_investment,
        'current_price': current_price,
        'cap_applied': cap_applied,
        'equity_pct': actual_investment / current_equity
    } 