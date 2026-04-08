#!/usr/bin/env bash
# Migrate repos listed in config.yaml to git-ai async mode.
# Cleans up legacy hooks and configures note pushing.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG="$PROJECT_DIR/config.yaml"

if ! command -v git-ai &> /dev/null; then
    echo "Error: git-ai is not installed."
    echo "Install it from: https://github.com/git-ai-project/git-ai"
    exit 1
fi

if [ ! -f "$CONFIG" ]; then
    echo "Error: config.yaml not found at $CONFIG"
    exit 1
fi

# Parse repo paths from config.yaml (simple grep, avoids python dependency)
REPOS=$(grep 'path:' "$CONFIG" | sed 's/.*path:\s*//' | tr -d '"' | tr -d "'")

if [ -z "$REPOS" ]; then
    echo "No repos found in config.yaml"
    exit 1
fi

echo "Migrating repos to git-ai async mode..."
echo ""

for repo in $REPOS; do
    if [ ! -d "$repo/.git" ]; then
        echo "SKIP: $repo (not a git repo)"
        continue
    fi

    repo_name=$(basename "$repo")

    # Clean up legacy hooks if present
    if [ -f "$repo/.git/hooks/post-commit" ] && readlink "$repo/.git/hooks/post-commit" 2>/dev/null | grep -q "git-ai"; then
        echo "Cleaning legacy hooks on: $repo_name"
        (cd "$repo" && git-ai git-hooks remove 2>/dev/null) && echo "  Hooks removed" || echo "  FAILED to remove hooks"
    fi

    # Configure note pushing
    CURRENT_PUSH=$(cd "$repo" && git config --get-all remote.origin.push 2>/dev/null || true)
    if echo "$CURRENT_PUSH" | grep -q "refs/notes/ai"; then
        echo "  Note push already configured for $repo_name"
    else
        (cd "$repo" && git config --add remote.origin.push "+refs/notes/ai:refs/notes/ai")
        echo "  Note push configured for $repo_name"
    fi
done

echo ""
echo "Done. Verify with: git-ai status"
