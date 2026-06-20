"""Agent domain services — intent routing and task planning."""
from __future__ import annotations
import json
import hashlib
import re
import time
from pathfinder.agent.domain.state import SupervisorState
from pathfinder.agent.domain.value_objects import Intent
from pathfinder.agent.domain.tools import ToolRegistry


class IntentRouter:
    SYSTEM_PROMPT = """You are an intent classifier for a career AI agent.
Classify the user's message into exactly one intent from: search_jobs, match_me, tailor_resume, generate_cover_letter, prep_interview, track_applications, follow_up, analyze_skill_gap, career_advice, update_profile, general_question.
Respond with ONLY this valid JSON object: {"intent": "...", "confidence": 0.0-1.0}"""

    # Keyword-based intent patterns (runs when LLM is unavailable)
    # Order matters — more specific patterns MUST come before broad ones
    _KEYWORD_PATTERNS: list[tuple[re.Pattern, Intent, float]] = [
        # Match/match score queries (check BEFORE search patterns — "how well do I match" is NOT a search)
        (re.compile(r"\b(how\s+(well|good|much)\s+(do|am|would)\s+i\s+(fit|match)|match\s+(me|my|score)|compatib|what(?:'s|\s+is)\s+my\s+match)\b", re.I), Intent.MATCH_ME, 0.80),
        # Tailor/customize resume
        (re.compile(r"\b(tailor|customize|rewrite|optimize|improve|tune|adapt)\b.*\b(resume|cv|cover\s+letter|application)\b", re.I), Intent.TAILOR_RESUME, 0.82),
        (re.compile(r"\b(tailor|customize)\b", re.I), Intent.TAILOR_RESUME, 0.65),
        # Cover letter
        (re.compile(r"\b(cover\s+letter|write\s+(?:a|me)\s+(?:cover\s+)?letter)\b", re.I), Intent.GENERATE_COVER_LETTER, 0.82),
        # Interview prep
        (re.compile(r"\b(interview|prep(?:are)?\s+for|mock\s+interview|practice\s+interview)\b", re.I), Intent.PREP_INTERVIEW, 0.78),
        # Skill gap analysis
        (re.compile(r"\b(skills?\s+gap|what\s+(?:skills?\s+)?(?:am\s+I|should\s+I|do\s+I\s+need\s+to)\s+(missing|lacking|learn|improve|work\s+on)|where\s+(?:am\s+I|do\s+I)\s+(lacking|falling\s+short)|what.+(?:should|need\s+to)\s+(?:learn|study|improve|get\s+better))\b", re.I), Intent.ANALYZE_SKILL_GAP, 0.82),
        # Application tracking
        (re.compile(r"\b(track|status|my\s+app|where.*application|check.*application|application.*status|pipeline|applied)\b", re.I), Intent.TRACK_APPLICATIONS, 0.78),
        # Career advice/recommendations
        (re.compile(r"\b(career\s+advice|what\s+should\s+I\s+do|career\s+path|career\s+change|should\s+I\s+(switch|change|move)|recommend|suggest.*career)\b", re.I), Intent.CAREER_ADVICE, 0.72),
        # Profile update
        (re.compile(r"\b(update|change|edit|modify|fix)\b.*\b(my\s+)?(profile|resume|skills?|information|details)\b", re.I), Intent.UPDATE_PROFILE, 0.80),
        # Follow up
        (re.compile(r"\b(follow\s*up|send\s+(?:a|an)\s+(?:follow|email)|reach\s+out)\b", re.I), Intent.FOLLOW_UP, 0.78),
        # Job search — MUST come last (broad pattern)
        (re.compile(r"\b(find|search|looking?\s+for|show|get\s+me|list|browse)\b.*\b(jobs?|positions?|roles?|openings?|opportunit)\b", re.I), Intent.SEARCH_JOBS, 0.78),
        # Search-like queries mentioning specific roles or technologies
        (re.compile(r"\b(find|search|looking?\s+for|show\s+me|get\s+me|any|some)\b", re.I), Intent.SEARCH_JOBS, 0.68),
        # Queries that mention job titles or tech stacks (likely job search intent)
        (re.compile(r"\b(remote|onsite|hybrid)\s*(jobs?|positions?|roles?|work)\b", re.I), Intent.SEARCH_JOBS, 0.72),
    ]

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

    @classmethod
    def _keyword_classify(cls, user_message: str) -> tuple[Intent, float]:
        """Fallback intent classification using keyword patterns when LLM is unavailable."""
        for pattern, intent, confidence in cls._KEYWORD_PATTERNS:
            if pattern.search(user_message):
                return intent, confidence
        return Intent.GENERAL_QUESTION, 0.50

    async def classify(self, user_message: str) -> tuple[Intent, float]:
        # Check cache first
        cached = self._cache_get(user_message)
        if cached is not None:
            return cached

        # Try LLM classification
        try:
            response = await self._llm.chat_completion(
                system_prompt=self.SYSTEM_PROMPT, user_prompt=user_message,
                temperature=0.1, response_format={"type": "json_object"},
            )
            result = json.loads(response.content)
            intent_str = result.get("intent", "general_question")
            confidence = float(result.get("confidence", 0.5))
            try:
                intent = Intent(intent_str)
            except ValueError:
                intent = Intent.GENERAL_QUESTION
            confidence = min(1.0, max(0.0, confidence))
            # Cache successful classifications with confidence >= 0.5
            if confidence >= 0.5:
                self._cache_set(user_message, intent, confidence)
            return intent, confidence
        except Exception:
            # LLM unavailable — use keyword-based fallback
            intent, confidence = self._keyword_classify(user_message)
            if confidence >= 0.6:
                self._cache_set(user_message, intent, confidence)
            return intent, confidence


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
            if isinstance(plan, list) and self._validate_plan(plan):
                return plan
            # LLM returned invalid plan — fall back
            return self._fallback_plan(intent, state)
        except Exception:
            return self._fallback_plan(intent, state)

    def _validate_plan(self, plan: list[dict]) -> bool:
        """Ensure all steps have required fields and valid tools."""
        for step in plan:
            if not isinstance(step, dict):
                return False
            tool_name = step.get("tool_name", "")
            if not tool_name or tool_name not in self._registry.tool_names:
                return False
            # Check that required params are present
            tool_def = self._registry.get_definition(tool_name)
            if tool_def:
                required = tool_def.parameters.get("required", [])
                tool_args = step.get("tool_args", {})
                for key in required:
                    if key not in tool_args or not tool_args[key]:
                        return False
        return True

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
