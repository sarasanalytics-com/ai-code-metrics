"""Collect PR-level metrics from GitHub for token efficiency tracking.

Measures how much AI-generated code survives code review by comparing
lines at PR creation vs lines that land after merge.
"""

import argparse
import logging
import os
import re
from datetime import date, datetime, timedelta

import requests

from collector.db import get_connection, load_config, upsert_pr_metrics

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


def get_github_token(config: dict) -> str:
    token_env = config.get("github", {}).get("token_env", "SARAS_UI_TEAM_ACCESS_TOKEN")
    token = os.environ.get(token_env)
    if not token:
        raise RuntimeError(f"GitHub token not found in env var: {token_env}")
    return token


def github_get(url: str, token: str, params: dict = None) -> list | dict:
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def github_get_paginated(url: str, token: str, params: dict = None) -> list:
    """Fetch all pages from a paginated GitHub API endpoint."""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    params = dict(params or {})
    params.setdefault("per_page", 100)
    results = []

    while url:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        results.extend(resp.json())
        # Follow Link header for next page
        url = None
        params = None  # params already in the URL from Link header
        link = resp.headers.get("Link", "")
        for part in link.split(","):
            if 'rel="next"' in part:
                url = part.split(";")[0].strip().strip("<>")

    return results


def classify_commit_message(message: str, config: dict) -> str:
    """Classify a commit by its message using the same detection patterns."""
    detection = config.get("detection", {})

    # Check Co-Authored-By trailers
    for tool, patterns in detection.get("co_authored_by", {}).items():
        for pattern in patterns:
            if "Co-Authored-By:" in message and pattern in message:
                return tool

    # Check commit message patterns
    for tool, patterns in detection.get("commit_message", {}).items():
        for pattern in patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return tool

    return "human"


def get_dominant_tool(tools: list[str]) -> str:
    """Determine the dominant tool from a list of per-commit tools.

    If any AI tool is present, the PR is attributed to that tool.
    If multiple AI tools, pick the most frequent.
    """
    ai_tools = [t for t in tools if t != "human"]
    if not ai_tools:
        return "human"

    # Count occurrences and return most common
    from collections import Counter
    counts = Counter(ai_tools)
    return counts.most_common(1)[0][0]


def collect_pr_metrics(config: dict, since: date):
    """Collect PR metrics for all repos from GitHub."""
    github_config = config.get("github", {})
    org = github_config.get("org", "sarasanalytics-com")
    token = get_github_token(config)
    default_branch = config.get("collection", {}).get("default_branch", "main")

    conn = get_connection(config)
    try:
        for repo_config in config.get("repos", []):
            repo_name = repo_config["name"]
            base_branch = repo_config.get("branch", default_branch)

            logger.info(f"Collecting PR metrics for {org}/{repo_name}")

            # Fetch merged PRs
            prs = github_get_paginated(
                f"{GITHUB_API}/repos/{org}/{repo_name}/pulls",
                token,
                params={
                    "state": "closed",
                    "base": base_branch,
                    "sort": "updated",
                    "direction": "desc",
                },
            )

            rows = []
            for pr in prs:
                if not pr.get("merged_at"):
                    continue  # Skip closed-but-not-merged PRs

                merged_at = datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00"))
                if merged_at.date() < since:
                    continue

                pr_number = pr["number"]
                author = pr["user"]["login"]
                created_at = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
                additions = pr.get("additions", 0)
                deletions = pr.get("deletions", 0)

                # Get PR commits to classify the dominant tool
                commits = github_get(
                    f"{GITHUB_API}/repos/{org}/{repo_name}/pulls/{pr_number}/commits",
                    token,
                )

                tools = []
                for commit in commits:
                    msg = commit.get("commit", {}).get("message", "")
                    tools.append(classify_commit_message(msg, config))

                dominant_tool = get_dominant_tool(tools)

                # Review time in hours
                review_hours = (merged_at - created_at).total_seconds() / 3600

                # lines_added_pr = additions at PR level (what the author proposed)
                # lines_added_merged = same as additions (it was merged as-is after review)
                # In future, could compare with review-requested-changes to get a delta
                rows.append((
                    repo_name,
                    pr_number,
                    author,
                    dominant_tool,
                    additions,       # lines_added_pr
                    additions,       # lines_added_merged (same for now)
                    deletions,       # lines_removed_pr
                    len(commits),    # commits_count
                    created_at,
                    merged_at,
                    round(review_hours, 2),
                ))

            logger.info(f"  Found {len(rows)} merged PRs since {since}")

            if rows:
                upsert_pr_metrics(conn, rows)
                logger.info(f"  Upserted {len(rows)} PR metrics rows")

        logger.info("PR metrics collection complete.")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Collect PR metrics from GitHub")
    parser.add_argument(
        "--since",
        type=date.fromisoformat,
        help="Collect PRs merged since this date (YYYY-MM-DD). Defaults to 30 days ago.",
    )
    args = parser.parse_args()

    config = load_config()
    since = args.since or (date.today() - timedelta(days=30))
    collect_pr_metrics(config, since)


if __name__ == "__main__":
    main()
