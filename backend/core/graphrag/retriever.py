from __future__ import annotations

import logging
from collections import defaultdict

from backend.core.graphrag.expansion import GraphExpander
from backend.core.graphrag.graph import GraphBuilder
from backend.core.graphrag.models import GraphEdge, GraphNode, GraphSubgraph
from backend.core.graphrag.ranking import GraphRanker
from backend.core.graphrag.traversal import GraphTraverser
from backend.core.query.analyzer import QueryAnalyzer
from backend.database.models import Relationship as RelationshipModel

logger = logging.getLogger(__name__)


class GraphRetriever:
    """Retrieves relevant subgraphs from the code relationship graph.

    Pipeline:
        1. Build in-memory graph from relationship data.
        2. Locate starting symbols from the query.
        3. Expand neighbours using configurable traversal.
        4. Rank nodes by relevance.
        5. Return ranked subgraph.
    """

    def __init__(
        self,
        graph_builder: GraphBuilder | None = None,
        traverser: GraphTraverser | None = None,
        expander: GraphExpander | None = None,
        ranker: GraphRanker | None = None,
        query_analyzer: QueryAnalyzer | None = None,
    ) -> None:
        self._graph_builder = graph_builder or GraphBuilder()
        self._traverser = traverser or GraphTraverser()
        self._expander = expander or GraphExpander()
        self._ranker = ranker or GraphRanker()
        self._query_analyzer = query_analyzer or QueryAnalyzer()

    def retrieve(
        self,
        relationships: list[RelationshipModel],
        query: str,
        max_nodes: int = 30,
        max_depth: int = 3,
    ) -> GraphSubgraph:
        """Retrieve a relevant subgraph for the query.

        Args:
            relationships: All relationships for the repository.
            query: The user's question.
            max_nodes: Maximum nodes in the result.
            max_depth: Maximum traversal depth.

        Returns:
            A ranked ``GraphSubgraph``.
        """
        # 1. Build graph.
        nodes, adjacency = self._graph_builder.build(relationships)

        if not nodes:
            return GraphSubgraph()

        # 2. Locate entry points from query.
        entry_points = self._find_entry_points(nodes, query)

        if not entry_points:
            # Fall back to highest-degree nodes.
            entry_points = self._fallback_entry_points(nodes, adjacency, top_k=3)

        # 3. Traverse from entry points.
        subgraph = self._traverser.bfs(
            nodes=nodes,
            adjacency=adjacency,
            entry_points=entry_points,
            max_depth=max_depth,
            max_nodes=max_nodes,
        )

        # 4. Expand if we have room.
        if len(subgraph.nodes) < max_nodes:
            subgraph = self._expander.expand(
                nodes=nodes,
                adjacency=adjacency,
                subgraph=subgraph,
                max_depth=2,
                max_nodes=max_nodes,
            )

        # 5. Rank and sort.
        analysis = self._query_analyzer.analyze(query)
        ranked = self._ranker.rank_and_sort(
            subgraph=subgraph,
            query_keywords=analysis.keywords,
            top_k=max_nodes,
        )

        return ranked

    def _find_entry_points(
        self,
        nodes: dict[str, GraphNode],
        query: str,
    ) -> list[str]:
        """Find starting nodes from the query text."""
        analysis = self._query_analyzer.analyze(query)
        candidates: list[tuple[str, float]] = []

        keywords = [k.lower() for k in analysis.keywords]

        for node_id, node in nodes.items():
            score = 0.0
            node_lower = node_id.lower()
            label_lower = node.label.lower()

            # Exact match on node ID.
            for kw in keywords:
                if kw == node_lower:
                    score += 2.0
                elif kw in node_lower:
                    score += 1.0
                elif kw in label_lower:
                    score += 0.5

            if score > 0:
                candidates.append((node_id, score))

        # Sort by score descending.
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [c[0] for c in candidates[:5]]

    @staticmethod
    def _fallback_entry_points(
        nodes: dict[str, GraphNode],
        adjacency: dict[str, list[GraphEdge]],
        top_k: int = 3,
    ) -> list[str]:
        """Fall back to highest-degree nodes."""
        from collections import Counter

        degree = Counter()
        for source, edges in adjacency.items():
            degree[source] += len(edges)
            for edge in edges:
                degree[edge.target] += 1

        top = degree.most_common(top_k)
        return [node_id for node_id, _ in top]