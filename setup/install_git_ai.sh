#!/usr/bin/env bash
# Install git-ai hooks on all repos listed in config.yaml
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG="$PROJECT_DIR/config.yaml"

if ! command -v git-ai &> /dev/null; then
    echo "Error: git-ai is not installed."
    echo "Install it from: https://github.com/lgtm-ai/git-ai"
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

echo "Installing git-ai hooks on repos..."
echo ""

for repo in $REPOS; do
    if [ ! -d "$repo/.git" ]; then
        echo "SKIP: $repo (not a git repo)"
        continue
    fi

    echo "Installing git-ai on: $repo"
    (cd "$repo" && git-ai install) && echo "  OK" || echo "  FAILED"
done

echo ""
echo "Done. Verify with: git-ai status"
