# clauding

A CLI tool for managing Claude Code projects. Handles path migrations when project folders are moved or renamed, and cleans up orphaned project references.

## Installation

### For users (recommended)

```bash
# Install pipx if not already installed
brew install pipx
pipx ensurepath

# Install clauding globally
pipx install /path/to/ClaudingTools

# Or use the install script
./scripts/install.sh

# Now available from anywhere
clauding list
```

### For developers

```bash
cd ClaudingTools
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Commands

### List Projects

```bash
# List all projects
clauding list

# Check specific paths
clauding list /path/to/project1 /path/to/project2

# List only projects with missing paths
clauding list --problems

# Output as JSON
clauding list --json

# Combine options
clauding list /path/to/project --json
```

### Move Project

Move a project folder and update all Claude Code references.

```bash
# Interactive wizard mode (finds orphaned projects)
clauding move

# Direct move (moves folder + updates metadata)
clauding move /old/path /new/path

# Preview changes without applying
clauding move /old/path /new/path --dry-run
```

**Behavior:**
- If OLD exists and NEW doesn't: moves folder, then updates metadata
- If OLD exists and NEW is a directory: moves OLD inside NEW (e.g., `/a/proj` → `/b/` becomes `/b/proj`)
- If OLD doesn't exist and NEW exists: only updates metadata (folder already moved)
- Neither exists: error
- Files are rejected (directories only)
- Moving a folder into itself is prevented

### Clean Orphaned References

Remove references to projects that no longer exist on disk.

```bash
# Interactive mode (default) - prompts for each orphan
clauding clean

# Clean all orphans without prompts
clauding clean --force

# Preview what would be cleaned
clauding clean --dry-run

# Clean specific path only
clauding clean --path /path/to/deleted/project
```

### Manage Backups

List and prune configuration backups created by move and clean commands.

```bash
# List all backups
clauding backups

# List in JSON format
clauding backups --json

# Delete old backups (requires --prune)
clauding backups --prune --older-than 30    # Older than 30 days
clauding backups --prune --keep 5           # Keep only 5 most recent
clauding backups --prune --older-than 7 --keep 3  # Combined criteria

# Preview without deleting
clauding backups --prune --keep 5 --dry-run

# Delete without confirmation
clauding backups --prune --keep 5 --force
```

## Options

| Flag | Commands | Description |
|------|----------|-------------|
| `--dry-run`, `-n` | move, clean, backups | Preview without changes |
| `--force`, `-f` | clean, backups | Skip confirmation prompts |
| `--problems`, `-p` | list | Show only missing paths |
| `--json`, `-j` | list, backups | JSON output |
| `--path`, `-p` | clean | Specific path to clean |
| `--no-backup` | move, clean | Skip backup creation |
| `--prune` | backups | Enable deletion mode |
| `--older-than` | backups | Delete backups older than N days |
| `--keep` | backups | Keep only N most recent backups |
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
pip install -e ".[dev]"

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
