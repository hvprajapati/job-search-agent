"""Guardrail node — first node in the graph."""
import re
from pathfinder.agent.domain.state import SupervisorState

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?)",
    r"you\s+are\s+now\s+(a\s+)?(different|new|other)",
    r"system\s*(prompt|message|instruction)\s*(:|=|is)",
]


def _detect_injection(message: str) -> bool:
    msg_lower = message.lower()
    return any(re.search(p, msg_lower) for p in INJECTION_PATTERNS)


async def guardrail_node(state: SupervisorState) -> dict:
    user_message = state.get("user_message", "")
    if not user_message or len(user_message.strip()) < 1:
        return {"final_response": "I didn't catch that. What would you like help with?", "agent_phase": "blocked"}
    if _detect_injection(user_message):
        return {"final_response": "I can only help with job search and career-related questions.", "agent_phase": "blocked"}
    return {"agent_phase": "guardrail_passed"}
