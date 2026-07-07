from __future__ import annotations

import logging
from typing import Any

from backend.core.agent.state import QueryState
from backend.core.agent.tools import BaseTool

logger = logging.getLogger(__name__)


class ToolRouter:
    """Executes only the required tools based on the execution plan.

    Does not execute every tool for every question.
    Wraps tool execution with timing and trace recording.
    """

    def __init__(self, tools: dict[str, BaseTool]) -> None:
        self._tools = tools

    async def execute_plan(
        self, state: QueryState, selected_tools: list[str]
    ) -> QueryState:
        """Execute only the selected tools in order.

        Args:
            state: The current query state.
            selected_tools: List of tool names to execute.

        Returns:
            Updated query state with tool results.
        """
        import time

        for tool_name in selected_tools:
            if tool_name not in self._tools:
                logger.warning("Unknown tool '%s', skipping", tool_name)
                continue

            tool = self._tools[tool_name]
            start = time.monotonic()

            try:
                logger.info("Executing tool '%s'…", tool_name)
                state = await tool.execute(state)
                elapsed = (time.monotonic() - start) * 1000
                self._record_tool_execution(state, tool_name, elapsed, None)
            except Exception as exc:
                elapsed = (time.monotonic() - start) * 1000
                error_msg = f"Tool '{tool_name}' failed: {exc}"
                logger.warning(error_msg)
                state.errors.append(error_msg)
                self._record_tool_execution(state, tool_name, elapsed, str(exc))

        return state

    def _record_tool_execution(
        self,
        state: QueryState,
        tool_name: str,
        latency_ms: float,
        error: str | None,
    ) -> None:
        """Record tool execution in the state trace."""
        state.tool_history.append({
            "tool": tool_name,
            "latency_ms": round(latency_ms, 2),
            "error": error,
        })
        state.latency_ms[tool_name] = round(latency_ms, 2)