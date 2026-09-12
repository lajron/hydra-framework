"""Provider capability-class/effort-budget resolution, and the skill/agent
wrapper rendering that resolution feeds. Also the fourth extension
registry: `PROVIDERS`.

Wrapper rendering (`build_skill_wrapper` and friends) lives here rather than
its own `wrappers.py`: splitting it out would have added a second
`hydra_engine.documents.yaml_documents` importer inside `providers/`, pushing
that module's in-degree from 10 to 11 and tripping check 4 (a module reached
by more than ten others must import nothing internally, and
`yaml_documents.py` imports `documents.tokens`). Keeping both in one module
holds the package's `yaml_documents` fan-in at 2 (this module, `reclaim.py`).

The same constraint is why `PROVIDERS` is a tuple in this module rather than
its own `provider_registry.py`, unlike the object-family, object-handler, and
validator registries before it: those replaced a flat dict, a suffix switch,
and an anonymous-lambda interleave that lived in *other* modules, so
extraction had no importer of its own to create. Here, the registry's own
field values (`build_agent_wrapper`, `build_codex_agent_wrapper`) are
functions this module already defines; a separate registry module would
either import them back from here -- while this module's own
`validate_capability_maps` reads the registry, which would create the import
cycle this layout avoids -- or duplicate them.
Keeping the registry where its data already lived is the smaller, honest
diff, following the "close to data already" characterization of
this cluster.

`ADAPTER_TARGETS`, a plain mutable list of raw tuples, is now `PROVIDERS`: a
frozen tuple of `Provider` records, matching `identity.object_families`'s
`OBJECT_FAMILIES`, `objects.object_handlers`'s `OBJECT_HANDLERS`, and
`checks.validator_registry`'s `VALIDATORS`. Its new field,
`build_agent_wrapper`, replaces the `if provider == "codex":` branch that
used to live in `adapter_plan.planned_adapter_files` -- which agent-wrapper
renderer a provider uses is a fact about the provider, not something each
caller re-derives, exactly as `objects.object_handlers.ObjectHandler` carries
`read_envelope` as a field instead of leaving callers to switch on suffix.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from collections.abc import Callable
from pathlib import Path

from hydra_engine.documents.tokens import HydraYamlError, display_path, read_text
from hydra_engine.documents.yaml_documents import parse_yaml, yaml_list, yaml_map, yaml_str
from hydra_engine import config as hydra_config
from hydra_engine.finding import Finding
from hydra_engine.identity.slugs import slugify
from hydra_engine.providers.paths import ProvidersPaths

CAPABILITY_MAP_SCHEMA = "hydra-framework.capability-map.v1"

# The one place a wrapper's name prefix is spelled. `adapter_plan.ownership_paths`,
# `reclaim.py`'s stale-wrapper naming, `selection.py`'s wrapper-name-in-prose
# check, and the generated `.gitignore` block (`git_ownership.py`) all read
# this constant rather than each hard-coding `"hydra-"` -- the ignore patterns
# in particular must track this value exactly, or a renamed prefix would
# silently stop being ignored.
WRAPPER_PREFIX = "hydra-"


@dataclasses.dataclass(frozen=True)
class Provider:
    """One provider's generated surfaces and the agent-wrapper renderer it uses.

    `agents_target` of `None` means the runtime has no verified agent
    surface, so Hydra does not invent one; every provider does render
    skills, so `skills_target` carries no such option. `build_agent_wrapper`
    is a field, not a branch, for the same reason `ObjectHandler.read_envelope`
    is: the registry is the one place that fact is recorded.
    """

    slug: str
    skills_target: str
    agents_target: str | None
    agent_extension: str | None
    build_agent_wrapper: Callable[[Path, str, dict, Path, hydra_config.EffectiveConfig], tuple[str, dict[str, str]]]


def capability_map(paths: ProvidersPaths, provider: str) -> dict:
    """Load a provider capability map, or an empty map when none is usable."""
    path = paths.capability_map_path(provider)
    try:
        data = parse_yaml(path, paths.root)
    except HydraYamlError as error:
        print(f"Hydra capability map ignored: {error}", file=sys.stderr)
        return {}
    if data.get("schema") != CAPABILITY_MAP_SCHEMA:
        return {}
    return data


def resolve_capability(mapping: dict, section: str, key: str) -> str:
    """Resolve a Hydra capability class or effort budget for one provider.

    Returns "" when there is no usable mapping, so exporters omit the field
    rather than inventing a provider value.
    """
    if not key:
        return ""
    value = yaml_map(mapping.get(section)).get(key, "")
    if not isinstance(value, str) or value in {"", "unresolved"}:
        return ""
    return value


def validate_capability_maps(paths: ProvidersPaths) -> list[Finding]:
    """Canonical capability classes and effort budgets must resolve per provider."""
    findings: list[Finding] = []
    classes: set[str] = set()
    efforts: set[str] = set()
    try:
        effective = hydra_config.load_effective_config(
            hydra_config.ConfigPaths(root=paths.root, hydra=paths.hydra, local=paths.root / ".hydra-framework.local")
        )
    except hydra_config.ConfigError:
        effective = None
    agents_root = paths.agents_root()
    if agents_root.exists():
        for metadata in sorted(agents_root.glob("*/metadata.yaml")):
            try:
                data = parse_yaml(metadata, paths.root)
            except HydraYamlError:
                continue
            role = yaml_str(data.get("name"), metadata.parent.name)
            capability_class = yaml_str(data.get("capability_class"))
            effort = yaml_str(data.get("effort"))
            if capability_class:
                classes.add(hydra_config.role_capability_class(effective, role, capability_class) if effective else capability_class)
            if effort:
                efforts.add(hydra_config.role_effort_ceiling(effective, role, effort) if effective else effort)

    for provider in PROVIDERS:
        path = paths.capability_map_path(provider.slug)
        label = display_path(path, paths.root)
        if not path.exists():
            if provider.agents_target is not None:
                findings.append(Finding(
                    path=label, code="capability-maps",
                    detail=f"{label} is missing; agents for `{provider.slug}` will export without a model",
                ))
            continue
        try:
            data = parse_yaml(path, paths.root)
        except HydraYamlError as error:
            findings.append(Finding(path=label, code="capability-maps", detail=str(error)))
            continue
        if data.get("schema") != CAPABILITY_MAP_SCHEMA:
            findings.append(Finding(
                path=label, code="capability-maps", detail=f"{label} schema must be `{CAPABILITY_MAP_SCHEMA}`",
            ))
            continue
        for key in ["provider", "verified", "certainty"]:
            if not yaml_str(data.get(key)):
                findings.append(Finding(path=label, code="capability-maps", detail=f"{label} missing `{key}`"))
        mapped_classes = yaml_map(data.get("capability_classes"))
        mapped_efforts = yaml_map(data.get("effort_budgets"))
        controls = yaml_map(data.get("delegation_controls"))
        for key in hydra_config.DELEGATION_CONTROL_KEYS:
            value = yaml_str(controls.get(key))
            if value not in hydra_config.DELEGATION_CONTROL_STATES:
                findings.append(Finding(
                    path=label, code="capability-maps",
                    detail=f"{label} delegation_controls `{key}` must be supported, advisory, or unsupported",
                ))
        for name in sorted(classes):
            if name not in mapped_classes:
                findings.append(Finding(
                    path=label, code="capability-maps",
                    detail=f"{label} has no entry for capability class `{name}`",
                ))
        for name in sorted(efforts):
            if name not in mapped_efforts:
                findings.append(Finding(
                    path=label, code="capability-maps",
                    detail=f"{label} has no entry for effort budget `{name}`",
                ))
    return findings


def adapter_sidecar(provider: str, rel_source: str, generated: str, kind: str) -> str:
    return (
        "schema: hydra-framework.adapter.v2\n"
        f"provider: {provider}\n"
        f"kind: {kind}\n"
        f"canonical_source: {rel_source}\n"
        f"generated_file: {generated}\n"
    )


def frontmatter_block(fields: list[tuple[str, str]]) -> str:
    lines = ["---"]
    lines.extend(f"{key}: {value}" for key, value in fields if value)
    lines.append("---")
    return "\n".join(lines)


def build_skill_wrapper(skill_dir: Path, provider: str, root: Path) -> tuple[str, dict[str, str]]:
    """Render one provider skill wrapper from a canonical Hydra skill."""
    meta = parse_yaml(skill_dir / "metadata.yaml", root)
    name = yaml_str(meta.get("name"), skill_dir.name)
    description = yaml_str(
        meta.get("description"), f"Use when the Hydra `{name}` workflow is relevant."
    )
    kind = yaml_str(meta.get("kind"), "procedure")
    wrapper_name = f"{WRAPPER_PREFIX}{name}"
    canonical = skill_dir / "skill.md"
    rel_source = canonical.relative_to(root).as_posix()

    fields = [("name", wrapper_name), ("description", description)]
    fields.append(("argument-hint", yaml_str(meta.get("argument_hint"))))
    if kind == "command":
        # Commands have side effects or need explicit timing, so only a human
        # should trigger them.
        fields.append(("disable-model-invocation", "true"))
    fields.append(("allowed-tools", yaml_str(meta.get("allowed_tools"))))
    if yaml_str(meta.get("user_invocable")) == "false":
        fields.append(("user-invocable", "false"))

    content = f"{frontmatter_block(fields)}\n\n{read_text(canonical)}"
    files = {
        "SKILL.md": content,
        ".hydra-adapter.yaml": adapter_sidecar(provider, rel_source, "SKILL.md", "skill"),
    }
    return wrapper_name, files


def agent_instruction_body(canonical: Path, meta: dict) -> str:
    body = [read_text(canonical).rstrip()]
    dependencies = yaml_map(meta.get("dependencies"))
    knowledge = yaml_list(dependencies.get("knowledge"))
    skills = yaml_list(dependencies.get("skills"))
    if knowledge or skills:
        body.append("\n## Hydra Context\n")
        body.append(
            "Load only what the task needs. Paths are relative to `.hydra-framework/`."
        )
        if knowledge:
            body.append("\nCanonical knowledge:\n")
            body.extend(f"- `.hydra-framework/{item}`" for item in knowledge)
        if skills:
            body.append("\nRelevant Hydra skills. The skill name works when the skill is materialized in\nthis checkout; the canonical source always resolves.\n")
            body.extend(
                f"- `{WRAPPER_PREFIX}{item}` -- `.hydra-framework/capabilities/skills/{item}/skill.md`"
                for item in skills
            )
        body.append("")
    return "\n".join(body) + "\n"


def build_agent_wrapper(
    agent_dir: Path,
    provider: str,
    mapping: dict,
    root: Path,
    config: hydra_config.EffectiveConfig | None = None,
) -> tuple[str, dict[str, str]]:
    """Render one provider subagent from a canonical Hydra agent role.

    Capability class and effort budget stay provider-neutral in canonical Hydra;
    the provider capability map turns them into concrete runtime values here.
    """
    meta = parse_yaml(agent_dir / "metadata.yaml", root)
    name = yaml_str(meta.get("name"), agent_dir.name)
    description = yaml_str(
        meta.get("description"), f"Use for the Hydra `{name}` role."
    )
    canonical = agent_dir / "agent.md"
    rel_source = canonical.relative_to(root).as_posix()
    wrapper_name = f"{WRAPPER_PREFIX}{name}"
    effective = config or hydra_config.load_effective_config(
        hydra_config.ConfigPaths(root=root, hydra=root / ".hydra-framework", local=root / ".hydra-framework.local")
    )
    capability_class = hydra_config.role_capability_class(effective, name, yaml_str(meta.get("capability_class")))
    effort_budget = hydra_config.role_effort_ceiling(effective, name, yaml_str(meta.get("effort")))

    tools = yaml_list(meta.get("tools"))
    fields = [("name", wrapper_name), ("description", description)]
    if tools:
        fields.append(("tools", ", ".join(tools)))
    fields.append(("model", resolve_capability(mapping, "capability_classes", capability_class)))
    fields.append(("effort", resolve_capability(mapping, "effort_budgets", effort_budget)))

    body = agent_instruction_body(canonical, meta)
    body += hydra_config.delegation_instruction(effective, hydra_config.provider_delegation_controls(mapping))

    content = f"{frontmatter_block(fields)}\n\n" + body
    files = {
        f"{wrapper_name}.md": content,
        f".hydra-adapter-{wrapper_name}.yaml": adapter_sidecar(
            provider, rel_source, f"{wrapper_name}.md", "agent"
        ),
    }
    return wrapper_name, files


def toml_string(value: str) -> str:
    return json.dumps(value)


def build_codex_agent_wrapper(
    agent_dir: Path,
    provider: str,
    mapping: dict,
    root: Path,
    config: hydra_config.EffectiveConfig | None = None,
) -> tuple[str, dict[str, str]]:
    """Render one Codex custom agent TOML file from a canonical Hydra role."""
    meta = parse_yaml(agent_dir / "metadata.yaml", root)
    name = yaml_str(meta.get("name"), agent_dir.name)
    description = yaml_str(meta.get("description"), f"Use for the Hydra `{name}` role.")
    canonical = agent_dir / "agent.md"
    rel_source = canonical.relative_to(root).as_posix()
    wrapper_slug = f"{WRAPPER_PREFIX}{name}"
    agent_name = slugify(wrapper_slug).replace("-", "_")
    effective = config or hydra_config.load_effective_config(
        hydra_config.ConfigPaths(root=root, hydra=root / ".hydra-framework", local=root / ".hydra-framework.local")
    )

    capability_class = hydra_config.role_capability_class(effective, name, yaml_str(meta.get("capability_class")))
    effort_budget = hydra_config.role_effort_ceiling(effective, name, yaml_str(meta.get("effort")))
    model = resolve_capability(mapping, "capability_classes", capability_class)
    effort = resolve_capability(mapping, "effort_budgets", effort_budget)
    body = agent_instruction_body(canonical, meta)
    body += hydra_config.delegation_instruction(effective, hydra_config.provider_delegation_controls(mapping))

    lines = [
        "# Generated by Hydra; edit the canonical source under .hydra-framework/.",
        f"name = {toml_string(agent_name)}",
        f"description = {toml_string(description)}",
    ]
    if model:
        lines.append(f"model = {toml_string(model)}")
    if effort:
        lines.append(f"model_reasoning_effort = {toml_string(effort)}")
    lines.append(f"developer_instructions = {toml_string(body)}")
    content = "\n".join(lines) + "\n"
    files = {
        f"{wrapper_slug}.toml": content,
        f".hydra-adapter-{wrapper_slug}.yaml": adapter_sidecar(
            provider, rel_source, f"{wrapper_slug}.toml", "agent"
        ),
    }
    return wrapper_slug, files


# Defined after the two builders it references by name: a dataclass field
# holding a function is bound at module-load time, not deferred like a
# function body's own name lookups, so this tuple cannot precede them.
PROVIDERS = (
    Provider("claude", ".claude/skills", ".claude/agents", ".md", build_agent_wrapper),
    Provider("codex", ".agents/skills", ".codex/agents", ".toml", build_codex_agent_wrapper),
)
