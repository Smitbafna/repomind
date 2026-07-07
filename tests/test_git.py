from __future__ import annotations

import os
import tempfile
from pathlib import Path

import git
import pytest

from backend.core.git.collector import GitCollector
from backend.core.git.diff_parser import DiffParser
from backend.core.git.exceptions import RepositoryNotClonedError
from backend.core.git.models import BlameInfo, CommitFileInfo, CommitInfo, TimelineEvent
from backend.core.git.timeline import BlameService, TimelineBuilder


class TestDiffParser:
    """Test suite for the diff parser."""

    def setup_method(self) -> None:
        self.parser = DiffParser()

    def test_parse_added_lines(self) -> None:
        diff = """--- a/file.py
+++ b/file.py
@@ -1 +1,2 @@
-old line
+new line
+another new line"""
        result = self.parser.parse(diff, "file.py")
        assert result.additions == 2
        assert result.deletions == 1
        assert "new line" in result.added_lines
        assert "old line" in result.removed_lines

    def test_parse_empty_diff(self) -> None:
        result = self.parser.parse("", "file.py")
        assert result.additions == 0
        assert result.deletions == 0

    def test_extract_function_symbols(self) -> None:
        diff = """+def hello():
+    pass
+class MyClass:
+    pass"""
        symbols = DiffParser._extract_symbols(diff.splitlines())
        assert "hello" in symbols
        assert "MyClass" in symbols

    def test_extract_async_function_symbols(self) -> None:
        diff = """+async def fetch_data():
+    pass"""
        symbols = DiffParser._extract_symbols(diff.splitlines())
        assert "fetch_data" in symbols

    def test_change_type_new_file(self) -> None:
        diff = """new file mode 100644
index 0000000..abc1234
--- /dev/null
+++ b/new_file.py"""
        assert DiffParser.change_type_from_diff(diff) == "ADDED"

    def test_change_type_deleted(self) -> None:
        diff = """deleted file mode 100644
index abc1234..0000000
--- a/old_file.py
+++ /dev/null"""
        assert DiffParser.change_type_from_diff(diff) == "DELETED"

    def test_change_type_modified(self) -> None:
        diff = """--- a/file.py
+++ b/file.py
@@ -1 +1 @@
-old
+new"""
        assert DiffParser.change_type_from_diff(diff) == "MODIFIED"


class TestGitCollector:
    """Test suite for the git collector using temporary repos."""

    def test_collect_single_commit(self) -> None:
        with _create_temp_repo() as repo_path:
            collector = GitCollector()
            commits = collector.collect(repo_path)
            assert len(commits) >= 1
            assert commits[0].author_name == "Test User"
            assert commits[0].author_email == "test@example.com"

    def test_collect_multiple_commits(self) -> None:
        with _create_temp_repo(num_commits=3) as repo_path:
            collector = GitCollector()
            commits = collector.collect(repo_path)
            assert len(commits) == 3

    def test_collect_nonexistent_path(self) -> None:
        collector = GitCollector()
        with pytest.raises(RepositoryNotClonedError):
            collector.collect(Path("/nonexistent/path"))

    def test_collect_commit_has_files(self) -> None:
        with _create_temp_repo() as repo_path:
            collector = GitCollector()
            commits = collector.collect(repo_path)
            assert len(commits) >= 1
            # The first commit should have at least one file.
            assert len(commits[0].files) >= 1


class TestTimelineBuilder:
    """Test suite for the timeline builder."""

    def test_build_empty(self) -> None:
        builder = TimelineBuilder()
        events = builder.build(Path("/tmp"), [])
        assert events == []

    def test_build_with_commits(self) -> None:
        builder = TimelineBuilder()
        from datetime import datetime, timezone

        class MockCommit:
            hash = "abc123"
            author_name = "Test"
            author_email = "test@test.com"
            committed_at = datetime.now(timezone.utc)
            commit_message = "Test commit"
            files = []

        events = builder.build(Path("/tmp"), [MockCommit()])
        assert len(events) == 1
        assert events[0].commit_hash == "abc123"
        assert events[0].author_name == "Test"


class TestBlameService:
    """Test suite for the blame service."""

    def test_blame_nonexistent_file(self) -> None:
        with _create_temp_repo() as repo_path:
            service = BlameService()
            result = service.blame(repo_path, "nonexistent.py", 1)
            assert result is None


# ── helpers ──────────────────────────────────────────────────

@pytest.fixture
def temp_git_repo() -> Path:
    """Create a temporary git repository with one commit."""
    with _create_temp_repo() as repo_path:
        yield repo_path


def _create_temp_repo(num_commits: int = 1):
    """Context manager that creates a temporary git repository."""
    import contextlib

    @contextlib.contextmanager
    def _manager():
        tmpdir = tempfile.mkdtemp()
        repo_path = Path(tmpdir)
        repo = git.Repo.init(str(repo_path))

        # Configure user.
        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()

        for i in range(num_commits):
            file_path = repo_path / f"file_{i}.py"
            file_path.write_text(f"# File {i}\ndef func_{i}():\n    pass\n")
            repo.index.add([str(file_path)])
            repo.index.commit(f"Commit {i}: added file_{i}.py")

        try:
            yield repo_path
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    return _manager()