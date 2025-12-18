"""Tests for clauding clean command."""

import json
from pathlib import Path

import pytest

from clauding.commands.clean import clean_projects
from clauding.core.paths import find_all_project_paths


class TestCleanProjects:
    """Tests for clean_projects function."""

    def test_clean_removes_project_directory(self, mock_claude_env, mock_project):
        """Test that cleaning removes project directory."""
        all_paths = find_all_project_paths(mock_claude_env["config"])
        orphans = {mock_project["path"]: all_paths[mock_project["path"]]}

        clean_projects(mock_claude_env["config"], orphans)

        assert not mock_project["project_dir"].exists()

    def test_clean_removes_history_entries(self, mock_claude_env, mock_project):
        """Test that cleaning removes history entries."""
        all_paths = find_all_project_paths(mock_claude_env["config"])
        orphans = {mock_project["path"]: all_paths[mock_project["path"]]}

        stats = clean_projects(mock_claude_env["config"], orphans)

        assert stats["history"] == 1

        # Verify history content
        content = mock_claude_env["history_file"].read_text()
        assert content.strip() == ""

    def test_clean_removes_claude_json_entries(self, mock_claude_env, mock_project):
        """Test that cleaning removes .claude.json entries."""
        all_paths = find_all_project_paths(mock_claude_env["config"])
        orphans = {mock_project["path"]: all_paths[mock_project["path"]]}

        stats = clean_projects(mock_claude_env["config"], orphans)

        assert stats["config"] == 1

        # Verify claude.json content
        content = mock_claude_env["claude_json_file"].read_text()
        data = json.loads(content)
        assert mock_project["path"] not in data.get("projects", {})

    def test_clean_returns_stats(self, mock_claude_env, mock_project):
        """Test that cleaning returns correct statistics."""
        all_paths = find_all_project_paths(mock_claude_env["config"])
        orphans = {mock_project["path"]: all_paths[mock_project["path"]]}

        stats = clean_projects(mock_claude_env["config"], orphans)

        assert stats["dirs"] == 1
        assert stats["history"] == 1
        assert stats["config"] == 1

    def test_clean_preserves_other_projects(self, mock_claude_env, mock_project):
        """Test that cleaning preserves other projects."""
        # Add another project to history
        other_path = "/Users/other/project"
        history_content = mock_claude_env["history_file"].read_text()
        new_entry = json.dumps({"project": other_path, "display": "other"})
        mock_claude_env["history_file"].write_text(history_content + new_entry + "\n")

        # Add to claude.json
        claude_json_content = json.loads(mock_claude_env["claude_json_file"].read_text())
        claude_json_content["projects"][other_path] = {}
        mock_claude_env["claude_json_file"].write_text(json.dumps(claude_json_content))

        # Clean only the mock project
        all_paths = find_all_project_paths(mock_claude_env["config"])
        orphans = {mock_project["path"]: all_paths[mock_project["path"]]}

        clean_projects(mock_claude_env["config"], orphans)

        # Verify other project preserved
        history_content = mock_claude_env["history_file"].read_text()
        assert other_path in history_content

        claude_json_content = json.loads(mock_claude_env["claude_json_file"].read_text())
        assert other_path in claude_json_content["projects"]
