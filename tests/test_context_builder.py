from __future__ import annotations

import pytest

from backend.core.query.context_builder import ContextBuilder
from backend.core.retrieval.retriever import RetrievalResult


class TestContextBuilder:
    """Test suite for the context builder."""

    def setup_method(self) -> None:
        self.builder = ContextBuilder(max_tokens=1000)

    def test_build_context_empty(self) -> None:
        context = self.builder.build_context([])
        assert context == ""

    def test_build_context_single_result(self) -> None:
        results = [
            RetrievalResult(
                content="def hello(): pass",
                score=0.9,
                document_type="function",
                file="main.py",
                symbol="hello",
                line_start="1",
                line_end="2",
            ),
        ]
        context = self.builder.build_context(results)
        assert "def hello(): pass" in context
        assert "main.py:hello" in context

    def test_build_context_deduplication(self) -> None:
        results = [
            RetrievalResult(content="def hello(): pass", score=0.9, file="a.py"),
            RetrievalResult(content="def hello(): pass", score=0.8, file="b.py"),
        ]
        context = self.builder.build_context(results)
        # Only one occurrence should appear.
        count = context.count("def hello(): pass")
        assert count == 1

    def test_build_context_respects_max_results(self) -> None:
        results = [
            RetrievalResult(content=f"content_{i}", score=1.0 - i * 0.1)
            for i in range(20)
        ]
        context = self.builder.build_context(results, max_results=5)
        # Should have at most 5 sections.
        section_count = context.count("=== From")
        assert section_count <= 5

    def test_build_context_with_sources(self) -> None:
        results = [
            RetrievalResult(
                content="class MyClass: pass",
                score=0.95,
                document_type="class",
                file="models.py",
                symbol="MyClass",
                line_start="1",
                line_end="2",
            ),
        ]
        context, sources = self.builder.build_context_with_sources(results)
        assert len(sources) == 1
        assert sources[0]["file"] == "models.py"
        assert sources[0]["symbol"] == "MyClass"
        assert "class MyClass: pass" in context

    def test_format_section_with_symbol(self) -> None:
        result = RetrievalResult(
            content="code here",
            score=0.5,
            file="app.py",
            symbol="MyClass.my_method",
        )
        section = ContextBuilder._format_section(result)
        assert "app.py:MyClass.my_method" in section
        assert "code here" in section

    def test_format_section_with_line(self) -> None:
        result = RetrievalResult(
            content="code here",
            score=0.5,
            file="app.py",
            symbol="MyClass",
            line_start="42",
        )
        section = ContextBuilder._format_section(result)
        assert "line 42" in section