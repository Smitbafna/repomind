from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_db, get_graphrag_service
from backend.core.graphrag.service import GraphRAGService
from backend.schemas.graphrag import (
    GraphEdgeResponse,
    GraphNodeResponse,
    GraphQueryResponse,
    GraphSubgraphResponse,
)
from backend.schemas.query import AskRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repositories", tags=["graphrag"])


@router.post("/{repository_id}/graph/query", response_model=GraphQueryResponse)
async def graph_query(
    repository_id: str,
    payload: AskRequest,
    graphrag_service: GraphRAGService = Depends(get_graphrag_service),
) -> GraphQueryResponse:
    """Query the code relationship graph.

    Returns a relevant subgraph with nodes, edges, and an answer
    generated from the graph context.
    """
    try:
        subgraph = await graphrag_service.query(
            repository_id=repository_id,
            question=payload.question,
        )

        return GraphQueryResponse(
            repository_id=repository_id,
            question=payload.question,
            answer="",  # Answer generation via LLM is handled by the agent
            retrieved_nodes=[
                GraphNodeResponse(
                    id=n.id,
                    label=n.label,
                    kind=n.kind,
                    file_path=n.file_path,
                    score=subgraph.scores.get(n.id, 0.0),
                )
                for n in subgraph.nodes
            ],
            retrieved_edges=[
                GraphEdgeResponse(
                    source=e.source,
                    target=e.target,
                    type=e.type,
                    weight=e.weight,
                )
                for e in subgraph.edges
            ],
            total_nodes=len(subgraph.nodes),
            total_edges=len(subgraph.edges),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get("/{repository_id}/graph/subgraph", response_model=GraphSubgraphResponse)
async def get_graph_subgraph(
    repository_id: str,
    graphrag_service: GraphRAGService = Depends(get_graphrag_service),
) -> GraphSubgraphResponse:
    """Return the full graph for frontend visualisation."""
    try:
        subgraph = await graphrag_service.get_subgraph(repository_id)

        return GraphSubgraphResponse(
            repository_id=repository_id,
            nodes=[
                GraphNodeResponse(
                    id=n.id,
                    label=n.label,
                    kind=n.kind,
                    file_path=n.file_path,
                )
                for n in subgraph.nodes
            ],
            edges=[
                GraphEdgeResponse(
                    source=e.source,
                    target=e.target,
                    type=e.type,
                    weight=e.weight,
                )
                for e in subgraph.edges
            ],
            total_nodes=len(subgraph.nodes),
            total_edges=len(subgraph.edges),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc