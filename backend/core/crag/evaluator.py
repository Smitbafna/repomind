from __future__ import annotations

import logging

from backend.core.crag.models import CorrectiveAction, EvaluationResult, RetrievalState
from backend.core.graphrag.models import GraphSubgraph

logger = logging.getLogger(__name__)


class RetrievalEvaluator:
    """Evaluates retrieval quality and determines corrective actions.

    Evaluates:
        - Coverage: How much of the query is covered by evidence
        - Redundancy: How much duplicate information exists
        - Evidence diversity: Variety of sources (docs, graph, git)
        - Context size: Whether we have enough context
    """

    def evaluate(self, state: RetrievalState) -> EvaluationResult:
        """Evaluate the current retrieval state.

        Args:
            state: The current retrieval state.

        Returns:
            An ``EvaluationResult`` with confidence and recommendations.
        """
        all_evidence = (
            state.retrieved_documents
            + state.graph_results
            + state.git_results
            + state.relationship_results
        )

        # Calculate coverage.
        coverage = self._calculate_coverage(state.question, all_evidence)

        # Calculate redundancy.
        redundancy = self._calculate_redundancy(all_evidence)

        # Calculate evidence diversity.
        diversity = self._calculate_diversity(state)

        # Calculate context size adequacy.
        context_adequate = len(state.context) > 100

        # Overall confidence.
        confidence = self._calculate_confidence(coverage, redundancy, diversity, context_adequate)

        # Determine missing information.
        missing = self._identify_missing(state.question, all_evidence)

        # Determine recommended actions.
        actions = self._recommend_actions(
            confidence=confidence,
            missing=missing,
            has_graph=bool(state.graph_results),
            has_git=bool(state.git_results),
            has_relationships=bool(state.relationship_results),
            attempt=state.attempt_number,
            max_attempts=state.max_attempts,
        )

        return EvaluationResult(
            confidence=confidence,
            coverage=coverage,
            redundancy=redundancy,
            evidence_diversity=diversity,
            missing_information=missing,
            recommended_actions=actions,
        )

    def _calculate_coverage(self, question: str, evidence: list[dict]) -> float:
        """Calculate how well the evidence covers the question."""
        if not evidence:
            return 0.0

        keywords = set(question.lower().split())
        covered = 0

        for doc in evidence:
            content = str(doc.get("content", "") or doc.get("commit_message", "") or "")
            content_lower = content.lower()
            if any(kw in content_lower for kw in keywords if len(kw) > 2):
                covered += 1

        return min(1.0, covered / max(1, len(keywords)))

    def _calculate_redundancy(self, evidence: list[dict]) -> float:
        """Calculate redundancy in evidence (0 = no redundancy, 1 = high redundancy)."""
        if len(evidence) < 2:
            return 0.0

        # Check for duplicate content.
        seen: set[int] = set()
        duplicates = 0

        for doc in evidence:
            content = str(doc.get("content", "") or doc.get("commit_message", "") or "")
            content_hash = hash(content[:100])
            if content_hash in seen:
                duplicates += 1
            seen.add(content_hash)

        return min(1.0, duplicates / len(evidence))

    def _calculate_diversity(self, state: RetrievalState) -> float:
        """Calculate evidence diversity across sources."""
        sources = 0
        if state.retrieved_documents:
            sources += 1
        if state.graph_results:
            sources += 1
        if state.git_results:
            sources += 1
        if state.relationship_results:
            sources += 1

        return min(1.0, sources / 4.0)

    def _calculate_confidence(
        self,
        coverage: float,
        redundancy: float,
        diversity: float,
        context_adequate: bool,
    ) -> float:
        """Calculate overall confidence score."""
        # Weight: coverage (40%), diversity (30%), context (20%), low redundancy (10%)
        confidence = (
            coverage * 0.4
            + diversity * 0.3
            + (1.0 if context_adequate else 0.0) * 0.2
            + (1.0 - redundancy) * 0.1
        )
        return round(confidence, 3)

    def _identify_missing(self, question: str, evidence: list[dict]) -> list[str]:
        """Identify what information is missing from evidence."""
        missing = []

        # Check for code-related keywords.
        code_keywords = ["function", "class", "method", "import", "def", "return"]
        has_code = any(
            any(kw in str(doc.get("content", "")).lower() for kw in code_keywords)
            for doc in evidence
        )
        if "code" in question.lower() and not has_code:
            missing.append("code implementation details")

        # Check for relationship keywords.
        rel_keywords = ["call", "inherit", "import", "use", "reference"]
        has_rel = any(
            any(kw in str(doc.get("content", "")).lower() for kw in rel_keywords)
            for doc in evidence
        )
        if any(kw in question.lower() for kw in rel_keywords) and not has_rel:
            missing.append("relationship information")

        # Check for history keywords.
        history_keywords = ["when", "history", "change", "commit", "blame"]
        has_history = any(
            "commit" in str(doc).lower() or "hash" in str(doc).lower()
            for doc in evidence
        )
        if any(kw in question.lower() for kw in history_keywords) and not has_history:
            missing.append("git history")

        return missing

    def _recommend_actions(
        self,
        confidence: float,
        missing: list[str],
        has_graph: bool,
        has_git: bool,
        has_relationships: bool,
        attempt: int,
        max_attempts: int,
    ) -> list[CorrectiveAction]:
        """Recommend corrective actions based on evaluation."""
        actions: list[CorrectiveAction] = []

        if attempt >= max_attempts:
            return [CorrectiveAction.GENERATE_ANSWER]

        if confidence >= 0.7:
            return [CorrectiveAction.GENERATE_ANSWER]

        # Recommend actions based on missing information.
        if "relationship information" in missing and not has_graph:
            actions.append(CorrectiveAction.EXPAND_GRAPH)
        if "git history" in missing and not has_git:
            actions.append(CorrectiveAction.RUN_GIT)
        if "code implementation details" in missing:
            actions.append(CorrectiveAction.INCREASE_TOP_K)

        # If no specific missing, try hybrid.
        if not actions:
            actions.append(CorrectiveAction.RUN_HYBRID)

        return actions