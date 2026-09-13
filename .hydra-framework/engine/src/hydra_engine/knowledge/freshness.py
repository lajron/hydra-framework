"""Git-derived corpus and knowledge-unit source freshness helpers."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
import re
import subprocess
from pathlib import Path
from typing import Mapping

from hydra_engine.documents.digests import normalized_digest
from hydra_engine.documents.frontmatter_blocks import yaml_list
from hydra_engine.knowledge.packages import ContextCompilerPaths
from hydra_engine.ports import git as git_port

SOURCE_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

# Keep these values aligned with knowledge.search_index.  This module cannot
# import that module: doing so would pull the SQLite-backed search surface into
# the process that decides whether it is safe to use.
SEARCH_EXTENSIONS = {".md", ".yaml", ".yml", ".txt", ".sh", ".py"}
SEARCH_ROOTS = (
    ".hydra-framework/repo/knowledge",
    ".hydra-framework/capabilities",
    ".hydra-framework/core",
    ".hydra-framework/validation",
    ".hydra-framework/engine/src/hydra_engine",
)
_OBJECT_HANDLER_SUFFIXES = {".md", ".yaml", ".yml"}
_OBJECT_ROOTS = (
    ".hydra-framework/repo/",
    ".hydra-framework/capabilities/",
    ".hydra-framework/core/",
    ".hydra-framework/validation/",
)

GUARD_OK = "ok"
_GUARD_REASONS = {
    "not-a-git-worktree",
    "git-unavailable",
    "trustctime-disabled",
    "checkstat-minimal",
    "governed-path-ignored",
    "governed-path-assume-unchanged",
    "governed-path-skip-worktree",
}


class FreshnessError(RuntimeError):
    """A Git or worktree read failed while computing freshness."""

    def __init__(self, message: str, *, git_missing: bool = False) -> None:
        super().__init__(message)
        self.git_missing = git_missing


@dataclass(frozen=True)
class GuardResult:
    ok: bool
    reason: str


@dataclass(frozen=True)
class CorpusDelta:
    added: tuple[str, ...]
    modified: tuple[str, ...]
    deleted: tuple[str, ...]

    def is_empty(self) -> bool:
        return not (self.added or self.modified or self.deleted)


def _git(root: Path, *args: str) -> bytes:
    """Run Git without taking optional locks, normalizing process failures."""
    try:
        result = subprocess.run(
            ["git", "--no-optional-locks", *args],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError as error:
        raise FreshnessError("git is unavailable", git_missing=True) from error
    except OSError as error:
        raise FreshnessError(str(error)) from error
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise FreshnessError(detail or f"git {' '.join(args)} failed")
    return result.stdout


def _git_config(root: Path, key: str) -> str:
    try:
        return _git(root, "config", "--get", key).decode("utf-8", "surrogateescape").strip()
    except FreshnessError as error:
        # `git config --get` exits 1 for an unset value, which is the default
        # and therefore passes both preconditions.
        if error.git_missing:
            raise
        return ""


def is_governed_path(rel: str) -> bool:
    """Whether a POSIX-relative path belongs to the searchable corpus."""
    if rel == "AI_SYSTEM.md":
        return True
    if not rel or rel.startswith("/") or rel.startswith("../") or "/../" in rel:
        return False
    suffix = Path(rel).suffix
    if suffix in SEARCH_EXTENSIONS and any(rel.startswith(f"{root}/") for root in SEARCH_ROOTS):
        return True
    # Registered Markdown/YAML object forms may live outside the lexical
    # search roots (for example legacy Knowledge units).  Derived registry
    # bytes are excluded: canonical envelopes, not their export, govern trust.
    if suffix in _OBJECT_HANDLER_SUFFIXES and any(rel.startswith(root) for root in _OBJECT_ROOTS):
        return True
    return rel.startswith(".hydra-framework/engine/src/") and suffix == ".py"


def object_format(root: Path) -> str:
    """Return this repository's Git object hash algorithm."""
    algo = _git(root, "rev-parse", "--show-object-format").decode("ascii").strip()
    if algo not in {"sha1", "sha256"}:
        raise FreshnessError(f"unsupported Git object format: {algo}")
    return algo


def blob_id(data: bytes, algo: str) -> str:
    """Return Git's blob identity for *data*."""
    return hashlib.new(algo, b"blob %d\0" % len(data) + data).hexdigest()


def evaluate_guard(root: Path) -> GuardResult:
    """Check whether Git's worktree divergence reporting is trustworthy."""
    try:
        _git(root, "rev-parse", "--show-toplevel")
    except FreshnessError as error:
        return GuardResult(False, "git-unavailable" if error.git_missing else "not-a-git-worktree")

    try:
        if _git_config(root, "core.trustctime").lower() == "false":
            return GuardResult(False, "trustctime-disabled")
        if _git_config(root, "core.checkStat").lower() == "minimal":
            return GuardResult(False, "checkstat-minimal")
        for record in _git(root, "ls-files", "-v", "-z").split(b"\0"):
            if not record:
                continue
            tag = chr(record[0])
            path = os.fsdecode(record[2:])
            if is_governed_path(path):
                if tag.islower():
                    return GuardResult(False, "governed-path-assume-unchanged")
                if tag == "S":
                    return GuardResult(False, "governed-path-skip-worktree")
        for raw_path in _git(root, "ls-files", "-o", "-i", "--exclude-standard", "-z").split(b"\0"):
            if raw_path and is_governed_path(os.fsdecode(raw_path)):
                return GuardResult(False, "governed-path-ignored")
    except FreshnessError:
        # The worktree was valid when checked above.  A later Git failure is
        # still a refusal, never a potentially stale answer.
        return GuardResult(False, "not-a-git-worktree")
    return GuardResult(True, GUARD_OK)


def fingerprint(root: Path) -> dict[str, str]:
    """Map governed worktree paths to their current Git blob identities.

    D21 tried folding this into one `git ls-files -s -m -d -o` call (see the
    superseded parity test in `test_freshness.py` for the exact replacement
    that was measured). It was semantically correct -- parity held across
    the full mutation matrix -- but empirically slower, not faster: `-m`/`-d`
    detection inside `ls-files` does a brute-force per-path stat compare with
    none of `git status`'s untracked-cache/fsmonitor fast paths, so the
    combined single call cost about 2x the paired calls below on a 10k-file
    governed corpus (~55ms vs ~27ms, measured 2026-09-13). The task's own
    fallback for exactly this case ("if [it] cannot [win], retain the
    existing two-command implementation and land only D20") applies: this
    stays the two-call form, and only the call-COUNT reduction (D20, six
    calls to five per incremental operation) is landed.
    """
    algo = object_format(root)
    ids: dict[str, str] = {}
    unmerged: set[str] = set()
    for record in _git(root, "ls-files", "-s", "-z").split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            _mode, oid, raw_stage = metadata.split(b" ")
        except ValueError as error:
            raise FreshnessError("malformed git ls-files record") from error
        path = os.fsdecode(raw_path)
        if not is_governed_path(path):
            continue
        if raw_stage != b"0":
            unmerged.add(path)
        ids[path] = oid.decode("ascii")

    changed = set(unmerged)
    records = _git(root, "status", "--porcelain=v2", "--untracked-files=all", "-z").split(b"\0")
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        kind = record[:1]
        try:
            if kind == b"1":
                path = os.fsdecode(record.split(b" ", 8)[8])
            elif kind == b"2":
                path = os.fsdecode(record.split(b" ", 9)[9])
                if index >= len(records):
                    raise FreshnessError("rename record missing original path")
                index += 1  # The next NUL record is origPath, never a status record.
            elif kind == b"u":
                path = os.fsdecode(record.split(b" ", 10)[10])
            elif kind == b"?":
                path = os.fsdecode(record[2:])
            elif kind == b"!":
                continue
            else:
                raise FreshnessError("unknown git status record")
        except IndexError as error:
            raise FreshnessError("malformed git status record") from error
        if is_governed_path(path):
            changed.add(path)

    for path in changed:
        worktree_path = root / path
        try:
            if worktree_path.exists():
                ids[path] = blob_id(worktree_path.read_bytes(), algo)
            else:
                ids.pop(path, None)
        except OSError as error:
            raise FreshnessError(f"cannot read status-reported path: {path}") from error
    return ids


def fingerprint_digest(mapping: Mapping[str, str]) -> str:
    """One aggregate digest of a path-to-content-id fingerprint map.

    Two mappings with the same digest are the same set of (path, content_id)
    pairs. Used to prove a published index still matches the governed corpus
    from a single stored string, without re-reading every row that produced
    it (D9)."""
    canonical = "\n".join(f"{path}\0{content_id}" for path, content_id in sorted(mapping.items()))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def delta(old: Mapping[str, str], new: Mapping[str, str]) -> CorpusDelta:
    """Classify path-to-content-id changes between two corpus snapshots."""
    old_paths = set(old)
    new_paths = set(new)
    return CorpusDelta(
        added=tuple(sorted(new_paths - old_paths)),
        modified=tuple(sorted(path for path in old_paths & new_paths if old[path] != new[path])),
        deleted=tuple(sorted(old_paths - new_paths)),
    )


def resolve_source_path(raw: str, paths: ContextCompilerPaths) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return paths.root / raw


def valid_source_digest_entries(value: object) -> dict[str, str]:
    if not isinstance(value, (list, tuple)):
        return {}
    result: dict[str, str] = {}
    for entry in value:
        if not isinstance(entry, dict):
            continue
        source = entry.get("source")
        digest = entry.get("digest")
        if isinstance(source, str) and isinstance(digest, str):
            result[source] = digest
    return result


def stale_provenance_sources(
    provenance: Mapping[str, object],
    *,
    checked_on: str,
    paths: ContextCompilerPaths,
) -> list[str]:
    """Advisory stale source list for a unit provenance block.

    A source with a fingerprint compares file content. A source without one
    falls back to the existing date rule unchanged.
    """
    if not checked_on:
        return []
    stale: list[str] = []
    sources = yaml_list(provenance.get("sources"))
    digest_by_source = valid_source_digest_entries(provenance.get("source_digests"))
    for raw in sources:
        path = resolve_source_path(raw, paths)
        if raw in digest_by_source:
            if path.exists() and path.is_file() and normalized_digest(path) != digest_by_source[raw]:
                stale.append(raw)
            continue
        if not path.exists():
            continue
        commit_date = git_port.last_commit_iso(paths.root, raw)[:10]
        if commit_date and commit_date > checked_on:
            stale.append(raw)
    return stale
