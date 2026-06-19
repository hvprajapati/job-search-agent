#!/usr/bin/env python3
"""Seed Pathfinder database with realistic demo data using raw SQL for speed and reliability."""
import asyncio, json, os, sys, random, uuid
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

SKILLS_POOL = [
    "Python", "JavaScript", "TypeScript", "Java", "Go", "Rust", "C++", "Ruby", "Scala", "Kotlin",
    "React", "Angular", "Vue.js", "Node.js", "Django", "Flask", "FastAPI", "Spring Boot",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Cassandra", "DynamoDB",
    "AWS", "GCP", "Azure", "Terraform", "Docker", "Kubernetes", "Helm", "Ansible",
    "Apache Spark", "Apache Kafka", "Airflow", "dbt", "Snowflake", "BigQuery", "Redshift",
    "PyTorch", "TensorFlow", "scikit-learn", "Pandas", "NumPy", "MLflow", "Kubeflow",
    "CI/CD", "GitHub Actions", "Jenkins", "GitLab CI", "CircleCI",
    "GraphQL", "REST", "gRPC", "WebSockets", "OAuth", "JWT",
    "Linux", "Bash", "Nginx", "Prometheus", "Grafana", "ELK Stack",
]

JOB_TITLES = [
    "Senior Software Engineer", "ML Engineer", "Data Engineer", "DevOps Engineer",
    "Full Stack Developer", "Frontend Engineer", "Backend Engineer", "Product Manager",
    "Engineering Manager", "Data Scientist", "Platform Engineer", "Security Engineer",
    "QA Engineer", "Site Reliability Engineer", "Technical Lead", "Solutions Architect",
    "Cloud Engineer", "iOS Developer", "Android Developer", "Research Scientist",
]
COMPANIES = [
    "Google", "Meta", "Amazon", "Apple", "Microsoft", "Netflix", "Stripe", "Airbnb",
    "Uber", "Spotify", "Slack", "Notion", "Figma", "Vercel", "Supabase", "Datadog",
    "Snowflake", "Databricks", "Anthropic", "OpenAI", "Scale AI", "Hugging Face",
    "Palantir", "Plaid", "Brex", "Ramp", "Coinbase", "Robinhood", "Instacart", "Doordash",
]
LOCATIONS = [
    "San Francisco, CA", "New York, NY", "Seattle, WA", "Austin, TX",
    "Remote (US)", "Remote (Global)", "London, UK", "Berlin, DE",
    "Toronto, CA", "Bangalore, IN", "Singapore", "Sydney, AU",
]
FIRST_NAMES = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Quinn", "Avery",
               "Sam", "Jamie", "Drew", "Blake", "Cameron", "Dakota", "Reese", "Skyler"]
LAST_NAMES = ["Chen", "Patel", "Kim", "Johnson", "Williams", "Garcia", "Martinez", "Lee",
              "Singh", "Silva", "Tanaka", "Mueller", "Andersen", "Okafor", "Santos", "Kapoor"]

TENANT_ID = "00000000-0000-0000-0000-000000000001"
NOW = datetime.utcnow().isoformat()


def rand_skills(n=8):
    return random.sample(SKILLS_POOL, min(n, len(SKILLS_POOL)))


async def seed():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text, DateTime, String, Integer, Text as SAText, ARRAY
    from sqlalchemy.sql import bindparam
    from sqlalchemy.dialects.postgresql import UUID as PGUUID
    from pathfinder.shared.config import get_settings
    from pathfinder.identity.infrastructure.auth.password_hasher import hash_password

    settings = get_settings()
    db_url = settings.database_url
    engine = create_async_engine(db_url, echo=False)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        # ── Phase 1: Users (50) ──
        print("Creating 50 users...")
        user_ids = []
        for i in range(50):
            fn = random.choice(FIRST_NAMES)
            ln = random.choice(LAST_NAMES)
            uid = uuid.uuid4()
            user_ids.append(uid)
            await session.execute(text("""
                INSERT INTO users (id, tenant_id, email, full_name, hashed_password, tier, status, role, email_verified, created_at, updated_at)
                VALUES (:id, :tenant_id, :email, :full_name, :hashed_password, 'free', 'active', 'user', true, NOW(), NOW())
            """), {"id": uid, "tenant_id": TENANT_ID, "email": f"{fn.lower()}.{ln.lower()}{i}@demo.dev",
                   "full_name": f"{fn} {ln}", "hashed_password": hash_password("DemoUser123!")})
        await session.flush()
        print(f"  Created {len(user_ids)} users")

        # ── Phase 2: Profiles (50) ──
        print("Creating profiles...")
        for uid in user_ids:
            skills_data = [{"name": s, "proficiency": random.choice(["beginner", "intermediate", "advanced", "expert"]), "years": random.randint(1, 10)}
                           for s in rand_skills(random.randint(5, 12))]
            structured = {
                "full_name": f"Demo User {uid.hex[:4]}",
                "headline": random.choice(["Software Engineer", "Data Scientist", "ML Engineer", "DevOps Engineer"]),
                "email": f"user-{uid.hex[:6]}@demo.dev",
                "skills": skills_data,
                "work_experiences": [{
                    "experience_id": uuid.uuid4().hex[:8],
                    "company": random.choice(COMPANIES),
                    "title": random.choice(JOB_TITLES),
                    "start_date": f"{random.randint(2016, 2023)}-{random.randint(1,12):02d}-01",
                    "description": f"Built {random.choice(['production systems', 'data pipelines', 'ML models'])}.",
                    "achievements": [f"Reduced {random.choice(['latency', 'costs'])} by {random.randint(20,70)}%"],
                    "tech_stack": rand_skills(random.randint(3, 6)),
                }],
                "education": [{
                    "education_id": uuid.uuid4().hex[:8],
                    "institution": random.choice(["MIT", "Stanford", "Berkeley", "CMU", "Georgia Tech", "Waterloo", "IIT"]),
                    "degree": random.choice(["BS", "MS", "PhD"]),
                    "field": "Computer Science",
                    "graduation_year": random.randint(2014, 2024),
                }],
            }
            await session.execute(text("""
                INSERT INTO profiles (id, tenant_id, user_id, version, is_active, structured_data, full_name_snapshot, headline_snapshot, skill_names_snapshot, parsing_confidence, enrichment_data, source, created_at, updated_at)
                VALUES (:id, :tenant_id, :user_id, 1, true, :structured_data, :full_name_snapshot, :headline_snapshot, :skill_names_snapshot, '{}', '{}', '{\"seed\"}', NOW(), NOW())
            """), {"id": uuid.uuid4(), "tenant_id": TENANT_ID, "user_id": uid,
                   "structured_data": json.dumps(structured),
                   "full_name_snapshot": structured["full_name"],
                   "headline_snapshot": structured["headline"],
                   "skill_names_snapshot": [s["name"] for s in skills_data]})
        await session.flush()
        print(f"  Created 50 profiles")

        # ── Phase 3: Resumes (200) ──
        print("Creating 200 resumes...")
        for uid in user_ids:
            for r in range(random.randint(2, 5)):
                await session.execute(text("""
                    INSERT INTO resumes (id, tenant_id, user_id, name, template_id, content, file_format, is_base, versions, created_at, updated_at)
                    VALUES (:id, :tenant_id, :user_id, :name, :template_id, :content, :file_format, :is_base, '[]', NOW(), NOW())
                """), {"id": uuid.uuid4(), "tenant_id": TENANT_ID, "user_id": uid,
                       "name": f"Resume {r+1} — {random.choice(['General', 'Tech', 'ML', 'Leadership'])}",
                       "template_id": random.choice(["modern_professional", "minimal", "executive"]),
                       "content": json.dumps({"summary": f"Experienced professional with skills in {', '.join(rand_skills(4))}."}),
                       "file_format": random.choice(["pdf", "docx"]),
                       "is_base": r == 0})
        await session.flush()
        print(f"  Created 200 resumes")

        # ── Phase 4: Jobs (500) ──
        print("Creating 500 jobs...")
        company_counters = {}
        for i in range(500):
            company = random.choice(COMPANIES)
            company_counters[company] = company_counters.get(company, 0) + 1
            title = random.choice(JOB_TITLES)
            location = random.choice(LOCATIONS)
            skills = rand_skills(random.randint(4, 10))
            salary_min = random.randint(120, 200) * 1000
            salary_max = random.randint(salary_min // 1000 + 30, 400) * 1000
            remote_policy = "remote" if "Remote" in location else random.choice(["onsite", "hybrid", "remote"])
            seniority = random.choice(["junior", "mid", "senior", "staff", "principal"])
            posted_days = random.randint(1, 30)
            first_seen = datetime.utcnow() - timedelta(days=posted_days)

            descriptions = [
                f"Join {company} as a {title} and help define the future. We need deep expertise in {skills[0]} and {skills[1]}. Work on {random.choice(['greenfield', 'high-scale', 'mission-critical'])} projects. ${salary_min//1000}k-${salary_max//1000}k + equity.",
                f"{company} is hiring a {title}! Build systems at scale serving millions. Requires {', '.join(skills[:3])}. {'Remote-friendly. ' if 'Remote' in location else ''}${salary_min//1000}k-${salary_max//1000}k.",
                f"We're looking for a {title} at {company}. Expertise in {', '.join(skills[:4])} required. Competitive comp: ${salary_min//1000}k-${salary_max//1000}k. Benefits + equity.",
            ]
            desc = random.choice(descriptions)

            await session.execute(text("""
                INSERT INTO job_postings (id, canonical_job_id, title, location, remote_policy,
                  description_raw, description_clean, source_url, source_type, is_active,
                  tech_stack, salary_min, salary_max, salary_currency, seniority,
                  source_ids, source_urls, created_at, updated_at, first_seen_at, last_seen_at, expires_at)
                VALUES (:id, :cjid, :title, CAST(:location AS JSONB), :remote_policy,
                  :desc, :desc, :url, 'seed_script', true,
                  :tech_stack, :salary_min, :salary_max, 'USD', :seniority,
                  '{}', '{}', NOW() - (:days * INTERVAL '1 day'), NOW() - (:days * INTERVAL '1 day'),
                  NOW() - (:days * INTERVAL '1 day') + INTERVAL '60 days',
                  NOW(), NOW())
            """).bindparams(
                bindparam("tech_stack", type_=ARRAY(SAText)),
            ), {
                "id": uuid.uuid4(), "cjid": f"seed-job-{i:05d}", "title": title,
                "location": json.dumps({"city": location.split(",")[0].strip(), "state": "", "country": "US", "display_text": location}),
                "remote_policy": remote_policy, "desc": desc,
                "url": f"https://careers.{company.lower().replace(' ', '')}.com/jobs/{company_counters[company]}",
                "tech_stack": skills,
                "salary_min": salary_min, "salary_max": salary_max, "seniority": seniority,
                "days": posted_days,
            })
        await session.flush()
        print(f"  Created 500 jobs across {len(company_counters)} companies")

        # ── Phase 5: Applications (100) ──
        print("Creating 100 applications...")
        result = await session.execute(text("SELECT id FROM job_postings WHERE is_active = true LIMIT 100"))
        job_ids = [row[0] for row in result.fetchall()]
        for i in range(min(100, len(user_ids))):
            uid = random.choice(user_ids)
            jid = random.choice(job_ids)
            status = random.choice(["saved", "applied", "applied", "applied", "phone_screen", "technical_interview"])
            applied = (datetime.utcnow() - timedelta(days=random.randint(0, 14))) if status != "saved" else None
            await session.execute(text("""
                INSERT INTO applications (id, tenant_id, user_id, job_id, status, status_history, notes, applied_at, last_updated_at, is_archived, created_at)
                VALUES (:id, :tenant_id, :user_id, :job_id, :status, :status_history, :notes, :applied_at, NOW(), false, NOW())
            """), {
                "id": uuid.uuid4(), "tenant_id": TENANT_ID, "user_id": uid, "job_id": jid,
                "status": status,
                "status_history": json.dumps([{"from": "saved", "to": status, "at": datetime.utcnow().isoformat()}]),
                "notes": random.choice(["", "Referred by friend", "Messaged recruiter", "Applied via LinkedIn"]),
                "applied_at": applied,
            })
        await session.flush()
        print(f"  Created 100 applications")

        # ── Phase 6: Knowledge Documents (50) ──
        print("Creating 50 knowledge documents...")
        topics = [
            ("Python Async Best Practices", "Use asyncio for I/O-bound tasks. Avoid blocking the event loop."),
            ("React Performance Guide", "Use React.memo, useCallback, and useMemo for expensive computations."),
            ("Kubernetes Production Checklist", "Set resource limits, implement liveness probes, use RBAC."),
            ("PostgreSQL Query Optimization", "Use EXPLAIN ANALYZE, create proper indexes, VACUUM regularly."),
            ("AWS Well-Architected", "Design for reliability, implement IAM least privilege, monitor with CloudWatch."),
            ("Docker Best Practices", "Multi-stage builds, minimize layers, run as non-root, scan for vulnerabilities."),
            ("CI/CD Pipeline Design", "Fast linting first, cache dependencies, deploy to staging before production."),
            ("Microservices Architecture", "Circuit breakers, async communication, distributed tracing, API gateway."),
            ("ML Operations Guide", "Version datasets, experiment tracking, automated retraining, drift monitoring."),
            ("System Design Interview", "Clarify requirements, estimate scale, design architecture, find bottlenecks."),
        ]
        from pathfinder.shared.infrastructure.embedding_service import generate_embedding
        for i in range(50):
            topic_idx = i % len(topics)
            title, content = topics[topic_idx]
            if i >= len(topics):
                title = f"{title} (Edition {i // len(topics) + 1})"
            doc_id = uuid.uuid4()
            await session.execute(text("""
                INSERT INTO knowledge_documents (id, user_id, title, content_raw, content_clean, source_type, source_id, chunk_count, is_indexed, last_indexed_at, created_at, updated_at)
                VALUES (:id, :uid, :title, :content, :content, 'manual', :source_id, 1, true, NOW(), NOW(), NOW())
            """), {"id": doc_id, "uid": random.choice(user_ids), "title": title, "content": content, "source_id": f"seed-{i}"})
            try:
                vec = await asyncio.get_event_loop().run_in_executor(None, generate_embedding, content[:8000])
                if vec:
                    await session.execute(text("""
                        INSERT INTO knowledge_chunks (id, document_id, user_id, chunk_index, content, metadata, embedding, created_at, updated_at)
                        VALUES (:id, :doc_id, :uid, 0, :content, :metadata, :embedding, NOW(), NOW())
                    """), {"id": uuid.uuid4(), "doc_id": doc_id, "uid": random.choice(user_ids), "content": content, "metadata": json.dumps({"topic": title, "source": "seed"}), "embedding": vec})
            except Exception:
                pass  # Embedding generation is best-effort
        await session.flush()
        print(f"  Created 50 knowledge documents")

        await session.commit()
        print(f"\n{'='*50}")
        print(f"  SEED COMPLETE — 50 users, 50 profiles, 200 resumes, 500 jobs, 100 applications, 50 knowledge docs")
        print(f"{'='*50}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
