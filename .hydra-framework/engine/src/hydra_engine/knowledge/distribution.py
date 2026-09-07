"""One scope policy for Knowledge v3 copy, adoption, reconciliation, and export."""

from __future__ import annotations

from pathlib import Path

from hydra_engine.documents.frontmatter_blocks import parse_yaml, yaml_str
from hydra_engine.knowledge.nodes import LEGAL_SCOPES

DISTRIBUTION_PROFILES = {
    "base": frozenset({"base-seed"}),
    "common": frozenset({"base-seed", "common-seed"}),
}


def included_scopes(profile: str) -> frozenset[str]:
    try:
        return DISTRIBUTION_PROFILES[profile]
    except KeyError as error:
        raise ValueError(f"unknown distribution profile `{profile}`; expected one of {tuple(DISTRIBUTION_PROFILES)}") from error


def scope_is_distributed(scope: str, profile: str) -> bool:
    if scope not in LEGAL_SCOPES:
        raise ValueError(f"invalid distribution scope `{scope}`")
    return scope in included_scopes(profile)


def _scope_from_document(path: Path, source_root: Path) -> str:
    return yaml_str(parse_yaml(path, source_root).get("scope")) if path.is_file() else ""


def knowledge_path_scope(rel: Path, source_root: Path) -> str | None:
    """Effective v3 distribution scope for one repository-relative path.

    `None` means the path is outside Knowledge v3 and this policy has no
    opinion. Infrastructure manifests are base-seed. Node-owned files use the
    nearest node envelope, so a child can narrow or widen distribution only by
    declaring its own explicit scope.
    """
    prefix = Path(".hydra-framework/repo/knowledge")
    try:
        knowledge_rel = rel.relative_to(prefix)
    except ValueError:
        return None
    if knowledge_rel.as_posix() == "spaces.yaml":
        return "base-seed"
    if knowledge_rel.parts[:1] == ("bindings",):
        if knowledge_rel.name == "manifest.yaml":
            return "base-seed"
        return _scope_from_document(source_root / rel, source_root) or "repo-local"
    if knowledge_rel.parts[:1] == ("views",):
        return _scope_from_document(source_root / rel, source_root) or "repo-local"
    if knowledge_rel.parts[:1] != ("spaces",) or len(knowledge_rel.parts) < 2:
        return None
    absolute = source_root / rel
    current = absolute if absolute.is_dir() else absolute.parent
    space_root = source_root / prefix / "spaces" / knowledge_rel.parts[1]
    while current == space_root or space_root in current.parents:
        node_file = current / ("space.yaml" if current == space_root else "node.yaml")
        scope = _scope_from_document(node_file, source_root)
        if scope:
            return scope
        if current == space_root:
            break
        current = current.parent
    return "repo-local"


def should_distribute_path(rel: Path, source_root: Path, profile: str) -> bool:
    scope = knowledge_path_scope(rel, source_root)
    return True if scope is None else scope_is_distributed(scope, profile)
