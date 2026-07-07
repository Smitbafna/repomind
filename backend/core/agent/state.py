from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class QueryState:
    """State passed through the LangGraph workflow.

    Tracks the full execution context of a query including
    analysis results, retrieved evidence, and execution metadata.
    """

    # Input
    repository_id: str = ""
    question: str = ""

    # Analysis
    intent: str = ""
    retrieval_strategy: str = ""
    keywords: list[str] = field(default_factory=list)
    filters: dict[str, str] = field(default_factory=dict)

    # Planned tools
    selected_tools: list[str] = field(default_factory=list)
    execution_plan: str = ""

    # Tool results
    retrieved_documents: list[dict] = field(default_factory=list)
    git_results: list[dict] = field(default_factory=list)
    relationship_results: list[dict] = field(default_factory=list)

    # Context
    context: str = ""
    sources: list[dict] = field(default_factory=list)

    # Answer
    answer: str = ""
    answer_valid: bool = True
    validation_message: str = ""

    # Execution trace
    tool_history: list[dict] = field(default_factory=list)
    execution_trace: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    # Metadata
    latency_ms: dict[str, float] = field(default_factory=dict)