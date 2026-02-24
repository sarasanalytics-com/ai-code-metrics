"""Wrapper around git-of-theseus for AI-segmented code half-life analysis."""

import json
import logging
import subprocess
import tempfile
from datetime import date, datetime
from pathlib import Path

from collector.db import get_connection, load_config, upsert_code_halflife
from collector.git_parser import CommitClassifier, get_git_ai_notes, parse_ai_notes, run_git

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def build_commit_tool_map(repo_path: str, classifier: CommitClassifier) -> dict[str, str]:
    """Build a map of commit SHA -> tool for all commits in the repo."""
    raw = run_git(repo_path, [
        "log", "--format=%H%x00%an%x00%ae%x00%B%x00%x01", "--all",
    ])

    tool_map = {}
    for entry in raw.split("\x01"):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split("\x00", 4)
        if len(parts) < 4:
            continue

        sha = parts[0].strip()

        # Check git-ai notes first
        notes = get_git_ai_notes(repo_path, sha)
        if notes:
            tool_map[sha] = parse_ai_notes(notes)
            continue

        # Fallback to classifier
        from collector.git_parser import CommitInfo
        commit = CommitInfo(
            sha=sha,
            author=parts[1].strip(),
            author_email=parts[2].strip(),
            date=date.today(),  # date doesn't matter for classification
            message=parts[3].strip(),
        )
        tool_map[sha] = classifier.classify(commit)

    return tool_map


def run_git_of_theseus(repo_path: str, output_dir: str) -> dict | None:
    """Run git-of-theseus survival analysis on a repo.

    Returns the parsed JSON output or None on failure.
    """
    try:
        subprocess.run(
            [
                "git-of-theseus-analyze",
                repo_path,
                "--outdir", output_dir,
            ],
            capture_output=True,
            text=True,
            timeout=600,  # 10 min timeout for large repos
            check=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"git-of-theseus failed for {repo_path}: {e.stderr}")
        return None
    except FileNotFoundError:
        logger.error("git-of-theseus-analyze not found. Install with: pip install git-of-theseus")
        return None

    # Read the survival data
    survival_file = Path(output_dir) / "survival.json"
    if not survival_file.exists():
        logger.error(f"No survival.json produced for {repo_path}")
        return None

    with open(survival_file) as f:
        return json.load(f)


def segment_survival_by_tool(
    repo_path: str,
    survival_data: dict,
    tool_map: dict[str, str],
) -> dict[str, list[dict]]:
    """Segment survival data by AI tool origin.

    Returns: {tool: [{cohort_date, lines_surviving, lines_original, survival_pct}, ...]}
    """
    # git-of-theseus outputs cohorts with commit SHAs
    # We cross-reference with our tool_map to segment
    segmented: dict[str, list[dict]] = {
        "human": [],
        "claude": [],
        "windsurf": [],
        "ai": [],
    }

    # The survival data structure from git-of-theseus varies by version.
    # Handle the common format: {"cohorts": {date_str: {sha: lines, ...}}, ...}
    cohorts = survival_data.get("cohorts", {})
    survival = survival_data.get("survival", {})

    if not cohorts:
        logger.warning("No cohort data found in survival output")
        return segmented

    for cohort_date_str, commit_data in cohorts.items():
        try:
            cohort_date = datetime.fromisoformat(cohort_date_str).date()
        except (ValueError, TypeError):
            continue

        # Aggregate lines by tool for this cohort
        tool_lines: dict[str, int] = {}
        for sha, lines in commit_data.items():
            tool = tool_map.get(sha, "human")
            tool_lines[tool] = tool_lines.get(tool, 0) + lines

        # Get surviving lines from the survival data
        surviving = survival.get(cohort_date_str, {})
        tool_surviving: dict[str, int] = {}
        for sha, lines in surviving.items():
            tool = tool_map.get(sha, "human")
            tool_surviving[tool] = tool_surviving.get(tool, 0) + lines

        for tool, original in tool_lines.items():
            if original == 0:
                continue
            surv = tool_surviving.get(tool, 0)
            pct = round((surv / original) * 100, 2) if original > 0 else 0
            bucket = tool if tool in segmented else "ai"
            segmented[bucket].append({
                "cohort_date": cohort_date,
                "lines_surviving": surv,
                "lines_original": original,
                "survival_pct": pct,
            })

    return segmented


def run_halflife_analysis(config: dict):
    """Run half-life analysis for all repos and write results to DB."""
    classifier = CommitClassifier.from_config(config)
    snapshot_date = date.today()
    min_cohort = config.get("halflife", {}).get("min_cohort_size", 50)

    conn = get_connection(config)
    try:
        for repo in config.get("repos", []):
            repo_name = repo["name"]
            repo_path = repo["path"]

            logger.info(f"Running half-life analysis for {repo_name}")

            # Build tool map for all commits
            tool_map = build_commit_tool_map(repo_path, classifier)
            logger.info(f"  Mapped {len(tool_map)} commits to tools")

            # Run git-of-theseus
            with tempfile.TemporaryDirectory() as tmpdir:
                survival_data = run_git_of_theseus(repo_path, tmpdir)
                if not survival_data:
                    logger.warning(f"  Skipping {repo_name} - no survival data")
                    continue

                segmented = segment_survival_by_tool(repo_path, survival_data, tool_map)

                # Write to DB
                rows = []
                for origin, entries in segmented.items():
                    for entry in entries:
                        if entry["lines_original"] < min_cohort:
                            continue
                        rows.append((
                            snapshot_date,
                            repo_name,
                            origin,
                            entry["cohort_date"],
                            entry["lines_surviving"],
                            entry["lines_original"],
                            entry["survival_pct"],
                        ))

                upsert_code_halflife(conn, rows)
                logger.info(f"  Wrote {len(rows)} half-life rows for {repo_name}")

        logger.info("Half-life analysis complete.")
    finally:
        conn.close()


def main():
    config = load_config()
    run_halflife_analysis(config)


if __name__ == "__main__":
    main()
