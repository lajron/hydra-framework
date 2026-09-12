"""Capability-profile selection and metadata validation.

This module owns canonical capability selection before provider rendering.
It intentionally does not mutate provider surfaces or register CLI commands;
those operations belong to later migration phases.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

from hydra_engine.documents.tokens import HydraYamlError, display_path, read_text, write_text
from hydra_engine.finding import Finding
from hydra_engine.providers import capabilities
from hydra_engine.providers.capabilities import WRAPPER_PREFIX
from hydra_engine.providers.paths import ProvidersPaths

CAPABILITY_PROFILES_SCHEMA = "hydra-framework.capability-profiles.v1"
LOCAL_PROFILES_SCHEMA = "hydra-framework.local-capability-profiles.v1"
LOCAL_SELECTION_SCHEMA = "hydra-framework.local-capability-selection.v1"
TAG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


@dataclasses.dataclass(frozen=True)
class CapabilityProfile:
    """One named set of opaque tags used to select canonical skills."""

    name: str
    tags: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class CapabilitySelection:
    """Resolved skill directories and the deterministic reasons for each."""

    name: str
    effective_tags: tuple[str, ...]
    skills: tuple[Path, ...]
    reasons: dict[Path, tuple[str, ...]]


def _profiles_path(paths: ProvidersPaths) -> Path:
    return paths.hydra / "capabilities/profiles.yaml"


def _local_profiles_path(paths: ProvidersPaths) -> Path:
    return paths.root / ".hydra-framework.local/capabilities/profiles.yaml"


def _local_selection_path(paths: ProvidersPaths) -> Path:
    return paths.root / ".hydra-framework.local/capabilities/active.yaml"


def _skill_dirs(paths: ProvidersPaths) -> list[Path]:
    return sorted(path for path in paths.skills_root().glob("*") if (path / "skill.md").exists())


def _profiles(data: dict) -> dict[str, CapabilityProfile]:
    return {
        name: CapabilityProfile(name, tuple(sorted(set(capabilities.yaml_list(capabilities.yaml_map(raw).get("tags"))))))
        for name, raw in sorted(capabilities.yaml_map(data.get("profiles")).items())
        if isinstance(name, str)
    }


def resolve_capability_selection(paths: ProvidersPaths, name: str | None = None) -> CapabilitySelection:
    """Resolve the requested or checkout-default profile without mutation."""
    shared = capabilities.parse_yaml(_profiles_path(paths), paths.root, required=True)
    local = capabilities.parse_yaml(_local_profiles_path(paths), paths.root)
    active = capabilities.parse_yaml(_local_selection_path(paths), paths.root)
    selected_name = name or capabilities.yaml_str(active.get("active")) or capabilities.yaml_str(shared.get("default_profile"))
    shared_profiles = _profiles(shared)
    profiles = {**shared_profiles, **_profiles(local)}
    skill_dirs = _skill_dirs(paths)
    if selected_name == "full":
        reasons = {skill: ("full-profile",) for skill in skill_dirs}
        return CapabilitySelection("full", (), tuple(skill_dirs), reasons)
    profile = profiles.get(selected_name)
    if profile is None:
        raise HydraYamlError(f"capability profile `{selected_name}` is not defined")
    baseline = set(capabilities.yaml_list(shared.get("baseline_tags")))
    effective_tags = tuple(sorted(baseline | set(profile.tags)))
    reasons: dict[Path, tuple[str, ...]] = {}
    for skill in skill_dirs:
        tags = set(capabilities.yaml_list(capabilities.parse_yaml(skill / "metadata.yaml", paths.root).get("tags")))
        selected_reasons = {f"baseline-tag:{tag}" for tag in tags & baseline}
        selected_reasons.update(f"profile-tag:{tag}" for tag in tags & set(profile.tags))
        if selected_reasons:
            reasons[skill] = tuple(sorted(selected_reasons))
    return CapabilitySelection(selected_name, effective_tags, tuple(reasons), reasons)


def write_active_selection(paths: ProvidersPaths, name: str) -> None:
    """`profile select`'s one write: the machine-owned selection file.

    Never touches the hand-authored local `profiles.yaml` -- that file is
    read-only from Hydra's side, precisely so a person's comments and key
    order survive every `profile select`.
    """
    write_text(_local_selection_path(paths), f"schema: {LOCAL_SELECTION_SCHEMA}\nactive: {name}\n")


def capability_profiles(paths: ProvidersPaths) -> tuple[tuple[CapabilityProfile, str], ...]:
    """List available profiles, recording whether shared or local owns each name."""
    shared = capabilities.parse_yaml(_profiles_path(paths), paths.root, required=True)
    local = capabilities.parse_yaml(_local_profiles_path(paths), paths.root)
    shared_profiles = _profiles(shared)
    local_profiles = _profiles(local)
    names = sorted(set(shared_profiles) | set(local_profiles))
    return ((CapabilityProfile("full", ()), "built-in"),) + tuple(
        (local_profiles[name], "local; shadows shared" if name in shared_profiles else "local")
        if name in local_profiles else (shared_profiles[name], "shared")
        for name in names
    )


def _tag_findings(path: Path, root: Path, value: object, label: str) -> list[Finding]:
    if not isinstance(value, list):
        return [Finding(path=display_path(path, root), code="capability-profiles", detail=f"{label} must be a YAML list")]
    tags = [item for item in value if isinstance(item, str)]
    findings: list[Finding] = []
    if len(tags) != len(value):
        findings.append(Finding(path=display_path(path, root), code="capability-profiles", detail=f"{label} must contain strings"))
    if len(tags) != len(set(tags)):
        findings.append(Finding(path=display_path(path, root), code="capability-profiles", detail=f"{label} contains duplicate tags"))
    for tag in tags:
        if not TAG_RE.fullmatch(tag):
            findings.append(Finding(path=display_path(path, root), code="capability-profiles", detail=f"{label} has invalid tag `{tag}`"))
    return findings


def validate_capability_profiles(paths: ProvidersPaths) -> list[Finding]:
    """Validate profile policy plus skill metadata that narrowing relies on."""
    findings: list[Finding] = []
    profile_path = _profiles_path(paths)
    try:
        shared = capabilities.parse_yaml(profile_path, paths.root, required=True)
    except capabilities.HydraYamlError as error:
        return [Finding(path=display_path(profile_path, paths.root), code="capability-profiles", detail=str(error))]
    if capabilities.yaml_str(shared.get("schema")) != CAPABILITY_PROFILES_SCHEMA:
        findings.append(Finding(path=display_path(profile_path, paths.root), code="capability-profiles", detail=f"schema must be `{CAPABILITY_PROFILES_SCHEMA}`"))
    findings.extend(_tag_findings(profile_path, paths.root, shared.get("baseline_tags", []), "baseline_tags"))
    profiles = _profiles(shared)
    if "full" in profiles:
        findings.append(Finding(path=display_path(profile_path, paths.root), code="capability-profiles", detail="`full` is reserved and must not be declared"))
    for name, profile in profiles.items():
        if not TAG_RE.fullmatch(name):
            findings.append(Finding(path=display_path(profile_path, paths.root), code="capability-profiles", detail=f"invalid profile name `{name}`"))
        findings.extend(_tag_findings(profile_path, paths.root, capabilities.yaml_map(capabilities.yaml_map(shared.get("profiles")).get(name)).get("tags", []), f"profiles.{name}.tags"))
    default = capabilities.yaml_str(shared.get("default_profile"))
    if default != "full" and default not in profiles:
        findings.append(Finding(path=display_path(profile_path, paths.root), code="capability-profiles", detail=f"default_profile `{default}` is not defined"))

    skill_dirs = _skill_dirs(paths)
    skill_names = {path.name for path in skill_dirs}
    agent_dirs = sorted(path for path in paths.agents_root().glob("*") if (path / "agent.md").exists())
    for module_dir in skill_dirs + agent_dirs:
        metadata = capabilities.parse_yaml(module_dir / "metadata.yaml", paths.root)
        findings.extend(_tag_findings(module_dir / "metadata.yaml", paths.root, metadata.get("tags", []), "tags") if "tags" in metadata else [])
        for dependency in capabilities.yaml_list(capabilities.yaml_map(metadata.get("dependencies")).get("skills")):
            if dependency not in skill_names:
                findings.append(Finding(path=display_path(module_dir / "metadata.yaml", paths.root), code="capability-profiles", detail=f"declared skill dependency `{dependency}` does not exist"))

    wrapper_names = skill_names | {path.name for path in agent_dirs}
    pattern = re.compile(r"(?<!/)\b" + re.escape(WRAPPER_PREFIX) + r"(" + "|".join(re.escape(name) for name in sorted(wrapper_names)) + r")\b") if wrapper_names else None
    if pattern:
        for module_dir in skill_dirs + agent_dirs:
            body = module_dir / ("skill.md" if module_dir in skill_dirs else "agent.md")
            match = pattern.search(read_text(body))
            if match:
                findings.append(Finding(path=display_path(body, paths.root), code="capability-profiles", detail=f"canonical prose must not name wrapper `{WRAPPER_PREFIX}{match.group(1)}`"))
    return findings
