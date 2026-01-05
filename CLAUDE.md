# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`clauding` is a CLI tool for managing Claude Code project references when folders are moved or renamed.

## Installation

When asked to install `clauding` globally, run:

```bash
./scripts/install.sh
```

This script uses `pipx` to install `clauding` as a global command.

## Commands

```bash
# Development setup
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run CLI
clauding list [paths...]           # List all or specific projects
clauding list --problems           # Show only missing paths
clauding move                      # Interactive wizard mode
clauding move OLD NEW              # Direct move
clauding clean                     # Interactive cleanup
clauding clean --force             # Clean all without prompts

# Run tests
pytest
pytest --cov=clauding
```

## Architecture

```
src/clauding/
├── cli.py              # Main CLI with argparse subparsers
├── core/
│   ├── config.py       # ClaudeConfig (paths to ~/.claude, etc.)
│   ├── paths.py        # normalize_path_to_dirname, find_all_project_paths
│   └── backup.py       # create_backup
└── commands/
    ├── list_cmd.py     # clauding list
    ├── move.py         # clauding move
    └── clean.py        # clauding clean
scripts/
└── install.sh          # Global installation script (pipx)
```

### Claude Code Data Locations

- `~/.claude/projects/{normalized-path}/` - Session JSONL files
- `~/.claude/history.jsonl` - Global history (`project` field)
- `~/.claude.json` - User config (`projects` dictionary)

### Path Normalization

Claude converts paths to directory names: `/`, `.`, ` `, `_`, non-ASCII -> `-`

Example: `/Users/test/My Project` -> `-Users-test-My-Project`
