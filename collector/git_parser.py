"""Parse git log and git-ai notes to classify commits as AI or human."""

import re
import subprocess
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import yaml


@dataclass
class CommitInfo:
    sha: str
    author: str
    author_email: str
    date: date
    message: str
    lines_added: int = 0
    lines_removed: int = 0
    tool: str = "human"  # 'claude', 'windsurf', 'cursor', 'human'


@dataclass
class CommitClassifier:
    """Classifies commits based on config-driven patterns."""

    co_authored_by: dict = field(default_factory=dict)
    commit_message: dict = field(default_factory=dict)
    author_email: dict = field(default_factory=dict)

    @classmethod
    def from_config(cls, config: dict) -> "CommitClassifier":
        detection = config.get("detection", {})
        return cls(
            co_authored_by=detection.get("co_authored_by", {}),
            commit_message=detection.get("commit_message", {}),
            author_email=detection.get("author_email", {}),
        )

    def classify(self, commit: CommitInfo) -> str:
        """Classify a commit. Returns tool name or 'human'."""
        # 1. Check git-ai notes (handled separately in parse_repo)

        # 2. Check Co-Authored-By trailers
        for tool, patterns in self.co_authored_by.items():
            for pattern in patterns:
                if f"Co-Authored-By:" in commit.message and pattern in commit.message:
                    return tool

        # 3. Check commit message patterns
        for tool, patterns in self.commit_message.items():
            for pattern in patterns:
                if re.search(pattern, commit.message, re.IGNORECASE):
                    return tool

        # 4. Check author email
        for tool, emails in self.author_email.items():
            for email in emails:
                if commit.author_email.lower() == email.lower():
                    return tool

        return "human"


def run_git(repo_path: str, args: list[str]) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git", "-C", repo_path] + args,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git error in {repo_path}: {result.stderr.strip()}")
    return result.stdout


def get_git_ai_notes(repo_path: str, sha: str) -> str | None:
    """Try to read git-ai notes for a commit."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "notes", "--ref=git-ai", "show", sha],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, Exception):
        pass
    return None


def parse_ai_notes(notes: str) -> str:
    """Parse git-ai notes to determine the AI tool.

    git-ai notes format varies; this handles common formats.
    Returns the tool name or 'ai' as a generic fallback.
    """
    notes_lower = notes.lower()
    if "claude" in notes_lower or "anthropic" in notes_lower:
        return "claude"
    if "windsurf" in notes_lower or "codeium" in notes_lower:
        return "windsurf"
    if "cursor" in notes_lower:
        return "cursor"
    # git-ai detected AI but we can't determine which tool
    if notes.strip():
        return "ai"
    return "human"


def parse_commits(
    repo_path: str,
    since: date,
    until: date,
    branch: str = "main",
) -> list[CommitInfo]:
    """Parse git log for a date range and return CommitInfo objects."""
    log_format = "%H%x00%an%x00%ae%x00%aI%x00%B%x00"
    separator = "%x01"

    try:
        raw = run_git(repo_path, [
            "log",
            f"--since={since.isoformat()}",
            f"--until={until.isoformat()}",
            f"--format={separator}{log_format}",
            "--numstat",
            branch,
        ])
    except RuntimeError:
        return []

    if not raw.strip():
        return []

    commits = []
    entries = raw.split("\x01")

    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue

        parts = entry.split("\x00", 5)
        if len(parts) < 5:
            continue

        sha, author, email, date_str, message = parts[0], parts[1], parts[2], parts[3], parts[4]

        # Parse numstat (lines after the message)
        remaining = parts[5] if len(parts) > 5 else ""
        added = 0
        removed = 0
        for line in remaining.strip().splitlines():
            nums = line.split("\t")
            if len(nums) >= 2:
                try:
                    added += int(nums[0])
                except ValueError:
                    pass  # binary file shows '-'
                try:
                    removed += int(nums[1])
                except ValueError:
                    pass

        try:
            dt = datetime.fromisoformat(date_str)
            commit_date = dt.date()
        except (ValueError, TypeError):
            continue

        commits.append(CommitInfo(
            sha=sha.strip(),
            author=author.strip(),
            author_email=email.strip(),
            date=commit_date,
            message=message.strip(),
            lines_added=added,
            lines_removed=removed,
        ))

    return commits


def classify_commits(
    repo_path: str,
    commits: list[CommitInfo],
    classifier: CommitClassifier,
) -> list[CommitInfo]:
    """Classify each commit's tool attribution."""
    for commit in commits:
        # Priority 1: git-ai notes
        notes = get_git_ai_notes(repo_path, commit.sha)
        if notes:
            commit.tool = parse_ai_notes(notes)
            continue

        # Priority 2-4: pattern matching
        commit.tool = classifier.classify(commit)

    return commits


def parse_repo(
    repo_path: str,
    since: date,
    until: date,
    classifier: CommitClassifier,
    branch: str = "main",
) -> list[CommitInfo]:
    """Parse and classify all commits for a repo in a date range."""
    commits = parse_commits(repo_path, since, until, branch)
    return classify_commits(repo_path, commits, classifier)
