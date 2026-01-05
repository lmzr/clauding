"""clauding backups - List and manage backups."""

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

from clauding.core.config import ClaudeConfig


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the backups subcommand."""
    parser = subparsers.add_parser(
        "backups",
        help="List and manage backups",
        description="List and prune Claude Code configuration backups.",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Enable deletion mode (requires --older-than or --keep)",
    )
    parser.add_argument(
        "--older-than",
        type=int,
        metavar="DAYS",
        help="Delete backups older than N days",
    )
    parser.add_argument(
        "--keep",
        type=int,
        metavar="N",
        help="Keep only the N most recent backups",
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Delete without confirmation prompts",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be deleted without making changes",
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output in JSON format (list mode only)",
    )
    parser.set_defaults(func=execute)


def execute(args: argparse.Namespace) -> int:
    """Execute the backups command."""
    config = ClaudeConfig(claude_dir=args.claude_dir)

    # Get all backups
    backups = get_all_backups(config)

    # Prune mode
    if args.prune:
        if not args.older_than and not args.keep:
            print("Error: --prune requires --older-than and/or --keep")
            return 1
        return prune_backups(config, backups, args)

    # List mode (default)
    return list_backups(backups, args.json)


def get_all_backups(config: ClaudeConfig) -> list[dict]:
    """Get all backups sorted by date (most recent first)."""
    backups = []

    if not config.backup_dir.exists():
        return backups

    for backup_dir in config.backup_dir.iterdir():
        if backup_dir.is_dir() and backup_dir.name.startswith("backup_"):
            info = get_backup_info(backup_dir)
            if info:
                backups.append(info)

    # Sort by date, most recent first
    backups.sort(key=lambda b: b["timestamp"], reverse=True)
    return backups


def get_backup_info(backup_path: Path) -> dict | None:
    """Extract backup metadata from directory."""
    name = backup_path.name

    # Check for backup_ prefix
    if not name.startswith("backup_"):
        return None

    # Parse timestamp from name: backup_YYYYMMDD_HHMMSS
    try:
        timestamp_str = name[7:]  # Remove "backup_" prefix
        timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
    except ValueError:
        return None

    size = calculate_dir_size(backup_path)

    return {
        "name": name,
        "path": backup_path,
        "timestamp": timestamp,
        "size": size,
    }


def calculate_dir_size(path: Path) -> int:
    """Calculate total size of a directory in bytes."""
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


def format_size(size_bytes: int) -> str:
    """Format size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def list_backups(backups: list[dict], as_json: bool) -> int:
    """List all backups."""
    if as_json:
        output = {
            "backups": [
                {
                    "name": b["name"],
                    "path": str(b["path"]),
                    "timestamp": b["timestamp"].isoformat(),
                    "size": b["size"],
                }
                for b in backups
            ],
            "total_count": len(backups),
            "total_size": sum(b["size"] for b in backups),
        }
        print(json.dumps(output, indent=2))
        return 0

    if not backups:
        print("No backups found.")
        return 0

    print(f"Found {len(backups)} backup(s):\n")

    for backup in backups:
        date_str = backup["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        size_str = format_size(backup["size"])
        print(f"  {backup['name']}")
        print(f"    Date: {date_str}")
        print(f"    Size: {size_str}")
        print()

    total_size = sum(b["size"] for b in backups)
    print(f"Total: {len(backups)} backup(s), {format_size(total_size)}")

    return 0


def prune_backups(config: ClaudeConfig, backups: list[dict], args: argparse.Namespace) -> int:
    """Prune backups based on criteria."""
    now = datetime.now()

    # Select backups to delete
    to_delete = []
    for i, backup in enumerate(backups):
        should_delete = True

        # Check --keep: keep the N most recent
        if args.keep and i < args.keep:
            should_delete = False

        # Check --older-than: must be older than N days
        if args.older_than:
            age_days = (now - backup["timestamp"]).days
            if age_days <= args.older_than:
                should_delete = False

        if should_delete:
            to_delete.append(backup)

    if not to_delete:
        print("No backups match the deletion criteria.")
        return 0

    # Dry run mode
    if args.dry_run:
        return show_dry_run(to_delete)

    # Force mode - delete all
    if args.force:
        return delete_all(to_delete)

    # Interactive mode (default)
    return interactive_delete(to_delete)


def show_dry_run(to_delete: list[dict]) -> int:
    """Show what would be deleted."""
    print(f"[DRY RUN] Would delete {len(to_delete)} backup(s):\n")

    for backup in to_delete:
        date_str = backup["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        size_str = format_size(backup["size"])
        print(f"  {backup['name']} ({date_str}, {size_str})")

    total_size = sum(b["size"] for b in to_delete)
    print(f"\nTotal: {len(to_delete)} backup(s), {format_size(total_size)}")

    return 0


def delete_all(to_delete: list[dict]) -> int:
    """Delete all specified backups."""
    print(f"Deleting {len(to_delete)} backup(s)...")

    for backup in to_delete:
        shutil.rmtree(backup["path"])
        print(f"  Deleted: {backup['name']}")

    total_size = sum(b["size"] for b in to_delete)
    print(f"\nDeleted {len(to_delete)} backup(s), freed {format_size(total_size)}")

    return 0


def interactive_delete(to_delete: list[dict]) -> int:
    """Interactive mode - prompt for each backup."""
    print(f"Found {len(to_delete)} backup(s) to delete.\n")

    confirmed = []
    for backup in to_delete:
        date_str = backup["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        size_str = format_size(backup["size"])
        print(f"  {backup['name']} ({date_str}, {size_str})")

        choice = input("  Delete? [y/N/a(ll)/q(uit)]: ").strip().lower()

        if choice == "q":
            print("Aborted.")
            return 0
        elif choice == "a":
            # Delete this and all remaining
            confirmed.append(backup)
            for remaining in to_delete:
                if remaining not in confirmed:
                    confirmed.append(remaining)
            break
        elif choice == "y":
            confirmed.append(backup)

        print()

    if not confirmed:
        print("Nothing to delete.")
        return 0

    print(f"\nDeleting {len(confirmed)} backup(s)...")

    for backup in confirmed:
        shutil.rmtree(backup["path"])
        print(f"  Deleted: {backup['name']}")

    total_size = sum(b["size"] for b in confirmed)
    print(f"\nDeleted {len(confirmed)} backup(s), freed {format_size(total_size)}")

    return 0
