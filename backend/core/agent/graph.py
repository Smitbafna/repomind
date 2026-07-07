from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from backend.core.agent.planner import Planner
from backend.core.agent.router import ToolRouter
from backend.core.agent.state import QueryState
from backend.core.agent.tools import (
    BaseTool,
    BlameTool,
    GitHistoryTool,
    GitHubRetrieverTool,
    HybridRetrieverTool,
    KeywordRetrieverTool,
    RelationshipRetrieverTool,
    SemanticRetrieverTool,
    TimelineTool,
)
from backend.core.llm.client import LLMClient
from backend.core.llm.ollama_client import OllamaClient
from backend.core.query.analyzer import QueryAnalyzer
from backend.core.query.context_builder import ContextBuilder
from backend.core.query.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class QueryGraph:
    """LangGraph workflow for orchestrating the query pipeline.

    Nodes:
        1. AnalyzeQuery — determine intent, keywords, strategy.
        2. PlanExecution — decide which tools to use.
        3. RouteTools — execute only the required tools.
        4. MergeEvidence — deduplicate, rank, build unified context.
        5. GenerateAnswer — construct prompt and call LLM.
        6. ValidateAnswer — verify context and evidence support.
        7. ReturnResponse — final state with answer and sources.
    """

    def __init__(
        self,
        planner: Planner | None = None,
        tool_router: ToolRouter | None = None,
        analyzer: QueryAnalyzer | None = None,
        context_builder: ContextBuilder | None = None,
        prompt_builder: PromptBuilder | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self._planner = planner or Planner()
        self._tool_router = tool_router or ToolRouter(self._build_default_tools())
        self._analyzer = analyzer or QueryAnalyzer()
        self._context_builder = context_builder or ContextBuilder()
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._llm_client = llm_client or OllamaClient()
        self._graph = self._build_graph()

    def _build_default_tools(self) -> dict[str, BaseTool]:
        """Create the default tool registry used by the agent."""
        return {
            "semantic_retriever": SemanticRetrieverTool(),
            "keyword_retriever": KeywordRetrieverTool(),
            "hybrid_retriever": HybridRetrieverTool(),
            "relationship_retriever": RelationshipRetrieverTool(),
            "git_history_tool": GitHistoryTool(),
            "blame_tool": BlameTool(),
            "timeline_tool": TimelineTool(),
            "github_retriever_tool": GitHubRetrieverTool(),
        }

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(QueryState)

        # Register nodes.
        workflow.add_node("AnalyzeQuery", self._analyze_query)
        workflow.add_node("PlanExecution", self._plan_execution)
        workflow.add_node("RouteTools", self._route_tools)
        workflow.add_node("MergeEvidence", self._merge_evidence)
        workflow.add_node("GenerateAnswer", self._generate_answer)
        workflow.add_node("ValidateAnswer", self._validate_answer)
        workflow.add_node("ReturnResponse", self._return_response)

        # Define edges.
        workflow.set_entry_point("AnalyzeQuery")
        workflow.add_edge("AnalyzeQuery", "PlanExecution")
        workflow.add_edge("PlanExecution", "RouteTools")
        workflow.add_edge("RouteTools", "MergeEvidence")
        workflow.add_edge("MergeEvidence", "GenerateAnswer")
        workflow.add_edge("GenerateAnswer", "ValidateAnswer")
        workflow.add_conditional_edges(
            "ValidateAnswer",
            self._decide_after_validation,
            {
                "valid": "ReturnResponse",
                "invalid": "GenerateAnswer",  # Retry with validation feedback
                "fail": END,
            },
        )
        workflow.add_edge("ReturnResponse", END)

        return workflow.compile()

    async def run(self, state: QueryState) -> QueryState:
        """Execute the full workflow.

        Args:
            state: Initial query state with repository_id and question.

        Returns:
            Final query state with answer, sources, and execution trace.
        """
        result_dict = await self._graph.ainvoke(state)
        
        # Convert dict to QueryState if needed
        if isinstance(result_dict, dict):
            result = QueryState(
                repository_id=state.repository_id,
                question=state.question,
                answer=result_dict.get("answer", ""),
                sources=result_dict.get("sources", []),
                intent=result_dict.get("intent", ""),
                retrieval_strategy=result_dict.get("retrieval_strategy", ""),
                selected_tools=result_dict.get("selected_tools", []),
                execution_plan=result_dict.get("execution_plan", ""),
                execution_trace=result_dict.get("execution_trace", []),
                tool_history=result_dict.get("tool_history", []),
                context=result_dict.get("context", ""),
                errors=result_dict.get("errors", []),
                validation_message=result_dict.get("validation_message", ""),
                answer_valid=result_dict.get("answer_valid", False),
                latency_ms=result_dict.get("latency_ms", {}),
                retrieved_documents=result_dict.get("retrieved_documents", []),
                relationship_results=result_dict.get("relationship_results", []),
                git_results=result_dict.get("git_results", []),
                keywords=result_dict.get("keywords", []),
                filters=result_dict.get("filters", {}),
            )
        else:
            result = result_dict
        
        return result

    # ── node implementations ──────────────────────────────────

    async def _analyze_query(self, state: QueryState) -> QueryState:
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

    async def _plan_execution(self, state: QueryState) -> QueryState:
        """Plan which tools to use."""
        plan = self._planner.plan(state.question)
        state.selected_tools = plan.selected_tools
        state.execution_plan = plan.reasoning
        state.execution_trace.append({
            "node": "PlanExecution",
            "selected_tools": state.selected_tools,
            "reasoning": state.execution_plan,
        })
        return state

    async def _route_tools(self, state: QueryState) -> QueryState:
        """Execute only the required tools."""
        import time
        start = time.monotonic()
        state = await self._tool_router.execute_plan(state, state.selected_tools)
        elapsed = (time.monotonic() - start) * 1000
        state.latency_ms["total_tools"] = round(elapsed, 2)
        return state

    async def _merge_evidence(self, state: QueryState) -> QueryState:
        """Merge evidence from all tools into unified context."""
        all_docs = (
            state.retrieved_documents
            + state.relationship_results
            + state.git_results
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
            content = doc.get("content", "") or doc.get("commit_message", "") or doc.get("hash", "")
            content_hash = hash(str(content)[:200])
            if content_hash not in seen:
                seen.add(content_hash)
                unique_docs.append(doc)

        # Sort by score descending where available.
        unique_docs.sort(key=lambda d: d.get("score", 0), reverse=True)

        # Build context string.
        sections: list[str] = []
        sources: list[dict] = []
        for doc in unique_docs[:10]:
            location = doc.get("file", "") or doc.get("author_name", "")
            symbol = doc.get("symbol", "")
            content = doc.get("content", "") or doc.get("commit_message", "") or ""
            if location:
                sections.append(f"=== From {location} ===\n{content}")
                sources.append({
                    "file": doc.get("file", ""),
                    "symbol": doc.get("symbol", ""),
                    "score": doc.get("score", 0),
                    "document_type": doc.get("document_type", "git"),
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

    async def _generate_answer(self, state: QueryState) -> QueryState:
        """Generate answer using LLM with merged context."""
        from backend.core.query.analyzer import QueryAnalysis

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

    async def _validate_answer(self, state: QueryState) -> QueryState:
        """Validate the generated answer."""
        if not state.context and state.answer:
            state.validation_message = (
                "Answer generated without context. May not be repository-specific."
            )
            state.answer_valid = True  # Allow through but note it
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

    async def _return_response(self, state: QueryState) -> QueryState:
        """Finalise and return the response."""
        state.execution_trace.append({
            "node": "ReturnResponse",
            "total_latency_ms": state.latency_ms,
        })
        return state

    def _decide_after_validation(self, state: QueryState) -> str:
        """Decide next step after validation."""
        if state.answer_valid:
            return "valid"
        if len(state.errors) < 3:
            return "invalid"
        return "fail"