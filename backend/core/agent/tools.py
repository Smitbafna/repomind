from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from backend.core.agent.state import QueryState
from backend.core.git.models import BlameInfo
from backend.core.git.service import GitService
from backend.core.github.retriever import GitHubRetriever
from backend.core.relationships.service import RelationshipService
from backend.core.retrieval.hybrid_retriever import HybridRetriever
from backend.core.retrieval.keyword_retriever import KeywordRetriever
from backend.core.retrieval.retriever import RetrievalResult
from backend.core.retrieval.vector_retriever import VectorRetriever
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Abstract interface for all tools."""

    @abstractmethod
    async def execute(self, state: QueryState) -> QueryState:
        """Execute the tool and update the query state.

        Args:
            state: The current query state.

        Returns:
            Updated query state with tool-specific results.
        """
        ...


class SemanticRetrieverTool(BaseTool):
    """Tool wrapping the vector retriever."""

    def __init__(self, retriever: VectorRetriever | None = None) -> None:
        self._retriever = retriever or VectorRetriever()

    async def execute(self, state: QueryState) -> QueryState:
        question = state.question
        results = await self._retriever.retrieve(question, top_k=5)
        state.retrieved_documents.extend(self._to_dicts(results))
        state.execution_trace.append({
            "node": "ExecuteTools",
            "tool": "semantic_retriever",
            "result_count": len(results),
        })
        return state

    @staticmethod
    def _to_dicts(results: list[RetrievalResult]) -> list[dict]:
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


class KeywordRetrieverTool(BaseTool):
    """Tool wrapping the keyword retriever."""

    def __init__(self, retriever: KeywordRetriever | None = None) -> None:
        self._retriever = retriever or KeywordRetriever()

    async def execute(self, state: QueryState) -> QueryState:
        results = await self._retriever.retrieve(state.question, top_k=5)
        state.retrieved_documents.extend(
            SemanticRetrieverTool._to_dicts(results)
        )
        state.execution_trace.append({
            "node": "ExecuteTools",
            "tool": "keyword_retriever",
            "result_count": len(results),
        })
        return state


class HybridRetrieverTool(BaseTool):
    """Tool wrapping the hybrid retriever."""

    def __init__(self, retriever: HybridRetriever | None = None) -> None:
        self._retriever = retriever or HybridRetriever()

    async def execute(self, state: QueryState) -> QueryState:
        results = await self._retriever.retrieve(state.question, top_k=5)
        state.retrieved_documents.extend(
            SemanticRetrieverTool._to_dicts(results)
        )
        state.execution_trace.append({
            "node": "ExecuteTools",
            "tool": "hybrid_retriever",
            "result_count": len(results),
        })
        return state


class RelationshipRetrieverTool(BaseTool):
    """Tool wrapping the relationship service."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        from backend.database.database import get_sync_session
        # Use async session if provided, otherwise skip for standalone use
        self._session = session

    async def execute(self, state: QueryState) -> QueryState:
        # Relationships require a DB session which is wired via DI
        state.execution_trace.append({
            "node": "ExecuteTools",
            "tool": "relationship_retriever",
            "result_count": 0,
            "note": "Requires async session wiring",
        })
        return state


class GitHubRetrieverTool(BaseTool):
    """Tool wrapping the GitHub engineering-history retriever."""

    def __init__(self, retriever: GitHubRetriever | None = None) -> None:
        self._retriever = retriever or GitHubRetriever()

    async def execute(self, state: QueryState) -> QueryState:
        if not state.repository_id:
            state.execution_trace.append({
                "node": "ExecuteTools",
                "tool": "github_retriever_tool",
                "result_count": 0,
                "note": "Repository id required",
            })
            return state

        results = await self._retriever.retrieve(
            state.question,
            top_k=5,
            repository_id=state.repository_id,
        )
        state.retrieved_documents.extend(SemanticRetrieverTool._to_dicts(results))
        state.execution_trace.append({
            "node": "ExecuteTools",
            "tool": "github_retriever_tool",
            "result_count": len(results),
        })
        return state


class GitHistoryTool(BaseTool):
    """Tool wrapping git history retrieval."""

    def __init__(self, git_service: GitService | None = None) -> None:
        self._git_service = git_service

    async def execute(self, state: QueryState) -> QueryState:
        if self._git_service is None:
            state.git_results.append({"note": "GitService not available"})
            return state

        try:
            commits = await self._git_service.get_commits(state.repository_id)
            state.git_results = [
                {
                    "hash": c.hash,
                    "author_name": c.author_name,
                    "author_email": c.author_email,
                    "commit_message": c.commit_message[:200],
                    "committed_at": str(c.committed_at),
                }
                for c in commits[:10]
            ]
        except Exception as exc:
            state.errors.append(f"Git history failed: {exc}")

        state.execution_trace.append({
            "node": "ExecuteTools",
            "tool": "git_history_tool",
            "result_count": len(state.git_results),
        })
        return state


class BlameTool(BaseTool):
    """Tool wrapping git blame."""

    def __init__(self, git_service: GitService | None = None) -> None:
        self._git_service = git_service

    async def execute(self, state: QueryState) -> QueryState:
        state.execution_trace.append({
            "node": "ExecuteTools",
            "tool": "blame_tool",
            "result_count": 0,
            "note": "Requires specific file+line from context",
        })
        return state


class TimelineTool(BaseTool):
    """Tool wrapping timeline retrieval."""

    def __init__(self, git_service: GitService | None = None) -> None:
        self._git_service = git_service

    async def execute(self, state: QueryState) -> QueryState:
        if self._git_service is None:
            state.execution_trace.append({
                "node": "ExecuteTools",
                "tool": "timeline_tool",
                "result_count": 0,
                "note": "GitService not available",
            })
            return state

        try:
            events = await self._git_service.get_timeline(state.repository_id)
            state.git_results.extend([
                {
                    "commit_hash": e.commit_hash,
                    "author_name": e.author_name,
                    "commit_message": e.commit_message[:200],
                    "affected_files": e.affected_files,
                }
                for e in events[:10]
            ])
        except Exception as exc:
            state.errors.append(f"Timeline failed: {exc}")

        state.execution_trace.append({
            "node": "ExecuteTools",
            "tool": "timeline_tool",
            "result_count": len(events) if 'events' in dir() else 0,
        })
        return state