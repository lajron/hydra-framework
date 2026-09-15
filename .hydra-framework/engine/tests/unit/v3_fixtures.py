"""Small deterministic Knowledge v3 fixtures shared by runtime tests."""

from __future__ import annotations

import uuid
from pathlib import Path

from hydra_engine.knowledge.packages import ContextCompilerPaths


def add_documentation_object(root: Path) -> Path:
    page = root / "project-wiki/wiki.md"
    page.parent.mkdir(parents=True)
    page.write_text("# Routing Guide\nhuman-facing documentation\n", encoding="utf-8")
    (root / ".hydra-framework/wiki-fixture.yaml").write_text(
        """schema: hydra-framework.object-sidecar.v1
objects:
  routing-guide:
    hydra_id: hydra://documentation/wiki
    aliases:
      - hydra://alias/wiki
    kind: documentation-page
    title: Routing Guide
    status: active
    scope: repo
    path: project-wiki/wiki.md
    relations: []
    provenance:
      sources: []
""",
        encoding="utf-8",
    )
    return root


def paths_for(root: Path, spaces: tuple[str, ...] = ("demo",)) -> ContextCompilerPaths:
    hydra = root / ".hydra-framework"
    knowledge = hydra / "repo/knowledge"
    knowledge.mkdir(parents=True, exist_ok=True)
    (knowledge / "spaces.yaml").write_text(
        "schema: hydra-framework.knowledge-spaces.v1\n"
        "default_depth: 3\n"
        "max_depth: 4\n"
        "spaces:\n" + "".join(f"  - {space}\n" for space in spaces),
        encoding="utf-8",
    )
    return ContextCompilerPaths(root=root, hydra=hydra)


def node_file(paths: ContextCompilerPaths, logical_id: str) -> Path:
    parts = logical_id.split("/")
    root = paths.hydra / "repo/knowledge/spaces" / Path(*parts)
    root.mkdir(parents=True, exist_ok=True)
    return root / ("space.yaml" if len(parts) == 1 else "node.yaml")


def write_node(
    paths: ContextCompilerPaths,
    logical_id: str,
    *,
    routable: bool = True,
    keywords: tuple[str, ...] = (),
    routes: str = "",
    state: bool = True,
    overview: bool = True,
    scope: str = "repo-local",
) -> Path:
    config = paths.hydra / "repo/knowledge/spaces.yaml"
    top_space = logical_id.split("/", 1)[0]
    if not config.is_file():
        paths_for(paths.root, (top_space,))
    else:
        content = config.read_text(encoding="utf-8")
        if f"  - {top_space}\n" not in content:
            config.write_text(content + f"  - {top_space}\n", encoding="utf-8")
    path = node_file(paths, logical_id)
    kind = "knowledge-space" if "/" not in logical_id else "knowledge-node"
    uid = uuid.uuid5(uuid.NAMESPACE_URL, f"hydra-test:{logical_id}")
    owner = "owners:\n  team: test\n" if kind == "knowledge-space" else ""
    path.write_text(
        "schema: hydra-framework.knowledge-node.v1\n"
        f"node: {logical_id}\n"
        f"hydra_id: hydra://{kind}/{logical_id}\n"
        f"uid: {uid}\n"
        "schema_version: 3\n"
        f"kind: {kind}\n"
        f"title: {logical_id.replace('/', ' ').title()}\n"
        "status: active\n"
        f"scope: {scope}\n"
        f"{owner}"
        "relations: []\n"
        "provenance:\n  sources: []\n"
        f"routable: {'true' if routable else 'false'}\n"
        + ("state: ./state.md\n" if state else "")
        + ("overview: ./overview.md\n" if overview else "")
        + ("keywords:\n" + "".join(f"  - {value}\n" for value in keywords) if keywords else "keywords: []\n")
        + routes,
        encoding="utf-8",
    )
    if state:
        (path.parent / "state.md").write_text(f"# {logical_id} state\n", encoding="utf-8")
    if overview:
        (path.parent / "overview.md").write_text(f"# {logical_id} overview\n", encoding="utf-8")
    return path


def write_unit(
    paths: ContextCompilerPaths,
    logical_id: str,
    name: str,
    *,
    requires: tuple[str, ...] = (),
    relations: tuple[tuple[str, str], ...] = (),
    scope: str = "repo-local",
    checked_on: str = "",
    sources: tuple[str, ...] = (),
    body: str = "Useful enterprise guidance.\n",
) -> Path:
    root = node_file(paths, logical_id).parent
    units = root / "units"
    units.mkdir(exist_ok=True)
    hydra_id = f"hydra://knowledge-unit/{logical_id}/{name}"
    uid = uuid.uuid5(uuid.NAMESPACE_URL, f"hydra-test:{hydra_id}")
    path = units / f"{name}.md"
    path.write_text(
        "---\n"
        f"hydra_id: {hydra_id}\n"
        f"uid: {uid}\n"
        "schema_version: 3\n"
        "kind: knowledge-unit\n"
        f"title: {name.title()}\n"
        "status: active\n"
        f"scope: {scope}\n"
        "owners:\n  team: test\n"
        + ("relations:\n" + "".join(f"  - type: {kind}\n    target: {target}\n" for kind, target in relations) if relations else "relations: []\n")
        + ("provenance:\n  sources:\n" + "".join(f"    - {value}\n" for value in sources) if sources else "provenance:\n  sources: []\n")
        + "unit_kind: note\n"
        + f"question: What is {name}?\n"
        + "certainty: confirmed\n"
        + (f"checked_on: {checked_on}\n" if checked_on else "")
        + "reads: []\n"
        + ("requires:\n" + "".join(f"  - {value}\n" for value in requires) if requires else "requires: []\n")
        + "---\n\n"
        + body,
        encoding="utf-8",
    )
    return path
