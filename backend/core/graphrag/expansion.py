from __future__ import annotations

import logging
from collections import defaultdict

from backend.core.graphrag.models import GraphEdge, GraphNode, GraphSubgraph
from backend.core.graphrag.traversal import GraphTraverser

logger = logging.getLogger(__name__)


class GraphExpander:
    """Configurable graph expansion.

    Expands a subgraph by adding related nodes based on
    configurable strategies.
    """

    def __init__(self, traverser: GraphTraverser | None = None) -> None:
        self._traverser = traverser or GraphTraverser()

    def expand(
        self,
        nodes: dict[str, GraphNode],
        adjacency: dict[str, list[GraphEdge]],
        subgraph: GraphSubgraph,
        max_depth: int = 2,
        max_nodes: int = 30,
        allowed_types: set[str] | None = None,
    ) -> GraphSubgraph:
        """Expand a subgraph by traversing from its boundary nodes.

        Args:
            nodes: All graph nodes.
            adjacency: Adjacency list.
            subgraph: The current subgraph to expand.
            max_depth: Additional depth to traverse.
            max_nodes: Maximum total nodes.
            allowed_types: Optional relationship type filter.

        Returns:
            An expanded ``GraphSubgraph``.
        """
        # Get boundary nodes (nodes that have edges to unvisited nodes).
        current_ids = {n.id for n in subgraph.nodes}
        boundary: list[str] = []

        for node_id in current_ids:
            for edge in adjacency.get(node_id, []):
                if edge.target not in current_ids and edge.target in nodes:
                    boundary.append(node_id)
                    break

        if not boundary:
            return subgraph

        # Traverse from boundary nodes.
        expanded = self._traverser.bfs(
            nodes=nodes,
            adjacency=adjacency,
            entry_points=boundary,
            max_depth=max_depth,
            max_nodes=max_nodes - len(subgraph.nodes),
            allowed_types=allowed_types,
        )

        # Merge subgraphs.
        merged_nodes = {n.id: n for n in subgraph.nodes}
        merged_edges = list(subgraph.edges)
        seen_edges = {(e.source, e.target, e.type) for e in subgraph.edges}

        for node in expanded.nodes:
            if node.id not in merged_nodes:
                merged_nodes[node.id] = node

        for edge in expanded.edges:
            key = (edge.source, edge.target, edge.type)
            if key not in seen_edges:
                seen_edges.add(key)
                merged_edges.append(edge)

        return GraphSubgraph(
            nodes=list(merged_nodes.values()),
            edges=merged_edges,
            entry_points=subgraph.entry_points,
            traversal_order=subgraph.traversal_order + expanded.traversal_order,
        )