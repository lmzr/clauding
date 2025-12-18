"""Claude Code configuration paths and constants."""

from pathlib import Path
from typing import Optional


class ClaudeConfig:
    """Configuration holder for Claude Code paths."""

    def __init__(
        self,
        claude_dir: Optional[Path] = None,
        claude_json_file: Optional[Path] = None,
    ):
        """
        Initialize configuration.

        Args:
            claude_dir: Path to .claude directory (default: ~/.claude)
            claude_json_file: Path to .claude.json file (default: ~/.claude.json)
        """
        self.claude_dir = claude_dir or Path.home() / ".claude"
        self.projects_dir = self.claude_dir / "projects"
        self.history_file = self.claude_dir / "history.jsonl"
        self.backup_dir = self.claude_dir / "backups"

        # If custom claude_dir is provided, put .claude.json in its parent
        # This allows for proper testing isolation
        if claude_json_file is not None:
            self.claude_json_file = claude_json_file
        elif claude_dir is not None:
            self.claude_json_file = claude_dir.parent / ".claude.json"
        else:
            self.claude_json_file = Path.home() / ".claude.json"
