# Endpoint Failure Analysis

**Source**: Phase 5 API Validation Matrix
**Date**: 2026-06-20

---

## Failure 1: GET `/v1/agent/executions` → 500

### Request
```
GET /v1/agent/executions?limit=20
Authorization: Bearer <valid_token>
```

### Response
```
500 Internal Server Error
```

### Stack Trace
```
sqlalchemy.exc.ProgrammingError: column agent_executions.intent does not exist

SELECT agent_executions.tenant_id, agent_executions.user_id, 
  agent_executions.session_id, agent_executions.call_id,
  agent_executions.parent_call_id, agent_executions.agent_type,
  agent_executions.action_type, agent_executions.intent,  ← DOES NOT EXIST
  agent_executions.intent_confidence,  ← DOES NOT EXIST
  agent_executions.user_message,  ← DOES NOT EXIST
  agent_executions.execution_plan,  ← DOES NOT EXIST
  agent_executions.tool_results,  ← named 'tools_called' in DB
  agent_executions.final_response,  ← named 'output_summary' in DB
  ...
FROM agent_executions
```

### Root Cause
**Model-DB schema mismatch**. The ORM model (`AgentExecutionModel`) was written AFTER migration 001, and 8+ columns diverge from the actual DB table:

| ORM Model Column | DB Column | Status |
|-----------------|-----------|--------|
| `intent` | ❌ Missing | NOT IN DB |
| `intent_confidence` | ❌ Missing | NOT IN DB |
| `user_message` | ❌ Missing | NOT IN DB |
| `execution_plan` | ❌ Missing | NOT IN DB |
| `tool_results` | `tools_called` | WRONG NAME |
| `final_response` | `output_summary` | WRONG NAME |
| `updated_at` | ❌ Missing | NOT IN DB (TimestampMixin) |
| ❌ Not in model | `input_context` | EXTRA IN DB |
| ❌ Not in model | `cost_estimate` | EXTRA IN DB |
| ❌ Not in model | `error_type` | EXTRA IN DB |
| ❌ Not in model | `retry_count` | EXTRA IN DB |
| ❌ Not in model | `user_approved` | EXTRA IN DB |
| ❌ Not in model | `user_modified` | EXTRA IN DB |

### Fix Complexity: **Medium** (1 file, ~25 lines)
Align ORM model with existing DB schema (no migration needed).

### Business Impact: **Medium**
Agent execution history is non-functional. Users cannot review past agent interactions. Episodic memory logging also uses incompatible models but swallows errors silently.

---

## Failure 2-3: GET/POST `/v1/match/history`, POST `/v1/match/compare` → 404

### Root Cause
**Endpoints never implemented.** The matching_router.py contains only `/compute` and `/feedback`. The `/history` and `/compare` endpoints were specified in the API design document but never coded.

### Fix Complexity: **N/A** (out of scope — would be a feature)
These are not bugs — they're unimplemented features. The API design spec listed them but they were descoped.

### Business Impact: **Low**
Users can compute matches and provide feedback. History/compare are nice-to-have for power users.

---

## Failure 4-6: POST/GET `/v1/tracking/events`, GET `/v1/tracking/funnel` → 404

### Root Cause
**Wrong URL path.** The tracking module is registered at `/v1/applications`, not `/v1/tracking/events`. The QA test used incorrect paths.

### Actual Tracking Endpoints
| Method | Path | Status |
|--------|------|:------:|
| GET | `/v1/applications` | ✅ Working |
| POST | `/v1/applications` | ✅ Working |
| PATCH | `/v1/applications/{id}` | ✅ Working |
| GET | `/v1/applications/{id}` | ✅ Working |
| DELETE | `/v1/applications/{id}` | ✅ Working |

### Fix Complexity: **None** (documentation issue)
No code change needed. The tracking module is fully functional at `/v1/applications`.

### Business Impact: **None**
All 5 tracking endpoints are operational under the correct URL path.

---

## Summary

| # | Endpoint | Error | Root Cause | Fixable | Effort |
|---|----------|:-----:|------------|:------:|:------:|
| 1 | `/v1/agent/executions` | 500 | ORM-DB schema mismatch (8+ columns) | Yes | 30 min |
| 2 | `/v1/match/history` | 404 | Never implemented | No | Feature |
| 3 | `/v1/match/compare` | 404 | Never implemented | No | Feature |
| 4 | `/v1/tracking/events` (POST) | 404 | Wrong URL (use /applications) | No | Docs |
| 5 | `/v1/tracking/events` (GET) | 404 | Wrong URL (use /applications) | No | Docs |
| 6 | `/v1/tracking/funnel` | 404 | Wrong URL (use /applications) | No | Docs |

**Actionable fix**: 1 (agent executions ORM model)
**Documentation issues**: 3 (tracking URL path)
**Unimplemented features**: 2 (match history/compare)
