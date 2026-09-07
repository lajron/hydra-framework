"""Per-unit knowledge source fingerprint command."""

from __future__ import annotations

import sys

from hydra_engine.commands import CommandResult
from hydra_engine.documents.digests import normalized_digest
from hydra_engine.documents.tokens import display_path, read_text, write_text
from hydra_engine.knowledge.freshness import resolve_source_path
from hydra_engine.knowledge.nodes import discover_knowledge_nodes, discover_node_unit_paths
from hydra_engine.knowledge.packages import ContextCompilerPaths
from hydra_engine.knowledge.units import read_unit


def _find_unit(paths: ContextCompilerPaths, hydra_id: str):
    if not (paths.hydra / "repo/knowledge/spaces.yaml").is_file():
        return None
    for node in discover_knowledge_nodes(paths):
        for unit_path in discover_node_unit_paths(node):
            unit = read_unit(unit_path, paths.root)
            if unit is not None and unit.hydra_id == hydra_id:
                return unit
    return None


def _line_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _frontmatter_end(lines: list[str]) -> int:
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing frontmatter")
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return index
    raise ValueError("unterminated frontmatter")


def _block_end(lines: list[str], start: int, limit: int) -> int:
    indent = _line_indent(lines[start])
    for index in range(start + 1, limit):
        if lines[index].strip() and _line_indent(lines[index]) <= indent:
            return index
    return limit


def _find_provenance_line(lines: list[str], end: int) -> int:
    for index in range(1, end):
        if _line_indent(lines[index]) == 0 and lines[index].strip() == "provenance:":
            return index
    raise ValueError("missing provenance block")


def _find_nested_line(lines: list[str], start: int, end: int, key: str) -> int | None:
    parent_indent = _line_indent(lines[start])
    for index in range(start + 1, end):
        if not lines[index].strip():
            continue
        indent = _line_indent(lines[index])
        if indent <= parent_indent:
            return None
        if indent == parent_indent + 2 and lines[index].strip().split(":", 1)[0] == key:
            return index
    return None


def replace_source_digests(content: str, entries: list[tuple[str, str]]) -> str:
    lines = content.splitlines()
    frontmatter_end = _frontmatter_end(lines)
    provenance = _find_provenance_line(lines, frontmatter_end)
    provenance_end = _block_end(lines, provenance, frontmatter_end)
    existing = _find_nested_line(lines, provenance, provenance_end, "source_digests")
    if existing is not None:
        existing_end = _block_end(lines, existing, provenance_end)
        del lines[existing:existing_end]
        frontmatter_end = _frontmatter_end(lines)
        provenance = _find_provenance_line(lines, frontmatter_end)
        provenance_end = _block_end(lines, provenance, frontmatter_end)

    sources = _find_nested_line(lines, provenance, provenance_end, "sources")
    if sources is None:
        raise ValueError("missing provenance.sources block")
    insert_at = _block_end(lines, sources, provenance_end)
    indent = " " * _line_indent(lines[sources])
    block = [f"{indent}source_digests:"]
    for source, digest in entries:
        block.extend([
            f"{indent}  - source: {source}",
            f"{indent}    digest: {digest}",
        ])
    lines[insert_at:insert_at] = block
    return "\n".join(lines) + "\n"


def command_knowledge_fingerprint(args, paths: ContextCompilerPaths) -> CommandResult:
    unit = _find_unit(paths, args.unit)
    if unit is None:
        print(f"Hydra knowledge fingerprint: unit not found: {args.unit}", file=sys.stderr)
        return CommandResult(1)
    if not unit.sources:
        print(f"Hydra knowledge fingerprint: unit has no provenance.sources: {args.unit}", file=sys.stderr)
        return CommandResult(1)

    entries: list[tuple[str, str]] = []
    seen: set[str] = set()
    for source in unit.sources:
        if source in seen:
            continue
        seen.add(source)
        path = resolve_source_path(source, paths)
        if not path.is_file():
            print(f"Hydra knowledge fingerprint: source is not one existing file: {source}", file=sys.stderr)
            return CommandResult(1)
        entries.append((source, normalized_digest(path)))

    try:
        updated = replace_source_digests(read_text(unit.path), entries)
    except ValueError as error:
        print(f"Hydra knowledge fingerprint: {display_path(unit.path, paths.root)}: {error}", file=sys.stderr)
        return CommandResult(1)
    write_text(unit.path, updated)

    print(f"Hydra knowledge fingerprint: updated {display_path(unit.path, paths.root)}")
    for source, digest in entries:
        print(f"- {source}: {digest}")
    return CommandResult(0)
