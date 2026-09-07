"""Git checkpoint preconditions for destructive Knowledge migration."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _output(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if result.returncode != 0:
        raise ValueError((result.stderr or result.stdout).strip() or "Git command failed")
    return result.stdout.strip()


def checkpoint(root: Path) -> str:
    return _output(root, "rev-parse", "HEAD")


def require_clean(root: Path, expected: str) -> None:
    current = checkpoint(root)
    if current != expected:
        raise ValueError(f"checkpoint commit changed: reviewed `{expected}`, current `{current}`")
    if _output(root, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("Git worktree is not clean at the reviewed checkpoint")
