"""Tests for clauding.core.backup module."""

import json
from pathlib import Path

import pytest

from clauding.core.backup import create_backup


class TestCreateBackup:
    """Tests for create_backup function."""

    def test_create_backup_creates_directory(self, mock_claude_env):
        """Test that backup creates a timestamped directory."""
        backup_path = create_backup(mock_claude_env["config"])

        assert backup_path.exists()
        assert backup_path.is_dir()
        assert backup_path.parent == mock_claude_env["claude_dir"] / "backups"
        assert backup_path.name.startswith("backup_")

    def test_create_backup_copies_projects(self, mock_claude_env, mock_project):
        """Test that backup copies projects directory."""
        backup_path = create_backup(mock_claude_env["config"])

        backed_up_projects = backup_path / "projects"
        assert backed_up_projects.exists()
        assert (backed_up_projects / mock_project["dirname"]).exists()

    def test_create_backup_copies_history(self, mock_claude_env, mock_project):
        """Test that backup copies history.jsonl."""
        backup_path = create_backup(mock_claude_env["config"])

        backed_up_history = backup_path / "history.jsonl"
        assert backed_up_history.exists()

    def test_create_backup_copies_claude_json(self, mock_claude_env, mock_project):
        """Test that backup copies .claude.json."""
        backup_path = create_backup(mock_claude_env["config"])

        backed_up_json = backup_path / ".claude.json"
        assert backed_up_json.exists()

    def test_backup_preserves_content(self, mock_claude_env, mock_project):
        """Test that backup preserves file content."""
        backup_path = create_backup(mock_claude_env["config"])

        # Check history content
        original_history = mock_claude_env["history_file"].read_text()
        backed_up_history = (backup_path / "history.jsonl").read_text()
        assert original_history == backed_up_history

        # Check session file content
        original_session = mock_project["session_file"].read_text()
        backed_up_session = (
            backup_path / "projects" / mock_project["dirname"] / "session-001.jsonl"
        ).read_text()
        assert original_session == backed_up_session
