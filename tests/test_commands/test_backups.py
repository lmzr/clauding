"""Tests for clauding backups command."""

import json
from argparse import Namespace
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from clauding.commands.backups import (
    execute,
    get_all_backups,
    get_backup_info,
    calculate_dir_size,
    format_size,
    list_backups,
    prune_backups,
)


class TestGetBackupInfo:
    """Tests for get_backup_info function."""

    def test_valid_backup_name(self, mock_claude_env):
        """Test parsing a valid backup directory name."""
        backup_dir = mock_claude_env["claude_dir"] / "backups" / "backup_20260105_143025"
        backup_dir.mkdir(parents=True)
        (backup_dir / "test.txt").write_text("test content")

        info = get_backup_info(backup_dir)

        assert info is not None
        assert info["name"] == "backup_20260105_143025"
        assert info["timestamp"] == datetime(2026, 1, 5, 14, 30, 25)
        assert info["size"] > 0

    def test_invalid_backup_name(self, mock_claude_env):
        """Test parsing an invalid backup directory name."""
        backup_dir = mock_claude_env["claude_dir"] / "backups" / "invalid_name"
        backup_dir.mkdir(parents=True)

        info = get_backup_info(backup_dir)

        assert info is None

    def test_non_backup_prefix(self, mock_claude_env):
        """Test parsing a directory without backup_ prefix."""
        backup_dir = mock_claude_env["claude_dir"] / "backups" / "other_20260105_143025"
        backup_dir.mkdir(parents=True)

        info = get_backup_info(backup_dir)

        assert info is None


class TestCalculateDirSize:
    """Tests for calculate_dir_size function."""

    def test_empty_directory(self, temp_dir):
        """Test size of empty directory."""
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()

        size = calculate_dir_size(empty_dir)

        assert size == 0

    def test_directory_with_files(self, temp_dir):
        """Test size of directory with files."""
        test_dir = temp_dir / "test"
        test_dir.mkdir()
        (test_dir / "file1.txt").write_text("Hello")  # 5 bytes
        (test_dir / "file2.txt").write_text("World!")  # 6 bytes

        size = calculate_dir_size(test_dir)

        assert size == 11

    def test_nested_directories(self, temp_dir):
        """Test size includes nested directories."""
        test_dir = temp_dir / "test"
        sub_dir = test_dir / "sub"
        sub_dir.mkdir(parents=True)
        (test_dir / "file1.txt").write_text("A" * 100)  # 100 bytes
        (sub_dir / "file2.txt").write_text("B" * 50)  # 50 bytes

        size = calculate_dir_size(test_dir)

        assert size == 150


class TestFormatSize:
    """Tests for format_size function."""

    def test_bytes(self):
        assert format_size(500) == "500 B"

    def test_kilobytes(self):
        assert format_size(2048) == "2.0 KB"

    def test_megabytes(self):
        assert format_size(5 * 1024 * 1024) == "5.0 MB"

    def test_gigabytes(self):
        assert format_size(2 * 1024 * 1024 * 1024) == "2.0 GB"


class TestGetAllBackups:
    """Tests for get_all_backups function."""

    def test_no_backups(self, mock_claude_env):
        """Test when no backups exist."""
        backups = get_all_backups(mock_claude_env["config"])

        assert backups == []

    def test_multiple_backups_sorted(self, mock_claude_env):
        """Test backups are sorted by date (most recent first)."""
        backup_dir = mock_claude_env["claude_dir"] / "backups"

        # Create backups with different timestamps
        (backup_dir / "backup_20260101_100000").mkdir()
        (backup_dir / "backup_20260105_120000").mkdir()
        (backup_dir / "backup_20260103_080000").mkdir()

        backups = get_all_backups(mock_claude_env["config"])

        assert len(backups) == 3
        assert backups[0]["name"] == "backup_20260105_120000"  # Most recent
        assert backups[1]["name"] == "backup_20260103_080000"
        assert backups[2]["name"] == "backup_20260101_100000"  # Oldest


class TestListBackups:
    """Tests for list_backups function."""

    def test_list_empty(self, capsys):
        """Test listing when no backups exist."""
        result = list_backups([], as_json=False)

        assert result == 0
        output = capsys.readouterr().out
        assert "No backups found" in output

    def test_list_json_empty(self, capsys):
        """Test JSON output when no backups exist."""
        result = list_backups([], as_json=True)

        assert result == 0
        output = capsys.readouterr().out
        data = json.loads(output)
        assert data["backups"] == []
        assert data["total_count"] == 0
        assert data["total_size"] == 0

    def test_list_with_backups(self, mock_claude_env, capsys):
        """Test listing backups."""
        backup_dir = mock_claude_env["claude_dir"] / "backups" / "backup_20260105_143025"
        backup_dir.mkdir()
        (backup_dir / "test.txt").write_text("content")

        backups = get_all_backups(mock_claude_env["config"])
        result = list_backups(backups, as_json=False)

        assert result == 0
        output = capsys.readouterr().out
        assert "backup_20260105_143025" in output
        assert "2026-01-05" in output

    def test_list_json_with_backups(self, mock_claude_env, capsys):
        """Test JSON output with backups."""
        backup_dir = mock_claude_env["claude_dir"] / "backups" / "backup_20260105_143025"
        backup_dir.mkdir()
        (backup_dir / "test.txt").write_text("content")

        backups = get_all_backups(mock_claude_env["config"])
        result = list_backups(backups, as_json=True)

        assert result == 0
        output = capsys.readouterr().out
        data = json.loads(output)
        assert len(data["backups"]) == 1
        assert data["backups"][0]["name"] == "backup_20260105_143025"
        assert data["total_count"] == 1


class TestPruneBackups:
    """Tests for prune_backups function."""

    def _create_backup(self, backup_dir: Path, days_ago: int) -> Path:
        """Helper to create a backup with a specific age."""
        timestamp = datetime.now() - timedelta(days=days_ago)
        name = f"backup_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        path = backup_dir / name
        path.mkdir(parents=True, exist_ok=True)
        (path / "test.txt").write_text("content")
        return path

    def test_prune_older_than(self, mock_claude_env, capsys):
        """Test pruning backups older than N days."""
        backup_dir = mock_claude_env["claude_dir"] / "backups"
        self._create_backup(backup_dir, days_ago=1)  # Recent
        self._create_backup(backup_dir, days_ago=10)  # Old
        self._create_backup(backup_dir, days_ago=20)  # Older

        backups = get_all_backups(mock_claude_env["config"])
        args = Namespace(older_than=7, keep=None, dry_run=False, force=True)

        result = prune_backups(mock_claude_env["config"], backups, args)

        assert result == 0
        remaining = get_all_backups(mock_claude_env["config"])
        assert len(remaining) == 1  # Only the 1-day-old backup remains

    def test_prune_keep(self, mock_claude_env, capsys):
        """Test pruning to keep only N most recent backups."""
        backup_dir = mock_claude_env["claude_dir"] / "backups"
        self._create_backup(backup_dir, days_ago=1)
        self._create_backup(backup_dir, days_ago=2)
        self._create_backup(backup_dir, days_ago=3)
        self._create_backup(backup_dir, days_ago=4)

        backups = get_all_backups(mock_claude_env["config"])
        args = Namespace(older_than=None, keep=2, dry_run=False, force=True)

        result = prune_backups(mock_claude_env["config"], backups, args)

        assert result == 0
        remaining = get_all_backups(mock_claude_env["config"])
        assert len(remaining) == 2

    def test_prune_combined_criteria(self, mock_claude_env, capsys):
        """Test pruning with both --older-than and --keep."""
        backup_dir = mock_claude_env["claude_dir"] / "backups"
        self._create_backup(backup_dir, days_ago=1)  # Recent, in top 3
        self._create_backup(backup_dir, days_ago=2)  # Recent, in top 3
        self._create_backup(backup_dir, days_ago=3)  # Recent, in top 3
        self._create_backup(backup_dir, days_ago=5)  # Old but not >7 days
        self._create_backup(backup_dir, days_ago=10)  # Old >7 days, not in top 3

        backups = get_all_backups(mock_claude_env["config"])
        args = Namespace(older_than=7, keep=3, dry_run=False, force=True)

        result = prune_backups(mock_claude_env["config"], backups, args)

        assert result == 0
        remaining = get_all_backups(mock_claude_env["config"])
        # Keep: 1, 2, 3 days (in top 3), 5 days (not older than 7)
        # Delete: 10 days (older than 7 AND not in top 3)
        assert len(remaining) == 4

    def test_prune_dry_run(self, mock_claude_env, capsys):
        """Test dry-run mode doesn't delete."""
        backup_dir = mock_claude_env["claude_dir"] / "backups"
        self._create_backup(backup_dir, days_ago=10)

        backups = get_all_backups(mock_claude_env["config"])
        args = Namespace(older_than=5, keep=None, dry_run=True, force=False)

        result = prune_backups(mock_claude_env["config"], backups, args)

        assert result == 0
        output = capsys.readouterr().out
        assert "[DRY RUN]" in output
        # Backup should still exist
        remaining = get_all_backups(mock_claude_env["config"])
        assert len(remaining) == 1

    def test_prune_no_matches(self, mock_claude_env, capsys):
        """Test when no backups match criteria."""
        backup_dir = mock_claude_env["claude_dir"] / "backups"
        self._create_backup(backup_dir, days_ago=1)

        backups = get_all_backups(mock_claude_env["config"])
        args = Namespace(older_than=30, keep=None, dry_run=False, force=True)

        result = prune_backups(mock_claude_env["config"], backups, args)

        assert result == 0
        output = capsys.readouterr().out
        assert "No backups match" in output


class TestExecute:
    """Tests for execute function."""

    def test_execute_list_default(self, mock_claude_env, capsys):
        """Test default behavior (list mode)."""
        args = Namespace(
            claude_dir=mock_claude_env["claude_dir"],
            prune=False,
            older_than=None,
            keep=None,
            force=False,
            dry_run=False,
            json=False,
        )

        result = execute(args)

        assert result == 0
        output = capsys.readouterr().out
        assert "No backups found" in output

    def test_execute_list_json(self, mock_claude_env, capsys):
        """Test JSON output mode."""
        args = Namespace(
            claude_dir=mock_claude_env["claude_dir"],
            prune=False,
            older_than=None,
            keep=None,
            force=False,
            dry_run=False,
            json=True,
        )

        result = execute(args)

        assert result == 0
        output = capsys.readouterr().out
        data = json.loads(output)
        assert "backups" in data

    def test_execute_prune_without_criteria(self, mock_claude_env, capsys):
        """Test error when --prune without --older-than or --keep."""
        args = Namespace(
            claude_dir=mock_claude_env["claude_dir"],
            prune=True,
            older_than=None,
            keep=None,
            force=False,
            dry_run=False,
            json=False,
        )

        result = execute(args)

        assert result == 1
        output = capsys.readouterr().out
        assert "--prune requires" in output

    def test_execute_interactive_mode(self, mock_claude_env):
        """Test interactive mode with user input."""
        backup_dir = mock_claude_env["claude_dir"] / "backups"
        backup = backup_dir / "backup_20250101_100000"
        backup.mkdir(parents=True)
        (backup / "test.txt").write_text("content")

        args = Namespace(
            claude_dir=mock_claude_env["claude_dir"],
            prune=True,
            older_than=1,
            keep=None,
            force=False,
            dry_run=False,
            json=False,
        )

        # Simulate user pressing 'y'
        with patch("builtins.input", return_value="y"):
            result = execute(args)

        assert result == 0
        # Backup should be deleted
        remaining = get_all_backups(mock_claude_env["config"])
        assert len(remaining) == 0
