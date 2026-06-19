#!/usr/bin/env python3
"""Skill extraction quality test — uploads 5 resumes and reports extracted skills."""
import json
import sys
import time
import os
import requests

BASE = os.environ.get("PATHFINDER_URL", "http://localhost:8000")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESUME_DIR = os.path.join(SCRIPT_DIR, "test_resumes")

# Expected skills for each resume (minimum set we should extract)
EXPECTED = {
    "ai_ml_engineer.txt": [
        "Python", "PyTorch", "TensorFlow", "CUDA", "Kubernetes", "Docker",
        "PostgreSQL", "MLOps", "Feature Engineering", "Model Deployment",
        "A/B Testing", "Distributed Training", "Generative AI", "LLMs",
        "RAG", "Embeddings", "Vector Search", "Ray", "Redis", "GCP",
    ],
    "data_engineer.txt": [
        "Python", "SQL", "Apache Spark", "Airflow", "Kafka", "AWS", "GCP",
        "Terraform", "dbt", "Snowflake", "Redshift", "ETL", "Data Modeling",
        "Data Warehousing", "Stream Processing", "BigQuery", "Flink", "Hadoop",
    ],
    "backend_engineer.txt": [
        "Go", "Rust", "Java", "Python", "PostgreSQL", "Redis", "Kafka",
        "MySQL", "Kubernetes", "Docker", "gRPC", "REST", "GraphQL",
        "CI/CD", "Microservices", "Distributed Systems", "Prometheus",
        "etcd", "Node.js",
    ],
    "fullstack_developer.txt": [
        "React", "TypeScript", "JavaScript", "Node.js", "Python", "Django",
        "GraphQL", "PostgreSQL", "HTML/CSS", "Tailwind CSS", "Docker",
        "AWS", "Git", "CI/CD", "Jest", "Cypress", "Redis", "WebSockets",
    ],
    "fresher.txt": [
        "Java", "Python", "JavaScript", "TypeScript", "React", "Spring Boot",
        "Node.js", "FastAPI", "PostgreSQL", "MongoDB", "Redis", "Docker",
        "Git", "Linux", "REST APIs", "Express", "AWS", "scikit-learn",
    ],
}

results = {}


def header(msg: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {msg}")
    print(f"{'='*70}")


def register_user() -> tuple[str, str]:
    """Register a new user, return (email, token)."""
    email = f"skill-test-{int(time.time())}@pathfinder.dev"
    resp = requests.post(
        f"{BASE}/v1/auth/register",
        json={"email": email, "password": "Test123!", "full_name": "Test User", "accept_terms": True},
        timeout=60,
    )
    if resp.status_code != 201:
        print(f"  FAIL: Register returned {resp.status_code}: {resp.text[:200]}")
        sys.exit(1)
    token = resp.json()["data"]["tokens"]["access_token"]
    return email, token


def upload_resume(token: str, filename: str) -> dict:
    """Upload a resume file and return the API response data."""
    filepath = os.path.join(RESUME_DIR, filename)
    with open(filepath, "r") as f:
        content = f.read()
    resp = requests.post(
        f"{BASE}/v1/profile/import/resume",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (filename, content, "text/plain")},
        data={"merge_strategy": "replace"},
        timeout=120,
    )
    if resp.status_code not in (200, 201):
        print(f"  FAIL: Upload returned {resp.status_code}: {resp.text[:300]}")
        return {}
    return resp.json()["data"]


def get_profile(token: str) -> dict:
    """Get the current user's profile."""
    resp = requests.get(
        f"{BASE}/v1/profile",
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    if resp.status_code != 200:
        print(f"  FAIL: Profile GET returned {resp.status_code}")
        return {}
    return resp.json()["data"]


def compute_accuracy(extracted: set[str], expected: list[str]) -> dict:
    """Compute precision, recall, F1 for extracted vs expected skills."""
    expected_set = {e.lower() for e in expected}
    extracted_set = {e.lower() for e in extracted}

    true_pos = len(extracted_set & expected_set)
    false_pos = len(extracted_set - expected_set)
    false_neg = len(expected_set - extracted_set)

    precision = true_pos / max(true_pos + false_pos, 1)
    recall = true_pos / max(true_pos + false_neg, 1)
    f1 = 2 * precision * recall / max(precision + recall, 0.001)

    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "matched": sorted(extracted_set & expected_set),
        "missing": sorted(expected_set - extracted_set),
        "extra": sorted(extracted_set - expected_set),
    }


# -- Run tests --
header("Skill Extraction Quality Test")

# Test each resume with a fresh user to avoid merge complexity
for filename in sorted(EXPECTED.keys()):
    resume_name = filename.replace(".txt", "")
    print(f"\n-- {resume_name} --")

    try:
        email, token = register_user()
        data = upload_resume(token, filename)

        skills_count = data.get("skills_extracted", 0)
        experiences_count = data.get("experiences_extracted", 0)
        education_count = data.get("education_extracted", 0)

        profile = get_profile(token)
        skills = profile.get("skills", [])
        skill_names = [s["name"] for s in skills]

        accuracy = compute_accuracy(set(skill_names), EXPECTED[filename])

        print(f"  Skills extracted: {skills_count}")
        print(f"  Experiences extracted: {experiences_count}")
        print(f"  Education extracted: {education_count}")
        print(f"  Skill names: {skill_names}")
        print(f"  Precision: {accuracy['precision']:.0%} | Recall: {accuracy['recall']:.0%} | F1: {accuracy['f1']:.0%}")
        if accuracy["missing"]:
            print(f"  Missing: {accuracy['missing']}")
        if accuracy["extra"]:
            print(f"  Extra: {accuracy['extra']}")

        results[resume_name] = {
            "skills_count": skills_count,
            "experiences_count": experiences_count,
            "education_count": education_count,
            "skill_names": skill_names,
            "accuracy": accuracy,
            "status": "PASS" if accuracy["recall"] >= 0.5 else "LOW_RECALL",
        }
    except Exception as e:
        print(f"  ERROR: {e}")
        results[resume_name] = {"status": "ERROR", "error": str(e)}


# -- Final Report --
header("RESULTS SUMMARY")
total = len(results)
passed = sum(1 for r in results.values() if r["status"] == "PASS")
avg_f1 = sum(
    r.get("accuracy", {}).get("f1", 0) for r in results.values()
) / max(total, 1)

print(f"\n{'Resume':<25} {'Skills':>7} {'Exp':>5} {'Edu':>5} {'Prec':>6} {'Recall':>6} {'F1':>6} {'Status'}")
print("-" * 75)
for name, r in results.items():
    if r["status"] == "ERROR":
        print(f"{name:<25} {'ERROR':>7} {'-':>5} {'-':>5} {'-':>6} {'-':>6} {'-':>6} {'ERROR'}")
    else:
        a = r.get("accuracy", {})
        print(f"{name:<25} {r['skills_count']:>7} {r['experiences_count']:>5} {r['education_count']:>5} "
              f"{a.get('precision', 0):>6.0%} {a.get('recall', 0):>6.0%} {a.get('f1', 0):>6.0%} {r['status']}")

print(f"\n  OVERALL: {passed}/{total} PASS  |  Avg F1: {avg_f1:.0%}  |  Target F1: >80%")
print(f"  {'PASS' if avg_f1 >= 0.8 else 'NEEDS IMPROVEMENT'}")
