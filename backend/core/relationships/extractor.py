from __future__ import annotations

import ast
import logging
from pathlib import Path

from backend.core.relationships.models import Relationship, RelationshipGraph
from backend.core.relationships.visitor import RelationshipVisitor

logger = logging.getLogger(__name__)


class RelationshipExtractor:
    """Extracts code relationships from source files using AST visitors.

    This class is the parser-agnostic entry point for relationship extraction.
    Currently uses Python's ``ast`` module but can be extended to use Tree-sitter
    without changing the output format (``Relationship`` dataclass).
    """

    def extract_relationships(self, path: Path) -> list[Relationship]:
        """Extract all relationships from a single source file.

        Args:
            path: Path to a Python source file.

        Returns:
            A list of ``Relationship`` instances found in the file.
        """
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning("Failed to read %s: %s", path, exc)
            return []

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            logger.warning("Syntax error in %s: %s", path, exc)
            return []

        visitor = RelationshipVisitor(source_file=str(path))
        visitor.visit(tree)
        return visitor.relationships

    def extract_graph(self, relationships: list[Relationship]) -> RelationshipGraph:
        """Build a graph representation suitable for frontend visualisation.

        Args:
            relationships: All relationships for a repository.

        Returns:
            A ``RelationshipGraph`` containing deduplicated nodes and edges.
        """
        nodes_map: dict[str, dict[str, str]] = {}
        edges: list[dict[str, str]] = []
        seen_edges: set[tuple[str, str, str]] = set()

        for rel in relationships:
            # Add source node
            if rel.source_symbol not in nodes_map:
                nodes_map[rel.source_symbol] = {
                    "id": rel.source_symbol,
                    "label": rel.source_symbol.split(".")[-1],
                    "kind": self._infer_kind(rel.source_symbol, rel.source_file),
                    "file_path": rel.source_file,
                }

            # Add target node
            if rel.target_symbol not in nodes_map:
                nodes_map[rel.target_symbol] = {
                    "id": rel.target_symbol,
                    "label": rel.target_symbol.split(".")[-1],
                    "kind": self._infer_kind(rel.target_symbol, rel.target_file),
                    "file_path": rel.target_file,
                }

            # Add edge (deduplicated)
            edge_key = (rel.source_symbol, rel.target_symbol, rel.relationship_type.value)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                edges.append({
                    "source": rel.source_symbol,
                    "target": rel.target_symbol,
                    "type": rel.relationship_type.value,
                })

        return RelationshipGraph(
            nodes=[_node_from_dict(n) for n in nodes_map.values()],
            edges=[_edge_from_dict(e) for e in edges],
        )

    @staticmethod
    def _infer_kind(symbol: str, file_path: str) -> str:
        """Infer the node kind from the symbol name and context."""
        # Simple heuristics for node type inference
        if symbol.startswith("<module>"):
            return "file"
        if "." in symbol:
            # Could be class.method or module.symbol
            return "function"
        return "module"


def _node_from_dict(d: dict[str, str]) -> "GraphNode":  # noqa: F821
    """Convert a node dictionary to a GraphNode, avoiding circular imports."""
    from backend.core.relationships.models import GraphNode
    return GraphNode(
        id=d["id"],
        label=d["label"],
        kind=d["kind"],
        file_path=d["file_path"],
    )


def _edge_from_dict(d: dict[str, str]) -> "GraphEdge":  # noqa: F821
    """Convert an edge dictionary to a GraphEdge, avoiding circular imports."""
    from backend.core.relationships.models import GraphEdge
    return GraphEdge(
        source=d["source"],
        target=d["target"],
        type=d["type"],
    )