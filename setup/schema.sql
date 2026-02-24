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
