from __future__ import annotations

import logging
import time
from typing import Any

from langgraph.graph import END, StateGraph

from backend.core.crag.evaluator import RetrievalEvaluator
from backend.core.crag.models import CorrectiveAction, RetrievalState
from backend.core.crag.planner import CorrectivePlanner
from backend.core.crag.retriever import CRAGRetriever
from backend.core.llm.client import LLMProvider
from backend.core.query.analyzer import QueryAnalysis, QueryAnalyzer
from backend.core.query.context_builder import ContextBuilder
from backend.core.query.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class CRAGGraph:
    """LangGraph workflow for Corrective RAG.

    Flow:
        1. AnalyzeQuery — determine intent, keywords, strategy.
        2. InitialRetrieval — run initial retrieval.
        3. EvaluateRetrieval — assess quality.
        4. ConfidenceCheck — decide next step.
        5. CorrectiveRetrieval — if low confidence, run corrective actions.
        6. MergeEvidence — combine all evidence.
        7. GenerateAnswer — create answer from context.
        8. ValidateAnswer — verify evidence support.
        9. ReturnResponse — final output.
    """

    def __init__(
        self,
        analyzer: QueryAnalyzer | None = None,
        crag_retriever: CRAGRetriever | None = None,
        evaluator: RetrievalEvaluator | None = None,
        corrective_planner: CorrectivePlanner | None = None,
        context_builder: ContextBuilder | None = None,
        prompt_builder: PromptBuilder | None = None,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self._analyzer = analyzer or QueryAnalyzer()
        self._crag_retriever = crag_retriever or CRAGRetriever()
        self._evaluator = evaluator or RetrievalEvaluator()
        self._corrective_planner = corrective_planner or CorrectivePlanner()
        self._context_builder = context_builder or ContextBuilder()
        self._prompt_builder = prompt_builder or PromptBuilder()
        from backend.core.llm.factory import get_llm_provider
        self._llm_client = llm_provider or get_llm_provider()
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the CRAG LangGraph workflow."""
        workflow = StateGraph(RetrievalState)

        workflow.add_node("AnalyzeQuery", self._analyze_query)
        workflow.add_node("InitialRetrieval", self._initial_retrieval)
        workflow.add_node("EvaluateRetrieval", self._evaluate_retrieval)
        workflow.add_node("CorrectiveRetrieval", self._corrective_retrieval)
        workflow.add_node("MergeEvidence", self._merge_evidence)
        workflow.add_node("GenerateAnswer", self._generate_answer)
        workflow.add_node("ValidateAnswer", self._validate_answer)
        workflow.add_node("ReturnResponse", self._return_response)

        workflow.set_entry_point("AnalyzeQuery")
        workflow.add_edge("AnalyzeQuery", "InitialRetrieval")
        workflow.add_edge("InitialRetrieval", "EvaluateRetrieval")
        workflow.add_conditional_edges(
            "EvaluateRetrieval",
            self._decide_after_evaluation,
            {
                "answer": "MergeEvidence",
                "correct": "CorrectiveRetrieval",
            },
        )
        workflow.add_edge("CorrectiveRetrieval", "EvaluateRetrieval")
        workflow.add_edge("MergeEvidence", "GenerateAnswer")
        workflow.add_edge("GenerateAnswer", "ValidateAnswer")
        workflow.add_conditional_edges(
            "ValidateAnswer",
            self._decide_after_validation,
            {
                "valid": "ReturnResponse",
                "invalid": "GenerateAnswer",
                "fail": END,
            },
        )
        workflow.add_edge("ReturnResponse", END)

        return workflow.compile()

    async def run(self, state: RetrievalState) -> RetrievalState:
        """Execute the CRAG workflow.

        Args:
            state: Initial retrieval state.

        Returns:
            Final state with answer and sources.
        """
        result_dict = await self._graph.ainvoke(state)
        
        # Convert dict to RetrievalState if needed
        if isinstance(result_dict, dict):
            result = RetrievalState(
                repository_id=state.repository_id,
                question=state.question,
                answer=result_dict.get("answer", ""),
                confidence=result_dict.get("confidence", 0.0),
                answer_valid=result_dict.get("answer_valid", False),
                validation_message=result_dict.get("validation_message", ""),
                context=result_dict.get("context", ""),
                sources=result_dict.get("sources", []),
                retrieved_documents=result_dict.get("retrieved_documents", []),
                graph_results=result_dict.get("graph_results", []),
                git_results=result_dict.get("git_results", []),
                relationship_results=result_dict.get("relationship_results", []),
                retrieval_history=result_dict.get("retrieval_history", []),
                execution_trace=result_dict.get("execution_trace", []),
                errors=result_dict.get("errors", []),
                intent=result_dict.get("intent", ""),
                retrieval_strategy=result_dict.get("retrieval_strategy", ""),
                keywords=result_dict.get("keywords", []),
                filters=result_dict.get("filters", {}),
                max_attempts=state.max_attempts,
                attempt_number=result_dict.get("attempt_number", 0),
                missing_information=result_dict.get("missing_information", ""),
                retrieval_score=result_dict.get("retrieval_score", 0.0),
                latency_ms=result_dict.get("latency_ms", {}),
            )
        else:
            result = result_dict
        
        return result

    # ── node implementations ──────────────────────────────────

    async def _analyze_query(self, state: RetrievalState) -> RetrievalState:
        """Analyze the query to determine intent and strategy."""
        analysis = self._analyzer.analyze(state.question)
        state.intent = analysis.intent
        state.retrieval_strategy = analysis.retrieval_strategy
        state.keywords = analysis.keywords
        state.filters = analysis.filters
        state.execution_trace.append({
            "node": "AnalyzeQuery",
            "intent": state.intent,
            "strategy": state.retrieval_strategy,
            "keywords": state.keywords,
        })
        return state

    async def _initial_retrieval(self, state: RetrievalState) -> RetrievalState:
        """Run initial hybrid retrieval."""
        state.attempt_number = 1
        await self._crag_retriever.retrieve(state, CorrectiveAction.RUN_HYBRID)
        return state

    async def _evaluate_retrieval(self, state: RetrievalState) -> RetrievalState:
        """Evaluate current retrieval quality."""
        evaluation = self._evaluator.evaluate(state)
        state.confidence = evaluation.confidence
        state.missing_information = evaluation.missing_information
        state.retrieval_score = evaluation.confidence

        state.execution_trace.append({
            "node": "EvaluateRetrieval",
            "confidence": state.confidence,
            "missing": state.missing_information,
            "attempt": state.attempt_number,
        })
        return state

    async def _corrective_retrieval(self, state: RetrievalState) -> RetrievalState:
        """Run corrective retrieval if confidence is low."""
        evaluation = self._evaluator.evaluate(state)
        actions = self._corrective_planner.plan(state, evaluation)

        for action in actions:
            if action == CorrectiveAction.GENERATE_ANSWER:
                break
            await self._crag_retriever.retrieve(state, action)

        return state

    async def _merge_evidence(self, state: RetrievalState) -> RetrievalState:
        """Merge all evidence into unified context."""
        all_docs = (
            state.retrieved_documents
            + state.graph_results
            + state.git_results
            + state.relationship_results
        )

        if not all_docs:
            state.context = ""
            state.sources = []
            state.execution_trace.append({
                "node": "MergeEvidence",
                "total_docs": 0,
                "note": "No evidence retrieved",
            })
            return state

        # Deduplicate by content.
        seen: set[int] = set()
        unique_docs: list[dict] = []
        for doc in all_docs:
            content = str(doc.get("content", "") or doc.get("commit_message", "") or doc.get("symbol", ""))
            content_hash = hash(content[:200])
            if content_hash not in seen:
                seen.add(content_hash)
                unique_docs.append(doc)

        # Sort by score descending.
        unique_docs.sort(key=lambda d: d.get("score", 0), reverse=True)

        # Build context.
        sections: list[str] = []
        sources: list[dict] = []
        for doc in unique_docs[:10]:
            location = doc.get("file", "") or doc.get("author_name", "") or doc.get("label", "")
            content = doc.get("content", "") or doc.get("commit_message", "") or ""
            if location:
                sections.append(f"=== From {location} ===\n{content}")
                sources.append({
                    "file": doc.get("file", ""),
                    "symbol": doc.get("symbol", "") or doc.get("id", ""),
                    "score": doc.get("score", 0),
                    "document_type": doc.get("document_type", "unknown"),
                })

        state.context = "\n\n".join(sections)
        state.sources = sources
        state.execution_trace.append({
            "node": "MergeEvidence",
            "total_docs": len(all_docs),
            "unique_docs": len(unique_docs),
            "context_length": len(state.context),
        })
        return state

    async def _generate_answer(self, state: RetrievalState) -> RetrievalState:
        """Generate answer using LLM with merged context."""
        analysis = QueryAnalysis(
            intent=state.intent,
            keywords=state.keywords,
            filters=state.filters,
            retrieval_strategy=state.retrieval_strategy,
        )

        system, user = self._prompt_builder.build_full_prompt(
            question=state.question,
            context=state.context,
            analysis=analysis,
        )

        try:
            response = await self._llm_client.generate(
                system_prompt=system,
                user_prompt=user,
            )
            state.answer = response.content
        except (ConnectionError, RuntimeError) as exc:
            error_msg = f"LLM generation failed: {exc}"
            state.errors.append(error_msg)
            state.answer = "I encountered an error generating the answer. Please try again."

        state.execution_trace.append({
            "node": "GenerateAnswer",
            "answer_length": len(state.answer),
            "error_count": len(state.errors),
        })
        return state

    async def _validate_answer(self, state: RetrievalState) -> RetrievalState:
        """Validate the generated answer."""
        if not state.context and state.answer:
            state.validation_message = (
                "Insufficient evidence. Answer may not be repository-specific."
            )
            state.answer_valid = False
        elif state.errors:
            state.validation_message = f"Errors occurred: {'; '.join(state.errors)}"
            state.answer_valid = False
        else:
            state.answer_valid = True
            state.validation_message = "Answer validated with evidence."

        state.execution_trace.append({
            "node": "ValidateAnswer",
            "valid": state.answer_valid,
            "message": state.validation_message,
        })
        return state

    async def _return_response(self, state: RetrievalState) -> RetrievalState:
        """Finalise and return the response."""
        state.execution_trace.append({
            "node": "ReturnResponse",
            "total_latency_ms": state.latency_ms,
        })
        return state

    def _decide_after_evaluation(self, state: RetrievalState) -> str:
        """Decide next step after evaluation."""
        if state.confidence >= 0.7 or state.attempt_number >= state.max_attempts:
            return "answer"
        return "correct"

    def _decide_after_validation(self, state: RetrievalState) -> str:
        """Decide next step after validation."""
        if state.answer_valid:
            return "valid"
        if len(state.errors) < 3:
            return "invalid"
        return "fail"