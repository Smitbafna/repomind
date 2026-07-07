from __future__ import annotations

import pytest

from backend.core.crag.evaluator import RetrievalEvaluator
from backend.core.crag.models import (
    CorrectiveAction,
    EvaluationResult,
    RetrievalHistory,
    RetrievalState,
)
from backend.core.crag.planner import CorrectivePlanner


class TestRetrievalEvaluator:
    """Test suite for retrieval evaluator."""

    def setup_method(self) -> None:
        self.evaluator = RetrievalEvaluator()

    def test_evaluate_empty_state(self) -> None:
        state = RetrievalState()
        result = self.evaluator.evaluate(state)
        assert result.confidence == 0.1  # Context adequacy gives 0.1
        assert result.coverage == 0.0
        assert len(result.recommended_actions) > 0

    def test_evaluate_high_confidence(self) -> None:
        state = RetrievalState(
            question="test question",
            retrieved_documents=[
                {"content": "test question answer with more keywords", "score": 0.9},
                {"content": "test question answer with more content", "score": 0.8},
            ],
            context="test question answer with more keywords and content",
        )
        result = self.evaluator.evaluate(state)
        assert result.confidence > 0.3  # Reasonable confidence with good coverage

    def test_evaluate_low_confidence(self) -> None:
        state = RetrievalState(
            question="test question",
            retrieved_documents=[],
            context="",
        )
        result = self.evaluator.evaluate(state)
        assert result.confidence < 0.2  # Low confidence with no evidence
        assert len(result.recommended_actions) > 0

    def test_evaluate_with_graph_results(self) -> None:
        state = RetrievalState(
            question="test question",
            graph_results=[{"symbol": "test", "score": 0.8}],
        )
        result = self.evaluator.evaluate(state)
        assert result.evidence_diversity > 0

    def test_evaluate_with_git_results(self) -> None:
        state = RetrievalState(
            question="when was test created",
            git_results=[{"hash": "abc123", "commit_message": "test commit"}],
        )
        result = self.evaluator.evaluate(state)
        assert "git history" not in result.missing_information

    def test_evaluate_missing_code(self) -> None:
        state = RetrievalState(
            question="show me the code function",
            retrieved_documents=[{"content": "some text", "score": 0.5}],
        )
        result = self.evaluator.evaluate(state)
        # "code" in question triggers missing code check
        # Evidence doesn't have code keywords, so it's missing
        assert "code implementation details" in result.missing_information

    def test_evaluate_with_code_content(self) -> None:
        state = RetrievalState(
            question="show me the function",
            retrieved_documents=[{"content": "def my_function(): pass", "score": 0.5}],
        )
        result = self.evaluator.evaluate(state)
        # Evidence has code keyword "def", so not missing
        assert "code implementation details" not in result.missing_information


class TestCorrectivePlanner:
    """Test suite for corrective planner."""

    def setup_method(self) -> None:
        self.planner = CorrectivePlanner()

    def test_plan_high_confidence(self) -> None:
        state = RetrievalState(attempt_number=1, max_attempts=3)
        evaluation = EvaluationResult(confidence=0.8, coverage=0.7, redundancy=0.1, evidence_diversity=0.5)
        actions = self.planner.plan(state, evaluation)
        assert actions == [CorrectiveAction.GENERATE_ANSWER]

    def test_plan_low_confidence(self) -> None:
        state = RetrievalState(attempt_number=1, max_attempts=3)
        evaluation = EvaluationResult(
            confidence=0.3,
            coverage=0.2,
            redundancy=0.1,
            evidence_diversity=0.1,
            missing_information=["code implementation details"],
            recommended_actions=[CorrectiveAction.INCREASE_TOP_K],
        )
        actions = self.planner.plan(state, evaluation)
        assert CorrectiveAction.INCREASE_TOP_K in actions

    def test_plan_max_attempts_reached(self) -> None:
        state = RetrievalState(attempt_number=3, max_attempts=3)
        evaluation = EvaluationResult(confidence=0.3, coverage=0.2, redundancy=0.1, evidence_diversity=0.1)
        actions = self.planner.plan(state, evaluation)
        assert actions == [CorrectiveAction.GENERATE_ANSWER]

    def test_get_next_attempt_params(self) -> None:
        state = RetrievalState()
        params = self.planner.get_next_attempt_params(state, CorrectiveAction.INCREASE_TOP_K)
        assert params["top_k"] == 10

        params = self.planner.get_next_attempt_params(state, CorrectiveAction.EXPAND_GRAPH)
        assert params["max_nodes"] == 50


class TestRetrievalState:
    """Test suite for retrieval state."""

    def test_default_state(self) -> None:
        state = RetrievalState()
        assert state.attempt_number == 0
        assert state.max_attempts == 3
        assert state.retrieved_documents == []
        assert state.graph_results == []

    def test_custom_state(self) -> None:
        state = RetrievalState(
            repository_id="test-repo",
            question="test question",
            max_attempts=5,
        )
        assert state.repository_id == "test-repo"
        assert state.max_attempts == 5


class TestRetrievalHistory:
    """Test suite for retrieval history."""

    def test_history_creation(self) -> None:
        history = RetrievalHistory(
            attempt_number=1,
            tool="hybrid",
            result_count=5,
            context_size=1000,
            score=0.85,
        )
        assert history.attempt_number == 1
        assert history.tool == "hybrid"


class TestCorrectiveAction:
    """Test suite for corrective action enum."""

    def test_action_values(self) -> None:
        assert CorrectiveAction.GENERATE_ANSWER.value == "generate_answer"
        assert CorrectiveAction.EXPAND_GRAPH.value == "expand_graph"
        assert CorrectiveAction.RUN_HYBRID.value == "run_hybrid"