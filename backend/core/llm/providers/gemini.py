from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from backend.core.llm.client import ChatMessage, LLMProvider, LLMResponse
from backend.config.settings import get_settings

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """LLM provider that uses Google's Generative AI SDK."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._api_key = self._settings.gemini_api_key
        self._model_name = "gemini-2.0-flash"  # Default model
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy-import and initialize the Google Generative AI client."""
        if self._client is not None:
            return self._client
        try:
            import google.generativeai as genai  # type: ignore[import-untyped]
            genai.configure(api_key=self._api_key)
            self._client = genai
            return self._client
        except ImportError:
            raise RuntimeError(
                "google-generativeai package is not installed. "
                "Install it with: pip install google-generativeai"
            )

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Generate a response using Gemini."""
        messages = [
            ChatMessage(role="user", content=f"{system_prompt}\n\n{user_prompt}"),
        ]
        return await self.chat(messages, temperature=temperature, max_tokens=max_tokens)

    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Send a chat conversation to Gemini."""
        genai = self._get_client()
        model = genai.GenerativeModel(self._model_name)

        # Build contents from messages
        contents = []
        system_instruction = None
        for m in messages:
            if m.role == "system":
                system_instruction = m.content
            elif m.role == "user":
                contents.append({"role": "user", "parts": [m.content]})
            elif m.role == "assistant":
                contents.append({"role": "model", "parts": [m.content]})

        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        try:
            chat = model.start_chat(history=contents[:-1] if contents else [])
            last_content = contents[-1]["parts"][0] if contents else ""
            response = chat.send_message(
                last_content,
                generation_config=generation_config,
            )
            return LLMResponse(
                content=response.text,
                model=self._model_name,
                usage={
                    "prompt_tokens": getattr(response, "usage_metadata", {}).get("prompt_token_count", 0),
                    "completion_tokens": getattr(response, "usage_metadata", {}).get("candidates_token_count", 0),
                },
            )
        except Exception as exc:
            raise RuntimeError(f"Gemini API error: {exc}") from exc

    async def stream(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """Stream a response from Gemini token by token."""
        genai = self._get_client()
        model = genai.GenerativeModel(self._model_name)

        contents = []
        for m in messages:
            if m.role == "user":
                contents.append({"role": "user", "parts": [m.content]})
            elif m.role == "assistant":
                contents.append({"role": "model", "parts": [m.content]})

        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        try:
            response = model.generate_content(
                contents,
                generation_config=generation_config,
                stream=True,
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as exc:
            raise RuntimeError(f"Gemini streaming error: {exc}") from exc