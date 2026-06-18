"""SupervisorAgent state — the core state object flowing through the LangGraph."""
from __future__ import annotations
from typing import TypedDict


class SupervisorState(TypedDict, total=False):
    """State carried through every node of the Supervisor graph."""

    session_id: str
    user_id: str
    tier: str
    user_message: str
    user_profile: dict | None
    user_preferences: dict | None
    user_resumes: list[dict]
    intent: str | None
    intent_confidence: float
    clarification_question: str | None
    execution_plan: list[dict]
    current_step: int
    tool_results: dict[str, dict]
    tool_errors: dict[str, str]
    final_response: str | None
    call_id: str
    errors: list[str]
    quality_gate_passes: int
    agent_phase: str
    recent_history: list[dict]
    memory_context: str
    knowledge_context: str
