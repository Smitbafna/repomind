from __future__ import annotations

from pydantic import BaseModel, Field


class PlanResponse(BaseModel):
    """Response returned from the plan endpoint."""

    execution_plan: str
    selected_tools: list[str]
    reasoning: str


class ExecutionStep(BaseModel):
    """A single step in the execution trace."""

    node: str = ""
    tool: str = ""
    result_count: int = 0
    latency_ms: float = 0.0
    error: str | None = None


class ExecuteResponse(BaseModel):
    """Response returned from the execute endpoint."""

    execution_trace: list[ExecutionStep]
    tool_outputs: dict[str, list[dict]] = Field(default_factory=dict)
    total_latency_ms: float = 0.0
    errors: list[str] = Field(default_factory=list)


class AgentAskResponse(BaseModel):
    """Response from the agentic ask endpoint."""

    repository_id: str
    question: str
    answer: str
    sources: list[dict]
    intent: str = ""
    retrieval_strategy: str = ""
    selected_tools: list[str] = Field(default_factory=list)
    execution_plan: str = ""
    execution_trace: list[ExecutionStep] = Field(default_factory=list)
    total_latency_ms: float = 0.0