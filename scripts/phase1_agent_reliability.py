#!/usr/bin/env python3
"""Phase 1: Agent Reliability — 50 consecutive requests."""
import json, os, sys, time, statistics
import requests

BASE = os.environ.get("PATHFINDER_URL", "http://localhost:8000")
RESULTS = []

def header(msg): print(f"\n{'='*60}\n  {msg}\n{'='*60}")

# Setup
header("Phase 1: Agent Reliability Test")
ts = int(time.time())
email = f"agent-load-{ts}@test.com"

# Register
for attempt in range(5):
    r = requests.post(f"{BASE}/v1/auth/register",
        json={"email": email, "password": "Test123!", "full_name": "Load Test", "accept_terms": True}, timeout=30)
    if r.status_code == 201:
        token = r.json()["data"]["tokens"]["access_token"]
        print(f"Registered: {email}")
        break
    elif r.status_code == 429:
        print(f"  Rate limited, waiting {10*(attempt+1)}s...")
        time.sleep(10*(attempt+1))
else:
    print("FAILED to register"); sys.exit(1)

# Upload minimal resume for context
resume = "Load Test User\n\nSKILLS\nPython, Docker, AWS, Kubernetes\n\nWORK EXPERIENCE\nTechCo - Engineer (2020-2023)\n\nEDUCATION\nState U - BS CS (2020)"
r = requests.post(f"{BASE}/v1/profile/import/resume",
    headers={"Authorization": f"Bearer {token}"},
    files={"file": ("resume.txt", resume, "text/plain")},
    data={"merge_strategy": "replace"}, timeout=60)
print(f"Resume upload: {r.status_code}, skills={r.json().get('data',{}).get('skills_extracted',0)}")

# ── Run 50 agent requests ──
MESSAGES = [
    "Find me jobs", "What skills do I have?", "Hi there", "Tailor my resume",
    "What is my match score?", "Help me with career advice", "Show my profile",
    "Search for remote jobs", "Any recommendations?", "Hello",
]
latencies = []
empty_responses = 0
crashes = 0
status_codes = {}
intents = {}

print(f"\nRunning 50 agent requests...")
for i in range(50):
    msg = MESSAGES[i % len(MESSAGES)]
    start = time.monotonic()

    try:
        r = requests.post(f"{BASE}/v1/agent/execute",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": msg, "stream": False}, timeout=120)
        elapsed_ms = (time.monotonic() - start) * 1000
        status = r.status_code
    except Exception as e:
        elapsed_ms = (time.monotonic() - start) * 1000
        status = 0
        crashes += 1
        RESULTS.append({"id": i+1, "message": msg, "status": 0, "latency_ms": elapsed_ms,
                        "response_len": 0, "intent": "crash", "error": str(e)[:100]})
        print(f"  {i+1:02d}: CRASH ({elapsed_ms:.0f}ms) - {str(e)[:80]}")
        continue

    status_codes[status] = status_codes.get(status, 0) + 1
    response_len = 0
    intent = ""

    if status == 200:
        try:
            data = r.json().get("data", {})
            response_len = len(data.get("response", ""))
            intent = data.get("intent", "?")
            if response_len == 0:
                empty_responses += 1
        except Exception:
            empty_responses += 1

    intents[intent] = intents.get(intent, 0) + 1
    latencies.append(elapsed_ms)

    status_icon = "OK" if (status == 200 and response_len > 0) else "FAIL"
    if i < 10 or i % 10 == 9:
        print(f"  {i+1:02d}: {status_icon} status={status}, {response_len} chars, {elapsed_ms:.0f}ms, intent={intent}")

    RESULTS.append({"id": i+1, "message": msg, "status": status, "latency_ms": elapsed_ms,
                    "response_len": response_len, "intent": intent})

    # Brief pause to respect rate limits
    if i % 5 == 4:
        time.sleep(2)

# ── Statistics ──
print(f"\n--- Agent Reliability Statistics ---")
print(f"  Total requests:    {len(RESULTS)}")
print(f"  Successful:        {sum(1 for r in RESULTS if r['status'] == 200 and r['response_len'] > 0)}")
print(f"  Empty responses:   {empty_responses}")
print(f"  Crashes:           {crashes}")
print(f"  Error rate:        {(empty_responses + crashes) / 50 * 100:.1f}%")

if latencies:
    latencies.sort()
    avg_lat = statistics.mean(latencies)
    p50 = latencies[len(latencies)//2]
    p95 = latencies[int(len(latencies)*0.95)]
    p99 = latencies[int(len(latencies)*0.99)]
    print(f"\n  Latency (ms):")
    print(f"    Mean: {avg_lat:.0f}  P50: {p50:.0f}  P95: {p95:.0f}  P99: {p99:.0f}  Max: {max(latencies):.0f}")
    print(f"    Min: {min(latencies):.0f}")

print(f"\n  Status codes: {status_codes}")
print(f"  Intents: {intents}")

# Save raw results
with open("scripts/phase1_agent_results.json", "w") as f:
    json.dump({"summary": {"total": 50, "empty": empty_responses, "crashes": crashes,
                "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
                "p95_latency_ms": p95 if latencies else 0,
                "error_rate": (empty_responses + crashes) / 50},
               "latencies": latencies, "requests": RESULTS}, f, indent=2)

print(f"\n  Results saved to scripts/phase1_agent_results.json")

# Exit code
if empty_responses > 0 or crashes > 0:
    print(f"\n  FAIL: {empty_responses} empty + {crashes} crashes")
    sys.exit(1)
print(f"\n  PASS: All 50 requests completed without crashes or empty responses")
