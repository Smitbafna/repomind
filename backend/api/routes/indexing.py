from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.dependencies import (
    get_db,
    get_hybrid_retriever,
    get_keyword_retriever,
    get_vector_indexer,
    get_vector_retriever,
)
from backend.core.indexing.vector_indexer import VectorIndexer
from backend.core.retrieval.hybrid_retriever import HybridRetriever
from backend.core.retrieval.keyword_retriever import KeywordRetriever
from backend.core.retrieval.retriever import BaseRetriever, RetrievalResult
from backend.core.retrieval.vector_retriever import VectorRetriever
from backend.schemas.indexing import (
    IndexResponse,
    QueryRequest,
    QueryResponse,
    SearchResult,
)
from backend.database.repositories import RepositoryRepository
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repositories", tags=["indexing"])


@router.post("/{repository_id}/index", response_model=IndexResponse)
async def index_repository(
    repository_id: str,
    vector_indexer: VectorIndexer = Depends(get_vector_indexer),
) -> IndexResponse:
    """Index all parsed data for a repository into the vector store.

    Builds semantic documents (modules, classes, functions, docstrings, README),
    generates embeddings via Ollama, and stores them in Qdrant.
    """
    try:
        count = await vector_indexer.index_repository(repository_id)
        return IndexResponse(
            repository_id=repository_id,
            documents_indexed=count,
            status="completed",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (ConnectionError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post("/{repository_id}/query", response_model=QueryResponse)
async def query_repository(
    repository_id: str,
    payload: QueryRequest,
    session: AsyncSession = Depends(get_db),
    vector_retriever: VectorRetriever = Depends(get_vector_retriever),
    keyword_retriever: KeywordRetriever = Depends(get_keyword_retriever),
    hybrid_retriever: HybridRetriever = Depends(get_hybrid_retriever),
) -> QueryResponse:
    """Query an indexed repository.

    Embeds the question, retrieves relevant documents, and returns
    the results. Does NOT call an LLM — only retrieval results are returned.

    Supports three retriever types:
    - ``vector``: Semantic vector search
    - ``keyword``: Keyword-based search
    - ``hybrid``: Combined vector + keyword with RRF fusion
    """
    # Verify repository exists.
    repo_repo = RepositoryRepository(session)
    repo = await repo_repo.get_by_id(repository_id)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository not found: {repository_id}",
        )

    # Select the retriever.
    retriever_map: dict[str, BaseRetriever] = {
        "vector": vector_retriever,
        "keyword": keyword_retriever,
        "hybrid": hybrid_retriever,
    }
    retriever = retriever_map[payload.retriever]

    try:
        results = await retriever.retrieve(
            query=payload.query,
            top_k=payload.top_k,
        )

        return QueryResponse(
            repository_id=repository_id,
            query=payload.query,
            results=[
                SearchResult(
                    content=r.content,
                    score=r.score,
                    document_type=r.document_type,
                    file=r.file,
                    symbol=r.symbol,
                    line_start=r.line_start,
                    line_end=r.line_end,
                )
                for r in results
            ],
            total=len(results),
        )
    except (ConnectionError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc