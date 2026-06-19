"""Admin dashboard routes — operational health and statistics."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pathfinder.shared.infrastructure.database import get_session
from pathfinder.identity.presentation.dependencies import get_current_user
from pathfinder.identity.domain.entities import User

router = APIRouter(prefix="/v1/admin", tags=["Admin"])


@router.get("/stats")
async def admin_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Return aggregate counts of all major entities for the admin dashboard."""

    tables = {
        "users": "users",
        "profiles": "profiles",
        "resumes": "resumes",
        "job_postings": "job_postings",
        "applications": "applications",
        "agent_executions": "agent_executions",
        "knowledge_documents": "knowledge_documents",
        "knowledge_chunks": "knowledge_chunks",
        "episodic_memories": "episodic_memories",
        "semantic_memories": "semantic_memories",
        "tailored_resumes": "tailored_resumes",
    }

    counts = {}
    for key, table in tables.items():
        try:
            result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            counts[key] = result.scalar() or 0
        except Exception:
            counts[key] = -1  # Table doesn't exist or inaccessible

    # Additional computed metrics
    counts["active_jobs"] = 0
    try:
        result = await session.execute(
            text("SELECT COUNT(*) FROM job_postings WHERE is_active = true")
        )
        counts["active_jobs"] = result.scalar() or 0
    except Exception:
        pass

    counts["applications_by_status"] = {}
    try:
        result = await session.execute(
            text("SELECT status, COUNT(*) FROM applications GROUP BY status")
        )
        for row in result:
            counts["applications_by_status"][row[0]] = row[1]
    except Exception:
        pass

    # Tier distribution
    counts["users_by_tier"] = {}
    try:
        result = await session.execute(
            text("SELECT tier, COUNT(*) FROM users GROUP BY tier")
        )
        for row in result:
            counts["users_by_tier"][row[0]] = row[1]
    except Exception:
        pass

    return {
        "data": {
            "entity_counts": counts,
            "timestamp": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        }
    }
