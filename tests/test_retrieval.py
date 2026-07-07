from __future__ import annotations

import pytest

from backend.core.retrieval.keyword_retriever import KeywordRetriever
from backend.core.retrieval.retriever import BaseRetriever, RetrievalResult


class TestRetrievalModels:
    """Test suite for retrieval models and interfaces."""

    def test_retrieval_result_creation(self) -> None:
        result = RetrievalResult(
            content="test content",
            score=0.95,
            document_type="class",
            file="main.py",
            symbol="MyClass",
            line_start="10",
            line_end="20",
        )
        assert result.content == "test content"
        assert result.score == 0.95
        assert result.document_type == "class"
        assert result.file == "main.py"
        assert result.symbol == "MyClass"

    def test_retrieval_result_defaults(self) -> None:
        result = RetrievalResult(content="test", score=0.5)
        assert result.document_type == ""
        assert result.file == ""
        assert result.symbol == ""
        assert result.line_start == ""
        assert result.line_end == ""

    def test_base_retriever_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            BaseRetriever()  # type: ignore[abstract]


class TestKeywordRetriever:
    """Test suite for the keyword retriever tokenizer."""

    def test_tokenize(self) -> None:
        tokens = KeywordRetriever._tokenize("Hello World! This is a test_function.")
        assert "hello" in tokens
        assert "world" in tokens
        assert "test_function" in tokens
        assert "a" not in tokens  # Filtered by length > 1

    def test_tokenize_empty(self) -> None:
        tokens = KeywordRetriever._tokenize("")
        assert tokens == []

    def test_tokenize_special_chars(self) -> None:
        tokens = KeywordRetriever._tokenize("foo.bar() -> baz_qux")
        assert "foo" in tokens
        assert "bar" in tokens
        assert "baz_qux" in tokens