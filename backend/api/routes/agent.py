from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import (
    get_agent_executor,
    get_db,
    get_planner,
)
from backend.core.agent.executor import AgentExecutor
from backend.core.agent.planner import Planner
from backend.core.agent.state import QueryState
from backend.database.repositories import RepositoryRepository
from backend.schemas.agent import (
    AgentAskResponse,
    ExecuteResponse,
    ExecutionStep,
    PlanResponse,
)
from backend.schemas.query import AskRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repositories", tags=["agent"])


@router.post("/{repository_id}/ask", response_model=AgentAskResponse)
async def agent_ask_repository(
    repository_id: str,
    payload: AskRequest,
    session: AsyncSession = Depends(get_db),
    agent_executor: AgentExecutor = Depends(get_agent_executor),
) -> AgentAskResponse:
    """Ask a question using the LangGraph agentic pipeline.

    Internally runs the full execution graph:
    Analyze → Plan → RouteTools → MergeEvidence → GenerateAnswer → Validate → Return
    """
    repo_repo = RepositoryRepository(session)
    repo = await repo_repo.get_by_id(repository_id)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository not found: {repository_id}",
        )

    try:
        result: QueryState = await agent_executor.run(
            repository_id=repository_id,
            question=payload.question,
        )

        return AgentAskResponse(
            repository_id=repository_id,
            question=payload.question,
            answer=result.answer,
            sources=result.sources,
            intent=result.intent,
            retrieval_strategy=result.retrieval_strategy,
            selected_tools=result.selected_tools,
            execution_plan=result.execution_plan,
            execution_trace=[
                ExecutionStep(
                    node=t.get("node", ""),
                    tool=t.get("tool", ""),
                    result_count=t.get("result_count", 0),
                    latency_ms=t.get("latency_ms", 0.0),
                    error=t.get("error"),
                )
                for t in result.execution_trace + result.tool_history
            ],
            total_latency_ms=sum(result.latency_ms.values()),
        )
    except (ConnectionError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post("/{repository_id}/plan", response_model=PlanResponse)
async def plan_query(
    repository_id: str,
    payload: AskRequest,
    session: AsyncSession = Depends(get_db),
    planner: Planner = Depends(get_planner),
) -> PlanResponse:
    """Return the execution plan for a question without running it."""
    repo_repo = RepositoryRepository(session)
    repo = await repo_repo.get_by_id(repository_id)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository not found: {repository_id}",
        )

    plan = await agent_executor.plan_only(payload.question, planner)
    return PlanResponse(
        execution_plan=plan.reasoning,
        selected_tools=plan.selected_tools,
        reasoning=plan.reasoning,
    )


@router.post("/{repository_id}/execute", response_model=ExecuteResponse)
async def execute_plan(
    repository_id: str,
    payload: AskRequest,
    session: AsyncSession = Depends(get_db),
    agent_executor: AgentExecutor = Depends(get_agent_executor),
) -> ExecuteResponse:
    """Execute a plan and return the trace without generating an answer."""
    repo_repo = RepositoryRepository(session)
    repo = await repo_repo.get_by_id(repository_id)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository not found: {repository_id}",
        )

    try:
        # Get plan, then execute tools.
        plan = await agent_executor.plan_only(payload.question)
        state = await agent_executor.execute_plan(
            repository_id=repository_id,
            question=payload.question,
            selected_tools=plan.selected_tools,
        )

        return ExecuteResponse(
            execution_trace=[
                ExecutionStep(
                    node=t.get("node", ""),
                    tool=t.get("tool", ""),
                    result_count=t.get("result_count", 0),
                    latency_ms=state.latency_ms.get(t.get("tool", ""), 0.0),
                    error=t.get("error"),
                )
                for t in state.execution_trace
            ],
            tool_outputs={
                "retrieved_documents": state.retrieved_documents,
                "git_results": state.git_results,
                "relationship_results": state.relationship_results,
            },
            total_latency_ms=sum(state.latency_ms.values()),
            errors=state.errors,
        )
    except (ConnectionError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc