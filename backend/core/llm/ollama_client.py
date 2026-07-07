from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from backend.config.settings import get_settings
from backend.core.llm.client import LLMClient, LLMResponse

logger = logging.getLogger(__name__)


class OllamaClient(LLMClient):
    """LLM client that uses Ollama's chat API.

    Supports configurable models and streaming via the
    ``/api/chat`` endpoint.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._base_url = self._settings.ollama_base_url.rstrip("/")
        self._model = self._settings.ollama_chat_model
        self._timeout = self._settings.ollama_timeout_seconds

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Generate a response using Ollama's chat API.

        Args:
            system_prompt: The system-level instruction prompt.
            user_prompt: The user message / question.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in the response.

        Returns:
            An ``LLMResponse`` with the generated text.

        Raises:
            ConnectionError: If Ollama is unreachable.
            RuntimeError: If the API returns an error.
        """
        url = f"{self._base_url}/api/chat"
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.RequestError as exc:
            raise ConnectionError(
                f"Failed to connect to Ollama at {self._base_url}: {exc}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Ollama chat API returned {exc.response.status_code}: {exc.response.text}"
            ) from exc

        content = data.get("message", {}).get("content", "")
        if not content:
            raise RuntimeError(
                f"Ollama returned empty response for model '{self._model}'"
            )

        return LLMResponse(
            content=content,
            model=self._model,
        )