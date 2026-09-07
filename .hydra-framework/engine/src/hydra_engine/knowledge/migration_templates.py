"""Deterministic conversion of the inactive Knowledge v2 authoring templates."""

import re
from pathlib import Path

from hydra_engine.knowledge import migration_format

# Template object titles are the only "Knowledge Package" strings the migration
# owns; every one of them ends in "Template" on the same line.
_TEMPLATE_TITLE = re.compile(r"Knowledge Package(?=[^\n]*Template)")


def _space_document() -> str:
    return migration_format.emit_yaml({
        "schema": "hydra-framework.knowledge-node.v1",
        "node": "<space-slug>",
        "hydra_id": "hydra://knowledge-space/<space-slug>",
        "uid": "<fresh uuid4>",
        "schema_version": 3,
        "kind": "knowledge-space",
        "title": "<Space Name>",
        "status": "active",
        "scope": "<base-seed|common-seed|repo-local>",
        "owners": {"team": "<owner>"},
        "relations": [],
        "provenance": {"sources": []},
        "role": "accountability-root",
        "routable": True,
        "state": "./state.md",
        "overview": "./overview.md",
        "keywords": ["<keyword>", "<phrase>", "<domain term>"],
        "defaults": {},
        "routes": {
            "example_route": {
                "use_when": ["<task shape or question this route answers>"],
                "priority_units": ["hydra://knowledge-unit/<space-slug>/<unit-slug>"],
                "requires": ["hydra://knowledge-unit/<space-slug>/<must-read-unit-slug>"],
                "expand_when": [{
                    "when_paths": ["@<namespace>/<binding>/**"],
                    "read": ["hydra://knowledge-unit/<space-slug>/<conditionally-relevant-unit-slug>"],
                    "why": "<why this verified binding implies that unit>",
                }],
                "avoid_by_default": ["<large generated or private area>"],
                "verify": ["<command that checks work under this route>"],
            },
        },
    })


def executable_mode(source: Path) -> int:
    """Deterministic target mode.

    Only the tracked executable bit is preserved.  Raw ``st_mode`` varies with
    the checkout umask, which would make the review digest irreproducible
    across clones and defeat the exact-digest approval gate.
    """
    return 0o755 if source.stat().st_mode & 0o100 else 0o644


def _rewrite_text(text: str) -> str:
    rewritten = (
        text.replace("knowledge-packages/<package-slug>", "spaces/<space-slug>")
        .replace("knowledge-packages.md", "../../core/knowledge-architecture.md")
        .replace("<package-slug>", "<space-slug>")
        .replace("<Package Name>", "<Space Name>")
        .replace("routing.yaml", "space.yaml.template")
        .replace("package gate", "node-document gate")
        .replace("package documentation", "node documentation")
        .replace("a package", "a knowledge space")
        .replace("A package", "A knowledge space")
    )
    return rewritten.replace(
        "relations:\n  - hydra://knowledge-space/<space-slug>",
        "relations:\n  - type: relates-to\n    target: hydra://knowledge-space/<space-slug>",
    )


LEGACY_CONCEPT_DOC = ".hydra-framework/repo/knowledge/knowledge-packages.md"
V3_CONTRACT_DOC = ".hydra-framework/core/knowledge-architecture.md"


def rewrite_references(text: str) -> str:
    """Rewrite template and superseded-contract *paths* only.

    Safe for any migrated content file: nothing here touches prose or identity
    vocabulary, both of which have a narrower legitimate scope.
    """
    return (
        text.replace(
            ".hydra-framework/repo/knowledge/knowledge-packages/templates/routing.yaml",
            ".hydra-framework/repo/knowledge/templates/space/space.yaml.template",
        )
        .replace("knowledge-packages/templates/routing.yaml", "knowledge/templates/space/space.yaml.template")
        .replace(
            ".hydra-framework/repo/knowledge/knowledge-packages/templates",
            ".hydra-framework/repo/knowledge/templates/space",
        )
        .replace("knowledge-packages/templates", "knowledge/templates/space")
        .replace(LEGACY_CONCEPT_DOC, V3_CONTRACT_DOC)
        .replace("repo/knowledge/knowledge-packages.md", "core/knowledge-architecture.md")
        .replace("knowledge-packages/<package-slug>", "spaces/<space-slug>")
    )


def rewrite_sidecar(text: str) -> str:
    """Rewrite template object identities, keys, and titles in the sidecar file.

    Template identity/key/title vocabulary exists only in the object sidecar;
    applying it repository-wide half-renames unrelated prose.
    """
    rewritten = (
        rewrite_references(text)
        .replace("package-template", "space-template")
        .replace("hydra:/" + "/knowledge-template/package/", "hydra:/" + "/knowledge-template/space/")
    )
    return _TEMPLATE_TITLE.sub("Knowledge Space", rewritten)


def plan(
    legacy: Path,
    knowledge: Path,
    root: Path,
    writes: dict[str, str],
    modes: dict[str, int],
    move_sources: dict[str, str],
    originals: dict[str, str],
    deletes: list[str],
) -> None:
    templates = legacy / "templates"
    if templates.is_dir():
        for source in sorted(path for path in templates.rglob("*") if path.is_file()):
            relative = source.relative_to(templates)
            if relative.as_posix() == "routing.yaml":
                relative = Path("space.yaml.template")
                rewritten = _space_document()
            else:
                rewritten = _rewrite_text(source.read_text(encoding="utf-8"))
            source_rel = source.relative_to(root).as_posix()
            target_rel = (knowledge / "templates/space" / relative).relative_to(root).as_posix()
            originals[source_rel] = source.read_text(encoding="utf-8")
            writes[target_rel] = rewritten
            modes[target_rel] = executable_mode(source)
            move_sources[target_rel] = source_rel
            deletes.append(source_rel)
    readme = legacy / "README.md"
    if readme.is_file():
        readme_rel = readme.relative_to(root).as_posix()
        originals[readme_rel] = readme.read_text(encoding="utf-8")
        deletes.append(readme_rel)
    concept = root / LEGACY_CONCEPT_DOC
    if concept.is_file():
        concept_rel = concept.relative_to(root).as_posix()
        originals[concept_rel] = concept.read_text(encoding="utf-8")
        deletes.append(concept_rel)
