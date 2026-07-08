from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from backend.core.llm.client import ChatMessage, LLMProvider, LLMResponse
from backend.config.settings import get_settings

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """LLM provider that uses the OpenAI SDK."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._api_key = self._settings.openai_api_key
        self._model = "gpt-4o-mini"  # Default model
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy-import and initialize the OpenAI client."""
        if self._client is not None:
            return self._client
        try:
            from openai import AsyncOpenAI  # type: ignore[import-untyped]
            self._client = AsyncOpenAI(api_key=self._api_key)
            return self._client
        except ImportError:
            raise RuntimeError(
                "openai package is not installed. "
                "Install it with: pip install openai"
            )

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Generate a response using OpenAI."""
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
        """Send a chat conversation to OpenAI."""
        client = self._get_client()
        openai_messages = [
            {"role": m.role, "content": m.content} for m in messages
        ]

        try:
            response = await client.chat.completions.create(
                model=self._model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            choice = response.choices[0]
            return LLMResponse(
                content=choice.message.content or "",
                model=self._model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                } if response.usage else {},
            )
        except Exception as exc:
            raise RuntimeError(f"OpenAI API error: {exc}") from exc

    async def stream(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """Stream a response from OpenAI token by token."""
        client = self._get_client()
        openai_messages = [
            {"role": m.role, "content": m.content} for m in messages
        ]

        try:
            stream = await client.chat.completions.create(
                model=self._model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as exc:
            raise RuntimeError(f"OpenAI streaming error: {exc}") from exc