"""Job search tools for the Supervisor Agent."""
from uuid import UUID
from pathfinder.shared.infrastructure.database import get_sessionmaker
from pathfinder.jobs.infrastructure.persistence.job_repository import SqlJobRepository
from pathfinder.agent.domain.tools import tool_registry, ToolDefinition


async def _search_jobs(query: str = "", location: str = "",
                       remote_only: bool = False, limit: int = 10, **kwargs) -> dict:
    maker = get_sessionmaker()
    async with maker() as session:
        repo = SqlJobRepository(session)
        filters = {}
        if remote_only:
            filters["remote_policy"] = "remote"
        jobs, _, total = await repo.search(query=query, filters=filters, limit=limit)
        return {
            "total": total,
            "jobs": [
                {"job_id": str(j.id), "title": j.title, "company": j.company_name,
                 "location": j.location.display_text, "remote": j.remote_policy.value,
                 "summary": (j.description_summary or "")[:200],
                 "tech_stack": j.tech_stack}
                for j in jobs
            ],
        }


async def _get_job_detail(job_id: str, **kwargs) -> dict:
    maker = get_sessionmaker()
    async with maker() as session:
        repo = SqlJobRepository(session)
        job = await repo.get_by_id(UUID(job_id))
        if not job:
            return {"error": "Job not found"}
        return {
            "job_id": str(job.id), "title": job.title, "company": job.company_name,
            "description": job.description_clean or job.description_raw or "",
            "tech_stack": job.tech_stack, "seniority": job.seniority.value,
            "remote_policy": job.remote_policy.value,
        }


def register_search_tools():
    if "search_jobs" not in tool_registry.tool_names:
        tool_registry.register(
            ToolDefinition(name="search_jobs", description="Search for job listings by keyword, location, or remote preference.",
                          parameters={"type": "object", "properties": {"query": {"type": "string"}, "location": {"type": "string"}, "remote_only": {"type": "boolean"}, "limit": {"type": "integer"}}, "required": ["query"]}),
            _search_jobs,
        )
    if "get_job_detail" not in tool_registry.tool_names:
        tool_registry.register(
            ToolDefinition(name="get_job_detail", description="Get full details for a specific job by its UUID.",
                          parameters={"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]}),
            _get_job_detail,
        )
