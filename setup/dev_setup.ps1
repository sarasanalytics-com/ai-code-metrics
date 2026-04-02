# =============================================================
# AI Code Metrics - Developer Setup (Windows PowerShell)
# =============================================================
# Run this script once to install git-ai on your machine.
# It enables line-level tracking of AI vs Human code contributions.
#
# As of git-ai v0.5+, NO per-repo hook installation is needed.
# git-ai uses a git wrapper + daemon that tracks attribution
# automatically across all repos.
#
# Usage:
#   .\dev_setup.ps1                              # install + verify
#   .\dev_setup.ps1 C:\Users\you\Work\repo1      # also clean legacy hooks
#
# Prerequisites:
#   - git
#   - PowerShell 5.1+
# =============================================================

$ErrorActionPreference = "Stop"

function Write-OK($msg)    { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg)  { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg)   { Write-Host "[ERROR] $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "========================================="
Write-Host "  AI Code Metrics - Developer Setup"
Write-Host "  Platform detected: Windows (PowerShell)"
Write-Host "========================================="
Write-Host ""

# --- Step 1: Check / Install git-ai ---
$gitAiCmd = Get-Command git-ai -ErrorAction SilentlyContinue
if ($gitAiCmd) {
    $version = try { & git-ai --version 2>$null } catch { "version unknown" }
    Write-OK "git-ai is already installed ($version)"
} else {
    Write-Host "git-ai is not installed. Attempting to install..."
    try {
        Invoke-Expression (Invoke-RestMethod http://usegitai.com/install.ps1)
        # Refresh PATH for current session
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "Machine")
        $gitAiCmd = Get-Command git-ai -ErrorAction SilentlyContinue
        if ($gitAiCmd) {
            Write-OK "git-ai installed successfully"
        } else {
            Write-Err "git-ai installation failed. Please install manually:"
            Write-Host '  powershell -NoProfile -ExecutionPolicy Bypass -Command "irm http://usegitai.com/install.ps1 | iex"'
            Write-Host "  See: https://github.com/git-ai-project/git-ai"
            exit 1
        }
    } catch {
        Write-Err "git-ai installation failed: $_"
        Write-Host '  powershell -NoProfile -ExecutionPolicy Bypass -Command "irm http://usegitai.com/install.ps1 | iex"'
        Write-Host "  See: https://github.com/git-ai-project/git-ai"
        exit 1
    }
}

# --- Step 2: Verify git-ai is working ---
Write-Host ""
Write-Host "Verifying git-ai setup..."

try {
    & git-ai status 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-OK "git-ai is active and tracking"
    } else {
        Write-Warn "git-ai status check returned an error. This may be normal if not inside a git repo."
        Write-Host "  Try running 'git-ai status' inside one of your repos to verify."
    }
} catch {
    Write-Warn "Could not run git-ai status. Try running it manually inside a git repo."
}

# --- Step 3: Clean up legacy hooks (if repos provided) ---
if ($args.Count -gt 0) {
    Write-Host ""
    Write-Host "Cleaning up legacy git-ai hooks from specified repos..."
    Write-Host "(git-ai no longer uses per-repo hooks - the wrapper handles everything)"
    Write-Host ""

    $Cleaned = 0
    $Skipped = 0

    foreach ($repo in $args) {
        if (-not (Test-Path (Join-Path $repo ".git"))) {
            Write-Warn "Skipping $repo (not a git repo)"
            $Skipped++
            continue
        }

        $repoName = Split-Path $repo -Leaf
        Write-Host -NoNewline "Checking $repoName for legacy hooks... "

        $hookPath = Join-Path $repo ".git" "hooks" "post-commit"
        $hasLegacyHook = $false
        if (Test-Path $hookPath) {
            $target = try { (Get-Item $hookPath).Target } catch { $null }
            if ($target -and $target -match "git-ai") {
                $hasLegacyHook = $true
            }
        }

        if ($hasLegacyHook) {
            try {
                Push-Location $repo
                & git-ai git-hooks remove 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-OK "cleaned up legacy hooks"
                    $Cleaned++
                } else {
                    Write-Warn "could not clean hooks (try manually: cd $repo; git-ai git-hooks remove)"
                }
            } catch {
                Write-Warn "could not clean hooks: $_"
            } finally {
                Pop-Location
            }
        } else {
            Write-OK "no legacy hooks found"
        }
    }

    if ($Cleaned -gt 0) {
        Write-Host ""
        Write-OK "Cleaned legacy hooks from $Cleaned repo(s)"
    }
}

# --- Step 4: Configure note pushing (for repos provided) ---
if ($args.Count -gt 0) {
    Write-Host ""
    Write-Host "Configuring git-ai note pushing on repos..."
    Write-Host ""

    foreach ($repo in $args) {
        if (-not (Test-Path (Join-Path $repo ".git"))) {
            continue
        }

        $repoName = Split-Path $repo -Leaf
        Write-Host -NoNewline "Configuring note push for $repoName... "

        try {
            Push-Location $repo
            $currentPush = & git config --get-all remote.origin.push 2>$null
            if ($currentPush -match "refs/notes/ai") {
                Write-OK "already configured"
            } else {
                & git config --add remote.origin.push "+refs/notes/ai:refs/notes/ai"
                Write-OK "done"
            }
        } catch {
            Write-Warn "could not configure: $_"
        } finally {
            Pop-Location
        }
    }
}

# --- Summary ---
Write-Host ""
Write-Host "========================================="
Write-Host "  Setup Complete"
Write-Host "========================================="
Write-Host ""
Write-Host "  git-ai is installed and active."
Write-Host "  No per-repo setup is needed anymore."
Write-Host "  Just commit as normal - git-ai tracks"
Write-Host "  AI attribution automatically via its"
Write-Host "  git wrapper."
Write-Host ""
Write-Host "  To verify in any repo:"
Write-Host "    git-ai status"
Write-Host ""
if ($args.Count -eq 0) {
    Write-Host "  To clean legacy hooks from repos, re-run:"
    Write-Host '    .\dev_setup.ps1 "C:\Users\you\Work\repo1"'
    Write-Host ""
}
Write-Host "========================================="
