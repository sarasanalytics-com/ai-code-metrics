# =============================================================
# AI Code Metrics - Developer Setup (Windows PowerShell)
# =============================================================
# Run this script once to install git-ai hooks on your repos.
# It enables line-level tracking of AI vs Human code contributions.
#
# Usage:
#   .\dev_setup.ps1                              # interactive - finds repos automatically
#   .\dev_setup.ps1 C:\Users\you\Work\repo1      # explicit repo paths
#
# Prerequisites:
#   - git
#   - PowerShell 5.1+
# =============================================================

$ErrorActionPreference = "Stop"

$Repos = @(
    "iq-webapp"
    # Add more repo names here as needed
)

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
            Write-Host "  See: https://github.com/lgtm-ai/git-ai"
            exit 1
        }
    } catch {
        Write-Err "git-ai installation failed: $_"
        Write-Host '  powershell -NoProfile -ExecutionPolicy Bypass -Command "irm http://usegitai.com/install.ps1 | iex"'
        Write-Host "  See: https://github.com/lgtm-ai/git-ai"
        exit 1
    }
}

# --- Step 2: Find repos to set up ---
$TargetRepos = @()

if ($args.Count -gt 0) {
    # Repos passed as arguments
    foreach ($repo in $args) {
        if (Test-Path (Join-Path $repo ".git")) {
            $TargetRepos += $repo
        } else {
            Write-Warn "Skipping $repo (not a git repo)"
        }
    }
} else {
    # Auto-detect: look for known repos in common locations
    $SearchDirs = @(
        (Join-Path $HOME "Work"),
        (Join-Path $HOME "work"),
        (Join-Path $HOME "projects"),
        (Join-Path $HOME "code"),
        (Join-Path $HOME "src"),
        (Split-Path (Get-Location) -Parent)
    )

    Write-Host "Searching for repos: $($Repos -join ', ')"
    Write-Host ""

    foreach ($dir in $SearchDirs) {
        if (-not (Test-Path $dir)) { continue }
        foreach ($repoName in $Repos) {
            $repoPath = Join-Path $dir $repoName
            if (Test-Path (Join-Path $repoPath ".git")) {
                $TargetRepos += $repoPath
            }
        }
    }

    if ($TargetRepos.Count -eq 0) {
        Write-Warn "No repos found automatically."
        Write-Host ""
        Write-Host "Please run with explicit paths:"
        Write-Host "  .\dev_setup.ps1 C:\Users\you\Work\iq-webapp"
        exit 1
    }

    Write-Host "Found the following repos:"
    foreach ($repo in $TargetRepos) {
        Write-Host "  - $repo"
    }
    Write-Host ""
    $confirm = Read-Host "Install git-ai hooks on these repos? (y/n)"
    if ($confirm -notmatch '^[Yy]$') {
        Write-Host "Aborted."
        exit 0
    }
}

# --- Step 3: Install git-ai hooks ---
Write-Host ""
$Installed = 0
$Failed = 0

foreach ($repo in $TargetRepos) {
    $repoName = Split-Path $repo -Leaf
    Write-Host -NoNewline "Installing git-ai on $repoName... "
    try {
        Push-Location $repo
        & git-ai install 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-OK "done"
            $Installed++
        } else {
            Write-Err "failed"
            $Failed++
        }
    } catch {
        Write-Err "failed"
        $Failed++
    } finally {
        Pop-Location
    }
}

# --- Summary ---
Write-Host ""
Write-Host "========================================="
Write-Host "  Setup Complete"
Write-Host "========================================="
Write-Host "  Installed: $Installed repo(s)"
if ($Failed -gt 0) {
    Write-Host "  Failed:    $Failed repo(s)"
}
Write-Host ""
Write-Host "From now on, your commits will be tagged"
Write-Host "with AI attribution data automatically."
Write-Host ""
Write-Host "To verify, run in any repo:"
Write-Host "  git-ai status"
Write-Host "========================================="
