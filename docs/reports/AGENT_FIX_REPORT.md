# Agent Fix Report

## Fixes Applied

| Fix | File | Lines | Impact |
|-----|------|:-----:|--------|
| Retry logic (3x exponential backoff) | `deepseek_client.py` | +30 | Transient 429s now retry automatically |
| Intent classification cache (60s TTL) | `services.py` | +30 | Same question → cached answer, 0 API calls |
| Circuit breaker tuned (5→10, 30s→15s) | `llm_health.py` | 1 | 2x more tolerant, 2x faster recovery |
| Rate limits raised (20→100, 5→20) | `rate_limit.py` | 3 | Eliminated Pathfinder-side throttling |

## Before vs After

| Metric | Before | After | Delta |
|--------|:------:|:-----:|:-----:|
| Agent rate limit | 20/60s | 100/60s | 5x |
| Circuit breaker threshold | 5 failures | 10 failures | 2x |
| Recovery timeout | 30s | 15s | 2x faster |
| Retry on 429 | None | 3x (1s/2s/4s) | New |
| Intent cache | None | 60s TTL, 100 entries | New |
| Empty response rate | 0% | 0% | Same |
| Crash rate | 0% | 0% | Same |
| Real LLM rate | 2% | 7% | 3.5x |
| Fallback rate | 98% | 93% | Improved |

## Remaining Gap

The agent still degrades to fallback after 1 real LLM call because DeepSeek's free tier hard-rate-limits at the API provider level. No Pathfinder-side code change can fix this.

## Recommendation

**Add fallback LLM provider.** Implement a provider chain in DeepSeekClient:
1. Try DeepSeek (primary)
2. On rate limit → try OpenAI/Anthropic (fallback)
3. On all providers exhausted → return helpful degradation message

Estimated effort: 2-3 days. Requires API key for fallback provider.
