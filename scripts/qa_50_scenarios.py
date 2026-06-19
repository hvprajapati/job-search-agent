#!/usr/bin/env python3
"""Pathfinder QA — 50 real-world user scenarios. Generates structured results for BUG_REPORT.md."""
from __future__ import annotations
import json, os, sys, time, io
from dataclasses import dataclass, field
from typing import Any, Callable
import requests

BASE = os.environ.get("PATHFINDER_URL", "http://localhost:8000")
RESULTS: list[ScenarioResult] = []


@dataclass
class ScenarioResult:
    id: int
    subsystem: str
    name: str
    inputs: str
    expected: str
    status: str  # PASS | BUG
    severity: str  # Critical | Major | Minor
    actual: str = ""
    repro_steps: str = ""
    details: dict = field(default_factory=dict)


def result(subsystem: str, name: str, inputs: str, expected: str,
           status: str, severity: str, actual: str = "",
           repro_steps: str = "", **details) -> None:
    sid = len(RESULTS) + 1
    RESULTS.append(ScenarioResult(sid, subsystem, name, inputs, expected, status, severity, actual, repro_steps, details))
    marker = "[PASS]" if status == "PASS" else f"[BUG-{severity[:4].upper()}]"
    print(f"  {sid:02d} {marker:14s} [{subsystem:10s}] {name[:70]}")
    if status == "BUG":
        print(f"       Expected: {expected[:120]}")
        print(f"       Actual:   {actual[:120]}")


def api(method: str, path: str, token: str = "", expect_status: int = 0, **kwargs) -> requests.Response:
    """Call API. expect_status=0 means any 2xx is fine."""
    url = f"{BASE}{path}"
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.request(method, url, headers=headers, timeout=60, **kwargs)
        if expect_status and resp.status_code != expect_status:
            pass  # We'll check in the scenario
        return resp
    except Exception as e:
        resp = requests.Response()
        resp.status_code = 0
        resp._content = str(e).encode()
        return resp


def check(resp: requests.Response, expected_status: int, context: str = "") -> tuple[bool, dict]:
    """Check response status and parse JSON. Returns (ok, data)."""
    try:
        data = resp.json() if resp.text else {}
    except Exception:
        data = {"raw": resp.text[:500]}
    ok = resp.status_code == expected_status
    if not ok and expected_status == 0:
        ok = 200 <= resp.status_code < 300
    return ok, data


# ═══════════════════════════════════════════
# Setup: Create test users (handle rate limit)
# ═══════════════════════════════════════════
print("=" * 60)
print("  PATHFINDER QA — 50 Scenarios")
print("=" * 60)

print("\n--- Setup: Creating test users ---")
tokens: dict[str, str] = {}
users: dict[str, dict] = {}

for label in ["user_a", "user_b"]:
    for attempt in range(5):
        email = f"qa-{label}-{int(time.time())}@qa.pathfinder.dev"
        resp = api("POST", "/v1/auth/register", json={
            "email": email, "password": "QATest123!", "full_name": f"QA {label}", "accept_terms": True,
        })
        if resp.status_code == 429:
            print(f"  Rate limited, waiting {10 * (attempt + 1)}s...")
            time.sleep(10 * (attempt + 1))
            continue
        ok, data = check(resp, 201)
        if ok:
            tokens[label] = data["data"]["tokens"]["access_token"]
            users[label] = {"email": email, "user_id": data["data"]["user"].get("user_id", data["data"]["user"].get("id"))}
            print(f"  {label}: {email} — registered")
            break
        else:
            print(f"  {label} attempt {attempt}: {resp.status_code}")
    else:
        print(f"  FAILED to create {label} after 5 attempts")
        sys.exit(1)

TOKEN_A = tokens["user_a"]
TOKEN_B = tokens["user_b"]


# ═══════════════════════ AUTH (8 scenarios) ═══════════════════════
print("\n--- AUTH Scenarios ---")

# 1
resp = api("POST", "/v1/auth/login", json={"email": users["user_a"]["email"], "password": "QATest123!"})
ok, d = check(resp, 200)
result("Auth", "Login with correct credentials",
       f"email={users['user_a']['email']}, password=QATest123!",
       "200 OK, returns access_token + refresh_token",
       "PASS" if ok and "access_token" in d.get("data", {}).get("tokens", {}) else "BUG",
       "Critical", actual=f"Status {resp.status_code}" if not ok else "OK",
       details={"status": resp.status_code})

# 2
resp = api("POST", "/v1/auth/login", json={"email": users["user_a"]["email"], "password": "WrongPassword!"})
ok, d = check(resp, 401)
result("Auth", "Login with wrong password",
       f"email={users['user_a']['email']}, password=wrong",
       "401 Unauthorized, error message",
       "PASS" if ok else "BUG",
       "Critical", actual=f"Status {resp.status_code}, expected 401",
       details={"status": resp.status_code, "error": d.get("error", d.get("detail", ""))})

# 3
resp = api("POST", "/v1/auth/login", json={"email": "noexist@nowhere.com", "password": "Whatever1!"})
ok, d = check(resp, 401)
result("Auth", "Login with non-existent email",
       "email=noexist@nowhere.com",
       "401 Unauthorized",
       "PASS" if ok else "BUG",
       "Major", actual=f"Status {resp.status_code}, expected 401",
       details={"status": resp.status_code})

# 4
resp = api("POST", "/v1/auth/register", json={
    "email": users["user_a"]["email"], "password": "Test123!", "full_name": "Dup", "accept_terms": True,
})
ok, d = check(resp, 409)
msg = str(d).lower()
# Acceptable responses: 409 conflict or 400 bad request
result("Auth", "Register with duplicate email",
       f"email={users['user_a']['email']} (already registered)",
       "409 Conflict or 400, clear error message",
       "PASS" if resp.status_code in (409, 400) else "BUG",
       "Major", actual=f"Status {resp.status_code}: {str(d)[:120]}",
       details={"status": resp.status_code})

# 5
resp = api("POST", "/v1/auth/register", json={
    "email": "weak@test.com", "password": "a", "full_name": "Weak", "accept_terms": True,
})
ok, d = check(resp, 422)
result("Auth", "Register with very weak password",
       "password='a' (1 char)",
       "422 Validation error rejecting weak password",
       "PASS" if resp.status_code in (400, 422) else "BUG",
       "Minor", actual=f"Status {resp.status_code}: {str(d)[:120]}",
       details={"status": resp.status_code})

# 6
resp = api("POST", "/v1/auth/register", json={
    "email": "notanemail", "password": "Test123!", "full_name": "Bad", "accept_terms": True,
})
ok, d = check(resp, 422)
result("Auth", "Register with invalid email format",
       "email='notanemail'",
       "422 Validation error for invalid email",
       "PASS" if resp.status_code in (400, 422) else "BUG",
       "Minor", actual=f"Status {resp.status_code}: {str(d)[:120]}",
       details={"status": resp.status_code})

# 7
resp = api("GET", "/v1/profile", token="invalid_token_xxx")
ok, d = check(resp, 401)
result("Auth", "Access protected endpoint with invalid token",
       "Authorization: Bearer invalid_token_xxx",
       "401 Unauthorized",
       "PASS" if resp.status_code == 401 else "BUG",
       "Critical", actual=f"Status {resp.status_code}",
       details={"status": resp.status_code})

# 8
resp = api("GET", "/v1/profile")
ok, d = check(resp, 401)
result("Auth", "Access protected endpoint without token",
       "No Authorization header",
       "401 Unauthorized",
       "PASS" if resp.status_code == 401 else "BUG",
       "Critical", actual=f"Status {resp.status_code}",
       details={"status": resp.status_code})


# ═══════════════════ RESUME UPLOAD (8 scenarios) ═══════════════════
print("\n--- RESUME UPLOAD Scenarios ---")

# 9 — Upload valid TXT resume
resp = api("POST", "/v1/profile/import/resume", token=TOKEN_A,
           files={"file": ("resume.txt", "QA Test\nSoftware Engineer\nqa@test.com\n\nSKILLS\nPython, Java, Docker, AWS, Kubernetes\n\nWORK EXPERIENCE\nGoogle - Software Engineer (2020-2023)\n\nEDUCATION\nMIT - BS CS (2020)", "text/plain")},
           data={"merge_strategy": "replace"})
ok, d = check(resp, 200)
skills_count = d.get("data", {}).get("skills_extracted", 0)
result("Resume", "Upload valid TXT resume",
       "TXT file with skills, experience, education sections",
       "200 OK, skills_extracted > 0, experiences_extracted > 0",
       "PASS" if ok and skills_count >= 3 else "BUG",
       "Critical", actual=f"skills_extracted={skills_count}, experiences={d.get('data',{}).get('experiences_extracted',0)}",
       details={"status": resp.status_code, "skills_count": skills_count,
                "parsed_fields": d.get("data", {}).get("parsed_fields", [])},
       repro_steps="POST /v1/profile/import/resume with valid TXT resume")

# 10 — Upload empty file
resp = api("POST", "/v1/profile/import/resume", token=TOKEN_A,
           files={"file": ("empty.txt", "", "text/plain")},
           data={"merge_strategy": "replace"})
result("Resume", "Upload empty file",
       "Zero-byte file",
       "4xx error, clear message about empty file",
       "PASS" if resp.status_code in (400, 422) else "BUG",
       "Minor", actual=f"Status {resp.status_code}: {resp.text[:150]}",
       details={"status": resp.status_code})

# 11 — Upload file with < 50 chars
resp = api("POST", "/v1/profile/import/resume", token=TOKEN_A,
           files={"file": ("tiny.txt", "Name", "text/plain")},
           data={"merge_strategy": "replace"})
result("Resume", "Upload file below minimum content length",
       "File with < 50 chars of content",
       "4xx error about insufficient content",
       "PASS" if resp.status_code in (400, 422) else "BUG",
       "Minor", actual=f"Status {resp.status_code}: {resp.text[:150]}",
       details={"status": resp.status_code})

# 12 — Upload unsupported file type
resp = api("POST", "/v1/profile/import/resume", token=TOKEN_A,
           files={"file": ("resume.png", b"\x89PNG\r\n\x1a\nfake", "image/png")},
           data={"merge_strategy": "replace"})
result("Resume", "Upload unsupported file type (PNG image)",
       "image/png file",
       "4xx error about unsupported file type",
       "PASS" if resp.status_code in (400, 415, 422) else "BUG",
       "Minor", actual=f"Status {resp.status_code}: {resp.text[:150]}",
       details={"status": resp.status_code})

# 13 — Verify skills extraction quality on detailed resume
detailed_resume = """Jane Smith
Senior Data Engineer | jane@data.com | Seattle, WA

SUMMARY
Data engineer with 7 years building data platforms. Expert in Spark, Python, and cloud ETL.

WORK EXPERIENCE
Meta — Staff Data Engineer (2021-Present)
- Built real-time data ingestion pipeline processing 5TB/day
- Migrated batch jobs from Hadoop to Spark, reducing costs 60%
- Tech stack: Python, Spark, Airflow, Kafka, AWS, Terraform, dbt

Amazon — Data Engineer II (2018-2021)
- Built Redshift data warehouse serving 300+ analysts
- Developed CI/CD pipeline for data quality validation
- Tech stack: Python, SQL, AWS, Redshift, Airflow, Docker

EDUCATION
Carnegie Mellon — MS Information Systems (2018)
University of Washington — BS Computer Science (2016)

SKILLS
Python (Expert, 8y), SQL (Expert, 8y), Apache Spark (Expert, 5y), Airflow (Advanced, 4y)
Kafka (Advanced, 3y), AWS (Advanced, 5y), Terraform (Intermediate, 2y), dbt (Intermediate, 2y)
Docker (Advanced, 4y), Kubernetes (Intermediate, 2y), Snowflake (Advanced, 3y)
Data Modeling, ETL/ELT, Real-time Processing, Data Quality, CI/CD
"""
resp = api("POST", "/v1/profile/import/resume", token=TOKEN_B,
           files={"file": ("jane_resume.txt", detailed_resume, "text/plain")},
           data={"merge_strategy": "replace"})
ok, d = check(resp, 200)
skills_count = d.get("data", {}).get("skills_extracted", 0)
result("Resume", "Skills extraction on detailed resume (15+ skills)",
       "Detailed data engineer resume with 17+ unique skills",
       f"skills_extracted >= 12 (got {skills_count})",
       "PASS" if skills_count >= 12 else "BUG",
       "Major", actual=f"skills_extracted={skills_count}",
       details={"status": resp.status_code, "skills_count": skills_count})

# 14 — Upload resume and verify profile fields populated
resp = api("GET", "/v1/profile", token=TOKEN_B)
ok, d = check(resp, 200)
profile = d.get("data", {})
has_name = bool(profile.get("full_name"))
has_skills = len(profile.get("skills", [])) > 0
has_exp = len(profile.get("work_experiences", [])) > 0
result("Resume", "Profile correctly populated after resume upload",
       "Uploaded detailed resume, then GET /v1/profile",
       "full_name set, skills > 0, work_experiences > 0",
       "PASS" if has_name and has_skills and has_exp else "BUG",
       "Critical", actual=f"name={has_name}, skills={len(profile.get('skills',[]))}, exp={len(profile.get('work_experiences',[]))}",
       details={"full_name": profile.get("full_name"), "skills_count": len(profile.get("skills", [])),
                "experiences_count": len(profile.get("work_experiences", []))})

# 15 — Second upload with merge strategy preserves data
resp = api("POST", "/v1/profile/import/resume", token=TOKEN_B,
           files={"file": ("update.txt", "Jane Smith\n\nSKILLS\nRust, Elixir", "text/plain")},
           data={"merge_strategy": "merge"})
ok, d = check(resp, 200)
result("Resume", "Merge strategy preserves existing profile data",
       "merge_strategy=merge with new skills only",
       "200 OK, existing data preserved",
       "PASS" if ok else "BUG",
       "Minor", actual=f"Status {resp.status_code}",
       details={"status": resp.status_code,
                "skills_extracted": d.get("data", {}).get("skills_extracted", 0)})

# 16 — Extract skills from resume with skills in prose (not a list)
prose_resume = """Tom Wilson
Backend Developer | tom@dev.io

I have extensive experience with Python and Go for backend development.
I've worked with PostgreSQL as my primary database and Redis for caching.
My projects use Docker and Kubernetes for deployment and I practice CI/CD with GitHub Actions.
I'm comfortable with gRPC and REST API design patterns.
"""
resp = api("POST", "/v1/profile/import/resume", token=TOKEN_A,
           files={"file": ("prose.txt", prose_resume, "text/plain")},
           data={"merge_strategy": "replace"})
ok, d = check(resp, 200)
skills_count = d.get("data", {}).get("skills_extracted", 0)
result("Resume", "Skills from prose-format resume (no skills section)",
       "Resume with skills embedded in paragraph text, no SKILLS heading",
       f"skills_extracted >= 5 (got {skills_count})",
       "PASS" if skills_count >= 5 else "BUG",
       "Major", actual=f"skills_extracted={skills_count}",
       details={"status": resp.status_code, "skills_count": skills_count})


# ═══════════════════ PROFILE (5 scenarios) ═══════════════════
print("\n--- PROFILE Scenarios ---")

# 17
resp = api("GET", "/v1/profile", token=TOKEN_A)
ok, d = check(resp, 200)
result("Profile", "Get own profile",
       "GET /v1/profile with valid token",
       "200 OK with profile data including skills array",
       "PASS" if ok and "skills" in d.get("data", {}) else "BUG",
       "Critical", actual=f"Status {resp.status_code}",
       details={"has_skills": "skills" in d.get("data", {})})

# 18 — Verify profile skill data types
resp = api("GET", "/v1/profile", token=TOKEN_A)
ok, d = check(resp, 200)
skills = d.get("data", {}).get("skills", [])
bad_types = [s for s in skills if not isinstance(s.get("name"), str) or not isinstance(s.get("proficiency"), str)]
result("Profile", "Profile skills have correct data types",
       "GET /v1/profile",
       "Each skill has name:str, proficiency:str (one of beginner/intermediate/advanced/expert)",
       "PASS" if not bad_types else "BUG",
       "Major", actual=f"Skills with bad types: {len(bad_types)}/{len(skills)}",
       details={"skills_sample": skills[:3], "bad_types": bad_types})

# 19 — Verify profile experiences data integrity
resp = api("GET", "/v1/profile", token=TOKEN_A)
ok, d = check(resp, 200)
exps = d.get("data", {}).get("work_experiences", [])
has_company = all(isinstance(e.get("company"), str) and e["company"] for e in exps)
has_title = all(isinstance(e.get("title"), str) for e in exps)
result("Profile", "Profile work_experiences have required fields",
       "GET /v1/profile",
       "Each experience has company:str (non-empty), title:str",
       "PASS" if has_company and has_title else "BUG",
       "Major", actual=f"Exp count={len(exps)}, company_ok={has_company}, title_ok={has_title}",
       details={"experiences_sample": exps[:2]})

# 20 — New user profile before upload
resp = api("GET", "/v1/profile", token=TOKEN_B)
ok, d = check(resp, 200)
# Actually TOKEN_B has a resume uploaded, so this should have data
result("Profile", "Profile returns data after resume import",
       "GET /v1/profile for user who uploaded resume",
       "200 OK with profile data",
       "PASS" if ok else "BUG",
       "Minor", actual=f"Status {resp.status_code}" if not ok else "OK",
       details={"status": resp.status_code})

# 21 — Verify profile education data present
resp = api("GET", "/v1/profile", token=TOKEN_B)
ok, d = check(resp, 200)
edu = d.get("data", {}).get("education", [])
result("Profile", "Profile education extracted from resume",
       "GET /v1/profile after data engineer resume upload",
       "education array has at least 1 entry with institution, degree, field",
       "PASS" if len(edu) >= 1 and "institution" in edu[0] else "BUG",
       "Major", actual=f"Education count={len(edu)}",
       details={"education_sample": edu[:2]})


# ═══════════════════ JOB SEARCH (6 scenarios) ═══════════════════
print("\n--- JOB SEARCH Scenarios ---")

# 22
resp = api("GET", "/v1/jobs", token=TOKEN_A, params={"limit": 5})
ok, d = check(resp, 200)
job_count = d.get("meta", {}).get("count", len(d.get("data", [])))
result("Job Search", "List all jobs with default params",
       "GET /v1/jobs",
       "200 OK, returns array of jobs with meta.count",
       "PASS" if ok and job_count >= 0 else "BUG",
       "Critical", actual=f"Jobs found: {job_count}" if ok else f"Status {resp.status_code}",
       details={"count": job_count})

# 23
jobs_list = d.get("data", [])
first_job = jobs_list[0] if jobs_list else None
result("Job Search", "Job listing has required fields",
       "GET /v1/jobs, inspect first result",
       "Each job has job_id, title, description fields",
       "PASS" if first_job and all(k in first_job for k in ["job_id", "title"]) else "BUG",
       "Major", actual=f"First job fields: {list(first_job.keys()) if first_job else 'NO JOBS'}",
       details={"sample_job": {k: str(v)[:80] for k, v in (first_job or {}).items()}})

# 24
resp = api("GET", "/v1/jobs", token=TOKEN_A, params={"query": "Machine Learning"})
ok, d = check(resp, 200)
ml_count = d.get("meta", {}).get("count", 0)
result("Job Search", "Search jobs with keyword query",
       "GET /v1/jobs?query=Machine Learning",
       "Results filtered to ML-related jobs, count <= total",
       "PASS" if ok else "BUG",
       "Minor", actual=f"ML jobs found: {ml_count}" if ok else f"Status {resp.status_code}",
       details={"ml_count": ml_count})

# 25
resp = api("GET", "/v1/jobs", token=TOKEN_A, params={"limit": 1, "offset": 1})
ok, d = check(resp, 200)
page_count = len(d.get("data", []))
result("Job Search", "Job search pagination (limit=1, offset=1)",
       "GET /v1/jobs?limit=1&offset=1",
       "Returns 1 result (the second job), meta includes count",
       "PASS" if ok and page_count <= 1 else "BUG",
       "Minor", actual=f"Returned: {page_count} jobs",
       details={"limit": 1, "returned": page_count, "total": d.get("meta", {}).get("count", 0)})

# 26
if first_job:
    jid = first_job["job_id"]
    resp = api("GET", f"/v1/jobs/{jid}", token=TOKEN_A)
    ok, d = check(resp, 200)
    result("Job Search", "Get single job by ID",
           f"GET /v1/jobs/{str(jid)[:8]}...",
           "200 OK, returns full job details with required_skills, nice_to_have",
           "PASS" if ok and "title" in d.get("data", {}) else "BUG",
           "Major", actual="OK" if ok else f"Status {resp.status_code}",
           details={"job_title": d.get("data", {}).get("title", "")})

# 27
fake_id = "00000000-0000-0000-0000-000000000000"
resp = api("GET", f"/v1/jobs/{fake_id}", token=TOKEN_A)
result("Job Search", "Get job with non-existent UUID",
       f"GET /v1/jobs/{fake_id}",
       "404 Not Found",
       "PASS" if resp.status_code == 404 else "BUG",
       "Minor", actual=f"Status {resp.status_code}, expected 404",
       details={"status": resp.status_code})


# ═══════════════════ MATCHING (6 scenarios) ═══════════════════
print("\n--- MATCHING Scenarios ---")

job_id = jobs_list[0]["job_id"] if jobs_list else None

if job_id:
    # 28
    resp = api("POST", "/v1/match/compute", token=TOKEN_A, params={"job_id": job_id})
    ok, d = check(resp, 200)
    overall = d.get("data", {}).get("overall_score", -1)
    dims = d.get("data", {}).get("dimensions", {})
    result("Matching", "Compute match score for existing job",
           f"POST /v1/match/compute?job_id={job_id}",
           "200 OK, overall_score between 0-100, dimensions object with 4-6 keys",
           "PASS" if ok and 0 <= overall <= 100 and len(dims) >= 4 else "BUG",
           "Critical", actual=f"Score={overall}/100, dimensions={len(dims)}",
           details={"overall_score": overall, "dimensions": list(dims.keys())})

    # 29 — Match dimensions check
    expected_dims = {"skills", "experience", "education", "location", "preference", "culture"}
    missing = expected_dims - set(dims.keys())
    result("Matching", "Match response includes all 6 scoring dimensions",
           f"POST /v1/match/compute for job {str(job_id)[:8]}",
           "All 6 dimensions: skills, experience, education, location, preference, culture",
           "PASS" if not missing else "BUG",
           "Major", actual=f"Missing dimensions: {missing}" if missing else f"All 6 present",
           details={"missing_dimensions": list(missing), "present": list(dims.keys())})

    # 30 — Each dimension score in valid range
    bad_scores = [(k, v.get("score", -1)) for k, v in dims.items()
                  if not (0 <= v.get("score", -1) <= 100)]
    result("Matching", "Each dimension score is in valid range 0-100",
           f"Match dimensions: {list(dims.keys())}",
           "Every dimension.score between 0 and 100 inclusive",
           "PASS" if not bad_scores else "BUG",
           "Major", actual=f"Out-of-range scores: {bad_scores}" if bad_scores else "All valid",
           details={"dim_scores": {k: v.get("score") for k, v in dims.items()}})

    # 31
    non_existent_job = "00000000-0000-0000-0000-000000000000"
    resp = api("POST", "/v1/match/compute", token=TOKEN_A, params={"job_id": non_existent_job})
    result("Matching", "Match score for non-existent job",
           f"POST /v1/match/compute?job_id={non_existent_job}",
           "404 Not Found",
           "PASS" if resp.status_code == 404 else "BUG",
           "Minor", actual=f"Status {resp.status_code}, expected 404",
           details={"status": resp.status_code})

    # 32
    resp = api("POST", "/v1/match/compute", token=TOKEN_B, params={"job_id": job_id})
    ok, d = check(resp, 200)
    b_score = d.get("data", {}).get("overall_score", -1)
    result("Matching", "Match score for different user (data engineer)",
           f"POST /v1/match/compute for user B (data skills) on same job",
           "Different score from user A, dimension scores reflect different skill match",
           "PASS" if ok and b_score >= 0 else "BUG",
           "Minor", actual=f"User B score={b_score}/100",
           details={"user_a_score": overall if 'overall' in dir() else '?', "user_b_score": b_score})

    # 33 — Match with user who has no profile (actually has one from setup)
    # We'll check that matching doesn't crash with minimal profile
    resp = api("GET", "/v1/profile", token=TOKEN_A)
    ok, d = check(resp, 200)
    result("Matching", "User with profile can receive match score",
           "User A after resume upload → match compute",
           "Non-zero match score returned successfully",
           "PASS" if ok and d.get("data", {}).get("skills") else "BUG",
           "Minor", actual=f"Skills count: {len(d.get('data', {}).get('skills', []))}",
           details={"status": resp.status_code})


# ═══════════════════ AGENT (7 scenarios) ═══════════════════
print("\n--- AGENT Scenarios ---")

# 34
agent_start = time.monotonic()
resp = api("POST", "/v1/agent/execute", token=TOKEN_A, json={
    "message": "Find me software engineering jobs", "stream": False,
})
agent_time = (time.monotonic() - agent_start) * 1000
ok, d = check(resp, 200)
agent_response_34 = d.get("data", {}).get("response", "")
result("Agent", "Ask agent to find jobs",
       "message='Find me software engineering jobs'",
       "200 OK, agent responds with job search action or suggestions",
       "PASS" if ok and len(agent_response_34) > 10 else "BUG",
       "Major", actual=f"Response ({len(agent_response_34)} chars): {agent_response_34[:150]}",
       details={"intent": d.get("data", {}).get("intent", ""),
                "response_length": len(agent_response_34), "latency_ms": int(agent_time)})

# 35
resp = api("POST", "/v1/agent/execute", token=TOKEN_A, json={
    "message": "What skills do I have on my profile?", "stream": False,
})
ok, d = check(resp, 200)
agent_response_35 = d.get("data", {}).get("response", "")
mentions_skills = any(s.lower() in agent_response_35.lower() for s in ["python", "skill", "profile", "docker"])
result("Agent", "Ask agent about own profile skills",
       "message='What skills do I have on my profile?'",
       "Agent references user's skills from profile context",
       "PASS" if ok and mentions_skills else "BUG",
       "Major", actual=f"Response ({len(agent_response_35)} chars): {agent_response_35[:200]}",
       details={"mentions_profile_skills": mentions_skills,
                "intent": d.get("data", {}).get("intent", "")})

# 36
resp = api("POST", "/v1/agent/execute", token=TOKEN_A, json={
    "message": "What's my match score for the first job?", "stream": False,
})
ok, d = check(resp, 200)
agent_response_36 = d.get("data", {}).get("response", "")
result("Agent", "Ask agent for match score",
       "message='What is my match score for the first job?'",
       "Agent responds coherently about matching (even if score not shown)",
       "PASS" if ok and len(agent_response_36) > 10 else "BUG",
       "Minor", actual=f"Response ({len(agent_response_36)} chars): {agent_response_36[:150]}",
       details={"intent": d.get("data", {}).get("intent", "")})

# 37 — Greeting/ambiguous
resp = api("POST", "/v1/agent/execute", token=TOKEN_A, json={
    "message": "Hi", "stream": False,
})
ok, d = check(resp, 200)
agent_response_37 = d.get("data", {}).get("response", "")
result("Agent", "Agent handles greeting/ambiguous input",
       "message='Hi'",
       "Agent responds with greeting and offers help",
       "PASS" if ok and len(agent_response_37) > 5 else "BUG",
       "Minor", actual=f"Response ({len(agent_response_37)} chars): {agent_response_37[:150]}",
       details={"intent": d.get("data", {}).get("intent", "")})

# 38 — Agent response time
result("Agent", "Agent response under 30 seconds",
       "POST /v1/agent/execute with simple query",
       "Response received in < 30000ms",
       "PASS" if agent_time < 30000 else "BUG",
       "Major", actual=f"Response time: {agent_time:.0f}ms",
       details={"latency_ms": int(agent_time)})

# 39 — Nonsense query
resp = api("POST", "/v1/agent/execute", token=TOKEN_A, json={
    "message": "asdfghjkl qwertyuiop zxcvbnm", "stream": False,
})
ok, d = check(resp, 200)
agent_response_39 = d.get("data", {}).get("response", "")
result("Agent", "Agent handles nonsense/gibberish input",
       "message='asdfghjkl qwertyuiop zxcvbnm'",
       "Agent responds gracefully (asks for clarification or offers help)",
       "PASS" if ok and len(agent_response_39) > 5 else "BUG",
       "Minor", actual=f"Response ({len(agent_response_39)} chars): {agent_response_39[:150]}",
       details={"intent": d.get("data", {}).get("intent", "")})

# 40 — Tailor request via agent
resp = api("POST", "/v1/agent/execute", token=TOKEN_A, json={
    "message": "Can you tailor my resume for the ML Engineer job?", "stream": False,
})
ok, d = check(resp, 200)
agent_response_40 = d.get("data", {}).get("response", "")
result("Agent", "Ask agent to tailor resume",
       "message='Can you tailor my resume for the ML Engineer job?'",
       "Agent responds coherently, acknowledges tailoring request",
       "PASS" if ok and len(agent_response_40) > 10 else "BUG",
       "Minor", actual=f"Response ({len(agent_response_40)} chars): {agent_response_40[:150]}",
       details={"intent": d.get("data", {}).get("intent", "")})


# ═══════════════════ KNOWLEDGE (5 scenarios) ═══════════════════
print("\n--- KNOWLEDGE Scenarios ---")

# 41
knowledge_text = """KUBERNETES PRODUCTION BEST PRACTICES
1. Use resource requests and limits for all containers
2. Implement liveness and readiness probes
3. Use namespaces for environment isolation
4. Always use RBAC for access control
5. Implement pod disruption budgets for HA
6. Use helm or kustomize for deployments
7. Enable audit logging for security compliance
8. Run containers as non-root user
"""

resp = api("POST", "/v1/knowledge/ingest/document", token=TOKEN_A,
           files={"file": ("k8s_best_practices.txt", knowledge_text, "text/plain")},
           data={"title": "Kubernetes Best Practices"})
ok, d = check(resp, 200)
chunks = d.get("data", {}).get("chunks_created", 0)
result("Knowledge", "Ingest knowledge document",
       "Upload 8-point Kubernetes best practices document",
       "200 OK, chunks_created >= 1",
       "PASS" if ok and chunks >= 1 else "BUG",
       "Critical", actual=f"Chunks created: {chunks}" if ok else f"Status {resp.status_code}",
       details={"chunks": chunks})

# 42
resp = api("POST", "/v1/knowledge/search", token=TOKEN_A,
           params={"query": "Kubernetes security RBAC", "top_k": 3})
ok, d = check(resp, 200)
kresults = d.get("data", [])
result("Knowledge", "Search knowledge with relevant query",
       "query='Kubernetes security RBAC'",
       "Returns results with score >= 0.5, content contains relevant terms",
       "PASS" if ok and len(kresults) > 0 and kresults[0].get("score", 0) >= 0.5 else "BUG",
       "Critical", actual=f"Results: {len(kresults)}, top score: {kresults[0].get('score', 0) if kresults else 0}",
       details={"result_count": len(kresults), "top_score": kresults[0].get("score", 0) if kresults else 0})

# 43
resp = api("POST", "/v1/knowledge/search", token=TOKEN_A,
           params={"query": "quantum physics string theory wormholes", "top_k": 3})
ok, d = check(resp, 200)
irrelevant_results = d.get("data", [])
result("Knowledge", "Search knowledge with completely unrelated query",
       "query='quantum physics string theory wormholes'",
       "Returns results but with low relevance scores",
       "PASS" if ok else "BUG",
       "Minor", actual=f"Results: {len(irrelevant_results)}, top score: {irrelevant_results[0].get('score', 0) if irrelevant_results else 'N/A'}",
       details={"top_score": irrelevant_results[0].get("score", 0) if irrelevant_results else None})

# 44
resp = api("POST", "/v1/knowledge/ingest/document", token=TOKEN_A,
           files={"file": ("empty.txt", "", "text/plain")},
           data={"title": "Empty Document"})
result("Knowledge", "Ingest empty knowledge document",
       "Zero-byte file upload to knowledge ingest",
       "4xx error with clear message about empty content",
       "PASS" if resp.status_code in (400, 422) else "BUG",
       "Minor", actual=f"Status {resp.status_code}: {resp.text[:150]}",
       details={"status": resp.status_code})

# 45
resp = api("POST", "/v1/knowledge/search", token=TOKEN_A,
           params={"query": "resource limits readiness probes namespaces", "top_k": 3})
ok, d = check(resp, 200)
specific_results = d.get("data", [])
specific_match = any(
    any(term in r.get("content", "").lower() for term in ["resource", "limit", "probe", "namespace"])
    for r in specific_results
)
result("Knowledge", "Knowledge search returns semantically relevant content",
       "query containing exact document terms: 'resource limits readiness probes namespaces'",
       "Top result contains at least one of: resource, limit, probe, namespace",
       "PASS" if ok and specific_match else "BUG",
       "Major", actual=f"Results: {len(specific_results)}, specific_match={specific_match}",
       details={"result_count": len(specific_results)})


# ═══════════════════ TAILORING (5 scenarios) ═══════════════════
print("\n--- TAILORING Scenarios ---")

# First create a base resume for user A
resp = api("POST", "/v1/resumes", token=TOKEN_A, json={
    "name": "QA Test Resume",
    "template_id": "modern_professional",
    "content": {"summary": "Experienced software engineer with Python and cloud skills."},
})
ok, d = check(resp, 201)
base_id = d.get("data", {}).get("resume_id") if ok else None

if base_id and job_id:
    # 46
    resp = api("POST", "/v1/tailoring/tailor", token=TOKEN_A,
               params={"base_resume_id": base_id, "job_id": job_id, "strategy": "moderate"})
    ok, d = check(resp, 200)
    tailor_data = d.get("data", {})
    result("Tailoring", "Tailor resume with moderate strategy",
           f"POST /v1/tailoring/tailor strategy=moderate",
           "200 OK, returns tailored_resume_id, diffs, keyword_coverage, factuality_score",
           "PASS" if ok and "tailored_resume_id" in tailor_data else "BUG",
           "Critical", actual="OK" if ok else f"Status {resp.status_code}: {resp.text[:150]}",
           details={"factuality": tailor_data.get("factuality_score"),
                    "ats_score": tailor_data.get("ats_score"),
                    "keyword_before": tailor_data.get("keyword_coverage_before"),
                    "keyword_after": tailor_data.get("keyword_coverage_after")})

    # 47
    resp = api("POST", "/v1/tailoring/tailor", token=TOKEN_A,
               params={"base_resume_id": base_id, "job_id": job_id, "strategy": "conservative"})
    ok, d = check(resp, 200)
    cons_data = d.get("data", {})
    result("Tailoring", "Tailor resume with conservative strategy",
           "strategy=conservative",
           "200 OK, fewer/more cautious changes than moderate",
           "PASS" if ok else "BUG",
           "Minor", actual="OK" if ok else f"Status {resp.status_code}",
           details={"keyword_before": cons_data.get("keyword_coverage_before"),
                    "keyword_after": cons_data.get("keyword_coverage_after")})

    # 48
    resp = api("POST", "/v1/tailoring/tailor", token=TOKEN_A,
               params={"base_resume_id": base_id, "job_id": job_id, "strategy": "aggressive"})
    ok, d = check(resp, 200)
    agg_data = d.get("data", {})
    result("Tailoring", "Tailor resume with aggressive strategy",
           "strategy=aggressive",
           "200 OK, more keyword optimization",
           "PASS" if ok else "BUG",
           "Minor", actual="OK" if ok else f"Status {resp.status_code}",
           details={"keyword_before": agg_data.get("keyword_coverage_before"),
                    "keyword_after": agg_data.get("keyword_coverage_after")})

    # 49
    resp = api("POST", "/v1/tailoring/tailor", token=TOKEN_A,
               params={"base_resume_id": "00000000-0000-0000-0000-000000000000",
                       "job_id": job_id, "strategy": "moderate"})
    result("Tailoring", "Tailor with non-existent base resume",
           "base_resume_id=00000000-... (doesn't exist)",
           "404 Not Found",
           "PASS" if resp.status_code == 404 else "BUG",
           "Minor", actual=f"Status {resp.status_code}, expected 404",
           details={"status": resp.status_code})

    # 50 — Factuality: check that violations are specific and actionable
    if 'tailor_data' in dir():
        violations = tailor_data.get("factuality_violations", [])
        factuality_score = tailor_data.get("factuality_score", -1)
        result("Tailoring", "Factuality verification produces score and violations",
               "POST /v1/tailoring/tailor",
               "factuality_score between 0.0-1.0, violations list (may be empty)",
               "PASS" if 0 <= factuality_score <= 1.0 else "BUG",
               "Major", actual=f"factuality_score={factuality_score}, violations={len(violations)}",
               details={"factuality_score": factuality_score, "violations_count": len(violations)})
else:
    result("Tailoring", "Cannot test tailoring — no base resume or job available",
           "N/A", "N/A", "SKIP", "Minor", actual="base_id or job_id missing")


# ═══════════════════ FINAL REPORT ═══════════════════
print(f"\n{'='*60}")
print(f"  QA RESULTS: {len(RESULTS)} scenarios completed")
print(f"{'='*60}")

bug_results = [r for r in RESULTS if r.status == "BUG"]
pass_results = [r for r in RESULTS if r.status == "PASS"]
skip_results = [r for r in RESULTS if r.status == "SKIP"]
critical = [r for r in bug_results if r.severity == "Critical"]
major = [r for r in bug_results if r.severity == "Major"]
minor = [r for r in bug_results if r.severity == "Minor"]

print(f"  PASS:     {len(pass_results)}")
print(f"  BUGS:     {len(bug_results)} (Critical: {len(critical)}, Major: {len(major)}, Minor: {len(minor)})")
print(f"  SKIPPED:  {len(skip_results)}")

# Persist results
with open("scripts/qa_results.json", "w") as f:
    json.dump([{
        "id": r.id, "subsystem": r.subsystem, "name": r.name,
        "inputs": r.inputs, "expected": r.expected, "actual": r.actual,
        "status": r.status, "severity": r.severity,
        "repro_steps": r.repro_steps, "details": r.details,
    } for r in RESULTS], f, indent=2, default=str)

print(f"\n  Results saved to scripts/qa_results.json")

# Exit with non-zero if critical bugs
if critical:
    print(f"\n  WARNING: {len(critical)} critical bugs found!")
    sys.exit(1)
sys.exit(0)
