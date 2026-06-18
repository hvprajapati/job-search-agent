"""Job domain services — normalization, deduplication, enrichment."""
from __future__ import annotations
import re
from pathfinder.jobs.domain.entities import JobPosting, Company
from pathfinder.jobs.domain.value_objects import (
    RawJobEntry, CanonicalJobId, RemotePolicy, JobSeniority, SalaryRange, JobLocation,
)
from pathfinder.jobs.domain.repositories import JobRepository, CompanyRepository


class JobNormalizer:
    TITLE_SYNONYMS = {
        "sde": "Software Engineer", "swe": "Software Engineer",
        "sr.": "Senior", "jr.": "Junior",
        "devops": "DevOps Engineer", "sre": "Site Reliability Engineer",
        "mle": "Machine Learning Engineer", "ml eng": "Machine Learning Engineer",
        "fe": "Frontend Engineer", "be": "Backend Engineer",
        "fs": "Full Stack Engineer",
    }

    @classmethod
    def normalize_title(cls, raw: str) -> str:
        title = raw.strip()
        for pat, repl in cls.TITLE_SYNONYMS.items():
            title = re.sub(rf"\b{re.escape(pat)}\b", repl, title, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", title).strip()

    @classmethod
    def infer_remote(cls, location: str, description: str) -> RemotePolicy:
        text = f"{location} {description}".lower()
        if "remote-first" in text or "fully remote" in text:
            return RemotePolicy.REMOTE
        if "remote" in text:
            return RemotePolicy.HYBRID
        if "hybrid" in text:
            return RemotePolicy.HYBRID
        return RemotePolicy.UNSPECIFIED

    @classmethod
    def infer_seniority(cls, title: str, description: str) -> JobSeniority:
        text = f"{title} {description}".lower()
        if any(w in text for w in ["principal", "distinguished"]):
            return JobSeniority.PRINCIPAL
        if any(w in text for w in ["staff engineer", "staff software"]):
            return JobSeniority.STAFF
        if any(w in text for w in ["senior", "sr.", "lead"]):
            return JobSeniority.SENIOR
        if any(w in text for w in ["junior", "jr.", "entry"]):
            return JobSeniority.JUNIOR
        if any(w in text for w in ["intern", "internship"]):
            return JobSeniority.INTERN
        return JobSeniority.MID

    @classmethod
    def normalize(cls, raw: RawJobEntry) -> JobPosting:
        canonical = CanonicalJobId.compute(title=raw.raw_title, company_name=raw.raw_company, location=raw.raw_location)
        title = cls.normalize_title(raw.raw_title)
        job = JobPosting.from_raw(raw, canonical)
        job.normalized_title = title
        job.remote_policy = cls.infer_remote(raw.raw_location, raw.raw_description)
        job.seniority = cls.infer_seniority(title, raw.raw_description)
        job.description_clean = re.sub(r"<[^>]+>", "", raw.raw_description)
        job.description_clean = re.sub(r"\s+", " ", job.description_clean).strip()
        job.description_summary = job.description_clean[:300] if job.description_clean else ""
        return job


class JobDedupService:
    def __init__(self, job_repo, company_repo) -> None:
        self._jobs = job_repo
        self._companies = company_repo

    async def deduplicate(self, job: JobPosting) -> tuple[JobPosting, bool]:
        existing = await self._jobs.get_by_canonical_id(job.canonical_job_id.value)
        if existing is None:
            if job.company_name:
                company = await self._companies.get_or_create(job.company_name)
                job.company_id = company.id
            await self._jobs.save(job)
            return job, True
        changed = existing.merge_from_source(RawJobEntry(
            source_name=list(job.source_ids.keys())[0] if job.source_ids else "unknown",
            source_type=job.source_type, raw_title=job.title, raw_company=job.company_name,
            raw_location=job.location.display_text, raw_description=job.description_raw,
            source_url=job.source_url, application_url=job.application_url,
            source_id=list(job.source_ids.values())[0] if job.source_ids else "",
        ))
        if changed:
            await self._jobs.save(existing)
        return existing, False


class JobEnrichmentService:
    TECH_KEYWORDS: dict[str, list[str]] = {
        "Python": ["python", "django", "flask", "fastapi"],
        "JavaScript": ["javascript", "js", "node", "react", "vue", "typescript"],
        "Java": ["java", "spring", "kotlin"],
        "Go": ["go", "golang"],
        "Rust": ["rust"],
        "AWS": ["aws", "amazon web services", "s3", "lambda"],
        "Docker": ["docker", "container"],
        "Kubernetes": ["kubernetes", "k8s"],
        "PostgreSQL": ["postgresql", "postgres"],
        "Redis": ["redis"],
        "React": ["react", "reactjs"],
        "TypeScript": ["typescript", "ts"],
    }

    @classmethod
    def extract_tech_stack(cls, text: str) -> list[str]:
        found = []
        text_lower = text.lower()
        for tech, keywords in cls.TECH_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                found.append(tech)
        return sorted(found)

    @classmethod
    def enrich(cls, job: JobPosting) -> JobPosting:
        job.tech_stack = cls.extract_tech_stack(f"{job.title} {job.description_raw}")
        return job
