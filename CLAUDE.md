# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`clauding` is a CLI tool for managing Claude Code project references when folders are moved or renamed.

## Commands

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install ".[dev]"

# Run CLI
clauding list
clauding move OLD NEW
clauding clean

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
```

### Claude Code Data Locations

- `~/.claude/projects/{normalized-path}/` - Session JSONL files
- `~/.claude/history.jsonl` - Global history (`project` field)
- `~/.claude.json` - User config (`projects` dictionary)

### Path Normalization

Claude converts paths to directory names: `/`, `.`, ` `, `_`, non-ASCII -> `-`

Example: `/Users/test/My Project` -> `-Users-test-My-Project`
