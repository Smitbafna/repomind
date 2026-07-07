from __future__ import annotations

from pydantic import BaseModel, Field


class RelationshipItem(BaseModel):
    """A single relationship record returned in API responses."""

    id: str
    source_symbol: str
    target_symbol: str
    relationship_type: str
    source_file: str
    target_file: str
    line_number: int

    model_config = {"from_attributes": True}


class RelationshipsResponse(BaseModel):
    """Response containing all relationships for a repository."""

    repository_id: str
    total: int
    relationships: list[RelationshipItem]


class GraphNode(BaseModel):
    """A node in the relationship graph."""

    id: str
    label: str
    kind: str
    file_path: str


class GraphEdge(BaseModel):
    """An edge in the relationship graph."""

    source: str
    target: str
    type: str


class GraphResponse(BaseModel):
    """Graph representation suitable for frontend visualisation."""

    repository_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class RelationshipsExtractResponse(BaseModel):
    """Response returned after extracting relationships."""

    repository_id: str
    relationships_extracted: int
    status: str = "completed"