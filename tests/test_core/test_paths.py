"""Tests for clauding.core.paths module."""

import json
from pathlib import Path

import pytest

from clauding.core.paths import (
    normalize_path_to_dirname,
    extract_path_from_session,
    find_all_project_paths,
)


class TestNormalizePathToDirname:
    """Tests for normalize_path_to_dirname function."""

    @pytest.mark.parametrize(
        "input_path,expected",
        [
            ("/Users/test/Documents", "-Users-test-Documents"),
            ("/Users/test/My Projects", "-Users-test-My-Projects"),
            ("/Users/test/file.txt", "-Users-test-file-txt"),
            ("/Users/test/2 Projects", "-Users-test-2-Projects"),
            ("/Users/test/my_project", "-Users-test-my-project"),
            # Non-ASCII characters (using English borrowed words)
            ("/Users/test/naïve", "-Users-test-na-ve"),
            ("/Users/test/résumé", "-Users-test-r-sum-"),
        ],
    )
    def test_normalize_various_paths(self, input_path, expected):
        """Test path normalization with various inputs."""
        assert normalize_path_to_dirname(input_path) == expected

    def test_empty_path(self):
        """Test normalization of empty path."""
        assert normalize_path_to_dirname("") == ""

    def test_path_with_multiple_spaces(self):
        """Test path with multiple consecutive spaces."""
        result = normalize_path_to_dirname("/path/with  multiple   spaces")
        assert result == "-path-with--multiple---spaces"


class TestExtractPathFromSession:
    """Tests for extract_path_from_session function."""

    def test_extract_path_from_valid_session(self, temp_dir):
        """Test extracting path from a valid session file."""
        session_file = temp_dir / "session.jsonl"
        session_data = {"cwd": "/Users/test/project", "sessionId": "123"}
        session_file.write_text(json.dumps(session_data) + "\n")

        result = extract_path_from_session(session_file)
        assert result == "/Users/test/project"

    def test_extract_path_cwd_not_first_line(self, temp_dir):
        """Test extracting path when cwd is not in first line."""
        session_file = temp_dir / "session.jsonl"
        lines = [
            json.dumps({"type": "summary"}),
            json.dumps({"cwd": "/Users/test/project", "type": "user"}),
        ]
        session_file.write_text("\n".join(lines) + "\n")

        result = extract_path_from_session(session_file)
        assert result == "/Users/test/project"

    def test_extract_path_from_empty_file(self, temp_dir):
        """Test extracting path from empty file."""
        session_file = temp_dir / "session.jsonl"
        session_file.write_text("")

        result = extract_path_from_session(session_file)
        assert result is None

    def test_extract_path_no_cwd(self, temp_dir):
        """Test extracting path from file without cwd field."""
        session_file = temp_dir / "session.jsonl"
        session_file.write_text(json.dumps({"type": "summary"}) + "\n")

        result = extract_path_from_session(session_file)
        assert result is None

    def test_extract_path_nonexistent_file(self, temp_dir):
        """Test extracting path from nonexistent file."""
        session_file = temp_dir / "nonexistent.jsonl"

        result = extract_path_from_session(session_file)
        assert result is None


class TestFindAllProjectPaths:
    """Tests for find_all_project_paths function."""

    def test_find_empty_environment(self, mock_claude_env):
        """Test finding projects in empty environment."""
        # Clear the mock environment
        mock_claude_env["history_file"].write_text("")
        mock_claude_env["claude_json_file"].write_text("{}")

        result = find_all_project_paths(mock_claude_env["config"])
        assert result == {}

    def test_find_project_from_projects_dir(self, mock_claude_env, mock_project):
        """Test finding project from projects directory."""
        result = find_all_project_paths(mock_claude_env["config"])

        assert mock_project["path"] in result
        assert result[mock_project["path"]]["exists"] is False  # Path doesn't actually exist
        sources = result[mock_project["path"]]["sources"]
        assert any(s["type"] == "projects_dir" for s in sources)

    def test_find_project_from_history(self, mock_claude_env, mock_project):
        """Test finding project from history.jsonl."""
        result = find_all_project_paths(mock_claude_env["config"])

        assert mock_project["path"] in result
        sources = result[mock_project["path"]]["sources"]
        assert any(s["type"] == "history" for s in sources)

    def test_find_project_from_claude_json(self, mock_claude_env, mock_project):
        """Test finding project from .claude.json."""
        result = find_all_project_paths(mock_claude_env["config"])

        assert mock_project["path"] in result
        sources = result[mock_project["path"]]["sources"]
        assert any(s["type"] == "claude_json" for s in sources)

    def test_find_project_all_sources(self, mock_claude_env, mock_project):
        """Test that project is found from all three sources."""
        result = find_all_project_paths(mock_claude_env["config"])

        assert mock_project["path"] in result
        sources = result[mock_project["path"]]["sources"]

        source_types = {s["type"] for s in sources}
        assert source_types == {"projects_dir", "history", "claude_json"}
