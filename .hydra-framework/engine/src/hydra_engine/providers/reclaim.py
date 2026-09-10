"""Provider-native file classification, promotion, and edit-time notice.

`provider_surface_notice` lives here rather than a separate `notices.py` --
see this package's `__init__.py` docstring for why.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from hydra_engine.documents.tokens import HydraYamlError, display_path, is_relative_to, read_text, write_text, yaml_scalar
from hydra_engine.documents.yaml_documents import parse_yaml, yaml_str
from hydra_engine.identity.slugs import slugify
from hydra_engine.ports import clock as clock_port
from hydra_engine.providers.adapter_plan import planned_adapter_files
from hydra_engine.providers.paths import ProvidersPaths

# Files a provider directory may contain without being an adapter over Hydra.
SURFACE_IGNORED_NAMES = {"README.md", "settings.json", "settings.local.json", ".gitkeep"}

# Provider-native artifact locations, and the canonical Hydra module each maps
# onto when a hand-authored file has to be promoted.
RECLAIM_SURFACES = [
    (".claude/skills", "skill", "capabilities/skills"),
    (".claude/agents", "agent", "capabilities/agents"),
    (".claude/commands", "legacy-command", "capabilities/skills"),
    (".agents/skills", "skill", "capabilities/skills"),
    (".codex/skills", "skill", "capabilities/skills"),
    (".codex/agents", "agent", "capabilities/agents"),
]


def canonical_source_of(sidecar: Path, root: Path) -> str:
    if not sidecar.exists():
        return ""
    try:
        return yaml_str(parse_yaml(sidecar, root).get("canonical_source"))
    except HydraYamlError:
        return ""


def sidecar_for(path: Path, kind: str) -> Path:
    if kind == "agent":
        return path.parent / f".hydra-adapter-{path.stem}.yaml"
    return path.parent / ".hydra-adapter.yaml"


def classify_surfaces(paths: ProvidersPaths) -> list[dict[str, str]]:
    """Classify every provider-native file against what Hydra generates.

    This is what catches a teammate hand-writing `.claude/skills/deploy/SKILL.md`:
    it has no canonical source, so it reports as `orphaned` with the Hydra path it
    should become.
    """
    try:
        plan = planned_adapter_files(paths)
    except HydraYamlError:
        plan = {}

    results: list[dict[str, str]] = []
    for surface, kind, canonical_dir in RECLAIM_SURFACES:
        root = paths.root / surface
        if not root.exists():
            continue
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            if path.name in SURFACE_IGNORED_NAMES:
                continue
            if path.name.startswith(".hydra-adapter"):
                continue
            if path.suffix not in {".md", ".toml"}:
                continue
            rel = display_path(path, paths.root)
            sidecar = sidecar_for(path, kind)
            canonical = canonical_source_of(sidecar, paths.root)
            if canonical:
                if not (paths.root / canonical).exists():
                    status = "stale"
                    detail = f"canonical source is gone: {canonical}"
                elif path in plan and read_text(path) != plan[path]:
                    status = "drifted"
                    detail = f"edited wrapper; canonical source is {canonical}"
                elif path in plan:
                    status = "generated"
                    detail = canonical
                else:
                    status = "stale"
                    detail = f"no longer generated; canonical source is {canonical}"
            else:
                status = "orphaned"
                slug = slugify(path.parent.name if path.name == "SKILL.md" else path.stem)
                slug = re.sub(r"^hydra-", "", slug)
                suggested = f".hydra-framework/{canonical_dir}/{slug}/"
                suggested += "agent.md" if kind == "agent" else "skill.md"
                detail = f"hand-authored {kind}; promote to {suggested}"
            results.append({"path": rel, "status": status, "kind": kind, "detail": detail})
    return results


def promote_surface(paths: ProvidersPaths, item: dict[str, str]) -> Path | None:
    """Move a hand-authored provider file into canonical Hydra."""
    source = paths.root / item["path"]
    if not source.exists():
        return None
    kind = item["kind"]
    slug = slugify(source.parent.name if source.name == "SKILL.md" else source.stem)
    slug = re.sub(r"^hydra-", "", slug)
    target_dir = paths.canonical_module_dir(kind) / slug
    body_name = "agent.md" if kind == "agent" else "skill.md"
    target = target_dir / body_name
    if target.exists():
        metadata_path = target_dir / "metadata.yaml"
        try:
            promoted_from = yaml_str(parse_yaml(metadata_path, paths.root).get("promoted_from"))
        except HydraYamlError:
            promoted_from = ""
        if promoted_from == item["path"]:
            source.unlink()
            return target
        return None

    text = read_text(source)
    front: dict[str, str] = {}
    body = text
    if source.suffix == ".toml" and kind == "agent":
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError:
            data = {}
        front = {key: str(value) for key, value in data.items() if isinstance(value, str)}
        body = front.get("developer_instructions", text)
    elif text.startswith("---\n"):
        _, _, rest = text.partition("---\n")
        raw_front, separator, remainder = rest.partition("\n---")
        if separator:
            for line in raw_front.splitlines():
                if ":" in line and not line.startswith(" "):
                    key, _, value = line.partition(":")
                    front[key.strip()] = yaml_scalar(value)
            body = remainder.lstrip("\n").lstrip("-").lstrip("\n")

    description = front.get("description", f"Promoted from {item['path']}.")
    schema = "hydra-framework.agent.v2" if kind == "agent" else "hydra-framework.skill.v2"
    metadata = [f"schema: {schema}"]
    if kind != "agent":
        metadata.append("kind: procedure")
    metadata.extend([
        f"name: {slug}",
        f"description: {description}",
        "scope: repo-local",
        "maturity: promoted",
        f"promoted_from: {item['path']}",
        f"promoted_date: {clock_port.today()}",
        "certainty: inferred",
    ])
    if kind == "agent":
        metadata.extend(["capability_class: fast-default", "effort: standard"])
        tools = front.get("tools", "")
        if tools:
            metadata.append("tools:")
            metadata.extend(f"  - {part.strip()}" for part in tools.split(",") if part.strip())
    write_text(target, body if body.endswith("\n") else f"{body}\n")
    write_text(target_dir / "metadata.yaml", "\n".join(metadata) + "\n")
    source.unlink()
    return target


def provider_surface_notice(paths: ProvidersPaths, edited: Path) -> list[str]:
    """Advisory lines when a write lands on a provider file Hydra does not own.

    Returns an empty list for anything clean, so the hook stays silent on the
    normal path. This is guidance, not enforcement: it never blocks the write.
    """
    if not is_relative_to(edited, paths.root):
        return []
    rel = edited.relative_to(paths.root).as_posix()
    if not any(rel.startswith(f"{surface}/") for surface, _kind, _dir in RECLAIM_SURFACES):
        return []
    if edited.name in SURFACE_IGNORED_NAMES:
        return []

    for item in classify_surfaces(paths):
        if item["path"] != rel:
            continue
        if item["status"] == "generated":
            return []
        if item["status"] == "orphaned":
            return [
                f"Hydra: `{rel}` is a provider-native file with no canonical Hydra source.",
                f"  {item['detail']}",
                "  Provider directories are generated adapters. Move the meaning into",
                "  `.hydra-framework/`, then run `hydra.py export-adapters`.",
                "  Mechanical path: `hydra.py reclaim --promote`.",
            ]
        if item["status"] == "drifted":
            return [
                f"Hydra: `{rel}` is generated, and this edit diverges from its canonical source.",
                f"  {item['detail']}",
                "  Edit the canonical file instead; `hydra.py export-adapters` will overwrite this.",
            ]
        return [
            f"Hydra: `{rel}` is stale. {item['detail']}",
            "  Delete the wrapper or restore its canonical source.",
        ]
    return []
