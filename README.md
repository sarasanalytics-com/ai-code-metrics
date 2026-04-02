# AI Code Metrics Dashboard

Track AI vs Human code contributions across repos using open-source tools.

## What it measures

- **Contribution %** -- AI vs Human code over time (stacked area chart)
- **Agent DAU/WAU/MAU** -- Active developers per AI tool per day/week/month
- **Code Half-life** -- How long AI vs Human code survives before rewrite
- **Code Half-life by Agent** -- Durability broken down by Claude vs Windsurf vs Junie

## Architecture

```
git-ai (wrapper + daemon on each dev machine)
    -> collector (daily cron)
        -> PostgreSQL (metrics DB)
            -> Grafana (dashboards)

git-of-theseus -> weekly half-life analysis -> PostgreSQL
```

## Quick Start -- Add metrics to any repo

Add the reusable workflow call to your repo's existing pipeline (e.g., `main.yml`):

```yaml
  collect-metrics:
    if: github.ref == 'refs/heads/dev'
    uses: sarasanalytics-com/ai-code-metrics/.github/workflows/collect-metrics.yml@dev
    with:
      base_sha: ${{ github.event.before }}
      head_sha: ${{ github.sha }}
```

That's it. On every merge to `dev`, commit metrics are collected and uploaded as an artifact. No separate workflow file needed -- it shows as a single entry in the Actions tab under your existing pipeline.

For the full deployment guide, see [SOP.md](SOP.md).

## Developer Setup (one-time)

Install git-ai for line-level AI attribution. **No per-repo setup is needed** — git-ai v0.5+ uses a git wrapper + daemon that tracks attribution automatically across all repos.

```bash
# macOS / Linux / WSL
curl -sSL https://usegitai.com/install.sh | bash
```

```powershell
# Windows (PowerShell)
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm http://usegitai.com/install.ps1 | iex"
```

Close and reopen your terminal, then verify:

```bash
git-ai --version
git-ai status
```

### Migrating from legacy hooks

If you previously ran `git-ai install` in your repos, the old hooks are now inactive (deprecated in [git-ai PR #847](https://github.com/git-ai-project/git-ai/pull/847)). Clean them up:

```bash
# Option A: Use the setup script to clean all repos at once
./setup/dev_setup.sh ~/Work/iq-webapp ~/Work/webapp ~/Work/insights-webapp

# Option B: Manual cleanup per repo
cd ~/Work/iq-webapp && git-ai git-hooks remove
```

### Pushing git-ai notes

By default, `git push` does **not** push git-ai notes to the remote. To ensure CI can access attribution data:

```bash
git config --add remote.origin.push "+refs/notes/ai:refs/notes/ai"
```

Run this once per repo. The setup script handles this automatically when you pass repo paths.

## Prerequisites

- Python 3.10+
- PostgreSQL 14+ *(Phase 2 -- aggregation & dashboards)*
- [git-ai](https://github.com/git-ai-project/git-ai) installed on dev machines
- [git-of-theseus](https://github.com/erikbern/git-of-theseus) (`pip install git-of-theseus`) *(Phase 2)*
- Grafana *(Phase 2)*

## Project Structure

```
ai-code-metrics/
├── config.yaml                           # Repo list, DB connection, detection patterns
├── docker-compose.yml                    # Postgres + Grafana (local dev)
├── .github/workflows/
│   └── collect-metrics.yml               # Reusable workflow (called by other repos)
├── ci/
│   └── collect_on_merge.py               # CI-level commit classifier
├── collector/
│   ├── git_parser.py                     # Parses git log + git-ai notes
│   ├── metrics_aggregator.py             # Computes daily AI vs Human stats
│   ├── halflife_runner.py                # Wraps git-of-theseus with AI segmentation
│   └── db.py                             # PostgreSQL writes
├── setup/
│   ├── dev_setup.sh                      # Developer setup (macOS/Linux/WSL)
│   ├── dev_setup.ps1                     # Developer setup (Windows PowerShell)
│   └── schema.sql                        # Database schema
├── dashboards/
│   └── ai_metrics.json                   # Grafana dashboard (exportable)
├── scripts/
│   ├── run_daily.sh                      # Cron entry point (daily)
│   └── run_weekly_halflife.sh            # Cron entry point (weekly)
└── SOP.md                                # Full deployment SOP
```

## AI Commit Classification

Commits are classified using this priority order:

1. **git-ai notes** (most accurate) -- line-level attribution from git-ai wrapper/daemon
2. **Co-Authored-By trailer** -- `Co-Authored-By: Claude` (Claude Code), `Co-Authored-By: Junie` (IntelliJ), etc.
3. **Commit message patterns** -- Windsurf/Cursor/Junie/Gemini identifiable patterns
4. **Author email convention** -- Team-configured AI tool emails

Supported tools: **Claude, Windsurf, Cursor, Copilot, Junie, Gemini** -- extensible via `config.yaml`.

## License

Internal use only.
