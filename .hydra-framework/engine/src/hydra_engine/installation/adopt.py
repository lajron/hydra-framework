"""Adoption report and lineage recording.

Returns data; `commands.installation` renders it to text, per Target
Structure rule 2. `PROVIDERS` (the provider registry, `ADAPTER_TARGETS`
as it was named before that registry existed) is reused from
`providers.capabilities` rather than duplicated: `command_adopt` was the sole
remaining `hydra.py` caller of its own copy, so that copy is deleted outright
rather than kept as an unused duplicate.

`manifest` (the already-parsed `manifest.yaml` dict) is a parameter here
rather than parsed by this module: importing `documents.yaml_documents` for
`parse_yaml` would have pushed that module's in-degree from 10 to 11,
tripping check 4 (the same kind of interaction the
`capabilities.py`/`wrappers.py` merge hit). `hydra.py`'s own `parse_yaml()`
wrapper computes it once; this module never imports `yaml_documents` itself,
and its two trivial value-coercion needs (`yaml_map`/`yaml_str`'s shape) are
reimplemented locally rather than pulled in for that alone.

`InstallationPaths`/`ProvidersPaths`/`ContextCompilerPaths` are bare
forward-reference type hints here (no real import): this module only calls
methods on already-constructed instances and never builds or introspects one
itself, matching the codebase-wide convention already established for
`ObjectLocations` elsewhere.
"""

from __future__ import annotations

from hydra_engine.documents.tokens import read_text, write_text
from hydra_engine.identity.slugs import slugify
from hydra_engine.installation.host_detection import detect_host_repo
from hydra_engine.installation.private_tier import private_tier_report
from hydra_engine.knowledge.nodes import discover_knowledge_nodes
from hydra_engine.ports import clock as clock_port
from hydra_engine.providers.capabilities import PROVIDERS
from hydra_engine.providers.reclaim import classify_surfaces

# `hydra.py` keeps its own copy for `command_doctor`, which does not move
# this cluster; duplicated here rather than passed as a parameter, matching
# the established `hydra.py`-keeps-its-own-copy pattern for small constants
# (e.g. `PERSONAL_TASKS_REL`).
REQUIRED_PATHS = [
    "AI_SYSTEM.md",
    "AGENTS.md",
    ".hydra-framework/README.md",
    ".hydra-framework/manifest.yaml",
    ".hydra-framework/core/placement-rules.md",
    ".hydra-framework/tasks/templates/task.md",
    ".hydra-framework/tasks/templates/checkpoint.md",
    ".hydra-framework/tasks/personal",
    ".hydra-framework/capabilities/skills",
    ".hydra-framework/capabilities/agents",
]


def _as_map(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _as_str(value: object, fallback: str = "") -> str:
    return value if isinstance(value, str) else fallback


def adoption_report(paths, providers_paths, context_compiler_paths, manifest: dict) -> dict:
    """Data for the human-readable adoption report (`adopt` without `--record`)."""
    missing = [path for path in REQUIRED_PATHS if not (paths.root / path).exists()]
    lineage = _as_map(manifest.get("lineage"))
    host_stacks = detect_host_repo(paths.root)

    provider_surfaces = []
    for provider in PROVIDERS:
        for label, target in [("skills", provider.skills_target), ("agents", provider.agents_target)]:
            if target is None:
                continue
            target_path = paths.root / target
            count = len(list(target_path.glob("*"))) if target_path.exists() else 0
            provider_surfaces.append((provider.slug, label, target, count))

    spaces_config = context_compiler_paths.hydra / "repo/knowledge/spaces.yaml"
    nodes = discover_knowledge_nodes(context_compiler_paths) if spaces_config.is_file() else []
    surfaces = classify_surfaces(providers_paths)
    unmanaged = [item for item in surfaces if item["status"] in {"orphaned", "drifted", "stale"}]

    return {
        "seed_version": _as_str(manifest.get("seed_version"), "unknown"),
        "missing": missing,
        "private_tier": private_tier_report(paths.root, paths.root / ".hydra-framework.local"),
        "lineage": lineage,
        "host_stacks": host_stacks,
        "provider_surfaces": provider_surfaces,
        "claude_md_present": (paths.root / "CLAUDE.md").exists(),
        "settings_json_present": (paths.root / ".claude/settings.json").exists(),
        "knowledge_nodes": nodes,
        "unmanaged_surfaces": unmanaged,
    }


def record_lineage(paths, manifest: dict, repo_slug: str) -> dict:
    """Data for `adopt --record`. `status` is one of `missing-paths`,
    `already-recorded`, or `recorded`."""
    missing = [path for path in REQUIRED_PATHS if not (paths.root / path).exists()]
    if missing:
        return {"status": "missing-paths", "missing": missing}

    lineage = _as_map(manifest.get("lineage"))
    if lineage:
        return {"status": "already-recorded", "adopted_into": _as_str(lineage.get("adopted_into"), "unknown")}

    slug = slugify(repo_slug)
    text = read_text(paths.manifest_path()).rstrip("\n")
    block = (
        "\nlineage:\n"
        f"  base_seed_version: {_as_str(manifest.get('seed_version'), 'unknown')}\n"
        f"  adopted_into: {slug}\n"
        f"  adopted_date: {clock_port.today()}\n"
        "  divergence_policy: reconcile-before-promoting\n"
    )
    write_text(paths.manifest_path(), f"{text}\n{block}")
    return {"status": "recorded", "slug": slug, "manifest_path": paths.manifest_path()}
