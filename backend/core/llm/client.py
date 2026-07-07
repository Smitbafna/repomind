from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResponse:
    """Response from an LLM call."""

    content: str
    model: str = ""
    usage: dict = None


class LLMClient(ABC):
    """Abstract interface for LLM clients.

    Every LLM implementation must expose a ``generate`` method
    that takes a system prompt and user prompt and returns text.
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