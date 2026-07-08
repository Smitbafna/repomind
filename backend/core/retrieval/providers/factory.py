from __future__ import annotations

import logging

from backend.core.retrieval.providers.embedding_provider import EmbeddingProvider
from backend.config.settings import get_settings

logger = logging.getLogger(__name__)


class EmbeddingProviderFactory:
    """Factory for creating embedding providers.

    Automatically selects the provider based on the ``EMBEDDING_PROVIDER``
    environment variable. New providers can be registered without modifying
    existing code.
    """

    _providers: dict[str, type[EmbeddingProvider]] = {}
    _instances: dict[str, EmbeddingProvider] = {}

    @classmethod
    def register(cls, name: str, provider_cls: type[EmbeddingProvider]) -> None:
        """Register a new embedding provider class.

        Args:
            name: The provider name (e.g. "ollama", "gemini").
            provider_cls: The provider class.
        """
        cls._providers[name] = provider_cls

    @classmethod
    def get_provider(cls, name: str | None = None) -> EmbeddingProvider:
        """Get an embedding provider instance.

        Args:
            name: Provider name. If None, uses ``EMBEDDING_PROVIDER`` env var.

        Returns:
            An ``EmbeddingProvider`` instance.

        Raises:
            ValueError: If the provider is unknown.
        """
        if name is None:
            settings = get_settings()
            name = settings.embedding_provider.lower().strip()

        if name in cls._instances:
            return cls._instances[name]

        if name in cls._providers:
            provider_cls = cls._providers[name]
            instance = provider_cls()
            cls._instances[name] = instance
            return instance

        # Fall back to built-in providers
        if name == "ollama":
            from backend.core.retrieval.providers.ollama_embeddings import OllamaEmbeddingProvider
            instance = OllamaEmbeddingProvider()
        elif name == "gemini":
            from backend.core.retrieval.providers.gemini_embeddings import GeminiEmbeddingProvider
            instance = GeminiEmbeddingProvider()
        else:
            raise ValueError(
                f"Unknown embedding provider: '{name}'. "
                f"Supported: ollama, gemini. "
                f"Register custom providers with EmbeddingProviderFactory.register()"
            )

        cls._instances[name] = instance
        return instance


def get_embedding_provider(name: str | None = None) -> EmbeddingProvider:
    """Convenience function to get the configured embedding provider.

    Args:
        name: Optional provider name override.

    Returns:
        An ``EmbeddingProvider`` instance.
    """
    return EmbeddingProviderFactory.get_provider(name)