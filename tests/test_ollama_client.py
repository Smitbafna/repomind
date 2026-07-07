from __future__ import annotations

import pytest

from backend.core.llm.client import LLMClient, LLMResponse


class TestLLMModels:
    """Test suite for LLM models and interfaces."""

    def test_llm_response_creation(self) -> None:
        response = LLMResponse(content="Hello, world!", model="llama3.2")
        assert response.content == "Hello, world!"
        assert response.model == "llama3.2"

    def test_llm_response_defaults(self) -> None:
        response = LLMResponse(content="test")
        assert response.content == "test"
        assert response.model == ""
        assert response.usage is None

    def test_base_client_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            LLMClient()  # type: ignore[abstract]