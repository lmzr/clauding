"""Tests for clauding list command."""

import json
from argparse import Namespace

import pytest

from clauding.commands.list_cmd import execute


class TestListCommand:
    """Tests for list command execute function."""

    def test_list_empty_environment(self, mock_claude_env, capsys):
        """Test list with empty environment."""
        # Clear environment
        mock_claude_env["history_file"].write_text("")
        mock_claude_env["claude_json_file"].write_text("{}")

        args = Namespace(
            claude_dir=mock_claude_env["claude_dir"],
            problems=False,
            json=False,
        )

        result = execute(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "No projects found" in captured.out

    def test_list_with_project(self, mock_claude_env, mock_project, capsys):
        """Test list with a project."""
        args = Namespace(
            claude_dir=mock_claude_env["claude_dir"],
            problems=False,
            json=False,
        )

        result = execute(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Found 1 project" in captured.out
        assert "TestProject" in captured.out

    def test_list_problems_all_accessible(self, mock_claude_env, capsys):
        """Test list --problems when all projects accessible."""
        # Create a project that actually exists
        project_path = mock_claude_env["claude_dir"].parent / "RealProject"
        project_path.mkdir()

        # Add to history
        mock_claude_env["history_file"].write_text(
            json.dumps({"project": str(project_path)}) + "\n"
        )

        args = Namespace(
            claude_dir=mock_claude_env["claude_dir"],
            problems=True,
            json=False,
        )

        result = execute(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "All projects are accessible" in captured.out

    def test_list_problems_with_missing(self, mock_claude_env, mock_project, capsys):
        """Test list --problems with missing project."""
        args = Namespace(
            claude_dir=mock_claude_env["claude_dir"],
            problems=True,
            json=False,
        )

        result = execute(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "with problems" in captured.out
        assert "TestProject" in captured.out

    def test_list_json_output(self, mock_claude_env, mock_project, capsys):
        """Test list with JSON output."""
        args = Namespace(
            claude_dir=mock_claude_env["claude_dir"],
            problems=False,
            json=True,
        )

        result = execute(args)

        assert result == 0
        captured = capsys.readouterr()

        # Parse JSON output
        data = json.loads(captured.out)
        assert mock_project["path"] in data
        assert "exists" in data[mock_project["path"]]
        assert "sources" in data[mock_project["path"]]
