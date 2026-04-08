import json, os, sys
from datetime import date
import psycopg2

def ingest(data: dict, conn):
    cur = conn.cursor()
    collected_date = date.fromisoformat(data["collected_at"][:10])
    repo = data["repo"]

    # Upsert daily_contributions
    for tool, stats in data["breakdown"].items():
        cur.execute("""
            INSERT INTO daily_contributions
              (date, repo, tool, lines_added, lines_removed, commits, unique_authors)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (date, repo, tool) DO UPDATE SET
              lines_added    = daily_contributions.lines_added    + EXCLUDED.lines_added,
              lines_removed  = daily_contributions.lines_removed  + EXCLUDED.lines_removed,
              commits        = daily_contributions.commits        + EXCLUDED.commits,
              unique_authors = GREATEST(daily_contributions.unique_authors, EXCLUDED.unique_authors)
        """, (
            collected_date, repo, tool,
            stats["lines_added"], stats["lines_removed"],
            stats["commits"], stats["unique_authors"]
        ))

    # Upsert daily_active_users (per commit author)
    for commit in data.get("commits", []):
        cur.execute("""
            INSERT INTO daily_active_users (date, repo, tool, author, commits)
            VALUES (%s, %s, %s, %s, 1)
            ON CONFLICT (date, repo, tool, author) DO UPDATE SET
              commits = daily_active_users.commits + 1
        """, (
            date.fromisoformat(commit["date"]), repo,
            commit["tool"], commit["author"]
        ))

    conn.commit()
    cur.close()

if __name__ == "__main__":
    with open(os.environ["METRICS_FILE"]) as f:
        data = json.load(f)

    conn = psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", 5432)),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        sslmode="disable" 
    )
    ingest(data, conn)
    conn.close()
    print("Ingested successfully.")