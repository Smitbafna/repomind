from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.agent.executor import AgentExecutor
from backend.core.agent.planner import Planner
from backend.core.git.service import GitService
from backend.core.github.service import GitHubService
from backend.core.graphrag.service import GraphRAGService
from backend.core.indexing.vector_indexer import VectorIndexer
from backend.core.ingestion.service import IngestionService
from backend.core.parser.service import ParserService
from backend.core.query.engine import QueryEngine
from backend.core.relationships.service import RelationshipService
from backend.core.retrieval.hybrid_retriever import HybridRetriever
from backend.core.retrieval.keyword_retriever import KeywordRetriever
from backend.core.retrieval.vector_retriever import VectorRetriever
from backend.database.database import get_async_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for use as a FastAPI dependency."""
    async for session in get_async_session():
        yield session


async def get_ingestion_service(
    session: AsyncSession = Depends(get_db),
) -> IngestionService:
    """Provide an ``IngestionService`` wired with the current DB session."""
    return IngestionService(session=session)


async def get_parser_service(
    session: AsyncSession = Depends(get_db),
) -> ParserService:
    """Provide a ``ParserService`` wired with the current DB session."""
    return ParserService(session=session)


async def get_relationship_service(
    session: AsyncSession = Depends(get_db),
) -> RelationshipService:
    """Provide a ``RelationshipService`` wired with the current DB session."""
    return RelationshipService(session=session)


async def get_vector_indexer(
    session: AsyncSession = Depends(get_db),
) -> VectorIndexer:
    """Provide a ``VectorIndexer`` wired with the current DB session."""
    return VectorIndexer(session=session)


async def get_vector_retriever() -> VectorRetriever:
    """Provide a ``VectorRetriever``."""
    return VectorRetriever()


async def get_keyword_retriever() -> KeywordRetriever:
    """Provide a ``KeywordRetriever``."""
    return KeywordRetriever()


async def get_hybrid_retriever() -> HybridRetriever:
    """Provide a ``HybridRetriever``."""
    return HybridRetriever()


async def get_query_engine() -> QueryEngine:
    """Provide a ``QueryEngine``."""
    return QueryEngine()


async def get_git_service(
    session: AsyncSession = Depends(get_db),
) -> GitService:
    """Provide a ``GitService`` wired with the current DB session."""
    return GitService(session=session)


async def get_github_service(
    session: AsyncSession = Depends(get_db),
) -> GitHubService:
    """Provide a ``GitHubService`` wired with the current DB session."""
    return GitHubService(session=session)


async def get_planner() -> Planner:
    """Provide a ``Planner``."""
    return Planner()


async def get_agent_executor() -> AgentExecutor:
    """Provide an ``AgentExecutor``."""
    return AgentExecutor()


async def get_graphrag_service(
    session: AsyncSession = Depends(get_db),
) -> GraphRAGService:
    """Provide a ``GraphRAGService`` wired with the current DB session."""
    return GraphRAGService(session=session)