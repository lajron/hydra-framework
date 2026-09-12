"""Read-only takeover candidate scan."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from hydra_engine.documents.tokens import display_path
from hydra_engine.intake.classification import classify_migration_file, read_migration_file_peek
from hydra_engine.identity.slugs import slugify
from hydra_engine.ports import git as git_port
from hydra_engine.providers.paths import ProvidersPaths
from hydra_engine.providers.reclaim import classify_surfaces

TAKEOVER_SCAN_SCHEMA = "hydra-framework.takeover-scan.v1"

TAKEOVER_MARKERS: tuple[tuple[str, str], ...] = (
    (".claude", "claude"),
    ("CLAUDE.md", "claude"),
    (".codex", "codex"),
    (".agents", "codex"),
    ("AGENTS.md", "codex"),
    (".cursor", "cursor"),
    (".cursorrules", "cursor"),
    (".windsurf", "windsurf"),
    (".windsurfrules", "windsurf"),
    (".github/copilot-instructions.md", "copilot"),
    ("prompts", "prompts"),
    ("docs/ai", "docs"),
    ("docs/agents", "docs"),
)

PROVIDER_ROOTS = {".claude", ".codex", ".agents", ".cursor", ".windsurf"}
HYDRA_ENTRYPOINTS = {"AGENTS.md", "CLAUDE.md"}
HYDRA_ENTRYPOINT_CONTENTS = {
    "AGENTS.md": {
        "# shared agent instructions\n\nread [`ai_system.md`](ai_system.md) first.",
        "this repository uses hydra.\nsee `.hydra-framework/`.",
    },
    "CLAUDE.md": {
        "@agents.md\n\nclaude-specific path-scoped rules live in `.claude/rules/`; generated skills and\nagents come from `.hydra-framework/capabilities/`.",
        "@agents.md\n\ngenerated skills come from `.hydra-framework/capabilities/`.",
    },
}
RISK_TAGS = {"credential-or-private-risk", "machine-local-risk", "private-hydra-risk"}
OWNER_DECISION_NAMES = {
    "settings.json",
    "settings.local.json",
    "config.json",
    "config.toml",
    "hooks.json",
    "scheduled_tasks.lock",
}
OWNER_DECISION_PARTS = {"rules", "hooks"}
IGNORED_SCAN_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}


def _candidate_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    files: list[Path] = []
    for item in sorted(path.rglob("*")):
        if any(part in IGNORED_SCAN_DIRS for part in item.relative_to(path).parts):
            continue
        if item.is_file():
            files.append(item)
    return files


def _is_hydra_entrypoint(path: Path) -> bool:
    text = read_migration_file_peek(path).replace("\r\n", "\n").strip().lower()
    return text in HYDRA_ENTRYPOINT_CONTENTS.get(path.name, set())


def _has_hydra_entrypoint_marker(path: Path) -> bool:
    text = read_migration_file_peek(path).lower()
    if path.name == "AGENTS.md":
        return (
            "this repository uses hydra" in text and ".hydra-framework/" in text
        ) or "read [`ai_system.md`](ai_system.md) first." in text
    if path.name == "CLAUDE.md":
        return "@agents.md" in text and ".hydra-framework/" in text
    return False


def _under(rel: str, root_rel: str) -> bool:
    return rel == root_rel or rel.startswith(f"{root_rel}/")


def _provider_surface_counts(surfaces: list[dict[str, str]], root_rel: str) -> dict[str, int]:
    counts = Counter(item["status"] for item in surfaces if _under(item["path"], root_rel))
    return dict(sorted(counts.items()))


def _provider_surface_items(surfaces: list[dict[str, str]], root_rel: str) -> list[dict[str, str]]:
    return [item for item in surfaces if _under(item["path"], root_rel)]


def _needs_owner_decision(root_rel: str, files: list[Path], root: Path) -> bool:
    for file_path in files:
        rel = display_path(file_path, root)
        parts = Path(rel).parts
        if file_path.name in OWNER_DECISION_NAMES:
            return True
        if any(part in OWNER_DECISION_PARTS for part in parts):
            return True
        if root_rel in {".cursor", ".windsurf"}:
            return False
    return False


def _candidate_classification(
    marker: str,
    candidate: Path,
    root: Path,
    files: list[Path],
    tag_counts: dict[str, int],
    surface_counts: dict[str, int],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    unmanaged = sum(surface_counts.get(status, 0) for status in ("orphaned", "drifted", "stale"))
    if marker in HYDRA_ENTRYPOINTS and _is_hydra_entrypoint(candidate):
        return "hydra-owned", ["thin Hydra provider entrypoint"]
    if tag_counts.keys() & RISK_TAGS:
        reasons.append("risk-classified material needs owner review")
        return "needs-owner-decision", reasons
    if unmanaged:
        reasons.append("provider reclaim reports unmanaged surface files")
        return "provider-native", reasons
    if marker in HYDRA_ENTRYPOINTS:
        if _has_hydra_entrypoint_marker(candidate):
            return "needs-owner-decision", ["Hydra entrypoint markers are mixed with unrecognized instructions"]
        return "foreign-entrypoint", ["root AI rule file is not a thin Hydra adapter"]
    if marker in {".cursorrules", ".windsurfrules", ".github/copilot-instructions.md", "docs/ai", "docs/agents"}:
        return "foreign-entrypoint", ["foreign AI instruction or documentation marker"]
    if marker == "prompts":
        return "needs-owner-decision", ["top-level prompt library needs owner review"]
    if marker in PROVIDER_ROOTS and _needs_owner_decision(marker, files, root):
        return "needs-owner-decision", ["settings, hooks, rules, or local config need owner review"]
    if surface_counts.get("generated", 0):
        return "hydra-owned", ["provider reclaim reports generated current surfaces"]
    if marker in PROVIDER_ROOTS:
        return "provider-native", ["provider directory is outside Hydra's generated adapter plan"]
    return "needs-owner-decision", ["ownership cannot be decided by marker shape alone"]


def _staging_recommendation(slug: str, classification: str, git_state: dict) -> dict[str, str]:
    if classification == "hydra-owned":
        return {
            "route": "do-not-stage",
            "path": "",
            "reason": "Hydra already owns this surface through canonical .hydra-framework state.",
        }
    if classification == "needs-owner-decision":
        return {
            "route": "confirm-owner",
            "path": "",
            "reason": "Ownership or privacy cannot be decided mechanically.",
        }
    if git_state["ignored_files"] or git_state["tracked_files"] == 0:
        return {
            "route": "private-staging",
            "path": f".hydra-framework.local/migrations/{slug}/originals/",
            "reason": "Material is ignored or never tracked, so Git does not own the undo.",
        }
    if git_state["untracked_files"]:
        return {
            "route": "confirm-owner",
            "path": "",
            "reason": "Tracked and untracked files are mixed under this root.",
        }
    return {
        "route": "shared-staging",
        "path": f".migrations/{slug}/",
        "reason": "All files under this root are already tracked by Git.",
    }


def _git_state(root: Path, candidate: Path, files: list[Path]) -> dict:
    rel = display_path(candidate, root)
    tracked = set(git_port.tracked_files(root, rel))
    ignored: list[dict[str, str]] = []
    tracked_count = 0
    for file_path in files:
        file_rel = display_path(file_path, root)
        if file_rel in tracked:
            tracked_count += 1
        match = git_port.ignore_match(root, file_rel)
        if match:
            ignored.append({"path": file_rel, "rule": match})
    root_match = git_port.ignore_match(root, rel)
    return {
        "tracked_files": tracked_count,
        "untracked_files": max(len(files) - tracked_count, 0),
        "ignored_files": len(ignored),
        "ignored": bool(root_match or ignored),
        "ignore_rule": root_match,
        "ignored_examples": ignored[:5],
    }


def _candidate(root: Path, marker: str, source: str, surfaces: list[dict[str, str]]) -> dict:
    path = root / marker
    files = _candidate_files(path)
    rel = display_path(path, root)
    tag_counts: Counter[str] = Counter()
    findings = []
    for file_path in files:
        tags = classify_migration_file(file_path, path if path.is_dir() else path.parent)
        tag_counts.update(tags)
        findings.append({"path": display_path(file_path, root), "classifications": tags})
    surface_counts = _provider_surface_counts(surfaces, rel)
    classification, reasons = _candidate_classification(marker, path, root, files, dict(tag_counts), surface_counts)
    git_state = _git_state(root, path, files)
    slug = slugify(marker.replace("/", "-").removeprefix(".") or source)
    return {
        "path": rel,
        "source": source,
        "kind": "directory" if path.is_dir() else "file",
        "classification": classification,
        "reasons": reasons,
        "slug": slug,
        "files": len(files),
        "classifications": dict(sorted(tag_counts.items())),
        "findings": sorted(findings, key=lambda item: item["path"]),
        "git": git_state,
        "provider_surfaces": _provider_surface_items(surfaces, rel),
        "provider_surface_counts": surface_counts,
        "staging": _staging_recommendation(slug, classification, git_state),
    }


def takeover_scan(root: Path) -> dict:
    root = root.resolve()
    report = {
        "schema": TAKEOVER_SCAN_SCHEMA,
        "root": display_path(root, root),
        "exists": root.is_dir(),
        "candidates": [],
        "totals": {"candidates": 0, "files": 0},
        "notes": [
            "read-only scan; no files are staged, moved, promoted, or rewritten",
            "confirm scope before moving any candidate root into migration staging",
        ],
    }
    if not root.is_dir():
        report["notes"].append("root does not exist or is not a directory")
        return report

    surfaces = classify_surfaces(ProvidersPaths(root=root, hydra=root / ".hydra-framework"))
    seen: set[str] = set()
    for marker, source in TAKEOVER_MARKERS:
        path = root / marker
        if not path.exists():
            continue
        rel = display_path(path, root)
        if rel in seen:
            continue
        seen.add(rel)
        item = _candidate(root, marker, source, surfaces)
        report["candidates"].append(item)
        report["totals"]["files"] += item["files"]
    report["totals"]["candidates"] = len(report["candidates"])
    if not report["candidates"]:
        report["notes"].append("no common AI architecture markers found")
    return report
