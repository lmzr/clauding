"""Tests for clauding move command."""

import json
import os
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest

from clauding.commands.move import execute, move_project
from clauding.core.paths import normalize_path_to_dirname, find_all_project_paths


def _register_mock_project(mock_claude_env, project_path: str) -> dict:
    """Register a fake project at the given path in the mock Claude env."""
    dirname = normalize_path_to_dirname(project_path)
    project_dir = mock_claude_env["projects_dir"] / dirname
    project_dir.mkdir(parents=True, exist_ok=True)

    session_file = project_dir / "session-001.jsonl"
    session_data = {
        "cwd": project_path,
        "sessionId": "session-001",
        "type": "user",
        "message": {"role": "user", "content": "test"},
    }
    session_file.write_text(json.dumps(session_data) + "\n")

    history_entry = {
        "display": "test prompt",
        "project": project_path,
        "timestamp": 1234567890,
    }
    with open(mock_claude_env["history_file"], "a", encoding="utf-8") as f:
        f.write(json.dumps(history_entry) + "\n")

    claude_json_data = json.loads(mock_claude_env["claude_json_file"].read_text())
    claude_json_data.setdefault("projects", {})[project_path] = {"allowedTools": []}
    mock_claude_env["claude_json_file"].write_text(json.dumps(claude_json_data))

    return {
        "path": project_path,
        "dirname": dirname,
        "session_file": session_file,
        "project_dir": project_dir,
    }


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

    def test_move_into_existing_directory(self, mock_claude_env, mock_project):
        """Test move into existing directory puts source inside it."""
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

        # Should succeed - source moved inside destination
        assert result == 0
        # Source should be moved inside destination
        final_path = new_path / old_path.name
        assert final_path.exists()
        assert not old_path.exists()

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


class TestMovePrefix:
    """Tests for bulk-rename mode (OLD is a prefix of multiple projects)."""

    def test_move_prefix_match(self, mock_claude_env):
        """Three projects under /tmp/parent are all rewritten when renaming /tmp/parent -> /tmp/renamed."""
        temp_dir = mock_claude_env["claude_dir"].parent
        old_parent = temp_dir / "parent"
        new_parent = temp_dir / "renamed"

        # Create three projects on disk and register them
        projects = ["projA", "projB", "projC"]
        for name in projects:
            (old_parent / name).mkdir(parents=True)
            _register_mock_project(mock_claude_env, str(old_parent / name))

        result = move_project(
            mock_claude_env["config"],
            str(old_parent),
            str(new_parent),
            dry_run=False,
            no_backup=True,
            yes=True,
        )

        assert result == 0

        # All three projects rewritten in all three data locations
        all_paths = find_all_project_paths(mock_claude_env["config"])
        for name in projects:
            assert str(new_parent / name) in all_paths
            assert str(old_parent / name) not in all_paths

        # Folder physically moved
        assert not old_parent.exists()
        assert new_parent.exists()
        for name in projects:
            assert (new_parent / name).exists()

    def test_move_prefix_dry_run(self, mock_claude_env):
        """Dry-run lists changes but writes nothing."""
        temp_dir = mock_claude_env["claude_dir"].parent
        old_parent = temp_dir / "parent"
        new_parent = temp_dir / "renamed"

        for name in ["projA", "projB"]:
            (old_parent / name).mkdir(parents=True)
            _register_mock_project(mock_claude_env, str(old_parent / name))

        before = find_all_project_paths(mock_claude_env["config"])

        result = move_project(
            mock_claude_env["config"],
            str(old_parent),
            str(new_parent),
            dry_run=True,
            no_backup=True,
            yes=True,
        )

        assert result == 0
        # Nothing on disk changed
        assert old_parent.exists()
        assert not new_parent.exists()
        # Metadata unchanged
        after = find_all_project_paths(mock_claude_env["config"])
        assert set(before.keys()) == set(after.keys())

    def test_move_prefix_no_match_errors(self, mock_claude_env):
        """OLD that is neither an exact project path nor a prefix returns error."""
        temp_dir = mock_claude_env["claude_dir"].parent

        result = move_project(
            mock_claude_env["config"],
            str(temp_dir / "does-not-exist"),
            str(temp_dir / "whatever"),
            dry_run=False,
            no_backup=True,
            yes=True,
        )

        assert result == 1

    def test_move_prefix_partial_name_not_matched(self, mock_claude_env):
        """`/tmp/data` must not match `/tmp/database` (prefix-of-path, not substring)."""
        temp_dir = mock_claude_env["claude_dir"].parent
        data_proj = temp_dir / "data"
        database_proj = temp_dir / "database"

        data_proj.mkdir()
        database_proj.mkdir()
        _register_mock_project(mock_claude_env, str(data_proj))
        _register_mock_project(mock_claude_env, str(database_proj))

        # `data` is an exact registered project, so this is single mode — not bulk.
        # To force the bulk branch, register a child of `data` and call with `data` as a
        # prefix that's NOT itself registered.
        # Reset: deregister `/tmp/data` by removing it from all sources, then add `/tmp/data/sub`.
        claude_json_data = json.loads(mock_claude_env["claude_json_file"].read_text())
        del claude_json_data["projects"][str(data_proj)]
        mock_claude_env["claude_json_file"].write_text(json.dumps(claude_json_data))

        history_lines = mock_claude_env["history_file"].read_text().splitlines()
        kept = [
            line for line in history_lines
            if line.strip() and json.loads(line).get("project") != str(data_proj)
        ]
        mock_claude_env["history_file"].write_text("\n".join(kept) + ("\n" if kept else ""))

        # Remove `data`'s projects/ entry too
        data_dirname = normalize_path_to_dirname(str(data_proj))
        import shutil as _shutil
        _shutil.rmtree(mock_claude_env["projects_dir"] / data_dirname)

        # Now register a child so `data` is only a prefix
        (data_proj / "sub").mkdir()
        _register_mock_project(mock_claude_env, str(data_proj / "sub"))

        result = move_project(
            mock_claude_env["config"],
            str(data_proj),
            str(temp_dir / "X"),
            dry_run=False,
            no_backup=True,
            yes=True,
        )

        assert result == 0

        all_paths = find_all_project_paths(mock_claude_env["config"])
        # `data/sub` was renamed
        assert str(temp_dir / "X" / "sub") in all_paths
        assert str(data_proj / "sub") not in all_paths
        # `database` was NOT touched
        assert str(database_proj) in all_paths

    def test_move_prefix_collision_detected(self, mock_claude_env):
        """If a computed new_p collides with an unrelated registered project, abort."""
        temp_dir = mock_claude_env["claude_dir"].parent
        old_parent = temp_dir / "parent"
        new_parent = temp_dir / "renamed"

        (old_parent / "projA").mkdir(parents=True)
        _register_mock_project(mock_claude_env, str(old_parent / "projA"))

        # Pre-register the target path so it collides
        (new_parent / "projA").mkdir(parents=True)
        _register_mock_project(mock_claude_env, str(new_parent / "projA"))

        before = find_all_project_paths(mock_claude_env["config"])

        result = move_project(
            mock_claude_env["config"],
            str(old_parent),
            str(new_parent),
            dry_run=False,
            no_backup=True,
            yes=True,
        )

        assert result == 1
        # Nothing was changed
        after = find_all_project_paths(mock_claude_env["config"])
        assert set(before.keys()) == set(after.keys())
        assert old_parent.exists()

    def test_move_prefix_includes_exact_match(self, mock_claude_env):
        """OLD is itself a registered project AND a prefix of others (Claude run in repo + subdir)."""
        temp_dir = mock_claude_env["claude_dir"].parent
        old_parent = temp_dir / "repo"
        new_parent = temp_dir / "renamed"

        # Register both the parent and a subdirectory as projects
        (old_parent / "sub").mkdir(parents=True)
        _register_mock_project(mock_claude_env, str(old_parent))
        _register_mock_project(mock_claude_env, str(old_parent / "sub"))

        result = move_project(
            mock_claude_env["config"],
            str(old_parent),
            str(new_parent),
            dry_run=False,
            no_backup=True,
            yes=True,
        )

        assert result == 0

        all_paths = find_all_project_paths(mock_claude_env["config"])
        # Both the parent project and its registered subdir are rewritten
        assert str(new_parent) in all_paths
        assert str(new_parent / "sub") in all_paths
        assert str(old_parent) not in all_paths
        assert str(old_parent / "sub") not in all_paths

        # Folder physically moved at the parent level
        assert not old_parent.exists()
        assert (new_parent / "sub").exists()

    def test_move_prefix_folder_move_once(self, mock_claude_env):
        """When parent exists and target doesn't, a single shutil.move at parent level is used."""
        temp_dir = mock_claude_env["claude_dir"].parent
        old_parent = temp_dir / "parent"
        new_parent = temp_dir / "renamed"

        for name in ["projA", "projB"]:
            (old_parent / name).mkdir(parents=True)
            _register_mock_project(mock_claude_env, str(old_parent / name))

        with patch("clauding.commands.move.shutil.move") as mock_move:
            result = move_project(
                mock_claude_env["config"],
                str(old_parent),
                str(new_parent),
                dry_run=False,
                no_backup=True,
                yes=True,
            )

        assert result == 0
        # shutil.move called exactly once (at the parent level), not per-project
        assert mock_move.call_count == 1
        args, _ = mock_move.call_args
        assert args == (str(old_parent), str(new_parent))
