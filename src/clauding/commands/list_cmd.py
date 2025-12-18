"""clauding list - List all Claude Code projects."""

import argparse
import json
from pathlib import Path

from clauding.core.config import ClaudeConfig
from clauding.core.paths import find_all_project_paths


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the list subcommand."""
    parser = subparsers.add_parser(
        "list",
        help="List all Claude Code projects",
        description="List all projects known to Claude Code with their status.",
    )
    parser.add_argument(
        "--problems", "-p",
        action="store_true",
        help="Show only projects with missing paths",
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output in JSON format",
    )
    parser.set_defaults(func=execute)


def execute(args: argparse.Namespace) -> int:
    """Execute the list command."""
    config = ClaudeConfig(claude_dir=args.claude_dir)
    all_paths = find_all_project_paths(config)

    if not all_paths:
        print("No projects found.")
        return 0

    # Filter to problems only if requested
    if args.problems:
        all_paths = {path: info for path, info in all_paths.items() if not info["exists"]}
        if not all_paths:
            print("All projects are accessible.")
            return 0

    # JSON output
    if args.json:
        print(json.dumps(all_paths, indent=2, default=str))
        return 0

    # Human-readable output
    count = len(all_paths)
    suffix = " with problems" if args.problems else ""
    print(f"Found {count} project(s){suffix}:\n")

    for path, info in sorted(all_paths.items()):
        status = "EXISTS" if info["exists"] else "NOT FOUND"
        name = Path(path).name

        print(f"{name}")
        print(f"  Path: {path}")
        print(f"  Status: {status}")

        sources_desc = []
        for source in info["sources"]:
            if source["type"] == "projects_dir":
                sources_desc.append(f"projects/ ({source['session_count']} sessions)")
            elif source["type"] == "history":
                sources_desc.append(f"history.jsonl ({source['entry_count']} entries)")
            elif source["type"] == "claude_json":
                sources_desc.append("~/.claude.json")

        if sources_desc:
            print(f"  Sources: {', '.join(sources_desc)}")
        print()

    return 0
