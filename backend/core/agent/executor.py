from __future__ import annotations

import logging
from typing import Any

from backend.core.agent.graph import QueryGraph
from backend.core.agent.planner import ExecutionPlan, Planner
from backend.core.agent.state import QueryState
from backend.core.agent.tools import BaseTool

logger = logging.getLogger(__name__)


class AgentExecutor:
    """High-level executor for the LangGraph query agent.

    Provides convenience methods for running the full workflow
    and for executing specific stages independently (plan / execute).
    """

    def __init__(self, graph: QueryGraph | None = None) -> None:
        self._graph = graph or QueryGraph()

    async def run(self, repository_id: str, question: str) -> QueryState:
        """Run the full agentic query workflow.

        Args:
            repository_id: The repository to query.
            question: The user's natural language question.

        Returns:
            Final ``QueryState`` with answer, sources, and execution trace.
        """
        initial_state = QueryState(
            repository_id=repository_id,
            question=question,
        )
        return await self._graph.run(initial_state)

    async def plan_only(
        self, question: str, planner: Planner | None = None
    ) -> ExecutionPlan:
        """Run only the planning stage.

        Args:
            question: The user's question.
            planner: Optional custom planner.

        Returns:
            An ``ExecutionPlan`` with selected tools and reasoning.
        """
        p = planner or Planner()
        return p.plan(question)

    async def execute_plan(
        self, repository_id: str, question: str, selected_tools: list[str]
    ) -> QueryState:
        """Execute a specific plan without the full graph.

        Args:
            repository_id: The repository to query.
            question: The user's question.
            selected_tools: List of tool names to execute.

        Returns:
            ``QueryState`` with tool results populated.
        """
        state = QueryState(
            repository_id=repository_id,
            question=question,
            selected_tools=selected_tools,
        )
        # Run a simplified version of the graph — just analysis + tools + merge.
        state = await self._graph._analyze_query(state)
        state = await self._graph._route_tools(state)
        state = await self._graph._merge_evidence(state)
        return state