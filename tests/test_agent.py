from __future__ import annotations

import pytest

from backend.core.agent.planner import Planner
from backend.core.agent.state import QueryState
from backend.core.agent.tools import (
    HybridRetrieverTool,
    KeywordRetrieverTool,
    SemanticRetrieverTool,
)


class TestPlanner:
    """Test suite for the planner."""

    def setup_method(self) -> None:
        self.planner = Planner()

    def test_general_question_uses_hybrid(self) -> None:
        plan = self.planner.plan("What does the Parser class do?")
        assert "hybrid_retriever" in plan.selected_tools
        assert "relationship_retriever" in plan.selected_tools

    def test_history_question_includes_git(self) -> None:
        plan = self.planner.plan("Who introduced JWT?")
        assert "git_history_tool" in plan.selected_tools
        assert "blame_tool" in plan.selected_tools

    def test_history_question_when_created(self) -> None:
        plan = self.planner.plan("When was AuthService created?")
        assert "git_history_tool" in plan.selected_tools

    def test_blame_question(self) -> None:
        plan = self.planner.plan("Who last edited this file?")
        assert "git_history_tool" in plan.selected_tools
        assert "blame_tool" in plan.selected_tools

    def test_relationship_question(self) -> None:
        plan = self.planner.plan("What imports does this class use?")
        assert "relationship_retriever" in plan.selected_tools

    def test_architecture_question(self) -> None:
        plan = self.planner.plan("Explain the architecture of this project")
        assert "relationship_retriever" in plan.selected_tools

    def test_vector_strategy_question(self) -> None:
        plan = self.planner.plan("Explain authentication flow")
        assert "hybrid_retriever" in plan.selected_tools or "semantic_retriever" in plan.selected_tools

    def test_timeline_question(self) -> None:
        plan = self.planner.plan("Show authentication changes over time")
        assert "git_history_tool" in plan.selected_tools

    def test_plan_has_reasoning(self) -> None:
        plan = self.planner.plan("How does the API work?")
        assert plan.reasoning
        assert len(plan.reasoning) > 0

    def test_plan_deduplicates_tools(self) -> None:
        plan = self.planner.plan("Who introduced JWT?")
        # git_history_tool should only appear once
        assert plan.selected_tools.count("git_history_tool") == 1


class TestQueryState:
    """Test suite for the query state."""

    def test_default_state(self) -> None:
        state = QueryState()
        assert state.question == ""
        assert state.repository_id == ""
        assert state.errors == []
        assert state.tool_history == []

    def test_custom_state(self) -> None:
        state = QueryState(
            repository_id="test-id",
            question="What does this do?",
            intent="explain_code",
            keywords=["Parser", "class"],
        )
        assert state.repository_id == "test-id"
        assert state.question == "What does this do?"
        assert state.intent == "explain_code"
        assert "Parser" in state.keywords


class TestSemanticRetrieverUtils:
    """Test suite for semantic retriever utility methods."""

    def test_to_dicts(self) -> None:
        from backend.core.retrieval.retriever import RetrievalResult

        results = [
            RetrievalResult(
                content="def hello(): pass",
                score=0.95,
                document_type="function",
                file="main.py",
                symbol="hello",
                line_start="1",
                line_end="2",
            ),
        ]
        dicts = SemanticRetrieverTool._to_dicts(results)
        assert len(dicts) == 1
        assert dicts[0]["content"] == "def hello(): pass"
        assert dicts[0]["score"] == 0.95
        assert dicts[0]["file"] == "main.py"

    def test_to_dicts_empty(self) -> None:
        assert SemanticRetrieverTool._to_dicts([]) == []


class TestSemanticRetrieverTool:
    """Test suite for semantic retriever tool."""

    def test_execute_empty_state(self) -> None:
        # Use a mock retriever to avoid requiring Qdrant
        from unittest.mock import AsyncMock
        mock_retriever = AsyncMock()
        mock_retriever.retrieve = AsyncMock(return_value=[])
        tool = SemanticRetrieverTool(retriever=mock_retriever)
        state = QueryState(question="test")
        import asyncio
        result = asyncio.run(tool.execute(state))
        assert result.question == "test"
        assert hasattr(result, "retrieved_documents")
        assert result.retrieved_documents == []


class TestHybridRetrieverTool:
    """Test suite for hybrid retriever tool."""

    def test_execute_empty_state(self) -> None:
        from unittest.mock import AsyncMock
        mock_retriever = AsyncMock()
        mock_retriever.retrieve = AsyncMock(return_value=[])
        tool = HybridRetrieverTool(retriever=mock_retriever)
        state = QueryState(question="test")
        import asyncio
        result = asyncio.run(tool.execute(state))
        assert result.question == "test"
        assert hasattr(result, "retrieved_documents")


class TestKeywordRetrieverTool:
    """Test suite for keyword retriever tool."""

    def test_execute_empty_state(self) -> None:
        from unittest.mock import AsyncMock
        mock_retriever = AsyncMock()
        mock_retriever.retrieve = AsyncMock(return_value=[])
        tool = KeywordRetrieverTool(retriever=mock_retriever)
        state = QueryState(question="test")
        import asyncio
        result = asyncio.run(tool.execute(state))
        assert result.question == "test"
        assert hasattr(result, "retrieved_documents")
