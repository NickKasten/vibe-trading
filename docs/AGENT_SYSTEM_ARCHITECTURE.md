# Multi-Agent System Architecture

## Philosophy & Design Principles

### Why Multi-Agent Architecture?

Traditional single-agent approaches suffer from:
- **Context Dilution**: One agent handling everything loses focus
- **Sequential Bottlenecks**: Tasks that could run in parallel wait in queue
- **Cognitive Overload**: Complex systems overwhelm single-agent reasoning
- **No Specialization**: Generalist agents lack deep domain expertise

Multi-agent systems solve these by:
- **Parallel Execution**: Independent tasks run simultaneously
- **Specialized Expertise**: Each agent masters one domain
- **Focused Context**: Agents work on narrow, well-defined problems
- **Scalability**: Add agents for new capabilities without complexity

---

## System Components

### 1. Orchestrator Agent (Mission Control)

**Role**: Central coordinator that manages all specialized agents

**Responsibilities**:
- **Mission Planning**: Break complex tasks into agent-sized chunks
- **Dependency Management**: Identify which tasks can run in parallel vs sequential
- **Agent Dispatching**: Launch agents at optimal times with precise prompts
- **Progress Monitoring**: Track agent status, ETAs, and blockers
- **Conflict Resolution**: Handle contradictory findings between agents
- **Results Aggregation**: Compile agent reports into cohesive action plan
- **Decision Making**: Make go/no-go decisions based on agent findings
- **Quality Assurance**: Validate agent outputs for accuracy and completeness

**Key Attributes**:
- Single source of truth for mission status
- Makes final decisions when agents conflict
- Responsible for user-facing reports
- Ensures no agent is blocked unnecessarily

---

### 2. Specialized Agents (Domain Experts)

**Agent Types** (see AGENT_TEAM_CATALOG.md for full list):
1. Trading Integration Auditor
2. Signal Generation Investigator
3. Database Integrity Validator
4. Configuration & Deployment Auditor
5. Frontend Integration Tester
6. Test Suite Completeness Reviewer
7. Code Quality & Performance Optimizer

**Agent Characteristics**:
- **Autonomous**: Execute mission without mid-flight guidance
- **Focused**: Work on single domain/problem
- **Thorough**: Deep dive into assigned area
- **Stateless**: Each mission is independent
- **Communicative**: Return detailed, actionable reports

---

## Communication Patterns

### 1. Orchestrator → Agent (Task Assignment)

```
INPUT: Detailed prompt with:
- Context: Background information
- Mission: Specific goal
- Tasks: Numbered checklist
- Files: Exact locations to investigate
- Expected Output: Format and content requirements

OUTPUT: Agent returns comprehensive report
```

**Example**:
```markdown
Orchestrator sends to Agent 1:
"Audit Alpaca integration. Context: simulate=True hardcoded.
Tasks: 1) Trace execution, 2) Test credentials, 3) Recommend fix.
Return: Root cause + implementation plan."

Agent 1 returns:
"Root Cause: main.py:151 hardcoded flag prevents API calls.
Fix: Add TRADING_MODE env var. See implementation plan below..."
```

---

### 2. Agent → Orchestrator (Status Updates)

Agents implicitly communicate status through Claude Code's Task tool:
- **Running**: Agent is actively working
- **Complete**: Agent finished, report available
- **Error**: Agent encountered blocker

Orchestrator uses AgentOutputTool to retrieve results when needed.

---

### 3. Inter-Agent Communication (via Orchestrator)

Agents **DO NOT** communicate directly. All coordination flows through orchestrator:

```
Agent 1 (completes) → Orchestrator (reads findings) → Agent 4 (uses findings)
```

**Example Scenario**:
- Agent 1 discovers: "Need to add TRADING_MODE env var"
- Orchestrator notes this finding
- Orchestrator sends to Agent 4: "Update render.yaml with TRADING_MODE variable"
- Agent 4 implements based on Agent 1's recommendation

---

## Execution Strategies

### Wave-Based Parallel Execution

**Definition**: Launch multiple agents simultaneously when they have no dependencies

**When to Use**:
- Agents work on independent subsystems (frontend + backend + database)
- Investigation phase (all gathering data, no changes yet)
- Time-critical missions requiring speed

**Example** (Alpaca Fix Mission):
```
Wave 1 (Parallel):
├── Agent 1: Trading Integration Auditor  ⏱️ 2 hours
├── Agent 2: Signal Strategy Investigator ⏱️ 2 hours
└── Agent 3: Database Integrity Validator ⏱️ 1.5 hours

Total Time: 2 hours (max of parallel agents)
vs Sequential: 5.5 hours (sum of all agents)
Savings: 3.5 hours (63% faster)
```

**Implementation**:
```python
# Launch all Wave 1 agents in single message
Task(agent_type="general-purpose", prompt=AGENT_1_PROMPT)
Task(agent_type="general-purpose", prompt=AGENT_2_PROMPT)
Task(agent_type="general-purpose", prompt=AGENT_3_PROMPT)
```

---

### Sequential Execution

**Definition**: Launch agents one at a time, each depending on previous results

**When to Use**:
- Agent B needs Agent A's findings to proceed
- Implementation phase (changes must happen in order)
- Risk of conflicting file edits

**Example**:
```
Agent 1: Identify bug root cause          ⏱️ 1 hour
   ↓ (Agent 1 complete, findings passed to Agent 7)
Agent 7: Implement fix based on findings  ⏱️ 30 min
   ↓ (Agent 7 complete, changes validated)
Agent 6: Write tests for the fix          ⏱️ 30 min

Total Time: 2 hours (sum of sequential agents)
```

---

### Hybrid Execution (Most Common)

**Definition**: Mix of parallel and sequential based on dependencies

**Example** (Typical Mission):
```
Wave 1: Discovery (Parallel)
├── Agent 1, 2, 3 run simultaneously
└── Total time: max(Agent1, Agent2, Agent3)

Wait for Wave 1 completion...

Wave 2: Configuration (Parallel, depends on Wave 1)
├── Agent 4 (uses Agent 1 findings)
├── Agent 5 (independent)
└── Agent 6 (independent)

Wave 3: Implementation (Sequential, orchestrator-driven)
├── Apply Agent 1's recommended fix
├── Update configs per Agent 4
└── Add tests per Agent 6
```

---

## Dependency Management

### Dependency Graph Example

```
         ┌─────────────┐
         │ Orchestrator│
         └──────┬──────┘
                │
    ┌───────────┴───────────┐
    │                       │
┌───▼────┐            ┌─────▼────┐
│Agent 1 │◄───────────┤ Agent 4  │ (depends on Agent 1)
│Trading │            │ Config   │
└────────┘            └──────────┘
    │
    │ (findings)
    ↓
┌────────┐
│Agent 7 │ (implements fix from Agent 1)
│Fixer   │
└────────┘
```

### Dependency Detection

Orchestrator identifies dependencies by:
1. **Explicit Requirements**: Agent prompt says "use Agent X findings"
2. **File Conflicts**: Two agents editing same file
3. **Domain Logic**: Config changes require knowing what to configure

### Deadlock Prevention

**Rule**: Never create circular dependencies
- ❌ Agent 1 waits for Agent 2, Agent 2 waits for Agent 1
- ✅ Agent 1 → Agent 2 → Agent 3 (linear chain)
- ✅ Agent 1 + Agent 2 (parallel) → Agent 3 (sequential)

---

## Error Handling & Recovery

### Agent Failures

**Scenario**: Agent encounters blocker and cannot complete mission

**Orchestrator Response**:
1. **Analyze Failure**: Read agent's error report
2. **Assess Impact**: Can mission continue without this agent?
3. **Recovery Options**:
   - **Retry**: Relaunch agent with clarified prompt
   - **Substitute**: Use different agent for same task
   - **Skip**: Continue if agent's work is non-critical
   - **Abort**: Halt mission if blocker is critical

**Example**:
```
Agent 3 fails: "Cannot connect to database"
Orchestrator assesses: CRITICAL BLOCKER
Action: Halt all agents, escalate to user
```

---

### Conflicting Findings

**Scenario**: Two agents recommend contradictory changes

**Orchestrator Resolution Process**:
1. **Identify Conflict**: Compare agent reports
2. **Request Clarification**: Ask agents to justify recommendations
3. **Evaluate Trade-offs**: Consider impact, risk, effort
4. **Make Decision**: Choose based on project priorities
5. **Document Rationale**: Explain why one option was chosen

**Example**:
```
Agent 1: "Remove TRADING_MODE flag, always use Alpaca"
Agent 4: "Keep TRADING_MODE flag for testing flexibility"

Orchestrator Decision: Keep TRADING_MODE
Rationale: Testing flexibility > code simplicity
Impact: Minimal (one env var)
```

---

## Performance Optimization

### Maximizing Parallelization

**Strategy**: Identify maximum independent work

**Example Analysis**:
```
Total Work: 10 hours across 6 agents
Dependency Graph:
- Wave 1: Agent 1, 2, 3 (max 2hr) = 2 hours
- Wave 2: Agent 4, 5, 6 (max 1.5hr, depends on Wave 1) = 1.5 hours
- Wave 3: Orchestrator aggregation = 1 hour

Total Wall Time: 4.5 hours
Speedup: 10 / 4.5 = 2.2x faster
```

---

### Context Window Management

**Challenge**: Large projects may exceed agent context limits

**Solutions**:
1. **Focused Prompts**: Direct agents to specific files/functions
2. **Pre-filtering**: Use Glob/Grep to find relevant code first
3. **Chunking**: Break large files into sections
4. **Summaries**: Agents return condensed findings (not full code dumps)

**Example**:
```
❌ Bad: "Review the entire backend codebase"
✅ Good: "Review backend/app/main.py lines 140-160 for trade execution logic"
```

---

## When to Use Multi-Agent vs Single-Agent

### Use Multi-Agent When:
- ✅ Task involves 3+ independent subsystems
- ✅ Complexity is high (need specialized expertise)
- ✅ Time is critical (parallelization saves hours)
- ✅ Investigation phase (many unknowns to explore)

### Use Single-Agent When:
- ✅ Task is simple and well-defined
- ✅ Everything in one file/module
- ✅ Sequential work (no parallelization benefit)
- ✅ Quick fixes (<30 minutes)

**Example Comparison**:

| Task | Approach | Reason |
|------|----------|--------|
| Fix typo in README | Single-Agent | Trivial, 1 file |
| Optimize slow function | Single-Agent | Focused problem |
| Debug Alpaca integration | Multi-Agent | Multiple subsystems involved |
| Full system audit | Multi-Agent | Many independent areas to check |
| Implement new feature | Multi-Agent | Backend + Frontend + Tests + Deployment |

---

## Success Metrics

### Mission Success Indicators
- ✅ All agents complete without blockers
- ✅ No conflicting recommendations
- ✅ Findings lead to actionable plan
- ✅ Changes validated by final testing
- ✅ Production deployment successful

### System Performance Metrics
- **Speedup Factor**: Wall time / Total agent time
- **Agent Utilization**: % of time agents are running vs waiting
- **Conflict Rate**: # of conflicting findings / # of agents
- **Retry Rate**: # of agent relaunches / # of agents

---

## Best Practices

### 1. Clear Agent Prompts
- Provide specific files and line numbers
- Include context about what to look for
- Define expected output format
- Set realistic scope (not "review everything")

### 2. Optimal Wave Structure
- Wave 1: Always discovery/investigation (parallel)
- Wave 2: Configuration and testing (parallel)
- Wave 3: Implementation (sequential, orchestrator-driven)
- Wave 4: Validation (orchestrator)

### 3. Conflict Prevention
- Assign non-overlapping domains to agents
- Clearly define ownership boundaries
- Use orchestrator for any cross-domain decisions

### 4. Progress Monitoring
- Check agent status every 15-30 minutes
- Identify blocked agents early
- Adjust wave composition if needed

---

## Future Enhancements

### Potential Improvements:
1. **Agent Specialization Levels**: Junior vs Senior agents
2. **Learning System**: Agents learn from past missions
3. **Auto-Dependency Detection**: Orchestrator auto-builds dependency graph
4. **Real-Time Collaboration**: Agents can request info from each other
5. **Quality Scoring**: Rate agent output quality automatically

---

## References

- **AGENT_TEAM_CATALOG.md**: Full agent directory
- **AGENT_PROMPTS_LIBRARY.md**: Reusable prompt templates
- **ORCHESTRATION_PLAYBOOK.md**: Mission execution guide
- **AGENT_LESSONS_LEARNED.md**: Historical learnings
