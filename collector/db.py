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
