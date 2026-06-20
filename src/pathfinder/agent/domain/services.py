"""Agent domain services — intent routing and task planning."""
from __future__ import annotations
import json
import hashlib
import time
from pathfinder.agent.domain.state import SupervisorState
from pathfinder.agent.domain.value_objects import Intent
from pathfinder.agent.domain.tools import ToolRegistry


class IntentRouter:
    SYSTEM_PROMPT = """You are an intent classifier for a career AI agent.
Classify the user's message into exactly one intent from: search_jobs, match_me, tailor_resume, generate_cover_letter, prep_interview, track_applications, follow_up, analyze_skill_gap, career_advice, update_profile, general_question.
Respond with ONLY: {"intent": "...", "confidence": 0.0-1.0}"""

    # Simple LRU-style cache for intent classifications
    _cache: dict[str, tuple[Intent, float, float]] = {}  # hash -> (intent, confidence, timestamp)
    _cache_ttl: float = 60.0  # Cache for 60 seconds
    _cache_max_size: int = 100

    def __init__(self, llm) -> None:
        self._llm = llm

    @classmethod
    def _cache_key(cls, user_message: str) -> str:
        return hashlib.md5(user_message.strip().lower().encode()).hexdigest()

    @classmethod
    def _cache_get(cls, user_message: str) -> tuple[Intent, float] | None:
        key = cls._cache_key(user_message)
        if key in cls._cache:
            intent, confidence, ts = cls._cache[key]
            if time.monotonic() - ts < cls._cache_ttl:
                return intent, confidence
            del cls._cache[key]
        return None

    @classmethod
    def _cache_set(cls, user_message: str, intent: Intent, confidence: float) -> None:
        if len(cls._cache) >= cls._cache_max_size:
            # Evict oldest entry
            oldest = min(cls._cache.items(), key=lambda x: x[1][2])
            del cls._cache[oldest[0]]
        cls._cache[cls._cache_key(user_message)] = (intent, confidence, time.monotonic())

    async def classify(self, user_message: str) -> tuple[Intent, float]:
        # Check cache first
        cached = self._cache_get(user_message)
        if cached is not None:
            return cached

        try:
            response = await self._llm.chat_completion(
                system_prompt=self.SYSTEM_PROMPT, user_prompt=user_message,
                temperature=0.1, response_format={"type": "json_object"},
            )
            result = json.loads(response.content)
            intent_str = result.get("intent", "general_question")
            confidence = float(result.get("confidence", 0.5))
            intent = Intent(intent_str) if intent_str in Intent.__members__.values() else Intent.GENERAL_QUESTION
            confidence = min(1.0, max(0.0, confidence))
            # Cache successful classifications with confidence >= 0.5
            if confidence >= 0.5:
                self._cache_set(user_message, intent, confidence)
            return intent, confidence
        except Exception:
            return Intent.GENERAL_QUESTION, 0.3


class TaskPlanner:
    SYSTEM_PROMPT = """You are a task planner. Given an intent and available tools, create an execution plan as a JSON array of steps.
Each step: {"step_id": "1", "tool_name": "name", "tool_args": {}, "depends_on": []}
Use minimum steps. For general_question: return []. Output ONLY the JSON array."""

    def __init__(self, llm, registry: ToolRegistry) -> None:
        self._llm = llm
        self._registry = registry

    async def plan(self, intent: Intent, user_message: str,
                   state: SupervisorState) -> list[dict]:
        if intent == Intent.GENERAL_QUESTION:
            return []

        tools_desc = "\n".join(
            f"- {t.name}: {t.description}" for t in self._registry.get_all_definitions()
        )
        memory = state.get("memory_context", "")
        knowledge = state.get("knowledge_context", "")
        context_parts = []
        if memory:
            context_parts.append(f"USER MEMORY:\n{memory[:1000]}")
        if knowledge:
            context_parts.append(f"RELEVANT KNOWLEDGE:\n{knowledge[:1000]}")
        ctx_block = "\n\n".join(context_parts)

        prompt = (
            f"{ctx_block}\n\n" if ctx_block else ""
        ) + (
            f"INTENT: {intent.value}\n"
            f"USER MESSAGE: \"{user_message}\"\n"
            f"AVAILABLE TOOLS:\n{tools_desc}\n\n"
            f"Create an execution plan as a JSON array."
        )

        try:
            response = await self._llm.chat_completion(
                system_prompt=self.SYSTEM_PROMPT, user_prompt=prompt,
                temperature=0.2, response_format={"type": "json_object"},
            )
            plan = json.loads(response.content)
            if isinstance(plan, dict):
                plan = plan.get("steps", plan.get("plan", []))
            return plan if isinstance(plan, list) else []
        except Exception:
            return self._fallback_plan(intent, state)

    def _fallback_plan(self, intent: Intent, state: SupervisorState | None = None) -> list[dict]:
        memory = (state or {}).get("memory_context", "")
        remote_only = "remote" in memory.lower() if memory else False
        return {
            Intent.SEARCH_JOBS: [{"step_id": "1", "tool_name": "search_jobs",
                                  "tool_args": {"query": "", "limit": 10,
                                  **({"remote_only": True} if remote_only else {})}, "depends_on": []}],
            Intent.MATCH_ME: [{"step_id": "1", "tool_name": "get_recommendations",
                               "tool_args": {"limit": 5}, "depends_on": []}],
            Intent.TAILOR_RESUME: [{"step_id": "1", "tool_name": "get_resumes", "tool_args": {}, "depends_on": []},
                                   {"step_id": "2", "tool_name": "get_profile", "tool_args": {}, "depends_on": []}],
            Intent.UPDATE_PROFILE: [{"step_id": "1", "tool_name": "get_profile", "tool_args": {}, "depends_on": []}],
            Intent.CAREER_ADVICE: [{"step_id": "1", "tool_name": "get_profile", "tool_args": {}, "depends_on": []},
                                   {"step_id": "2", "tool_name": "get_recommendations", "tool_args": {"limit": 5}, "depends_on": []}],
            Intent.ANALYZE_SKILL_GAP: [{"step_id": "1", "tool_name": "get_profile", "tool_args": {}, "depends_on": []},
                                       {"step_id": "2", "tool_name": "get_recommendations", "tool_args": {"limit": 5}, "depends_on": []}],
        }.get(intent, [])
