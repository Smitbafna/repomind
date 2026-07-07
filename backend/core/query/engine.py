from __future__ import annotations

import logging
from dataclasses import dataclass, field

from backend.core.llm.client import LLMClient
from backend.core.llm.ollama_client import OllamaClient
from backend.core.query.analyzer import QueryAnalyzer
from backend.core.query.context_builder import ContextBuilder
from backend.core.query.prompt_builder import PromptBuilder
from backend.core.retrieval.hybrid_retriever import HybridRetriever
from backend.core.retrieval.keyword_retriever import KeywordRetriever
from backend.core.retrieval.retriever import BaseRetriever, RetrievalResult
from backend.core.retrieval.vector_retriever import VectorRetriever
from backend.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QueryResult:
    """Result of a full query pipeline execution."""

    answer: str
    sources: list[dict] = field(default_factory=list)
    intent: str = ""
    retrieval_strategy: str = ""
    keywords: list[str] = field(default_factory=list)


class QueryEngine:
    """Orchestrates the full question-answering pipeline.

    Pipeline:
        1. Analyze the query (intent, keywords, strategy).
        2. Retrieve relevant documents using the selected retriever.
        3. Build optimised context from retrieved documents.
        4. Construct prompts for the LLM.
        5. Generate an answer using the LLM.
        6. Return the answer with sources.
    """

    def __init__(
        self,
        vector_retriever: VectorRetriever | None = None,
        keyword_retriever: KeywordRetriever | None = None,
        hybrid_retriever: HybridRetriever | None = None,
        llm_client: LLMClient | None = None,
        query_analyzer: QueryAnalyzer | None = None,
        context_builder: ContextBuilder | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self._vector_retriever = vector_retriever or VectorRetriever()
        self._keyword_retriever = keyword_retriever or KeywordRetriever()
        self._hybrid_retriever = hybrid_retriever or HybridRetriever()
        self._llm_client = llm_client or OllamaClient()
        self._query_analyzer = query_analyzer or QueryAnalyzer()
        self._context_builder = context_builder or ContextBuilder()
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._settings = get_settings()

    async def answer(self, question: str) -> QueryResult:
        """Answer a question about the repository.

        Args:
            question: The user's natural language question.

        Returns:
            A ``QueryResult`` containing the answer, sources, and analysis.
        """
        # 1. Analyze the query.
        analysis = self._query_analyzer.analyze(question)
        logger.info(
            "Query analysis: intent=%s strategy=%s keywords=%s",
            analysis.intent,
            analysis.retrieval_strategy,
            analysis.keywords,
        )

        # 2. Retrieve relevant documents.
        retriever = self._get_retriever(analysis.retrieval_strategy)
        results = await retriever.retrieve(
            query=question,
            top_k=self._settings.default_top_k,
        )

        if not results:
            logger.info("No retrieval results for query: %s", question)
            # Still try to answer with no context.
            system, user = self._prompt_builder.build_full_prompt(
                question=question, context="", analysis=analysis,
            )
            response = await self._llm_client.generate(
                system_prompt=system, user_prompt=user,
            )
            return QueryResult(
                answer=response.content,
                intent=analysis.intent,
                retrieval_strategy=analysis.retrieval_strategy,
                keywords=analysis.keywords,
            )

        # 3. Build context and sources.
        context, sources = self._context_builder.build_context_with_sources(
            results=results,
            max_results=self._settings.default_top_k,
        )

        # 4. Build prompts.
        system, user = self._prompt_builder.build_full_prompt(
            question=question, context=context, analysis=analysis,
        )

        # 5. Generate answer.
        response = await self._llm_client.generate(
            system_prompt=system,
            user_prompt=user,
        )

        logger.info(
            "Generated answer (len=%d) for intent=%s",
            len(response.content),
            analysis.intent,
        )

        return QueryResult(
            answer=response.content,
            sources=sources,
            intent=analysis.intent,
            retrieval_strategy=analysis.retrieval_strategy,
            keywords=analysis.keywords,
        )

    def _get_retriever(self, strategy: str) -> BaseRetriever:
        """Get the retriever for the given strategy."""
        retriever_map = {
            "vector": self._vector_retriever,
            "keyword": self._keyword_retriever,
            "hybrid": self._hybrid_retriever,
        }
        return retriever_map.get(strategy, self._hybrid_retriever)