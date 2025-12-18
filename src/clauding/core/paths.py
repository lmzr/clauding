"""Path normalization and discovery utilities."""

import json
from pathlib import Path
from typing import Optional

from clauding.core.config import ClaudeConfig


# Type alias for project info dictionary
ProjectInfo = dict


def normalize_path_to_dirname(path: str) -> str:
    """
    Convert a file path to Claude's project directory name format.

    Replaces special characters with '-':
    - '/' -> '-'
    - '.' -> '-'
    - ' ' -> '-'
    - '_' -> '-'
    - Non-ASCII characters (accented letters) -> '-'

    Args:
        path: Absolute file path

    Returns:
        Normalized directory name
    """
    result = []
    for char in path:
        if char in "/._ ":
            result.append("-")
        elif ord(char) < 128 and (char.isalnum() or char == "-"):
            result.append(char)
        else:
            result.append("-")
    return "".join(result)


def extract_path_from_session(session_file: Path) -> Optional[str]:
    """
    Extract the project path (cwd) from a session file.

    Args:
        session_file: Path to a session .jsonl file

    Returns:
        The project path or None if not found
    """
    try:
        with open(session_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    if "cwd" in data:
                        return data["cwd"]
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return None


def find_all_project_paths(config: ClaudeConfig) -> dict[str, ProjectInfo]:
    """
    Find all project paths referenced in Claude Code configuration.

    Searches in:
    - ~/.claude/projects/ (session files)
    - ~/.claude/history.jsonl
    - ~/.claude.json

    Args:
        config: ClaudeConfig instance

    Returns:
        Dictionary mapping paths to project info:
        {
            "/path/to/project": {
                "path": "/path/to/project",
                "exists": True/False,
                "sources": [
                    {"type": "projects_dir", "dirname": "...", "session_count": N},
                    {"type": "history", "entry_count": N},
                    {"type": "claude_json", "has_config": True}
                ]
            }
        }
    """
    all_paths: dict[str, ProjectInfo] = {}

    # 1. From ~/.claude/projects/ directories
    if config.projects_dir.exists():
        for project_dir in config.projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            session_files = list(project_dir.glob("*.jsonl"))
            if not session_files:
                continue

            path = extract_path_from_session(session_files[0])
            if path:
                if path not in all_paths:
                    all_paths[path] = {
                        "path": path,
                        "exists": Path(path).exists(),
                        "sources": [],
                    }
                all_paths[path]["sources"].append({
                    "type": "projects_dir",
                    "dirname": project_dir.name,
                    "session_count": len(session_files),
                })

    # 2. From ~/.claude/history.jsonl
    if config.history_file.exists():
        with open(config.history_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    path = data.get("project")
                    if path:
                        if path not in all_paths:
                            all_paths[path] = {
                                "path": path,
                                "exists": Path(path).exists(),
                                "sources": [],
                            }
                        history_source = next(
                            (s for s in all_paths[path]["sources"] if s["type"] == "history"),
                            None,
                        )
                        if history_source:
                            history_source["entry_count"] += 1
                        else:
                            all_paths[path]["sources"].append({
                                "type": "history",
                                "entry_count": 1,
                            })
                except json.JSONDecodeError:
                    continue

    # 3. From ~/.claude.json
    if config.claude_json_file.exists():
        try:
            with open(config.claude_json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "projects" in data:
                    for path in data["projects"].keys():
                        if path not in all_paths:
                            all_paths[path] = {
                                "path": path,
                                "exists": Path(path).exists(),
                                "sources": [],
                            }
                        all_paths[path]["sources"].append({
                            "type": "claude_json",
                            "has_config": True,
                        })
        except json.JSONDecodeError:
            pass

    return all_paths
