"""Main CLI entry point for clauding."""

import argparse
import sys
from pathlib import Path

from clauding import __version__
from clauding.commands import list_cmd, move, clean


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="clauding",
        description="Claude Code project management tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--claude-dir",
        type=Path,
        help="Custom .claude directory (default: ~/.claude)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Register subcommands
    list_cmd.register(subparsers)
    move.register(subparsers)
    clean.register(subparsers)

    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nAborted.")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
