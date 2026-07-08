from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _generate_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    """Represents an authenticated user."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_generate_uuid
    )
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    repositories: Mapped[list[Repository]] = relationship(
        "Repository", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class Repository(Base):
    """Represents a cloned git repository."""

    __tablename__ = "repositories"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_generate_uuid
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    owner: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    local_path: Mapped[str] = mapped_column(Text, nullable=False)
    default_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    github_last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    user: Mapped[User | None] = relationship("User", back_populates="repositories")

    # ── relationships ──────────────────────────────────────────
    files: Mapped[list[File]] = relationship(
        "File",
        back_populates="repository",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    code_files: Mapped[list[CodeFile]] = relationship(
        "CodeFile",
        back_populates="repository",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    relationships: Mapped[list[Relationship]] = relationship(
        "Relationship",
        back_populates="repository",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    commits: Mapped[list[Commit]] = relationship(
        "Commit",
        back_populates="repository",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    github_issues: Mapped[list[GitHubIssue]] = relationship(
        "GitHubIssue",
        back_populates="repository",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    github_pull_requests: Mapped[list[GitHubPullRequest]] = relationship(
        "GitHubPullRequest",
        back_populates="repository",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    github_reviews: Mapped[list[GitHubReview]] = relationship(
        "GitHubReview",
        back_populates="repository",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    github_comments: Mapped[list[GitHubComment]] = relationship(
        "GitHubComment",
        back_populates="repository",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    github_discussions: Mapped[list[GitHubDiscussion]] = relationship(
        "GitHubDiscussion",
        back_populates="repository",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    github_releases: Mapped[list[GitHubRelease]] = relationship(
        "GitHubRelease",
        back_populates="repository",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    github_labels: Mapped[list[GitHubLabel]] = relationship(
        "GitHubLabel",
        back_populates="repository",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Repository {self.owner}/{self.name}>"


class File(Base):
    """Represents a file within a cloned repository."""

    __tablename__ = "files"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_generate_uuid
    )
    repository_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    path: Mapped[str] = mapped_column(Text, nullable=False)
    extension: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_binary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ── relationships ──────────────────────────────────────────
    repository: Mapped[Repository] = relationship(
        "Repository", back_populates="files"
    )

    def __repr__(self) -> str:
        return f"<File {self.path} ({self.size}b)>"


class CodeFile(Base):
    """Represents a parsed source code file within a repository."""

    __tablename__ = "code_files"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_generate_uuid
    )
    repository_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    path: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False)

    # ── relationships ──────────────────────────────────────────
    repository: Mapped[Repository] = relationship(
        "Repository", back_populates="code_files"
    )
    classes: Mapped[list[Class]] = relationship(
        "Class",
        back_populates="code_file",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    functions: Mapped[list[Function]] = relationship(
        "Function",
        back_populates="code_file",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="Function.file_id",
    )
    imports: Mapped[list[Import]] = relationship(
        "Import",
        back_populates="code_file",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<CodeFile {self.path} ({self.language})>"


class Class(Base):
    """Represents a class extracted from a parsed source file."""

    __tablename__ = "classes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_generate_uuid
    )
    file_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("code_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    line_start: Mapped[int] = mapped_column(Integer, nullable=False)
    line_end: Mapped[int] = mapped_column(Integer, nullable=False)
    docstring: Mapped[str | None] = mapped_column(Text, nullable=True)
    decorators: Mapped[str | None] = mapped_column(Text, nullable=True)
    bases: Mapped[str | None] = mapped_column(Text, nullable=True)
    methods: Mapped[list[Function]] = relationship(
        "Function",
        back_populates="parent_class",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="Function.class_id",
    )

    # ── relationships ──────────────────────────────────────────
    code_file: Mapped[CodeFile] = relationship(
        "CodeFile", back_populates="classes"
    )

    def __repr__(self) -> str:
        return f"<Class {self.name} (lines {self.line_start}-{self.line_end})>"


class Function(Base):
    """Represents a function or method extracted from a parsed source file."""

    __tablename__ = "functions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_generate_uuid
    )
    file_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("code_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    class_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("classes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    line_start: Mapped[int] = mapped_column(Integer, nullable=False)
    line_end: Mapped[int] = mapped_column(Integer, nullable=False)
    is_async: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    docstring: Mapped[str | None] = mapped_column(Text, nullable=True)
    decorators: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── relationships ──────────────────────────────────────────
    code_file: Mapped[CodeFile] = relationship(
        "CodeFile", back_populates="functions", foreign_keys=[file_id]
    )
    parent_class: Mapped[Class | None] = relationship(
        "Class", back_populates="methods", foreign_keys=[class_id]
    )

    def __repr__(self) -> str:
        return f"<Function {self.name} (lines {self.line_start}-{self.line_end})>"


class Import(Base):
    """Represents an import statement extracted from a parsed source file."""

    __tablename__ = "imports"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_generate_uuid
    )
    file_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("code_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    module: Mapped[str] = mapped_column(Text, nullable=False)
    imported_name: Mapped[str] = mapped_column(String(255), nullable=False)
    alias: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── relationships ──────────────────────────────────────────
    code_file: Mapped[CodeFile] = relationship(
        "CodeFile", back_populates="imports"
    )

    def __repr__(self) -> str:
        return f"<Import {self.module}.{self.imported_name}>"


class Relationship(Base):
    """Represents a relationship between two code symbols."""

    __tablename__ = "relationships"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_generate_uuid
    )
    repository_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_symbol: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    target_symbol: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_file: Mapped[str] = mapped_column(Text, nullable=False, default="")
    target_file: Mapped[str] = mapped_column(Text, nullable=False, default="")
    line_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── relationships ──────────────────────────────────────────
    repository: Mapped[Repository] = relationship(
        "Repository", back_populates="relationships"
    )

    def __repr__(self) -> str:
        return (
            f"<Relationship {self.source_symbol} "
            f"{self.relationship_type} {self.target_symbol}>"
        )


class Commit(Base):
    """Represents a single git commit."""

    __tablename__ = "commits"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_generate_uuid
    )
    repository_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hash: Mapped[str] = mapped_column(String(40), nullable=False, index=True, unique=True)
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    author_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    commit_message: Mapped[str] = mapped_column(Text, nullable=False)
    committed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    parent_hash: Mapped[str | None] = mapped_column(String(40), nullable=True)
    branch: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # ── relationships ──────────────────────────────────────────
    repository: Mapped[Repository] = relationship(
        "Repository", back_populates="commits"
    )
    files: Mapped[list[CommitFile]] = relationship(
        "CommitFile",
        back_populates="commit",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    symbol_relationships: Mapped[list[CommitRelationship]] = relationship(
        "CommitRelationship",
        back_populates="commit",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Commit {self.hash[:8]} by {self.author_name} "
            f"on {self.committed_at}>"
        )


class CommitFile(Base):
    """Represents a file changed in a commit."""

    __tablename__ = "commit_files"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_generate_uuid
    )
    commit_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("commits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    change_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # ADDED, MODIFIED, RENAMED, DELETED
    additions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deletions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── relationships ──────────────────────────────────────────
    commit: Mapped[Commit] = relationship(
        "Commit", back_populates="files"
    )

    def __repr__(self) -> str:
        return (
            f"<CommitFile {self.file_path} "
            f"{self.change_type} +{self.additions}-{self.deletions}>"
        )


class CommitRelationship(Base):
    """Represents how a commit affects a code symbol."""

    __tablename__ = "commit_relationships"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_generate_uuid
    )
    commit_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("commits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symbol_name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # CREATED, MODIFIED, RENAMED, DELETED

    # ── relationships ──────────────────────────────────────────
    commit: Mapped[Commit] = relationship(
        "Commit", back_populates="symbol_relationships"
    )

    def __repr__(self) -> str:
        return (
            f"<CommitRelationship {self.symbol_name} "
            f"{self.relationship_type}>"
        )


class GitHubIssue(Base):
    """Represents a GitHub issue synced for a repository."""

    __tablename__ = "github_issues"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_generate_uuid
    )
    repository_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="open")
    author_login: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    html_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    labels: Mapped[str | None] = mapped_column(Text, nullable=True)
    pull_request_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    repository: Mapped[Repository] = relationship(
        "Repository", back_populates="github_issues"
    )


class GitHubPullRequest(Base):
    """Represents a GitHub pull request synced for a repository."""

    __tablename__ = "github_pull_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_generate_uuid
    )
    repository_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="open")
    author_login: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    merged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    draft: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    html_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    labels: Mapped[str | None] = mapped_column(Text, nullable=True)
    merge_commit_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)
    base_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    head_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)

    repository: Mapped[Repository] = relationship(
        "Repository", back_populates="github_pull_requests"
    )


class GitHubReview(Base):
    """Represents a review attached to a GitHub pull request."""

    __tablename__ = "github_reviews"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_generate_uuid
    )
    repository_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pull_request_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    reviewer_login: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="commented")
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    commit_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    html_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    repository: Mapped[Repository] = relationship(
        "Repository", back_populates="github_reviews"
    )


class GitHubComment(Base):
    """Represents an issue or PR comment synced from GitHub."""

    __tablename__ = "github_comments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_generate_uuid
    )
    repository_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_type: Mapped[str] = mapped_column(String(50), nullable=False, default="issue")
    subject_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    author_login: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    html_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    commit_id: Mapped[str | None] = mapped_column(String(40), nullable=True)

    repository: Mapped[Repository] = relationship(
        "Repository", back_populates="github_comments"
    )


class GitHubDiscussion(Base):
    """Represents a GitHub discussion synced for a repository."""

    __tablename__ = "github_discussions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_generate_uuid
    )
    repository_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="open")
    author_login: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    html_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    repository: Mapped[Repository] = relationship(
        "Repository", back_populates="github_discussions"
    )


class GitHubRelease(Base):
    """Represents a GitHub release synced for a repository."""

    __tablename__ = "github_releases"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_generate_uuid
    )
    repository_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tag_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    prerelease: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    html_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    repository: Mapped[Repository] = relationship(
        "Repository", back_populates="github_releases"
    )


class GitHubLabel(Base):
    """Represents a GitHub label synced for a repository."""

    __tablename__ = "github_labels"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_generate_uuid
    )
    repository_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    repository: Mapped[Repository] = relationship(
        "Repository", back_populates="github_labels"
    )