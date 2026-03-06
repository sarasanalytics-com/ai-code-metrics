#!/usr/bin/env bash
# =============================================================
# AI Code Metrics - Developer Setup
# =============================================================
# Run this script once to install git-ai hooks on your repos.
# It enables line-level tracking of AI vs Human code contributions.
#
# Usage:
#   ./dev_setup.sh                    # interactive - finds repos automatically
#   ./dev_setup.sh /path/to/repo1 /path/to/repo2  # explicit repo paths
#
# Prerequisites:
#   - git
#   - curl
# =============================================================
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

REPOS=(
  "iq-webapp"
  # Add more repo names here as needed
)

info()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# --- OS Detection ---
detect_platform() {
    case "$(uname -s)" in
        Darwin)  echo "macOS" ;;
        Linux)
            if grep -qiE '(microsoft|wsl)' /proc/version 2>/dev/null; then
                echo "WSL"
            else
                echo "Linux"
            fi
            ;;
        MINGW*|MSYS*|CYGWIN*)
            echo "Windows-GitBash"
            ;;
        *)       echo "Unknown" ;;
    esac
}

PLATFORM=$(detect_platform)

echo ""
echo "========================================="
echo "  AI Code Metrics - Developer Setup"
echo "========================================="
echo "  Platform detected: $PLATFORM"
echo "========================================="
echo ""

if [ "$PLATFORM" = "Windows-GitBash" ]; then
    error "This bash script is not supported on Windows outside of WSL."
    echo ""
    echo "Please use the PowerShell setup script instead:"
    echo "  .\\setup\\dev_setup.ps1"
    exit 1
fi

# --- Step 1: Check / Install git-ai ---
if command -v git-ai &> /dev/null; then
    info "git-ai is already installed ($(git-ai --version 2>/dev/null || echo 'version unknown'))"
else
    echo "git-ai is not installed. Attempting to install..."
    if command -v curl &> /dev/null; then
        curl -sSL https://usegitai.com/install.sh | bash
        # Reload PATH so git-ai is available in this session
        export PATH="$HOME/.local/bin:$HOME/.git-ai/bin:$PATH"
        if command -v git-ai &> /dev/null; then
            info "git-ai installed successfully"
        else
            error "git-ai installation failed. Please install manually:"
            echo "  curl -sSL https://usegitai.com/install.sh | bash"
            echo "  See: https://github.com/lgtm-ai/git-ai"
            exit 1
        fi
    else
        error "curl not found. Please install git-ai manually:"
        echo "  curl -sSL https://usegitai.com/install.sh | bash"
        echo "  See: https://github.com/lgtm-ai/git-ai"
        exit 1
    fi
fi

# --- Step 2: Find repos to set up ---
TARGET_REPOS=()

if [ $# -gt 0 ]; then
    # Repos passed as arguments
    for repo in "$@"; do
        if [ -d "$repo/.git" ]; then
            TARGET_REPOS+=("$repo")
        else
            warn "Skipping $repo (not a git repo)"
        fi
    done
else
    # Auto-detect: look for known repos in common locations
    SEARCH_DIRS=("$HOME/Work" "$HOME/work" "$HOME/projects" "$HOME/code" "$HOME/src" "$(pwd)/..")

    echo "Searching for repos: ${REPOS[*]}"
    echo ""

    for dir in "${SEARCH_DIRS[@]}"; do
        [ ! -d "$dir" ] && continue
        for repo_name in "${REPOS[@]}"; do
            repo_path="$dir/$repo_name"
            if [ -d "$repo_path/.git" ]; then
                TARGET_REPOS+=("$repo_path")
            fi
        done
    done

    if [ ${#TARGET_REPOS[@]} -eq 0 ]; then
        warn "No repos found automatically."
        echo ""
        echo "Please run with explicit paths:"
        echo "  ./dev_setup.sh /path/to/iq-webapp /path/to/other-repo"
        exit 1
    fi

    echo "Found the following repos:"
    for repo in "${TARGET_REPOS[@]}"; do
        echo "  - $repo"
    done
    echo ""
    read -p "Install git-ai hooks on these repos? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
fi

# --- Step 3: Install git-ai hooks ---
echo ""
INSTALLED=0
FAILED=0

for repo in "${TARGET_REPOS[@]}"; do
    repo_name=$(basename "$repo")
    echo -n "Installing git-ai on $repo_name... "
    if (cd "$repo" && git-ai install 2>/dev/null); then
        # Configure git to push ai notes alongside code so CI can read them
        (cd "$repo" && git config remote.origin.push "+refs/notes/ai:refs/notes/ai")
        info "done"
        ((INSTALLED++))
    else
        error "failed"
        ((FAILED++))
    fi
done

# --- Summary ---
echo ""
echo "========================================="
echo "  Setup Complete"
echo "========================================="
echo "  Installed: $INSTALLED repo(s)"
if [ $FAILED -gt 0 ]; then
    echo "  Failed:    $FAILED repo(s)"
fi
echo ""
echo "From now on, your commits will be tagged"
echo "with AI attribution data automatically."
echo ""
echo "To verify, run in any repo:"
echo "  git-ai status"
echo "========================================="
