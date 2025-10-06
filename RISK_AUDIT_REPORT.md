# Risk Calculator Audit Report

**Date:** 2025-10-06
**Auditor:** Agent 3 - Risk Calculator Auditor
**Status:** ✅ COMPLETE - All Issues Resolved

---

## Executive Summary

The risk calculator audit identified a critical issue where position sizes could exceed buying power limits, potentially causing margin calls and rejected orders. This has been **successfully fixed** with a 30% position cap implementation.

### Key Findings

| Metric | Before Fix | After Fix | Status |
|--------|-----------|-----------|--------|
| Max position size | 40% of equity | 30% of equity | ✅ Fixed |
| 3 positions total | 120% of equity | 90% of equity | ✅ Safe |
| Margin call risk | HIGH | None | ✅ Eliminated |
| Buying power validation | None | Implemented | ✅ Added |

---

## 1. Problem Analysis

### Original Formula

```python
risk_per_trade = equity × 0.02  # 2% risk
max_investment = risk_per_trade / 0.05  # 5% stop loss
# Result: max_investment = equity × 0.40 (40%)
```

### Issue Identified

With **3 maximum concurrent positions**:
- Each position: 40% of equity
- Total exposure: **3 × 40% = 120% of equity**

**Problem:** Exceeds overnight buying power (1x equity)

### Impact

1. **Margin calls**: Positions would be force-liquidated at end of day
2. **Rejected orders**: Broker would reject orders exceeding buying power
3. **Trading disruption**: Bot couldn't execute strategy as designed
4. **Risk**: Unexpected liquidations at unfavorable prices

---

## 2. Buying Power Constraints

### Paper Trading Account Limits

| Period | Buying Power | Total Allowed |
|--------|--------------|---------------|
| Intraday | 2x equity | 200% |
| Overnight | 1x equity | 100% |

### Risk Scenarios (Before Fix)

**Standard Account ($100K)**

| Positions | Investment per Position | Total | % of Equity | Risk |
|-----------|------------------------|-------|-------------|------|
| 1 | $40,000 | $40,000 | 40% | ⚠️ High |
| 2 | $40,000 | $80,000 | 80% | ⚠️ Very High |
| 3 | $40,000 | **$120,000** | **120%** | 🚫 **EXCEEDS LIMITS** |

---

## 3. Solution Implemented

### Approach: Option B - Position Cap

**Why this approach?**
- ✅ Maintains standard 2% risk formula
- ✅ Explicit and easy to understand
- ✅ Provides clear safety valve
- ✅ Flexible for different scenarios

### Implementation

```python
# Added constants
MAX_POSITION_PCT = 0.30  # 30% cap per position

# Modified calculation
formula_max_investment = risk_per_trade / stop_loss_pct  # 40%
capped_max_investment = equity × MAX_POSITION_PCT        # 30%
max_investment = min(formula_max_investment, capped_max_investment)
```

### New Risk Scenarios (After Fix)

**Standard Account ($100K)**

| Positions | Investment per Position | Total | % of Equity | Status |
|-----------|------------------------|-------|-------------|--------|
| 1 | $30,000 | $30,000 | 30% | ✅ Safe |
| 2 | $30,000 | $60,000 | 60% | ✅ Safe |
| 3 | $30,000 | **$90,000** | **90%** | ✅ **SAFE** |

---

## 4. Buying Power Validation

### New Function: `validate_buying_power()`

```python
def validate_buying_power(equity, proposed_investment, open_positions):
    total_if_all_max = proposed_investment × MAX_POSITIONS
    safe_limit = equity × 0.90  # 90% threshold

    if total_if_all_max > safe_limit:
        return False, "Would exceed buying power limits"
    return True, ""
```

### Validation Logic

1. Calculate worst-case scenario (all 3 positions at max size)
2. Compare against 90% equity threshold
3. Reject if would exceed safe limits
4. Provide clear error message

---

## 5. Test Results

### Unit Tests: 19/19 Passed ✅

```
bot/risk/tests/test_risk.py           3 passed
bot/risk/tests/test_risk_with_cap.py  16 passed
```

### Test Coverage

- ✅ Standard accounts ($100K)
- ✅ Small accounts ($10K)
- ✅ Large accounts ($500K+)
- ✅ Expensive stocks (TSLA @ $350)
- ✅ Cheap stocks ($5)
- ✅ Edge cases (very expensive stocks, minimum accounts)
- ✅ Buying power validation
- ✅ Max positions rejection
- ✅ No signal rejection

### Stress Test Results

| Account Size | Stock Price | 3 Positions Total | % of Equity | Status |
|--------------|-------------|-------------------|-------------|--------|
| $5,000 | $150 | $4,500 | 90.0% | ✅ SAFE |
| $10,000 | $180 | $8,640 | 86.4% | ✅ SAFE |
| $100,000 | $180 | $89,640 | 89.6% | ✅ SAFE |
| $500,000 | $350 | $449,400 | 89.9% | ✅ SAFE |
| $1,000,000 | $450 | $899,100 | 89.9% | ✅ SAFE |

---

## 6. Position Size Examples

### Realistic Multi-Position Scenario

**Account:** $100,000

| Stock | Price | Shares | Investment | % of Equity |
|-------|-------|--------|------------|-------------|
| AAPL | $180.00 | 166 | $29,880 | 29.9% |
| MSFT | $410.00 | 73 | $29,930 | 29.9% |
| GOOGL | $140.00 | 214 | $29,960 | 30.0% |
| **TOTAL** | - | - | **$89,770** | **89.8%** |

**Remaining Cash:** $10,230 (10.2% buffer)

### Edge Cases Handled

1. **Very expensive stock + small account**
   - Account: $10,000, Stock: $5,000/share
   - Result: Rejected (position too small)
   - Prevents fractional share issues

2. **Cheap stock + large account**
   - Account: $500,000, Stock: $2.50/share
   - Max shares: 60,000 (still capped at $150K / 30%)
   - Prevents over-concentration

---

## 7. Risk Metrics Summary

### Current Risk Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Risk per trade** | 2% of equity | Standard risk management |
| **Stop loss** | 5% | Reasonable for volatile stocks |
| **Max positions** | 3 | Balanced diversification |
| **Position cap** | 30% | **NEW: Prevents buying power issues** |
| **Total exposure** | ~90% (with 3 positions) | Safe for overnight holding |

### Safety Margins

- **Overnight buffer**: 10% cash reserve
- **Volatility buffer**: Can handle 10% adverse moves
- **Margin call risk**: Eliminated
- **Force liquidation risk**: Eliminated

---

## 8. Files Modified/Created

### Core Implementation

| File | Changes | Status |
|------|---------|--------|
| `/bot/risk/risk.py` | Added position cap, buying power validation | ✅ Updated |

### Tests

| File | Purpose | Status |
|------|---------|--------|
| `/bot/risk/tests/test_risk.py` | Original tests (still pass) | ✅ Pass |
| `/bot/risk/tests/test_risk_with_cap.py` | Comprehensive cap tests | ✅ Created |
| `/test_risk_audit.py` | Audit analysis script | ✅ Created |
| `/test_final_risk_verification.py` | End-to-end verification | ✅ Created |

### Documentation

| File | Purpose | Status |
|------|---------|--------|
| `/RISK_PARAMETERS.md` | Complete risk documentation | ✅ Created |
| `/RISK_AUDIT_REPORT.md` | This audit report | ✅ Created |

---

## 9. Code Quality Improvements

### Added Features

1. **Constant definitions**: Centralized risk parameters
   ```python
   RISK_PER_TRADE_PCT = 0.02
   STOP_LOSS_PCT = 0.05
   MAX_POSITIONS = 3
   MAX_POSITION_PCT = 0.30
   ```

2. **Buying power validation**: Proactive checks
   ```python
   validate_buying_power(equity, investment, open_positions)
   ```

3. **Enhanced logging**: Clear audit trail
   ```python
   logger.info(f"Safety cap applied: ${capped_max} < ${formula_max}")
   ```

4. **Better return values**: More metadata
   ```python
   return {
       'position_size': shares,
       'cap_applied': bool,
       'equity_pct': float,
       # ... more fields
   }
   ```

5. **Minimum position check**: Prevents 0-share orders
   ```python
   if position_size < 1:
       logger.warning("Position too small")
       return None
   ```

---

## 10. Comparison: Before vs After

### Position Sizing

| Scenario | Before | After | Improvement |
|----------|--------|-------|-------------|
| Single position | 40% | 30% | ✅ -25% reduction |
| Three positions | 120% | 90% | ✅ 30% reduction |
| Buying power safety | None | Validated | ✅ Protection added |

### Risk Metrics

| Metric | Before | After |
|--------|--------|-------|
| Margin call risk | HIGH | **ZERO** ✅ |
| Overnight holding | Unsafe | **SAFE** ✅ |
| Position validation | Basic | **Comprehensive** ✅ |
| Error handling | Minimal | **Robust** ✅ |

---

## 11. Recommendations

### For Production Use

1. **Monitor actual broker responses**: Track any order rejections
2. **Log position sizes**: Analyze actual vs expected
3. **Alert on cap hits**: Know when 30% cap is applied
4. **Review after market moves**: Adjust if market conditions change

### Future Enhancements (Optional)

1. **Dynamic position sizing**: Adjust based on market volatility
2. **Individual stock limits**: Different caps for different risk levels
3. **Cash reserve requirements**: Explicit minimum cash balance
4. **Real-time buying power checks**: Query broker API directly

### Configuration Flexibility

If different risk profiles are needed:

```python
# More conservative (25% cap)
MAX_POSITION_PCT = 0.25  # 3 × 25% = 75%

# More aggressive (33% cap) - not recommended
MAX_POSITION_PCT = 0.33  # 3 × 33% = 99%
```

---

## 12. Verification Checklist

- ✅ **Formula verified**: Math is correct (2% risk / 5% stop)
- ✅ **Cap implemented**: 30% maximum per position
- ✅ **Validation added**: Buying power checks in place
- ✅ **Tests passing**: 19/19 unit tests pass
- ✅ **Edge cases handled**: Expensive stocks, small accounts, etc.
- ✅ **Documentation complete**: RISK_PARAMETERS.md created
- ✅ **Error handling**: Robust rejection logic
- ✅ **Logging enhanced**: Clear audit trail
- ✅ **Backward compatible**: Existing tests still pass
- ✅ **Production ready**: Safe for deployment

---

## 13. Conclusion

### Summary

The risk calculator audit successfully identified and resolved a critical buying power issue. The implementation:

1. **Maintains strategy integrity**: Still uses 2% risk per trade
2. **Ensures safety**: Positions capped at 30% of equity
3. **Prevents margin calls**: Total exposure limited to 90%
4. **Provides validation**: Buying power checks prevent overexposure
5. **Maintains effectiveness**: Position sizes still meaningful for testing

### Risk Status

| Risk Category | Status |
|---------------|--------|
| Margin calls | ✅ ELIMINATED |
| Buying power violations | ✅ PREVENTED |
| Order rejections | ✅ PREVENTED |
| Over-leverage | ✅ PREVENTED |
| Position sizing accuracy | ✅ VERIFIED |

### Final Verdict

**✅ APPROVED FOR PRODUCTION**

The risk calculator is now safe, well-tested, and properly documented. All position sizes respect buying power limits and prevent margin calls.

---

## Appendix A: Quick Reference

### Safe Position Sizes (100K Account)

| Stock Price | Max Shares | Investment | % of Equity |
|-------------|-----------|------------|-------------|
| $50 | 600 | $30,000 | 30% |
| $100 | 300 | $30,000 | 30% |
| $150 | 200 | $30,000 | 30% |
| $200 | 150 | $30,000 | 30% |
| $350 | 85 | $29,750 | 29.8% |
| $500 | 60 | $30,000 | 30% |

### Testing Commands

```bash
# Run all risk tests
python -m pytest bot/risk/tests/ -v

# Run comprehensive verification
python test_final_risk_verification.py

# Run original audit (shows before/after)
python test_risk_audit.py
```

### Key Files

- Implementation: `/Users/nick/Desktop/Summer2025Projects/vibe-trading/bot/risk/risk.py`
- Documentation: `/Users/nick/Desktop/Summer2025Projects/vibe-trading/RISK_PARAMETERS.md`
- Tests: `/Users/nick/Desktop/Summer2025Projects/vibe-trading/bot/risk/tests/`

---

**Report Generated:** 2025-10-06
**Agent:** Risk Calculator Auditor
**Status:** ✅ Complete
