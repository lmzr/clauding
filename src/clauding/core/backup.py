"""Backup functionality for Claude Code configuration."""

import shutil
from datetime import datetime
from pathlib import Path

from clauding.core.config import ClaudeConfig


def create_backup(config: ClaudeConfig) -> Path:
    """
    Create a timestamped backup of the entire .claude directory.

    Backs up:
    - projects/
    - history.jsonl
    - todos/
    - file-history/
    - ~/.claude.json

    Args:
        config: ClaudeConfig instance

    Returns:
        Path to the backup directory
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = config.backup_dir / f"backup_{timestamp}"
    backup_path.mkdir(parents=True, exist_ok=True)

    # Backup critical directories and files
    for item in ["projects", "history.jsonl", "todos", "file-history"]:
        source = config.claude_dir / item
        if source.exists():
            dest = backup_path / item
            if source.is_dir():
                shutil.copytree(source, dest)
            else:
                shutil.copy2(source, dest)

    # Also backup ~/.claude.json
    if config.claude_json_file.exists():
        shutil.copy2(config.claude_json_file, backup_path / ".claude.json")

    return backup_path
