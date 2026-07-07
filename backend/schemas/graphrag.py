from __future__ import annotations

from pydantic import BaseModel, Field


class GraphNodeResponse(BaseModel):
    """A node in the graph response."""

    id: str
    label: str
    kind: str
    file_path: str = ""
    score: float = 0.0


class GraphEdgeResponse(BaseModel):
    """An edge in the graph response."""

    source: str
    target: str
    type: str
    weight: float = 1.0


class GraphQueryResponse(BaseModel):
    """Response from a graph query."""

    repository_id: str
    question: str
    answer: str = ""
    retrieved_nodes: list[GraphNodeResponse]
    retrieved_edges: list[GraphEdgeResponse]
    total_nodes: int
    total_edges: int


class GraphSubgraphResponse(BaseModel):
    """Response containing the full graph subgraph."""

    repository_id: str
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]
    total_nodes: int
    total_edges: int