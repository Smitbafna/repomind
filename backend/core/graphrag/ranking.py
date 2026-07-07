from __future__ import annotations

import logging
from collections import Counter, defaultdict

from backend.core.graphrag.models import GraphEdge, GraphNode, GraphSubgraph

logger = logging.getLogger(__name__)


class GraphRanker:
    """Ranks graph nodes using multiple signals.

    Ranking factors:
        - Degree centrality (number of connections)
        - Traversal distance (closer to entry = higher rank)
        - Relationship weights
        - Node frequency across queries
    """

    def rank(
        self,
        subgraph: GraphSubgraph,
        query_keywords: list[str] | None = None,
    ) -> dict[str, float]:
        """Rank nodes in a subgraph.

        Args:
            subgraph: The subgraph to rank.
            query_keywords: Optional keywords from the query for semantic boost.

        Returns:
            A dict mapping node_id -> score (higher = more relevant).
        """
        scores: dict[str, float] = {}
        node_ids = {n.id for n in subgraph.nodes}

        if not node_ids:
            return scores

        # 1. Degree centrality.
        degree = Counter()
        for edge in subgraph.edges:
            if edge.source in node_ids:
                degree[edge.source] += 1
            if edge.target in node_ids:
                degree[edge.target] += 1

        max_degree = max(degree.values()) if degree else 1

        # 2. Traversal distance (closer to entry = higher score).
        distance_scores: dict[str, float] = {}
        for i, node_id in enumerate(subgraph.traversal_order):
            # Score decreases with distance from entry.
            distance_scores[node_id] = 1.0 / (1.0 + i * 0.1)

        # 3. Keyword matching boost.
        keyword_scores: dict[str, float] = {}
        if query_keywords:
            keywords_lower = [k.lower() for k in query_keywords]
            for node in subgraph.nodes:
                label_lower = node.label.lower()
                match_count = sum(1 for kw in keywords_lower if kw in label_lower)
                if match_count > 0:
                    keyword_scores[node.id] = match_count * 0.5

        # Combine scores.
        for node_id in node_ids:
            score = 0.0

            # Degree centrality (normalized).
            score += degree.get(node_id, 0) / max_degree * 0.3

            # Distance score.
            score += distance_scores.get(node_id, 0.0) * 0.4

            # Keyword boost.
            score += keyword_scores.get(node_id, 0.0) * 0.3

            scores[node_id] = round(score, 4)

        return scores

    def rank_and_sort(
        self,
        subgraph: GraphSubgraph,
        query_keywords: list[str] | None = None,
        top_k: int = 20,
    ) -> GraphSubgraph:
        """Rank nodes and return a sorted subgraph.

        Args:
            subgraph: The subgraph to rank and sort.
            query_keywords: Optional keywords for semantic boost.
            top_k: Maximum nodes to keep.

        Returns:
            A new ``GraphSubgraph`` with scores and sorted nodes.
        """
        scores = self.rank(subgraph, query_keywords)

        # Sort nodes by score descending.
        sorted_nodes = sorted(
            subgraph.nodes,
            key=lambda n: scores.get(n.id, 0.0),
            reverse=True,
        )[:top_k]

        # Keep only edges between kept nodes.
        kept_ids = {n.id for n in sorted_nodes}
        kept_edges = [
            e for e in subgraph.edges
            if e.source in kept_ids and e.target in kept_ids
        ]

        return GraphSubgraph(
            nodes=sorted_nodes,
            edges=kept_edges,
            entry_points=subgraph.entry_points,
            traversal_order=[n.id for n in sorted_nodes],
            scores=scores,
        )