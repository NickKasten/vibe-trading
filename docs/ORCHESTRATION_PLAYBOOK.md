# Orchestration Playbook

## Quick Start

**Goal**: Execute complex multi-agent missions efficiently

**Steps**:
1. Define mission objectives
2. Break into agent-sized tasks
3. Identify dependencies
4. Create wave structure
5. Launch agents
6. Aggregate findings
7. Implement changes
8. Validate results

---

## Wave-Based Execution

### Wave 1: Discovery (Always Parallel)
**Purpose**: Gather information without making changes

**Agents**: All investigators/auditors
**Duration**: Max of all agent times
**Success**: All agents return detailed reports

**Example**:
```
Wave 1 (Parallel - 2 hours):
├── Agent 1: Trading Integration (2hr)
├── Agent 2: Signal Strategy (2hr)
└── Agent 3: Database Integrity (1.5hr)

Wall Time: 2 hours (vs 5.5hrs sequential)
```

---

### Wave 2: Validation & Config (Parallel after Wave 1)
**Purpose**: Validate findings and prepare implementation

**Dependencies**: May need Wave 1 findings
**Agents**: Config, Testing, Frontend agents
**Duration**: Max of all agent times

---

### Wave 3: Implementation (Sequential, Orchestrator-Led)
**Purpose**: Apply fixes in correct order

**Mode**: Sequential (one at a time)
**Leader**: Orchestrator makes changes
**Duration**: Sum of fix times

---

### Wave 4: Final Validation (Orchestrator)
**Purpose**: Verify everything works

**Tasks**:
- Run full test suite
- Test critical paths manually
- Build frontend
- Generate deployment checklist

---

## Conflict Resolution

### Scenario A: Contradictory Recommendations
**Agent 1**: "Remove feature X"
**Agent 5**: "Frontend depends on X"

**Resolution**:
1. Identify conflict
2. Request clarification from both
3. Evaluate trade-offs
4. Decide based on priorities
5. Document rationale

---

### Scenario B: Blocking Issue
**Agent 3**: "Database corrupted!"

**Response**:
1. HALT all other agents
2. Escalate to user
3. Create emergency plan
4. Resume after resolution

---

## Dependency Patterns

### Pattern: A → B (Sequential)
```
Agent 1 completes → Findings used by Agent 4
```

### Pattern: A, B, C (Parallel)
```
All independent, launch together
```

### Pattern: (A, B) → C (Hybrid)
```
A and B parallel → Both complete → Launch C
```

---

## Monitoring Dashboard

Track agent status in real-time:

| Agent | Status | Progress | ETA | Blockers |
|-------|--------|----------|-----|----------|
| 1 | Running | 60% | 30min | None |
| 2 | Complete | 100% | Done | None |
| 3 | Queued | 0% | - | Waiting Agent 1 |

---

## Best Practices

### ✅ Do
- Launch independent agents in parallel
- Give agents specific files/lines
- Define clear deliverable formats
- Monitor for blockers every 15-30min
- Document all decisions

### ❌ Don't
- Launch dependent agents before prereqs complete
- Give vague "check everything" prompts
- Assume agents will coordinate themselves
- Ignore conflicts between findings
- Skip final validation wave

---

## Common Patterns

### Full System Audit
**Use**: Pre-deployment, quarterly review
**Agents**: All 6-7 specialists
**Structure**: Single parallel wave
**Duration**: 2-3 hours wall time

### Bug Investigation
**Use**: Production issue
**Agents**: 1-2 relevant specialists
**Structure**: Sequential
**Duration**: 1-2 hours

### Feature Implementation
**Use**: New capability
**Agents**: 3-4 (backend, frontend, tests, deploy)
**Structure**: Hybrid (design → parallel impl)
**Duration**: 3-4 hours

---

## Troubleshooting

### Agent Not Completing
**Check**: Is context too large? Narrow scope
**Fix**: Relaunch with more specific prompt

### Conflicting Findings
**Check**: Are domains overlapping?
**Fix**: Clarify ownership boundaries

### Slow Progress
**Check**: Are agents truly parallel or waiting?
**Fix**: Review dependency graph

---

## Quick Launch Template

```bash
# Wave 1: Discovery
Task(subagent_type="general-purpose",
     description="Audit X integration",
     prompt=AGENT_1_PROMPT)

Task(subagent_type="general-purpose",
     description="Investigate Y",
     prompt=AGENT_2_PROMPT)

# Wait for completion, then Wave 2...
```

---

## References
- AGENT_SYSTEM_ARCHITECTURE.md (system design)
- AGENT_TEAM_CATALOG.md (agent directory)
- AGENT_PROMPTS_LIBRARY.md (prompt templates)
