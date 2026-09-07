"""Git checkpoint preconditions for destructive Knowledge migration."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _output(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if result.returncode != 0:
        raise ValueError((result.stderr or result.stdout).strip() or "Git command failed")
    return result.stdout.strip()


def tracked_files(root: Path) -> list[str] | None:
    """Repository-relative tracked paths, or None when `root` is not a Git tree.

    The migration may only rewrite files Git can restore. `require_clean`
    ignores untracked files, so rewriting one would put it outside the recorded
    rollback boundary, and its contents would leak into the reviewed plan
    digest.
    """
    try:
        listed = _output(root, "ls-files", "-z")
    except (ValueError, OSError):
        return None
    return [item for item in listed.split("\0") if item]


def rewrite_candidates(root: Path) -> list[Path]:
    """Files the migration may rewrite, deterministically ordered.

    Tracked files where `root` is a Git tree; otherwise the whole tree, which
    only happens in inspection and test contexts, since apply always requires
    a Git checkpoint.
    """
    tracked = tracked_files(root)
    if tracked is None:
        return sorted(item for item in root.rglob("*") if item.is_file())
    return sorted(path for item in tracked if (path := root / item).is_file())


def checkpoint(root: Path) -> str:
    return _output(root, "rev-parse", "HEAD")


def require_clean(root: Path, expected: str) -> None:
    current = checkpoint(root)
    if current != expected:
        raise ValueError(f"checkpoint commit changed: reviewed `{expected}`, current `{current}`")
    if _output(root, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("Git worktree is not clean at the reviewed checkpoint")
