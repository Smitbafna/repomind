from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

import httpx

from backend.config.settings import get_settings
from backend.core.llm.client import ChatMessage, LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """LLM provider that uses Ollama's chat API.

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
        """Generate a response using Ollama's chat API."""
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt),
        ]
        return await self.chat(messages, temperature=temperature, max_tokens=max_tokens)

    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Send a chat conversation to Ollama."""
        url = f"{self._base_url}/api/chat"
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": m.role, "content": m.content} for m in messages
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

    async def stream(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """Stream a response from Ollama token by token."""
        url = f"{self._base_url}/api/chat"
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": m.role, "content": m.content} for m in messages
            ],
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk = json.loads(line)
                            token = chunk.get("message", {}).get("content", "")
                            if token:
                                yield token
                        except json.JSONDecodeError:
                            continue
        except httpx.RequestError as exc:
            raise ConnectionError(
                f"Failed to connect to Ollama at {self._base_url}: {exc}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Ollama chat API returned {exc.response.status_code}: {exc.response.text}"
            ) from exc


# Backwards compatibility alias
OllamaClient = OllamaProvider