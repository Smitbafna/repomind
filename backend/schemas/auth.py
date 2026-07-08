from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Request body for user registration."""

    email: str = Field(..., description="User email address", examples=["user@example.com"])
    password: str = Field(..., min_length=6, description="User password")


class LoginRequest(BaseModel):
    """Request body for user login."""

    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """Response containing a JWT access token."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Response containing user information."""

    id: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class JobResponse(BaseModel):
    """Response containing job status information."""

    id: str
    type: str
    status: str
    progress: float
    current_step: str = ""
    message: str = ""
    created_at: float
    started_at: float | None = None
    completed_at: float | None = None
    elapsed_time: float = 0.0
    result: dict | None = None
    errors: list[str] = Field(default_factory=list)


class ImportRequest(BaseModel):
    """Request body for the unified import endpoint."""

    url: str = Field(
        ...,
        description="GitHub repository URL",
        examples=["https://github.com/fastapi/fastapi"],
    )


class ImportResponse(BaseModel):
    """Response returned after initiating a repository import."""

    job_id: str
    repository_id: str | None = None
    status: str = "queued"


class StreamEvent(BaseModel):
    """An SSE event sent during streaming responses."""

    event: str
    data: str