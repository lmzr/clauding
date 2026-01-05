"""clauding move - Move project paths."""

import argparse
import json
import shutil
from pathlib import Path

from clauding.core.config import ClaudeConfig
from clauding.core.paths import normalize_path_to_dirname, find_all_project_paths
from clauding.core.backup import create_backup


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the move subcommand."""
    parser = subparsers.add_parser(
        "move",
        help="Move project path references",
        description="Move a project folder and update Claude Code references.",
    )
    parser.add_argument(
        "old_path",
        nargs="?",
        help="Current/old project path",
    )
    parser.add_argument(
        "new_path",
        nargs="?",
        help="New project path",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating a backup before changes",
    )
    parser.set_defaults(func=execute)


def execute(args: argparse.Namespace) -> int:
    """Execute the move command."""
    config = ClaudeConfig(claude_dir=args.claude_dir)

    # No args = wizard mode
    if not args.old_path and not args.new_path:
        return interactive_mode(config, args.dry_run, args.no_backup)

    if not args.old_path or not args.new_path:
        print("Error: Both OLD_PATH and NEW_PATH are required")
        return 1

    # Convert to absolute paths (Claude stores absolute paths)
    old_path = str(Path(args.old_path).resolve())
    new_path = str(Path(args.new_path).resolve())

    return move_project(config, old_path, new_path, args.dry_run, args.no_backup)


def move_project(
    config: ClaudeConfig,
    old_path: str,
    new_path: str,
    dry_run: bool = False,
    no_backup: bool = False,
) -> int:
    """
    Move a project from old path to new path.

    Behavior:
    - If OLD exists and NEW doesn't: move folder, then update metadata
    - If OLD doesn't exist and NEW exists: skip folder move, only update metadata
    - If both exist or neither exists: error
    """
    old_exists = Path(old_path).exists()
    new_exists = Path(new_path).exists()

    # Determine action
    if old_exists and not new_exists:
        need_folder_move = True
    elif not old_exists and new_exists:
        need_folder_move = False
    elif old_exists and new_exists:
        print(f"Error: Both paths exist")
        print(f"  Old: {old_path}")
        print(f"  New: {new_path}")
        return 1
    else:
        print(f"Error: Neither path exists")
        print(f"  Old: {old_path}")
        print(f"  New: {new_path}")
        return 1

    # Check that old path is referenced in Claude config
    all_paths = find_all_project_paths(config)
    if old_path not in all_paths:
        print(f"Error: Path not found in Claude config: {old_path}")
        return 1

    # Check that new path is not already referenced
    if new_path in all_paths:
        print(f"Error: New path already exists in Claude config: {new_path}")
        return 1

    # Plan output
    prefix = "[DRY RUN] " if dry_run else ""
    print(f"{prefix}Move: {old_path} -> {new_path}")

    if need_folder_move:
        print(f"{prefix}  Folder: will be moved")
    else:
        print(f"{prefix}  Folder: already moved (metadata-only)")

    if dry_run:
        print(f"\n{prefix}Would update:")
        _show_metadata_changes(config, old_path, new_path)
        return 0

    # Create backup
    if not no_backup:
        backup_path = create_backup(config)
        print(f"Backup: {backup_path}")

    # Move folder if needed
    if need_folder_move:
        new_parent = Path(new_path).parent
        if not new_parent.exists():
            print(f"Error: Destination parent does not exist: {new_parent}")
            return 1

        shutil.move(old_path, new_path)
        print(f"Moved folder: {old_path} -> {new_path}")

    # Update metadata
    _update_metadata(config, old_path, new_path)

    print("Done.")
    return 0


def _show_metadata_changes(config: ClaudeConfig, old_path: str, new_path: str) -> None:
    """Show what metadata changes would be made."""
    old_dirname = normalize_path_to_dirname(old_path)
    new_dirname = normalize_path_to_dirname(new_path)

    old_project_dir = config.projects_dir / old_dirname
    if old_project_dir.exists():
        session_count = len(list(old_project_dir.glob("*.jsonl")))
        print(f"  - projects/{old_dirname} -> projects/{new_dirname} ({session_count} sessions)")

    if config.history_file.exists():
        print(f"  - history.jsonl (path references)")

    if config.claude_json_file.exists():
        print(f"  - ~/.claude.json (project key)")


def _update_metadata(config: ClaudeConfig, old_path: str, new_path: str) -> None:
    """Update all Claude metadata for the path change."""
    old_dirname = normalize_path_to_dirname(old_path)
    new_dirname = normalize_path_to_dirname(new_path)

    # 1. Rename project directory
    old_project_dir = config.projects_dir / old_dirname
    new_project_dir = config.projects_dir / new_dirname

    if old_project_dir.exists():
        old_project_dir.rename(new_project_dir)
        print(f"Updated: projects/{old_dirname} -> projects/{new_dirname}")

        # 2. Update session files
        for session_file in new_project_dir.glob("*.jsonl"):
            _update_jsonl_file(session_file, old_path, new_path)

    # 3. Update history.jsonl
    if config.history_file.exists():
        _update_jsonl_file(config.history_file, old_path, new_path)
        print(f"Updated: history.jsonl")

    # 4. Update ~/.claude.json
    if config.claude_json_file.exists():
        _update_claude_json(config.claude_json_file, old_path, new_path)
        print(f"Updated: ~/.claude.json")


def _update_jsonl_file(file_path: Path, old_path: str, new_path: str) -> None:
    """Update all occurrences of old_path with new_path in a JSONL file."""
    temp_file = file_path.with_suffix(".jsonl.tmp")

    with open(file_path, "r", encoding="utf-8") as f_in:
        with open(temp_file, "w", encoding="utf-8") as f_out:
            for line in f_in:
                updated_line = line.replace(old_path, new_path)
                f_out.write(updated_line)

    temp_file.replace(file_path)


def _update_claude_json(file_path: Path, old_path: str, new_path: str) -> None:
    """Update the ~/.claude.json file to rename project key."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "projects" in data and old_path in data["projects"]:
        data["projects"][new_path] = data["projects"][old_path]
        del data["projects"][old_path]

        temp_file = file_path.with_suffix(".json.tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_file.replace(file_path)


def interactive_mode(config: ClaudeConfig, dry_run: bool, no_backup: bool) -> int:
    """Run interactive mode to fix multiple projects."""
    print("Claude Code Project Migrator - Interactive Mode")
    print("=" * 50)

    while True:
        all_paths = find_all_project_paths(config)
        if not all_paths:
            print("\nNo projects found.")
            return 0

        # Find projects with issues
        problems = [(path, info) for path, info in all_paths.items() if not info["exists"]]

        if not problems:
            print("\nAll projects are accessible.")
            return 0

        print(f"\nFound {len(problems)} project(s) with missing paths:\n")
        for i, (path, info) in enumerate(problems, 1):
            name = Path(path).name
            print(f"  {i}. {name}")
            print(f"     {path}")

        print("\nOptions:")
        print("  [1-N] Select project to move")
        print("  [s] Skip / Exit")

        choice = input("\nChoice: ").strip().lower()

        if choice == "s":
            return 0

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(problems):
                old_path, _ = problems[idx]
                print(f"\nMoving: {old_path}")
                new_path = input("New path: ").strip().strip("'\"")

                if not new_path:
                    print("Cancelled.")
                    continue

                # Dry run first
                if not dry_run:
                    print("\nPreview:")
                    move_project(config, old_path, new_path, dry_run=True, no_backup=True)
                    confirm = input("\nProceed? [y/N]: ").strip().lower()
                    if confirm != "y":
                        print("Cancelled.")
                        continue

                result = move_project(config, old_path, new_path, dry_run, no_backup)
                if result != 0:
                    print("Move failed.")
            else:
                print("Invalid choice.")
        except ValueError:
            print("Invalid input.")

    return 0
