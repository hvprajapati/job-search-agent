"""Task Planner node — decomposes intent into tool calls."""
from pathfinder.agent.domain.state import SupervisorState
from pathfinder.agent.domain.services import TaskPlanner
from pathfinder.agent.domain.value_objects import Intent
from pathfinder.agent.domain.tools import tool_registry
from pathfinder.profile.infrastructure.llm.deepseek_client import DeepSeekClient

_llm_client: DeepSeekClient | None = None
_planner: TaskPlanner | None = None


def _get_planner() -> TaskPlanner:
    global _llm_client, _planner
    if _planner is None:
        _llm_client = DeepSeekClient()
        _planner = TaskPlanner(_llm_client, tool_registry)
    return _planner


async def task_planner_node(state: SupervisorState) -> dict:
    intent_str = state.get("intent", "general_question")
    user_message = state.get("user_message", "")

    try:
        intent = Intent(intent_str)
    except ValueError:
        intent = Intent.GENERAL_QUESTION

    planner = _get_planner()
    plan = await planner.plan(intent, user_message, state)

    return {"execution_plan": plan, "current_step": 0, "agent_phase": "plan_created"}
