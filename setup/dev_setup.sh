#!/usr/bin/env bash
# =============================================================
# AI Code Metrics - Developer Setup
# =============================================================
# Run this script once to install git-ai on your machine.
# It enables line-level tracking of AI vs Human code contributions.
#
# As of git-ai v0.5+, NO per-repo hook installation is needed.
# git-ai uses a git wrapper + daemon that tracks attribution
# automatically across all repos.
#
# Usage:
#   ./dev_setup.sh                                # install + verify
#   ./dev_setup.sh /path/to/repo1 /path/to/repo2  # also clean legacy hooks
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
            echo "  See: https://github.com/git-ai-project/git-ai"
            exit 1
        fi
    else
        error "curl not found. Please install git-ai manually:"
        echo "  curl -sSL https://usegitai.com/install.sh | bash"
        echo "  See: https://github.com/git-ai-project/git-ai"
        exit 1
    fi
fi

# --- Step 2: Verify git-ai is working ---
echo ""
echo "Verifying git-ai setup..."

# Check that git-ai status works (confirms wrapper/daemon mode is active)
if git-ai status &>/dev/null; then
    info "git-ai is active and tracking"
else
    warn "git-ai status check returned an error. This may be normal if not inside a git repo."
    echo "  Try running 'git-ai status' inside one of your repos to verify."
fi

# --- Step 3: Clean up legacy hooks (if repos provided) ---
if [ $# -gt 0 ]; then
    echo ""
    echo "Cleaning up legacy git-ai hooks from specified repos..."
    echo "(git-ai no longer uses per-repo hooks — the wrapper handles everything)"
    echo ""

    CLEANED=0
    SKIPPED=0

    for repo in "$@"; do
        if [ ! -d "$repo/.git" ]; then
            warn "Skipping $repo (not a git repo)"
            ((SKIPPED++))
            continue
        fi

        repo_name=$(basename "$repo")
        echo -n "Checking $repo_name for legacy hooks... "

        # Check if legacy git-ai hook symlinks exist
        if [ -f "$repo/.git/hooks/post-commit" ] && readlink "$repo/.git/hooks/post-commit" 2>/dev/null | grep -q "git-ai"; then
            # Remove legacy hooks using git-ai's built-in cleanup
            if (cd "$repo" && git-ai git-hooks remove 2>/dev/null); then
                info "cleaned up legacy hooks"
                ((CLEANED++))
            else
                warn "could not clean hooks (try manually: cd $repo && git-ai git-hooks remove)"
            fi
        else
            info "no legacy hooks found"
        fi
    done

    echo ""
    if [ $CLEANED -gt 0 ]; then
        info "Cleaned legacy hooks from $CLEANED repo(s)"
    fi
fi

# --- Step 4: Configure note pushing (for repos provided) ---
if [ $# -gt 0 ]; then
    echo ""
    echo "Configuring git-ai note pushing on repos..."
    echo ""

    for repo in "$@"; do
        if [ ! -d "$repo/.git" ]; then
            continue
        fi

        repo_name=$(basename "$repo")
        echo -n "Configuring note push for $repo_name... "

        # Ensure git-ai notes are pushed automatically
        CURRENT_PUSH=$(cd "$repo" && git config --get-all remote.origin.push 2>/dev/null || true)
        if echo "$CURRENT_PUSH" | grep -q "refs/notes/ai"; then
            info "already configured"
        else
            (cd "$repo" && git config --add remote.origin.push "+refs/notes/ai:refs/notes/ai")
            info "done"
        fi
    done
fi

# --- Summary ---
echo ""
echo "========================================="
echo "  Setup Complete"
echo "========================================="
echo ""
echo "  git-ai is installed and active."
echo "  No per-repo setup is needed anymore."
echo "  Just commit as normal — git-ai tracks"
echo "  AI attribution automatically via its"
echo "  git wrapper."
echo ""
echo "  To verify in any repo:"
echo "    git-ai status"
echo ""
if [ $# -eq 0 ]; then
    echo "  To clean legacy hooks from repos, re-run:"
    echo "    ./dev_setup.sh ~/Work/repo1 ~/Work/repo2"
    echo ""
fi
echo "========================================="
