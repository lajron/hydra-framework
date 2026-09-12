"""Bootstrap helpers for Hydra's untracked private tier."""

from __future__ import annotations

import dataclasses
import subprocess
from pathlib import Path

from hydra_engine.documents.tokens import read_text, write_text
from hydra_engine.installation.private_tier_templates import (
    AREA_README,
    DEVELOPER_PREFERENCES_STUB,
    MACHINE_PROFILE_STUB,
    TOKEN_USAGE_TEMPLATE,
    TOP_LEVEL_README,
)

GITIGNORE_RULE = ".hydra-framework.local/"
GITIGNORE_BLOCK_HEADER = "# Hydra private local state"
GITIGNORE_BLOCK = f"{GITIGNORE_BLOCK_HEADER}\n{GITIGNORE_RULE}\n"


@dataclasses.dataclass(frozen=True)
class SeedArea:
    path: str
    purpose: str
    kind: str


PRIVATE_TIER_SEED: list[SeedArea] = [
    SeedArea("notes", "Free-form thinking. `hydra.py note \"Some Title\"` creates a dated titled note; stdin-only input appends to today's scratch note.", "machine"),
    SeedArea("intake/raw", "Source descriptors and safe source copies awaiting processing.", "machine"),
    SeedArea("intake/extracted", "Text, links, parsed metadata, and other source-derived artifacts.", "machine"),
    SeedArea("intake/triage", "Staging notes deciding what is useful, duplicated, unclear, or promotable.", "machine"),
    SeedArea("monitoring", "Private token, retry, loop-halt, and cost observations.", "machine"),
    SeedArea("index", "Rebuildable private search and retrieval indexes.", "machine"),
    SeedArea("logs", "Private execution logs kept out of shared history.", "machine"),
    SeedArea("baseline", "Private baseline snapshots and local comparison state.", "machine"),
    SeedArea("tasks/retired", "Finished records Git never tracked, kept because nothing else holds them.", "machine"),
    SeedArea("migrations", "Originals drained from a source area.", "machine"),
    SeedArea("evolution/experiments", "Framework trials that have not earned a candidate yet.", "machine"),
    SeedArea("scratch", "Half-formed work, temporary calculations, and quick throwaways.", "thinking"),
    SeedArea("plans", "Private planning before the useful result becomes a task record or shared doc.", "thinking"),
    SeedArea("research", "Private research notes and checked-but-not-promoted findings.", "thinking"),
    SeedArea("prompts", "Prompt drafts, comparisons, and local prompt experiments.", "thinking"),
    SeedArea("diagrams", "Private sketches and diagrams before they become durable documentation.", "thinking"),
    SeedArea("source-material", "Local source material that should not be committed as an archive.", "thinking"),
    SeedArea("tickets", "Private ticket notes, triage, and issue-system drafts.", "thinking"),
    SeedArea("bug-reports", "Private bug reproduction notes and report drafts.", "thinking"),
    SeedArea("developer", "Personal workflow preferences.", "config"),
    SeedArea("machine", "Operating system, capabilities, and local tool mappings.", "config"),
    SeedArea("repo-overrides", "Repository-specific private overrides.", "config"),
    SeedArea("secrets", "Credentials or secret references.", "config"),
    SeedArea("locks", "The per-checkout export lock guarding `export-adapters`/`profile select`.", "machine"),
    SeedArea("capabilities", "The local capability-profile policy (`profiles.yaml`) and machine-owned selection (`active.yaml`).", "config"),
]


def _gitignore_rule_present(text: str) -> bool:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.lstrip("/") in {".hydra-framework.local", ".hydra-framework.local/"}:
            return True
    return False


def gitignore_rule_present(root: Path) -> bool:
    gitignore = root / ".gitignore"
    return gitignore.exists() and _gitignore_rule_present(read_text(gitignore))


def ensure_gitignore_rule(root: Path) -> str:
    """Ensure the private tier is ignored by Git."""
    gitignore = root / ".gitignore"
    text = read_text(gitignore) if gitignore.exists() else ""
    if _gitignore_rule_present(text):
        return "already-present"

    prefix = "" if not text else "\n" if text.endswith("\n") else "\n\n"
    write_text(gitignore, f"{text}{prefix}{GITIGNORE_BLOCK}")
    return "added"


def private_tier_ignored(root: Path) -> bool:
    """Return whether Git ignores a probe path beneath the private tier."""
    probe = f"{GITIGNORE_RULE}.hydra-ignore-probe"
    result = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "--quiet", "--", probe],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def private_tier_report(root: Path, local: Path) -> dict:
    missing_seeded_areas = [
        f"{GITIGNORE_RULE}{area.path}/"
        for area in PRIVATE_TIER_SEED
        if not (local / area.path).is_dir()
    ]
    return {
        "gitignore_rule_present": gitignore_rule_present(root),
        "ignored": private_tier_ignored(root),
        "directory_exists": local.is_dir(),
        "seeded_areas_present": not missing_seeded_areas,
        "missing_seeded_areas": missing_seeded_areas,
    }


def _seed_files() -> dict[str, str]:
    local_rel = GITIGNORE_RULE.rstrip("/")
    files = {f"{local_rel}/README.md": TOP_LEVEL_README}
    for area in PRIVATE_TIER_SEED:
        files[f"{local_rel}/{area.path}/README.md"] = AREA_README[area.path]
    files.update({
        f"{local_rel}/monitoring/token-usage.md": TOKEN_USAGE_TEMPLATE,
        f"{local_rel}/developer/preferences.md": DEVELOPER_PREFERENCES_STUB,
        f"{local_rel}/machine/profile.yaml": MACHINE_PROFILE_STUB,
    })
    return files


def ensure_private_tier(root: Path, local: Path) -> dict[str, list[str]]:
    """Create missing private-tier areas and seed missing files without overwriting."""
    created: list[str] = []
    existing: list[str] = []
    seeded: list[str] = []

    for directory in [local] + [local / area.path for area in PRIVATE_TIER_SEED]:
        rel = directory.relative_to(root).as_posix()
        if directory.exists():
            existing.append(rel)
        else:
            directory.mkdir(parents=True, exist_ok=True)
            created.append(rel)

    for rel, content in _seed_files().items():
        path = root / rel
        if path.exists():
            continue
        write_text(path, content)
        seeded.append(rel)

    return {"created": created, "existing": existing, "seeded": seeded}
