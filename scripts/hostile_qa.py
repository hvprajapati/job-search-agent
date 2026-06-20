#!/usr/bin/env python3
"""Hostile QA — 5 user personas + break-the-product tests."""
import requests, time, json, sys, statistics
from datetime import datetime

BASE = "http://localhost:8000"
RESULTS = []
FAILURES = []

def t(name, fn):
    """Run a test. Catch everything."""
    start = time.monotonic()
    try:
        fn()
        elapsed = (time.monotonic() - start) * 1000
        RESULTS.append({"name": name, "status": "PASS", "latency_ms": elapsed})
        print(f"  PASS: {name} ({elapsed:.0f}ms)")
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        msg = str(e)[:120]
        FAILURES.append({"name": name, "error": msg, "latency_ms": elapsed})
        RESULTS.append({"name": name, "status": "FAIL", "error": msg, "latency_ms": elapsed})
        print(f"  FAIL: {name} — {msg}")

def api(method, path, token="", **kw):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    r = requests.request(method, f"{BASE}{path}", headers=h, timeout=30, **kw)
    if r.status_code >= 500:
        raise Exception(f"Status {r.status_code}: {r.text[:150]}")
    return r

# ═══════════════════════════════════════════
print("=" * 60)
print("  HOSTILE QA — 5 Personas + Break Tests")
print("=" * 60)

# -- Setup: Register 5 personas --
print("\n-- Registering 5 Personas --")
personas = {}
for persona in ["AI/ML Engineer", "Data Engineer", "Backend Engineer", "Fresher", "Career Switcher"]:
    ts = int(time.time())
    email = f"{persona.lower().replace(' ', '-').replace('/', '-')}-{ts}@qa.dev"
    r = api("POST", "/v1/auth/register", json={
        "email": email, "password": "QATest123!", "full_name": persona, "accept_terms": True,
    })
    if r.status_code == 429:
        time.sleep(10)
        r = api("POST", "/v1/auth/register", json={"email": email, "password": "QATest123!", "full_name": persona, "accept_terms": True})
    token = r.json()["data"]["tokens"]["access_token"]
    personas[persona] = {"email": email, "token": token}
    print(f"  {persona}: {email}")

# -- Persona 1: Complete Journey (AI/ML Engineer) --
print("\n-- Persona 1: AI/ML Engineer — Complete Journey --")
p = personas["AI/ML Engineer"]
resume = """Alex Chen\nSenior ML Engineer\nalex@example.com\n\nSKILLS\nPython, PyTorch, TensorFlow, Kubernetes, Docker, PostgreSQL, MLOps, AWS, CI/CD, LLMs\n\nWORK EXPERIENCE\nStripe - Senior ML Engineer (2022-Present)\nBuilt real-time fraud detection models\n\nEDUCATION\nStanford - MS Computer Science (2020)"""

t("1.1 Upload resume", lambda: api("POST", "/v1/profile/import/resume", token=p["token"],
    files={"file": ("resume.txt", resume, "text/plain")}, data={"merge_strategy": "replace"}))

t("1.2 Get profile", lambda: api("GET", "/v1/profile", token=p["token"]))

r = api("GET", "/v1/jobs", token=p["token"], params={"limit": 3})
jobs = r.json().get("data", [])
t("1.3 Search jobs", lambda: jobs and len(jobs) > 0)

if jobs:
    jid = jobs[0]["job_id"]
    t("1.4 Compute match", lambda: api("POST", "/v1/match/compute", token=p["token"], params={"job_id": jid}))
    r = api("POST", "/v1/resumes", token=p["token"], json={"name": "Base", "template_id": "modern", "content": {"summary": "ML engineer."}})
    rid = r.json()["data"]["resume_id"] if r.status_code in (200,201) else None
    if rid:
        t("1.5 Tailor resume", lambda: api("POST", "/v1/tailoring/tailor", token=p["token"], params={"base_resume_id": rid, "job_id": jid, "strategy": "moderate"}))

t("1.6 Agent query", lambda: api("POST", "/v1/agent/execute", token=p["token"], json={"message": "Find me ML jobs", "stream": False}))

doc = "ML Best Practices: Use PyTorch for deep learning, Docker for deployment."
t("1.7 Upload knowledge", lambda: api("POST", "/v1/knowledge/ingest/document", token=p["token"],
    files={"file": ("ml.txt", doc, "text/plain")}, data={"title": "ML Best Practices"}))

t("1.8 Search knowledge", lambda: api("POST", "/v1/knowledge/search", token=p["token"], params={"query": "PyTorch deep learning", "top_k": 3}))

# -- Persona 2: Data Engineer --
print("\n-- Persona 2: Data Engineer --")
p = personas["Data Engineer"]
resume_de = """Priya Sharma\nSenior Data Engineer\npriya@data.com\n\nSKILLS\nPython, SQL, Apache Spark, Airflow, AWS, dbt, Snowflake, Kafka, Terraform, Docker\n\nWORK EXPERIENCE\nAmazon - Data Engineer II (2021-Present)\nBuilt ETL pipelines processing 30TB daily\n\nEDUCATION\nIIT Delhi - B.Tech CS (2019)"""

t("2.1 Upload resume", lambda: api("POST", "/v1/profile/import/resume", token=p["token"],
    files={"file": ("de_resume.txt", resume_de, "text/plain")}, data={"merge_strategy": "replace"}))

t("2.2 Search + filter", lambda: api("GET", "/v1/jobs", token=p["token"], params={"limit": 5, "query": "data"}))

t("2.3 Agent: find data jobs", lambda: api("POST", "/v1/agent/execute", token=p["token"], json={"message": "Find me data engineering roles", "stream": False}))

# -- Persona 3: Backend Engineer --
print("\n-- Persona 3: Backend Engineer --")
p = personas["Backend Engineer"]
resume_be = """Marcus Johnson\nSenior Backend Engineer\nmarcus@dev.io\n\nSKILLS\nGo, Rust, Java, PostgreSQL, Redis, Kafka, Kubernetes, Docker, gRPC, CI/CD\n\nWORK EXPERIENCE\nCloudflare - Senior Backend Engineer (2022-Present)\nDesigned rate-limiting service handling 2M req/s\n\nEDUCATION\nGeorgia Tech - BS CS (2018)"""

t("3.1 Upload resume", lambda: api("POST", "/v1/profile/import/resume", token=p["token"],
    files={"file": ("be_resume.txt", resume_be, "text/plain")}, data={"merge_strategy": "replace"}))

t("3.2 Agent query", lambda: api("POST", "/v1/agent/execute", token=p["token"], json={"message": "What backend jobs match my Go skills?", "stream": False}))

# -- Persona 4: Fresher --
print("\n-- Persona 4: Fresher --")
p = personas["Fresher"]
resume_fr = """Rahul Gupta\nCS Graduate\nrahul@college.edu\n\nSKILLS\nJava, Python, JavaScript, React, Node.js, PostgreSQL, Git, Linux, REST APIs\n\nPROJECTS\nE-Commerce Microservices - Built full-stack platform with React + Spring Boot\n\nEDUCATION\nUniversity of Pune - B.Tech CS (2024)"""

t("4.1 Upload fresher resume", lambda: api("POST", "/v1/profile/import/resume", token=p["token"],
    files={"file": ("fresher.txt", resume_fr, "text/plain")}, data={"merge_strategy": "replace"}))

t("4.2 Browse entry-level", lambda: api("GET", "/v1/jobs", token=p["token"], params={"limit": 5}))

# -- Persona 5: Career Switcher --
print("\n-- Persona 5: Career Switcher --")
p = personas["Career Switcher"]
resume_cs = """Sarah Kim\nMarketing Manager → Aspiring Data Analyst\nsarah@switch.com\n\nSKILLS\nSQL, Excel, Python (learning), Tableau, Data Visualization, Communication\n\nWORK EXPERIENCE\nShopify - Marketing Manager (2020-Present)\nAnalyzed campaign data using SQL and Tableau\n\nEDUCATION\nUniversity of Toronto - BA Business (2018)"""

t("5.1 Upload career-switcher resume", lambda: api("POST", "/v1/profile/import/resume", token=p["token"],
    files={"file": ("switch.txt", resume_cs, "text/plain")}, data={"merge_strategy": "replace"}))

t("5.2 Ask agent for advice", lambda: api("POST", "/v1/agent/execute", token=p["token"], json={"message": "I'm switching from marketing to data analytics. What should I do?", "stream": False}))

# ═══════════════════════════════════════════
# PART 2: BREAK THE PRODUCT
# ═══════════════════════════════════════════
print("\n-- BREAK TESTS --")
p = personas["AI/ML Engineer"]  # use existing user

t("B1. Empty resume file", lambda: api("POST", "/v1/profile/import/resume", token=p["token"],
    files={"file": ("empty.txt", "", "text/plain")}, data={"merge_strategy": "replace"}))

t("B2. Giant resume (>1MB text)", lambda: api("POST", "/v1/profile/import/resume", token=p["token"],
    files={"file": ("giant.txt", "SKILLS\n" + "Skill, " * 50000, "text/plain")}, data={"merge_strategy": "replace"}))

t("B3. Binary file as resume", lambda: api("POST", "/v1/profile/import/resume", token=p["token"],
    files={"file": ("fake.pdf", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "application/pdf")}, data={"merge_strategy": "replace"}))

t("B4. Invalid job ID match", lambda: api("POST", "/v1/match/compute", token=p["token"],
    params={"job_id": "00000000-0000-0000-0000-000000000000"}))

t("B5. Empty agent message", lambda: api("POST", "/v1/agent/execute", token=p["token"],
    json={"message": "", "stream": False}))

t("B6. Agent: very long message", lambda: api("POST", "/v1/agent/execute", token=p["token"],
    json={"message": "Find jobs " * 500, "stream": False}))

t("B7. Knowledge: empty document", lambda: api("POST", "/v1/knowledge/ingest/document", token=p["token"],
    files={"file": ("empty.txt", "", "text/plain")}, data={"title": "Empty"}))

t("B8. Knowledge: nonsense search", lambda: api("POST", "/v1/knowledge/search", token=p["token"],
    params={"query": "asdfhjklqwertyuiopzxcvbnm", "top_k": 5}))

t("B9. Missing auth header", lambda: api("GET", "/v1/profile"))

t("B10. Invalid JWT", lambda: api("GET", "/v1/profile", token="invalid.jwt.token"))

t("B11. Login with SQL injection", lambda: api("POST", "/v1/auth/login",
    json={"email": "' OR 1=1 --", "password": "anything"}))

t("B12. Register: missing fields", lambda: api("POST", "/v1/auth/register",
    json={"email": "bad@test.com"}))

t("B13. Tailor: non-existent resume", lambda: api("POST", "/v1/tailoring/tailor", token=p["token"],
    params={"base_resume_id": "00000000-0000-0000-0000-000000000000", "job_id": "00000000-0000-0000-0000-000000000001", "strategy": "moderate"}))

t("B14. Tailor: invalid strategy", lambda: api("POST", "/v1/tailoring/tailor", token=p["token"],
    params={"base_resume_id": "00000000-0000-0000-0000-000000000001", "job_id": "00000000-0000-0000-0000-000000000001", "strategy": "nuclear"}))

# -- Performance measurements --
print("\n-- PERFORMANCE --")
r = api("GET", "/v1/health/live")
t("P1. Health check latency", lambda: r.elapsed.total_seconds() < 0.1)

r = api("GET", "/v1/jobs", token=p["token"], params={"limit": 100})
t("P2. 100-job listing", lambda: r.elapsed.total_seconds() < 2)

r = api("GET", "/v1/jobs", token=p["token"], params={"query": "engineer", "limit": 10})
t("P3. Job search latency", lambda: r.elapsed.total_seconds() < 1)

# -- Summary --
print(f"\n{'='*60}")
print(f"  HOSTILE QA RESULTS")
print(f"{'='*60}")
passed = sum(1 for r in RESULTS if r["status"] == "PASS")
total = len(RESULTS)
print(f"  Passed: {passed}/{total} ({passed/total*100:.0f}%)")
print(f"  Failed: {len(FAILURES)}")

if FAILURES:
    print(f"\n  FAILURES:")
    for f in FAILURES:
        print(f"    - {f['name']}: {f['error']}")

lats = [r["latency_ms"] for r in RESULTS if r["status"] == "PASS"]
if lats:
    print(f"\n  Latency (passing tests):")
    print(f"    Mean: {statistics.mean(lats):.0f}ms  P50: {statistics.median(lats):.0f}ms  Max: {max(lats):.0f}ms")

with open("scripts/hostile_qa_results.json", "w") as f:
    json.dump({"total": total, "passed": passed, "failed": len(FAILURES), "results": RESULTS}, f, indent=2, default=str)

print(f"\n  Results saved to scripts/hostile_qa_results.json")
sys.exit(0 if len(FAILURES) == 0 else 1)
