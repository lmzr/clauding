#!/bin/bash
# Install clauding CLI tool globally using pipx

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Check if pipx is installed
if ! command -v pipx &> /dev/null; then
    echo "pipx not found. Installing via brew..."
    brew install pipx
    pipx ensurepath
    echo "Please restart your shell or run: source ~/.zshrc"
fi

# Install or reinstall clauding
echo "Installing clauding from $PROJECT_DIR..."
pipx install --force "$PROJECT_DIR"

echo ""
echo "Done! Run 'clauding --help' to get started."
