"""Tool Executor node — executes the plan by calling tools."""
from pathfinder.agent.domain.state import SupervisorState
from pathfinder.agent.domain.tools import tool_registry


async def tool_executor_node(state: SupervisorState) -> dict:
    plan = state.get("execution_plan", [])
    user_id = state.get("user_id", "")
    results: dict[str, dict] = {}
    errors: dict[str, str] = {}

    for step in plan:
        tool_name = step.get("tool_name", "")
        tool_args = step.get("tool_args", {})
        step_id = step.get("step_id", "unknown")
        if "user_id" in tool_args or tool_name in ("get_profile", "get_resumes", "compute_match", "get_recommendations"):
            tool_args.setdefault("user_id", user_id)

        result = await tool_registry.execute(tool_name, **tool_args)
        if result.success:
            results[step_id] = result.data or {"status": "completed"}
        else:
            errors[step_id] = result.error or "Unknown error"

    return {"tool_results": results, "tool_errors": errors, "agent_phase": "tools_executed"}
