from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_db, get_query_engine
from backend.core.query.engine import QueryEngine
from backend.database.repositories import RepositoryRepository
from backend.schemas.query import AskRequest, AskResponse, SourceInfo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repositories", tags=["query"])


@router.post("/{repository_id}/ask", response_model=AskResponse)
async def ask_repository(
    repository_id: str,
    payload: AskRequest,
    session: AsyncSession = Depends(get_db),
    query_engine: QueryEngine = Depends(get_query_engine),
) -> AskResponse:
    """Ask a natural language question about a repository.

    The pipeline:
        1. Analyzes the query to determine intent and strategy.
        2. Retrieves relevant documents from the index.
        3. Builds context from retrieved documents.
        4. Constructs a prompt for the LLM.
        5. Generates an answer using Ollama.
        6. Returns the answer with source citations.

    Does NOT use LangGraph, agents, or GraphRAG.
    Only uses retrieval + LLM generation.
    """
    # Verify repository exists.
    repo_repo = RepositoryRepository(session)
    repo = await repo_repo.get_by_id(repository_id)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository not found: {repository_id}",
        )

    try:
        result = await query_engine.answer(payload.question)

        return AskResponse(
            repository_id=repository_id,
            question=payload.question,
            answer=result.answer,
            sources=[
                SourceInfo(
                    file=s["file"],
                    symbol=s["symbol"],
                    score=s["score"],
                    document_type=s["document_type"],
                    line_start=s["line_start"],
                    line_end=s["line_end"],
                )
                for s in result.sources
            ],
            intent=result.intent,
            retrieval_strategy=result.retrieval_strategy,
            keywords=result.keywords,
        )
    except (ConnectionError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc