"""Context-packet candidate construction."""

from __future__ import annotations

from pathlib import Path

from hydra_engine.documents.tokens import display_path, read_text
from hydra_engine.knowledge.freshness import stale_provenance_sources
from hydra_engine.knowledge.node_catalog import discover_knowledge_nodes, discover_node_unit_paths
from hydra_engine.knowledge.units import Unit
from hydra_engine.knowledge.units import read_unit

APPROX_CHARS_PER_TOKEN = 4
UNIT_PRIORITY = 15
UNIT_READ_PRIORITY = 25


def approx_tokens(text: str, chars_per_token: int = APPROX_CHARS_PER_TOKEN) -> int:
    if not text:
        return 0
    divisor = max(chars_per_token, 1)
    return max(1, (len(text) + divisor - 1) // divisor)


def file_candidate(
    path: Path,
    *,
    kind: str,
    reason: str,
    priority: int,
    paths: ContextCompilerPaths,
    source: str = "",
    chars_per_token: int = APPROX_CHARS_PER_TOKEN,
) -> dict:
    text = read_text(path)
    return {
        "kind": kind,
        "path": display_path(path, paths.root),
        "reason": reason,
        "source": source,
        "priority": priority,
        "chars": len(text),
        "lines": len(text.splitlines()),
        "approx_tokens": approx_tokens(text, chars_per_token),
    }


def add_candidate(candidates: list[dict], seen: set[str], candidate: dict) -> None:
    key = candidate.get("pointer", candidate["path"])
    if key in seen:
        for existing in candidates:
            existing_key = existing.get("pointer", existing["path"])
            if existing_key != key:
                continue
            # `required` must survive a merge regardless of which duplicate
            # arrived first: an explicit `--object` reference and a unit's
            # own required-unit candidate can name the same path, and either
            # order must still leave the merged candidate exempt.
            if candidate.get("required"):
                existing["required"] = True
            if candidate["reason"] not in existing["reason"]:
                existing["reason"] += f"; {candidate['reason']}"
                if candidate.get("source") and candidate["source"] not in existing.get("source", ""):
                    existing["source"] = f"{existing.get('source', '')}; {candidate['source']}".strip("; ")
            break
        return
    seen.add(key)
    candidates.append(candidate)


def resolve_context_path(raw: str, paths: ContextCompilerPaths) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return paths.root / raw


def stale_unit_sources(unit: Unit, paths: ContextCompilerPaths) -> list[str]:
    """Advisory stale source list for one unit.

    Fingerprinted sources compare content; unfingerprinted sources keep
    the date-only fallback. This returns a plain list, never a
    `Finding`, so staleness cannot become a hard `validate` failure.
    """
    return stale_provenance_sources(
        {"sources": list(unit.sources), "source_digests": unit.source_digests},
        checked_on=unit.checked_on,
        paths=paths,
    )


def stale_unit_source_report(paths: ContextCompilerPaths) -> tuple[int, list[dict[str, object]]]:
    """Every stale knowledge-unit source across every node.

    This deliberately reuses `stale_unit_sources`'s date-only rule. The
    reporting surface is wider than `compile-context`, but the freshness
    semantics are unchanged.
    """
    rows: list[dict[str, object]] = []
    checked_units = 0
    if not (paths.hydra / "repo/knowledge/spaces.yaml").is_file():
        return checked_units, rows
    for node in discover_knowledge_nodes(paths):
        for unit_path in discover_node_unit_paths(node):
            unit = read_unit(unit_path, paths.root)
            if unit is None:
                continue
            checked_units += 1
            stale_sources = stale_unit_sources(unit, paths)
            if not stale_sources:
                continue
            rows.append({
                "node": node.logical_id,
                "hydra_id": unit.hydra_id,
                "path": display_path(unit.path, paths.root),
                "stale_sources": stale_sources,
            })
    return checked_units, rows


def unit_candidates(
    units: list[Unit],
    *,
    package: str,
    paths: ContextCompilerPaths,
    required_ids: set[str],
    warnings: list[str],
    chars_per_token: int = APPROX_CHARS_PER_TOKEN,
) -> list[dict]:
    """One candidate per unit file, plus one per resolved `reads:` path.

    The `required` flag scopes narrowly to the unit's own file: a unit named
    in `required_ids` is budget-exempt, but the files its `reads:` names are
    always `required=False` -- otherwise one `requires` edge could drag
    arbitrary source files past the budget alongside it.
    """
    result: list[dict] = []
    for unit in units:
        candidate = file_candidate(
            unit.path,
            kind="knowledge-unit",
            reason=f"{package} unit {unit.hydra_id}",
            priority=UNIT_PRIORITY,
            paths=paths,
            source=unit.hydra_id,
            chars_per_token=chars_per_token,
        )
        candidate["required"] = unit.hydra_id in required_ids
        stale_sources = stale_unit_sources(unit, paths)
        if stale_sources:
            candidate["stale_sources"] = stale_sources
        result.append(candidate)
        for raw_path in unit.reads:
            path = resolve_context_path(raw_path, paths)
            if not path.exists() or not path.is_file():
                warnings.append(f"Unit read path not found: {package} / {unit.hydra_id} / {raw_path}")
                continue
            read_candidate = file_candidate(
                path,
                kind="knowledge-unit-read",
                reason=f"{package} / {unit.hydra_id} reads",
                priority=UNIT_READ_PRIORITY,
                paths=paths,
                source=unit.hydra_id,
                chars_per_token=chars_per_token,
            )
            read_candidate["required"] = False
            result.append(read_candidate)
    return result


def object_lookup(objects: list[dict]) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for obj in objects:
        lookup[obj["id"]] = obj
        for alias in obj["aliases"]:
            lookup[alias] = obj
    return lookup


def annotate_candidate(candidate: dict, by_path: dict[str, dict]) -> dict:
    annotated = dict(candidate)
    obj = by_path.get(candidate["path"])
    if obj:
        annotated["hydra_id"] = obj["id"]
        annotated["status"] = obj["status"]
        annotated["digest"] = obj["digest"]
        annotated["provenance_sources"] = obj["provenance_sources"]
    return annotated
