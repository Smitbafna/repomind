from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Pattern to detect function/method signatures in diffs.
_FUNC_PATTERN = re.compile(
    r"^\+\s*(?:async\s+)?(?:def|class)\s+([a-zA-Z_][a-zA-Z0-9_]*)"
)


@dataclass(frozen=True)
class DiffInfo:
    """Structured diff information for a single file."""

    file_path: str
    change_type: str  # ADDED, MODIFIED, RENAMED, DELETED
    additions: int
    deletions: int
    added_lines: list[str] = field(default_factory=list)
    removed_lines: list[str] = field(default_factory=list)
    modified_symbols: list[str] = field(default_factory=list)


class DiffParser:
    """Parses git diffs to extract structured information.

    Extracts:
        - Changed files
        - Added/removed lines
        - Modified functions/classes (when detectable)
    """

    def parse(self, diff_text: str, file_path: str) -> DiffInfo:
        """Parse a raw diff for a single file.

        Args:
            diff_text: The raw diff text.
            file_path: The file path.

        Returns:
            A ``DiffInfo`` with structured diff data.
        """
        added_lines: list[str] = []
        removed_lines: list[str] = []
        additions = 0
        deletions = 0
        change_type = "MODIFIED"

        for line in diff_text.splitlines():
            if line.startswith("+++") or line.startswith("---"):
                continue
            if line.startswith("@@"):
                continue
            if line.startswith("+"):
                additions += 1
                content = line[1:]
                added_lines.append(content)
            elif line.startswith("-"):
                deletions += 1
                content = line[1:]
                removed_lines.append(content)

        # Detect change type from added/removed content.
        if additions > 0 and deletions == 0:
            # Could be an addition if the file is new, but we can't reliably tell from diff alone.
            pass

        # Detect modified symbols.
        modified_symbols = self._extract_symbols(added_lines)

        return DiffInfo(
            file_path=file_path,
            change_type=change_type,
            additions=additions,
            deletions=deletions,
            added_lines=added_lines,
            removed_lines=removed_lines,
            modified_symbols=modified_symbols,
        )

    @staticmethod
    def _extract_symbols(added_lines: list[str]) -> list[str]:
        """Extract function/class names from added lines."""
        symbols: list[str] = []
        for line in added_lines:
            match = _FUNC_PATTERN.match(line)
            if match:
                symbols.append(match.group(1))
        return symbols

    @staticmethod
    def change_type_from_diff(diff_text: str) -> str:
        """Determine the change type from diff text."""
        if not diff_text.strip():
            return "ADDED"

        lines = diff_text.splitlines()
        # If the diff starts with "new file mode" or has no --- line, it's an addition.
        has_new_file = any("new file mode" in l for l in lines[:5])
        has_delete = any("deleted file mode" in l for l in lines[:5])
        has_rename = any("rename from" in l for l in lines)

        if has_new_file:
            return "ADDED"
        if has_delete:
            return "DELETED"
        if has_rename:
            return "RENAMED"
        return "MODIFIED"