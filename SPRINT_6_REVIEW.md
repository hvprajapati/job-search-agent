# Sprint 6 — Principal AI Engineer Review

**Review Date:** 2026-06-18
**Reviewer:** Principal AI Engineer & LangGraph Architect
**Sprint Reviewed:** Sprint 6 — Agent Foundation
**Documents Audited:** SPRINT_6.md (full implementation)
**Classification:** Confidential — Internal

---

## Verdict: CONDITIONALLY APPROVED — 2 Critical Fixes Required

The Sprint 6 Agent Foundation correctly implements the MVP architecture (Supervisor + Tools). It is genuinely agentic — intent routing, planning, and tool execution form a complete reasoning→action loop. However, two critical issues must be fixed before production: the Task Planner fallback is incomplete (silent failure for 9 of 11 intents), and the `context_builder_node` has a reference-before-assignment bug.

---

## Six Evaluation Questions — Answered First

### Q1: Is this a real agent or just tool routing?

**Answer: This is a real agent — Level 2 on the agentic spectrum.**

A pure tool router would be: `if intent == X: call tool Y`. This implementation has:
- **Reasoning:** IntentRouter (LLM) classifies intent with confidence scoring
- **Planning:** TaskPlanner (LLM) decomposes intent into ordered tool calls with dependencies
- **Execution:** ToolExecutor runs the plan sequentially
- **Reflection:** QualityGate validates output and can loop back for revision (up to 3 passes)
- **Context:** ContextBuilder assembles user profile, preferences, and history before any action

What's missing for Level 3 autonomy:
- No dynamic replanning when a tool fails (the agent doesn't adapt its plan mid-execution)
- No multi-turn reasoning (each invocation is stateless beyond the session checkpoint)
- No proactive behavior (agent only responds to user messages, never initiates)

**Verdict:** Correctly calibrated for MVP. The architecture is designed to add replanning and multi-turn reasoning in V1 without restructuring.

### Q2: Is SupervisorState over-engineered?

**Answer: Yes, moderately. 7 of 25 fields are dead code in MVP.**

Fields that are defined but never populated or read:
| Field | Status |
|-------|--------|
| `active_applications` | Always `[]` — waiting for Sprint 5 tracking |
| `recent_history` | Always `[]` — waiting for Memory Agent |
| `messages` | Never appended to — the graph doesn't use LangChain message history |
| `execution_plan` | Set to `[]` in initial state but TaskPlanner output goes nowhere — the plan is never written back to state before tool_executor reads it |
| `response_artifacts` | Always `[]` — ResultSynthesizer only sets `final_response` |
| `user_action` | Never set — no button-click flow implemented |
| `attachments` | Never set — no file upload through agent |

**CRITICAL BUG discovered:** The TaskPlanner node produces a plan, but the code path from `intent_router_node` to `tool_executor` never writes the plan into state. The `should_short_circuit` conditional edge checks `agent_phase` and routes to `tool_executor`, but the `task_planner_node` is defined as a file but **never added to the graph** in `supervisor_graph.py`. The compiled graph jumps directly from `intent_router` to `tool_executor`, skipping planning entirely.

**Fix:** Add `task_planner_node` to the graph, insert it between `intent_router` and `tool_executor`, and have it write `execution_plan` into state.

**Recommendation:** Remove unused fields from SupervisorState for MVP. Only add fields when the code that populates and reads them exists. This eliminates the over-engineering concern.

### Q3: Should intent classification remain LLM-based?

**Answer: Yes, for MVP. But add a keyword-first fast path.**

The LLM-based intent router costs ~100 tokens per invocation. For unambiguous queries ("find python jobs in SF"), a keyword-based classifier would be free and faster. The LLM adds value for ambiguous queries ("I'm looking for something new").

**Recommendation:** Add a keyword pre-filter before the LLM call:
```python
KEYWORD_INTENTS = {
    "find": "search_jobs", "search": "search_jobs", "looking for": "search_jobs",
    "match": "match_me", "fit": "match_me", "score": "match_me",
    "tailor": "tailor_resume", "rewrite my resume": "tailor_resume",
}
for keyword, intent in KEYWORD_INTENTS.items():
    if keyword in user_message.lower():
        return Intent(intent), 0.90  # Skip LLM, save tokens
```
This reduces LLM costs by ~40% while preserving LLM fallback for ambiguous cases.

### Q4: Is planning logic robust enough?

**Answer: No. The fallback plan covers only 2 of 11 intents.**

The `_fallback_plan` method handles `search_jobs` and `match_me`. The other 9 intents return an empty list `[]`. When the LLM fails and the user requests `tailor_resume`, the agent returns a generic "I've completed your request" with no action taken. This is a silent failure — the user gets a response but nothing happened.

**Fix:** Add deterministic fallback plans for all 11 intents:
```python
FALLBACK_PLANS = {
    Intent.SEARCH_JOBS: [{"step_id": "1", "tool_name": "search_jobs", "tool_args": {"query": ""}, "depends_on": []}],
    Intent.MATCH_ME: [{"step_id": "1", "tool_name": "get_recommendations", "tool_args": {}, "depends_on": []}],
    Intent.TAILOR_RESUME: [{"step_id": "1", "tool_name": "get_resumes", "tool_args": {}, "depends_on": []}],
    Intent.UPDATE_PROFILE: [{"step_id": "1", "tool_name": "get_profile", "tool_args": {}, "depends_on": []}],
    Intent.GENERAL_QUESTION: [],  # Valid — no tools needed
    # ... all 11 intents covered
}
```

### Q5: Is tool execution production-safe?

**Answer: Partially. Three production risks exist.**

1. **No per-tool timeout.** If `search_jobs` hangs (DB connection pool exhausted), the agent hangs indefinitely. There's no `asyncio.wait_for(tool.execute(), timeout=30)`.

2. **No retry on transient failures.** A momentary DB connection error fails the entire agent invocation. Tools should retry once for `ConnectionRefusedError` and `TimeoutError`.

3. **Sequential execution only.** The `tool_executor_node` runs tools in a for-loop even when `depends_on` is empty (independent tools). This is correct for MVP (6 tools, ~50ms each) but noted for V1 optimization.

### Q6: Will execution history design scale?

**Answer: Yes, with the existing partitioning strategy. One gap identified.**

The `agent_executions` table stores `execution_plan` and `tool_results` as JSONB. At 500K calls/day, this is ~50 GB/month if full payloads are stored. The Sprint 6 code stores the execution plan and tool results — this is metadata, typically < 5KB per execution. At 500K calls/day × 5KB = 2.5 GB/day = 75 GB/month. This is manageable but will grow.

**Missing:** The table is not partitioned. Sprint 2's migration 001 partitioned `audit_logs` by day but `agent_executions` is a regular table. Add monthly partitioning before production deployment.

**Missing:** No retention policy. Agent executions older than 90 days should be archived to cold storage.

---

## Detailed Audit Findings

### 1. LangGraph Architecture — B

**CRIT-1: TaskPlanner node not wired into the graph.** The file `task_planner_node.py` exists, but `supervisor_graph.py` never calls `builder.add_node("task_planner", task_planner_node)` or adds an edge to it. The compiled graph has 6 nodes but only 5 are connected. The execution plan is never generated — `tool_executor_node` reads `state.get("execution_plan", [])` which is always `[]`.

**Fix:** Add the node and edge:
```python
builder.add_node("task_planner", task_planner_node)
builder.add_edge("intent_router", "task_planner")
builder.add_edge("task_planner", "tool_executor")
```

**CRIT-2: HumanGate node declared but never implemented.** The file list includes `human_gate.py` and the graph overview diagram shows it, but no implementation is provided and it's not added to the compiled graph. The HITL framework (ApprovalRequest entity, model, API endpoint) exists but the graph has no pause point.

**Fix for MVP:** Document that HITL gates are deferred to Sprint 7 (Production Hardening). The ApprovalRequest infrastructure is ready — it just needs a graph node. Remove `human_gate.py` from the Sprint 6 deliverables list.

### 2. State Design — C+

**MAJ-1: State has fields that are never populated (see Q2).** 7 dead fields create confusion about what the graph actually uses. A developer adding a new node will assume `active_applications` is available when it's always empty.

**MAJ-2: `execution_plan` is declared but never populated by any node (because TaskPlanner isn't wired).** ToolExecutor reads an empty list and does nothing. This is why the agent currently only works for `general_question` — the ResultSynthesizer's general_question branch doesn't depend on tool results.

**MIN-1: `total_tokens_used` is set to 0 in initial state and never incremented.** No node tracks token usage. The observability requirement ("Track token usage") is not met.

**MIN-2: State update pattern is inconsistent.** Some nodes return partial state dicts (`{"agent_phase": "..."} `), others return large dicts. LangGraph's state reducer merges these correctly, but it's hard to trace which field is set where.

### 3. Tool Architecture — B+

**What's right:** ToolRegistry with ToolDefinition metadata is clean. Tools wrap existing services — no duplicate logic. The `get_definitions_for_llm()` method outputs OpenAI function-calling format, which is correct for DeepSeek (compatible API).

**MAJ-3: Tool parameters declared in JSON Schema but never validated.** The tool_registry.execute() passes `**kwargs` directly to handlers. If the LLM hallucinates a parameter name, it silently passes through. Add JSON Schema validation before handler invocation.

**MIN-3: Tool error messages include full exception strings.** `str(e)[:500]` could leak database connection strings or internal paths to the user-facing response. Sanitize error messages before returning them in ToolResult.

**MIN-4: `is_expensive` and `tier_required` fields are defined but never checked.** The tool_registry doesn't enforce tier gating or circuit-breaker for expensive tools.

### 4. Intent Routing — B

**MAJ-4: IntentRouter creates a new DeepSeekClient on every invocation.** The `intent_router_node` instantiates `DeepSeekClient()` directly — no connection reuse, no dependency injection. Each intent classification opens a new HTTP client.

**Q3 recommendation applies:** Add keyword pre-filter to reduce LLM calls.

### 5. Planning Layer — C

**CRIT-1 (duplicate): TaskPlanner not wired.**
**MAJ-5: Fallback plans cover only 2 of 11 intents (see Q4).**

### 6. Execution Flow — B-

**MAJ-6: No per-tool timeout (see Q5).** Add `asyncio.wait_for(tool_registry.execute(...), timeout=30.0)`.

**MIN-5: Tool execution errors are collected but don't affect the response quality.** If `search_jobs` fails and `get_profile` succeeds, the ResultSynthesizer only formats `search_jobs` results (because intent is `search_jobs`). The successful profile retrieval is invisible to the user. The synthesizer should incorporate partial successes.

### 7. Checkpointing — B-

**MIN-6: PostgresSaver `setup()` is commented out.** The code has `# checkpointer.setup()  # Run once to create checkpoint tables`. If the checkpoint tables don't exist, the first graph invocation will crash. This must be run in a migration or startup hook.

**MIN-7: No checkpoint TTL.** LangGraph checkpoint tables grow unboundedly. Add a periodic cleanup task that deletes checkpoints older than 30 days for completed sessions.

### 8. HITL Architecture — B

**What's right:** ApprovalRequest entity, model, repository interface, and API endpoint are well-designed. The `approve()/reject()/edit()` methods are clean.

**CRIT-2 (duplicate): No graph node to trigger the interrupt.** The API endpoint exists but there's no LangGraph `interrupt()` call in any node. The approval flow is infrastructure without a trigger.

### 9. API Design — B

**MIN-8: POST /v1/agent/execute reads body with `request.json()` even when Content-Type isn't JSON.** This will raise an exception. Use FastAPI's `Body()` or a Pydantic model.

**MIN-9: SSE streaming yields raw LangGraph event objects.** `json.dumps(event, default=str)` will produce unparseable JSON for complex objects. Events should be formatted before serialization.

**MIN-10: No rate limiting on POST /v1/agent/execute.** This is the most expensive endpoint (LLM calls + DB queries). Rate limits must be enforced.

### 10. Streaming Implementation — C+

**MIN-11: The streaming path doesn't persist the execution record.** The non-streaming path saves to `agent_executions` table. The streaming path emits events and returns — no persistence. Streaming executions are lost from the history.

**MIN-12: No heartbeat for long-running executions.** If a tool takes 20 seconds, the SSE connection is silent for 20 seconds. Proxies may close the connection. Add a heartbeat comment (`: heartbeat\n\n`) every 15 seconds.

### 11. Security — B

**MIN-13: Prompt injection defense is documented but not implemented.** The guardrail_node comment says "Prompt injection hardening — wrap user text for downstream nodes" but doesn't actually wrap user text in `<user_data>` tags. All downstream LLM calls receive raw user input.

**MIN-14: No authorization check in tools.** Any user can pass any `user_id` to `get_profile`. The tool should validate that `user_id` matches the authenticated user (or reject cross-user access).

### 12. Prompt Injection Defenses — C

See MIN-13. Additionally:
- The IntentRouter sends raw user_message to the LLM with no sanitization
- The TaskPlanner sends raw user_message to the LLM with no sanitization
- The ResultSynthesizer doesn't sanitize user data before embedding in responses (potential XSS if responses are rendered as HTML)

### 13. Scalability — C+

**MIN-15: No connection pooling for tool sessions.** Each tool creates a new `get_sessionmaker()` and opens a new session. For 7 tools called in sequence, that's 7 DB connections. For 100 concurrent agents, that's 700 connections. The sessionmaker should be injected as a dependency.

**MIN-16: `agent_executions` table not partitioned (see Q6).**

### 14. Failure Recovery — C

**MIN-17: No graph-level error boundary.** If any node raises an unhandled exception, the entire graph invocation crashes. LangGraph supports `retry` policies on nodes — none are configured.

**MIN-18: No circuit breaker for LLM calls.** The `CircuitBreakerOpenError` exception class exists but is never raised. Three consecutive DeepSeek failures should open the circuit and return a graceful degradation message.

### 15. Testing Quality — C+

**MIN-19: No graph integration tests.** Tests cover individual components (ToolRegistry, IntentRouter) but there's no test that compiles the graph, invokes it with a real state object, and verifies the output. The most critical path — "graph compiles and runs" — is untested.

**MIN-20: No SSE streaming tests.** The streaming path is untested. There's no test verifying that SSE events arrive in the correct order with the correct format.

---

## Issue Summary

| ID | Severity | Area | Issue |
|----|----------|------|-------|
| CRIT-1 | CRITICAL | Graph | TaskPlanner node not added to compiled graph |
| CRIT-2 | CRITICAL | HITL | HumanGate node declared but not implemented — no graph interrupt |
| MAJ-1 | MAJOR | State | 7 dead fields in SupervisorState |
| MAJ-2 | MAJOR | State | `execution_plan` never populated (consequence of CRIT-1) |
| MAJ-3 | MAJOR | Tools | Tool parameters not validated against JSON Schema |
| MAJ-4 | MAJOR | Intent | New DeepSeekClient per invocation — no connection reuse |
| MAJ-5 | MAJOR | Planning | Fallback plans cover 2 of 11 intents |
| MAJ-6 | MAJOR | Execution | No per-tool timeout |
| MIN-1 | MINOR | State | Token tracking declared but not implemented |
| MIN-2 | MINOR | State | Inconsistent state update patterns |
| MIN-3 | MINOR | Tools | Error messages may leak internal details |
| MIN-4 | MINOR | Tools | `is_expensive`/`tier_required` not enforced |
| MIN-5 | MINOR | Execution | Partial successes invisible to user |
| MIN-6 | MINOR | Checkpoint | setup() commented out — tables may not exist |
| MIN-7 | MINOR | Checkpoint | No TTL on checkpoint data |
| MIN-8 | MINOR | API | request.json() without Content-Type guard |
| MIN-9 | MINOR | API | Raw LangGraph events in SSE |
| MIN-10 | MINOR | API | No rate limiting on agent endpoint |
| MIN-11 | MINOR | Streaming | No persistence for streaming executions |
| MIN-12 | MINOR | Streaming | No heartbeat during long executions |
| MIN-13 | MINOR | Security | Prompt injection defense not implemented |
| MIN-14 | MINOR | Security | No user_id authorization in tools |
| MIN-15 | MINOR | Scalability | No connection pooling for tool sessions |
| MIN-16 | MINOR | Scalability | agent_executions not partitioned |
| MIN-17 | MINOR | Recovery | No graph-level error boundary |
| MIN-18 | MINOR | Recovery | Circuit breaker defined but never used |
| MIN-19 | MINOR | Testing | No graph compilation/invocation test |
| MIN-20 | MINOR | Testing | No SSE streaming test |

---

## LangGraph Best Practice Recommendations

1. **Use `interrupt()` correctly.** When HITL is implemented, call `interrupt()` inside the node function, not as a graph edge. The node should: (a) create ApprovalRequest in DB, (b) call `interrupt({"approval_id": str(id)})`, (c) on resume, read the approval decision and continue.

2. **Use `Command` for state updates from interrupts.** When the user responds to an approval, use `Command(resume=...)` to pass the decision back into the graph.

3. **Add node-level retry policies.** Configure `retry` on the LLM-calling nodes (intent_router, task_planner) with `RetryPolicy(max_attempts=2, backoff_factor=2.0)`.

4. **Use `Send` API for parallel tool execution.** When tools have no dependencies, use `Send()` to execute them concurrently instead of sequentially.

5. **Configure `config["recursion_limit"]`** to prevent infinite revision loops in the quality gate. Default is 25 — set to 10 for this graph.

6. **Use `astream_events()` instead of `astream()` for SSE.** `astream_events()` provides granular events (on_chat_model_start, on_tool_start, on_tool_end) that map naturally to SSE event types.

---

## Remediation Requirements

### Must-Fix Before Production (4 hours)

| Fix | Effort |
|-----|--------|
| **CRIT-1:** Wire TaskPlanner into graph | 30 min |
| **CRIT-2:** Document HITL deferral; remove human_gate from Sprint 6 scope | 15 min |
| **MAJ-1:** Remove 7 dead fields from SupervisorState | 30 min |
| **MAJ-5:** Add fallback plans for all 11 intents | 1 hour |
| **MAJ-6:** Add `asyncio.wait_for(..., timeout=30)` to tool execution | 15 min |
| **MAJ-3:** Add JSON Schema validation before tool handler invocation | 1 hour |
| **MIN-13:** Implement prompt injection defense in guardrail_node | 30 min |

### Should-Fix Before Sprint 7 (3 hours)

| Fix | Effort |
|-----|--------|
| MAJ-4: Inject DeepSeekClient instead of instantiating per call | 30 min |
| MIN-6: Run checkpointer.setup() in migration or startup | 15 min |
| MIN-14: Add user_id authorization check in tools | 30 min |
| MIN-11: Persist streaming executions to agent_executions | 1 hour |
| MIN-17: Add retry policies to LLM nodes | 30 min |

---

## Production Readiness Assessment

| Criterion | Status | Notes |
|-----------|--------|-------|
| **Graph compiles and runs** | ⚠️ CRIT-1 | TaskPlanner not wired |
| **Intent routing** | ✅ | LLM-based with confidence scoring |
| **Tool execution** | ⚠️ MAJ-6 | Needs timeout |
| **State management** | ⚠️ MAJ-1 | Dead fields |
| **Checkpointing** | ⚠️ MIN-6 | Setup not automated |
| **HITL framework** | ⚠️ CRIT-2 | Infrastructure exists, trigger missing |
| **API** | ⚠️ MIN-10 | Needs rate limiting |
| **Security** | ⚠️ MIN-13 | Prompt injection defense absent |
| **Testing** | ⚠️ MIN-19 | No graph-level tests |

---

## SPRINT 6 CONDITIONALLY APPROVED FOR PRODUCTION

**Condition:** The 2 critical issues (CRIT-1, CRIT-2) and 5 major issues (MAJ-1, MAJ-3, MAJ-4, MAJ-5, MAJ-6) must be fixed before production deployment. These are ~4 hours of work. No architectural changes are needed.

The Supervisor + Tools architecture is correct. The LangGraph graph structure is well-designed. The tool wrapping pattern (existing services → ToolRegistry → agent-callable) is exactly right. The fixes are implementation-level, not design-level.

> *"This is a real agent. It reasons, plans, and executes. The missing TaskPlanner wire is a bug, not a design flaw. Fix it and ship."*

**End of Sprint 6 Review**
