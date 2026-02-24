# AI Code Metrics Dashboard

Track AI vs Human code contributions across frontend repos using open-source tools.

## What it measures

- **Contribution %** -- AI vs Human code over time (stacked area chart)
- **Agent DAU/WAU/MAU** -- Active developers per AI tool per day/week/month
- **Code Half-life** -- How long AI vs Human code survives before rewrite
- **Code Half-life by Agent** -- Durability broken down by Claude vs Windsurf

## Architecture

```
git-ai (hooks on each repo)
    → collector (daily cron)
        → PostgreSQL (metrics DB)
            → Grafana (dashboards)

git-of-theseus → weekly half-life analysis → PostgreSQL
```

## Prerequisites

- Python 3.10+
- PostgreSQL 14+
- [git-ai](https://github.com/lgtm-ai/git-ai) installed on target repos
- [git-of-theseus](https://github.com/erikbern/git-of-theseus) (`pip install git-of-theseus`)
- Grafana (use existing instance or local via docker-compose)

## Quick Start

### 1. Configure

Copy and edit the config file:

```bash
cp config.yaml.example config.yaml
# Edit config.yaml with your repo paths, DB connection, etc.
```

### 2. Set up the database

```bash
# Start Postgres (local dev)
docker-compose up -d postgres

# Apply schema
psql -h localhost -U metrics -d ai_code_metrics -f setup/schema.sql
```

### 3. Install git-ai on your repos

```bash
./setup/install_git_ai.sh
```

### 4. Run the daily collector

```bash
# Manual run
python -m collector.metrics_aggregator

# Or set up cron
crontab -e
# Add: 0 2 * * * /path/to/scripts/run_daily.sh
```

### 5. Set up Grafana

Import `dashboards/ai_metrics.json` into your Grafana instance and point it at the PostgreSQL data source.

## Project Structure

```
ai-code-metrics/
├── config.yaml              # Repo list, DB connection, schedule
├── docker-compose.yml        # Postgres + Grafana (local dev)
├── collector/
│   ├── git_parser.py         # Parses git log + git-ai notes
│   ├── metrics_aggregator.py # Computes daily AI vs Human stats
│   ├── halflife_runner.py    # Wraps git-of-theseus with AI segmentation
│   └── db.py                 # PostgreSQL writes
├── setup/
│   ├── install_git_ai.sh     # Install git-ai hooks on repos
│   └── schema.sql            # Database schema
├── dashboards/
│   └── ai_metrics.json       # Grafana dashboard (exportable)
└── scripts/
    └── run_daily.sh          # Cron entry point
```

## AI Commit Classification

Commits are classified using this priority order:

1. **git-ai notes** (most accurate) -- line-level attribution from git-ai hooks
2. **Co-Authored-By trailer** -- `Co-Authored-By: Claude` in commit message (Claude Code)
3. **Commit message patterns** -- Windsurf/Cursor identifiable patterns
4. **Author email convention** -- Team-configured AI tool emails

## License

Internal use only.
