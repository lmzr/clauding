# clauding

A CLI tool for managing Claude Code projects. Handles path migrations when project folders are moved or renamed, and cleans up orphaned project references.

## Installation

### For users (recommended)

```bash
# Install pipx if not already installed
brew install pipx
pipx ensurepath

# Install clauding globally
pipx install /path/to/ClaudeCodeTools

# Now available from anywhere
clauding list
```

### For developers

```bash
cd ClaudeCodeTools
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Commands

### List Projects

```bash
# List all projects
clauding list

# List only projects with missing paths
clauding list --problems

# Output as JSON
clauding list --json
```

### Move Project

Move a project folder and update all Claude Code references.

```bash
# Move project (moves folder + updates metadata)
clauding move /old/path /new/path

# Preview changes without applying
clauding move /old/path /new/path --dry-run

# Interactive mode for multiple projects
clauding move --interactive
```

**Behavior:**
- If OLD exists and NEW doesn't: moves folder, then updates metadata
- If OLD doesn't exist and NEW exists: only updates metadata (folder already moved)
- If both exist or neither exists: error

### Clean Orphaned References

Remove references to projects that no longer exist on disk.

```bash
# Interactive mode (default) - prompts for each orphan
clauding clean

# Clean all orphans without prompts
clauding clean --all

# Preview what would be cleaned
clauding clean --dry-run

# Clean specific path only
clauding clean --path /path/to/deleted/project
```

## Options

| Flag | Commands | Description |
|------|----------|-------------|
| `--dry-run`, `-n` | move, clean | Preview without changes |
| `--problems`, `-p` | list | Show only missing paths |
| `--json`, `-j` | list | JSON output |
| `--interactive`, `-i` | move, clean | Interactive mode |
| `--all`, `-a` | clean | Clean all without prompts |
| `--path`, `-p` | clean | Specific path to clean |
| `--no-backup` | move, clean | Skip backup creation |
| `--claude-dir` | all | Custom .claude directory |

## How It Works

Claude Code stores project data in:
- `~/.claude/projects/` - Session files (directories named by normalized path)
- `~/.claude/history.jsonl` - Global history with `project` field
- `~/.claude.json` - User configuration with `projects` dictionary

When you move or rename a project folder, Claude Code loses track of it because it uses absolute paths as identifiers. This tool updates all references to maintain your session history.

## Development

```bash
# Install dev dependencies
pip install ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=clauding
```

## Requirements

- Python 3.10+
- No external dependencies (stdlib only)

## License

GPL-3.0
