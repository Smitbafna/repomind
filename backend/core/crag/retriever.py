from __future__ import annotations

import logging

from backend.core.crag.models import CorrectiveAction, RetrievalHistory, RetrievalState
from backend.core.graphrag.context import GraphContextBuilder
from backend.core.graphrag.service import GraphRAGService
from backend.core.query.context_builder import ContextBuilder
from backend.core.retrieval.hybrid_retriever import HybridRetriever
from backend.core.retrieval.vector_retriever import VectorRetriever

logger = logging.getLogger(__name__)


class CRAGRetriever:
    """Performs corrective retrieval based on evaluation.

    Executes retrieval with different strategies based on
    the recommended corrective action.
    """

    def __init__(
        self,
        graphrag_service: GraphRAGService | None = None,
        hybrid_retriever: HybridRetriever | None = None,
        vector_retriever: VectorRetriever | None = None,
        context_builder: ContextBuilder | None = None,
        graph_context_builder: GraphContextBuilder | None = None,
    ) -> None:
        self._graphrag_service = graphrag_service
        self._hybrid_retriever = hybrid_retriever or HybridRetriever()
        self._vector_retriever = vector_retriever or VectorRetriever()
        self._context_builder = context_builder or ContextBuilder()
        self._graph_context_builder = graph_context_builder or GraphContextBuilder()

    async def retrieve(
        self,
        state: RetrievalState,
        action: CorrectiveAction,
    ) -> RetrievalState:
        """Execute retrieval based on the corrective action.

        Args:
            state: Current retrieval state.
            action: The corrective action to take.

        Returns:
            Updated state with new evidence.
        """
        state.attempt_number += 1

        if action == CorrectiveAction.EXPAND_GRAPH and self._graphrag_service:
            await self._run_graphrag(state)
        elif action == CorrectiveAction.RUN_HYBRID:
            await self._run_hybrid(state)
        elif action == CorrectiveAction.RUN_GIT:
            # Git retrieval handled by tool
            pass
        elif action == CorrectiveAction.RUN_RELATIONSHIPS:
            # Relationship retrieval handled by tool
            pass
        elif action == CorrectiveAction.RETRY_SEMANTIC:
            await self._run_semantic(state)
        elif action == CorrectiveAction.INCREASE_TOP_K:
            await self._run_hybrid(state, top_k=10)
        elif action == CorrectiveAction.INCREASE_DEPTH:
            if self._graphrag_service:
                await self._run_graphrag(state, max_depth=4)

        return state

    async def _run_graphrag(
        self,
        state: RetrievalState,
        max_depth: int = 3,
    ) -> None:
        """Run GraphRAG retrieval."""
        if self._graphrag_service is None:
            return

        try:
            subgraph = await self._graphrag_service.query(
                repository_id=state.repository_id,
                question=state.question,
                max_nodes=50,
                max_depth=max_depth,
            )

            context, sources = self._graph_context_builder.build_context_with_sources(subgraph)
            state.graph_results.extend(sources)
            state.context = context

            state.retrieval_history.append(
                RetrievalHistory(
                    attempt_number=state.attempt_number,
                    tool="graphrag",
                    result_count=len(subgraph.nodes),
                    context_size=len(context),
                    score=sum(subgraph.scores.values()) / max(1, len(subgraph.scores)),
                )
            )
        except Exception as exc:
            state.errors.append(f"GraphRAG failed: {exc}")

    async def _run_hybrid(
        self,
        state: RetrievalState,
        top_k: int = 5,
    ) -> None:
        """Run hybrid retrieval."""
        try:
            results = await self._hybrid_retriever.retrieve(state.question, top_k=top_k)
            state.retrieved_documents.extend(
                self._to_dicts(results)
            )

            state.retrieval_history.append(
                RetrievalHistory(
                    attempt_number=state.attempt_number,
                    tool="hybrid",
                    result_count=len(results),
                    context_size=sum(len(r.content) for r in results),
                    score=sum(r.score for r in results) / max(1, len(results)),
                )
            )
        except Exception as exc:
            state.errors.append(f"Hybrid retrieval failed: {exc}")

    async def _run_semantic(
        self,
        state: RetrievalState,
        top_k: int = 5,
    ) -> None:
        """Run semantic (vector) retrieval."""
        try:
            results = await self._vector_retriever.retrieve(state.question, top_k=top_k)
            state.retrieved_documents.extend(
                self._to_dicts(results)
            )

            state.retrieval_history.append(
                RetrievalHistory(
                    attempt_number=state.attempt_number,
                    tool="semantic",
                    result_count=len(results),
                    context_size=sum(len(r.content) for r in results),
                    score=sum(r.score for r in results) / max(1, len(results)),
                )
            )
        except Exception as exc:
            state.errors.append(f"Semantic retrieval failed: {exc}")

    @staticmethod
    def _to_dicts(results) -> list[dict]:
        """Convert retrieval results to dicts."""
        return [
            {
                "content": r.content,
                "score": r.score,
                "document_type": r.document_type,
                "file": r.file,
                "symbol": r.symbol,
                "line_start": r.line_start,
                "line_end": r.line_end,
            }
            for r in results
        ]