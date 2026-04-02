# Standard Operating Procedure: AI Code Metrics — Organization-Wide Deployment

**Version:** 1.4
**Last Updated:** 2026-04-02
**Audience:** Engineering Managers, DevOps, Platform Teams, Individual Developers

---

## Table of Contents

1. [Purpose](#1-purpose)
2. [Scope](#2-scope)
3. [System Overview](#3-system-overview)
4. **Phase 1 — Start Collecting**
   - 4\. [Developer System Setup (Per Developer)](#4-developer-system-setup)
   - 5\. [GitHub-Level Setup (Per Repository)](#5-github-level-setup)
   - 6\. [How Commit Classification Works](#6-how-commit-classification-works)
   - 7\. [Roles & Responsibilities](#7-roles--responsibilities)
5. **Phase 2 — Aggregate & Visualize** *(work in progress)*
   - 8\. [Verification Checklist](#8-verification-checklist)
   - 9\. [Infrastructure Setup](#9-infrastructure-setup-wip) *(WIP)*
   - 10\. [Scheduled Jobs & Automation](#10-scheduled-jobs--automation-wip) *(WIP)*
   - 11\. [Dashboard & Visualization](#11-dashboard--visualization-wip) *(WIP)*
6. [Troubleshooting](#12-troubleshooting)
7. [Maintenance & Operations](#13-maintenance--operations)
8. [Security Considerations](#14-security-considerations)
9. [Appendices](#appendix-a--file-reference)

---

## 1. Purpose

This SOP defines the step-by-step process for deploying the **AI Code Metrics** system across an organization. The system measures:

- **AI vs Human contribution ratio** — What percentage of code is written with AI assistance?
- **Tool adoption** — Which AI tools (Claude, Windsurf, Cursor, Copilot, Junie, Gemini) are developers using?
- **Code durability (half-life)** — Does AI-written code survive, or get rewritten quickly?
- **Developer engagement** — DAU/WAU/MAU of AI tool usage across teams.

---

## 2. Scope

This SOP is **agnostic to**:

| Dimension | Coverage |
|-----------|----------|
| Programming language | Any — metrics are git-level (lines added/removed), not language-specific |
| Operating system | macOS, Linux, Windows (WSL2 or PowerShell) |
| IDE / Editor | VS Code, IntelliJ/JetBrains, Vim, terminal — all supported |
| Team / department | Any team with a git repository |
| Git hosting | GitHub (Actions workflow included), adaptable to GitLab/Bitbucket |
| AI tools tracked | Claude, Windsurf, Cursor, Copilot, Junie, Gemini — extensible via config |

---

## 3. System Overview

```
DEVELOPER MACHINES                    GITHUB (per repo)
┌──────────────────┐                  ┌───────────────────────────┐
│  git-ai wrapper  │                  │  GitHub Actions workflow   │
│  + daemon        │                  │  (runs on merge to dev)   │
│                  │                  │                           │
│  Tracks AI attri-│    git push      │  Classifies commits,      │
│  bution on each  │ ──────────────►  │  generates summary,       │
│  commit auto-    │                  │  uploads artifact         │
│  matically       │                  └───────────┬───────────────┘
└──────────────────┘                              │
                                                  ▼
COLLECTION SERVER                     ┌───────────────────────────┐
┌──────────────────┐                  │  metrics_output.json      │
│  Daily cron      │                  │  (per-merge artifact)     │
│  (2 AM)          │                  └───────────────────────────┘
│                  │
│  Weekly cron     │          ┌─────────────────────┐
│  (Sunday 4 AM)   │ ───────► │  PostgreSQL          │
│                  │          │  (3 tables)          │
└──────────────────┘          └──────────┬──────────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │  Grafana Dashboards  │
                              │  (6 panels)          │
                              └─────────────────────┘
```

**Two-phase rollout:**
- **Phase 1** (this SOP) gets data flowing immediately — developers install git-ai, repos get the GitHub workflow, commits start being classified.
- **Phase 2** aggregates that data into a database and dashboards for org-wide visibility.

---

# Phase 1 — Start Collecting

> Phase 1 gets attribution data attached to every commit and per-merge summaries generated in GitHub Actions. No infrastructure needed — just developer machines and GitHub.

---

## 4. Developer System Setup

**Owner:** Each individual developer
**Time:** 5 minutes
**Repository:** https://github.com/sarasanalytics-com/ai-code-metrics

### 4.1 What This Does

Installing `git-ai` on your machine enables **automatic, line-level attribution** of AI-assisted code. As of git-ai v0.5+, it uses a **git wrapper + daemon** that intercepts git commands globally — **no per-repo hook installation is needed**. Every commit you make in any repo will be silently annotated with which AI tool (if any) helped write the code.

> **Note for existing users:** If you previously ran `git-ai install` in your repos, those hooks are now deprecated and inactive ([git-ai PR #847](https://github.com/git-ai-project/git-ai/pull/847)). See [Section 4.4](#44-migrating-from-legacy-hooks) to clean them up.

### 4.2 Step 1 — Install git-ai

`git-ai` is an open-source CLI tool that tracks AI code contributions.

**macOS / Linux / WSL:**

```bash
curl -sSL https://usegitai.com/install.sh | bash
```

**Windows (PowerShell — run as Administrator):**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm http://usegitai.com/install.ps1 | iex"
```

After installation, **close and reopen your terminal** so the `git-ai` command is available in your PATH.

**Verify it installed correctly:**

```bash
git-ai --version
```

You should see a version number (e.g., `v0.5.0`). If you get `command not found`, see [Troubleshooting — git-ai installation fails](#git-ai-installation-fails).

### 4.3 Step 2 — Verify It's Working

Run this in any git repo:

```bash
cd ~/Work/iq-webapp
git-ai status
```

This confirms git-ai is active and tracking. **No `git-ai install` is needed** — the wrapper/daemon handles everything automatically.

**Quick verification across all repos:**

```bash
for repo in ~/Work/iq-webapp ~/Work/webapp ~/Work/insights-webapp; do
  echo "--- $repo ---"
  cd "$repo" && git-ai status
done
```

### 4.4 Migrating from Legacy Hooks

If you previously ran `git-ai install` in your repos (which installed `post-commit` hook symlinks), those hooks are now deprecated. They print a warning message and do nothing. Clean them up:

**Option A — Use the setup script (cleans all repos at once):**

```bash
git clone https://github.com/sarasanalytics-com/ai-code-metrics.git
cd ai-code-metrics
./setup/dev_setup.sh ~/Work/iq-webapp ~/Work/webapp ~/Work/insights-webapp
```

**Option B — Manual cleanup (per repo):**

```bash
cd ~/Work/iq-webapp && git-ai git-hooks remove
cd ~/Work/webapp && git-ai git-hooks remove
cd ~/Work/insights-webapp && git-ai git-hooks remove
```

### 4.5 Enable Note Pushing

By default, `git push` does **not** push git-ai notes to the remote. The GitHub Actions workflow fetches these notes for classification, so they must be available on the remote.

Run this once per repo:

```bash
git config --add remote.origin.push "+refs/notes/ai:refs/notes/ai"
```

After this, every `git push` will also push git-ai notes. Without this, tools that don't add Co-Authored-By trailers (like Gemini CLI) will be classified as "human" in CI even though git-ai detected them locally.

> The setup script handles this automatically when you pass repo paths.

### 4.6 What Changes for Developers?

**Nothing in your daily workflow changes.** git-ai runs silently via its git wrapper. The only visible differences:

- Commits made with **Claude Code** will include a `Co-Authored-By: Claude <noreply@anthropic.com>` trailer (Claude Code adds this automatically).
- Commits made with **Junie (IntelliJ)** will include a `Co-Authored-By: Junie <noreply@jetbrains.com>` trailer.
- **Gemini CLI** and some other tools do **not** add trailers — git-ai is the only way to detect them.
- git-ai will add notes to `refs/notes/ai` with line-level attribution data.
- Your commit messages, code, and workflow remain exactly the same.

### 4.7 Onboarding New Developers

Add this to your team's onboarding checklist:

> **AI Code Metrics Setup (5 min)**
>
> 1. Install git-ai: `curl -sSL https://usegitai.com/install.sh | bash`
> 2. Close and reopen your terminal
> 3. Verify: `git-ai --version`
> 4. Verify in a repo: `cd /path/to/repo && git-ai status`
> 5. Enable note pushing per repo: `git config --add remote.origin.push "+refs/notes/ai:refs/notes/ai"`
>
> Full instructions: https://github.com/sarasanalytics-com/ai-code-metrics/blob/dev/SOP.md#4-developer-system-setup

---

## 5. GitHub-Level Setup (Per Repository)

**Owner:** Repo owner or maintainer
**Time:** 5 minutes per repo
**One-time per repo**

### 5.1 Add the collect-metrics Job

Open your repo's existing CI workflow file (e.g., `.github/workflows/main.yml`). Add this job:

```yaml
  collect-metrics:
    if: github.ref == 'refs/heads/dev'
    uses: sarasanalytics-com/ai-code-metrics/.github/workflows/collect-metrics.yml@dev
    with:
      base_sha: ${{ github.event.before }}
      head_sha: ${{ github.sha }}
```

**Where to add it:**
- Add it as a new top-level job in your workflow, at the same level as `build`, `test`, etc.
- The `if: github.ref == 'refs/heads/dev'` ensures it only runs on merges to your protected branch. Change `dev` to `main` if your default branch is `main`.

### 5.2 What the Workflow Does

1. Checks out the repo with full history.
2. Fetches git-ai notes from the remote (if available).
3. Installs git-ai (for `git-ai stats` line-level data).
4. Downloads and runs `collect_on_merge.py` from this repo.
5. Classifies each commit as AI or human (with tool attribution).
6. Writes a `metrics_output.json` artifact and a GitHub Actions job summary.

### 5.3 Verify the Pipeline

After merging the workflow change:

1. Make a test commit and merge to `dev`.
2. Go to **Actions** tab → find the workflow run.
3. Check the **collect-metrics** job → it should show an "AI Code Metrics" summary.
4. Download the `ai-metrics-*` artifact to inspect the raw data.

---

## 6. How Commit Classification Works

Commits are classified using a priority-ordered fallback chain:

| Priority | Source | Accuracy | Coverage |
|----------|--------|----------|----------|
| 1 | **git-ai notes** (`refs/notes/ai`) | Line-level | Requires git-ai on dev machine |
| 2 | **Co-Authored-By trailers** | Commit-level | Claude Code, Junie add automatically |
| 3 | **Commit message patterns** | Commit-level | Windsurf, Cursor add identifiers |
| 4 | **Author email** | Commit-level | Requires team configuration |

**git-ai notes** (priority 1) provide the most accurate attribution — they record exactly which lines were AI-generated and by which tool/model. When git-ai is installed on the developer's machine, these notes are generated automatically on every commit via the git wrapper.

If git-ai notes are not available (e.g., developer doesn't have git-ai installed), the system falls back to parsing commit metadata.

---

## 7. Roles & Responsibilities

| Role | Responsibility |
|------|---------------|
| **Individual Developer** | Install git-ai (Section 4). Clean up legacy hooks if applicable. |
| **Repo Owner / Maintainer** | Add `collect-metrics` job to CI (Section 5). |
| **Engineering Manager** | Ensure team adoption. Review dashboards (Phase 2). |
| **Platform / DevOps** | Phase 2: Deploy PostgreSQL + Grafana + cron jobs. |

---

## 8. Verification Checklist

- [ ] `git-ai --version` returns a version number
- [ ] `git-ai status` works in at least one repo
- [ ] Legacy hooks cleaned up (no deprecation warnings on push)
- [ ] Note pushing configured: `git config --get-all remote.origin.push` shows `+refs/notes/ai:refs/notes/ai`
- [ ] `collect-metrics` job added to repo CI
- [ ] Test merge produces an `ai-metrics-*` artifact

---

## 9. Infrastructure Setup *(WIP)*

> This section is under development.

**Owner:** Platform / DevOps Team

### 9.1 Prerequisites

| Component | Version | Purpose |
|-----------|---------|--------|
| PostgreSQL | 14+ | Metrics storage |
| Python | 3.10+ | Collection scripts |
| Grafana | 10+ | Dashboards |
| Docker *(optional)* | 24+ | Local dev environment |

### 9.2 Database Setup

```bash
psql -h <host> -U postgres -c "CREATE DATABASE ai_code_metrics;"
psql -h <host> -U postgres -d ai_code_metrics -c "CREATE USER metrics WITH PASSWORD '<password>';"
psql -h <host> -U postgres -d ai_code_metrics -c "GRANT ALL PRIVILEGES ON DATABASE ai_code_metrics TO metrics;"
psql -h <host> -U metrics -d ai_code_metrics -f setup/schema.sql
```

### 9.3 Docker Compose (Local Development)

```bash
docker-compose up -d
```

This starts PostgreSQL (port 5432) and Grafana (port 3000) locally.

### 9.4 Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 9.5 Configure `config.yaml`

Update `config.yaml` with your repos and database connection:

```yaml
repos:
  - name: iq-webapp
    path: /opt/repos/iq-webapp
  - name: webapp
    path: /opt/repos/webapp

database:
  host: db-internal.example.com
  port: 5432
  name: ai_code_metrics
  user: metrics
  password: <use-env-var-in-production>
```

**Important:** For production, use environment variables for the database password instead of hardcoding it in the config file.

### 9.6 Test the Collector Manually

```bash
cd /opt/ai-code-metrics
python -m collector.metrics_aggregator --since 2026-02-25 --until 2026-03-03
```

Verify data reached the database:

```sql
SELECT date, repo, tool, lines_added, commits
FROM daily_contributions ORDER BY date DESC LIMIT 10;
```

---

## 10. Scheduled Jobs & Automation *(WIP)*

> This section is under development.

**Owner:** Platform / DevOps Team

### 10.1 Daily Collection (2 AM)

```bash
crontab -e
```

Add:

```
0 2 * * * /opt/ai-code-metrics/scripts/run_daily.sh
```

### 10.2 Weekly Half-Life Analysis (Sunday 4 AM)

```
0 4 * * 0 /opt/ai-code-metrics/scripts/run_weekly_halflife.sh
```

### 10.3 Keep Repo Clones Fresh

```
30 1 * * * cd /opt/repos/frontend-app && git fetch --all && git pull origin main
30 1 * * * cd /opt/repos/backend-api && git fetch --all && git pull origin main
```

---

## 11. Dashboard & Visualization *(WIP)*

> This section is under development.

**Owner:** Platform / DevOps Team

### 11.1 Start Grafana

```bash
docker-compose up -d grafana
# Access at http://localhost:3000 (admin/admin)
```

### 11.2 Add PostgreSQL Data Source

In Grafana: **Connections > Data sources > Add data source > PostgreSQL**

| Field | Value |
|-------|-------|
| Host | Your PostgreSQL host:port |
| Database | `ai_code_metrics` |
| User | `metrics` |
| Password | Your database password |
| TLS/SSL Mode | `require` (for production) |

### 11.3 Import the Dashboard

1. In Grafana: **Dashboards > New > Import**
2. Upload `dashboards/ai_metrics.json`
3. Select the PostgreSQL data source.
4. Click **Import**.

### 11.4 Dashboard Panels

| Panel | What it shows |
|-------|--------------|
| **Contribution % (AI vs Human)** | Stacked area chart of lines added by tool over time |
| **Agent DAU by Tool** | Daily active developers per AI tool |
| **Agent WAU by Tool** | Weekly active developers (7-day rolling window) |
| **Agent MAU by Tool** | Monthly active developers (30-day rolling window) |
| **AI Code Half-life** | Survival curves — what % of AI vs human code still exists after N days |
| **Half-life by Tool** | Durability broken down by Claude vs Windsurf vs Junie |

---

## 12. Troubleshooting

### git-ai installation fails

**Symptom:** `curl: (7) Failed to connect`

**Fix:**
1. Check internet/proxy settings.
2. Manually download from https://github.com/git-ai-project/git-ai
3. Place the binary in `$HOME/.local/bin/` (Linux/macOS) or add to PATH (Windows).

### Deprecation warning: "git core hooks feature has been sunset"

**Symptom:** On `git push`, you see:
```
git-ai: the git core hooks feature has been sunset.
To remove the deprecated git-ai hook symlinks from this repository, run:
  git-ai git-hooks remove
```

**Cause:** You have legacy git-ai hook symlinks from a previous installation. These hooks are now inactive and do nothing.

**Fix:** Run `git-ai git-hooks remove` in the affected repo, or use the setup script:
```bash
./setup/dev_setup.sh ~/Work/iq-webapp ~/Work/webapp
```

### Commits not classified as AI

**Diagnostic steps:**

```bash
# Check git-ai notes
git notes --ref=ai show <commit-sha>

# Check Co-Authored-By trailers
git log --format="%B" -1 <commit-sha> | grep -i "co-authored-by"

# Check commit message
git log --format="%s" -1 <commit-sha>
```

**Common causes:**
- git-ai not installed on the developer's machine — install it
- AI tool not configured to add trailers — check tool settings
- Detection patterns in `config.yaml` don't match your tool's output — update patterns

### GitHub Actions collect-metrics job fails

**Symptom:** The `collect-metrics` job fails in the pipeline.

**Fix:**
1. Verify the `ai-code-metrics` repo is accessible.
2. Check the `uses:` line — `sarasanalytics-com/ai-code-metrics/.github/workflows/collect-metrics.yml@dev` must be reachable.
3. Check the `if:` condition matches the correct branch ref.
4. If the "Download collector script" step fails, the raw GitHub URL may be temporarily unavailable — re-run the job.

### Database connection errors *(Phase 2)*

**Fix:**
1. Verify PostgreSQL is running: `pg_isready -h <host> -p 5432`
2. Test credentials: `psql -h <host> -U metrics -d ai_code_metrics -c "SELECT 1"`
3. Check firewall/security group rules.

### Grafana dashboard shows no data *(Phase 2)*

**Fix:**
1. Test data source in Grafana.
2. Verify data exists: `SELECT COUNT(*) FROM daily_contributions;`
3. Check the dashboard's time range.

---

## 13. Maintenance & Operations

### Log Management

| Log type | Location | Retention |
|----------|----------|-----------|
| Daily collection | `logs/daily_YYYYMMDD_HHMMSS.log` | Auto-cleaned after 30 days |
| Half-life analysis | `logs/halflife_YYYYMMDD_HHMMSS.log` | Auto-cleaned after 90 days |

### Adding a New Repository

1. Add the `collect-metrics` job to the repo's `main.yml` (see Section 5.1).
2. Have developers ensure git-ai is installed (Section 4).
3. *(Phase 2)* Clone the repo on the collection server, add to `config.yaml`.

### Adding a New AI Tool

1. Update `detection` section in `config.yaml` with the tool's Co-Authored-By patterns, commit message patterns, or author email.
2. Update `ci/collect_on_merge.py` `classify_commit()` if the tool uses unique trailer formats.
3. No other code changes needed — the tool will appear in dashboards automatically.

---

## 14. Security Considerations

| Concern | Mitigation |
|---------|------------|
| Database credentials in config | Use environment variables (`AI_METRICS_DB_PASSWORD`) instead of plaintext in `config.yaml`. |
| Grafana access | Require authentication. Use RBAC to restrict dashboard editing. |
| Data sensitivity | The system stores commit metadata (author, dates, line counts) — **not code content**. No source code is persisted in the database. |
| Tamper resistance | Co-Authored-By trailers are part of the commit SHA — modifying them changes the hash. git-ai notes provide additional verification. |
| Secret rotation | Rotate database passwords quarterly. |

---

## Appendix A — File Reference

| File | Purpose |
|------|---------|
| `config.yaml` | Central configuration: repos, database, detection patterns |
| `setup/schema.sql` | Database schema (3 tables + indexes) |
| `setup/dev_setup.sh` | Developer setup script (macOS/Linux/WSL) |
| `setup/dev_setup.ps1` | Developer setup script (Windows PowerShell) |
| `.github/workflows/collect-metrics.yml` | Reusable workflow (called by other repos) |
| `ci/collect_on_merge.py` | CI-level commit classifier |
| `collector/metrics_aggregator.py` | Daily metrics aggregation |
| `collector/halflife_runner.py` | Weekly code survival analysis |
| `collector/git_parser.py` | Git log parsing and commit classification |
| `collector/db.py` | PostgreSQL database operations |
| `scripts/run_daily.sh` | Cron entry point for daily collection |
| `scripts/run_weekly_halflife.sh` | Cron entry point for weekly analysis |
| `dashboards/ai_metrics.json` | Grafana dashboard (importable) |
| `docker-compose.yml` | Local dev environment (PostgreSQL + Grafana) |
| `requirements.txt` | Python dependencies |

## Appendix B — Quick Command Reference

```bash
# === PHASE 1: DEVELOPER SETUP ===
curl -sSL https://usegitai.com/install.sh | bash  # Step 1: Install git-ai
git-ai --version                                   # Verify git-ai installed
git-ai status                                      # Verify git-ai is active (run in any repo)
git-ai git-hooks remove                            # Clean up legacy hooks (if applicable)
git config --add remote.origin.push "+refs/notes/ai:refs/notes/ai"  # Enable note pushing

# === PHASE 2: COLLECTION (WIP) ===
psql -h <host> -U metrics -d ai_code_metrics -f setup/schema.sql   # Apply schema
pip install -r requirements.txt                                      # Install Python deps
python -m collector.metrics_aggregator                                # Daily collection
python -m collector.metrics_aggregator --since 2026-02-01             # Custom date range
python -m collector.halflife_runner                                   # Weekly half-life

# === LOGS ===
tail -20 logs/daily_*.log                    # Check daily collection logs
tail -20 logs/halflife_*.log                 # Check weekly analysis logs

# === CRON (Phase 2) ===
# Daily at 2 AM:      0 2 * * * /opt/ai-code-metrics/scripts/run_daily.sh
# Weekly Sunday 4 AM:  0 4 * * 0 /opt/ai-code-metrics/scripts/run_weekly_halflife.sh
```
