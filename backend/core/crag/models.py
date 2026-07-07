from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CorrectiveAction(str, Enum):
    """Actions the CRAG planner can take to improve retrieval."""

    INCREASE_DEPTH = "increase_depth"
    EXPAND_GRAPH = "expand_graph"
    INCREASE_TOP_K = "increase_top_k"
    RUN_GIT = "run_git"
    RUN_RELATIONSHIPS = "run_relationships"
    RUN_HYBRID = "run_hybrid"
    RETRY_SEMANTIC = "retry_semantic"
    GENERATE_ANSWER = "generate_answer"


@dataclass
class RetrievalHistory:
    """Tracks a single retrieval attempt."""

    attempt_number: int
    tool: str
    result_count: int
    context_size: int
    score: float = 0.0


@dataclass
class EvaluationResult:
    """Result of evaluating retrieval quality."""

    confidence: float  # 0.0 to 1.0
    coverage: float  # 0.0 to 1.0
    redundancy: float  # 0.0 to 1.0
    evidence_diversity: float  # 0.0 to 1.0
    missing_information: list[str] = field(default_factory=list)
    recommended_actions: list[CorrectiveAction] = field(default_factory=list)


@dataclass
class RetrievalState:
    """Extended state for CRAG workflow.

    Tracks retrieval attempts and evaluation for iterative improvement.
    """

    # Input
    repository_id: str = ""
    question: str = ""

    # Analysis
    intent: str = ""
    retrieval_strategy: str = ""
    keywords: list[str] = field(default_factory=list)
    filters: dict[str, str] = field(default_factory=dict)

    # Retrieval tracking
    attempt_number: int = 0
    max_attempts: int = 3

    # Evidence
    retrieved_documents: list[dict] = field(default_factory=list)
    graph_results: list[dict] = field(default_factory=list)
    git_results: list[dict] = field(default_factory=list)
    relationship_results: list[dict] = field(default_factory=list)

    # Evaluation
    retrieval_score: float = 0.0
    confidence: float = 0.0
    missing_information: list[str] = field(default_factory=list)
    retrieval_history: list[RetrievalHistory] = field(default_factory=list)

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