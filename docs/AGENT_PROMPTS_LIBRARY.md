# Agent Prompts Library

## Purpose
Reusable, optimized prompt templates for each specialized agent. Copy, customize with project-specific variables, and launch.

---

## Trading Integration Auditor

### Template
```
Audit the {INTEGRATION_NAME} trading integration in backend/app/services/broker/{BROKER}.py.

**Context**:
- Suspected Issue: {ISSUE_DESCRIPTION}
- Evidence: {SYMPTOMS (e.g., "0 trades in DB despite signals")}
- Location: {FILE_PATH}:{LINE_NUMBER}

**Investigation Tasks**:
1. Trace execution flow from {ENTRY_POINT} to actual API call
2. Check if {INTEGRATION_NAME} API credentials in .env are valid
3. Test connectivity: Make a test call to {API_ENDPOINT} (read-only if possible)
4. Review execute_trade() function - identify all code paths (simulate vs real)
5. Check for hardcoded flags preventing real execution
6. Audit error handling: retry logic, timeout handling, rate limits
7. Review logging: Are API responses captured for debugging?

**Files to Investigate**:
- {MAIN_TRADING_LOOP_FILE}
- {BROKER_INTEGRATION_FILE}
- .env (credentials)
- {CONFIG_FILE} (if applicable)

**Expected Deliverable**:
## Executive Summary
[1-2 sentences: What's broken and why]

## Root Cause Analysis
[Detailed findings with code snippets showing the issue]

## API Connectivity Test Results
[Output from test API call attempt]

## Configuration Issues
[Missing env vars, hardcoded values, etc.]

## Recommendations
1. Immediate Fix: [One-liner change needed]
2. Configuration: [Env vars to add]
3. Long-term: [Architecture improvements]

## Implementation Plan
- [ ] File: {file}:{line} - Change X to Y
- [ ] File: {file} - Add configuration for Z
- [ ] Test: Verify API call succeeds with real credentials
```

### Alpaca Example (This Project)
```
Audit the Alpaca trading integration in backend/app/services/broker/paper.py.

**Context**:
- Suspected Issue: simulate=True flag hardcoded, preventing real Alpaca API calls
- Evidence: 0 trades in database despite 238 signals generated over 3 days
- Location: backend/app/main.py:151

**Investigation Tasks**:
1. Trace execution flow from main.py:151 execute_trade() call to Alpaca API
2. Check if ALPACA_API_KEY and ALPACA_SECRET_KEY in .env are valid
3. Test connectivity: Make test call to https://paper-api.alpaca.markets/v2/account
4. Review execute_trade() in paper.py - what happens when simulate=True vs False?
5. Check for hardcoded simulate flag in main.py trading cycle
6. Audit error handling in paper.py lines 125-169 (real API call section)
7. Review logging: Would we see Alpaca API responses if calls were made?

**Files to Investigate**:
- backend/app/main.py (line 151 and surrounding context)
- backend/app/services/broker/paper.py (entire file, especially lines 81-169)
- .env (ALPACA_API_KEY, ALPACA_SECRET_KEY)
- render.yaml (production env var configuration)

**Expected Deliverable**:
[Follow template format above with specific findings]

Return detailed analysis with code snippets showing exactly why simulate=True is preventing trading.
```

---

## Signal Generation Investigator

### Template
```
Investigate why the trading bot's signal generation is producing {UNEXPECTED_BEHAVIOR}.

**Context**:
- Strategy: {STRATEGY_NAME (e.g., "SMA/RSI Crossover")}
- Issue: {SPECIFIC_PROBLEM (e.g., "All 238 signals are HOLD, no BUY/SELL")}
- Time Period: {DATE_RANGE}
- Symbol(s): {TRADING_SYMBOLS}

**Database Evidence**:
- Total signals: {COUNT}
- Signal distribution: {BUY_COUNT} buy, {SELL_COUNT} sell, {HOLD_COUNT} hold
- Strength range: {MIN_STRENGTH} to {MAX_STRENGTH}
- Price range: ${LOW_PRICE} to ${HIGH_PRICE}

**Investigation Tasks**:
1. Review signal generation logic in {SIGNALS_FILE}
2. Check data sufficiency: Does bot have {REQUIRED_HISTORY} days for {INDICATOR}?
3. Validate indicator calculations: {INDICATOR_LIST}
4. Test with synthetic bullish data: prices increasing from $90 → $110 over 60 days
5. Test with synthetic bearish data: prices decreasing from $110 → $90 over 60 days
6. Check if fallback strategy is being used (insufficient data?)
7. Review position-aware signal logic: Are signals suppressed when position exists?
8. Analyze actual market data from {DATE_RANGE}: Was market ranging (no trends)?

**Files to Investigate**:
- {SIGNALS_FILE} (full signal generation logic)
- {FETCHER_FILE} (market data retrieval)
- Database: signals table (query last {COUNT} signals)

**Expected Deliverable**:
## Root Cause
[Why strategy isn't generating expected signals]

## Data Sufficiency Analysis
[Do we have enough historical data? Show calculation]

## Test Results
### Synthetic Bullish Trend Test
[Signal output with uptrending data]

### Synthetic Bearish Trend Test
[Signal output with downtrending data]

## Market Conditions Analysis
[Was actual market too flat for strategy to trigger?]

## Recommendations
1. Parameter Tuning: [Adjust X from Y to Z]
2. Strategy Selection: [Use fallback strategy? Different indicators?]
3. Data Requirements: [Wait for more history? Use shorter periods?]

Return comprehensive analysis with test data showing when signals DO generate.
```

### This Project Example
```
Investigate why the trading bot generated 238 consecutive "HOLD" signals with zero BUY or SELL signals.

**Context**:
- Strategy: SMA 20/50 Crossover with RSI 70/30 filter
- Issue: All signals are HOLD despite 3 days of trading
- Time Period: June 23-26, 2025
- Symbol: AAPL

**Database Evidence** (from comprehensive_database_report.md):
- Total signals: 238
- Signal distribution: 0 buy, 0 sell, 238 hold
- Strength range: 0.5 to 0.6 (all neutral)
- Price range: $201.00 to $201.56 (very tight range)

**Investigation Tasks**:
1. Review signal generation in bot/strategy/signals.py
2. Check if bot has 50+ days of AAPL data for SMA50 calculation
3. Validate SMA and RSI calculations match expected formulas
4. Test with synthetic bullish trend: Close prices [90, 92, 94, ..., 110] over 60 days
5. Test with bearish trend: Close prices [110, 108, 106, ..., 90] over 60 days
6. Check if fallback strategy (10/20 SMA) was used
7. Are buy signals suppressed due to existing position?
8. Was AAPL market too flat ($201 ± $0.56) for crossover to trigger?

**Files to Investigate**:
- bot/strategy/signals.py (generate_signals function)
- backend/app/services/fetcher.py (how much history is fetched?)
- Database signals table (all 238 records)

**Expected Deliverable**:
[Follow template above - focus on whether issue is: insufficient data, flat market, or strategy bug]
```

---

## Quick Reference: All Agent Prompts

Due to space constraints, see full templates for remaining agents online or expand this file as needed.

**Agent 3 - Database Integrity Validator**: Focus on schema.sql vs models.py alignment, constraint testing, data flow validation

**Agent 4 - Configuration & Deployment Auditor**: Compare .env vs render.yaml, security audit, health checks

**Agent 5 - Frontend Integration Tester**: API field names, error handling, component empty states

**Agent 6 - Test Suite Completeness Reviewer**: Coverage analysis, mock quality, missing test identification

---

## Prompt Optimization Tips

### 1. Be Specific
- ✅ "Check backend/app/main.py line 151"
- ❌ "Check the trading code"

### 2. Provide Context
- ✅ "Evidence: 0 trades in DB despite 238 signals"
- ❌ "Trading isn't working"

### 3. Define Expected Output
- ✅ "Return: Root cause + test results + implementation plan"
- ❌ "Figure out what's wrong"

### 4. Include Evidence
- ✅ "Database shows 238 signals, all 'hold', price $201±$0.56"
- ❌ "Signals seem wrong"

### 5. Set Scope
- ✅ "Investigate lines 80-170 in paper.py"
- ❌ "Review everything"

---

## Customization Variables

When using templates, replace these placeholders:

| Variable | Example |
|----------|---------|
| {INTEGRATION_NAME} | Alpaca, Interactive Brokers, TD Ameritrade |
| {ISSUE_DESCRIPTION} | "simulate=True hardcoded" |
| {SYMPTOMS} | "0 trades in DB" |
| {FILE_PATH} | backend/app/main.py |
| {LINE_NUMBER} | 151 |
| {STRATEGY_NAME} | SMA/RSI Crossover |
| {REQUIRED_HISTORY} | 50 days |
| {INDICATOR_LIST} | SMA20, SMA50, RSI |

---

## Version History
- v1.0 (2025-10-06): Initial library with 2 detailed templates + quick ref
- v1.1 (planned): Expand remaining 5 agent templates to full detail
