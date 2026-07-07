from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.graphrag.graph import GraphBuilder
from backend.core.graphrag.models import GraphSubgraph
from backend.core.graphrag.retriever import GraphRetriever
from backend.database.repositories import RelationshipRepository, RepositoryRepository

logger = logging.getLogger(__name__)


class GraphRAGService:
    """Orchestrates GraphRAG operations.

    Responsibilities:
        1. Retrieve relevant subgraphs for queries.
        2. Build full graph for visualisation.
        3. Integrate with existing retrieval services.
    """

    def __init__(
        self,
        session: AsyncSession,
        graph_retriever: GraphRetriever | None = None,
        graph_builder: GraphBuilder | None = None,
        repo_repo: RepositoryRepository | None = None,
        relationship_repo: RelationshipRepository | None = None,
    ) -> None:
        self._session = session
        self._graph_retriever = graph_retriever or GraphRetriever()
        self._graph_builder = graph_builder or GraphBuilder()
        self._repo_repo = repo_repo or RepositoryRepository(session)
        self._relationship_repo = relationship_repo or RelationshipRepository(session)

    async def query(
        self,
        repository_id: str,
        question: str,
        max_nodes: int = 30,
        max_depth: int = 3,
    ) -> GraphSubgraph:
        """Query the graph for a relevant subgraph.

        Args:
            repository_id: The repository to query.
            question: The user's question.
            max_nodes: Maximum nodes in the result.
            max_depth: Maximum traversal depth.

        Returns:
            A ranked ``GraphSubgraph``.

        Raises:
            ValueError: If the repository is not found.
        """
        repo = await self._repo_repo.get_by_id(repository_id)
        if repo is None:
            raise ValueError(f"Repository not found: {repository_id}")

        relationships = list(
            await self._relationship_repo.get_by_repository(repository_id)
        )

        if not relationships:
            logger.info("No relationships found for repository %s", repository_id)
            return GraphSubgraph()

        return self._graph_retriever.retrieve(
            relationships=relationships,
            query=question,
            max_nodes=max_nodes,
            max_depth=max_depth,
        )

    async def get_subgraph(
        self,
        repository_id: str,
        max_nodes: int = 100,
    ) -> GraphSubgraph:
        """Get the full graph for visualisation.

        Args:
            repository_id: The repository.
            max_nodes: Maximum nodes to include.

        Returns:
            A ``GraphSubgraph`` with the highest-degree nodes.
        """
        repo = await self._repo_repo.get_by_id(repository_id)
        if repo is None:
            raise ValueError(f"Repository not found: {repository_id}")

        relationships = list(
            await self._relationship_repo.get_by_repository(repository_id)
        )

        if not relationships:
            return GraphSubgraph()

        nodes, adjacency = self._graph_builder.build(relationships)

        # Return highest-degree nodes.
        from collections import Counter
        degree = Counter()
        for source, edges in adjacency.items():
            degree[source] += len(edges)
            for edge in edges:
                degree[edge.target] += 1

        top_nodes = degree.most_common(max_nodes)
        kept_ids = {nid for nid, _ in top_nodes}

        return GraphSubgraph(
            nodes=[n for nid, n in nodes.items() if nid in kept_ids],
            edges=[
                e for edges in adjacency.values() for e in edges
                if e.source in kept_ids and e.target in kept_ids
            ],
        )