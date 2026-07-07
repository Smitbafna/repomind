from __future__ import annotations

import pytest

from backend.core.query.analyzer import QueryAnalyzer


class TestQueryAnalyzer:
    """Test suite for the query analyzer."""

    def setup_method(self) -> None:
        self.analyzer = QueryAnalyzer()

    def test_explain_code_intent(self) -> None:
        analysis = self.analyzer.analyze("What does the Parser class do?")
        assert analysis.intent == "explain_code"

    def test_find_function_intent(self) -> None:
        analysis = self.analyzer.analyze("Find the parse_file method")
        assert analysis.intent == "find_function"

    def test_architecture_intent(self) -> None:
        analysis = self.analyzer.analyze("architecture of this project")
        assert analysis.intent == "architecture"

    def test_usage_example_intent(self) -> None:
        analysis = self.analyzer.analyze("How to use the DocumentBuilder class")
        assert analysis.intent == "usage_example"

    def test_implementation_intent(self) -> None:
        analysis = self.analyzer.analyze("implement a new parser")
        assert analysis.intent == "implementation"

    def test_debugging_intent(self) -> None:
        analysis = self.analyzer.analyze("Why does this code fail with an error?")
        assert analysis.intent == "debugging"

    def test_comparison_intent(self) -> None:
        analysis = self.analyzer.analyze("Compare VectorRetriever and KeywordRetriever")
        assert analysis.intent == "comparison"

    def test_general_intent(self) -> None:
        analysis = self.analyzer.analyze("Python programming language features")
        assert analysis.intent == "general"

    def test_keyword_extraction(self) -> None:
        analysis = self.analyzer.analyze("How does the PythonParser handle async functions?")
        assert "PythonParser" in analysis.keywords
        assert "async" in analysis.keywords

    def test_keyword_stop_words_filtered(self) -> None:
        analysis = self.analyzer.analyze("What is a function in this code?")
        # "function" is a stop word
        assert "function" not in analysis.keywords

    def test_file_filter_extraction(self) -> None:
        analysis = self.analyzer.analyze("Find the code in parser.py")
        assert "file" in analysis.filters
        assert analysis.filters["file"] == "parser.py"

    def test_class_filter_extraction(self) -> None:
        analysis = self.analyzer.analyze("Explain the class ParserFactory")
        assert "class" in analysis.filters
        assert analysis.filters["class"] == "ParserFactory"

    def test_retrieval_strategy_explain(self) -> None:
        analysis = self.analyzer.analyze("What does this function do?")
        # "what does" matches explain_code, which uses hybrid strategy
        assert analysis.retrieval_strategy == "hybrid"

    def test_retrieval_strategy_architecture(self) -> None:
        analysis = self.analyzer.analyze("architecture overview of project")
        assert analysis.retrieval_strategy == "keyword"

    def test_retrieval_strategy_find(self) -> None:
        analysis = self.analyzer.analyze("Find the QueryEngine class")
        assert analysis.retrieval_strategy == "hybrid"

    def test_empty_query(self) -> None:
        analysis = self.analyzer.analyze("")
        assert analysis.intent == "general"
        assert analysis.keywords == []
        assert analysis.filters == {}