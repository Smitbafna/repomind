from __future__ import annotations

import enum
import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from backend.database.models import (
    Class as ClassModel,
    CodeFile as CodeFileModel,
    Function as FunctionModel,
    Repository,
)

logger = logging.getLogger(__name__)


class DocumentType(str, enum.Enum):
    """Types of semantic documents that can be indexed."""

    README = "readme"
    MARKDOWN = "markdown"
    PYTHON_MODULE = "python_module"
    CLASS = "class"
    FUNCTION = "function"
    DOCSTRING = "docstring"


@dataclass(frozen=True)
class SemanticDocument:
    """A single semantic document ready for embedding and indexing."""

    id: str
    repository_id: str
    document_type: DocumentType
    content: str
    metadata: dict[str, str] = field(default_factory=dict)


class DocumentBuilder:
    """Converts parsed repository information into semantic documents.

    Documents are chunked by semantic units (not by character count):
    - README files become single documents
    - Markdown files become single documents
    - Python modules become module-level documents
    - Each class becomes a document with its source code
    - Each function becomes a document with its source code
    - Each docstring becomes a separate document
    """

    def build_documents(
        self,
        repository: Repository,
        code_files: list[CodeFileModel],
    ) -> list[SemanticDocument]:
        """Build semantic documents from a repository's parsed data.

        Args:
            repository: The repository model.
            code_files: List of parsed code files with eager-loaded relationships.

        Returns:
            A list of ``SemanticDocument`` instances ready for embedding.
        """
        documents: list[SemanticDocument] = []
        repo_path = Path(repository.local_path)

        # Build README document.
        readme_docs = self._build_readme_document(repository, repo_path)
        documents.extend(readme_docs)

        # Build documents from parsed code files.
        for code_file in code_files:
            file_path = Path(code_file.path)

            # Python module document.
            module_doc = self._build_module_document(repository, code_file, repo_path)
            if module_doc:
                documents.append(module_doc)

            # Class documents.
            for cls in code_file.classes:
                class_doc = self._build_class_document(repository, code_file, cls)
                if class_doc:
                    documents.append(class_doc)

                # Method docstrings as separate documents.
                for method in cls.methods:
                    if method.docstring:
                        docstring_doc = self._build_docstring_document(
                            repository, code_file, method, cls
                        )
                        if docstring_doc:
                            documents.append(docstring_doc)

            # Top-level function documents.
            for func in code_file.functions:
                func_doc = self._build_function_document(repository, code_file, func)
                if func_doc:
                    documents.append(func_doc)

                # Function docstring as separate document.
                if func.docstring:
                    docstring_doc = self._build_docstring_document(
                        repository, code_file, func
                    )
                    if docstring_doc:
                        documents.append(docstring_doc)

        logger.info("Built %d semantic documents for %s/%s", len(documents), repository.owner, repository.name)
        return documents

    # ── private builders ──────────────────────────────────────────

    def _build_readme_document(
        self, repository: Repository, repo_path: Path
    ) -> list[SemanticDocument]:
        """Build documents from README files."""
        documents: list[SemanticDocument] = []
        readme_names = {"README.md", "README.rst", "README.txt", "README"}

        for readme_name in readme_names:
            readme_path = repo_path / readme_name
            if readme_path.is_file():
                try:
                    content = readme_path.read_text(encoding="utf-8", errors="replace")
                    doc_type = (
                        DocumentType.README
                        if readme_name == "README.md"
                        else DocumentType.MARKDOWN
                    )
                    documents.append(
                        SemanticDocument(
                            id=str(uuid.uuid4()),
                            repository_id=repository.id,
                            document_type=doc_type,
                            content=content,
                            metadata={
                                "file": readme_name,
                                "type": doc_type.value,
                            },
                        )
                    )
                except OSError as exc:
                    logger.warning("Failed to read %s: %s", readme_path, exc)

        return documents

    def _build_module_document(
        self, repository: Repository, code_file: CodeFileModel, repo_path: Path
    ) -> SemanticDocument | None:
        """Build a document for a Python module."""
        try:
            full_path = repo_path / code_file.path
            if not full_path.is_file():
                return None
            content = full_path.read_text(encoding="utf-8", errors="replace")
            return SemanticDocument(
                id=str(uuid.uuid4()),
                repository_id=repository.id,
                document_type=DocumentType.PYTHON_MODULE,
                content=content,
                metadata={
                    "file": code_file.path,
                    "language": code_file.language,
                    "type": DocumentType.PYTHON_MODULE.value,
                },
            )
        except OSError as exc:
            logger.warning("Failed to read module %s: %s", code_file.path, exc)
            return None

    def _build_class_document(
        self, repository: Repository, code_file: CodeFileModel, cls: ClassModel
    ) -> SemanticDocument | None:
        """Build a document for a class."""
        try:
            full_path = Path(repository.local_path) / code_file.path
            if not full_path.is_file():
                return None
            lines = full_path.read_text(encoding="utf-8", errors="replace").splitlines()
            # Extract class source lines (0-indexed).
            class_lines = lines[cls.line_start - 1 : cls.line_end]
            content = "\n".join(class_lines)

            return SemanticDocument(
                id=str(uuid.uuid4()),
                repository_id=repository.id,
                document_type=DocumentType.CLASS,
                content=content,
                metadata={
                    "file": code_file.path,
                    "class": cls.name,
                    "line_start": str(cls.line_start),
                    "line_end": str(cls.line_end),
                    "docstring": cls.docstring or "",
                    "bases": cls.bases or "",
                    "type": DocumentType.CLASS.value,
                },
            )
        except OSError as exc:
            logger.warning("Failed to read class source %s: %s", code_file.path, exc)
            return None

    def _build_function_document(
        self, repository: Repository, code_file: CodeFileModel, func: FunctionModel
    ) -> SemanticDocument | None:
        """Build a document for a top-level function."""
        try:
            full_path = Path(repository.local_path) / code_file.path
            if not full_path.is_file():
                return None
            lines = full_path.read_text(encoding="utf-8", errors="replace").splitlines()
            func_lines = lines[func.line_start - 1 : func.line_end]
            content = "\n".join(func_lines)

            return SemanticDocument(
                id=str(uuid.uuid4()),
                repository_id=repository.id,
                document_type=DocumentType.FUNCTION,
                content=content,
                metadata={
                    "file": code_file.path,
                    "function": func.name,
                    "line_start": str(func.line_start),
                    "line_end": str(func.line_end),
                    "is_async": str(func.is_async),
                    "docstring": func.docstring or "",
                    "type": DocumentType.FUNCTION.value,
                },
            )
        except OSError as exc:
            logger.warning("Failed to read function source %s: %s", code_file.path, exc)
            return None

    def _build_docstring_document(
        self,
        repository: Repository,
        code_file: CodeFileModel,
        func: FunctionModel,
        parent_cls: ClassModel | None = None,
    ) -> SemanticDocument | None:
        """Build a document from a function or method docstring."""
        if not func.docstring:
            return None

        symbol_name = (
            f"{parent_cls.name}.{func.name}" if parent_cls else func.name
        )

        return SemanticDocument(
            id=str(uuid.uuid4()),
            repository_id=repository.id,
            document_type=DocumentType.DOCSTRING,
            content=func.docstring,
            metadata={
                "file": code_file.path,
                "symbol": symbol_name,
                "line_start": str(func.line_start),
                "line_end": str(func.line_end),
                "type": DocumentType.DOCSTRING.value,
            },
        )
