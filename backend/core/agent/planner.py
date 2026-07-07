from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.core.query.analyzer import QueryAnalyzer


@dataclass
class ExecutionPlan:
    """Plan for executing a query."""

    selected_tools: list[str]
    reasoning: str


class Planner:
    """Determines which tools to use for a given question.

    Uses deterministic rules initially.
    Designed so an LLM-based planner can replace it later
    without changing the interface.
    """

    _HISTORY_PATTERNS: list[re.Pattern] = [
        re.compile(r"\b(who|when)\s+(introduced|created|added|wrote|authored)\b", re.IGNORECASE),
        re.compile(r"\b(who|when)\s+(last|recently|modified|changed|edited|updated)\b", re.IGNORECASE),
        re.compile(r"\b(history|timeline|evolution|changes|changelog)\b", re.IGNORECASE),
        re.compile(r"\b(blame|who.*wrote|who.*created|when.*created)\b", re.IGNORECASE),
        re.compile(r"\b(commit|git|version|revision)\b", re.IGNORECASE),
    ]

    _RELATIONSHIP_PATTERNS: list[re.Pattern] = [
        re.compile(r"\b(relationship|dependency|depend|import|inherit|call|reference)\b", re.IGNORECASE),
        re.compile(r"\b(how.*(relate|connect|link)|what.*(use|call|import))\b", re.IGNORECASE),
        re.compile(r"\b(class\s+hierarchy|inheritance|interface)\b", re.IGNORECASE),
    ]

    _GITHUB_PATTERNS: list[re.Pattern] = [
        re.compile(r"\b(why|why was|who reviewed|reviewed|review|bug|discussion|issue|release|pr|pull request|feature added)\b", re.IGNORECASE),
        re.compile(r"\b(introduced|added|discussed|reviewed|released|release)\b", re.IGNORECASE),
    ]

    def __init__(self, query_analyzer: QueryAnalyzer | None = None) -> None:
        self._analyzer = query_analyzer or QueryAnalyzer()

    def plan(self, question: str) -> ExecutionPlan:
        """Create an execution plan for the question.

        Args:
            question: The user's natural language question.

        Returns:
            An ``ExecutionPlan`` with selected tools and reasoning.
        """
        analysis = self._analyzer.analyze(question)
        tools: list[str] = []
        reasoning_parts: list[str] = []
        needs_git = self._needs_git(question)
        needs_relationships = self._needs_relationships(question)
        needs_github = self._needs_github(question)

        # Select semantic retrieval tools based on strategy.
        if analysis.retrieval_strategy == "vector":
            tools.append("semantic_retriever")
            reasoning_parts.append(
                f"Intent '{analysis.intent}' suggests vector semantic search"
            )
        elif analysis.retrieval_strategy == "keyword":
            tools.append("keyword_retriever")
            reasoning_parts.append(
                f"Intent '{analysis.intent}' suggests keyword search"
            )
        else:
            tools.append("hybrid_retriever")
            reasoning_parts.append(
                f"Intent '{analysis.intent}' suggests hybrid search"
            )

        # Add relationship retriever for structural questions.
        if needs_relationships or analysis.intent in ("architecture", "explain_code"):
            tools.append("relationship_retriever")
            reasoning_parts.append(
                "Question involves code relationships or structure"
            )

        # Add GitHub engineering-history tools.
        if needs_github:
            tools.append("github_retriever_tool")
            reasoning_parts.append(
                "Question involves GitHub engineering history or project discussions"
            )

        # Add git tools for history questions.
        if needs_git:
            tools.append("git_history_tool")
            tools.append("blame_tool")
            reasoning_parts.append(
                "Question involves code history or authorship"
            )
            # Timeline for evolution questions.
            if "evolution" in question.lower() or "timeline" in question.lower():
                tools.append("timeline_tool")
                reasoning_parts.append(
                    "Question involves repository evolution over time"
                )

        return ExecutionPlan(
            selected_tools=list(dict.fromkeys(tools)),  # Deduplicate while preserving order
            reasoning="; ".join(reasoning_parts),
        )

    def _needs_git(self, question: str) -> bool:
        """Check if the question requires git history."""
        return any(p.search(question) for p in self._HISTORY_PATTERNS)

    def _needs_relationships(self, question: str) -> bool:
        """Check if the question requires code relationships."""
        return any(p.search(question) for p in self._RELATIONSHIP_PATTERNS)

    def _needs_github(self, question: str) -> bool:
        """Check if the question requires GitHub engineering-history retrieval."""
        return any(p.search(question) for p in self._GITHUB_PATTERNS)