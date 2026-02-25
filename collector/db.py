"""PostgreSQL database interface for AI code metrics."""

import psycopg2
import psycopg2.extras
import yaml
from pathlib import Path


def load_config():
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_connection(config=None):
    if config is None:
        config = load_config()
    db = config["database"]
    return psycopg2.connect(
        host=db["host"],
        port=db["port"],
        dbname=db["name"],
        user=db["user"],
        password=db["password"],
    )


def upsert_daily_contributions(conn, rows):
    """Upsert daily contribution rows.

    Each row: (date, repo, tool, lines_added, lines_removed, commits, unique_authors)
    """
    if not rows:
        return
    query = """
        INSERT INTO daily_contributions (date, repo, tool, lines_added, lines_removed, commits, unique_authors)
        VALUES %s
        ON CONFLICT (date, repo, tool)
        DO UPDATE SET
            lines_added = EXCLUDED.lines_added,
            lines_removed = EXCLUDED.lines_removed,
            commits = EXCLUDED.commits,
            unique_authors = EXCLUDED.unique_authors
    """
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, query, rows)
    conn.commit()


def upsert_daily_active_users(conn, rows):
    """Upsert daily active user rows.

    Each row: (date, repo, tool, author, commits)
    """
    if not rows:
        return
    query = """
        INSERT INTO daily_active_users (date, repo, tool, author, commits)
        VALUES %s
        ON CONFLICT (date, repo, tool, author)
        DO UPDATE SET
            commits = EXCLUDED.commits
    """
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, query, rows)
    conn.commit()


def upsert_code_halflife(conn, rows):
    """Insert code half-life snapshot rows.

    Each row: (snapshot_date, repo, origin, cohort_date, lines_surviving, lines_original, survival_pct)
    """
    if not rows:
        return
    query = """
        INSERT INTO code_halflife (snapshot_date, repo, origin, cohort_date, lines_surviving, lines_original, survival_pct)
        VALUES %s
    """
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, query, rows)
    conn.commit()


def upsert_pr_metrics(conn, rows):
    """Upsert PR metrics rows.

    Each row: (repo, pr_number, author, tool, lines_added_pr, lines_added_merged,
               lines_removed_pr, commits_count, created_at, merged_at, review_time_hours)
    """
    if not rows:
        return
    query = """
        INSERT INTO pr_metrics (repo, pr_number, author, tool, lines_added_pr, lines_added_merged,
                                lines_removed_pr, commits_count, created_at, merged_at, review_time_hours)
        VALUES %s
        ON CONFLICT (repo, pr_number)
        DO UPDATE SET
            author = EXCLUDED.author,
            tool = EXCLUDED.tool,
            lines_added_pr = EXCLUDED.lines_added_pr,
            lines_added_merged = EXCLUDED.lines_added_merged,
            lines_removed_pr = EXCLUDED.lines_removed_pr,
            commits_count = EXCLUDED.commits_count,
            created_at = EXCLUDED.created_at,
            merged_at = EXCLUDED.merged_at,
            review_time_hours = EXCLUDED.review_time_hours
    """
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, query, rows)
    conn.commit()


def upsert_incident_commits(conn, rows):
    """Upsert incident commit rows.

    Each row: (repo, sentry_issue_id, sentry_issue_title, release_version,
               commit_sha, commit_tool, first_seen, events_count)
    """
    if not rows:
        return
    query = """
        INSERT INTO incident_commits (repo, sentry_issue_id, sentry_issue_title, release_version,
                                      commit_sha, commit_tool, first_seen, events_count)
        VALUES %s
        ON CONFLICT (repo, sentry_issue_id, commit_sha)
        DO UPDATE SET
            sentry_issue_title = EXCLUDED.sentry_issue_title,
            release_version = EXCLUDED.release_version,
            commit_tool = EXCLUDED.commit_tool,
            first_seen = EXCLUDED.first_seen,
            events_count = EXCLUDED.events_count
    """
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, query, rows)
    conn.commit()


def upsert_ai_spend(conn, rows):
    """Upsert AI spend rows.

    Each row: (date, repo, tool, spend_usd, tokens_input, tokens_output, source)
    """
    if not rows:
        return
    query = """
        INSERT INTO ai_spend (date, repo, tool, spend_usd, tokens_input, tokens_output, source)
        VALUES %s
        ON CONFLICT (date, repo, tool, source)
        DO UPDATE SET
            spend_usd = EXCLUDED.spend_usd,
            tokens_input = EXCLUDED.tokens_input,
            tokens_output = EXCLUDED.tokens_output
    """
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, query, rows)
    conn.commit()
