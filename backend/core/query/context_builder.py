from __future__ import annotations

import logging

from backend.core.retrieval.retriever import RetrievalResult

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Builds optimised context from retrieved documents.

    Responsibilities:
        - Remove duplicate content.
        - Respect maximum token limit (approximate).
        - Order by semantic relevance (score descending).
        - Format into a coherent text block.
    """

    def __init__(self, max_tokens: int = 4096) -> None:
        self._max_tokens = max_tokens

    def build_context(
        self,
        results: list[RetrievalResult],
        max_results: int = 10,
    ) -> str:
        """Build an optimised context string from retrieval results.

        Args:
            results: Retrieved documents, expected in score-descending order.
            max_results: Maximum number of results to include.

        Returns:
            A formatted context string suitable for injection into a prompt.
        """
        # Deduplicate by content hash.
        seen_hashes: set[int] = set()
        unique_results: list[RetrievalResult] = []

        for result in results:
            content_hash = hash(result.content[:200])  # Use first 200 chars as key
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_results.append(result)

        # Sort by score descending (already sorted, but be safe).
        unique_results.sort(key=lambda r: r.score, reverse=True)

        # Limit to max_results.
        unique_results = unique_results[:max_results]

        # Build context respecting token limit.
        sections: list[str] = []
        total_chars = 0
        # Rough estimate: 1 token ≈ 4 characters.
        max_chars = self._max_tokens * 4

        for result in unique_results:
            section = self._format_section(result)
            section_len = len(section)

            if total_chars + section_len > max_chars:
                break

            sections.append(section)
            total_chars += section_len

        return "\n\n".join(sections) if sections else ""

    def build_context_with_sources(
        self,
        results: list[RetrievalResult],
        max_results: int = 10,
    ) -> tuple[str, list[dict]]:
        """Build context and return it along with source metadata.

        Args:
            results: Retrieved documents.
            max_results: Maximum number of results.

        Returns:
            A tuple of (context_string, sources_list).
        """
        seen_hashes: set[int] = set()
        unique_results: list[RetrievalResult] = []
        sources: list[dict] = []

        for result in results:
            content_hash = hash(result.content[:200])
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_results.append(result)
                sources.append({
                    "file": result.file,
                    "symbol": result.symbol,
                    "score": result.score,
                    "document_type": result.document_type,
                    "line_start": result.line_start,
                    "line_end": result.line_end,
                })

        unique_results.sort(key=lambda r: r.score, reverse=True)
        unique_results = unique_results[:max_results]
        sources = sources[:max_results]

        sections: list[str] = []
        total_chars = 0
        max_chars = self._max_tokens * 4

        for result in unique_results:
            section = self._format_section(result)
            section_len = len(section)
            if total_chars + section_len > max_chars:
                break
            sections.append(section)
            total_chars += section_len

        return "\n\n".join(sections) if sections else "", sources

    @staticmethod
    def _format_section(result: RetrievalResult) -> str:
        """Format a single retrieval result as a context section."""
        parts: list[str] = []

        location = result.file
        if result.symbol:
            location = f"{result.file}:{result.symbol}"
        if result.line_start:
            location = f"{location} (line {result.line_start})"

        parts.append(f"=== From {location} ===")
        parts.append(result.content)

        return "\n".join(parts)