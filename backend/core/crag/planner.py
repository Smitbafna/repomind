from __future__ import annotations

import logging

from backend.core.crag.models import CorrectiveAction, EvaluationResult, RetrievalState
from backend.core.query.analyzer import QueryAnalyzer

logger = logging.getLogger(__name__)


class CorrectivePlanner:
    """Plans corrective actions when retrieval quality is insufficient.

    If confidence is high → generate answer.
    If confidence is low → choose corrective actions.
    """

    def __init__(self, analyzer: QueryAnalyzer | None = None) -> None:
        self._analyzer = analyzer or QueryAnalyzer()

    def plan(
        self,
        state: RetrievalState,
        evaluation: EvaluationResult,
    ) -> list[CorrectiveAction]:
        """Plan next steps based on evaluation.

        Args:
            state: Current retrieval state.
            evaluation: Evaluation result.

        Returns:
            List of recommended corrective actions.
        """
        # If confidence is high, generate answer.
        if evaluation.confidence >= 0.7:
            return [CorrectiveAction.GENERATE_ANSWER]

        # If max attempts reached, must generate answer.
        if state.attempt_number >= state.max_attempts:
            return [CorrectiveAction.GENERATE_ANSWER]

        # Use recommended actions from evaluation.
        return evaluation.recommended_actions

    def should_generate_answer(self, evaluation: EvaluationResult) -> bool:
        """Check if we should generate an answer."""
        return evaluation.confidence >= 0.7

    def get_next_attempt_params(
        self,
        state: RetrievalState,
        action: CorrectiveAction,
    ) -> dict:
        """Get parameters for the next retrieval attempt.

        Args:
            state: Current state.
            action: The corrective action to take.

        Returns:
            Dict with parameters for the retriever.
        """
        params: dict = {
            "top_k": 5,
            "max_depth": 2,
            "max_nodes": 20,
        }

        if action == CorrectiveAction.INCREASE_TOP_K:
            params["top_k"] = 10
        elif action == CorrectiveAction.INCREASE_DEPTH:
            params["max_depth"] = 4
        elif action == CorrectiveAction.EXPAND_GRAPH:
            params["max_nodes"] = 50
        elif action == CorrectiveAction.RUN_HYBRID:
            params["top_k"] = 10

        return params