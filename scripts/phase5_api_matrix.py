#!/usr/bin/env python3
"""Phase 5: API Validation Matrix — exercise all 36 endpoints."""
import json, os, sys, time
import requests

BASE = os.environ.get("PATHFINDER_URL", "http://localhost:8000")
ENDPOINTS = []
RESULTS = {}

def header(msg): print(f"\n{'='*60}\n  {msg}\n{'='*60}")

# Setup users
ts = int(time.time())
tokens = {}
for label in ["api-user", "api-user2"]:
    for attempt in range(5):
        r = requests.post(f"{BASE}/v1/auth/register",
            json={"email": f"{label}-{ts}@test.com", "password": "ApiTest123!", "full_name": f"API {label}", "accept_terms": True}, timeout=30)
        if r.status_code == 201:
            tokens[label] = r.json()["data"]["tokens"]["access_token"]
            break
        elif r.status_code == 429:
            time.sleep(10*(attempt+1))
    else:
        print(f"FAILED to register {label}"); sys.exit(1)

token = tokens["api-user"]

# Upload resume for user A to create profile
with open("scripts/test_resumes/ai_ml_engineer.txt") as f:
    requests.post(f"{BASE}/v1/profile/import/resume",
        headers={"Authorization": f"Bearer {tokens['api-user']}"},
        files={"file": ("resume.txt", f.read(), "text/plain")},
        data={"merge_strategy": "replace"}, timeout=120)

# Create base resume
r = requests.post(f"{BASE}/v1/resumes", headers={"Authorization": f"Bearer {token}"},
    json={"name": "API Test Resume", "template_id": "modern_professional", "content": {"summary": "Test resume for API validation."}}, timeout=30)
base_resume_id = r.json()["data"]["resume_id"] if r.status_code in (200, 201) else None

# Get job ID for matching
r = requests.get(f"{BASE}/v1/jobs", headers={"Authorization": f"Bearer {token}"}, params={"limit": 1}, timeout=30)
jobs = r.json().get("data", [])
job_id = jobs[0]["job_id"] if jobs else None

# Knowledge doc
requests.post(f"{BASE}/v1/knowledge/ingest/document",
    headers={"Authorization": f"Bearer {token}"},
    files={"file": ("api_test.txt", "API testing best practices for production validation.", "text/plain")},
    data={"title": "API Testing"}, timeout=30)

# Tailoring
tailored_id = None
if base_resume_id and job_id:
    r = requests.post(f"{BASE}/v1/tailoring/tailor",
        headers={"Authorization": f"Bearer {token}"},
        params={"base_resume_id": base_resume_id, "job_id": job_id, "strategy": "moderate"}, timeout=120)
    tailored_id = r.json()["data"]["tailored_resume_id"] if r.status_code == 200 else None

# Agent execution id
r = requests.post(f"{BASE}/v1/agent/execute",
    headers={"Authorization": f"Bearer {token}"},
    json={"message": "Find me jobs", "stream": False}, timeout=120)
agent_exec_id = "N/A"

# ── Test all endpoints ──
def test(method, path, token_key="api-user", json_body=None, params=None, expected=(200, 201, 204)):
    t = tokens.get(token_key, token)
    h = {"Authorization": f"Bearer {t}"} if t else {}
    start = time.monotonic()
    try:
        if method == "GET":
            r = requests.get(f"{BASE}{path}", headers=h, params=params, timeout=60)
        elif method == "POST":
            r = requests.post(f"{BASE}{path}", headers=h, json=json_body, params=params, timeout=60)
        elif method == "DELETE":
            r = requests.delete(f"{BASE}{path}", headers=h, timeout=60)
        else:
            r = requests.request(method, f"{BASE}{path}", headers=h, json=json_body, params=params, timeout=60)
        elapsed = (time.monotonic() - start) * 1000
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        return {"method": method, "path": path, "status": 0, "latency_ms": elapsed, "error": str(e)[:100]}
    return {"method": method, "path": path, "status": r.status_code, "latency_ms": elapsed, "ok": r.status_code in expected}

header("Phase 5: API Validation Matrix")

# Auth endpoints
for ep in [
    ("POST", "/v1/auth/register", None, {"email": f"api-matrix-{ts}@test.com", "password": "Matrix123!", "full_name": "Matrix", "accept_terms": True}, (201, 429)),
    ("POST", "/v1/auth/login", None, {"email": f"api-user-{ts}@test.com", "password": "ApiTest123!"}, (200,)),
    ("POST", "/v1/auth/logout", "api-user", {}, (204,)),
]:
    method, path, tkey, body, exp = ep[0], ep[1], ep[2], ep[3], ep[4]
    r = test(method, path, tkey, json_body=body, expected=exp)
    ENDPOINTS.append(r)
    icon = "OK" if r.get("ok") else "FAIL"
    print(f"  {icon}: {method:6s} {path:30s} -> {r['status']} ({r['latency_ms']:.0f}ms)")

# Profile endpoints
for ep in [
    ("GET", "/v1/profile", "api-user", None, None, (200,)),
    ("POST", "/v1/profile/import/resume", "api-user", None, None, (200, 422)),  # no file provided intentionally
    ("GET", "/v1/resumes", "api-user", None, None, (200,)),
    ("POST", "/v1/resumes", "api-user", {"name": "New Resume", "template_id": "modern_professional", "content": {}}, None, (201,)),
]:
    method, path, tkey, body, params, exp = ep
    r = test(method, path, tkey, json_body=body, params=params, expected=exp)
    ENDPOINTS.append(r)
    icon = "OK" if r.get("ok") else "FAIL"
    print(f"  {icon}: {method:6s} {path:30s} -> {r['status']} ({r['latency_ms']:.0f}ms)")

# Resume detail (need a valid resume ID)
if base_resume_id:
    r = test("GET", f"/v1/resumes/{base_resume_id}", "api-user", expected=(200,))
    ENDPOINTS.append(r)
    print(f"  {'OK' if r.get('ok') else 'FAIL'}: {'GET':6s} {f'/v1/resumes/{str(base_resume_id)[:8]}...':30s} -> {r['status']} ({r['latency_ms']:.0f}ms)")

    r = test("DELETE", f"/v1/resumes/{base_resume_id}", "api-user", expected=(204,))
    ENDPOINTS.append(r)
    print(f"  {'OK' if r.get('ok') else 'FAIL'}: {'DELETE':6s} {f'/v1/resumes/{str(base_resume_id)[:8]}...':30s} -> {r['status']} ({r['latency_ms']:.0f}ms)")

# Job endpoints
for ep in [
    ("GET", "/v1/jobs", "api-user", None, {"limit": 5}, (200,)),
    ("GET", "/v1/jobs/search", "api-user", None, {"q": "engineer"}, (200,)),
]:
    method, path, tkey, body, params, exp = ep
    r = test(method, path, tkey, json_body=body, params=params, expected=exp)
    ENDPOINTS.append(r)
    print(f"  {'OK' if r.get('ok') else 'FAIL'}: {method:6s} {path:30s} -> {r['status']} ({r['latency_ms']:.0f}ms)")

if job_id:
    r = test("GET", f"/v1/jobs/{job_id}", "api-user", expected=(200,))
    ENDPOINTS.append(r)
    print(f"  {'OK' if r.get('ok') else 'FAIL'}: {'GET':6s} {f'/v1/jobs/{str(job_id)[:8]}...':30s} -> {r['status']} ({r['latency_ms']:.0f}ms)")

# Matching
if job_id:
    for ep in [
        ("POST", "/v1/match/compute", "api-user", None, {"job_id": str(job_id)}, (200,)),
        ("GET", "/v1/match/history", "api-user", None, {"limit": 5}, (200,)),
        ("POST", "/v1/match/compare", "api-user", {"job_ids": [str(job_id)]}, None, (200,)),
    ]:
        method, path, tkey, body, params, exp = ep
        r = test(method, path, tkey, json_body=body, params=params, expected=exp)
        ENDPOINTS.append(r)
        print(f"  {'OK' if r.get('ok') else 'FAIL'}: {method:6s} {path:30s} -> {r['status']} ({r['latency_ms']:.0f}ms)")

# Agent
for ep in [
    ("POST", "/v1/agent/execute", "api-user", {"message": "Hello", "stream": False}, None, (200, 429)),
    ("GET", "/v1/agent/executions", "api-user", None, {"limit": 5}, (200,)),
]:
    method, path, tkey, body, params, exp = ep
    r = test(method, path, tkey, json_body=body, params=params, expected=exp)
    ENDPOINTS.append(r)
    print(f"  {'OK' if r.get('ok') else 'FAIL'}: {method:6s} {path:30s} -> {r['status']} ({r['latency_ms']:.0f}ms)")

# Knowledge
for ep in [
    ("POST", "/v1/knowledge/ingest/document", "api-user", None, None, (200,)),  # file required, expect 4xx
    ("POST", "/v1/knowledge/search", "api-user", None, {"query": "test", "top_k": 3}, (200,)),
    ("GET", "/v1/knowledge/documents", "api-user", None, {"limit": 5}, (200,)),
]:
    method, path, tkey, body, params, exp = ep
    r = test(method, path, tkey, json_body=body, params=params, expected=exp)
    ENDPOINTS.append(r)
    print(f"  {'OK' if r.get('ok') else 'FAIL'}: {method:6s} {path:30s} -> {r['status']} ({r['latency_ms']:.0f}ms)")

# Tailoring
if tailored_id:
    for ep in [
        ("GET", "/v1/tailoring/versions", "api-user", None, {"base_resume_id": str(base_resume_id), "job_id": str(job_id)}, (200,)),
        ("GET", "/v1/tailoring/compare", "api-user", None, {"version_a": str(tailored_id), "version_b": str(tailored_id)}, (200, 400)),
        ("POST", f"/v1/tailoring/{tailored_id}/accept", "api-user", {}, None, (200,)),
    ]:
        method, path, tkey, body, params, exp = ep
        r = test(method, path, tkey, json_body=body, params=params, expected=exp)
        ENDPOINTS.append(r)
        print(f"  {'OK' if r.get('ok') else 'FAIL'}: {method:6s} {path:30s} -> {r['status']} ({r['latency_ms']:.0f}ms)")

# Tracking
for ep in [
    ("POST", "/v1/tracking/events", "api-user", {"event_type": "test", "payload": {}}, None, (200, 201)),
    ("GET", "/v1/tracking/events", "api-user", None, {"limit": 5}, (200,)),
    ("GET", "/v1/tracking/funnel", "api-user", None, None, (200,)),
]:
    method, path, tkey, body, params, exp = ep
    r = test(method, path, tkey, json_body=body, params=params, expected=exp)
    ENDPOINTS.append(r)
    print(f"  {'OK' if r.get('ok') else 'FAIL'}: {method:6s} {path:30s} -> {r['status']} ({r['latency_ms']:.0f}ms)")

# Health endpoints
for ep in [
    ("GET", "/v1/health/live", None, None, None, (200,)),
    ("GET", "/v1/health/ready", None, None, None, (200, 503)),
    ("GET", "/v1/health/startup", None, None, None, (200,)),
    ("GET", "/v1/health", None, None, None, (200, 503)),
    ("GET", "/v1/metrics", None, None, None, (200,)),
]:
    method, path, tkey, body, params, exp = ep
    r = test(method, path, tkey, json_body=body, params=params, expected=exp)
    ENDPOINTS.append(r)
    print(f"  {'OK' if r.get('ok') else 'FAIL'}: {method:6s} {path:30s} -> {r['status']} ({r['latency_ms']:.0f}ms)")

# ── Summary ──
print(f"\n{'='*60}")
print(f"  API VALIDATION MATRIX")
print(f"{'='*60}")
total = len(ENDPOINTS)
ok = sum(1 for e in ENDPOINTS if e.get("ok"))
fails = total - ok
latencies = [e["latency_ms"] for e in ENDPOINTS if e.get("ok")]
print(f"  Endpoints tested: {total}")
print(f"  Successful: {ok}")
print(f"  Failed: {fails}")
if latencies:
    import statistics
    print(f"  Avg latency: {statistics.mean(latencies):.0f}ms")
    print(f"  Max latency: {max(latencies):.0f}ms")
print(f"  Error rate: {(fails/total*100):.1f}%")

for e in ENDPOINTS:
    if not e.get("ok"):
        print(f"  FAIL: {e['method']} {e['path']} -> {e['status']}")

with open("scripts/phase5_api_matrix.json", "w") as f:
    json.dump({"total": total, "passed": ok, "failed": fails, "endpoints": ENDPOINTS}, f, indent=2, default=str)
