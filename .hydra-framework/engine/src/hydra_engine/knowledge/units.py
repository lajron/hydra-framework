"""Knowledge-unit discovery and compilation glue.

A unit is one durable, addressable operational question under a knowledge
package's `units/` directory -- a Markdown object with `kind: knowledge-unit`
in its frontmatter envelope. `unit_kind` (`answer | rule | map | divergence |
status`) is a second, package-local kind field alongside the object-family
`kind`. Two kind fields on the same object look redundant; they answer
different questions on purpose. `kind: knowledge-unit` is what
`identity.object_families` and `ref check` need to place the object in the
Knowledge family. `unit_kind` is what this package's own validation profile
switches on (`map` requires every `reads:` path to resolve; `rule` requires
non-empty `provenance.sources`; and so on) and no object family cares about
it. Folding the two into one field would make the object-family registry
carry a package-local distinction, or make this package reach into
`identity.object_families` for a concept it does not own. Do not collapse
them.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from hydra_engine.documents.frontmatter_blocks import markdown_frontmatter, yaml_list, yaml_map, yaml_str
from hydra_engine.identity.hydra_ids import HYDRA_REF_RE

UNIT_KINDS = ("answer", "rule", "map", "divergence", "status")


@dataclasses.dataclass(frozen=True)
class Unit:
    path: Path
    hydra_id: str
    unit_kind: str
    title: str
    question: str
    group: str
    certainty: str
    checked_on: str
    reads: tuple[str, ...]
    requires: tuple[str, ...]
    see_also: tuple[str, ...]
    verify: tuple[str, ...]
    expand_when: tuple[dict, ...]
    sources: tuple[str, ...]
    source_digests: object = ()
    relations: tuple[tuple[str, str], ...] = ()
    uid: str = ""


def units_root(package_root: Path) -> Path:
    return package_root / "units"


def discover_unit_paths(package_root: Path) -> list[Path]:
    root = units_root(package_root)
    if not root.is_dir():
        return []
    return sorted(root.glob("*.md"))


def read_unit(path: Path, repo_root: Path) -> Unit | None:
    """The unit at `path`, or `None` when it is not one.

    `None` covers two real, non-error cases: a file with no frontmatter at
    all, and a Markdown file in `units/` whose `kind` is something other than
    `knowledge-unit` (validation reports that case; this function just
    declines to parse it as a unit). A missing optional field is `""` / `()`,
    never a raised error -- only an unterminated frontmatter block raises,
    via `markdown_frontmatter` itself, because that is a real authoring
    mistake this function has no safe way to guess past.
    """
    data = markdown_frontmatter(path, repo_root)
    if not data or yaml_str(data.get("kind")) != "knowledge-unit":
        return None
    provenance = yaml_map(data.get("provenance"))
    relations_raw = data.get("relations")
    relations = tuple(
        (yaml_str(item.get("type")), yaml_str(item.get("target")).lower())
        for item in relations_raw
        if isinstance(item, dict)
    ) if isinstance(relations_raw, list) else ()
    expand_when_raw = data.get("expand_when")
    expand_when = tuple(
        item for item in expand_when_raw if isinstance(item, dict)
    ) if isinstance(expand_when_raw, list) else ()
    return Unit(
        path=path,
        hydra_id=yaml_str(data.get("hydra_id")),
        unit_kind=yaml_str(data.get("unit_kind")),
        title=yaml_str(data.get("title")),
        question=yaml_str(data.get("question")),
        group=yaml_str(data.get("group")),
        certainty=yaml_str(data.get("certainty")),
        checked_on=yaml_str(data.get("checked_on")),
        reads=tuple(yaml_list(data.get("reads"))),
        requires=tuple(yaml_list(data.get("requires"))),
        see_also=tuple(yaml_list(data.get("see_also"))),
        verify=tuple(yaml_list(data.get("verify"))),
        expand_when=expand_when,
        sources=tuple(yaml_list(provenance.get("sources"))),
        source_digests=provenance.get("source_digests", ()),
        relations=relations,
        uid=yaml_str(data.get("uid")),
    )


def non_unit_reason(path: Path, repo_root: Path) -> str:
    """Why a Markdown file under `units/` did not parse as a unit, or `""`
    when it did -- kept beside `read_unit` since both read the same envelope,
    for `package_checks.validate_units_dir` to turn into a finding. A file in
    `units/` with no frontmatter, or a `kind` other than `knowledge-unit`, is
    otherwise invisible to everything: not a unit, not reported."""
    data = markdown_frontmatter(path, repo_root)
    if not data:
        return "no frontmatter"
    kind = yaml_str(data.get("kind"))
    if kind != "knowledge-unit":
        return f"kind is `{kind or '(absent)'}`, not `knowledge-unit`"
    return ""


def units_by_id(package_root: Path, repo_root: Path) -> dict[str, Unit]:
    result: dict[str, Unit] = {}
    for path in discover_unit_paths(package_root):
        unit = read_unit(path, repo_root)
        if unit is not None and unit.hydra_id:
            result[unit.hydra_id] = unit
    return result


def required_seed_ids(pack: dict | None, object_refs: list[str]) -> set[str]:
    """`hydra://` ids to treat as required-unit seeds for one compile.

    Commit 1's interim rule (package-routing v2 routes replace this in
    Commit 3, per the design note's own §4.4): any explicit `--object`
    reference, plus any id a selected context pack's `Read:` bullets name
    directly.
    """
    seeds = {ref.lower() for ref in object_refs}
    if pack:
        for bullet in pack.get("read", []):
            seeds.update(match.lower() for match in HYDRA_REF_RE.findall(bullet))
    return seeds


def required_closure(units: dict[str, Unit], seed_ids: set[str], warnings: list[str]) -> set[str]:
    """Transitive closure of `requires` over `seed_ids`.

    Walks with an explicit path stack, not just a visited set, so a genuine
    `requires` cycle (A requires B requires A) is caught and reported once --
    a diamond, where two branches converge on the same unit without ever
    revisiting an in-progress node, is not a cycle and produces no warning.
    Termination is guaranteed either way; the stack is what lets a real cycle
    be told apart from a converging diamond.
    """
    closure: set[str] = set()

    def visit(node: str, stack: tuple[str, ...]) -> None:
        if node in stack:
            warnings.append(f"requires cycle detected: {' -> '.join((*stack, node))}")
            return
        if node in closure:
            return
        closure.add(node)
        unit = units.get(node)
        if unit is None:
            return
        for target in unit.requires:
            visit(target, (*stack, node))

    for seed in seed_ids:
        visit(seed, ())
    return closure
