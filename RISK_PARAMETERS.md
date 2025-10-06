# Risk Management Parameters

## Overview

This document explains the risk management system used in the Vibe Trading Bot. The system is designed to protect capital while allowing meaningful position sizes for effective backtesting and paper trading.

## Core Risk Parameters

### Constants (defined in `bot/risk/risk.py`)

| Parameter | Value | Description |
|-----------|-------|-------------|
| `RISK_PER_TRADE_PCT` | 0.02 (2%) | Maximum equity at risk per trade |
| `STOP_LOSS_PCT` | 0.05 (5%) | Stop-loss distance from entry |
| `MAX_POSITIONS` | 3 | Maximum concurrent open positions |
| `MAX_POSITION_PCT` | 0.30 (30%) | Maximum position size as % of equity |

## Position Sizing Formula

### Base Formula

The position size is calculated using the following risk management formula:

```
risk_per_trade = equity × RISK_PER_TRADE_PCT
formula_max_investment = risk_per_trade / STOP_LOSS_PCT
```

**Example (100K account):**
- Risk per trade: $100,000 × 0.02 = $2,000
- Formula max: $2,000 / 0.05 = $40,000 (40% of equity)

### Safety Cap Applied

To prevent buying power issues, a **30% cap** is applied:

```
max_investment = min(formula_max_investment, equity × MAX_POSITION_PCT)
```

**Result:**
- Without cap: $40,000 (40% of equity)
- With cap: $30,000 (30% of equity) ← **USED**

### Share Calculation

```
position_size = int(max_investment / current_price)
actual_investment = position_size × current_price
```

## Why the 30% Cap?

### The Problem

Without the cap, the formula allows positions up to 40% of equity:
- 1 position: 40% of equity
- 2 positions: 80% of equity
- **3 positions: 120% of equity** ← **EXCEEDS BUYING POWER**

### Paper Trading Buying Power

Paper trading accounts typically have:
- **2x buying power intraday**: Can use up to 2x equity during market hours
- **1x buying power overnight**: Must close positions within equity limits

**Problem:** 3 positions at 40% each = 120% of equity
- Exceeds overnight buying power → **Margin call risk**
- Positions would be force-liquidated

### The Solution

With 30% cap per position:
- 1 position: 30% of equity
- 2 positions: 60% of equity
- **3 positions: 90% of equity** ← **SAFE**

**Benefits:**
- Stays within overnight buying power (< 100%)
- 10% buffer for price fluctuations
- Avoids margin calls and forced liquidations
- Still meaningful position sizes for testing

## Buying Power Validation

The `validate_buying_power()` function provides an additional safety check:

```python
def validate_buying_power(equity, proposed_investment, open_positions):
    total_if_all_max = proposed_investment × MAX_POSITIONS
    safe_limit = equity × 0.90

    if total_if_all_max > safe_limit:
        return False, "Would exceed buying power limits"
    return True, ""
```

This ensures that even if all 3 positions are opened at maximum size, total exposure stays under 90% of equity.

## Position Size Examples

### Standard Account ($100,000)

| Stock | Price | Shares | Investment | % of Equity |
|-------|-------|--------|------------|-------------|
| AAPL | $180 | 166 | $29,880 | 29.9% |
| TSLA | $350 | 85 | $29,750 | 29.8% |
| SPY | $450 | 66 | $29,700 | 29.7% |

**3 positions total:** ~$89,640 (89.6% of equity) ✅

### Small Account ($10,000)

| Stock | Price | Shares | Investment | % of Equity |
|-------|-------|--------|------------|-------------|
| AAPL | $180 | 16 | $2,880 | 28.8% |
| SPY | $450 | 6 | $2,700 | 27.0% |
| QQQ | $380 | 7 | $2,660 | 26.6% |

**3 positions total:** ~$8,240 (82.4% of equity) ✅

### Large Account ($500,000)

| Stock | Price | Shares | Investment | % of Equity |
|-------|-------|--------|------------|-------------|
| TSLA | $350 | 428 | $149,800 | 30.0% |
| GOOGL | $140 | 1,071 | $149,940 | 30.0% |
| AMZN | $175 | 857 | $149,975 | 30.0% |

**3 positions total:** ~$449,715 (90.0% of equity) ✅

### Edge Cases

#### Very Expensive Stock ($5,000/share with $100K account)

| Parameter | Value |
|-----------|-------|
| Max investment | $30,000 (30% cap) |
| Shares | 6 |
| Actual investment | $30,000 |

Still respects the 30% cap ✅

#### Cheap Stock ($5/share with $10K account)

| Parameter | Value |
|-----------|-------|
| Max investment | $3,000 (30% cap) |
| Shares | 600 |
| Actual investment | $3,000 |

Still respects the 30% cap ✅

## Risk vs Reward Trade-offs

### Why Not Make Positions Smaller?

| Position % | 3 Positions | Safety | Effectiveness |
|-----------|-------------|--------|---------------|
| 20% | 60% | Very Safe | Too conservative |
| 25% | 75% | Safe | Moderate |
| **30%** | **90%** | **Safe** | **Optimal** ✅ |
| 33% | 99% | Risky | Aggressive |
| 40% | 120% | Unsafe | Too aggressive ❌ |

**30% strikes the best balance:**
- Large enough for meaningful testing
- Small enough to avoid margin issues
- Allows 3 simultaneous positions safely

### Why Not Use Dynamic Sizing?

We considered dynamic sizing based on open positions:
- 0 positions: 40% allowed
- 1 position: 35% allowed
- 2 positions: 30% allowed

**Why we chose fixed 30% instead:**
1. **Simpler to understand**: One rule for all positions
2. **More predictable**: Same behavior every time
3. **Safer**: No edge cases where 2 positions at 40% = 80%
4. **Easier to test**: Consistent behavior

## Validation Flow

```
New Signal Received
        ↓
Check if signal is valid (signal != 0)
        ↓
Check if max positions reached (< 3)
        ↓
Calculate position size with 30% cap
        ↓
Validate buying power (3 × position ≤ 90%)
        ↓
Execute trade or reject
```

## Error Messages

### Position Rejected - Max Positions

```
Max positions (3) exceeded
```

**Action:** Wait for a position to close before opening new ones.

### Position Rejected - Buying Power

```
Position would risk exceeding buying power limits.
With 3 positions at this size, total exposure would be $X (>90% of equity)
```

**Action:** This should never happen with 30% cap, but if it does, indicates a calculation error.

## Monitoring and Adjustments

### When to Adjust Parameters

Consider adjusting if:
1. **Account grows significantly**: Parameters scale automatically with equity
2. **Strategy changes**: Different strategies may need different risk profiles
3. **Market volatility changes**: Higher volatility may require smaller positions

### How to Adjust

Edit constants in `bot/risk/risk.py`:

```python
# For more aggressive (not recommended)
MAX_POSITION_PCT = 0.35  # 3 × 35% = 105% (risky!)

# For more conservative
MAX_POSITION_PCT = 0.25  # 3 × 25% = 75% (very safe)

# For different risk per trade
RISK_PER_TRADE_PCT = 0.015  # 1.5% risk (more conservative)
```

## Testing

Run tests to verify risk parameters:

```bash
# Unit tests
python -m pytest bot/risk/tests/test_risk.py -v

# Comprehensive tests with cap
python bot/risk/tests/test_risk_with_cap.py

# Audit current behavior
python test_risk_audit.py
```

## Summary

| Metric | Value | Status |
|--------|-------|--------|
| Risk per trade | 2% of equity | ✅ Standard |
| Stop loss | 5% | ✅ Standard |
| Max positions | 3 | ✅ Optimal |
| Position cap | 30% of equity | ✅ Safe |
| Total exposure | ~90% with 3 positions | ✅ Within limits |
| Margin call risk | None | ✅ Protected |

**Result:** Safe, effective risk management for paper trading and backtesting.

## References

- Formula derivation: `bot/risk/risk.py`
- Implementation: `calculate_position_size()` function
- Tests: `bot/risk/tests/test_risk_with_cap.py`
- Validation: `validate_buying_power()` function

---

**Last Updated:** 2025-10-06
**Version:** 1.0 (with 30% position cap)
