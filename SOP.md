# Standard Operating Procedure: AI Code Metrics — Organization-Wide Deployment

**Version:** 1.2
**Last Updated:** 2026-03-04
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
- **Tool adoption** — Which AI tools (Claude, Windsurf, Cursor, Copilot, Junie) are developers using?
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
| AI tools tracked | Claude, Windsurf, Cursor, Copilot, Junie — extensible via config |

---

## 3. System Overview

```
DEVELOPER MACHINES                    GITHUB (per repo)
┌──────────────────┐                  ┌───────────────────────────┐
│  git-ai hooks    │                  │  GitHub Actions workflow   │
│  (post-commit)   │                  │  (runs on merge to dev)   │
│                  │                  │                           │
│  Adds AI attri-  │    git push      │  Classifies commits,      │
│  bution to each  │ ──────────────►  │  generates summary,       │
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
- **Phase 1** (this SOP) gets data flowing immediately — developers install hooks, repos get the GitHub workflow, commits start being classified.
- **Phase 2** aggregates that data into a database and dashboards for org-wide visibility.

---

# Phase 1 — Start Collecting

> Phase 1 gets attribution data attached to every commit and per-merge summaries generated in GitHub Actions. No infrastructure needed — just developer machines and GitHub.

---

## 4. Developer System Setup

**Owner:** Each individual developer
**Time:** 5 minutes

### 4.1 What This Does

Installing `git-ai` hooks on your machine enables **automatic, line-level attribution** of AI-assisted code. Every commit you make will be silently annotated with which AI tool (if any) helped write the code. No manual action is needed after setup.

### 4.2 macOS / Linux / WSL

```bash
# Option A: Interactive (auto-discovers repos)
./setup/dev_setup.sh

# Option B: Explicit repos
./setup/dev_setup.sh /path/to/repo1 /path/to/repo2 /path/to/repo3
```

**What happens:**
1. Checks if `git-ai` CLI is installed; installs it if missing.
2. Runs `git-ai install` in each repo to set up post-commit hooks.
3. Prints a summary of installed repos.

### 4.3 Windows (PowerShell)

```powershell
# Option A: Interactive
.\setup\dev_setup.ps1

# Option B: Explicit repos
.\setup\dev_setup.ps1 "C:\Users\you\Work\repo1" "C:\Users\you\Work\repo2"
```

**Note:** Windows GitBash is **not supported** — use WSL2 or PowerShell.

### 4.4 Verify Installation

In any repo where git-ai was installed:

```bash
git-ai status
```

Expected output confirms git-ai is active with hooks installed.

### 4.5 What Changes for Developers?

**Nothing in your daily workflow changes.** git-ai runs silently as a post-commit hook. The only visible differences:

- Commits made with **Claude Code** will include a `Co-Authored-By: Claude <noreply@anthropic.com>` trailer (Claude Code adds this automatically).
- Commits made with **Junie (IntelliJ)** will include a `Co-Authored-By: Junie <noreply@jetbrains.com>` trailer.
- git-ai will add notes to `refs/notes/git-ai` with line-level attribution data.
- Your commit messages, code, and workflow remain exactly the same.

### 4.6 Onboarding New Developers

Add this to your team's onboarding checklist:

> **AI Code Metrics Setup (5 min)**
> Run the developer setup script to enable AI code attribution:
> - macOS/Linux: `./setup/dev_setup.sh /path/to/your-repos`
> - Windows: `.\setup\dev_setup.ps1 "C:\path\to\your-repos"`
> Verify with `git-ai status` in any repo.

---

## 5. GitHub-Level Setup

**Owner:** Repo Owner / Tech Lead (per repository)
**Time:** 5 minutes per repo

### 5.1 Add the Reusable Workflow Call

This project provides a **reusable workflow** at `.github/workflows/collect-metrics.yml`. Instead of copying a standalone workflow file into each repo, you add a single job to the repo's existing pipeline (e.g., `main.yml`).

Open the repo's `.github/workflows/main.yml` and add the `collect-metrics` job:

```yaml
jobs:
  # ... your existing jobs (e.g., Daton, build, deploy) ...

  collect-metrics:
    if: github.ref == 'refs/heads/dev'    # Change to your integration branch
    uses: sarasanalytics-com/ai-code-metrics/.github/workflows/collect-metrics.yml@dev
    with:
      base_sha: ${{ github.event.before }}
      head_sha: ${{ github.sha }}
```

**That's it.** No separate workflow file needed. No GitHub secrets required (the `ai-code-metrics` repo is public).

### 5.2 How It Works

- The `collect-metrics` job calls the reusable workflow hosted in the `ai-code-metrics` repo.
- The reusable workflow checks out the repo, installs git-ai, downloads the collector script, classifies commits, and uploads the metrics as an artifact.
- It runs as part of your existing pipeline — **one workflow entry** in the Actions tab, not two.

### 5.3 Configure the Trigger Branch

The `if:` condition controls which branch triggers metrics collection. Adjust it to match your integration branch:

```yaml
  collect-metrics:
    if: github.ref == 'refs/heads/dev'       # or 'refs/heads/main', etc.
```

**Rationale:** Code should be counted once — when it merges into the integration branch. Do not trigger on promotion branches (staging, production) to avoid double-counting.

### 5.4 Commit and Push

```bash
git add .github/workflows/main.yml
git commit -m "Add AI Code Metrics collection to pipeline"
git push origin main
```

### 5.5 Verify

1. Create a branch, make some commits, merge to your trigger branch (e.g., `dev`).
2. Go to the repo's **Actions** tab on GitHub.
3. Confirm the pipeline ran with the `collect-metrics` job visible.
4. Check the workflow run for:
   - A job summary with the AI contribution breakdown.
   - An uploaded artifact named `ai-metrics-<sha>`.

### 5.6 Adding Custom Logic Per Repo

Since the reusable workflow is a job in your `main.yml`, you can add repo-specific logic around it:

```yaml
  collect-metrics:
    if: github.ref == 'refs/heads/dev'
    needs: [build]                           # Wait for build to pass first
    uses: sarasanalytics-com/ai-code-metrics/.github/workflows/collect-metrics.yml@dev
    with:
      base_sha: ${{ github.event.before }}
      head_sha: ${{ github.sha }}

  notify-metrics:                            # Custom post-metrics job
    needs: [collect-metrics]
    runs-on: ubuntu-latest
    steps:
      - run: echo "Metrics collected successfully"
```

---

## 6. How Commit Classification Works

Every commit is classified into a tool category using this **priority order**:

```
Priority 1 (highest): git-ai notes
    |  not found
Priority 2: Co-Authored-By trailers
    |  not found
Priority 3: Commit message patterns
    |  not found
Priority 4: Author email patterns
    |  not found
Default: "human"
```

### Priority 1 — git-ai Notes (Most Accurate)

If the developer has `git-ai` installed (Section 4), each commit gets a git note at `refs/notes/git-ai` with line-level attribution. The collector parses these notes to determine the tool.

### Priority 2 — Co-Authored-By Trailers

If git-ai notes are unavailable, the system checks for trailers in the commit message body:

```
Co-Authored-By: Claude <noreply@anthropic.com>     -> claude
Co-Authored-By: Windsurf <noreply@codeium.com>     -> windsurf
Co-Authored-By: Junie <noreply@jetbrains.com>      -> junie
Co-Authored-By: Cursor <noreply@cursor.com>        -> cursor
```

These trailers are **tamper-resistant** — they are part of the commit SHA. Changing them changes the commit hash.

### Priority 3 — Commit Message Patterns

Regex patterns defined in `config.yaml` under `detection.commit_message`:

```
"Generated by Windsurf"    -> windsurf
"[Windsurf]"               -> windsurf
"Generated by Cursor"      -> cursor
"Generated by Junie"       -> junie
```

### Priority 4 — Author Email

If your organization configures AI tools to use dedicated email addresses, these can be matched via `detection.author_email` in `config.yaml`.

### Default — Human

If no patterns match, the commit is classified as `human`.

### Supported Tools

| Tool | Detection methods |
|------|------------------|
| **Claude** (Claude Code) | git-ai notes, `Co-Authored-By: Claude`, `Co-Authored-By: ...anthropic...` |
| **Windsurf** | git-ai notes, `Co-Authored-By: Windsurf`, `Co-Authored-By: ...Codeium...`, commit message patterns |
| **Cursor** | git-ai notes, `Co-Authored-By: Cursor`, commit message patterns |
| **Copilot** | git-ai notes, `Co-Authored-By: Copilot` |
| **Junie** (IntelliJ/JetBrains) | git-ai notes, `Co-Authored-By: Junie`, `Co-Authored-By: ...jetbrains...`, commit message patterns |

To add a new tool, update the `detection` section in `config.yaml`. No code changes needed.

---

## 7. Roles & Responsibilities

| Role | Phase 1 (now) | Phase 2 (later) |
|------|--------------|-----------------|
| **Individual Developer** | Run `dev_setup.sh` once to install git-ai hooks | Nothing — data flows automatically |
| **Repo Owner / Tech Lead** | Add GitHub Actions workflow to each repo | Nothing — already set up |
| **Platform / DevOps Team** | Nothing | Provision PostgreSQL, deploy collector, set up cron, configure Grafana |
| **Engineering Manager** | Define which repos to track | Review dashboards, set adoption targets |

---

# Phase 2 — Aggregate & Visualize

> Phase 2 takes the per-commit attribution data from Phase 1 and aggregates it into a database with dashboards for org-wide visibility. **This phase is a work in progress.**

---

## 8. Verification Checklist

Use this checklist when rolling out to a new team or repo.

### Phase 1 — Developer & GitHub (do this now)

**Per developer:**

- [ ] `git-ai` is installed: `git-ai --version`
- [ ] Hooks are active in each repo: `git-ai status`
- [ ] Test commit with an AI tool shows correct `Co-Authored-By` trailer

**Per repo:**

- [ ] `collect-metrics` job added to the repo's `main.yml` (calls the reusable workflow)
- [ ] `if:` condition matches the repo's integration branch (e.g., `refs/heads/dev`)
- [ ] A test merge triggers the pipeline and the `collect-metrics` job runs
- [ ] An artifact named `ai-metrics-<sha>` is uploaded
- [ ] Job summary shows correct AI vs Human breakdown

### Phase 2 — Infrastructure & Dashboards *(WIP)*

**Infrastructure:**

- [ ] PostgreSQL is running and accessible from the collection server
- [ ] Schema applied (3 tables created)
- [ ] `config.yaml` lists all repos with correct paths
- [ ] Collector runs successfully: `python -m collector.metrics_aggregator`
- [ ] Data appears in database

**Scheduled jobs:**

- [ ] Daily cron runs at 2 AM: check `logs/daily_*.log`
- [ ] Weekly cron runs Sunday 4 AM: check `logs/halflife_*.log`
- [ ] Repo clones are refreshed before collection runs

**Dashboards:**

- [ ] Grafana data source connects to PostgreSQL
- [ ] Dashboard imported and shows data
- [ ] Date range includes recent data
- [ ] All panels render without query errors

---

## 9. Infrastructure Setup *(WIP)*

> This section is under development. The steps below outline the planned approach.

**Owner:** Platform / DevOps Team

### 9.1 Prerequisites

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.10+ | Collector scripts |
| PostgreSQL | 14+ | Metrics storage |
| Grafana | 11.0+ | Visualization |
| git | 2.20+ | Repository access |
| git-of-theseus | 0.3.4+ | Code survival analysis |

### 9.2 Provision the Database

**Option A — Cloud (recommended for production):**
Create a PostgreSQL 14+ instance on your cloud provider (AWS RDS, Azure Database, GCP Cloud SQL). Create a database named `ai_code_metrics` and a user `metrics` with write permissions.

**Option B — Docker (local/dev):**

```bash
docker-compose up -d postgres
```

This starts PostgreSQL 16-Alpine on `localhost:5432` with database `ai_code_metrics`, user `metrics`, password `metrics`.

### 9.3 Apply the Schema

```bash
psql -h <host> -U metrics -d ai_code_metrics -f setup/schema.sql
```

This creates three tables:

| Table | Purpose | Key columns |
|-------|---------|-------------|
| `daily_contributions` | Daily aggregated metrics | `date, repo, tool, lines_added, lines_removed, commits` |
| `daily_active_users` | Per-developer activity | `date, repo, tool, author, commits` |
| `code_halflife` | Weekly survival snapshots | `snapshot_date, repo, origin, cohort_date, survival_pct` |

### 9.4 Clone the Collector Repo

On the server that will run scheduled jobs:

```bash
git clone https://github.com/sarasanalytics-com/ai-code-metrics.git /opt/ai-code-metrics
cd /opt/ai-code-metrics
pip install -r requirements.txt
```

### 9.5 Configure `config.yaml`

```yaml
repos:
  - name: frontend-app
    path: /opt/repos/frontend-app
  - name: backend-api
    path: /opt/repos/backend-api
  # Add all repos across all teams

database:
  host: prod-postgres.internal.example.com
  port: 5432
  name: ai_code_metrics
  user: metrics
  password: <use-env-var-in-production>

collection:
  lookback_days: 7
  default_branch: main

halflife:
  schedule: weekly
  min_cohort_size: 50

detection:
  co_authored_by:
    claude:
      - "Claude"
      - "anthropic"
    windsurf:
      - "Windsurf"
      - "Codeium"
    cursor:
      - "Cursor"
    copilot:
      - "Copilot"
    junie:
      - "Junie"
      - "jetbrains"
      - "JetBrains"

  commit_message:
    windsurf:
      - "Generated by Windsurf"
      - "\\[Windsurf\\]"
    cursor:
      - "Generated by Cursor"
    junie:
      - "Generated by Junie"
      - "\\[Junie\\]"

  author_email:
    # If your org configures AI tools to use specific bot emails:
    # claude:
    #   - "claude-bot@yourcompany.com"
    # junie:
    #   - "junie-bot@yourcompany.com"
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

The daily collector scans all configured repos, classifies commits from the last N days, and writes aggregated metrics into PostgreSQL.

**Set up the cron job:**

```bash
crontab -e
```

Add:

```
0 2 * * * /opt/ai-code-metrics/scripts/run_daily.sh
```

**What `run_daily.sh` does:**
1. Creates `logs/` directory if missing.
2. Runs `python -m collector.metrics_aggregator`.
3. Logs output to `logs/daily_YYYYMMDD_HHMMSS.log`.
4. Auto-deletes logs older than 30 days.

### 10.2 Weekly Half-Life Analysis (Sunday 4 AM)

The weekly job runs `git-of-theseus` survival analysis to measure how long AI vs human code persists over time.

```
0 4 * * 0 /opt/ai-code-metrics/scripts/run_weekly_halflife.sh
```

**What `run_weekly_halflife.sh` does:**
1. Runs `python -m collector.halflife_runner`.
2. Logs output to `logs/halflife_YYYYMMDD_HHMMSS.log`.
3. Auto-deletes logs older than 90 days.

### 10.3 Keep Repo Clones Fresh

The collectors need local git clones of every tracked repo. Set up a cron to sync them **before** the 2 AM collection:

```
30 1 * * * cd /opt/repos/frontend-app && git fetch --all && git pull origin main
30 1 * * * cd /opt/repos/backend-api && git fetch --all && git pull origin main
```

---

## 11. Dashboard & Visualization *(WIP)*

> This section is under development.

**Owner:** Platform / DevOps Team

### 11.1 Start Grafana

**Option A — Docker (included):**

```bash
docker-compose up -d grafana
# Access at http://localhost:3000 (admin/admin)
```

**Option B — Existing Grafana instance:**
Use your organization's existing Grafana deployment.

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
2. Manually download from https://github.com/lgtm-ai/git-ai
3. Place the binary in `$HOME/.local/bin/` (Linux/macOS) or add to PATH (Windows).

### Commits not classified as AI

**Diagnostic steps:**

```bash
# Check git-ai notes
git notes --ref=git-ai show <commit-sha>

# Check Co-Authored-By trailers
git log --format="%B" -1 <commit-sha> | grep -i "co-authored-by"

# Check commit message
git log --format="%s" -1 <commit-sha>
```

**Common causes:**
- git-ai hooks not installed in the repo — run `git-ai install`
- AI tool not configured to add trailers — check tool settings
- Detection patterns in `config.yaml` don't match your tool's output — update patterns

### GitHub Actions collect-metrics job fails

**Symptom:** The `collect-metrics` job fails in the pipeline.

**Fix:**
1. Verify the `ai-code-metrics` repo is public and accessible.
2. Check the `uses:` line — `sarasanalytics-com/ai-code-metrics/.github/workflows/collect-metrics.yml@dev` must be reachable.
3. Check the `if:` condition matches the correct branch ref (e.g., `refs/heads/dev`).
4. If the "Download collector script" step fails, the raw GitHub URL may be temporarily unavailable — re-run the job.

### Database connection errors *(Phase 2)*

**Fix:**
1. Verify PostgreSQL is running: `pg_isready -h <host> -p 5432`
2. Test credentials: `psql -h <host> -U metrics -d ai_code_metrics -c "SELECT 1"`
3. Check firewall/security group rules between collection server and database.

### Grafana dashboard shows no data *(Phase 2)*

**Fix:**
1. Test data source: Grafana > Data Sources > PostgreSQL > Test.
2. Verify data exists: `SELECT COUNT(*) FROM daily_contributions;`
3. Check the dashboard's time range — ensure it covers dates with data.

---

## 13. Maintenance & Operations

### Log Management

| Log type | Location | Retention |
|----------|----------|-----------|
| Daily collection | `logs/daily_YYYYMMDD_HHMMSS.log` | Auto-cleaned after 30 days |
| Half-life analysis | `logs/halflife_YYYYMMDD_HHMMSS.log` | Auto-cleaned after 90 days |

### Adding a New Repository

1. Add the `collect-metrics` job to the repo's `main.yml` (see Section 5.1).
2. Have developers on that repo run `dev_setup.sh`.
3. *(Phase 2)* Clone the repo on the collection server, add to `config.yaml`.

### Adding a New AI Tool

1. Update `detection` section in `config.yaml` with the tool's Co-Authored-By patterns, commit message patterns, or author email.
2. Update `ci/collect_on_merge.py` `classify_commit()` if the tool uses unique trailer formats.
3. No other code changes needed — the tool will appear in dashboards automatically.

### Updating Detection Patterns

If an AI tool changes its trailer format:

1. Update `config.yaml` with the new pattern.
2. Re-run the daily collector to reclassify recent commits: `python -m collector.metrics_aggregator --since <date>`
3. Historical data before the change will retain old classification (this is expected — it reflects what was true at commit time).

---

## 14. Security Considerations

| Concern | Mitigation |
|---------|-----------|
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
./setup/dev_setup.sh /path/to/repo          # Install git-ai hooks (macOS/Linux)
git-ai status                               # Verify git-ai is active in a repo

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
