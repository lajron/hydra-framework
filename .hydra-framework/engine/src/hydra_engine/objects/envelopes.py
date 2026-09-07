"""Object envelope construction and field-level text surgery.

`object_state_tier`/`object_display_path` live here rather than in
`discovery.py` because `build_hydra_object` needs both, and `discovery.py`'s
`extract_hydra_object`/`extract_sidecar_objects` need `build_hydra_object` -
splitting them across two files would make the two files import each other.
Their `paths` parameter is annotated as `ObjectLocations` (defined in
`discovery.py`) without importing it: nothing here calls a method on it, only
attributes duck-typed at the call site, and `from __future__ import
annotations` makes the annotation itself a string that is never evaluated -
so writing out the real name documents the contract without recreating the
cycle discovery.py's own dependency on this module would otherwise cause.
"""

from __future__ import annotations

from pathlib import Path

from hydra_engine.documents.digests import normalized_digest
from hydra_engine.documents.tokens import display_path, is_relative_to
from hydra_engine.documents.yaml_documents import yaml_list, yaml_map, yaml_str
from hydra_engine.identity.hydra_ids import HYDRA_ID_RE, hydra_refs_in_text
from hydra_engine.identity.object_families import family_for, unregistered_family_tokens
from hydra_engine.identity.schema_versions import envelope_schema_version


def object_state_tier(path: Path, paths: ObjectLocations) -> str:
    if is_relative_to(path, paths.local):
        return "private"
    if is_relative_to(path, paths.personal_tasks_root()):
        return "personal"
    if is_relative_to(path, paths.hydra):
        return "shared"
    return "external"


def object_display_path(path: Path, paths: ObjectLocations) -> str:
    if is_relative_to(path, paths.hydra):
        return f".hydra-framework/{path.resolve().relative_to(paths.hydra.resolve()).as_posix()}"
    if is_relative_to(path, paths.local):
        return f".hydra-framework.local/{path.resolve().relative_to(paths.local.resolve()).as_posix()}"
    return display_path(path, paths.root)


def resolved_envelope_path(display: str, paths: ObjectLocations) -> Path:
    """Reverse `object_display_path`: turn a tier-prefixed display path back
    into a real filesystem path under the tier actually in effect. Lives
    beside its inverse so both
    `commands.object_moves` and `commands.schema` -- which each need it --
    import it downward from the same layer-1 module rather than one
    commands module importing another."""
    if display.startswith(".hydra-framework/"):
        return paths.hydra / display.removeprefix(".hydra-framework/")
    if display.startswith(".hydra-framework.local/"):
        return paths.local / display.removeprefix(".hydra-framework.local/")
    return paths.root / display


def object_aliases(data: dict, path: Path, paths: ObjectLocations) -> tuple[list[str], str | None]:
    aliases: list[str] = []
    for alias in yaml_list(data.get("aliases")):
        hydra_alias = alias.lower()
        if not HYDRA_ID_RE.match(hydra_alias):
            return [], f"{display_path(path, paths.root)} has invalid hydra alias `{hydra_alias}`"
        aliases.append(hydra_alias)
    return sorted(set(aliases)), None


def missing_envelope_fields(data: dict, *, kind: str, title: str, status: str, scope: str) -> list[str]:
    """Which mandatory envelope fields this object does not actually carry.

    `kind`, `title`, and `status` arrive already resolved because each has a
    second spelling a human genuinely wrote: a YAML manifest declares its object
    kind as `hydra_object_kind`, its title as `name`, and its lifecycle state as
    `maturity`, and a Markdown object's title may be its own `# ` heading.
    Reading an alternate authored spelling is not defaulting. Substituting a
    value nobody wrote is, and that is what this function exists to catch.

    `relations` and `provenance.sources` are tested for presence of the key
    alone: an empty list is a real answer there (see
    EMPTY_ALLOWED_ENVELOPE_FIELDS), an absent key is not. `owners` is not in
    that pair - every object has an owner - so an empty owners map counts as
    absent.
    """
    missing = [
        name
        for name, value in (("kind", kind), ("title", title), ("status", status), ("scope", scope))
        if not value
    ]
    # Descendant Knowledge v3 nodes inherit owners from their accountability
    # chain.  The Knowledge validator proves that chain and requires owners on
    # spaces, so the generic object envelope must not demand a duplicate local
    # declaration on `knowledge-node` objects.
    if not yaml_map(data.get("owners")) and kind != "knowledge-node":
        missing.append("owners")
    if "relations" not in data:
        missing.append("relations")
    if "sources" not in yaml_map(data.get("provenance")):
        missing.append("provenance.sources")
    return missing


def build_hydra_object(
    path: Path,
    data: dict,
    *,
    title: str,
    kind: str,
    envelope_path: Path,
    paths: ObjectLocations,
) -> tuple[dict | None, str | None]:
    hydra_id = yaml_str(data.get("hydra_id")).lower()
    if not hydra_id:
        return None, None

    if not HYDRA_ID_RE.match(hydra_id):
        return None, f"{display_path(envelope_path, paths.root)} has invalid hydra_id `{hydra_id}`"

    aliases, alias_error = object_aliases(data, envelope_path, paths)
    if alias_error:
        return None, alias_error

    provenance = yaml_map(data.get("provenance"))
    owners = yaml_map(data.get("owners"))
    raw_relations = data.get("relations")
    relation_values = raw_relations if isinstance(raw_relations, list) else yaml_list(raw_relations)
    relations: list[str] = []
    for value in relation_values:
        relation_text = yaml_str(value.get("target")) if isinstance(value, dict) else str(value)
        relations.extend(hydra_refs_in_text(envelope_path, relation_text))

    # No defaults here on purpose. An absent field stays absent and is reported
    # by validation from ENVELOPE_REQUIRED_FROM_SCHEMA_VERSION onward; it is
    # never replaced with "active", "unspecified", or a kind read back out of
    # the hydra_id, all of which used to make an unauthored envelope read as an
    # authored one.
    status = yaml_str(data.get("status")) or yaml_str(data.get("maturity"))
    scope = yaml_str(data.get("scope"))
    family = family_for(hydra_id, kind)
    obj = {
        "id": hydra_id,
        "uid": yaml_str(data.get("uid")),
        "aliases": aliases,
        "kind": kind,
        "family": family,
        "title": title,
        "status": status,
        "scope": scope,
        "schema_version": envelope_schema_version(data),
        "tier": object_state_tier(path, paths),
        "owners": owners,
        "relations": sorted(set(relations)),
        "provenance_sources": yaml_list(provenance.get("sources")),
        "path": object_display_path(path, paths),
        "envelope_path": object_display_path(envelope_path, paths),
        "digest": normalized_digest(path),
        "missing_envelope_fields": missing_envelope_fields(
            data, kind=kind, title=title, status=status, scope=scope
        ),
        # Recorded here, beside `missing_envelope_fields` and for the same
        # reason: family resolution already happens on this line, so asking
        # the registry what it could not claim costs one more call rather
        # than a second pass over every object during validation.
        "unregistered_family_tokens": unregistered_family_tokens(hydra_id, kind),
    }
    return obj, None


def envelope_field_line_index(lines: list[str], field: str, value: str) -> int | None:
    needle = f"{field}: {value}".strip().lower()
    for index, line in enumerate(lines):
        if line.strip().lower() == needle:
            return index
    return None


def envelope_block_end(lines: list[str], start: int, indent: int) -> int:
    """Exclusive end of the mapping block `start` belongs to.

    Sibling fields of the same object sit at the same indent as `start`
    (frontmatter keys, a sidecar entry's fields, or a standalone YAML
    object's root keys); nested values (owners, relations, provenance) sit
    deeper. The block ends at the frontmatter close, at end of file, or at
    the first line indented *less* than `start` - the next sidecar entry or
    the next top-level section.
    """
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped in {"---", "..."}:
            return index
        if not stripped:
            continue
        current_indent = len(lines[index]) - len(lines[index].lstrip(" "))
        if current_indent < indent:
            return index
    return len(lines)


def replace_envelope_field(text: str, hydra_id: str, field: str, value: str) -> tuple[str, bool]:
    """Rewrite one field of the envelope block named by `hydra_id`.

    Only fields at the envelope's own indent are eligible, so rewriting
    `path` cannot hit a `path` nested under `provenance` or `owners`. Returns
    unchanged text and False when the object or the field is not there;
    the caller decides whether that is an error.
    """
    lines = text.splitlines()
    anchor = envelope_field_line_index(lines, "hydra_id", hydra_id)
    if anchor is None:
        return text, False
    indent = len(lines[anchor]) - len(lines[anchor].lstrip(" "))
    end = envelope_block_end(lines, anchor, indent)
    prefix = f"{field}:"
    for index in range(anchor, end):
        line = lines[index]
        if len(line) - len(line.lstrip(" ")) != indent:
            continue
        if line.strip().lower().startswith(prefix):
            lines[index] = " " * indent + f"{field}: {value}"
            newline = "\n" if text.endswith("\n") else ""
            return "\n".join(lines) + newline, True
    return text, False
