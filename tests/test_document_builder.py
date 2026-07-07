from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

import pytest

from backend.core.indexing.document_builder import DocumentBuilder, DocumentType
from backend.database.models import (
    Class as ClassModel,
    CodeFile as CodeFileModel,
    Function as FunctionModel,
    Repository,
)


class TestDocumentBuilder:
    """Test suite for the document builder."""

    def setup_method(self) -> None:
        self.builder = DocumentBuilder()
        self.repo = Repository(
            id="test-repo-id",
            owner="test-owner",
            name="test-repo",
            local_path="/tmp/test-repo-path",
            created_at=datetime.now(timezone.utc),
        )

    def test_build_module_document(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            code_file = CodeFileModel(
                id="cf-1",
                repository_id=self.repo.id,
                path="main.py",
                language="python",
            )
            # Create the actual file.
            file_path = repo_path / "main.py"
            file_path.write_text("def hello():\n    pass\n")

            self.repo.local_path = str(repo_path)
            docs = self.builder.build_documents(self.repo, [code_file])

            module_docs = [d for d in docs if d.document_type == DocumentType.PYTHON_MODULE]
            assert len(module_docs) >= 1
            assert module_docs[0].content == "def hello():\n    pass\n"
            assert module_docs[0].repository_id == self.repo.id

    def test_build_class_document(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            code_file_id = "cf-1"
            code_file = CodeFileModel(
                id=code_file_id,
                repository_id=self.repo.id,
                path="models.py",
                language="python",
            )
            cls_model = ClassModel(
                id="cls-1",
                file_id=code_file_id,
                name="MyClass",
                line_start=1,
                line_end=3,
                docstring="My test class.",
            )
            code_file.classes = [cls_model]

            file_path = repo_path / "models.py"
            file_path.write_text("class MyClass:\n    pass\n\nclass Other:\n    pass\n")

            self.repo.local_path = str(repo_path)
            docs = self.builder.build_documents(self.repo, [code_file])

            class_docs = [d for d in docs if d.document_type == DocumentType.CLASS]
            assert len(class_docs) >= 1
            assert class_docs[0].metadata["class"] == "MyClass"

    def test_build_function_document(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            code_file_id = "cf-1"
            code_file = CodeFileModel(
                id=code_file_id,
                repository_id=self.repo.id,
                path="utils.py",
                language="python",
            )
            func_model = FunctionModel(
                id="fn-1",
                file_id=code_file_id,
                name="my_function",
                line_start=1,
                line_end=3,
                is_async=False,
            )
            code_file.functions = [func_model]

            file_path = repo_path / "utils.py"
            file_path.write_text("def my_function():\n    return 42\n\ndef other():\n    pass\n")

            self.repo.local_path = str(repo_path)
            docs = self.builder.build_documents(self.repo, [code_file])

            func_docs = [d for d in docs if d.document_type == DocumentType.FUNCTION]
            assert len(func_docs) >= 1
            assert func_docs[0].metadata["function"] == "my_function"

    def test_build_readme_document(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            readme_path = repo_path / "README.md"
            readme_path.write_text("# Test Repository\n\nThis is a test.\n")

            self.repo.local_path = str(repo_path)
            docs = self.builder.build_documents(self.repo, [])

            readme_docs = [d for d in docs if d.document_type == DocumentType.README]
            assert len(readme_docs) == 1
            assert "Test Repository" in readme_docs[0].content

    def test_build_docstring_document(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            code_file_id = "cf-1"
            code_file = CodeFileModel(
                id=code_file_id,
                repository_id=self.repo.id,
                path="utils.py",
                language="python",
            )
            func_model = FunctionModel(
                id="fn-1",
                file_id=code_file_id,
                name="my_function",
                line_start=1,
                line_end=3,
                is_async=False,
                docstring="This function does something useful.",
            )
            code_file.functions = [func_model]

            file_path = repo_path / "utils.py"
            file_path.write_text("def my_function():\n    \"\"\"This function does something useful.\"\"\"\n    pass\n")

            self.repo.local_path = str(repo_path)
            docs = self.builder.build_documents(self.repo, [code_file])

            docstring_docs = [d for d in docs if d.document_type == DocumentType.DOCSTRING]
            assert len(docstring_docs) >= 1
            assert "useful" in docstring_docs[0].content

    def test_build_no_files(self) -> None:
        docs = self.builder.build_documents(self.repo, [])
        # Should still return an empty list (no README found either).
        assert isinstance(docs, list)

    def test_build_document_types(self) -> None:
        """Verify that all document types are in the enum."""
        types = {t.value for t in DocumentType}
        assert types == {
            "readme",
            "markdown",
            "python_module",
            "class",
            "function",
            "docstring",
        }