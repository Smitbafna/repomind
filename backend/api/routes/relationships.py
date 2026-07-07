from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.dependencies import get_db, get_relationship_service
from backend.core.relationships.service import RelationshipService
from backend.schemas.relationships import (
    GraphEdge,
    GraphNode,
    GraphResponse,
    RelationshipItem,
    RelationshipsExtractResponse,
    RelationshipsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repositories", tags=["relationships"])


@router.post("/{repository_id}/relationships", response_model=RelationshipsExtractResponse)
async def extract_relationships(
    repository_id: str,
    relationship_service: RelationshipService = Depends(get_relationship_service),
) -> RelationshipsExtractResponse:
    """Extract all code relationships for an already-parsed repository.

    Walks all Python source files and extracts function calls, method calls,
    class inheritance, module imports, object instantiations, attribute access,
    return type annotations, parameter type annotations, and global variable
    references.
    """
    try:
        count = await relationship_service.extract_relationships(repository_id)
        return RelationshipsExtractResponse(
            repository_id=repository_id,
            relationships_extracted=count,
            status="completed",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get("/{repository_id}/relationships", response_model=RelationshipsResponse)
async def get_relationships(
    repository_id: str,
    relationship_service: RelationshipService = Depends(get_relationship_service),
) -> RelationshipsResponse:
    """Return all extracted relationships for a repository."""
    try:
        relationships = await relationship_service.get_relationships(repository_id)
        items = [
            RelationshipItem(
                id=r.id,
                source_symbol=r.source_symbol,
                target_symbol=r.target_symbol,
                relationship_type=r.relationship_type,
                source_file=r.source_file,
                target_file=r.target_file,
                line_number=r.line_number,
            )
            for r in relationships
        ]
        return RelationshipsResponse(
            repository_id=repository_id,
            total=len(items),
            relationships=items,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get("/{repository_id}/graph", response_model=GraphResponse)
async def get_relationship_graph(
    repository_id: str,
    relationship_service: RelationshipService = Depends(get_relationship_service),
) -> GraphResponse:
    """Return a graph representation of all relationships in a repository.

    Returns nodes and edges suitable for frontend visualisation libraries
    (e.g. D3.js, vis.js, Cytoscape).
    """
    try:
        graph = await relationship_service.get_graph(repository_id)
        return GraphResponse(
            repository_id=repository_id,
            nodes=[
                GraphNode(
                    id=n.id,
                    label=n.label,
                    kind=n.kind,
                    file_path=n.file_path,
                )
                for n in graph.nodes
            ],
            edges=[
                GraphEdge(
                    source=e.source,
                    target=e.target,
                    type=e.type,
                )
                for e in graph.edges
            ],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc