from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.relationships.extractor import RelationshipExtractor
from backend.core.relationships.models import Relationship, RelationshipGraph, RelationshipType
from backend.database.models import Relationship as RelationshipModel, Repository
from backend.database.repositories import RelationshipRepository, RepositoryRepository

logger = logging.getLogger(__name__)


class RelationshipService:
    """Orchestrates the relationship extraction pipeline.

    Responsibilities:
        1. Discover supported source files in a repository.
        2. Extract relationships from each file using the ``RelationshipExtractor``.
        3. Persist extracted relationships into the database.
        4. Serve relationship queries and graph data.
    """

    def __init__(
        self,
        session: AsyncSession,
        extractor: RelationshipExtractor | None = None,
        repo_repo: RepositoryRepository | None = None,
        relationship_repo: RelationshipRepository | None = None,
    ) -> None:
        self._session = session
        self._extractor = extractor or RelationshipExtractor()
        self._repo_repo = repo_repo or RepositoryRepository(session)
        self._relationship_repo = relationship_repo or RelationshipRepository(session)

    async def extract_relationships(self, repository_id: str) -> int:
        """Extract and persist all relationships for a repository.

        Previous relationships for the repository are cleared before re-extraction.

        Args:
            repository_id: The primary key of the repository.

        Returns:
            The number of relationships extracted.

        Raises:
            ValueError: If the repository ID is not found.
        """
        repo = await self._repo_repo.get_by_id(repository_id)
        if repo is None:
            raise ValueError(f"Repository not found: {repository_id}")

        # Clear previous relationships.
        await self._relationship_repo.delete_by_repository(repository_id)

        repo_path = Path(repo.local_path)
        if not repo_path.is_dir():
            logger.warning("Repository path does not exist: %s", repo_path)
            return 0

        all_relationships: list[Relationship] = []
        python_files = sorted(repo_path.rglob("*.py"))

        for file_path in python_files:
            if not file_path.is_file():
                continue
            rels = self._extractor.extract_relationships(file_path)
            all_relationships.extend(rels)

        # Persist all relationships.
        relationship_models = [
            RelationshipModel(
                repository_id=repository_id,
                source_symbol=rel.source_symbol,
                target_symbol=rel.target_symbol,
                relationship_type=rel.relationship_type.value,
                source_file=rel.source_file,
                target_file=rel.target_file,
                line_number=rel.line_number,
            )
            for rel in all_relationships
        ]

        if relationship_models:
            await self._relationship_repo.add_many(relationship_models)

        await self._session.flush()
        logger.info(
            "Extracted %d relationships for repository %s",
            len(all_relationships),
            repository_id,
        )
        return len(all_relationships)

    async def get_relationships(
        self, repository_id: str
    ) -> list[RelationshipModel]:
        """Return all persisted relationships for a repository.

        Args:
            repository_id: The primary key of the repository.

        Returns:
            A list of ``RelationshipModel`` instances.

        Raises:
            ValueError: If the repository ID is not found.
        """
        repo = await self._repo_repo.get_by_id(repository_id)
        if repo is None:
            raise ValueError(f"Repository not found: {repository_id}")

        return list(
            await self._relationship_repo.get_by_repository(repository_id)
        )

    async def get_graph(self, repository_id: str) -> RelationshipGraph:
        """Build a graph representation of all relationships in a repository.

        Args:
            repository_id: The primary key of the repository.

        Returns:
            A ``RelationshipGraph`` with deduplicated nodes and edges.
        """
        rel_models = await self.get_relationships(repository_id)
        relationships = [
            Relationship(
                source_symbol=rm.source_symbol,
                target_symbol=rm.target_symbol,
                relationship_type=RelationshipType(rm.relationship_type),
                source_file=rm.source_file,
                target_file=rm.target_file,
                line_number=rm.line_number,
            )
            for rm in rel_models
        ]
        return self._extractor.extract_graph(relationships)