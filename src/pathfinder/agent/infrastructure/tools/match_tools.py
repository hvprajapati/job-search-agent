"""Matching tools for the Supervisor Agent."""
from uuid import UUID
from pathfinder.shared.infrastructure.database import get_sessionmaker
from pathfinder.jobs.infrastructure.persistence.job_repository import SqlJobRepository
from pathfinder.profile.infrastructure.persistence.profile_repository import SqlProfileRepository
from pathfinder.jobs.domain.matching.services import MatchingOrchestrator, MatchContext
from pathfinder.agent.domain.tools import tool_registry, ToolDefinition


async def _compute_match(user_id: str, job_id: str, **kwargs) -> dict:
    maker = get_sessionmaker()
    async with maker() as session:
        profile_repo = SqlProfileRepository(session)
        job_repo = SqlJobRepository(session)
        profile = await profile_repo.get_by_user_id(UUID(user_id))
        job = await job_repo.get_by_id(UUID(job_id))
        if not profile or not job:
            return {"error": "Profile or job not found"}
        ctx = MatchContext(
            user_id=UUID(user_id), job_id=UUID(job_id),
            user_skills=[{"name": s.name, "proficiency": s.proficiency.value, "years": s.years} for s in profile.skills],
            user_experiences=[{"company": e.company, "title": e.title, "years": 0} for e in profile.work_experiences],
            user_education=[{"degree": e.degree, "field": e.field} for e in profile.education],
            user_location=profile.location,
            job_title=job.title, job_description=job.description_clean or "",
            job_required_skills=job.required_skills if job.required_skills else [{"name": s} for s in (job.tech_stack or [])],
            job_seniority=job.seniority.value, job_remote_policy=job.remote_policy.value,
            job_company_name=job.company_name,
        )
        orchestrator = MatchingOrchestrator()
        match = await orchestrator.compute_match(ctx, UUID(user_id), UUID(job_id))
        return {
            "overall_score": match.overall_score,
            "dimensions": {d.dimension.value: {"score": d.score, "weight": d.weight} for d in match.dimensions},
            "strengths": [s.text for s in match.strengths[:3]],
            "skill_gaps": [{"skill": g.skill_name, "severity": g.severity.value} for g in match.skill_gaps[:5]],
            "has_dealbreaker": match.has_dealbreaker_gap,
        }


async def _get_recommendations(user_id: str, limit: int = 5, **kwargs) -> dict:
    from pathfinder.jobs.infrastructure.persistence.job_repository import SqlJobRepository
    maker = get_sessionmaker()
    async with maker() as session:
        repo = SqlJobRepository(session)
        jobs, _, _ = await repo.search(limit=limit)
        return {
            "recommendations": [
                {"job_id": str(j.id), "title": j.title, "company": j.company_name}
                for j in jobs
            ],
        }


def register_match_tools():
    if "compute_match" not in tool_registry.tool_names:
        tool_registry.register(
            ToolDefinition(name="compute_match", description="Calculate how well a user matches a specific job. Returns scores, strengths, and skill gaps.",
                          parameters={"type": "object", "properties": {"user_id": {"type": "string"}, "job_id": {"type": "string"}}, "required": ["user_id", "job_id"]},
                          is_expensive=True),
            _compute_match,
        )
    if "get_recommendations" not in tool_registry.tool_names:
        tool_registry.register(
            ToolDefinition(name="get_recommendations", description="Get top job recommendations for a user.",
                          parameters={"type": "object", "properties": {"user_id": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["user_id"]}),
            _get_recommendations,
        )
