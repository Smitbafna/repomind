from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_db
from backend.core.crag.service import CRAGService
from backend.schemas.crag import CRAGQueryResponse, EvaluationResponse, RetrieveResponse
from backend.schemas.query import AskRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repositories", tags=["crag"])


async def get_crag_service(
    session: AsyncSession = Depends(get_db),
) -> CRAGService:
    """Provide a ``CRAGService``."""
    return CRAGService()


@router.post("/{repository_id}/crag/ask", response_model=CRAGQueryResponse)
async def crag_ask(
    repository_id: str,
    payload: AskRequest,
    crag_service: CRAGService = Depends(get_crag_service),
) -> CRAGQueryResponse:
    """Query with CRAG iterative retrieval.

    Uses CRAG to evaluate and improve retrieval quality iteratively.
    """
    state = await crag_service.query(
        repository_id=repository_id,
        question=payload.question,
    )

    return CRAGQueryResponse(
        repository_id=repository_id,
        question=payload.question,
        answer=state.answer,
        confidence=state.confidence,
        sources=state.sources,
        retrieval_history=[
            {
                "attempt": h.attempt_number,
                "tool": h.tool,
                "result_count": h.result_count,
                "context_size": h.context_size,
                "score": h.score,
            }
            for h in state.retrieval_history
        ],
        answer_valid=state.answer_valid,
        validation_message=state.validation_message,
    )


@router.post("/{repository_id}/evaluate", response_model=EvaluationResponse)
async def crag_evaluate(
    repository_id: str,
    payload: AskRequest,
    crag_service: CRAGService = Depends(get_crag_service),
) -> EvaluationResponse:
    """Evaluate retrieval quality without generating answer."""
    result = await crag_service.evaluate(
        repository_id=repository_id,
        question=payload.question,
    )

    return EvaluationResponse(
        confidence=result["confidence"],
        coverage=result["coverage"],
        redundancy=result["redundancy"],
        evidence_diversity=result["evidence_diversity"],
        missing_information=result["missing_information"],
        recommended_actions=result["recommended_actions"],
    )


@router.post("/{repository_id}/retrieve", response_model=RetrieveResponse)
async def crag_retrieve(
    repository_id: str,
    payload: AskRequest,
    crag_service: CRAGService = Depends(get_crag_service),
) -> RetrieveResponse:
    """Run retrieval only, return history without answer."""
    result = await crag_service.retrieve_only(
        repository_id=repository_id,
        question=payload.question,
    )

    return RetrieveResponse(
        iterations=result["iterations"],
        retrieval_history=result["retrieval_history"],
        confidence=result["confidence"],
        missing_information=result["missing_information"],
    )