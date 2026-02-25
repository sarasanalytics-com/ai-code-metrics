"""Correlate Sentry incidents with AI-attributed commits.

Links Sentry issues to commits via releases, then classifies each commit's
AI tool attribution to measure if AI code causes more incidents.
"""

import argparse
import logging
import os
import re
from datetime import date, datetime, timedelta

import requests

from collector.db import get_connection, load_config, upsert_incident_commits

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SENTRY_API = "https://sentry.io/api/0"


def get_sentry_token(config: dict) -> str:
    token_env = config.get("sentry", {}).get("token_env", "SENTRY_AUTH_TOKEN")
    token = os.environ.get(token_env)
    if not token:
        raise RuntimeError(f"Sentry token not found in env var: {token_env}")
    return token


def sentry_get(url: str, token: str, params: dict = None) -> list | dict:
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def classify_commit_sha(sha: str, repo_path: str, config: dict) -> str:
    """Classify a commit by its SHA using local git log.

    Falls back to querying the commit message from git.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "log", "--format=%B", "-n", "1", sha],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return "unknown"
        message = result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "unknown"

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


def get_repo_path(repo_name: str, config: dict) -> str | None:
    """Find the local path for a repo by name."""
    for repo in config.get("repos", []):
        if repo["name"] == repo_name:
            return repo["path"]
    return None


def collect_incidents(config: dict, since: date):
    """Collect Sentry incidents and correlate with AI-attributed commits."""
    sentry_config = config.get("sentry", {})
    org = sentry_config.get("org", "sarasanalytics")
    token = get_sentry_token(config)
    projects = sentry_config.get("projects", [])

    if not projects:
        logger.warning("No Sentry projects configured")
        return

    conn = get_connection(config)
    try:
        for project in projects:
            slug = project["slug"]
            repo_name = project["repo"]
            repo_path = get_repo_path(repo_name, config)

            logger.info(f"Collecting Sentry incidents for {org}/{slug} (repo: {repo_name})")

            # Fetch recent issues
            issues = sentry_get(
                f"{SENTRY_API}/projects/{org}/{slug}/issues/",
                token,
                params={
                    "query": f"firstSeen:>{since.isoformat()}",
                    "sort": "date",
                },
            )

            logger.info(f"  Found {len(issues)} issues since {since}")

            # Fetch releases with commits
            releases = sentry_get(
                f"{SENTRY_API}/organizations/{org}/releases/",
                token,
                params={"project": slug},
            )

            # Build a map of release version -> commits
            release_commits: dict[str, list[str]] = {}
            for release in releases:
                version = release["version"]
                try:
                    commits_data = sentry_get(
                        f"{SENTRY_API}/organizations/{org}/releases/{version}/commits/",
                        token,
                    )
                    release_commits[version] = [
                        c.get("id", "") for c in commits_data if c.get("id")
                    ]
                except requests.HTTPError:
                    logger.warning(f"  Could not fetch commits for release {version}")
                    continue

            # Build a map of issue -> release (via firstRelease)
            rows = []
            for issue in issues:
                issue_id = str(issue["id"])
                issue_title = issue.get("title", "")[:500]
                first_seen_str = issue.get("firstSeen")
                events_count = issue.get("count", 0)

                # Get the release this issue first appeared in
                first_release = issue.get("firstRelease")
                if not first_release:
                    continue

                release_version = first_release.get("version", "")
                commits = release_commits.get(release_version, [])

                if not commits:
                    continue

                first_seen = None
                if first_seen_str:
                    try:
                        first_seen = datetime.fromisoformat(
                            first_seen_str.replace("Z", "+00:00")
                        )
                    except ValueError:
                        pass

                # Classify each commit in the release
                for sha in commits:
                    if repo_path:
                        tool = classify_commit_sha(sha, repo_path, config)
                    else:
                        tool = "unknown"

                    rows.append((
                        repo_name,
                        issue_id,
                        issue_title,
                        release_version,
                        sha[:40],
                        tool,
                        first_seen,
                        int(events_count) if events_count else 0,
                    ))

            if rows:
                upsert_incident_commits(conn, rows)
                logger.info(f"  Upserted {len(rows)} incident-commit rows")
            else:
                logger.info(f"  No incident-commit correlations found")

        logger.info("Sentry incident collection complete.")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Collect Sentry incident correlations")
    parser.add_argument(
        "--since",
        type=date.fromisoformat,
        help="Collect issues first seen since this date (YYYY-MM-DD). Defaults to 30 days ago.",
    )
    args = parser.parse_args()

    config = load_config()
    since = args.since or (date.today() - timedelta(days=30))
    collect_incidents(config, since)


if __name__ == "__main__":
    main()
