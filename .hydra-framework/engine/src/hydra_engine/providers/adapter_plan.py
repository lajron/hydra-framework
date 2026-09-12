"""The one planner every provider-surface command reads.

Reads `providers.capabilities.PROVIDERS` (the fourth extension
registry) rather than branching on provider slug: which renderer builds a
provider's agent wrapper is `Provider.build_agent_wrapper`, a field on the
registry entry, not an `if provider == "codex":` this planner used to carry.
"""

from __future__ import annotations

import contextlib
import dataclasses
from collections.abc import Iterable
from pathlib import Path

from hydra_engine.config import ConfigPaths, load_effective_config
from hydra_engine.documents.tokens import display_path, is_relative_to, write_text
from hydra_engine.ports import lock as lock_port
from hydra_engine.providers import capabilities
from hydra_engine.providers.capabilities import PROVIDERS, WRAPPER_PREFIX, build_skill_wrapper, capability_map
from hydra_engine.providers.paths import ProvidersPaths

ADAPTER_SIDECAR_SCHEMA = "hydra-framework.adapter.v2"

# Re-exported so callers (`commands.providers`, `providers.reclaim`) can
# catch it alongside `HydraYamlError`/`ConfigError` with no import edge of
# their own; it subclasses `HydraYamlError` for exactly that reason.
LockUnavailableError = lock_port.LockUnavailableError


def ownership_paths(paths: ProvidersPaths) -> frozenset[Path]:
    """Every adapter path canonical sources can own, without rendered bytes."""
    owned: set[Path] = set()
    skill_dirs = sorted(path for path in paths.skills_root().glob("*") if (path / "skill.md").exists())
    agent_dirs = sorted(path for path in paths.agents_root().glob("*") if (path / "agent.md").exists())
    for provider in PROVIDERS:
        for skill_dir in skill_dirs:
            name = capability_map_name(skill_dir, paths.root)
            wrapper = paths.root / provider.skills_target / f"{WRAPPER_PREFIX}{name}"
            owned.update({wrapper / "SKILL.md", wrapper / ".hydra-adapter.yaml"})
        if provider.agents_target is None or provider.agent_extension is None:
            continue
        for agent_dir in agent_dirs:
            name = capability_map_name(agent_dir, paths.root)
            wrapper_name = f"{WRAPPER_PREFIX}{name}"
            wrapper = paths.root / provider.agents_target / f"{wrapper_name}{provider.agent_extension}"
            owned.update({wrapper, wrapper.parent / f".hydra-adapter-{wrapper_name}.yaml"})
    return frozenset(owned)


def capability_map_name(module_dir: Path, root: Path) -> str:
    """The canonical name shared by byte planning and ownership identity."""
    return capabilities.yaml_str(capabilities.parse_yaml(module_dir / "metadata.yaml", root).get("name"), module_dir.name)


def planned_adapter_files(paths: ProvidersPaths, selection: Iterable[Path] | None = None) -> dict[Path, str]:
    """Every provider file that export-adapters owns, mapped to its content.

    One planner drives generate, dry-run, drift-check, and orphan detection, so
    those four can never disagree about what is generated.
    """
    plan: dict[Path, str] = {}
    skill_dirs = sorted(
        path for path in paths.skills_root().glob("*") if (path / "skill.md").exists()
    )
    if selection is not None:
        selected = set(selection)
        skill_dirs = [path for path in skill_dirs if path in selected]
    agent_dirs = sorted(
        path for path in paths.agents_root().glob("*") if (path / "agent.md").exists()
    )
    config = load_effective_config(ConfigPaths(root=paths.root, hydra=paths.hydra, local=paths.root / ".hydra-framework.local"))

    for provider in PROVIDERS:
        mapping = capability_map(paths, provider.slug)
        for skill_dir in skill_dirs:
            wrapper_name, files = build_skill_wrapper(skill_dir, provider.slug, paths.root)
            for filename, content in files.items():
                plan[paths.root / provider.skills_target / wrapper_name / filename] = content
        if provider.agents_target is None:
            continue
        for agent_dir in agent_dirs:
            wrapper_name, files = provider.build_agent_wrapper(agent_dir, provider.slug, mapping, paths.root, config)
            for filename, content in files.items():
                plan[paths.root / provider.agents_target / filename] = content
    return plan


def path_is_contained(target: Path, root: Path) -> bool:
    """Whether `target` may be created, updated, or removed under `root`.

    Applies to every mutation, not only removal: `documents.tokens.write_text`
    follows a symlink, so a symlinked wrapper directory, body, or provider
    target could redirect a create or update outside the repository just as
    easily as a delete could escape through one.

    Refuses when the resolved location is not under `root`, when any path
    component up to and including `target` itself is a symlink (so a
    symlinked wrapper is never followed or written through), or when
    resolution otherwise fails.
    """
    try:
        relative = target.relative_to(root)
    except ValueError:
        return False
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return False
    try:
        resolved_target = target.resolve()
        resolved_root = root.resolve()
    except OSError:
        return False
    return is_relative_to(resolved_target, resolved_root)


@dataclasses.dataclass(frozen=True)
class RemovableUnit:
    """One atomic wrapper unit safe to delete, whole, never partially."""

    kind: str
    members: tuple[Path, ...]
    directory: Path | None


@dataclasses.dataclass(frozen=True)
class ReconcilePlan:
    """The one plan `export-adapters`' `--check`, `--dry-run`, real run, and
    `profile select`'s step 2 all read, so they can never disagree about
    what would happen. `abort_reason` set means no mutation may proceed."""

    contents: dict[Path, str]
    created: tuple[Path, ...]
    changed: tuple[Path, ...]
    removable: tuple[RemovableUnit, ...]
    kept: tuple[tuple[str, str], ...]
    abort_reason: str | None


def _sidecar_agrees(sidecar: Path, provider_slug: str, kind: str, root: Path) -> tuple[bool, str]:
    """Condition 4: the adjacent sidecar parses as a supported adapter schema
    and agrees on `provider`/`kind`. Returns its declared `canonical_source`
    on success, so the caller does not re-open and re-parse the file."""
    if not sidecar.is_file():
        return False, ""
    try:
        data = capabilities.parse_yaml(sidecar, root)
    except capabilities.HydraYamlError:
        return False, ""
    if data.get("schema") != ADAPTER_SIDECAR_SCHEMA:
        return False, ""
    if capabilities.yaml_str(data.get("provider")) != provider_slug or capabilities.yaml_str(data.get("kind")) != kind:
        return False, ""
    return True, capabilities.yaml_str(data.get("canonical_source"))


def _valid_canonical_source(raw: str, kind: str, paths: ProvidersPaths) -> bool:
    """Condition 5: `canonical_source` resolves under
    `capabilities/skills/<slug>/skill.md` or `capabilities/agents/<slug>/agent.md`,
    contains no `..`, and the file exists."""
    if not raw or ".." in Path(raw).parts or Path(raw).is_absolute():
        return False
    target = paths.root / raw
    if not path_is_contained(target, paths.root):
        return False
    canonical_root = paths.skills_root() if kind == "skill" else paths.agents_root()
    body_name = "skill.md" if kind == "skill" else "agent.md"
    if not is_relative_to(target, canonical_root):
        return False
    rel = target.relative_to(canonical_root)
    return len(rel.parts) == 2 and rel.parts[1] == body_name and target.is_file()


def candidate_removals(
    paths: ProvidersPaths, ownership: frozenset[Path], desired: dict[Path, str]
) -> tuple[list[RemovableUnit], list[tuple[str, str]]]:
    """Owned paths no longer desired, grouped into atomic wrapper units and
    checked against the six ownership conditions from the private plan's
    "What Hydra owns". Conditions 1 (membership) and 3 (the wrapper directory
    is named exactly for the canonical skill) are enforced by `ownership`
    itself: `ownership_paths()` only ever contains a wrapper path derived
    from a currently-existing canonical source, so a hand-renamed or
    hand-named wrapper directory never appears in it at all -- it is simply
    absent, which is what keeps a rename safe without a separate check here.
    Conditions 2, 4, 5, and 6 are checked below against the real files.

    Only skill wrappers are considered: agents are never filtered by profile
    (`planned_adapter_files` never excludes an agent), so an agent path can
    only leave `ownership - desired` when its canonical agent itself is
    deleted -- at which point it also leaves `ownership`, and is report-only
    `stale` via `reclaim.classify_surfaces`, the same as a deleted skill.
    """
    removable: list[RemovableUnit] = []
    kept: list[tuple[str, str]] = []
    stale = {path for path in ownership if path not in desired}

    for provider in PROVIDERS:
        skills_root = paths.root / provider.skills_target
        wrapper_dirs = sorted({
            path.parent for path in stale
            if path.name == "SKILL.md" and is_relative_to(path, skills_root)
        })
        for wrapper_dir in wrapper_dirs:
            if not wrapper_dir.is_dir():
                # Owned in identity only: this skill was never materialized
                # under this name (deselected before its first export, or
                # already removed), so there is nothing here to remove.
                continue
            body = wrapper_dir / "SKILL.md"
            sidecar = wrapper_dir / ".hydra-adapter.yaml"
            label = f"{display_path(wrapper_dir, paths.root)}/"
            if not (
                path_is_contained(wrapper_dir, paths.root)
                and path_is_contained(body, paths.root)
                and path_is_contained(sidecar, paths.root)
            ):
                kept.append((label, "containment check failed; not removed"))
                continue
            present = sorted(item.name for item in wrapper_dir.iterdir())
            if present != [".hydra-adapter.yaml", "SKILL.md"]:
                kept.append((label, f"directory holds files Hydra did not generate ({', '.join(present)}); not removed"))
                continue
            ok, canonical = _sidecar_agrees(sidecar, provider.slug, "skill", paths.root)
            if not ok:
                kept.append((label, "sidecar is malformed or disagrees on provider/kind; not removed"))
                continue
            if not _valid_canonical_source(canonical, "skill", paths):
                kept.append((label, "canonical_source is not a valid skill reference; not removed"))
                continue
            removable.append(RemovableUnit(kind="skill", members=(body, sidecar), directory=wrapper_dir))

    return removable, kept


def apply_reconcile_plan(plan: ReconcilePlan) -> None:
    """Apply a plan with no `abort_reason`: create, update, then remove whole
    units. Callers hold `acquire_export_lock` across planning and this call."""
    for path in plan.created + plan.changed:
        write_text(path, plan.contents[path])
    for unit in plan.removable:
        for member in unit.members:
            member.unlink(missing_ok=True)
        if unit.directory is not None:
            with contextlib.suppress(OSError):
                unit.directory.rmdir()


def acquire_export_lock(paths: ProvidersPaths):
    """The one per-checkout lock guarding every `export-adapters`/`profile
    select` mutation. Read-only operations (`--check`, `--dry-run`, `profile
    show`) never call this."""
    return lock_port.acquire(paths.root / ".hydra-framework.local/locks/export.lock")
