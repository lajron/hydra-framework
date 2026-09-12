"""Git port.

The sole source of git-derived state: config values and tracked-file
listings. Parameterized by `root` instead of a module global, so a golden
fixture points these at a fixture tree the same way `RepoContext` does for
the rest of command dispatch.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

GIT_CONFIG_TIMEOUT_SECONDS = 5
GIT_ADD_TIMEOUT_SECONDS = 15
GIT_DIFF_TIMEOUT_SECONDS = 15
GIT_LOG_TIMEOUT_SECONDS = 15
GIT_LS_FILES_TIMEOUT_SECONDS = 15
GIT_CHECK_IGNORE_TIMEOUT_SECONDS = 15
GIT_STATUS_TIMEOUT_SECONDS = 15


def config_email(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "config", "user.email"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=GIT_CONFIG_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def last_commit_iso(root: Path, path: str) -> str:
    """The ISO-8601 commit date of the last commit touching `path`, or `""`
    when git is absent, the path is untracked, or the call fails. Never
    raises: staleness is a warning-level convenience, not something that
    should ever break a caller."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", path],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=GIT_LOG_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def tracked_files(root: Path, prefix: str) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--", prefix],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=GIT_LS_FILES_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def ignored_files(root: Path, prefix: str) -> list[str]:
    """Untracked files beneath `prefix` that Git's ignore rules currently
    exclude. Used to check that everything a provider directory ignores is a
    verified Hydra ownership member -- narrower than `ignore_match` per path,
    since it reports only what actually exists on disk, not every path a
    glob could ever match."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--others", "--ignored", "--exclude-standard", "--", prefix],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=GIT_LS_FILES_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def ignore_match(root: Path, path: str, *, no_index: bool = False) -> str:
    """Verbose `git check-ignore` match for `path`, or `""` when not ignored.

    The verbose line is useful evidence for migration/takeover routing, but a
    missing Git repository or a non-ignored path is not an error for callers.

    `no_index=True` evaluates ignore patterns alone, ignoring whether `path`
    is currently tracked. Plain `check-ignore` treats an already-tracked path
    as never-ignored (verified against real Git), which is right for "is
    this untracked path safe to leave out" but wrong for "would this pattern
    also swallow a file that happens to be tracked right now" -- the check
    Git ownership validation needs when confirming a stable tracked file
    does not collide with a generated-adapter ignore pattern.
    """
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-v", *(["--no-index"] if no_index else []), "--", path],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=GIT_CHECK_IGNORE_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def stage_file(root: Path, path: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "add", "--", path],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=GIT_ADD_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def is_tracked(root: Path, path: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", path],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=GIT_LS_FILES_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def worktree_matches_index(root: Path, path: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "diff", "--quiet", "--", path],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=GIT_DIFF_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def short_status(root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=GIT_STATUS_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]
