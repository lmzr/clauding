"""Pytest fixtures for clauding tests."""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from clauding.core.config import ClaudeConfig


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    dir_path = tempfile.mkdtemp()
    # Resolve to handle symlinks (e.g., /var -> /private/var on macOS)
    resolved_path = Path(dir_path).resolve()
    yield resolved_path
    shutil.rmtree(resolved_path)


@pytest.fixture
def mock_claude_env(temp_dir):
    """
    Create a mock Claude Code environment.

    Returns a dict with:
    - config: ClaudeConfig instance
    - claude_dir: Path to .claude directory
    - projects_dir: Path to projects directory
    - history_file: Path to history.jsonl
    - claude_json_file: Path to .claude.json
    """
    claude_dir = temp_dir / ".claude"
    claude_dir.mkdir()
    (claude_dir / "projects").mkdir()
    (claude_dir / "backups").mkdir()

    # Create mock .claude.json
    claude_json_file = temp_dir / ".claude.json"
    claude_json_file.write_text("{}")

    # Create mock history.jsonl
    history_file = claude_dir / "history.jsonl"
    history_file.write_text("")

    # Create config pointing to mock environment
    # The ClaudeConfig will automatically put .claude.json in the parent of claude_dir
    config = ClaudeConfig(claude_dir=claude_dir)

    return {
        "config": config,
        "claude_dir": claude_dir,
        "projects_dir": claude_dir / "projects",
        "history_file": history_file,
        "claude_json_file": claude_json_file,
    }


@pytest.fixture
def mock_project(mock_claude_env):
    """
    Create a mock project in the Claude environment.

    Returns a dict with:
    - path: The mock project path
    - dirname: The normalized directory name
    - session_file: Path to the session file
    """
    from clauding.core.paths import normalize_path_to_dirname

    project_path = str(mock_claude_env["claude_dir"].parent / "TestProject")
    dirname = normalize_path_to_dirname(project_path)

    project_dir = mock_claude_env["projects_dir"] / dirname
    project_dir.mkdir()

    # Create a session file
    session_file = project_dir / "session-001.jsonl"
    session_data = {
        "cwd": project_path,
        "sessionId": "session-001",
        "type": "user",
        "message": {"role": "user", "content": "test"},
    }
    session_file.write_text(json.dumps(session_data) + "\n")

    # Add to history
    history_entry = {
        "display": "test prompt",
        "project": project_path,
        "timestamp": 1234567890,
    }
    mock_claude_env["history_file"].write_text(json.dumps(history_entry) + "\n")

    # Add to claude.json
    claude_json_data = {"projects": {project_path: {"allowedTools": []}}}
    mock_claude_env["claude_json_file"].write_text(json.dumps(claude_json_data))

    return {
        "path": project_path,
        "dirname": dirname,
        "session_file": session_file,
        "project_dir": project_dir,
    }
