"""DeepSeek API client with health tracking and graceful degradation."""
from __future__ import annotations
import time
import logging
import httpx
from pathfinder.shared.config import get_settings
from pathfinder.shared.infrastructure.llm_health import llm_health, LLMStatus

logger = logging.getLogger(__name__)


class DeepSeekUnavailableError(Exception):
    """Raised when DeepSeek is unavailable and no fallback exists."""


class DeepSeekClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.deepseek_api_key
        self._base_url = settings.deepseek_base_url.rstrip("/")
        self._model = settings.deepseek_model
        self._timeout = settings.deepseek_timeout_seconds
        self._client: httpx.AsyncClient | None = None
        self._api_configured = bool(self._api_key and self._api_key != "sk-your-key-here")

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=float(self._timeout),
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
        return self._client

    async def chat_completion(
        self, *, system_prompt: str, user_prompt: str,
        temperature: float = 0.3, response_format: dict | None = None,
        fallback_on_unavailable: bool = True,
    ) -> "LLMResponse":
        if not self._api_configured:
            if fallback_on_unavailable:
                logger.info("DeepSeek API key not configured — using fallback")
                return LLMResponse(content="", tokens_used=0, model="none", latency_ms=0)
            raise DeepSeekUnavailableError("DeepSeek API key not configured")

        if llm_health.status == LLMStatus.UNAVAILABLE and fallback_on_unavailable:
            logger.warning("DeepSeek circuit breaker open — using fallback")
            return LLMResponse(content="", tokens_used=0, model="none", latency_ms=0)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        body: dict = {
            "model": self._model, "messages": messages,
            "temperature": temperature, "max_tokens": 4096,
        }
        if response_format:
            body["response_format"] = response_format

        start = time.monotonic()
        try:
            client = await self._get_client()
            resp = await client.post(f"{self._base_url}/v1/chat/completions", json=body)
            resp.raise_for_status()
            data = resp.json()
            latency_ms = int((time.monotonic() - start) * 1000)
            llm_health.record_success()

            choice = data["choices"][0]
            return LLMResponse(
                content=choice["message"]["content"],
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
                model=data.get("model", self._model),
                latency_ms=latency_ms,
            )
        except Exception as e:
            llm_health.record_failure(str(e)[:200])
            if fallback_on_unavailable:
                logger.warning(f"DeepSeek call failed (fallback mode): {str(e)[:120]}")
                return LLMResponse(content="", tokens_used=0, model="none", latency_ms=0)
            raise DeepSeekUnavailableError(str(e)) from e

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding using local sentence-transformers model.
        Falls back to DeepSeek API if available, but primary path is local."""
        # Use local embedding model (primary)
        try:
            from pathfinder.shared.infrastructure.embedding_service import generate_embedding as local_embed
            import asyncio as _asyncio
            loop = _asyncio.get_running_loop()
            result = await loop.run_in_executor(None, local_embed, text)
            if result and not all(v == 0.0 for v in result):
                return result
        except Exception:
            pass  # Fall through to DeepSeek API attempt

        # DeepSeek API fallback (if local model unavailable)
        if self._api_configured and llm_health.status != LLMStatus.UNAVAILABLE:
            try:
                client = await self._get_client()
                resp = await client.post(
                    f"{self._base_url}/v1/embeddings",
                    json={"model": "deepseek-embed", "input": text[:8000]},
                )
                resp.raise_for_status()
                data = resp.json()
                llm_health.record_success()
                return data["data"][0]["embedding"]
            except Exception as e:
                llm_health.record_failure(str(e)[:200])
                logger.warning(f"DeepSeek embedding failed: {str(e)[:120]}")

        # Last resort: zero vector
        from pathfinder.shared.infrastructure.embedding_service import VECTOR_DIM
        return [0.0] * VECTOR_DIM

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


class LLMResponse:
    def __init__(self, content: str, tokens_used: int, model: str, latency_ms: int) -> None:
        self.content = content
        self.tokens_used = tokens_used
        self.model = model
        self.latency_ms = latency_ms
