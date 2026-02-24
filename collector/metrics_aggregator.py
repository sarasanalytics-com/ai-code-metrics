"""Daily metrics aggregator. Collects commits from all repos and writes to PostgreSQL."""

import argparse
import logging
from collections import defaultdict
from datetime import date, timedelta

from collector.db import get_connection, load_config, upsert_daily_active_users, upsert_daily_contributions
from collector.git_parser import CommitClassifier, CommitInfo, parse_repo

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def aggregate_contributions(
    repo_name: str, commits: list[CommitInfo]
) -> list[tuple]:
    """Aggregate commits into daily contribution rows.

    Returns rows of: (date, repo, tool, lines_added, lines_removed, commits, unique_authors)
    """
    # Group by (date, tool)
    groups: dict[tuple[date, str], dict] = defaultdict(
        lambda: {"added": 0, "removed": 0, "commits": 0, "authors": set()}
    )

    for c in commits:
        key = (c.date, c.tool)
        groups[key]["added"] += c.lines_added
        groups[key]["removed"] += c.lines_removed
        groups[key]["commits"] += 1
        groups[key]["authors"].add(c.author)

    rows = []
    for (d, tool), stats in groups.items():
        rows.append((
            d,
            repo_name,
            tool,
            stats["added"],
            stats["removed"],
            stats["commits"],
            len(stats["authors"]),
        ))
    return rows


def aggregate_active_users(
    repo_name: str, commits: list[CommitInfo]
) -> list[tuple]:
    """Aggregate commits into daily active user rows.

    Returns rows of: (date, repo, tool, author, commits)
    """
    groups: dict[tuple[date, str, str], int] = defaultdict(int)

    for c in commits:
        key = (c.date, c.tool, c.author)
        groups[key] += 1

    rows = []
    for (d, tool, author), commit_count in groups.items():
        rows.append((d, repo_name, tool, author, commit_count))
    return rows


def run_collection(config: dict, since: date, until: date):
    """Run the full collection pipeline for all repos."""
    classifier = CommitClassifier.from_config(config)
    default_branch = config.get("collection", {}).get("default_branch", "main")

    conn = get_connection(config)
    try:
        for repo in config.get("repos", []):
            repo_name = repo["name"]
            repo_path = repo["path"]
            branch = repo.get("branch", default_branch)

            logger.info(f"Processing {repo_name} ({repo_path}) [{since} to {until}]")

            commits = parse_repo(repo_path, since, until, classifier, branch)
            logger.info(f"  Found {len(commits)} commits")

            if not commits:
                continue

            contribution_rows = aggregate_contributions(repo_name, commits)
            active_user_rows = aggregate_active_users(repo_name, commits)

            upsert_daily_contributions(conn, contribution_rows)
            upsert_daily_active_users(conn, active_user_rows)

            # Log summary
            by_tool = defaultdict(int)
            for c in commits:
                by_tool[c.tool] += 1
            logger.info(f"  Breakdown: {dict(by_tool)}")

        logger.info("Collection complete.")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Collect AI code metrics from git repos")
    parser.add_argument(
        "--since",
        type=date.fromisoformat,
        help="Start date (YYYY-MM-DD). Defaults to lookback_days from config.",
    )
    parser.add_argument(
        "--until",
        type=date.fromisoformat,
        default=date.today(),
        help="End date (YYYY-MM-DD). Defaults to today.",
    )
    args = parser.parse_args()

    config = load_config()
    lookback = config.get("collection", {}).get("lookback_days", 7)
    since = args.since or (args.until - timedelta(days=lookback))

    run_collection(config, since, args.until)


if __name__ == "__main__":
    main()
