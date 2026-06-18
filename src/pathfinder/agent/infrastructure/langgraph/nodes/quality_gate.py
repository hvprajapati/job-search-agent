"""Quality Gate node — validates response before sending to user."""
from pathfinder.agent.domain.state import SupervisorState


async def quality_gate_node(state: SupervisorState) -> dict:
    response = state.get("final_response", "")
    passes = state.get("quality_gate_passes", 0)

    if not response or len(response.strip()) < 10:
        if passes < 3:
            return {"quality_gate_passes": passes + 1, "agent_phase": "revise"}
        return {"final_response": "I encountered an issue processing your request. Please try again.", "agent_phase": "quality_failed"}

    return {"agent_phase": "quality_passed"}
