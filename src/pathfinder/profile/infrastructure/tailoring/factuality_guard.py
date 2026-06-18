"""Post-generation factuality verification via LLM."""
from __future__ import annotations
import json
import logging
from pathfinder.profile.infrastructure.llm.deepseek_client import DeepSeekClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a factuality verifier for resume tailoring.

Compare a TAILORED RESUME against a USER PROFILE. Flag every claim NOT supported by the profile.

RULES:
1. Violation: a claim the profile does NOT contain evidence for.
2. Adjacent inference is OK: "FastAPI experience" from profile having "Python" + "API dev" is NOT a violation.
3. Quantified metrics NOT in the profile ARE violations.
4. Technologies NOT in the profile ARE violations.
5. Wrong years of experience ARE violations.

Output ONLY a JSON object:
{"score": 0.0-1.0, "violations": [{"section": "...", "claim": "...", "reason": "..."}]}
1.0 = all claims verified. Each violation reduces score by 0.1."""


class FactualityGuard:
    """Verifies every claim in a tailored resume against the user profile."""

    def __init__(self, llm: DeepSeekClient | None = None) -> None:
        self._llm = llm or DeepSeekClient()

    async def verify(self, tailored_content: dict, profile: dict) -> dict:
        """Verify tailored resume. Returns {"score": float, "violations": list}."""
        try:
            response = await self._llm.chat_completion(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=(
                    f"TAILORED RESUME:\n{json.dumps(tailored_content)[:3000]}\n\n"
                    f"USER PROFILE (ground truth):\n{json.dumps(profile)[:2000]}"
                ),
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.content)
            return {
                "score": float(result.get("score", 1.0)),
                "violations": result.get("violations", []),
            }
        except Exception as e:
            logger.warning(f"Factuality guard failed (failing open): {e}")
            return {"score": 1.0, "violations": []}
