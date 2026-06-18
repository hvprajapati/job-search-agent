"""Intent Router node — LLM classifies user message into an intent."""
from pathfinder.agent.domain.state import SupervisorState
from pathfinder.agent.domain.services import IntentRouter
from pathfinder.profile.infrastructure.llm.deepseek_client import DeepSeekClient

_llm_client: DeepSeekClient | None = None
_router: IntentRouter | None = None


def _get_router() -> IntentRouter:
    global _llm_client, _router
    if _router is None:
        _llm_client = DeepSeekClient()
        _router = IntentRouter(_llm_client)
    return _router


async def intent_router_node(state: SupervisorState) -> dict:
    user_message = state.get("user_message", "")
    memory_context = state.get("memory_context", "")
    knowledge_context = state.get("knowledge_context", "")

    enriched = user_message
    if memory_context or knowledge_context:
        parts = []
        if memory_context:
            parts.append(f"User context:\n{memory_context[:1000]}")
        if knowledge_context:
            parts.append(f"Relevant knowledge:\n{knowledge_context[:1000]}")
        enriched = "\n\n".join(parts) + f"\n\n---\nUser message: {user_message}"

    router = _get_router()
    intent, confidence = await router.classify(enriched)

    if confidence < 0.7:
        return {
            "intent": "general_question", "intent_confidence": confidence,
            "clarification_question": "I'm not quite sure what you'd like me to do. Could you rephrase?",
            "agent_phase": "needs_clarification",
        }

    return {"intent": intent.value, "intent_confidence": confidence, "agent_phase": "intent_classified"}
