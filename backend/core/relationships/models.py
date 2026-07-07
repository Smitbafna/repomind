from __future__ import annotations

import enum
from dataclasses import dataclass, field


class RelationshipType(str, enum.Enum):
    """Types of relationships that can exist between code symbols."""

    CALLS = "CALLS"
    IMPORTS = "IMPORTS"
    INHERITS = "INHERITS"
    DEFINES = "DEFINES"
    RETURNS = "RETURNS"
    USES = "USES"
    CREATES = "CREATES"
    REFERENCES = "REFERENCES"


@dataclass(frozen=True)
class Relationship:
    """A single relationship between two symbols in the codebase."""

    source_symbol: str
    target_symbol: str
    relationship_type: RelationshipType
    source_file: str = ""
    target_file: str = ""
    line_number: int = 0


@dataclass(frozen=True)
class RelationshipGraph:
    """A complete relationship graph for a repository.

    Suitable for frontend visualisation.
    """

    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)


@dataclass(frozen=True)
class GraphNode:
    """A node in the relationship graph."""

    id: str
    label: str
    kind: str  # "file", "class", "function", "module"
    file_path: str = ""


@dataclass(frozen=True)
class GraphEdge:
    """An edge in the relationship graph."""

    source: str
    target: str
    type: str  # RelationshipType value