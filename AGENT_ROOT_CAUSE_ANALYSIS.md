# Agent Root Cause Analysis

## Failure Chain (Traced from Code)

### Step 1: DeepSeek API Rate Limit
```
DeepSeekClient.chat_completion()
  → POST https://api.deepseek.com/v1/chat/completions
  → HTTP 429 Too Many Requests
  → Retry 3x with exponential backoff (1s, 2s, 4s)
  → All retries exhausted
  → Return LLMResponse(content="[LLM error — service degraded]", model="none")
```

**Root cause**: DeepSeek free tier imposes a rate limit of approximately 3-5 requests per minute. The retry logic added in this sprint helps with transient failures but cannot overcome a hard rate limit.

### Step 2: Intent Classification Degradation
```
IntentRouter.classify()
  → json.loads("[LLM error — service degraded]")
  → JSONDecodeError
  → Return (Intent.GENERAL_QUESTION, 0.3)
```

### Step 3: Graph Execution Failure
```
agent_execute()
  → supervisor_graph.ainvoke(state)
  → intent_router_node → phase="needs_clarification" (confidence < 0.7)
  → result_synthesizer_node → produces "I'm having trouble..."
  → quality_gate → END
  → Return final_state without real response
```

### Step 4: Circuit Breaker Cascade
```
5 failures → circuit opens → ALL subsequent calls fail immediately
After fix: 10 failures → circuit opens → 15s recovery
```

## Evidence

### Before Fixes (Phase 1 Agent Reliability Test)
- 50 requests: 19 OK (200), 31 rate-limited (429)
- 0 real LLM responses after request #1
- Latency: 16ms (fallback), 406ms (first LLM call)

### After Fixes (Current Test)
- 15 requests: 15 OK (200), 0 rate-limited, 0 empty
- 14/15 fallback responses (intent=error)
- Latency: 16ms (fallback), 469ms (first LLM call)
- Rate limiting eliminated from Pathfinder's side (100/60s limit)
- DeepSeek API rate limit still active

## The Hard Truth

The agent reliability problem has TWO layers:

| Layer | Fixed? | Evidence |
|-------|:------:|----------|
| Pathfinder rate limiter (20 → 100/60s) | ✅ | No more 429 from Pathfinder |
| Circuit breaker tuning (5→10, 30s→15s) | ✅ | More resilient |
| Retry logic (3x exponential backoff) | ✅ | Added |
| Intent classification cache | ✅ | Reduces unnecessary LLM calls |
| **DeepSeek API rate limit** | ❌ | 1 real call, then 14 fallbacks |

**The DeepSeek free tier rate limit is a hard constraint at the API provider level. No code change in Pathfinder can bypass it.**

## Only Real Fix

Add a fallback LLM provider (OpenAI, Anthropic, or Groq) in `DeepSeekClient`. When the primary provider rate-limits, automatically switch to the fallback. This is a 2-3 day implementation that requires an API key for the second provider.
