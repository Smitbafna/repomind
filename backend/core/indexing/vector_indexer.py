from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.indexing.document_builder import DocumentBuilder, SemanticDocument
from backend.core.retrieval.embeddings import EmbeddingService
from backend.core.retrieval.vector_store import VectorStore
from backend.database.repositories import (
    CodeFileRepository,
    RepositoryRepository,
)

logger = logging.getLogger(__name__)


class VectorIndexer:
    """Orchestrates the indexing pipeline.

    Responsibilities:
        1. Build semantic documents from parsed repository data.
        2. Generate embeddings for each document.
        3. Store embeddings in the vector database.
    """

    def __init__(
        self,
        session: AsyncSession,
        document_builder: DocumentBuilder | None = None,
        embedding_service: EmbeddingService | None = None,
        vector_store: VectorStore | None = None,
        repo_repo: RepositoryRepository | None = None,
        code_file_repo: CodeFileRepository | None = None,
    ) -> None:
        self._session = session
        self._document_builder = document_builder or DocumentBuilder()
        self._embedding_service = embedding_service or EmbeddingService()
        self._vector_store = vector_store or VectorStore()
        self._repo_repo = repo_repo or RepositoryRepository(session)
        self._code_file_repo = code_file_repo or CodeFileRepository(session)

    async def index_repository(self, repository_id: str) -> int:
        """Index all parsed data for a repository into the vector store.

        Previous index data for the repository is cleared before re-indexing.

        Args:
            repository_id: The primary key of the repository.

        Returns:
            The number of documents indexed.

        Raises:
            ValueError: If the repository ID is not found.
        """
        repo = await self._repo_repo.get_by_id(repository_id)
        if repo is None:
            raise ValueError(f"Repository not found: {repository_id}")

        # Clear previous index data.
        await self._vector_store.delete_repository_points(repository_id)

        # Get parsed code files.
        code_files = list(await self._code_file_repo.get_by_repository(repository_id))

        # Build semantic documents.
        documents = self._document_builder.build_documents(repo, code_files)

        if not documents:
            logger.info("No documents to index for repository %s", repository_id)
            return 0

        # Generate embeddings and store.
        texts = [doc.content for doc in documents]
        embeddings = await self._embedding_service.embed(texts)

        points = [
            self._vector_store.make_point(
                doc_id=doc.id,
                vector=embeddings[i],
                payload={
                    "repository_id": doc.repository_id,
                    "document_type": doc.document_type.value,
                    "content": doc.content,
                    **doc.metadata,
                },
            )
            for i, doc in enumerate(documents)
        ]

        await self._vector_store.upsert(points)

        logger.info(
            "Indexed %d documents for repository %s",
            len(documents),
            repository_id,
        )
        return len(documents)

    async def search(
        self,
        query: str,
        repository_id: str | None = None,
        top_k: int = 10,
    ) -> list[dict]:
        """Search the vector store for documents matching the query.

        Args:
            query: The search query text.
            repository_id: Optional repository ID to filter by.
            top_k: Maximum number of results to return.

        Returns:
            A list of result dictionaries with content and metadata.
        """
        query_vector = await self._embedding_service.embed([query])
        results = await self._vector_store.search(
            vector=query_vector[0],
            repository_id=repository_id,
            top_k=top_k,
        )
        return results