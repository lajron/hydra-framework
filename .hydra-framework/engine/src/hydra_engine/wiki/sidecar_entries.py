"""Read the supported provenance subset of a wiki object sidecar.

This is deliberately a small, line-based reader rather than a second general
YAML parser. Wiki sidecars use one stable block shape, and keeping this reader
local lets the audit and the later fingerprint writer preserve unrelated
fields and comments.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from hydra_engine.documents.tokens import HydraYamlError, display_path, read_text, reject_unsupported_yaml, yaml_scalar

OBJECT_SIDECAR_SCHEMA = "hydra-framework.object-sidecar.v1"
SOURCE_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class SidecarParseError(HydraYamlError):
    """A wiki sidecar is outside the supported restricted grammar."""


@dataclass(frozen=True)
class SidecarEntry:
    """The fields consumed by wiki freshness reporting and fingerprinting."""

    name: str
    hydra_id: str
    path: str
    checked_on: str
    provenance: dict[str, object]

    @property
    def sources(self) -> list[str]:
        value = self.provenance.get("sources")
        return list(value) if isinstance(value, list) else []

    @property
    def source_digests(self) -> list[dict[str, str]]:
        value = self.provenance.get("source_digests")
        return list(value) if isinstance(value, list) else []


def _fail(path: Path, root: Path, number: int, detail: str) -> None:
    raise SidecarParseError(f"{display_path(path, root)}:{number}: {detail}")


def _lines(text: str, path: Path, root: Path) -> list[tuple[int, int, str]]:
    result: list[tuple[int, int, str]] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        if "\t" in raw:
            _fail(path, root, number, "tabs are not valid YAML indentation")
        stripped = raw.strip()
        if not stripped or stripped.startswith("#") or stripped in {"---", "..."}:
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent % 2:
            _fail(path, root, number, "ambiguous indentation; use two-space levels")
        result.append((number, indent, stripped))
    return result


def _mapping(line: tuple[int, int, str], path: Path, root: Path) -> tuple[str, str]:
    number, _indent, text = line
    if ":" not in text:
        _fail(path, root, number, "expected `key: value`")
    key, _separator, value = text.partition(":")
    key = key.strip()
    if not key:
        _fail(path, root, number, "empty mapping key")
    return key, value.strip()


def _scalar(value: str, line: tuple[int, int, str], path: Path, root: Path, *, allow_empty: bool = False) -> str:
    number = line[0]
    if not value and not allow_empty:
        _fail(path, root, number, "value must not be empty")
    if value:
        reject_unsupported_yaml(path, number, value, root)
    return yaml_scalar(value)


def _string_list(
    lines: list[tuple[int, int, str]],
    start: int,
    end: int,
    path: Path,
    root: Path,
) -> list[str]:
    line = lines[start]
    value = _mapping(line, path, root)[1]
    if value == "[]":
        return []
    if value:
        reject_unsupported_yaml(path, line[0], value, root)
        _fail(path, root, line[0], "provenance.sources must be a list")

    items: list[str] = []
    index = start + 1
    while index < end and lines[index][1] > 6:
        item = lines[index]
        if item[1] != 8 or not item[2].startswith("- "):
            _fail(path, root, item[0], "provenance.sources must contain scalar list items")
        raw = item[2][2:].strip()
        if not raw or re.match(r"^[A-Za-z_][A-Za-z0-9_-]*:\s", raw):
            _fail(path, root, item[0], "provenance.sources must contain scalar list items")
        source = _scalar(raw, item, path, root)
        if source in items:
            _fail(path, root, item[0], f"duplicate provenance source: {source}")
        items.append(source)
        index += 1
    if not items:
        _fail(path, root, line[0], "provenance.sources must be a list")
    return items


def _digest_list(
    lines: list[tuple[int, int, str]],
    start: int,
    end: int,
    path: Path,
    root: Path,
) -> list[dict[str, str]]:
    line = lines[start]
    value = _mapping(line, path, root)[1]
    if value == "[]":
        return []
    if value:
        reject_unsupported_yaml(path, line[0], value, root)
        _fail(path, root, line[0], "provenance.source_digests must be a list")

    entries: list[dict[str, str]] = []
    seen_sources: set[str] = set()
    index = start + 1
    while index < end and lines[index][1] > 6:
        item = lines[index]
        if item[1] != 8 or not item[2].startswith("- "):
            _fail(path, root, item[0], "malformed provenance.source_digests entry")
        first = item[2][2:].strip()
        if not first or ":" not in first:
            _fail(path, root, item[0], "malformed provenance.source_digests entry")
        key, _separator, raw_value = first.partition(":")
        key = key.strip()
        if key not in {"source", "digest"}:
            _fail(path, root, item[0], "malformed provenance.source_digests entry")
        entry: dict[str, str] = {}
        entry[key] = _scalar(raw_value.strip(), item, path, root)
        index += 1
        while index < end and lines[index][1] > 8:
            continuation = lines[index]
            if continuation[1] != 10:
                _fail(path, root, continuation[0], "ambiguous indentation in provenance.source_digests")
            continuation_key, continuation_value = _mapping(continuation, path, root)
            if continuation_key not in {"source", "digest"} or continuation_key in entry:
                _fail(path, root, continuation[0], "malformed provenance.source_digests entry")
            entry[continuation_key] = _scalar(continuation_value, continuation, path, root)
            index += 1
        if set(entry) != {"source", "digest"}:
            _fail(path, root, item[0], "malformed provenance.source_digests entry")
        source = entry["source"]
        digest = entry["digest"]
        if not source or not SOURCE_DIGEST_RE.fullmatch(digest):
            _fail(path, root, item[0], "malformed provenance.source_digests entry")
        if source in seen_sources:
            _fail(path, root, item[0], f"duplicate provenance source digest: {source}")
        seen_sources.add(source)
        entries.append(entry)
    if not entries:
        _fail(path, root, line[0], "provenance.source_digests must be a list")
    return entries


def _provenance(
    lines: list[tuple[int, int, str]],
    start: int,
    end: int,
    path: Path,
    root: Path,
) -> dict[str, object]:
    line = lines[start]
    if _mapping(line, path, root)[1]:
        _fail(path, root, line[0], "provenance must be a mapping block")
    result: dict[str, object] = {}
    seen: set[str] = set()
    index = start + 1
    while index < end:
        current = lines[index]
        if current[1] < 6:
            break
        if current[1] != 6:
            index += 1
            continue
        key, _value = _mapping(current, path, root)
        if key in {"sources", "source_digests"}:
            if key in seen:
                _fail(path, root, current[0], f"duplicate provenance key: {key}")
            seen.add(key)
            if key == "sources":
                result[key] = _string_list(lines, index, end, path, root)
            else:
                result[key] = _digest_list(lines, index, end, path, root)
        index += 1
    if "sources" not in result:
        _fail(path, root, line[0], "missing provenance.sources block")
    sources = result["sources"]
    digests = result.get("source_digests", [])
    if isinstance(digests, list) and any(item["source"] not in sources for item in digests):
        _fail(path, root, line[0], "provenance.source_digests names an undeclared source")
    return result


def _entry(
    name: str,
    lines: list[tuple[int, int, str]],
    start: int,
    end: int,
    path: Path,
    root: Path,
) -> SidecarEntry:
    values: dict[str, str] = {}
    provenance: dict[str, object] | None = None
    seen: set[str] = set()
    index = start + 1
    while index < end:
        line = lines[index]
        if line[1] != 4:
            index += 1
            continue
        key, value = _mapping(line, path, root)
        if key in {"hydra_id", "path", "checked_on", "provenance"}:
            if key in seen:
                _fail(path, root, line[0], f"duplicate object key: {key}")
            seen.add(key)
        if key == "provenance":
            provenance = _provenance(lines, index, end, path, root)
        elif key in {"hydra_id", "path", "checked_on"}:
            values[key] = _scalar(value, line, path, root, allow_empty=key == "checked_on")
        index += 1
    for required in ("hydra_id", "path"):
        if not values.get(required):
            _fail(path, root, lines[start][0], f"object {name} is missing {required}")
    if provenance is None:
        _fail(path, root, lines[start][0], f"object {name} is missing provenance block")
    return SidecarEntry(
        name=name,
        hydra_id=values["hydra_id"],
        path=values["path"],
        checked_on=values.get("checked_on", ""),
        provenance=provenance,
    )


def _parse_sidecar_text(text: str, path: Path, root: Path) -> tuple[list[SidecarEntry], list[tuple[int, int, str]]]:
    lines = _lines(text, path, root)
    schema: str | None = None
    objects_index: int | None = None
    for index, line in enumerate(lines):
        if line[1] != 0:
            continue
        key, value = _mapping(line, path, root)
        if key == "schema":
            schema = _scalar(value, line, path, root)
        elif key == "objects":
            objects_index = index
            if value == "{}":
                return [], lines
            if value:
                reject_unsupported_yaml(path, line[0], value, root)
                _fail(path, root, line[0], "objects must be a mapping block")
    if schema != OBJECT_SIDECAR_SCHEMA:
        _fail(path, root, 1, "not a Hydra object sidecar")
    if objects_index is None:
        _fail(path, root, 1, "missing objects block")

    entries: list[SidecarEntry] = []
    names: set[str] = set()
    hydra_ids: set[str] = set()
    index = objects_index + 1
    while index < len(lines):
        line = lines[index]
        if line[1] == 0:
            index += 1
            continue
        if line[1] != 2 or not line[2].endswith(":"):
            _fail(path, root, line[0], "object names must be two-space mapping keys")
        name = line[2][:-1].strip()
        if not name:
            _fail(path, root, line[0], "empty object name")
        if name in names:
            _fail(path, root, line[0], f"duplicate object name: {name}")
        end = index + 1
        while end < len(lines) and lines[end][1] > 2:
            end += 1
        entry = _entry(name, lines, index, end, path, root)
        if entry.hydra_id.lower() in hydra_ids:
            _fail(path, root, line[0], f"duplicate hydra_id: {entry.hydra_id}")
        names.add(name)
        hydra_ids.add(entry.hydra_id.lower())
        entries.append(entry)
        index = end
    return entries, lines


def read_sidecar_entries(path: Path, root: Path) -> list[SidecarEntry]:
    """Read all provenance-bearing entries from one canonical wiki sidecar."""
    entries, _lines = _parse_sidecar_text(read_text(path), path, root)
    return entries


def _logical_block_end(lines: list[tuple[int, int, str]], start: int, limit: int) -> int:
    indent = lines[start][1]
    return next((index for index in range(start + 1, limit) if lines[index][1] <= indent), limit)


def _field_index(
    lines: list[tuple[int, int, str]],
    start: int,
    end: int,
    indent: int,
    key: str,
) -> int | None:
    return next(
        (index for index in range(start, end)
         if lines[index][1] == indent and lines[index][2].partition(":")[0].strip() == key),
        None,
    )


def _digest_block(entries: list[tuple[str, str]], ending: str) -> list[str]:
    block = [f"      source_digests:{ending}"]
    for source, digest in entries:
        block.extend((f"        - source: {source}{ending}", f"          digest: {digest}{ending}"))
    return block


def replace_sidecar_fingerprint(
    content: str,
    *,
    path: Path,
    root: Path,
    hydra_id: str,
    entries: list[tuple[str, str]],
    checked_on: str,
) -> str:
    """Replace one entry's checked date and source digests in a sidecar."""
    parsed, lines = _parse_sidecar_text(content, path, root)
    matches = [entry for entry in parsed if entry.hydra_id == hydra_id]
    if not matches:
        raise SidecarParseError(f"page not found: {hydra_id}")
    if len(matches) != 1:
        raise SidecarParseError(f"duplicate hydra_id: {hydra_id}")
    target = matches[0]
    if not entries:
        raise SidecarParseError("provenance.sources must not be empty")
    if {source for source, _digest in entries} != set(target.sources):
        raise SidecarParseError("fingerprint entries must match provenance.sources")

    raw_lines = content.splitlines(keepends=True)
    ending = "\r\n" if any(line.endswith("\r\n") for line in raw_lines) else "\n"
    object_start = next(index for index, line in enumerate(lines) if line[1] == 2 and line[2] == f"{target.name}:")
    object_end = _logical_block_end(lines, object_start, len(lines))
    provenance = _field_index(lines, object_start + 1, object_end, 4, "provenance")
    if provenance is None:
        raise SidecarParseError(f"object {target.name} is missing provenance block")
    provenance_end = _logical_block_end(lines, provenance, object_end)
    sources = _field_index(lines, provenance + 1, provenance_end, 6, "sources")
    if sources is None:
        raise SidecarParseError(f"object {target.name} is missing provenance.sources block")
    source_digests = _field_index(lines, provenance + 1, provenance_end, 6, "source_digests")
    checked = _field_index(lines, object_start + 1, object_end, 4, "checked_on")

    changes: list[tuple[int, int, list[str]]] = []
    if checked is None:
        insert_at = lines[provenance][0] - 1
        changes.append((insert_at, insert_at, [f"    checked_on: '{checked_on}'{ending}"]))
    else:
        raw_index = lines[checked][0] - 1
        changes.append((raw_index, raw_index + 1, [f"    checked_on: '{checked_on}'{ending}"]))

    block = _digest_block(entries, ending)
    if source_digests is None:
        source_end = _logical_block_end(lines, sources, provenance_end)
        insert_at = lines[source_end - 1][0]
        changes.append((insert_at, insert_at, block))
    else:
        digest_end = _logical_block_end(lines, source_digests, provenance_end)
        raw_start = lines[source_digests][0] - 1
        raw_end = lines[digest_end - 1][0]
        preserved = [line for line in raw_lines[raw_start:raw_end] if not line.strip() or line.lstrip().startswith("#")]
        changes.append((raw_start, raw_end, block + preserved))

    for start, end, replacement in sorted(changes, reverse=True):
        raw_lines[start:end] = replacement
    return "".join(raw_lines)
