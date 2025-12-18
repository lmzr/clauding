"""Tests for clauding move command."""

import json
import os
from argparse import Namespace
from pathlib import Path

import pytest

from clauding.commands.move import execute, move_project
from clauding.core.paths import normalize_path_to_dirname, find_all_project_paths


class TestMoveProject:
    """Tests for move_project function."""

    def test_move_with_folder_move(self, mock_claude_env, mock_project):
        """Test move when old path exists and new doesn't (folder move)."""
        # Create the actual old folder
        old_path = Path(mock_project["path"])
        old_path.mkdir(parents=True)

        new_path = str(old_path.parent / "NewProject")

        result = move_project(
            mock_claude_env["config"],
            mock_project["path"],
            new_path,
            dry_run=False,
            no_backup=True,
        )

        assert result == 0
        assert not old_path.exists()
        assert Path(new_path).exists()

        # Check metadata updated
        all_paths = find_all_project_paths(mock_claude_env["config"])
        assert new_path in all_paths
        assert mock_project["path"] not in all_paths

    def test_move_metadata_only(self, mock_claude_env, mock_project):
        """Test move when old path doesn't exist but new does (metadata-only)."""
        # Create only the new folder
        old_path = Path(mock_project["path"])
        new_path = old_path.parent / "NewProject"
        new_path.mkdir(parents=True)

        result = move_project(
            mock_claude_env["config"],
            mock_project["path"],
            str(new_path),
            dry_run=False,
            no_backup=True,
        )

        assert result == 0

        # Check metadata updated
        all_paths = find_all_project_paths(mock_claude_env["config"])
        assert str(new_path) in all_paths
        assert mock_project["path"] not in all_paths

    def test_move_error_both_exist(self, mock_claude_env, mock_project):
        """Test move error when both paths exist."""
        # Create both folders
        old_path = Path(mock_project["path"])
        new_path = old_path.parent / "NewProject"
        old_path.mkdir(parents=True)
        new_path.mkdir(parents=True)

        result = move_project(
            mock_claude_env["config"],
            mock_project["path"],
            str(new_path),
            dry_run=False,
            no_backup=True,
        )

        assert result == 1

    def test_move_error_neither_exist(self, mock_claude_env, mock_project):
        """Test move error when neither path exists."""
        new_path = Path(mock_project["path"]).parent / "NewProject"

        result = move_project(
            mock_claude_env["config"],
            mock_project["path"],
            str(new_path),
            dry_run=False,
            no_backup=True,
        )

        assert result == 1

    def test_move_dry_run_no_changes(self, mock_claude_env, mock_project):
        """Test that dry-run doesn't make changes."""
        # Create old folder
        old_path = Path(mock_project["path"])
        old_path.mkdir(parents=True)
        new_path = str(old_path.parent / "NewProject")

        result = move_project(
            mock_claude_env["config"],
            mock_project["path"],
            new_path,
            dry_run=True,
            no_backup=True,
        )

        assert result == 0
        # Original folder still exists
        assert old_path.exists()
        # New folder not created
        assert not Path(new_path).exists()
        # Metadata unchanged
        all_paths = find_all_project_paths(mock_claude_env["config"])
        assert mock_project["path"] in all_paths
        assert new_path not in all_paths

    def test_move_updates_session_files(self, mock_claude_env, mock_project):
        """Test that session files are updated with new path."""
        # Create old folder
        old_path = Path(mock_project["path"])
        old_path.mkdir(parents=True)
        new_path = str(old_path.parent / "NewProject")

        move_project(
            mock_claude_env["config"],
            mock_project["path"],
            new_path,
            dry_run=False,
            no_backup=True,
        )

        # Check session file content
        new_dirname = normalize_path_to_dirname(new_path)
        new_session_file = (
            mock_claude_env["projects_dir"] / new_dirname / "session-001.jsonl"
        )
        assert new_session_file.exists()

        content = new_session_file.read_text()
        data = json.loads(content.strip())
        assert data["cwd"] == new_path

    def test_move_updates_history(self, mock_claude_env, mock_project):
        """Test that history.jsonl is updated."""
        # Create old folder
        old_path = Path(mock_project["path"])
        old_path.mkdir(parents=True)
        new_path = str(old_path.parent / "NewProject")

        move_project(
            mock_claude_env["config"],
            mock_project["path"],
            new_path,
            dry_run=False,
            no_backup=True,
        )

        # Check history content
        content = mock_claude_env["history_file"].read_text()
        data = json.loads(content.strip())
        assert data["project"] == new_path

    def test_move_updates_claude_json(self, mock_claude_env, mock_project):
        """Test that .claude.json is updated."""
        # Create old folder
        old_path = Path(mock_project["path"])
        old_path.mkdir(parents=True)
        new_path = str(old_path.parent / "NewProject")

        move_project(
            mock_claude_env["config"],
            mock_project["path"],
            new_path,
            dry_run=False,
            no_backup=True,
        )

        # Check claude.json content
        content = mock_claude_env["claude_json_file"].read_text()
        data = json.loads(content)
        assert new_path in data["projects"]
        assert mock_project["path"] not in data["projects"]


class TestExecuteRelativePaths:
    """Tests for execute function with relative paths."""

    def test_execute_with_relative_paths(self, mock_claude_env, mock_project):
        """Test that relative paths are converted to absolute paths."""
        # Create old folder
        old_path = Path(mock_project["path"])
        old_path.mkdir(parents=True)

        # Calculate relative paths from temp_dir
        temp_dir = mock_claude_env["claude_dir"].parent
        old_relative = "TestProject"
        new_relative = "NewProject"

        # Change to temp_dir to make relative paths work
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            args = Namespace(
                claude_dir=mock_claude_env["claude_dir"],
                old_path=old_relative,
                new_path=new_relative,
                dry_run=False,
                no_backup=True,
                interactive=False,
            )

            result = execute(args)

            assert result == 0
            assert not old_path.exists()
            assert (temp_dir / "NewProject").exists()

            # Check metadata updated with absolute paths
            all_paths = find_all_project_paths(mock_claude_env["config"])
            assert str(temp_dir / "NewProject") in all_paths
            assert mock_project["path"] not in all_paths
        finally:
            os.chdir(original_cwd)

    def test_execute_with_dot_relative_path(self, mock_claude_env, mock_project):
        """Test that ./relative paths work correctly."""
        # Create old folder
        old_path = Path(mock_project["path"])
        old_path.mkdir(parents=True)

        temp_dir = mock_claude_env["claude_dir"].parent
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            args = Namespace(
                claude_dir=mock_claude_env["claude_dir"],
                old_path="./TestProject",
                new_path="./NewProject",
                dry_run=False,
                no_backup=True,
                interactive=False,
            )

            result = execute(args)

            assert result == 0
            assert not old_path.exists()
            assert (temp_dir / "NewProject").exists()
        finally:
            os.chdir(original_cwd)
