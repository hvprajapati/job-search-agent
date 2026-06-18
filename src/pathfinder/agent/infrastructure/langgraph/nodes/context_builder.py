"""Context Builder node — loads profile, preferences, memory, and knowledge."""
from uuid import UUID
import logging
from pathfinder.agent.domain.state import SupervisorState
from pathfinder.shared.infrastructure.database import get_sessionmaker
from pathfinder.profile.infrastructure.persistence.profile_repository import SqlProfileRepository
from pathfinder.profile.infrastructure.persistence.resume_repository import SqlResumeRepository
from pathfinder.agent.infrastructure.memory.repositories import SqlEpisodicRepository, SqlSemanticRepository

logger = logging.getLogger(__name__)


async def context_builder_node(state: SupervisorState) -> dict:
    user_id = state.get("user_id")
    if not user_id:
        return {"errors": ["No user_id in state"]}

    maker = get_sessionmaker()
    async with maker() as session:
        profile_repo = SqlProfileRepository(session)
        profile = await profile_repo.get_by_user_id(UUID(user_id))

        resume_repo = SqlResumeRepository(session)
        resumes = await resume_repo.list_by_user(UUID(user_id), limit=10)

        episodic_repo = SqlEpisodicRepository(session)
        recent = await episodic_repo.list_recent(UUID(user_id), limit=20)

        semantic_repo = SqlSemanticRepository(session)
        semantic = await semantic_repo.search_by_type(UUID(user_id), limit=10)

    # Build memory context text
    memory_lines: list[str] = []
    if semantic:
        memory_lines.append("FACTS ABOUT THIS USER:")
        for s in semantic[:8]:
            content = (s.content_text or str(s.content))[:200]
            memory_lines.append(f"  - {s.subject}: {content} (confidence: {s.confidence:.0%})")
    if recent:
        memory_lines.append("\nRECENT ACTIVITY:")
        for ep in recent[:10]:
            if ep.context_summary:
                memory_lines.append(f"  - {ep.context_summary[:150]}")

    return {
        "user_profile": {
            "full_name": profile.full_name,
            "headline": profile.headline,
            "skills": [{"name": s.name, "proficiency": s.proficiency.value} for s in profile.skills],
            "education": [{"degree": e.degree, "field": e.field} for e in profile.education],
        } if profile else None,
        "user_preferences": {},
        "user_resumes": [
            {"resume_id": str(r.id), "name": r.name, "is_base": r.is_base} for r in resumes
        ],
        "recent_history": [
            {"type": ep.episode_type.value if hasattr(ep, 'episode_type') else str(ep.episode_type),
             "summary": ep.context_summary, "timestamp": ep.created_at.isoformat() if ep.created_at else ""}
            for ep in recent[:15]
        ],
        "memory_context": "\n".join(memory_lines) if memory_lines else "",
        "knowledge_context": "",
        "agent_phase": "context_loaded",
    }
