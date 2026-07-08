from __future__ import annotations

import logging

from backend.core.llm.client import LLMProvider
from backend.config.settings import get_settings

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """Factory for creating LLM providers.

    Automatically selects the provider based on the ``LLM_PROVIDER``
    environment variable. No service outside this factory should know
    which provider is being used.
    """

    _instances: dict[str, LLMProvider] = {}

    @classmethod
    def get_provider(cls) -> LLMProvider:
        """Get the LLM provider based on configuration.

        Returns:
            An ``LLMProvider`` instance.

        Raises:
            ValueError: If the configured provider is unknown.
        """
        settings = get_settings()
        provider_name = settings.llm_provider.lower().strip()

        if provider_name in cls._instances:
            return cls._instances[provider_name]

        provider = cls._create_provider(provider_name)
        cls._instances[provider_name] = provider
        return provider

    @classmethod
    def _create_provider(cls, name: str) -> LLMProvider:
        """Create a provider instance by name."""
        if name == "ollama":
            from backend.core.llm.providers.ollama import OllamaProvider
            return OllamaProvider()
        elif name == "gemini":
            from backend.core.llm.providers.gemini import GeminiProvider
            return GeminiProvider()
        elif name == "openai":
            from backend.core.llm.providers.openai import OpenAIProvider
            return OpenAIProvider()
        else:
            raise ValueError(
                f"Unknown LLM provider: '{name}'. "
                f"Supported: ollama, gemini, openai"
            )

    @classmethod
    def register_provider(cls, name: str, provider: LLMProvider) -> None:
        """Register a custom provider (for extensibility).

        Args:
            name: The provider name.
            provider: The provider instance.
        """
        cls._instances[name] = provider


def get_llm_provider() -> LLMProvider:
    """Convenience function to get the configured LLM provider.

    Returns:
        An ``LLMProvider`` instance.
    """
    return LLMProviderFactory.get_provider()