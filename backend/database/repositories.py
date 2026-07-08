from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database.models import (
    Class,
    CodeFile,
    Commit,
    CommitFile,
    CommitRelationship,
    File,
    Function,
    Import,
    Relationship,
    Repository,
    User,
)


class UserRepository:
    """Data-access layer for the ``users`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> User:
        """Persist a new user row."""
        self._session.add(user)
        await self._session.flush()
        return user

    async def get_by_id(self, user_id: str) -> User | None:
        """Look up a user by primary key."""
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        """Look up a user by email address."""
        stmt = select(User).where(User.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


class RepositoryRepository:
    """Data-access layer for the ``repositories`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, repo: Repository) -> Repository:
        """Persist a new repository row."""
        self._session.add(repo)
        await self._session.flush()
        return repo

    async def get_by_id(self, repo_id: str) -> Repository | None:
        """Look up a repository by its primary key."""
        return await self._session.get(Repository, repo_id)

    async def list_all(self) -> Sequence[Repository]:
        """Return every repository ordered by creation time descending."""
        stmt = select(Repository).order_by(Repository.created_at.desc())
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_by_user(self, user_id: str) -> Sequence[Repository]:
        """Return repositories belonging to a user."""
        stmt = (
            select(Repository)
            .where(Repository.user_id == user_id)
            .order_by(Repository.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def delete(self, repo: Repository) -> None:
        """Remove a repository row."""
        await self._session.delete(repo)
        await self._session.flush()


class FileRepository:
    """Data-access layer for the ``files`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, file_record: File) -> File:
        """Persist a new file row."""
        self._session.add(file_record)
        await self._session.flush()
        return file_record

    async def add_many(self, file_records: list[File]) -> list[File]:
        """Bulk-persist file rows."""
        self._session.add_all(file_records)
        await self._session.flush()
        return file_records

    async def get_by_repository(self, repository_id: str) -> Sequence[File]:
        """Return all files belonging to a repository."""
        stmt = (
            select(File)
            .where(File.repository_id == repository_id)
            .order_by(File.path)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_by_repository(self, repository_id: str) -> int:
        """Return the number of files in a repository."""
        stmt = (
            select(File)
            .where(File.repository_id == repository_id)
            .with_only_columns(File.id)
        )
        result = await self._session.execute(stmt)
        return len(result.all())

    async def delete_by_repository(self, repository_id: str) -> None:
        """Delete all files belonging to a repository."""
        stmt = File.__table__.delete().where(  # type: ignore[attr-defined]
            File.repository_id == repository_id
        )
        await self._session.execute(stmt)
        await self._session.flush()


class CodeFileRepository:
    """Data-access layer for the ``code_files`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, code_file: CodeFile) -> CodeFile:
        """Persist a new code file row."""
        self._session.add(code_file)
        await self._session.flush()
        return code_file

    async def add_many(self, code_files: list[CodeFile]) -> list[CodeFile]:
        """Bulk-persist code file rows."""
        self._session.add_all(code_files)
        await self._session.flush()
        return code_files

    async def get_by_repository(self, repository_id: str) -> Sequence[CodeFile]:
        """Return all code files belonging to a repository with eager-loaded relationships."""
        stmt = (
            select(CodeFile)
            .where(CodeFile.repository_id == repository_id)
            .options(
                selectinload(CodeFile.classes).selectinload(Class.methods),
                selectinload(CodeFile.functions),
                selectinload(CodeFile.imports),
            )
            .order_by(CodeFile.path)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, code_file_id: str) -> CodeFile | None:
        """Return a single code file with eager-loaded relationships."""
        stmt = (
            select(CodeFile)
            .where(CodeFile.id == code_file_id)
            .options(
                selectinload(CodeFile.classes).selectinload(Class.methods),
                selectinload(CodeFile.functions),
                selectinload(CodeFile.imports),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_by_repository(self, repository_id: str) -> None:
        """Delete all code files belonging to a repository."""
        stmt = CodeFile.__table__.delete().where(  # type: ignore[attr-defined]
            CodeFile.repository_id == repository_id
        )
        await self._session.execute(stmt)
        await self._session.flush()


class ClassRepository:
    """Data-access layer for the ``classes`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, cls: Class) -> Class:
        """Persist a new class row."""
        self._session.add(cls)
        await self._session.flush()
        return cls

    async def add_many(self, classes: list[Class]) -> list[Class]:
        """Bulk-persist class rows."""
        self._session.add_all(classes)
        await self._session.flush()
        return classes

    async def get_by_file(self, file_id: str) -> Sequence[Class]:
        """Return all classes in a given file."""
        stmt = (
            select(Class)
            .where(Class.file_id == file_id)
            .order_by(Class.line_start)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()


class FunctionRepository:
    """Data-access layer for the ``functions`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, func: Function) -> Function:
        """Persist a new function row."""
        self._session.add(func)
        await self._session.flush()
        return func

    async def add_many(self, functions: list[Function]) -> list[Function]:
        """Bulk-persist function rows."""
        self._session.add_all(functions)
        await self._session.flush()
        return functions


class ImportRepository:
    """Data-access layer for the ``imports`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, imp: Import) -> Import:
        """Persist a new import row."""
        self._session.add(imp)
        await self._session.flush()
        return imp

    async def add_many(self, imports: list[Import]) -> list[Import]:
        """Bulk-persist import rows."""
        self._session.add_all(imports)
        await self._session.flush()
        return imports


class RelationshipRepository:
    """Data-access layer for the ``relationships`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, relationship: Relationship) -> Relationship:
        """Persist a new relationship row."""
        self._session.add(relationship)
        await self._session.flush()
        return relationship

    async def add_many(self, relationships: list[Relationship]) -> list[Relationship]:
        """Bulk-persist relationship rows."""
        self._session.add_all(relationships)
        await self._session.flush()
        return relationships

    async def get_by_repository(
        self, repository_id: str
    ) -> Sequence[Relationship]:
        """Return all relationships for a repository ordered by type."""
        stmt = (
            select(Relationship)
            .where(Relationship.repository_id == repository_id)
            .order_by(Relationship.relationship_type, Relationship.source_symbol)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def delete_by_repository(self, repository_id: str) -> None:
        """Delete all relationships belonging to a repository."""
        stmt = Relationship.__table__.delete().where(  # type: ignore[attr-defined]
            Relationship.repository_id == repository_id
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def count_by_repository(self, repository_id: str) -> int:
        """Return the number of relationships in a repository."""
        stmt = (
            select(Relationship)
            .where(Relationship.repository_id == repository_id)
            .with_only_columns(Relationship.id)
        )
        result = await self._session.execute(stmt)
        return len(result.all())

    async def get_by_type(
        self, repository_id: str, relationship_type: str
    ) -> Sequence[Relationship]:
        """Return all relationships of a specific type."""
        stmt = (
            select(Relationship)
            .where(
                Relationship.repository_id == repository_id,
                Relationship.relationship_type == relationship_type,
            )
            .order_by(Relationship.source_symbol)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()


class CommitRepository:
    """Data-access layer for the ``commits`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, commit: Commit) -> Commit:
        """Persist a new commit row."""
        self._session.add(commit)
        await self._session.flush()
        return commit

    async def add_many(self, commits: list[Commit]) -> list[Commit]:
        """Bulk-persist commit rows."""
        self._session.add_all(commits)
        await self._session.flush()
        return commits

    async def get_by_repository(
        self, repository_id: str
    ) -> Sequence[Commit]:
        """Return all commits for a repository with file data."""
        stmt = (
            select(Commit)
            .where(Commit.repository_id == repository_id)
            .options(selectinload(Commit.files))
            .order_by(Commit.committed_at.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_hash(self, hash: str) -> Commit | None:
        """Look up a commit by its hash."""
        stmt = select(Commit).where(Commit.hash == hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_by_repository(self, repository_id: str) -> None:
        """Delete all commits belonging to a repository."""
        stmt = Commit.__table__.delete().where(  # type: ignore[attr-defined]
            Commit.repository_id == repository_id
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def count_by_repository(self, repository_id: str) -> int:
        """Return the number of commits in a repository."""
        stmt = (
            select(Commit)
            .where(Commit.repository_id == repository_id)
            .with_only_columns(Commit.id)
        )
        result = await self._session.execute(stmt)
        return len(result.all())


class CommitFileRepository:
    """Data-access layer for the ``commit_files`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, commit_file: CommitFile) -> CommitFile:
        """Persist a new commit file row."""
        self._session.add(commit_file)
        await self._session.flush()
        return commit_file

    async def add_many(self, commit_files: list[CommitFile]) -> list[CommitFile]:
        """Bulk-persist commit file rows."""
        self._session.add_all(commit_files)
        await self._session.flush()
        return commit_files


class CommitRelationshipRepository:
    """Data-access layer for the ``commit_relationships`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, rel: CommitRelationship) -> CommitRelationship:
        """Persist a new commit relationship row."""
        self._session.add(rel)
        await self._session.flush()
        return rel

    async def add_many(
        self, rels: list[CommitRelationship]
    ) -> list[CommitRelationship]:
        """Bulk-persist commit relationship rows."""
        self._session.add_all(rels)
        await self._session.flush()
        return rels