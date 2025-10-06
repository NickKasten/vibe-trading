# Agent Team Catalog

## Overview

This catalog documents all specialized agent types available for multi-agent orchestration. Each agent has specific expertise, optimal use cases, and reusable characteristics.

**Total Agent Types**: 7 core specialists + orchestrator

---

## Core Specialized Agents

### 1. Trading Integration Auditor

**Type**: `general-purpose`
**Specialty**: External API integrations, broker connections, order execution flows
**Domain Expertise**: REST APIs, authentication, WebSocket connections, order lifecycle

**Best Used For**:
- ✅ Validating broker integrations (Alpaca, Interactive Brokers, Robinhood, TD Ameritrade)
- ✅ Testing API connectivity and credentials
- ✅ Debugging order execution failures
- ✅ Auditing trade flow from signal → execution → confirmation
- ✅ Reviewing rate limits and error handling

**Key Capabilities**:
- Trace execution paths through multiple files
- Make test API calls to validate connectivity
- Read API documentation and compare to implementation
- Identify hardcoded flags vs configurable behavior
- Recommend environment variable strategies

**Typical Deliverables**:
- Root cause analysis of integration failures
- API connectivity test results
- Configuration recommendations
- Implementation plan with file:line changes

**Example Tasks**:
```
- "Why is simulate=True hardcoded in main.py?"
- "Test if Alpaca paper API credentials are valid"
- "Trace order execution from signal to database"
- "Review error handling for API timeout scenarios"
```

**Common Findings**:
- Hardcoded simulation flags preventing real trading
- Invalid/expired API credentials
- Missing retry logic for transient errors
- Rate limit violations
- Improper error propagation

---

### 2. Signal Generation Investigator

**Type**: `general-purpose`
**Specialty**: Trading strategy logic, technical indicators, signal generation algorithms
**Domain Expertise**: Pandas, NumPy, indicator math (SMA, RSI, MACD), strategy backtesting

**Best Used For**:
- ✅ Debugging why signals aren't generating (all HOLD)
- ✅ Strategy parameter optimization
- ✅ Indicator calculation validation
- ✅ Testing signal logic with synthetic market data
- ✅ Backtesting strategy performance

**Key Capabilities**:
- Understand technical indicator formulas
- Generate test data with specific characteristics (trending, ranging, volatile)
- Trace signal calculation from raw data to final buy/sell/hold
- Recommend parameter adjustments based on market conditions
- Identify data sufficiency issues (not enough history)

**Typical Deliverables**:
- Root cause of signal generation issues
- Strategy parameter recommendations
- Test results with synthetic data
- Performance analysis of different parameter sets

**Example Tasks**:
```
- "Why are all 238 signals 'HOLD'?"
- "Test signal generation with bullish trending data"
- "Validate SMA crossover calculation accuracy"
- "Recommend RSI threshold adjustments"
```

**Common Findings**:
- Insufficient historical data (need 50+ days for SMA50)
- Strategy parameters too conservative (RSI 70/30 → 65/35)
- Market in ranging phase (no crossovers)
- Indicator calculation bugs (off-by-one errors)
- Position-aware signal suppression working correctly

---

### 3. Database Integrity Validator

**Type**: `general-purpose`
**Specialty**: Schema design, data consistency, transaction integrity, SQL optimization
**Domain Expertise**: PostgreSQL, Supabase, Pydantic models, database migrations

**Best Used For**:
- ✅ Schema validation before deployment
- ✅ Testing unique constraints and foreign keys
- ✅ Verifying data flow consistency (trades → positions → equity)
- ✅ Auditing upsert logic and conflict handling
- ✅ Performance testing (indexes, query optimization)

**Key Capabilities**:
- Cross-reference schema.sql with ORM models
- Test constraint violations (duplicate keys, etc.)
- Trace data flow through create/update/delete operations
- Validate transaction isolation and rollback handling
- Identify missing indexes

**Typical Deliverables**:
- Schema validation report
- Data integrity test results
- Performance optimization recommendations
- Missing constraint/index identification

**Example Tasks**:
```
- "Verify schema.sql matches Pydantic models"
- "Test delete_position() method actually removes records"
- "Trace equity calculation from trades + positions"
- "Check if UNIQUE constraints are properly enforced"
```

**Common Findings**:
- Field name mismatches (average_entry_price vs avg_price)
- Missing cascade deletes
- Upsert conflicts not handled
- Missing indexes on frequently queried columns
- Data type mismatches (DECIMAL vs float)

---

### 4. Configuration & Deployment Auditor

**Type**: `general-purpose`
**Specialty**: Environment variables, secrets management, deployment configs, infrastructure
**Domain Expertise**: Docker, Render, Vercel, env vars, YAML, CI/CD

**Best Used For**:
- ✅ Pre-deployment environment validation
- ✅ Comparing local .env vs production configs
- ✅ Security audits (exposed secrets, hardcoded keys)
- ✅ Dockerfile optimization
- ✅ Health check and monitoring setup

**Key Capabilities**:
- Compare env vars across environments (local/staging/prod)
- Detect hardcoded secrets in code
- Validate service configurations (workers, web servers)
- Review health check endpoints
- Audit logging and monitoring setup

**Typical Deliverables**:
- Environment parity report
- Security audit findings
- Deployment readiness checklist
- render.yaml/vercel.json updates

**Example Tasks**:
```
- "Compare .env with render.yaml env vars"
- "Grep for hardcoded API keys in codebase"
- "Add TRADING_MODE to render.yaml"
- "Validate Dockerfile multi-stage build"
```

**Common Findings**:
- Missing env vars in production
- Secrets committed to repo
- Misconfigured service types (web vs worker)
- Missing health checks
- Inefficient Docker layers

---

### 5. Frontend Integration Tester

**Type**: `general-purpose`
**Specialty**: UI/API integration, component testing, error handling, user experience
**Domain Expertise**: React/Next.js, API clients, error boundaries, state management

**Best Used For**:
- ✅ Verifying frontend consumes backend API correctly
- ✅ Testing component error states
- ✅ Field name alignment between API and UI
- ✅ Empty state and loading state testing
- ✅ API client error handling validation

**Key Capabilities**:
- Trace data flow from API response to UI rendering
- Test components with various data scenarios
- Validate API client retry logic
- Check for snake_case ↔ camelCase mismatches
- Review user-facing error messages

**Typical Deliverables**:
- API integration test results
- Field name mismatch list
- Component error handling validation
- UX improvement recommendations

**Example Tasks**:
```
- "Check if PortfolioSummary uses average_entry_price or avg_price"
- "Test API client with 500 error response"
- "Validate components handle empty positions array"
- "Verify disclaimer banner appears on all pages"
```

**Common Findings**:
- Field name mismatches (backend changed, frontend didn't)
- Poor error handling (crashes instead of showing message)
- Missing empty states
- Hardcoded API URLs instead of env vars
- Stale data not indicated to user

---

### 6. Test Suite Completeness Reviewer

**Type**: `general-purpose`
**Specialty**: Test coverage analysis, mock quality, integration testing, CI/CD
**Domain Expertise**: pytest, unittest, mocking, fixtures, coverage tools

**Best Used For**:
- ✅ Identifying untested code paths
- ✅ Reviewing mock quality (too permissive?)
- ✅ Adding missing test cases
- ✅ Integration test design
- ✅ CI/CD pipeline optimization

**Key Capabilities**:
- Analyze test coverage reports
- Review mock fixtures for realism
- Identify edge cases not covered
- Design integration tests
- Recommend testing strategies

**Typical Deliverables**:
- Test coverage report
- List of untested critical paths
- New test files for gaps
- Mock fixture improvements

**Example Tasks**:
```
- "What code paths are untested?"
- "Review conftest.py mocks - are they realistic?"
- "Write tests for position deletion logic"
- "Should any of the 15 skipped tests be enabled?"
```

**Common Findings**:
- Critical code paths with 0 test coverage
- Mocks too permissive (pass when real code would fail)
- Missing edge case tests
- Integration tests skipped unnecessarily
- Flaky tests due to timing issues

---

### 7. Code Quality & Performance Optimizer

**Type**: `general-purpose`
**Specialty**: Code smells, refactoring, performance bottlenecks, best practices
**Domain Expertise**: Profiling, linting, design patterns, algorithm optimization

**Best Used For**:
- ✅ Identifying performance bottlenecks
- ✅ Refactoring opportunities
- ✅ Code smell detection
- ✅ Design pattern recommendations
- ✅ Memory leak investigation

**Key Capabilities**:
- Profile code execution
- Identify N+1 query problems
- Detect code duplication
- Recommend design patterns
- Memory and CPU optimization

**Typical Deliverables**:
- Performance profiling results
- Refactoring recommendations
- Code smell report
- Optimization implementation plan

**Example Tasks**:
```
- "Profile trading cycle execution time"
- "Identify duplicate code in signal generation"
- "Optimize database query performance"
- "Recommend caching strategy for market data"
```

**Common Findings**:
- N+1 database queries
- In-memory caching when Redis would be better
- Duplicate code across files
- Inefficient pandas operations
- Missing database indexes

---

## Orchestrator Agent

**Type**: Special (not launched via Task tool)
**Role**: Mission control, coordinator, decision maker

**Responsibilities**:
- Break complex missions into agent tasks
- Launch agents in optimal order (parallel/sequential)
- Monitor agent progress and blockers
- Resolve conflicts between agent findings
- Aggregate results into actionable plan
- Make final deployment decisions

**Key Capabilities**:
- Dependency graph construction
- Wave-based execution planning
- Conflict resolution strategies
- Results aggregation
- Quality assurance validation

**See**: ORCHESTRATION_PLAYBOOK.md for detailed orchestrator patterns

---

## Agent Selection Guide

### Quick Reference Table

| Need | Best Agent | Alternative |
|------|-----------|-------------|
| API not working | Trading Integration Auditor | Config Auditor |
| No buy/sell signals | Signal Generation Investigator | - |
| Database schema issues | Database Integrity Validator | - |
| Deployment failing | Config & Deployment Auditor | - |
| Frontend errors | Frontend Integration Tester | - |
| Low test coverage | Test Suite Completeness Reviewer | - |
| Slow performance | Code Quality Optimizer | Database Validator |
| Refactoring needed | Code Quality Optimizer | - |

---

## Agent Combination Patterns

### Pattern 1: Full System Audit

**Use Case**: Pre-deployment validation, quarterly health check

**Agent Team**:
- Agent 1: Trading Integration Auditor
- Agent 2: Signal Generation Investigator
- Agent 3: Database Integrity Validator
- Agent 4: Configuration & Deployment Auditor
- Agent 5: Frontend Integration Tester
- Agent 6: Test Suite Completeness Reviewer

**Execution**: All agents in parallel (Wave 1), orchestrator aggregates findings

**Expected Duration**: 2-3 hours (wall time), 10-15 hours (agent time)

---

### Pattern 2: New Feature Implementation

**Use Case**: Add new trading strategy

**Agent Team**:
- Agent 2: Design and implement signal logic
- Agent 3: Add database tables if needed
- Agent 5: Create frontend components
- Agent 6: Write comprehensive tests

**Execution**:
- Wave 1: Agent 2 (strategy design)
- Wave 2: Agents 3, 5, 6 in parallel (depends on strategy design)

**Expected Duration**: 3-4 hours

---

### Pattern 3: Bug Investigation & Fix

**Use Case**: Production issue needs root cause analysis

**Agent Team**:
- Agent X: Domain-specific investigator (depends on bug location)
- Agent 6: Add regression test

**Execution**:
- Agent X investigates root cause
- Orchestrator implements fix
- Agent 6 adds test to prevent recurrence

**Expected Duration**: 1-2 hours

---

## Extending the Agent Team

### Adding New Agent Types

**When to Add**:
- Recurring need not covered by existing agents
- Specialized domain requires deep expertise
- Complexity justifies dedicated agent

**Example New Agents**:
- **Machine Learning Model Validator**: For ML trading strategies
- **Security Penetration Tester**: For API security audits
- **Documentation Writer**: For auto-generating docs from code
- **Dependency Updater**: For keeping packages up-to-date

**Process**:
1. Define agent specialty and domain expertise
2. Create prompt template (see AGENT_PROMPTS_LIBRARY.md)
3. Test agent on sample tasks
4. Document in this catalog
5. Add to orchestration patterns

---

## Best Practices

### Agent Naming
- ✅ **Good**: "Trading Integration Auditor" (clear role)
- ❌ **Bad**: "Agent A" (meaningless)

### Agent Scope
- ✅ **Good**: Single domain, deep expertise
- ❌ **Bad**: "Do everything" agent (defeats purpose)

### Agent Autonomy
- ✅ **Good**: Agent completes mission without mid-flight guidance
- ❌ **Bad**: Agent asks orchestrator for constant direction

### Agent Output
- ✅ **Good**: Detailed report with actionable recommendations
- ❌ **Bad**: "I found some issues" (not actionable)

---

## Version History

- **v1.0** (2025-10-06): Initial catalog with 7 core agents
- **v1.1** (TBD): Add ML Model Validator after first ML strategy
- **v2.0** (TBD): Expand to 15 agents based on project needs

---

## References

- **AGENT_SYSTEM_ARCHITECTURE.md**: Overall system design
- **AGENT_PROMPTS_LIBRARY.md**: Detailed prompts for each agent
- **ORCHESTRATION_PLAYBOOK.md**: How to orchestrate missions
- **AGENT_LESSONS_LEARNED.md**: Historical performance data
