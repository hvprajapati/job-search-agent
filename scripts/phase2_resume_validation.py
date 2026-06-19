#!/usr/bin/env python3
"""Phase 2: Resume Import Validation — 8 diverse resume scenarios."""
import json, os, sys, time, io
import requests

BASE = os.environ.get("PATHFINDER_URL", "http://localhost:8000")
RESUME_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_resumes")
RESULTS = []

def header(msg): print(f"\n{'='*60}\n  {msg}\n{'='*60}")

header("Phase 2: Resume Import Validation")

# Setup
ts = int(time.time())
for attempt in range(5):
    r = requests.post(f"{BASE}/v1/auth/register",
        json={"email": f"resume-val-{ts}@test.com", "password": "Test123!", "full_name": "Resume QA", "accept_terms": True}, timeout=30)
    if r.status_code == 201:
        token = r.json()["data"]["tokens"]["access_token"]
        break
    elif r.status_code == 429:
        time.sleep(10*(attempt+1))
else:
    print("FAILED to register"); sys.exit(1)

def test_resume(name, content, content_type="text/plain"):
    """Upload resume and return extraction data."""
    r = requests.post(f"{BASE}/v1/profile/import/resume",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (name, content, content_type)},
        data={"merge_strategy": "replace"}, timeout=120)
    try:
        data = r.json().get("data", {})
    except:
        data = {}
    return {
        "name": name, "status": r.status_code,
        "skills": data.get("skills_extracted", 0),
        "experiences": data.get("experiences_extracted", 0),
        "education": data.get("education_extracted", 0),
        "parsed_fields": data.get("parsed_fields", []),
        "error": r.text[:200] if r.status_code >= 400 else "",
    }

# ── Test 1: AI/ML Engineer ──
with open(os.path.join(RESUME_DIR, "ai_ml_engineer.txt")) as f:
    r1 = test_resume("ai_ml_engineer.txt", f.read())
print(f"  1. AI/ML Engineer: status={r1['status']}, skills={r1['skills']}, exp={r1['experiences']}, edu={r1['education']}")
RESULTS.append({**r1, "expected_skills_min": 12, "expected_experiences_min": 1, "expected_education_min": 1})

# ── Test 2: Data Engineer ──
with open(os.path.join(RESUME_DIR, "data_engineer.txt")) as f:
    r2 = test_resume("data_engineer.txt", f.read())
print(f"  2. Data Engineer: status={r2['status']}, skills={r2['skills']}, exp={r2['experiences']}, edu={r2['education']}")
RESULTS.append({**r2, "expected_skills_min": 10, "expected_experiences_min": 1, "expected_education_min": 1})

# ── Test 3: Backend Engineer ──
with open(os.path.join(RESUME_DIR, "backend_engineer.txt")) as f:
    r3 = test_resume("backend_engineer.txt", f.read())
print(f"  3. Backend Engineer: status={r3['status']}, skills={r3['skills']}, exp={r3['experiences']}, edu={r3['education']}")
RESULTS.append({**r3, "expected_skills_min": 10, "expected_experiences_min": 1, "expected_education_min": 1})

# ── Test 4: Fresher ──
with open(os.path.join(RESUME_DIR, "fresher.txt")) as f:
    r4 = test_resume("fresher.txt", f.read())
print(f"  4. Fresher: status={r4['status']}, skills={r4['skills']}, exp={r4['experiences']}, edu={r4['education']}")
RESULTS.append({**r4, "expected_skills_min": 10, "expected_experiences_min": 0, "expected_education_min": 1})

# ── Test 5: Empty file ──
r5 = test_resume("empty.txt", "")
print(f"  5. Empty file: status={r5['status']} (expected 4xx)")
RESULTS.append({**r5, "expected_status": "4xx"})

# ── Test 6: Corrupted/binary as PDF ──
r6 = test_resume("corrupt.pdf", b"%PDF-1.4\n%INVALID\x00\xFF\xFE\n%%EOF", "application/pdf")
print(f"  6. Corrupt PDF: status={r6['status']} (expected 4xx)")
RESULTS.append({**r6, "expected_status": "4xx"})

# ── Test 7: PNG renamed as PDF ──
png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
r7 = test_resume("fake.pdf", png_bytes, "application/pdf")
print(f"  7. PNG as PDF: status={r7['status']} (expected 4xx)")
RESULTS.append({**r7, "expected_status": "4xx"})

# ── Test 8: Large resume (~100KB text) ──
large = "Large Resume Test\n\n" + "SKILLS\n" + ", ".join([f"Skill{i}" for i in range(500)]) + "\n\n" + "WORK EXPERIENCE\n" + "\n".join([f"Company{i} - Role{i} (2020-2023)\n  - Achievement {i}" for i in range(100)]) + "\n\nEDUCATION\nUniversity - BS CS (2020)"
r8 = test_resume("large.txt", large)
print(f"  8. Large resume: status={r8['status']}, skills={r8['skills']}, len={len(large)} chars")
RESULTS.append({**r8, "expected_skills_min": 10, "resume_size_chars": len(large)})

# ── Summary ──
print(f"\n--- Resume Validation Summary ---")
passed = 0
for i, r in enumerate(RESULTS):
    label = f"  Test {i+1}: {r['name']:<30s}"
    if r.get("expected_status") == "4xx":
        ok = 400 <= r["status"] < 500
        print(f"{label} status={r['status']} (4xx expected) -> {'PASS' if ok else 'FAIL'}")
    else:
        skills_ok = r["skills"] >= r.get("expected_skills_min", 1)
        exp_ok = r["experiences"] >= r.get("expected_experiences_min", 0)
        edu_ok = r["education"] >= r.get("expected_education_min", 0)
        ok = r["status"] == 200 and skills_ok and exp_ok and edu_ok
        print(f"{label} skills={r['skills']} exp={r['experiences']} edu={r['education']} -> {'PASS' if ok else 'FAIL'}")
        if not skills_ok:
            print(f"         Skills below minimum ({r['skills']} < {r.get('expected_skills_min', 0)})")
    if ok:
        passed += 1

print(f"\n  {passed}/{len(RESULTS)} tests passed")

with open("scripts/phase2_resume_results.json", "w") as f:
    json.dump({"passed": passed, "total": len(RESULTS), "tests": RESULTS}, f, indent=2, default=str)
