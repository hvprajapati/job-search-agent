"""Tests for FactualityGuard."""
import pytest
from unittest.mock import AsyncMock, patch
from pathfinder.profile.infrastructure.tailoring.factuality_guard import FactualityGuard


class TestFactualityGuard:
    @pytest.mark.asyncio
    async def test_clean_content_scores_high(self):
        """Content matching profile should return score >= 0.9."""
        mock_llm = AsyncMock()
        mock_llm.chat_completion.return_value.content = (
            '{"score": 1.0, "violations": []}'
        )
        guard = FactualityGuard(mock_llm)
        result = await guard.verify(
            {"summary": "Python developer with 5 years experience."},
            {"skills": [{"name": "Python", "years": 5}]},
        )
        assert result["score"] >= 0.9
        assert len(result["violations"]) == 0

    @pytest.mark.asyncio
    async def test_fabricated_skill_flagged(self):
        """Claiming a skill not in profile should produce violations."""
        mock_llm = AsyncMock()
        mock_llm.chat_completion.return_value.content = (
            '{"score": 0.8, "violations": ['
            '{"section": "skills", "claim": "Kubernetes", "reason": "Not in profile"}'
            ']}'
        )
        guard = FactualityGuard(mock_llm)
        result = await guard.verify(
            {"skills": ["Python", "Kubernetes"]},
            {"skills": [{"name": "Python"}]},
        )
        assert result["score"] < 1.0
        assert len(result["violations"]) >= 1

    @pytest.mark.asyncio
    async def test_guard_fails_open_on_llm_error(self):
        """When LLM is unavailable, guard returns score=1.0 (fail open)."""
        mock_llm = AsyncMock()
        mock_llm.chat_completion.side_effect = Exception("API timeout")
        guard = FactualityGuard(mock_llm)
        result = await guard.verify({"test": "data"}, {"test": "profile"})
        assert result["score"] == 1.0
        assert len(result["violations"]) == 0

    @pytest.mark.asyncio
    async def test_guard_handles_invalid_json(self):
        """Malformed LLM response should not crash."""
        mock_llm = AsyncMock()
        mock_llm.chat_completion.return_value.content = "not valid json"
        guard = FactualityGuard(mock_llm)
        result = await guard.verify({"test": "data"}, {"test": "profile"})
        assert result["score"] == 1.0  # Fail open
