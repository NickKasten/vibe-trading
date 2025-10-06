# Alpaca Integration Fix - Multi-Agent Execution Plan

**Mission ID**: ALPACA-2025-10-06
**Date**: October 6, 2025
**Status**: Ready to Execute
**Priority**: CRITICAL

---

## Executive Summary

### Critical Finding
The trading bot has `simulate=True` hardcoded at `backend/app/main.py:151`, preventing ALL real Alpaca API calls. Despite valid credentials and 238 generated signals, ZERO trades have been executed.

### Mission Objective
1. Enable real Alpaca paper trading via configuration
2. Investigate why all 238 signals are "HOLD"
3. Validate entire stack (DB, API, frontend, deployment)
4. Achieve production-ready deployment

### Success Criteria
- ✅ `TRADING_MODE` environment variable implemented
- ✅ Test shows Alpaca API is called with simulate=False
- ✅ Root cause of HOLD-only signals identified
- ✅ All tests passing (157+new → ~175 total)
- ✅ Deployment configs updated
- ✅ Frontend integration validated

---

## Agent Team Composition

| Agent | Role | Domain | Wave | Duration |
|-------|------|--------|------|----------|
| 1 | Trading Integration Auditor | Alpaca API | 1 | 2hr |
| 2 | Signal Generation Investigator | SMA/RSI Strategy | 1 | 2hr |
| 3 | Database Integrity Validator | Schema & Data Flow | 1 | 1.5hr |
| 4 | Configuration & Deployment Auditor | Render, Env Vars | 2 | 1hr |
| 5 | Frontend Integration Tester | UI/API Contract | 2 | 1hr |
| 6 | Test Suite Completeness Reviewer | Coverage Gaps | 2 | 1.5hr |

**Total Agent Time**: 10 hours
**Estimated Wall Time**: 4.5 hours (with parallelization)
**Speedup Factor**: 2.2x

---

## Wave 1: Discovery & Root Cause Analysis

### Launch Command (Parallel - 3 agents simultaneously)

```python
# LAUNCH ALL THREE IN SINGLE MESSAGE
Task(subagent_type="general-purpose",
     description="Audit Alpaca integration",
     prompt=AGENT_1_PROMPT)

Task(subagent_type="general-purpose",
     description="Investigate signal strategy",
     prompt=AGENT_2_PROMPT)

Task(subagent_type="general-purpose",
     description="Validate database integrity",
     prompt=AGENT_3_PROMPT)
```

---

### Agent 1: Trading Integration Auditor

#### Full Prompt
```
Audit the Alpaca paper trading integration in this codebase. The main trading loop appears to have simulate=True hardcoded, preventing actual paper trades through Alpaca.

**Context**:
- Suspected Issue: simulate=True flag hardcoded at backend/app/main.py:151
- Evidence: Database shows 0 trades despite 238 signals generated over 3 days (June 23-26, 2025)
- Valid Credentials: ALPACA_API_KEY and ALPACA_SECRET_KEY exist in .env file
- Trading Symbols: AAPL primarily

**Investigation Tasks**:
1. **Trace Execution Flow**:
   - Start at backend/app/main.py line 151: execute_trade(position_size, symbol=symbol, side=side, simulate=True)
   - Follow into backend/app/services/broker/paper.py execute_trade() function
   - Identify what code executes when simulate=True vs simulate=False
   - Determine: Has the Alpaca API section (lines 116-169 in paper.py) EVER executed?

2. **Credential Validation**:
   - Check if ALPACA_API_KEY=PKB5GORB2ONB8VBTVVZ4 in .env is valid format
   - Check if ALPACA_SECRET_KEY exists and looks valid
   - Review ALPACA_BASE_URL = "https://paper-api.alpaca.markets" (correct endpoint?)

3. **API Connectivity Test** (READ-ONLY):
   - Attempt test call to Alpaca account endpoint to verify credentials work
   - If possible: GET https://paper-api.alpaca.markets/v2/account with headers
   - Report: Do credentials authenticate successfully?

4. **Analyze simulate_fill_price() Function**:
   - Location: paper.py lines 23-28
   - Issue: Returns random price between $100-$110
   - Problem: Should use actual market data from fetch_ohlcv()
   - Recommendation: How to fix?

5. **Configuration Strategy**:
   - Current: simulate flag is hardcoded True in main.py
   - Recommendation: Add TRADING_MODE environment variable?
   - Options: "simulate", "paper", "live"
   - Where to add: .env, render.yaml, code changes needed

6. **Error Handling Review**:
   - paper.py lines 125-169: Real API call section
   - Check: timeout handling, retry logic, rate limits
   - Check: Are API responses logged for debugging?

**Files to Investigate**:
- backend/app/main.py (lines 140-160, especially line 151)
- backend/app/services/broker/paper.py (entire file, focus on lines 81-169)
- .env (ALPACA_API_KEY, ALPACA_SECRET_KEY)
- render.yaml (check if TRADING_MODE or similar exists)
- logs/app.log (search for any Alpaca API response logs)

**Expected Deliverable Format**:

## Executive Summary
[1-2 sentences: simulate=True is hardcoded, preventing all real trades]

## Root Cause Analysis
### Hardcoded Simulation Flag
[Code snippet from main.py:151 showing simulate=True]
[Explanation: This forces execute_trade() to ALWAYS take simulation branch]

### API Section Never Executes
[Code from paper.py lines 98-114 vs 116-169]
[Proof: Lines 116-169 never run because simulate=True]

### Fake Price Generation
[simulate_fill_price() returns random $100-$110]
[Should use: actual market data from latest close price]

## API Connectivity Test Results
[Attempt to call Alpaca account endpoint]
[Result: Success/Failure, HTTP status code, response]

## Configuration Analysis
### Current State
[simulate flag hardcoded in main.py:151]

### Recommended Solution
[Add TRADING_MODE environment variable]
[Code changes: main.py, .env, render.yaml]

## Implementation Plan
**Step 1**: Add TRADING_MODE to .env
```env
TRADING_MODE=paper  # Options: simulate, paper, live
```

**Step 2**: Update main.py:151
```python
trading_mode = os.getenv("TRADING_MODE", "simulate")
simulate = (trading_mode == "simulate")
trade_result = execute_trade(position_size, symbol=symbol, side=side, simulate=simulate)
```

**Step 3**: Update render.yaml
[Add TRADING_MODE env var to both services]

**Step 4**: Fix simulate_fill_price()
[Use actual market data instead of random prices]

## Risk Assessment
[Low: Paper trading has no financial risk]
[Monitoring needed: API rate limits (500/day free tier)]

Return comprehensive analysis with code snippets proving the issue and clear implementation steps.
```

---

### Agent 2: Signal Generation Investigator

#### Full Prompt
```
Investigate why the trading bot generated 238 consecutive "HOLD" signals with zero BUY or SELL signals over a 3-day period.

**Context**:
- Strategy: SMA 20/50 Crossover with RSI 70/30 filter
- Symbol: AAPL (Apple Inc.)
- Time Period: June 23-26, 2025 (3 days, ~238 signals at 5-min intervals)
- Issue: All signals are "hold", none are "buy" or "sell"

**Database Evidence** (from comprehensive_database_report.md):
- Total signals recorded: 238
- Signal type distribution:
  - BUY: 0
  - SELL: 0
  - HOLD: 238 (100%)
- Signal strength range: 0.5 to 0.6 (all neutral/weak)
- AAPL price range: $201.00 to $201.56 (extremely tight, $0.56 range)
- Strategy: "sma_rsi" for all signals

**Investigation Tasks**:

1. **Review Signal Generation Logic**:
   - File: bot/strategy/signals.py, function generate_signals()
   - Lines to focus: 59-160 (entire function)
   - Understand: SMA 20/50 crossover logic (lines 111-112)
   - Understand: RSI filter (lines 111-112)
   - Question: What conditions must be met for BUY signal? For SELL signal?

2. **Data Sufficiency Check**:
   - Strategy requires: 50 days of historical data for SMA50 calculation
   - Check: bot/strategy/signals.py lines 47-57 (validate_data_sufficiency)
   - Look for: "Insufficient data for SMA50" warning in logs
   - Question: Is fallback strategy (10/20 SMA) being used? (lines 79-108)

3. **Validate Indicator Calculations**:
   - SMA20 calculation: lines 87-91
   - SMA50 calculation: lines 91-92
   - RSI calculation: lines 94-99
   - Test: Are formulas correct? Do they match standard definitions?

4. **Test with Synthetic Bullish Trend**:
   - Create test data: 60 days, close prices increasing from $90 → $110
   - Run: generate_signals(test_data)
   - Expected: Should generate BUY signals when SMA20 crosses above SMA50
   - Report: What signals are actually generated?

5. **Test with Synthetic Bearish Trend**:
   - Create test data: 60 days, close prices decreasing from $110 → $90
   - Run: generate_signals(test_data)
   - Expected: Should generate SELL signals when SMA20 crosses below SMA50
   - Report: What signals are actually generated?

6. **Market Conditions Analysis**:
   - Actual AAPL data: $201.00 to $201.56 range ($0.56 movement, 0.28%)
   - Question: Is this range too tight for SMA crossover to trigger?
   - Compare: Typical daily AAPL volatility is ~1-2%
   - Conclusion: Was market simply too flat for strategy to activate?

7. **Position-Aware Signal Logic**:
   - Lines 121-146: Existing position handling
   - Check: Are BUY signals suppressed if position already exists?
   - Check: Are SELL signals suppressed if no position exists?
   - Question: Could this be preventing signals?

8. **Parameter Sensitivity Analysis**:
   - Current RSI thresholds: 70 (overbought) / 30 (oversold)
   - Test: What if RSI thresholds were 65/35 (less strict)?
   - Current SMA periods: 20/50 days
   - Test: What if using 10/20 days (faster response)?

**Files to Investigate**:
- bot/strategy/signals.py (full file, especially generate_signals function)
- backend/app/services/fetcher.py (how much historical data is fetched?)
- backend/app/main.py (lines 90-110, signal generation call)
- Database: Query SELECT * FROM signals WHERE symbol='AAPL' ORDER BY timestamp DESC LIMIT 238

**Expected Deliverable Format**:

## Root Cause Analysis
[Primary reason: Insufficient data? Flat market? Strategy bug?]

## Data Sufficiency Check
### Historical Data Available
[How many days of AAPL data does bot have?]
[Is SMA50 calculable or using fallback?]

### Fallback Strategy Status
[Is 10/20 SMA fallback active? Evidence?]

## Indicator Calculation Validation
### SMA Calculation
[Verify formula matches: sum(last_N_prices) / N]
[Any bugs found?]

### RSI Calculation
[Verify formula matches standard: 100 - (100/(1+RS))]
[Any bugs found?]

## Synthetic Data Test Results
### Bullish Trend Test (90→110)
```
Data: [90, 91, 92, ..., 110] over 60 days
Signals Generated: [list of signals]
Conclusion: BUY signals DO/DON'T generate with trending data
```

### Bearish Trend Test (110→90)
```
Data: [110, 108, 106, ..., 90] over 60 days
Signals Generated: [list of signals]
Conclusion: SELL signals DO/DON'T generate with trending data
```

## Market Conditions Analysis
### AAPL Volatility June 23-26
- Price Range: $201.00 - $201.56 ($0.56, 0.28%)
- Typical Daily Volatility: ~1-2%
- **Conclusion**: Market was extremely flat (10x below normal)
- **Impact**: SMA crossovers unlikely in ranging market

## Position-Aware Logic Review
[Are signals being suppressed due to existing/no position?]
[Is this logic working as intended?]

## Recommendations
1. **If Insufficient Data**: Wait for 50+ days of history OR use fallback strategy
2. **If Flat Market**: Expected behavior - no action until trends emerge
3. **If Strategy Bug**: [Specific fix needed]
4. **Parameter Tuning**:
   - Consider: RSI 70/30 → 65/35 (more sensitive)
   - Consider: SMA 20/50 → 10/20 (faster response)
   - Trade-off: More signals vs more false signals

## Testing Recommendations
[Backtest strategy on historical AAPL data from volatile period]
[Validate strategy generates expected signals in trending markets]

Return detailed analysis with test results showing when signals DO generate successfully.
```

---

### Agent 3: Database Integrity Validator

#### Full Prompt
```
Validate the database layer is production-ready after recent schema changes and new position deletion functionality.

**Context**:
- Recent Changes:
  1. Added delete_position() method to DatabaseOperations class
  2. Standardized field names to "average_entry_price" across all layers
  3. Fixed test mocks for Supabase query chains
- Database: Supabase (PostgreSQL)
- Current State: 0 trades, 0 positions, 1 equity record ($100k initial), 238 signals

**Investigation Tasks**:

1. **Schema Validation**:
   - Compare: backend/app/db/schema.sql vs backend/app/db/models.py
   - Check: Do Pydantic model fields match SQL column names exactly?
   - Check: Do data types align (DECIMAL vs float, VARCHAR length, etc.)?
   - Look for: Any field name mismatches (e.g., "entry_price" vs "average_entry_price")

2. **Test Position Deletion**:
   - New method: backend/app/db/operations.py lines 67-76 (delete_position)
   - Implementation: backend/app/main.py lines 212-216 (position close logic)
   - Test scenario:
     1. Create test position in database
     2. Call delete_position('AAPL')
     3. Verify position is actually removed
   - Check: Error handling if position doesn't exist
   - Check: Returns boolean success/failure correctly

3. **Trace Complete Trade Cycle**:
   - **BUY Trade**:
     1. Initial state: $100k cash, 0 positions
     2. BUY 100 shares AAPL @ $200 = $20k spent
     3. Expected: Cash = $80k, Position = 100 shares @ $200 avg
     4. Verify: equity.cash updated correctly
     5. Verify: positions table has correct entry
   - **SELL Trade** (Partial):
     1. SELL 50 shares @ $210
     2. Expected: Cash = $90.5k, Position = 50 shares @ $200 avg
     3. Verify: Position updated, not deleted
   - **SELL Trade** (Complete):
     1. SELL remaining 50 shares @ $210
     2. Expected: Cash = $100.5k, Position DELETED
     3. Verify: delete_position() was called
     4. Verify: positions table is empty

4. **Constraint Testing**:
   - **UNIQUE Constraints**:
     - trades.order_id: Try inserting duplicate order_id
     - positions.symbol: Try inserting duplicate AAPL position
     - equity.timestamp: Try inserting same timestamp twice
     - signals.(symbol, timestamp, strategy): Try duplicate composite
   - Expected: All should fail with constraint violation
   - Verify: Error handling in operations.py catches these

5. **Upsert Logic Validation**:
   - Positions: operations.py lines 52-60 (upsert with on_conflict='symbol')
   - Equity: operations.py lines 67-75 (upsert with on_conflict='timestamp')
   - Signals: operations.py lines 91-99 (upsert with composite key)
   - Test: Does ON CONFLICT properly update existing records?

6. **Index Performance**:
   - schema.sql lines 54-61: Defined indexes
   - Check: Are all frequently queried columns indexed?
   - Missing indexes? (e.g., WHERE side='buy' on trades?)
   - Recommendation: Any additional indexes needed?

**Files to Investigate**:
- backend/app/db/schema.sql (full schema definition)
- backend/app/db/models.py (Pydantic models)
- backend/app/db/operations.py (database operations, especially delete_position)
- backend/app/main.py (lines 161-240: position/equity update logic)
- comprehensive_database_report.md (current database state)

**Expected Deliverable Format**:

## Schema Validation Results
### Fields Comparison
| Table | SQL Column | Pydantic Field | Match? | Issue |
|-------|-----------|----------------|--------|-------|
| trades | order_id | order_id | ✅ | None |
| positions | average_entry_price | average_entry_price | ✅ | Fixed |
[Complete table for all fields]

### Data Type Alignment
[Any DECIMAL vs float mismatches?]
[VARCHAR length sufficient?]

## Position Deletion Test
### Test Execution
```sql
-- Setup
INSERT INTO positions (symbol, quantity, average_entry_price, current_price, unrealized_pnl, timestamp)
VALUES ('TEST', 100, 200.00, 200.00, 0, NOW());

-- Delete
[Call delete_position('TEST')]

-- Verify
SELECT * FROM positions WHERE symbol='TEST';
-- Expected: 0 rows
```

### Results
[Success/Failure]
[Any errors encountered?]

## Complete Trade Cycle Validation
### BUY Trade
[Step-by-step verification with SQL queries]
[Screenshots or output showing correct cash/position updates]

### Partial SELL Trade
[Verify position reduced, not deleted]

### Complete SELL Trade
[Verify position deleted via delete_position()]

## Constraint Violation Tests
### Duplicate order_id (trades)
[Test result: Constraint enforced? ✅/❌]

### Duplicate symbol (positions)
[Test result: Constraint enforced? ✅/❌]

### Duplicate timestamp (equity)
[Test result: Constraint enforced? ✅/❌]

### Duplicate composite (signals)
[Test result: Constraint enforced? ✅/❌]

## Upsert Logic Validation
### Position Upsert
[Does updating existing symbol work correctly?]

### Equity Upsert
[Does same timestamp update rather than error?]

### Signals Upsert
[Does composite key conflict update properly?]

## Performance & Indexing
### Current Indexes
[List from schema.sql lines 54-61]

### Query Performance
[Are common queries using indexes?]

### Recommendations
[Any missing indexes for frequent WHERE clauses?]

## Issues Found
[List any problems discovered]

## Production Readiness
[✅ Ready / ❌ Blockers found]

Return comprehensive validation with test results and SQL queries demonstrating all assertions.
```

---

## Wave 2: Configuration, Testing & Frontend

**Dependency**: Requires Wave 1 Agent 1 completion (TRADING_MODE recommendation)

### Launch Command (Parallel - 3 agents simultaneously)

```python
# AFTER WAVE 1 COMPLETES, LAUNCH WAVE 2
Task(subagent_type="general-purpose",
     description="Audit deployment configuration",
     prompt=AGENT_4_PROMPT)

Task(subagent_type="general-purpose",
     description="Test frontend integration",
     prompt=AGENT_5_PROMPT)

Task(subagent_type="general-purpose",
     description="Review test suite coverage",
     prompt=AGENT_6_PROMPT)
```

---

### Agent 4: Configuration & Deployment Auditor

#### Full Prompt
```
Audit deployment configuration for production readiness after adding TRADING_MODE environment variable (per Agent 1 recommendation).

**Context**:
- Agent 1 Finding: Need to add TRADING_MODE env var to enable/disable Alpaca paper trading
- Deployment: Render.com (qualquant-api web service + qualquant-bot worker)
- Frontend: Vercel
- Current env vars: ALPACA_API_KEY, ALPACA_SECRET_KEY, SUPABASE_URL, SUPABASE_KEY, etc.

**Investigation Tasks**:

1. **Environment Variable Audit**:
   - Compare: .env (local) vs render.yaml (production config)
   - Identify: Missing vars in production
   - Check: All required vars present for both services (api + bot)?
   - Verify: Sensitive vars (API keys) marked sync: false

2. **Add TRADING_MODE Configuration**:
   - Local: Add to .env
   - Production: Add to render.yaml for both services
   - Default value: "simulate" (safe default)
   - Production value: "paper" (enable Alpaca)
   - Documentation: Add comment explaining options

3. **Render Service Configuration**:
   - qualquant-api (web service):
     - Port: 8000
     - RUN_MODE: api
     - Health check: /health endpoint
   - qualquant-bot (worker):
     - RUN_MODE: bot
     - TRADING_SYMBOL: AAPL
     - TRADING_INTERVAL: 300 (5 minutes)
   - Verify: Correct service types and env vars for each

4. **Dockerfile Review**:
   - Dockerfile.api: Check for optimization opportunities
   - Dockerfile.bot: Check for optimization opportunities
   - Multi-stage builds?: Could reduce image size
   - Layer caching?: Is COPY optimized?

5. **Security Audit**:
   - Grep for hardcoded API keys: `grep -r "ALPACA_API_KEY\|SUPABASE_KEY" backend/ --exclude=".env"`
   - Check: Are all secrets in .env or render.yaml, NOT in code?
   - Review: .gitignore includes .env file
   - Check: No credentials committed to git history

6. **Health Checks & Monitoring**:
   - API health: /health endpoint (backend/app/utils/health.py)
   - Status endpoint: /api/status (requires auth)
   - Verify: Both endpoints return proper status codes
   - Check: Logging configured for production debugging

**Files to Investigate**:
- .env (local development environment variables)
- render.yaml (production deployment configuration)
- Dockerfile.api, Dockerfile.bot
- backend/app/core/server.py (server modes)
- backend/app/utils/health.py (health check implementation)
- .gitignore (verify .env is excluded)

**Expected Deliverable Format**:

## Environment Variable Comparison
| Variable | .env (Local) | render.yaml (API) | render.yaml (Bot) | Status |
|----------|--------------|-------------------|-------------------|--------|
| TRADING_MODE | ✅ Added | ❌ Missing | ❌ Missing | ACTION NEEDED |
| ALPACA_API_KEY | ✅ | ✅ | ✅ | ✅ |
[Complete table]

## TRADING_MODE Configuration

### .env Update
```env
# Trading mode: simulate (local testing), paper (Alpaca paper), live (real money)
TRADING_MODE=simulate
```

### render.yaml Update
```yaml
services:
  - type: web
    name: qualquant-api
    envVars:
      - key: TRADING_MODE
        value: "paper"  # Enable Alpaca paper trading

  - type: worker
    name: qualquant-bot
    envVars:
      - key: TRADING_MODE
        value: "paper"  # Enable Alpaca paper trading
```

## Service Configuration Validation
### qualquant-api (Web Service)
[Verify all settings correct]

### qualquant-bot (Worker)
[Verify all settings correct]

## Dockerfile Analysis
### Optimization Opportunities
[Multi-stage builds? Layer caching improvements?]

### Current Issues
[Any problems found?]

## Security Audit Results
### Hardcoded Secrets Check
[grep results - should find NONE in code]

### .gitignore Validation
[.env excluded? ✅]

### Git History
[Any credentials in commit history? Check: git log --all --full-history --source -- .env]

## Health Check Validation
### /health Endpoint
[Test: curl http://localhost:8000/health]
[Expected: {"status": "healthy"}]

### /api/status Endpoint
[Test: curl -H "X-API-Key: test-key" http://localhost:8000/api/status]
[Expected: {"status": {"api": "healthy", "database": "healthy"}, ...}]

## Production Readiness Checklist
- [ ] TRADING_MODE added to .env
- [ ] TRADING_MODE added to render.yaml (both services)
- [ ] No hardcoded secrets in code
- [ ] .env in .gitignore
- [ ] Health checks functional
- [ ] Logging configured
- [ ] Dockerfiles optimized

## render.yaml Changes Needed
[Provide complete diff or updated file sections]

Return comprehensive audit with specific render.yaml updates ready to apply.
```

---

### Agent 5 & 6 Prompts

*(Due to length, condensed versions - full prompts follow same detailed structure as above)*

**Agent 5**: Verify frontend (frontend/components/*.js) uses `average_entry_price` field, test API client error handling, validate empty states

**Agent 6**: Identify untested code paths (position deletion, TRADING_MODE flag, simulate=False), review mock quality, add missing tests

---

## Wave 3: Orchestrator Implementation

**Duration**: 1 hour

**Process**:
1. Aggregate all agent findings
2. Identify any conflicts
3. Create prioritized fix list
4. Apply changes sequentially:
   - Add TRADING_MODE to .env
   - Update main.py:151 to use TRADING_MODE
   - Update render.yaml with new env var
   - Fix simulate_fill_price() if needed
   - Add any missing tests
   - Update frontend if field mismatches found

---

## Wave 4: Final Validation

**Duration**: 30 minutes

**Checklist**:
- [ ] Run full test suite: `pytest backend/tests`
- [ ] Test with TRADING_MODE=simulate (verify no regression)
- [ ] Test with TRADING_MODE=paper (dry run, check logs)
- [ ] Build frontend: `cd frontend && npm run build`
- [ ] Review all agent reports for consistency
- [ ] Generate deployment checklist

---

## Risk Assessment

### Technical Risks
| Risk | Severity | Mitigation |
|------|----------|------------|
| Alpaca credentials invalid | Medium | Agent 1 tests credentials |
| Signal strategy needs tuning | Low | Agent 2 analyzes thoroughly |
| Database issues | Low | Agent 3 validates completely |
| Frontend breaks | Low | Agent 5 tests integration |

### Deployment Risks
| Risk | Severity | Mitigation |
|------|----------|------------|
| Rate limit violations | Low | 500 calls/day limit, monitor |
| Configuration errors | Low | Agent 4 validates render.yaml |
| Zero downtime? | Low | Render handles gracefully |

---

## Success Metrics

### Immediate (Post-Mission)
- ✅ TRADING_MODE implemented and working
- ✅ Agent 1 confirms Alpaca API callable
- ✅ Agent 2 explains HOLD-only signals
- ✅ All tests passing
- ✅ Documentation updated

### Short-Term (Next 24 Hours)
- ✅ First paper trade executes successfully
- ✅ Trade appears in database with real price (not $100-$110)
- ✅ Position management works (BUY → SELL → delete)

### Long-Term (Next Week)
- ✅ 50+ days of data enables full SMA50 strategy
- ✅ BUY/SELL signals generate in trending markets
- ✅ Frontend displays trades correctly
- ✅ No API errors or rate limit issues

---

## Rollback Plan

If critical issues found:
1. **Immediate**: Set TRADING_MODE=simulate in production
2. **Code**: Keep simulate=True in main.py until fixed
3. **Deploy**: Revert render.yaml to previous version
4. **Investigate**: Relaunch problematic agent with refined prompt

---

## Timeline

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Wave 1 (parallel) | 2hr | 2hr |
| Wave 2 (parallel) | 1.5hr | 3.5hr |
| Wave 3 (sequential) | 1hr | 4.5hr |
| Wave 4 (validation) | 30min | 5hr |

**Total**: 5 hours wall time (vs 10hr sequential)

---

## Next Steps

1. ✅ **Approve This Plan**: Confirm ready to launch agents
2. 🚀 **Execute Wave 1**: Launch Agents 1-3 in parallel
3. ⏳ **Monitor Progress**: Check agent status every 15-30 minutes
4. 🔍 **Wave 2 Launch**: After Agent 1 completes
5. 🎯 **Aggregate & Implement**: Orchestrator Wave 3
6. ✅ **Final Validation**: Wave 4 checklist
7. 📝 **Update Lessons Learned**: Capture findings for future missions

**Status**: READY TO LAUNCH - Awaiting approval to begin Wave 1
