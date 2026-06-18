"""Job Search and Company API routes."""
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.shared.infrastructure.database import get_session
from pathfinder.identity.presentation.dependencies import get_current_user
from pathfinder.identity.domain.entities import User
from pathfinder.jobs.infrastructure.persistence.job_repository import SqlJobRepository
from pathfinder.jobs.infrastructure.persistence.company_repository import SqlCompanyRepository
from pathfinder.jobs.domain.exceptions import JobNotFoundError, CompanyNotFoundError

router = APIRouter(prefix="/v1", tags=["Jobs & Companies"])


@router.get("/jobs")
async def search_jobs(
    q: str | None = Query(None),
    remote_policy: str | None = Query(None),
    seniority: str | None = Query(None),
    salary_min: int | None = Query(None, ge=0),
    source_type: str | None = Query(None),
    sort: str = Query("-first_seen_at"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    repo = SqlJobRepository(session)
    filters = {}
    if remote_policy:
        filters["remote_policy"] = remote_policy
    if seniority:
        filters["seniority"] = seniority
    if salary_min:
        filters["salary_min"] = salary_min
    if source_type:
        filters["source_type"] = source_type

    jobs, next_cursor, total = await repo.search(
        query=q, filters=filters, sort=sort, limit=limit,
    )
    return {
        "data": [
            {
                "job_id": str(j.id), "title": j.title,
                "company": j.company_name,
                "location": j.location.display_text,
                "remote_policy": j.remote_policy.value,
                "description_summary": j.description_summary,
                "salary_range": {
                    "min": j.salary_range.min_amount,
                    "max": j.salary_range.max_amount,
                } if j.salary_range else None,
                "tech_stack": j.tech_stack,
                "seniority": j.seniority.value,
                "first_seen_at": j.first_seen_at.isoformat() if j.first_seen_at else None,
            }
            for j in jobs
        ],
        "meta": {"cursor_next": next_cursor, "count": total, "limit": limit},
    }


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    repo = SqlJobRepository(session)
    job = await repo.get_by_id(job_id)
    if not job:
        raise JobNotFoundError(str(job_id))

    company = None
    if job.company_id:
        company_repo = SqlCompanyRepository(session)
        company = await company_repo.get_by_id(job.company_id)

    return {
        "data": {
            "job_id": str(job.id), "title": job.title,
            "company": {
                "company_id": str(company.id) if company else None,
                "name": job.company_name,
                "industry": company.industry if company else "",
            } if company or job.company_name else None,
            "description": job.description_clean or job.description_raw,
            "remote_policy": job.remote_policy.value,
            "tech_stack": job.tech_stack,
            "seniority": job.seniority.value,
            "source_url": job.source_url,
            "application_url": job.application_url,
        }
    }


@router.get("/companies")
async def search_companies(
    q: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    repo = SqlCompanyRepository(session)
    companies = await repo.search(query=q, limit=limit)
    return {
        "data": [
            {"company_id": str(c.id), "name": c.name, "website": c.website,
             "industry": c.industry}
            for c in companies
        ],
    }


@router.get("/companies/{company_id}")
async def get_company(
    company_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    repo = SqlCompanyRepository(session)
    company = await repo.get_by_id(company_id)
    if not company:
        raise CompanyNotFoundError(str(company_id))
    return {
        "data": {
            "company_id": str(company.id), "name": company.name,
            "website": company.website, "industry": company.industry,
            "size_range": company.size_range, "funding_stage": company.funding_stage,
            "glassdoor_rating": company.glassdoor_rating,
        }
    }
