"""Resume Tailoring API routes."""
from __future__ import annotations
import json
import time
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.shared.infrastructure.database import get_session
from pathfinder.identity.presentation.dependencies import get_current_user
from pathfinder.identity.domain.entities import User
from pathfinder.profile.domain.tailoring.value_objects import TailoringRequest, TailoringStrategy
from pathfinder.profile.domain.tailoring.exceptions import (
    BaseResumeNotFoundError, TailoredResumeNotFoundError,
)
from pathfinder.profile.infrastructure.persistence.profile_repository import SqlProfileRepository
from pathfinder.profile.infrastructure.persistence.resume_repository import SqlResumeRepository
from pathfinder.profile.infrastructure.persistence.tailored_resume_repository import SqlTailoredResumeRepository
from pathfinder.profile.infrastructure.tailoring.tailoring_engine import TailoringEngine
from pathfinder.profile.infrastructure.tailoring.keyword_extractor import KeywordExtractor
from pathfinder.jobs.infrastructure.persistence.job_repository import SqlJobRepository

router = APIRouter(prefix="/v1/tailoring", tags=["Resume Tailoring"])


@router.post("/analyze")
async def analyze_resume(
    base_resume_id: UUID = Query(..., description="Base resume UUID"),
    job_id: UUID = Query(..., description="Target job UUID"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Analyze a resume against a job description. Returns keyword gaps."""
    resume_repo = SqlResumeRepository(session)
    job_repo = SqlJobRepository(session)

    resume = await resume_repo.get_by_user_and_id(current_user.id, base_resume_id)
    if not resume:
        raise BaseResumeNotFoundError(str(base_resume_id))

    job = await job_repo.get_by_id(job_id)
    if not job:
        from pathfinder.jobs.domain.exceptions import JobNotFoundError
        raise JobNotFoundError(str(job_id))

    extractor = KeywordExtractor()
    required = [s.get("name", s) for s in (job.required_skills or [])]
    nice = [s.get("name", s) for s in (job.nice_to_have_skills or [])]
    keywords = extractor.extract(
        job.description_clean or job.description_raw or "",
        required_skills=required,
        nice_to_have=nice,
    )
    resume_text = json.dumps(resume.content)
    coverage, keywords = extractor.compute_coverage(keywords, resume_text)

    return {
        "data": {
            "resume_name": resume.name,
            "job_title": job.title,
            "company": job.company_name,
            "keyword_coverage": round(coverage, 2),
            "keywords": [
                {"keyword": k.keyword, "importance": k.importance, "in_resume": k.in_original}
                for k in keywords
            ],
            "missing_keywords": [
                k.keyword for k in keywords if not k.in_original and k.importance in ("required", "recommended")
            ],
            "total_keywords": len(keywords),
        }
    }


@router.post("/tailor")
async def tailor_resume(
    base_resume_id: UUID = Query(..., description="Base resume UUID"),
    job_id: UUID = Query(..., description="Target job UUID"),
    strategy: str = Query("moderate", pattern="^(conservative|moderate|aggressive|ats_only)$"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Generate a job-tailored resume variant with factuality verification."""
    profile_repo = SqlProfileRepository(session)
    resume_repo = SqlResumeRepository(session)
    job_repo = SqlJobRepository(session)
    tailored_repo = SqlTailoredResumeRepository(session)

    # Validate inputs
    resume = await resume_repo.get_by_user_and_id(current_user.id, base_resume_id)
    if not resume:
        raise BaseResumeNotFoundError(str(base_resume_id))

    profile = await profile_repo.get_by_user_id(current_user.id)
    job = await job_repo.get_by_id(job_id)
    if not job:
        from pathfinder.jobs.domain.exceptions import JobNotFoundError
        raise JobNotFoundError(str(job_id))

    # Build profile data
    profile_data = {}
    if profile:
        profile_data = {
            "full_name": profile.full_name,
            "headline": profile.headline,
            "skills": [
                {"name": s.name, "proficiency": s.proficiency.value, "years": s.years}
                for s in profile.skills
            ],
            "experiences": [
                {"company": e.company, "title": e.title, "description": e.description,
                 "achievements": list(e.achievements), "tech_stack": list(e.tech_stack)}
                for e in profile.work_experiences
            ],
            "education": [
                {"institution": e.institution, "degree": e.degree, "field": e.field}
                for e in profile.education
            ],
        }

    # Build request
    request = TailoringRequest(
        user_id=str(current_user.id),
        base_resume_id=str(base_resume_id),
        job_id=str(job_id),
        strategy=strategy,
    )

    # Tailor
    start = time.monotonic()
    engine = TailoringEngine()
    tailored = await engine.tailor(
        request=request,
        profile=profile_data,
        base_resume=resume.content,
        job_description=job.description_clean or job.description_raw or "",
        required_skills=[s.get("name", s) for s in (job.required_skills or [])],
        nice_to_have=[s.get("name", s) for s in (job.nice_to_have_skills or [])],
    )

    tailored.generation_metadata = {
        "latency_ms": int((time.monotonic() - start) * 1000),
        "model": "deepseek-chat",
        "strategy": strategy,
    }

    await tailored_repo.save(tailored)
    await session.commit()

    return {
        "data": {
            "tailored_resume_id": str(tailored.id),
            "job_title": tailored.job_title or job.title,
            "company": tailored.company_name or job.company_name,
            "strategy": tailored.strategy,
            "diffs": [
                {
                    "section": d.section,
                    "change": d.change_type,
                    "rationale": d.rationale,
                    "before_excerpt": d.before[:200] if d.before else "",
                    "after_excerpt": d.after[:200] if d.after else "",
                }
                for d in tailored.diffs
            ],
            "keyword_coverage_before": tailored.keyword_analysis.coverage_before if tailored.keyword_analysis else 0,
            "keyword_coverage_after": tailored.keyword_analysis.coverage_after if tailored.keyword_analysis else 0,
            "ats_score": tailored.scores.ats_score if tailored.scores else 0,
            "factuality_score": tailored.factuality_score,
            "factuality_violations": tailored.factuality_violations,
            "is_clean": tailored.is_clean,
            "generation_metadata": tailored.generation_metadata,
        }
    }


@router.get("/versions")
async def list_versions(
    base_resume_id: UUID = Query(...),
    job_id: UUID = Query(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List all tailored versions for a base resume + job combination."""
    repo = SqlTailoredResumeRepository(session)
    versions = await repo.list_versions(base_resume_id, job_id)
    return {
        "data": [
            {
                "version_id": str(v.id),
                "version": v.version,
                "strategy": v.strategy,
                "factuality_score": v.factuality_score,
                "is_accepted": v.is_accepted,
                "is_clean": v.is_clean,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ],
        "meta": {"count": len(versions)},
    }


@router.get("/compare")
async def compare_versions(
    version_a: UUID = Query(...),
    version_b: UUID = Query(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Compare two tailored resume versions side by side."""
    repo = SqlTailoredResumeRepository(session)
    a = await repo.get_by_id(version_a)
    b = await repo.get_by_id(version_b)

    if not a or not b:
        raise TailoredResumeNotFoundError()

    def _summary(t: TailoredResume) -> dict:
        return {
            "id": str(t.id),
            "version": t.version,
            "strategy": t.strategy,
            "factuality_score": t.factuality_score,
            "ats_score": t.scores.ats_score if t.scores else 0,
            "keyword_coverage": t.keyword_analysis.coverage_after if t.keyword_analysis else 0,
            "violations_count": len(t.factuality_violations),
            "is_accepted": t.is_accepted,
        }

    a_ats = a.scores.ats_score if a.scores else 0
    b_ats = b.scores.ats_score if b.scores else 0
    if a_ats > b_ats:
        recommendation = "version_a"
    elif b_ats > a_ats:
        recommendation = "version_b"
    else:
        recommendation = "either"

    return {
        "data": {
            "version_a": _summary(a),
            "version_b": _summary(b),
            "recommendation": recommendation,
        }
    }


@router.post("/{tailored_id}/accept")
async def accept_tailored(
    tailored_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Accept a tailored resume variant."""
    repo = SqlTailoredResumeRepository(session)
    tailored = await repo.get_by_user_and_id(current_user.id, tailored_id)
    if not tailored:
        raise TailoredResumeNotFoundError(str(tailored_id))

    tailored.accept()
    await repo.save(tailored)
    await session.commit()
    return {"data": {"status": "accepted", "tailored_id": str(tailored_id)}}
