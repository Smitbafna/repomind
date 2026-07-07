from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.parser.exceptions import ParserError, UnsupportedLanguageError
from backend.core.parser.factory import ParserFactory
from backend.core.parser.models import ParsedFile
from backend.database.models import (
    Class as ClassModel,
    CodeFile as CodeFileModel,
    Function as FunctionModel,
    Import as ImportModel,
    Repository,
)
from backend.database.repositories import (
    ClassRepository,
    CodeFileRepository,
    FunctionRepository,
    ImportRepository,
    RepositoryRepository,
)

logger = logging.getLogger(__name__)


class ParserService:
    """Orchestrates the repository parsing pipeline.

    Responsibilities:
        1. Discover supported source files in a repository.
        2. Select the appropriate parser for each file.
        3. Parse each file to extract structural information.
        4. Persist the extracted information into the database.
    """

    def __init__(
        self,
        session: AsyncSession,
        parser_factory: ParserFactory | None = None,
        repo_repo: RepositoryRepository | None = None,
        code_file_repo: CodeFileRepository | None = None,
        class_repo: ClassRepository | None = None,
        function_repo: FunctionRepository | None = None,
        import_repo: ImportRepository | None = None,
    ) -> None:
        self._session = session
        self._factory = parser_factory or ParserFactory()
        self._repo_repo = repo_repo or RepositoryRepository(session)
        self._code_file_repo = code_file_repo or CodeFileRepository(session)
        self._class_repo = class_repo or ClassRepository(session)
        self._function_repo = function_repo or FunctionRepository(session)
        self._import_repo = import_repo or ImportRepository(session)

    async def parse_repository(self, repository_id: str) -> int:
        """Parse every supported source file in a repository.

        This method:
            1. Loads the repository record.
            2. Scans the repository path for supported files.
            3. Parses each file and persists the extracted information.

        Previous parse results for the repository are cleared before re-parsing.

        Args:
            repository_id: The primary key of the repository to parse.

        Returns:
            The number of files successfully parsed.

        Raises:
            ValueError: If the repository ID is not found.
            ParserError: If parsing fails fatally.
        """
        repo = await self._repo_repo.get_by_id(repository_id)
        if repo is None:
            raise ValueError(f"Repository not found: {repository_id}")

        # Clear any previous parse results for this repository.
        await self._code_file_repo.delete_by_repository(repository_id)

        repo_path = Path(repo.local_path)
        if not repo_path.is_dir():
            logger.warning("Repository path does not exist: %s", repo_path)
            return 0

        supported_files = self._discover_supported_files(repo_path)
        parsed_count = 0

        for file_path in supported_files:
            try:
                parser = self._factory.get_parser(file_path)
                parsed = parser.parse_file(file_path)
                await self._persist_parsed_file(repository_id, parsed)
                parsed_count += 1
            except UnsupportedLanguageError:
                continue  # Should not happen since we pre-filter.
            except ParserError as exc:
                logger.warning("Failed to parse %s: %s", file_path, exc)
                continue

        await self._session.flush()
        logger.info(
            "Parsed %d/%d files for repository %s",
            parsed_count,
            len(supported_files),
            repository_id,
        )
        return parsed_count

    async def get_repository_structure(self, repository_id: str) -> list[CodeFileModel]:
        """Return the full parse structure for a repository.

        Args:
            repository_id: The primary key of the repository.

        Returns:
            A list of ``CodeFileModel`` instances with eager-loaded relationships.

        Raises:
            ValueError: If the repository ID is not found.
        """
        repo = await self._repo_repo.get_by_id(repository_id)
        if repo is None:
            raise ValueError(f"Repository not found: {repository_id}")

        return list(await self._code_file_repo.get_by_repository(repository_id))

    async def get_parsed_file(self, file_id: str) -> CodeFileModel | None:
        """Return a single parsed file with all its structural information.

        Args:
            file_id: The primary key of the code file record.

        Returns:
            A ``CodeFileModel`` with eager-loaded relationships, or ``None``.
        """
        return await self._code_file_repo.get_by_id(file_id)

    # ── private helpers ───────────────────────────────────────────

    def _discover_supported_files(self, repo_path: Path) -> list[Path]:
        """Walk the repository and return paths for supported source files."""
        supported_extensions = self._factory.supported_extensions
        files: list[Path] = []

        for path in repo_path.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() in supported_extensions:
                files.append(path)

        return sorted(files)

    async def _persist_parsed_file(
        self, repository_id: str, parsed: ParsedFile
    ) -> None:
        """Persist a ``ParsedFile`` into the database."""
        code_file = CodeFileModel(
            repository_id=repository_id,
            path=parsed.path,
            language=parsed.language,
        )
        persisted_code_file = await self._code_file_repo.add(code_file)
        file_id = persisted_code_file.id

        # Persist imports.
        if parsed.imports:
            import_models = [
                ImportModel(
                    file_id=file_id,
                    module=imp.module,
                    imported_name=imp.imported_name,
                    alias=imp.alias,
                )
                for imp in parsed.imports
            ]
            await self._import_repo.add_many(import_models)

        # Persist top-level functions.
        if parsed.functions:
            function_models = [
                FunctionModel(
                    file_id=file_id,
                    class_id=None,
                    name=fn.name,
                    line_start=fn.line_start,
                    line_end=fn.line_end,
                    is_async=fn.is_async,
                    docstring=fn.docstring,
                    decorators=", ".join(fn.decorators) if fn.decorators else None,
                )
                for fn in parsed.functions
            ]
            await self._function_repo.add_many(function_models)

        # Persist classes and their methods.
        if parsed.classes:
            for cls in parsed.classes:
                class_model = ClassModel(
                    file_id=file_id,
                    name=cls.name,
                    line_start=cls.line_start,
                    line_end=cls.line_end,
                    docstring=cls.docstring,
                    decorators=", ".join(cls.decorators) if cls.decorators else None,
                    bases=", ".join(cls.bases) if cls.bases else None,
                )
                persisted_class = await self._class_repo.add(class_model)

                # Persist methods belonging to this class.
                if cls.methods:
                    method_models = [
                        FunctionModel(
                            file_id=file_id,
                            class_id=persisted_class.id,
                            name=fn.name,
                            line_start=fn.line_start,
                            line_end=fn.line_end,
                            is_async=fn.is_async,
                            docstring=fn.docstring,
                            decorators=", ".join(fn.decorators)
                            if fn.decorators
                            else None,
                        )
                        for fn in cls.methods
                    ]
                    await self._function_repo.add_many(method_models)