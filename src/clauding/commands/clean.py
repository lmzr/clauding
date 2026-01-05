"""clauding clean - Clean up orphaned project references."""

import argparse
import json
import shutil
from pathlib import Path

from clauding.core.config import ClaudeConfig
from clauding.core.paths import find_all_project_paths
from clauding.core.backup import create_backup


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the clean subcommand."""
    parser = subparsers.add_parser(
        "clean",
        help="Remove references to nonexistent projects",
        description="Clean up Claude Code configuration for deleted projects.",
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Clean all orphaned references without prompts",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be cleaned without making changes",
    )
    parser.add_argument(
        "--path", "-p",
        action="append",
        dest="paths",
        help="Specific path(s) to clean (can be repeated)",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating a backup before changes",
    )
    parser.set_defaults(func=execute)


def execute(args: argparse.Namespace) -> int:
    """Execute the clean command."""
    config = ClaudeConfig(claude_dir=args.claude_dir)

    # Find orphaned projects
    all_paths = find_all_project_paths(config)
    orphans = {path: info for path, info in all_paths.items() if not info["exists"]}

    if not orphans:
        print("No orphaned projects found.")
        return 0

    # Filter to specific paths if provided
    if args.paths:
        orphans = {path: info for path, info in orphans.items() if path in args.paths}
        if not orphans:
            print("Specified paths not found in orphaned projects.")
            return 0

    # Dry run mode
    if args.dry_run:
        return show_dry_run(orphans)

    # Force mode - clean everything
    if args.force:
        return clean_all(config, orphans, args.no_backup)

    # Interactive mode (default)
    return interactive_clean(config, orphans, args.no_backup)


def show_dry_run(orphans: dict) -> int:
    """Show what would be cleaned."""
    print(f"[DRY RUN] Found {len(orphans)} orphaned project(s):\n")

    for path, info in sorted(orphans.items()):
        name = Path(path).name
        print(f"  {name}")
        print(f"    Path: {path}")

        for source in info["sources"]:
            if source["type"] == "projects_dir":
                print(f"    Would remove: projects/{source['dirname']} ({source['session_count']} sessions)")
            elif source["type"] == "history":
                print(f"    Would remove: {source['entry_count']} history entries")
            elif source["type"] == "claude_json":
                print(f"    Would remove: ~/.claude.json entry")
        print()

    return 0


def clean_all(config: ClaudeConfig, orphans: dict, no_backup: bool) -> int:
    """Clean all orphaned projects."""
    print(f"Cleaning {len(orphans)} orphaned project(s)...")

    if not no_backup:
        backup_path = create_backup(config)
        print(f"Backup: {backup_path}\n")

    stats = clean_projects(config, orphans)

    print(f"\nCleaned:")
    print(f"  Project directories: {stats['dirs']}")
    print(f"  History entries: {stats['history']}")
    print(f"  Config entries: {stats['config']}")

    return 0


def interactive_clean(config: ClaudeConfig, orphans: dict, no_backup: bool) -> int:
    """Interactive mode - prompt for each orphan."""
    print(f"Found {len(orphans)} orphaned project(s).\n")

    to_clean = {}
    for path, info in sorted(orphans.items()):
        name = Path(path).name
        print(f"  {name}")
        print(f"  Path: {path}")

        sources_desc = []
        for source in info["sources"]:
            if source["type"] == "projects_dir":
                sources_desc.append(f"projects/ ({source['session_count']} sessions)")
            elif source["type"] == "history":
                sources_desc.append(f"history ({source['entry_count']} entries)")
            elif source["type"] == "claude_json":
                sources_desc.append("config")

        print(f"  Sources: {', '.join(sources_desc)}")

        choice = input("  Clean? [y/N/a(ll)/q(uit)]: ").strip().lower()

        if choice == "q":
            print("Aborted.")
            return 0
        elif choice == "a":
            # Clean this and all remaining
            to_clean[path] = info
            for remaining_path, remaining_info in orphans.items():
                if remaining_path not in to_clean:
                    to_clean[remaining_path] = remaining_info
            break
        elif choice == "y":
            to_clean[path] = info

        print()

    if not to_clean:
        print("Nothing to clean.")
        return 0

    print(f"\nCleaning {len(to_clean)} project(s)...")

    if not no_backup:
        backup_path = create_backup(config)
        print(f"Backup: {backup_path}\n")

    stats = clean_projects(config, to_clean)

    print(f"\nCleaned:")
    print(f"  Project directories: {stats['dirs']}")
    print(f"  History entries: {stats['history']}")
    print(f"  Config entries: {stats['config']}")

    return 0


def clean_projects(config: ClaudeConfig, projects: dict) -> dict:
    """Clean the specified projects from Claude configuration."""
    stats = {"dirs": 0, "history": 0, "config": 0}
    paths_to_remove = set(projects.keys())

    # 1. Remove project directories
    for path, info in projects.items():
        for source in info["sources"]:
            if source["type"] == "projects_dir":
                project_dir = config.projects_dir / source["dirname"]
                if project_dir.exists():
                    shutil.rmtree(project_dir)
                    stats["dirs"] += 1

    # 2. Clean history.jsonl
    if config.history_file.exists():
        stats["history"] = _clean_history_file(config.history_file, paths_to_remove)

    # 3. Clean ~/.claude.json
    if config.claude_json_file.exists():
        stats["config"] = _clean_claude_json(config.claude_json_file, paths_to_remove)

    return stats


def _clean_history_file(file_path: Path, paths_to_remove: set) -> int:
    """Remove entries from history.jsonl for specified projects."""
    temp_file = file_path.with_suffix(".jsonl.tmp")
    removed_count = 0

    with open(file_path, "r", encoding="utf-8") as f_in:
        with open(temp_file, "w", encoding="utf-8") as f_out:
            for line in f_in:
                if not line.strip():
                    f_out.write(line)
                    continue

                try:
                    data = json.loads(line)
                    if data.get("project") not in paths_to_remove:
                        f_out.write(line)
                    else:
                        removed_count += 1
                except json.JSONDecodeError:
                    f_out.write(line)

    temp_file.replace(file_path)
    return removed_count


def _clean_claude_json(file_path: Path, paths_to_remove: set) -> int:
    """Remove entries from ~/.claude.json for specified projects."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    removed_count = 0
    if "projects" in data:
        keys_to_remove = [path for path in data["projects"].keys() if path in paths_to_remove]
        removed_count = len(keys_to_remove)

        if removed_count > 0:
            for path in keys_to_remove:
                del data["projects"][path]

            temp_file = file_path.with_suffix(".json.tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            temp_file.replace(file_path)

    return removed_count
