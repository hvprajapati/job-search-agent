"""Matching API routes."""
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.shared.infrastructure.database import get_session
from pathfinder.identity.presentation.dependencies import get_current_user
from pathfinder.identity.domain.entities import User
from pathfinder.jobs.domain.matching.services import MatchingOrchestrator, MatchContext
from pathfinder.profile.infrastructure.persistence.profile_repository import SqlProfileRepository
from pathfinder.jobs.infrastructure.persistence.job_repository import SqlJobRepository

router = APIRouter(prefix="/v1/match", tags=["Matching"])


@router.post("/compute")
async def compute_match(
    job_id: UUID = Query(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    profile_repo = SqlProfileRepository(session)
    job_repo = SqlJobRepository(session)

    profile = await profile_repo.get_by_user_id(current_user.id)
    job = await job_repo.get_by_id(job_id)
    if not job:
        from pathfinder.jobs.domain.exceptions import JobNotFoundError
        raise JobNotFoundError(str(job_id))

    ctx = MatchContext(
        user_id=current_user.id, job_id=job_id,
        user_skills=[{"name": s.name, "proficiency": s.proficiency.value, "years": s.years}
                      for s in (profile.skills if profile else [])],
        user_experiences=[{"company": e.company, "title": e.title,
                           "years": 0, "description": e.description}
                          for e in (profile.work_experiences if profile else [])],
        user_education=[{"degree": e.degree, "field": e.field}
                        for e in (profile.education if profile else [])],
        user_location=profile.location if profile else None,
        job_title=job.title,
        job_description=job.description_clean or "",
        job_required_skills=job.required_skills if job.required_skills else [
            {"name": s} for s in (job.tech_stack or [])
        ],
        job_seniority=job.seniority.value,
        job_remote_policy=job.remote_policy.value,
        job_company_name=job.company_name,
    )

    orchestrator = MatchingOrchestrator()
    match = await orchestrator.compute_match(ctx, current_user.id, job_id)

    return {
        "data": {
            "overall_score": match.overall_score,
            "dimensions": {
                d.dimension.value: {"score": d.score, "weight": d.weight}
                for d in match.dimensions
            },
            "strengths": [s.text for s in match.strengths[:3]],
            "skill_gaps": [
                {"skill": g.skill_name, "severity": g.severity.value}
                for g in match.skill_gaps[:5]
            ],
            "has_dealbreaker": match.has_dealbreaker_gap,
            "is_high_match": match.is_high_match,
        }
    }


@router.post("/feedback")
async def record_feedback(
    job_id: UUID = Query(...),
    feedback: str = Query(..., pattern="^(thumbs_up|thumbs_down|dismiss)$"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    import logging
    from pathfinder.agent.infrastructure.memory.models import EpisodicMemoryModel
    from pathfinder.agent.domain.memory.entities import EpisodicMemory

    # Persist feedback as episodic memory
    try:
        ep = EpisodicMemory.record_feedback(
            user_id=current_user.id, job_id=job_id, feedback=feedback,
        )
        model = EpisodicMemoryModel(
            id=ep.id,
            user_id=ep.user_id,
            tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
            session_id=ep.session_id,
            episode_type=ep.episode_type.value,
            actor=ep.actor,
            action=ep.action,
            payload=ep.payload,
            importance_score=ep.importance.value,
            context_summary=ep.context_summary,
            is_consolidated=False,
            expires_at=ep.expires_at,
            created_at=ep.created_at,
            recorded_at=ep.created_at,
        )
        session.add(model)
        await session.commit()
        logging.getLogger(__name__).info(f"Feedback recorded: user={current_user.id} job={job_id} feedback={feedback}")
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to persist feedback: {e}")

    return {"data": {"status": "feedback_recorded", "job_id": str(job_id), "feedback": feedback}}
