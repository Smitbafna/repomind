from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GraphNode:
    """A node in the GraphRAG graph."""

    id: str
    label: str
    kind: str  # "repository", "module", "class", "function", "method", "import", "commit"
    file_path: str = ""
    properties: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class GraphEdge:
    """An edge in the GraphRAG graph."""

    source: str
    target: str
    type: str  # CALLS, IMPORTS, INHERITS, DEFINES, USES, CREATES, RETURNS, REFERENCES, MODIFIED
    weight: float = 1.0
    properties: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class GraphSubgraph:
    """A subgraph extracted from the full graph."""

    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    traversal_order: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)