from __future__ import annotations

import logging

from backend.core.crag.evaluator import RetrievalEvaluator
from backend.core.crag.graph import CRAGGraph
from backend.core.crag.models import RetrievalState
from backend.core.graphrag.service import GraphRAGService

logger = logging.getLogger(__name__)


class CRAGService:
    """Orchestrates CRAG operations.

    Provides:
        - Query endpoint with iterative retrieval
        - Evaluation endpoint for retrieval quality
        - Retrieval-only endpoint for debugging
    """

    def __init__(
        self,
        crag_graph: CRAGGraph | None = None,
        evaluator: RetrievalEvaluator | None = None,
        graphrag_service: GraphRAGService | None = None,
    ) -> None:
        self._crag_graph = crag_graph or CRAGGraph()
        self._evaluator = evaluator or RetrievalEvaluator()
        self._graphrag_service = graphrag_service

    async def query(
        self,
        repository_id: str,
        question: str,
        max_attempts: int = 3,
    ) -> RetrievalState:
        """Run CRAG query with iterative retrieval.

        Args:
            repository_id: The repository to query.
            question: The user's question.
            max_attempts: Maximum retrieval attempts.

        Returns:
            Final retrieval state with answer.
        """
        state = RetrievalState(
            repository_id=repository_id,
            question=question,
            max_attempts=max_attempts,
        )
        return await self._crag_graph.run(state)

    async def evaluate(
        self,
        repository_id: str,
        question: str,
    ) -> dict:
        """Evaluate retrieval quality without generating answer.

        Args:
            repository_id: The repository.
            question: The user's question.

        Returns:
            Evaluation metrics and recommendations.
        """
        state = RetrievalState(
            repository_id=repository_id,
            question=question,
        )

        # Run initial retrieval.
        from backend.core.crag.retriever import CRAGRetriever
        from backend.core.crag.models import CorrectiveAction

        retriever = CRAGRetriever()
        await retriever.retrieve(state, CorrectiveAction.RUN_HYBRID)

        # Evaluate.
        evaluation = self._evaluator.evaluate(state)

        return {
            "confidence": evaluation.confidence,
            "coverage": evaluation.coverage,
            "redundancy": evaluation.redundancy,
            "evidence_diversity": evaluation.evidence_diversity,
            "missing_information": evaluation.missing_information,
            "recommended_actions": [a.value for a in evaluation.recommended_actions],
        }

    async def retrieve_only(
        self,
        repository_id: str,
        question: str,
        max_attempts: int = 3,
    ) -> dict:
        """Run retrieval only, return history without answer.

        Args:
            repository_id: The repository.
            question: The user's question.
            max_attempts: Maximum retrieval attempts.

        Returns:
            Retrieval history and scores.
        """
        state = RetrievalState(
            repository_id=repository_id,
            question=question,
            max_attempts=max_attempts,
        )

        # Run initial retrieval.
        from backend.core.crag.retriever import CRAGRetriever
        from backend.core.crag.models import CorrectiveAction

        retriever = CRAGRetriever()
        await retriever.retrieve(state, CorrectiveAction.RUN_HYBRID)

        # Evaluate.
        evaluation = self._evaluator.evaluate(state)

        return {
            "iterations": state.attempt_number,
            "retrieval_history": [
                {
                    "attempt": h.attempt_number,
                    "tool": h.tool,
                    "result_count": h.result_count,
                    "context_size": h.context_size,
                    "score": h.score,
                }
                for h in state.retrieval_history
            ],
            "confidence": evaluation.confidence,
            "missing_information": evaluation.missing_information,
        }