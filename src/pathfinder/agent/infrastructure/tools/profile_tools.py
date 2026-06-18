"""Profile tools for the Supervisor Agent."""
from uuid import UUID
from pathfinder.shared.infrastructure.database import get_sessionmaker
from pathfinder.profile.infrastructure.persistence.profile_repository import SqlProfileRepository
from pathfinder.profile.infrastructure.persistence.resume_repository import SqlResumeRepository
from pathfinder.agent.domain.tools import tool_registry, ToolDefinition


async def _get_profile(user_id: str, **kwargs) -> dict:
    maker = get_sessionmaker()
    async with maker() as session:
        repo = SqlProfileRepository(session)
        profile = await repo.get_by_user_id(UUID(user_id))
        if not profile:
            return {"error": "Profile not found"}
        return {
            "full_name": profile.full_name, "headline": profile.headline,
            "skills": [{"name": s.name, "proficiency": s.proficiency.value, "years": s.years} for s in profile.skills],
            "experience_count": len(profile.work_experiences),
            "education_count": len(profile.education),
        }


async def _get_resumes(user_id: str, **kwargs) -> dict:
    maker = get_sessionmaker()
    async with maker() as session:
        repo = SqlResumeRepository(session)
        resumes = await repo.list_by_user(UUID(user_id), limit=20)
        return {
            "count": len(resumes),
            "resumes": [
                {"resume_id": str(r.id), "name": r.name, "is_base": r.is_base,
                 "template": r.template_id, "tailored_for": r.tailored_for_role}
                for r in resumes
            ],
        }


def register_profile_tools():
    if "get_profile" not in tool_registry.tool_names:
        tool_registry.register(
            ToolDefinition(name="get_profile", description="Retrieve the user's professional profile including skills, experience, and education.",
                          parameters={"type": "object", "properties": {"user_id": {"type": "string"}}, "required": ["user_id"]}),
            _get_profile,
        )
    if "get_resumes" not in tool_registry.tool_names:
        tool_registry.register(
            ToolDefinition(name="get_resumes", description="Retrieve the user's saved resumes (base and tailored variants).",
                          parameters={"type": "object", "properties": {"user_id": {"type": "string"}}, "required": ["user_id"]}),
            _get_resumes,
        )
