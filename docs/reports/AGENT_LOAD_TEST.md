# Agent Load Test

## Before (Phase 1)
- 50 requests: 19 OK (200), 31 rate-limited (429), 0 empty, 0 crashes
- Real LLM responses: 1
- Fallback responses: 18
- Error rate: 62% (rate limited)

## After (Current)
- 15 requests: 15 OK (200), 0 rate-limited, 0 empty, 0 crashes
- Real LLM responses: 1
- Fallback responses: 14
- Error rate: 0%

## Key Change
Pathfinder rate limiting eliminated (100/60s now). But DeepSeek API rate limit unchanged — still only serves 1 real response per batch.

## Latency

| Metric | Before | After |
|--------|:------:|:-----:|
| First LLM call | 406ms | 469ms |
| Fallback responses | 16ms | 16ms |
| P50 | 16ms | 16ms |
| P95 | 32ms | 469ms |
| Max | 406ms | 469ms |

## Empty Responses: 0 (was 0)
## Crashes: 0 (was 0)
## Circuit Breaker Activations: 0 (was yes, after 5 failures)

## Verdict
Agent is STABLE (0 crashes, 0 empty) but not INTELLIGENT under load.
Fallback quality is the remaining gap.
