#!/usr/bin/env python3
"""Pathfinder — Complete User Demo.

Exercises all major subsystems end-to-end against the running API.
Fails fast on any error. No mocks. No stubs. Real endpoints only.
"""
import json
import sys
import time
import os
import requests

BASE = os.environ.get("PATHFINDER_URL", "http://localhost:8000")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESUME_FILE = os.path.join(SCRIPT_DIR, "sample_resume.txt")
KNOWLEDGE_FILE = os.path.join(SCRIPT_DIR, "sample_knowledge.txt")

DEMO_EMAIL = f"demo-{int(time.time())}@pathfinder.dev"
DEMO_PASSWORD = "DemoUser123!"
DEMO_NAME = "Alex Chen"

results = {}
token = None


def step(name: str) -> None:
    print(f"\n{'='*60}")
    print(f"  STEP: {name}")
    print(f"{'='*60}")


def fail(name: str, msg: str) -> None:
    print(f"\n  [{name}] FAIL: {msg}")
    results[name] = "FAIL"
    print(f"\n{'='*60}")
    print(f"  OVERALL: FAIL ({sum(1 for v in results.values() if v == 'PASS')}/{len(results)} passed)")
    sys.exit(1)


def ok(name: str) -> None:
    results[name] = "PASS"


def api(method: str, path: str, **kwargs) -> requests.Response:
    """Make an API call. Fail fast on error."""
    url = f"{BASE}{path}"
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.request(method, url, headers=headers, timeout=30, **kwargs)
        if resp.status_code >= 500:
            fail("API", f"Server error {resp.status_code} on {method} {path}: {resp.text[:200]}")
        return resp
    except requests.exceptions.ConnectionError:
        fail("API", f"Cannot connect to {BASE}. Is Pathfinder running? docker compose up -d")


# ── STEP 1: Register ──
step("1: Register")
resp = api("POST", "/v1/auth/register", json={
    "email": DEMO_EMAIL, "password": DEMO_PASSWORD,
    "full_name": DEMO_NAME, "accept_terms": True,
})
if resp.status_code != 201:
    fail("AUTH", f"Register returned {resp.status_code}: {resp.text[:200]}")
data = resp.json()["data"]
print(f"  User: {data['user']['email']} (tier={data['user']['tier']})")
print(f"  Tokens: access={data['tokens']['access_token'][:30]}...")
ok("AUTH")

# ── STEP 2: Login ──
step("2: Login + Capture JWT")
resp = api("POST", "/v1/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
if resp.status_code != 200:
    fail("AUTH", f"Login returned {resp.status_code}")
token = resp.json()["data"]["tokens"]["access_token"]
print(f"  JWT captured: {token[:30]}...")
ok("AUTH")

# ── STEP 3: Upload Resume ──
step("3: Upload Resume")
with open(RESUME_FILE, "r") as f:
    resume_text = f.read()
resp = api("POST", "/v1/profile/import/resume",
           files={"file": ("resume.txt", resume_text, "text/plain")},
           data={"merge_strategy": "replace"})
if resp.status_code not in (200, 201):
    fail("PROFILE", f"Resume upload returned {resp.status_code}: {resp.text[:200]}")
data = resp.json()["data"]
print(f"  Profile ID: {data.get('profile_id', '?')}")
print(f"  Parsed fields: {data.get('parsed_fields', [])}")
ok("PROFILE")

# ── STEP 4: Verify Profile ──
step("4: Verify Profile")
resp = api("GET", "/v1/profile")
if resp.status_code != 200:
    fail("PROFILE", f"Profile GET returned {resp.status_code}")
profile_data = resp.json()["data"]
print(f"  Name: {profile_data.get('full_name', '?')[:50]}")
print(f"  Skills: {len(profile_data.get('skills', []))}")
ok("PROFILE")

# ── STEP 5: Create a base resume ──
step("5: Create Base Resume")
resp = api("POST", "/v1/resumes", json={
    "name": "Alex Chen — ML Engineer",
    "template_id": "modern_professional",
    "content": {"summary": resume_text.split('SUMMARY')[1].split('WORK')[0].strip() if 'SUMMARY' in resume_text else resume_text[:200]},
})
if resp.status_code not in (200, 201):
    fail("PROFILE", f"Resume create returned {resp.status_code}")
base_resume_id = resp.json()["data"]["resume_id"]
print(f"  Base Resume ID: {base_resume_id}")
ok("PROFILE")

# ── STEP 6: Search Jobs ──
step("6: Search Jobs")
resp = api("GET", "/v1/jobs", params={"limit": 10})
if resp.status_code != 200:
    fail("JOBS", f"Job search returned {resp.status_code}")
jobs = resp.json()["data"]
job_count = resp.json()["meta"]["count"]
print(f"  Found: {job_count} jobs")
if job_count > 0:
    job_id = jobs[0]["job_id"]
    print(f"  First job: {jobs[0]['title']} at {jobs[0].get('company', '?')}")
    ok("JOBS")
else:
    print("  WARNING: No jobs in DB (job discovery has not run).")
    print("  Run: docker compose exec api python -c \"from pathfinder.agent.infrastructure.celery_tasks.scraping import sweep_all_sources; sweep_all_sources.delay()\"")
    print("  Skipping MATCH and TAILOR — no jobs to match against.")
    results["JOBS"] = "SKIP (no data)"
    results["MATCHING"] = "SKIP (no jobs)"
    results["TAILORING"] = "SKIP (no jobs)"
    job_id = None

# ── STEP 7: Compute Match ──
if job_id is None:
    print("  Skipped — no jobs available")
else:
    step("7: Compute Match Score")
    resp = api("POST", "/v1/match/compute", params={"job_id": job_id})
    if resp.status_code != 200:
        fail("MATCHING", f"Match compute returned {resp.status_code}: {resp.text[:200]}")
    match_data = resp.json()["data"]
    print(f"  Overall Score: {match_data.get('overall_score', '?')}/100")
    dims = match_data.get("dimensions", {})
    for dim_name, dim_data in dims.items():
        print(f"    {dim_name}: {dim_data.get('score', 0):.0f}/100")
    ok("MATCHING")

# ── STEP 8: Ask the Agent ──
step("8: Agent — 'Find me AI/ML jobs matching my profile'")
resp = api("POST", "/v1/agent/execute", json={
    "message": "Find me AI and ML engineering jobs that match my profile. I have Python, PyTorch, and Kubernetes experience.",
    "stream": False,
})
if resp.status_code != 200:
    fail("AGENT", f"Agent returned {resp.status_code}: {resp.text[:200]}")
agent_data = resp.json()["data"]
print(f"  Intent: {agent_data.get('intent', '?')}")
print(f"  Response: {agent_data.get('response', '?')[:200]}")
ok("AGENT")

# ── STEP 9: Ingest Knowledge ──
step("9: Ingest Knowledge Document")
with open(KNOWLEDGE_FILE, "r") as f:
    knowledge_text = f.read()
resp = api("POST", "/v1/knowledge/ingest/document",
           files={"file": ("ml_requirements.txt", knowledge_text, "text/plain")},
           data={"title": "ML Engineer Job Requirements"})
if resp.status_code != 200:
    fail("KNOWLEDGE", f"Knowledge ingest returned {resp.status_code}: {resp.text[:200]}")
chunks = resp.json()["data"]["chunks_created"]
print(f"  Chunks created: {chunks}")
ok("KNOWLEDGE")

# ── STEP 10: Query Knowledge ──
step("10: Query Knowledge Search")
resp = api("POST", "/v1/knowledge/search", params={"query": "ML engineer requirements PyTorch Kubernetes", "top_k": 3})
if resp.status_code != 200:
    fail("KNOWLEDGE", f"Knowledge search returned {resp.status_code}: {resp.text[:200]}")
kresults = resp.json()["data"]
print(f"  Results: {len(kresults)}")
for r in kresults:
    print(f"    Score={r['score']} | {r['content'][:80]}...")
ok("KNOWLEDGE")

# ── STEP 11: Tailor Resume ──
if job_id is None:
    print("  Skipped — no jobs available for tailoring")
else:
    step("11: Tailor Resume")
    resp = api("POST", "/v1/tailoring/tailor",
               params={"base_resume_id": base_resume_id, "job_id": job_id, "strategy": "moderate"})
    if resp.status_code != 200:
        fail("TAILORING", f"Tailor returned {resp.status_code}: {resp.text[:200]}")
    tailor_data = resp.json()["data"]
    print(f"  Factuality Score: {tailor_data.get('factuality_score', '?')}")
    print(f"  ATS Score: {tailor_data.get('ats_score', '?')}")
    print(f"  Keyword Coverage: {tailor_data.get('keyword_coverage_before', 0):.0%} -> {tailor_data.get('keyword_coverage_after', 0):.0%}")
    diffs = tailor_data.get("diffs", [])
    for d in diffs:
        print(f"    {d['section']}: {d['change']} — {d.get('rationale', '')[:80]}")
    ok("TAILORING")

# ── FINAL REPORT ──
print(f"\n{'='*60}")
print(f"  PATHFINDER DEMO — COMPLETE")
print(f"{'='*60}")
for name, result in results.items():
    print(f"  {name:12s} = {result}")
passed = sum(1 for v in results.values() if v == "PASS")
total = len(results)
print(f"\n  OVERALL: {'PASS' if passed == total else 'FAIL'} ({passed}/{total} subsystems)")
print(f"{'='*60}")
sys.exit(0 if passed == total else 1)
