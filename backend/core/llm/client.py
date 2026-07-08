from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator


@dataclass(frozen=True)
class LLMResponse:
    """Response from an LLM call."""

    content: str
    model: str = ""
    usage: dict | None = None


@dataclass(frozen=True)
class ChatMessage:
    """A single chat message."""
    role: str  # "system", "user", "assistant"
    content: str


class LLMProvider(ABC):
    """Abstract interface for LLM providers.

    Every LLM implementation must expose ``generate``, ``chat``,
    and ``stream`` methods.
    """

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Generate a response from the LLM.

        Args:
            system_prompt: The system-level instruction prompt.
            user_prompt: The user message / question.
            temperature: Sampling temperature (0.0 = deterministic).
            max_tokens: Maximum tokens in the response.

        Returns:
            An ``LLMResponse`` containing the generated text.
        """
        ...

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Send a chat conversation to the LLM.

        Args:
            messages: List of chat messages forming the conversation.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in the response.

        Returns:
            An ``LLMResponse`` containing the generated text.
        """
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """Stream a response from the LLM token by token.

        Args:
            messages: List of chat messages forming the conversation.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in the response.

        Yields:
            Tokens as they are generated.
        """
        ...
        # pylint: disable=unreachable
        yield ""


# Backward compatibility alias
LLMClient = LLMProvider