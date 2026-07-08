from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field


class JobStatus(str, enum.Enum):
    """Status of a background job."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStep(str, enum.Enum):
    """Steps in the import pipeline."""

    QUEUED = "Queued"
    CLONING = "Cloning"
    SCANNING = "Scanning"
    PARSING = "Parsing"
    RELATIONSHIPS = "Relationships"
    GIT = "Git"
    GITHUB = "GitHub"
    EMBEDDINGS = "Embeddings"
    FINISHED = "Finished"


@dataclass
class Job:
    """Represents a background job."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0  # 0.0 to 100.0
    current_step: str = ""
    message: str = ""
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    elapsed_time: float = 0.0
    result: dict | None = None
    errors: list[str] = field(default_factory=list)

    def start(self) -> None:
        """Mark job as running."""
        self.status = JobStatus.RUNNING
        self.started_at = time.time()

    def complete(self, result: dict | None = None) -> None:
        """Mark job as completed."""
        self.status = JobStatus.COMPLETED
        self.completed_at = time.time()
        self.elapsed_time = (self.completed_at - (self.started_at or self.created_at))
        self.progress = 100.0
        self.current_step = JobStep.FINISHED.value
        self.result = result

    def fail(self, error: str) -> None:
        """Mark job as failed."""
        self.status = JobStatus.FAILED
        self.completed_at = time.time()
        self.elapsed_time = (self.completed_at - (self.started_at or self.created_at))
        self.errors.append(error)

    def update(self, progress: float, step: str, message: str = "") -> None:
        """Update job progress."""
        self.progress = progress
        self.current_step = step
        if message:
            self.message = message

    def to_dict(self) -> dict:
        """Serialize job to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "status": self.status.value,
            "progress": self.progress,
            "current_step": self.current_step,
            "message": self.message,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "elapsed_time": self.elapsed_time,
            "result": self.result,
            "errors": self.errors,
        }