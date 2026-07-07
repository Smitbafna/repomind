from __future__ import annotations

import logging
from collections import defaultdict

from backend.core.graphrag.models import GraphEdge, GraphNode, GraphSubgraph
from backend.database.models import Relationship as RelationshipModel

logger = logging.getLogger(__name__)


class GraphBuilder:
    """Builds an in-memory graph from the existing relationship database.

    Converts persisted ``RelationshipModel`` rows into a graph
    representation with nodes and edges suitable for traversal.
    """

    def build(
        self,
        relationships: list[RelationshipModel],
    ) -> tuple[dict[str, GraphNode], dict[str, list[GraphEdge]]]:
        """Build an in-memory graph from relationship data.

        Args:
            relationships: List of relationship models from the database.

        Returns:
            A tuple of (nodes_map, adjacency_list) where:
            - nodes_map: symbol -> GraphNode
            - adjacency_list: symbol -> list of outgoing GraphEdge
        """
        nodes: dict[str, GraphNode] = {}
        adjacency: dict[str, list[GraphEdge]] = defaultdict(list)

        for rel in relationships:
            # Ensure source node exists.
            if rel.source_symbol not in nodes:
                nodes[rel.source_symbol] = GraphNode(
                    id=rel.source_symbol,
                    label=rel.source_symbol.split(".")[-1],
                    kind=self._infer_kind(rel.source_symbol, rel.source_file),
                    file_path=rel.source_file,
                )

            # Ensure target node exists.
            if rel.target_symbol not in nodes:
                nodes[rel.target_symbol] = GraphNode(
                    id=rel.target_symbol,
                    label=rel.target_symbol.split(".")[-1],
                    kind=self._infer_kind(rel.target_symbol, rel.target_file),
                    file_path=rel.target_file,
                )

            # Add edge.
            edge = GraphEdge(
                source=rel.source_symbol,
                target=rel.target_symbol,
                type=rel.relationship_type,
                weight=self._get_edge_weight(rel.relationship_type),
            )
            adjacency[rel.source_symbol].append(edge)

        logger.info("Built graph with %d nodes and %d edges", len(nodes), sum(len(e) for e in adjacency.values()))
        return nodes, dict(adjacency)

    @staticmethod
    def _infer_kind(symbol: str, file_path: str) -> str:
        """Infer the node kind from the symbol name."""
        if symbol.startswith("<module>"):
            return "module"
        if "." in symbol:
            parts = symbol.split(".")
            # If the last part starts with uppercase, it's likely a class method
            if parts[-1][0].isupper() if parts[-1] else False:
                return "class"
            return "method" if len(parts) > 1 else "function"
        if symbol[0].isupper() if symbol else False:
            return "class"
        return "function"

    @staticmethod
    def _get_edge_weight(rel_type: str) -> float:
        """Get a weight for the relationship type.

        Higher weight = stronger relationship.
        """
        weights = {
            "DEFINES": 1.5,
            "INHERITS": 1.4,
            "CALLS": 1.3,
            "CREATES": 1.2,
            "IMPORTS": 1.1,
            "RETURNS": 1.0,
            "USES": 0.9,
            "REFERENCES": 0.8,
            "MODIFIED": 0.7,
        }
        return weights.get(rel_type, 1.0)