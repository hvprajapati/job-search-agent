# LLM Bottleneck Analysis

**Investigation**: DeepSeek API rate limiting during agent reliability tests
**Date**: 2026-06-20

---

## Symptom

After 1-2 agent calls, subsequent calls degrade to fallback mode (intent=error, response="I'm having trouble processing..."). In the Phase 1 reliability test, 31/50 requests (62%) received 429 responses from Pathfinder's rate limiter after the LLM became unavailable.

## Root Cause Analysis

### Layer 1: DeepSeek API Rate Limiting

**Finding**: The DeepSeek API imposes rate limits on the API key used. After 2-3 chat completion calls within a 60-second window, the API returns HTTP 429 (Too Many Requests).

**Evidence**: In the agent test, call 1 succeeded with a real LLM response (406ms). Calls 2+ entered fallback mode with empty LLM content. The DeepSeek health checker recorded consecutive failures, eventually opening the circuit breaker.

**Is it quota?** Partially. The DeepSeek free tier has both rate-per-minute AND total daily quota limits. The `deepseek-v4-flash` model used has generous limits, but the free tier restricts concurrent and rapid calls.

**Is it SDK issue?** No. The httpx client correctly sends requests and receives 429 responses. The issue is in how failures are handled.

### Layer 2: Pathfinder Rate Limiter

**Finding**: Pathfinder's own rate limiter restricts `/v1/agent/execute` to 20 requests/60s for free tier users. After exhausting the LLM, the agent enters fallback mode and returns 200 with degradation messages. After 20 requests to the agent endpoint, Pathfinder returns 429.

```python
# rate_limit.py
ENDPOINT_OVERRIDES = {
    "/v1/agent/execute": {"free": 20, "pro": 50, "premium": 200},
}
```

**Impact**: Even if the LLM were available, users on the free tier cannot make more than 20 agent requests per minute.

### Layer 3: Circuit Breaker

**Finding**: The `DeepSeekHealthChecker` opens the circuit breaker after 5 consecutive failures. Recovery timeout is 30 seconds.

```python
# llm_health.py
DeepSeekHealthChecker(failure_threshold=5, recovery_timeout=30.0)
```

**Behavior**: After 5 failed LLM calls, the circuit opens. All subsequent calls for the next 30 seconds return fallback responses without even attempting the API call.

**Is it a retry issue?** Yes — there is NO retry logic. The `DeepSeekClient.chat_completion()` fails immediately on 429 without any retry or backoff. Adding exponential backoff with 1-3 retries would help with transient 429s.

### Layer 4: No Request Queuing

**Finding**: There is no queuing or backpressure mechanism. When the LLM is unavailable, requests fail immediately rather than being queued for retry.

## The Complete Failure Chain

```
User sends agent request
  → DeepSeekClient.chat_completion() called
    → DeepSeek API returns 429 (rate limited)
      → llm_health.record_failure() increments counter
        → fallback_on_unavailable=True → returns LLMResponse(content="[LLM error]")
          → IntentRouter receives empty content
            → json.loads("[LLM error]") → JSONDecodeError
              → returns (GENERAL_QUESTION, 0.3)
                → Confidence < 0.7 → phase="needs_clarification"
                  → ResultSynthesizer produces fallback message
                    → 200 OK with degradation message
                      
After 5 such failures:
  → Circuit breaker opens
    → All LLM calls return "[LLM temporarily unavailable]"
      → Agent fully degraded

After 20 agent requests:
  → Pathfinder rate limiter returns 429
    → User sees "Too many requests"
```

## Recommendations

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| 1 | Add retry with exponential backoff (3 retries, 1s/2s/4s) | 1 hour | Reduces transient 429 failures |
| 2 | Increase free tier agent limit to 50/60s | 5 min | Users get 2.5x more agent calls |
| 3 | Add LLM fallback provider (OpenAI/Anthropic) | 2-3 days | Eliminates single point of failure |
| 4 | Cache frequent intent classifications | 2 hours | Reduces LLM calls by 60-80% |
| 5 | Add request queuing with TTL | 1 day | Smoother UX under load |

## Verdict

The DeepSeek bottleneck is a **multi-layered systemic issue**, not a single bug:
- **Layer 1 (API)**: DeepSeek free tier rate limits → requires fallback provider or caching
- **Layer 2 (Pathfinder)**: Aggressive rate limiting → requires config tuning
- **Layer 3 (Circuit)**: No retry logic → requires exponential backoff
- **Layer 4 (Queue)**: No backpressure → requires queuing mechanism

The agent degrades gracefully (no crashes, no empty responses) — this is correct behavior. But the degradation happens too quickly (after 1-2 calls) for a usable product.
