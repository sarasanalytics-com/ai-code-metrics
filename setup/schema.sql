-- AI Code Metrics Database Schema

-- Daily contribution metrics per repo per tool
CREATE TABLE IF NOT EXISTS daily_contributions (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    repo VARCHAR(255) NOT NULL,
    tool VARCHAR(50) NOT NULL,        -- 'claude', 'windsurf', 'human'
    lines_added INT DEFAULT 0,
    lines_removed INT DEFAULT 0,
    commits INT DEFAULT 0,
    unique_authors INT DEFAULT 0,
    UNIQUE(date, repo, tool)
);

CREATE INDEX IF NOT EXISTS idx_daily_contributions_date ON daily_contributions(date);
CREATE INDEX IF NOT EXISTS idx_daily_contributions_repo ON daily_contributions(repo);

-- Active users per tool per day (for DAU/WAU/MAU)
CREATE TABLE IF NOT EXISTS daily_active_users (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    repo VARCHAR(255) NOT NULL,
    tool VARCHAR(50) NOT NULL,
    author VARCHAR(255) NOT NULL,
    commits INT DEFAULT 0,
    UNIQUE(date, repo, tool, author)
);

CREATE INDEX IF NOT EXISTS idx_daily_active_users_date ON daily_active_users(date);
CREATE INDEX IF NOT EXISTS idx_daily_active_users_tool ON daily_active_users(tool);

-- Code half-life snapshots (weekly)
CREATE TABLE IF NOT EXISTS code_halflife (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    repo VARCHAR(255) NOT NULL,
    origin VARCHAR(50) NOT NULL,      -- 'ai', 'human', 'claude', 'windsurf'
    cohort_date DATE NOT NULL,        -- when the code was originally written
    lines_surviving INT NOT NULL,
    lines_original INT NOT NULL,
    survival_pct DECIMAL(5,2) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_code_halflife_snapshot ON code_halflife(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_code_halflife_repo ON code_halflife(repo);
CREATE INDEX IF NOT EXISTS idx_code_halflife_origin ON code_halflife(origin);

-- PR-level metrics (for token efficiency tracking)
CREATE TABLE IF NOT EXISTS pr_metrics (
    id SERIAL PRIMARY KEY,
    repo VARCHAR(255) NOT NULL,
    pr_number INT NOT NULL,
    author VARCHAR(255) NOT NULL,
    tool VARCHAR(50) NOT NULL,           -- dominant tool in the PR
    lines_added_pr INT DEFAULT 0,        -- lines at PR creation
    lines_added_merged INT DEFAULT 0,    -- lines that landed after review
    lines_removed_pr INT DEFAULT 0,
    commits_count INT DEFAULT 0,
    created_at TIMESTAMP,
    merged_at TIMESTAMP,
    review_time_hours DECIMAL(10,2),     -- time from PR open to merge
    UNIQUE(repo, pr_number)
);

CREATE INDEX IF NOT EXISTS idx_pr_metrics_repo ON pr_metrics(repo);
CREATE INDEX IF NOT EXISTS idx_pr_metrics_tool ON pr_metrics(tool);

-- Incident correlation (Sentry issues linked to commits)
CREATE TABLE IF NOT EXISTS incident_commits (
    id SERIAL PRIMARY KEY,
    repo VARCHAR(255) NOT NULL,
    sentry_issue_id VARCHAR(255) NOT NULL,
    sentry_issue_title TEXT,
    release_version VARCHAR(255),
    commit_sha VARCHAR(40) NOT NULL,
    commit_tool VARCHAR(50) NOT NULL,    -- AI tool attribution
    first_seen TIMESTAMP,
    events_count INT DEFAULT 0,
    UNIQUE(repo, sentry_issue_id, commit_sha)
);

CREATE INDEX IF NOT EXISTS idx_incident_commits_repo ON incident_commits(repo);
CREATE INDEX IF NOT EXISTS idx_incident_commits_tool ON incident_commits(commit_tool);

-- AI spend tracking (estimated or self-reported)
CREATE TABLE IF NOT EXISTS ai_spend (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    repo VARCHAR(255),                   -- NULL for org-wide spend
    tool VARCHAR(50) NOT NULL,
    spend_usd DECIMAL(10,2) DEFAULT 0,
    tokens_input BIGINT DEFAULT 0,
    tokens_output BIGINT DEFAULT 0,
    source VARCHAR(50) NOT NULL,         -- 'api', 'manual', 'estimated'
    UNIQUE(date, repo, tool, source)
);

CREATE INDEX IF NOT EXISTS idx_ai_spend_date ON ai_spend(date);
CREATE INDEX IF NOT EXISTS idx_ai_spend_tool ON ai_spend(tool);
