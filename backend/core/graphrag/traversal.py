from __future__ import annotations

import logging
from collections import deque

from backend.core.graphrag.models import GraphEdge, GraphNode, GraphSubgraph

logger = logging.getLogger(__name__)


class GraphTraverser:
    """Traverses the graph using configurable strategies.

    Supports:
        - Depth-limited BFS
        - Relationship filtering
        - Cycle detection
        - Maximum node limits
    """

    def bfs(
        self,
        nodes: dict[str, GraphNode],
        adjacency: dict[str, list[GraphEdge]],
        entry_points: list[str],
        max_depth: int = 3,
        max_nodes: int = 50,
        allowed_types: set[str] | None = None,
    ) -> GraphSubgraph:
        """Breadth-first traversal from entry points.

        Args:
            nodes: All graph nodes.
            adjacency: Adjacency list.
            entry_points: Starting node IDs.
            max_depth: Maximum traversal depth.
            max_nodes: Maximum nodes to collect.
            allowed_types: Optional set of relationship types to follow.

        Returns:
            A ``GraphSubgraph`` with visited nodes and edges.
        """
        visited_nodes: dict[str, GraphNode] = {}
        visited_edges: list[GraphEdge] = []
        visited_order: list[str] = []
        queue: deque[tuple[str, int]] = deque()

        for ep in entry_points:
            if ep in nodes:
                queue.append((ep, 0))
                if ep not in visited_nodes:
                    visited_nodes[ep] = nodes[ep]
                    visited_order.append(ep)

        while queue and len(visited_nodes) < max_nodes:
            current, depth = queue.popleft()

            if depth >= max_depth:
                continue

            for edge in adjacency.get(current, []):
                if allowed_types and edge.type not in allowed_types:
                    continue

                if edge.target not in visited_nodes and edge.target in nodes:
                    visited_nodes[edge.target] = nodes[edge.target]
                    visited_order.append(edge.target)
                    visited_edges.append(edge)
                    queue.append((edge.target, depth + 1))
                elif edge.target in visited_nodes:
                    # Still add the edge even if target already visited
                    if edge not in visited_edges:
                        visited_edges.append(edge)

        return GraphSubgraph(
            nodes=list(visited_nodes.values()),
            edges=visited_edges,
            entry_points=entry_points,
            traversal_order=visited_order,
        )

    def weighted_traversal(
        self,
        nodes: dict[str, GraphNode],
        adjacency: dict[str, list[GraphEdge]],
        entry_points: list[str],
        max_nodes: int = 50,
        min_weight: float = 0.0,
    ) -> GraphSubgraph:
        """Traverse using edge weights as priority.

        Higher-weight edges are traversed first.

        Args:
            nodes: All graph nodes.
            adjacency: Adjacency list.
            entry_points: Starting node IDs.
            max_nodes: Maximum nodes to collect.
            min_weight: Minimum edge weight to follow.

        Returns:
            A ``GraphSubgraph``.
        """
        import heapq

        visited_nodes: dict[str, GraphNode] = {}
        visited_edges: list[GraphEdge] = []
        visited_order: list[str] = []
        # Use negative weight as priority (higher weight = higher priority)
        heap: list[tuple[float, str, int]] = []

        for ep in entry_points:
            if ep in nodes:
                heapq.heappush(heap, (0.0, ep, 0))
                if ep not in visited_nodes:
                    visited_nodes[ep] = nodes[ep]
                    visited_order.append(ep)

        while heap and len(visited_nodes) < max_nodes:
            neg_weight, current, depth = heapq.heappop(heap)

            for edge in adjacency.get(current, []):
                if edge.weight < min_weight:
                    continue

                if edge.target not in visited_nodes and edge.target in nodes:
                    visited_nodes[edge.target] = nodes[edge.target]
                    visited_order.append(edge.target)
                    visited_edges.append(edge)
                    # Push with negative weight for max-heap behavior
                    heapq.heappush(heap, (-edge.weight, edge.target, depth + 1))
                elif edge.target in visited_nodes:
                    if edge not in visited_edges:
                        visited_edges.append(edge)

        return GraphSubgraph(
            nodes=list(visited_nodes.values()),
            edges=visited_edges,
            entry_points=entry_points,
            traversal_order=visited_order,
        )