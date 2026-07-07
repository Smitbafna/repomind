from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class QueryAnalysis:
    """Result of analyzing a user query."""

    intent: str
    keywords: list[str] = field(default_factory=list)
    filters: dict[str, str] = field(default_factory=dict)
    retrieval_strategy: str = "hybrid"  # "vector", "keyword", or "hybrid"


class QueryAnalyzer:
    """Analyzes user queries using deterministic rules.

    Returns:
        - intent: What the user wants (e.g. "explain_code", "find_function",
          "architecture", "usage_example", "general")
        - keywords: Extracted important terms
        - filters: Optional constraints
        - retrieval_strategy: Which retriever to use

    No AI is used for analysis — only pattern matching and heuristics.
    """

    _INTENT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
        (re.compile(r"\b(what|how)\s+(does|is|are|can|do)\b", re.IGNORECASE), "explain_code"),
        (re.compile(r"\b(explain|describe|tell|understand)\b", re.IGNORECASE), "explain_code"),
        (re.compile(r"\b(find|locate|where|search|lookup)\b", re.IGNORECASE), "find_function"),
        (re.compile(r"\b(architecture|structure|design|overview|diagram)\b", re.IGNORECASE), "architecture"),
        (re.compile(r"\b(usage|example|how to|tutorial|demo|sample)\b", re.IGNORECASE), "usage_example"),
        (re.compile(r"\b(implement|write|create|add|change|modify|update)\b", re.IGNORECASE), "implementation"),
        (re.compile(r"\b(compare|difference|versus|vs)\b", re.IGNORECASE), "comparison"),
        (re.compile(r"\b(error|bug|issue|problem|fail|exception)\b", re.IGNORECASE), "debugging"),
    ]

    _KEYWORD_PATTERNS = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")

    def analyze(self, query: str) -> QueryAnalysis:
        """Analyze a user query using deterministic rules.

        Args:
            query: The user's natural language question.

        Returns:
            A ``QueryAnalysis`` with intent, keywords, filters, and strategy.
        """
        intent = self._detect_intent(query)
        keywords = self._extract_keywords(query)
        filters = self._extract_filters(query)
        strategy = self._select_strategy(intent, keywords)

        return QueryAnalysis(
            intent=intent,
            keywords=keywords,
            filters=filters,
            retrieval_strategy=strategy,
        )

    def _detect_intent(self, query: str) -> str:
        """Detect the user's intent based on pattern matching."""
        for pattern, intent in self._INTENT_PATTERNS:
            if pattern.search(query):
                return intent
        return "general"

    def _extract_keywords(self, query: str) -> list[str]:
        """Extract important keywords from the query."""
        # Find all identifier-like words (potential code symbols).
        identifiers = self._KEYWORD_PATTERNS.findall(query)

        # Filter out common stop words.
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "has", "have", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "can", "shall",
            "what", "how", "why", "when", "where", "who", "which",
            "this", "that", "these", "those", "it", "its", "they", "them",
            "we", "you", "he", "she", "his", "her", "our", "your",
            "and", "or", "but", "not", "if", "in", "on", "at", "to", "for",
            "with", "by", "from", "of", "as", "into", "through", "during",
            "before", "after", "above", "below", "between", "out", "off",
            "over", "under", "again", "further", "then", "once", "here",
            "there", "tell", "find", "explain", "describe", "show", "give",
            "get", "use", "using", "used", "like", "just", "also", "very",
            "too", "about", "more", "some", "any", "each", "every", "own",
            "same", "other", "another", "many", "much", "such", "only",
            "still", "while", "because", "does", "doesn", "don", "wont",
            "function", "class", "method", "code", "file", "module",
        }

        return [id for id in identifiers if id.lower() not in stop_words]

    def _extract_filters(self, query: str) -> dict[str, str]:
        """Extract filter constraints from the query."""
        filters: dict[str, str] = {}

        # Detect file references.
        file_match = re.search(r"(?:in|from|inside)\s+`?([a-zA-Z_][a-zA-Z0-9_/]*\.\w+)`?", query)
        if file_match:
            filters["file"] = file_match.group(1)

        # Detect class references.
        class_match = re.search(r"(?:class|type)\s+`?([A-Z][a-zA-Z0-9_]*)`?", query)
        if class_match:
            filters["class"] = class_match.group(1)

        # Detect function/method references.
        func_match = re.search(r"(?:function|method)\s+`?([a-z_][a-zA-Z0-9_]*)`?", query)
        if func_match:
            filters["function"] = func_match.group(1)

        return filters

    def _select_strategy(self, intent: str, keywords: list[str]) -> str:
        """Select the retrieval strategy based on intent and keywords."""
        # Architecture questions benefit from keyword search.
        if intent in ("architecture", "overview"):
            return "keyword"

        # Finding specific symbols benefits from hybrid.
        if intent in ("find_function", "implementation"):
            return "hybrid"

        # General questions benefit from vector search.
        if intent == "general":
            return "vector"

        # If there are specific code symbols, hybrid works best.
        if any(k[0].isupper() for k in keywords):
            return "hybrid"

        return "hybrid"