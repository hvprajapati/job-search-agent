#!/usr/bin/env python3
"""Phase 3: Knowledge RAG Validation — 20 documents, relevance measurement."""
import json, os, sys, time, statistics
import requests

BASE = os.environ.get("PATHFINDER_URL", "http://localhost:8000")
DOCS = [
    ("Python Best Practices", "Use type hints, write docstrings, follow PEP 8, use virtual environments. Leverage list comprehensions and generators for performance."),
    ("Docker Container Guide", "Use multi-stage builds, minimize layers, run as non-root, use health checks. Tag images with version and latest. Use .dockerignore files."),
    ("Kubernetes Deployment", "Use deployments not pods, set resource limits, configure liveness probes, use ConfigMaps, implement HPA for autoscaling."),
    ("AWS Architecture", "Use VPC with public/private subnets, implement IAM least privilege, use S3 for static assets, CloudFront for CDN, RDS for databases."),
    ("Machine Learning Pipeline", "Data collection, cleaning, feature engineering, model training, hyperparameter tuning, evaluation, deployment, monitoring."),
    ("React Performance", "Use React.memo, useCallback, useMemo for expensive computations. Implement code splitting with lazy loading. Virtualize long lists."),
    ("PostgreSQL Optimization", "Use EXPLAIN ANALYZE, create proper indexes, vacuum regularly, configure shared_buffers, use connection pooling with PgBouncer."),
    ("CI/CD Pipeline Design", "Run tests in parallel, cache dependencies, use matrix builds, deploy to staging first, implement canary deployments, automated rollbacks."),
    ("API Design Principles", "Use RESTful conventions, version APIs in URL, implement pagination, use proper HTTP status codes, document with OpenAPI, rate limit."),
    ("Security Best Practices", "Hash passwords with Argon2, use HTTPS everywhere, implement CSP headers, validate all inputs, use prepared statements, rotate secrets."),
    ("Data Engineering Fundamentals", "ETL vs ELT, data lake vs warehouse, schema-on-read vs schema-on-write. Use Apache Spark for big data, dbt for transformations."),
    ("TypeScript Type System", "Use interfaces for object shapes, union types for variants, generics for reusable code, strict null checks, discriminated unions for state."),
    ("Redis Caching Strategies", "Cache-aside pattern, write-through, write-behind. Use TTL for expiration, Redis Streams for event sourcing, Redisearch for full-text."),
    ("Git Workflow", "Feature branches, pull requests, squash merge, semantic versioning, conventional commits. Use git rebase for clean history, git bisect for debugging."),
    ("Monitoring and Observability", "Three pillars: logs, metrics, traces. Use structured logging, Prometheus for metrics, Grafana for dashboards, OpenTelemetry for tracing."),
    ("System Design Scalability", "Horizontal vs vertical scaling, load balancing, database sharding, message queues, CDN caching, eventual consistency, circuit breakers."),
    ("Node.js Backend", "Use async/await, handle uncaught exceptions, implement graceful shutdown, use cluster mode, stream large responses, validate with Joi/Zod."),
    ("Project Management Agile", "Scrum ceremonies, sprint planning, daily standups, retrospectives. Write user stories with acceptance criteria. Use story points estimation."),
    ("Linux Administration", "Use systemd for services, cron for scheduling, iptables/nftables for firewall, logrotate for logs, SSH key authentication, fail2ban for security."),
    ("Testing Pyramid", "Unit tests at bottom, integration tests in middle, E2E tests at top. Use mocks sparingly, prefer test doubles, aim for 80% coverage on critical paths."),
]

QUERIES = [
    ("Python coding standards", ["type hints", "docstrings", "PEP 8"]),
    ("container security non-root", ["multi-stage builds", "non-root", "health checks"]),
    ("Kubernetes resource limits autoscaling", ["deployments", "resource limits", "liveness probes"]),
    ("AWS VPC IAM S3", ["VPC", "IAM", "S3"]),
    ("ML model training evaluation deployment", ["feature engineering", "model training", "hyperparameter"]),
    ("React performance memo lazy loading", ["React.memo", "useCallback", "code splitting"]),
    ("PostgreSQL indexes vacuum performance", ["EXPLAIN ANALYZE", "indexes", "vacuum"]),
    ("CI/CD canary deployments rollback", ["tests in parallel", "canary deployments", "rollback"]),
    ("REST API versioning pagination OpenAPI", ["RESTful", "version APIs", "OpenAPI"]),
    ("password hashing CSP input validation", ["Argon2", "CSP headers", "validate"]),
]


def header(msg): print(f"\n{'='*60}\n  {msg}\n{'='*60}")

header("Phase 3: Knowledge RAG Validation")

# Setup
ts = int(time.time())
for attempt in range(5):
    r = requests.post(f"{BASE}/v1/auth/register",
        json={"email": f"rag-val-{ts}@test.com", "password": "Test123!", "full_name": "RAG QA", "accept_terms": True}, timeout=30)
    if r.status_code == 201:
        token = r.json()["data"]["tokens"]["access_token"]
        break
    elif r.status_code == 429:
        time.sleep(10*(attempt+1))
else:
    print("FAILED to register"); sys.exit(1)

print(f"Registered user for RAG tests")

# ── Ingest 20 documents ──
ingestion_times = []
total_chunks = 0
print(f"\nIngesting {len(DOCS)} documents...")
for title, content in DOCS:
    start = time.monotonic()
    r = requests.post(f"{BASE}/v1/knowledge/ingest/document",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (f"{title}.txt", content, "text/plain")},
        data={"title": title}, timeout=60)
    elapsed = (time.monotonic() - start) * 1000
    ingestion_times.append(elapsed)
    chunks = r.json().get("data", {}).get("chunks_created", 0) if r.status_code == 200 else 0
    total_chunks += chunks
    status = "OK" if r.status_code == 200 else f"FAIL({r.status_code})"
    print(f"  {status}: {title} ({chunks} chunks, {elapsed:.0f}ms)")

print(f"  Total: {total_chunks} chunks from {len(DOCS)} docs, avg ingest: {statistics.mean(ingestion_times):.0f}ms")

# ── Search evaluation ──
print(f"\nEvaluating search relevance with {len(QUERIES)} queries...")
search_times = []
top1_hits = 0
top3_hits = 0

for query, expected_keywords in QUERIES:
    start = time.monotonic()
    r = requests.post(f"{BASE}/v1/knowledge/search",
        headers={"Authorization": f"Bearer {token}"},
        params={"query": query, "top_k": 5}, timeout=60)
    elapsed = (time.monotonic() - start) * 1000
    search_times.append(elapsed)

    results = r.json().get("data", []) if r.status_code == 200 else []
    top_score = results[0]["score"] if results else 0
    top1_content = results[0]["content"][:80] if results else ""

    # Check if top-1 or top-3 contain expected keywords
    top1_content = (results[0].get("content", "") if results else "").lower()
    top1_match = any(kw.lower() in top1_content for kw in expected_keywords)
    top3_match = any(
        any(kw.lower() in r.get("content", "").lower() for kw in expected_keywords)
        for r in results[:3]
    )

    if top1_match: top1_hits += 1
    if top3_match: top3_hits += 1

    icon = "OK" if top1_match else ("TOP3" if top3_match else "MISS")
    print(f"  {icon}: '{query[:55]}...' -> score={top_score:.2f} | {top1_content}...")

print(f"\n  Top-1 relevance: {top1_hits}/{len(QUERIES)} ({top1_hits/len(QUERIES)*100:.0f}%)")
print(f"  Top-3 relevance: {top3_hits}/{len(QUERIES)} ({top3_hits/len(QUERIES)*100:.0f}%)")
print(f"  Avg search latency: {statistics.mean(search_times):.0f}ms")
print(f"  P95 search latency: {sorted(search_times)[int(len(search_times)*0.95)]:.0f}ms")

# Save results
results_data = {
    "documents_ingested": len(DOCS),
    "total_chunks": total_chunks,
    "avg_ingestion_ms": statistics.mean(ingestion_times),
    "top1_relevance": top1_hits / len(QUERIES),
    "top3_relevance": top3_hits / len(QUERIES),
    "avg_search_latency_ms": statistics.mean(search_times),
    "queries": len(QUERIES),
}
with open("scripts/phase3_rag_results.json", "w") as f:
    json.dump(results_data, f, indent=2)

print(f"\n  Results saved to scripts/phase3_rag_results.json")
print(f"  {'PASS' if top3_hits/len(QUERIES) >= 0.7 else 'NEEDS IMPROVEMENT'}")
