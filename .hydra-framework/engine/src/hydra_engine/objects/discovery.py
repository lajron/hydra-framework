"""Object location and tree-walking discovery.

Which document forms exist, and where each keeps its envelope, moved to
`objects.object_handlers` (the second explicit extension registry). What
is left here is form-independent: where the tiers are, how a sidecar names
objects in other files, and how the two are collected together.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hydra_engine.documents.tokens import HydraYamlError, display_path
from hydra_engine.documents.yaml_documents import parse_yaml, yaml_map, yaml_str
from hydra_engine.objects.envelopes import build_hydra_object
from hydra_engine.objects.object_handlers import handler_for, object_document_paths, read_object_envelope

OBJECT_SIDECAR_SCHEMA = "hydra-framework.object-sidecar.v1"


@dataclass(frozen=True)
class ObjectLocations:
    root: Path
    hydra: Path
    local: Path
    personal_tasks_rel: str
    object_registry: Path

    def personal_tasks_root(self) -> Path:
        return self.hydra / self.personal_tasks_rel


def object_metadata_paths(paths: ObjectLocations) -> list[Path]:
    """Every file a registered document form claims.

    Kept as the name callers use (`objects.references` scans these files for
    references, `commands.object_moves` for stale path citations) while the
    set itself is now the registry's answer rather than a suffix list here.
    """
    return object_document_paths(paths.hydra)


def resolve_sidecar_object_path(sidecar_path: Path, raw_path: str, paths: ObjectLocations) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    if raw_path.startswith((".hydra-framework/", ".hydra-framework.local/", "project-wiki/")):
        return paths.root / raw_path
    return sidecar_path.parent / path


def extract_hydra_object(path: Path, paths: ObjectLocations) -> tuple[dict | None, str | None]:
    try:
        envelope = read_object_envelope(path, paths.root)
    except HydraYamlError as error:
        return None, str(error)
    if envelope is None:
        return None, None

    data, title, kind = envelope
    return build_hydra_object(path, data, title=title, kind=kind, envelope_path=path, paths=paths)


def extract_sidecar_objects(path: Path, paths: ObjectLocations) -> tuple[list[dict], list[str]]:
    # Not a document-form switch: OBJECT_SIDECAR_SCHEMA defines a sidecar as a
    # YAML file, so this asks whether `path` could be one at all, not which
    # handler owns it. Sidecars allow a form with nowhere to put an envelope,
    # such as a `.txt` or `.sh` file, to become an object. Directories cannot
    # become valid objects because sidecar construction fingerprints and reads
    # the target as text.
    if path.suffix not in {".yaml", ".yml"}:
        return [], []
    try:
        data = parse_yaml(path, paths.root)
    except HydraYamlError as error:
        return [], [str(error)]
    if yaml_str(data.get("schema")) != OBJECT_SIDECAR_SCHEMA:
        return [], []

    objects: list[dict] = []
    errors: list[str] = []
    entries = yaml_map(data.get("objects"))
    for name, raw in sorted(entries.items()):
        entry_path = f"{display_path(path, paths.root)} objects.{name}"
        entry = yaml_map(raw)
        if not entry:
            errors.append(f"{entry_path} must be a mapping")
            continue
        raw_object_path = yaml_str(entry.get("path"))
        if not raw_object_path:
            errors.append(f"{entry_path} is missing path")
            continue
        object_path = resolve_sidecar_object_path(path, raw_object_path, paths)
        if not object_path.exists():
            errors.append(f"{entry_path} points at missing path {raw_object_path}")
            continue
        title = yaml_str(entry.get("title"))
        handler = handler_for(object_path)
        if not title and handler is not None and handler.title_fallback is not None:
            # The object's own heading is a title a human wrote about it. The
            # file name is not, so there is deliberately no fallback past what
            # the handler declares: a sidecar entry for a directory, or for a
            # form with no in-document title, has to declare `title` rather
            # than be handed its own basename.
            title = handler.title_fallback(object_path)
        kind = yaml_str(entry.get("kind"))
        obj, error = build_hydra_object(object_path, entry, title=title, kind=kind, envelope_path=path, paths=paths)
        if error:
            errors.append(error.replace(display_path(path, paths.root), entry_path, 1))
        if obj:
            objects.append(obj)
    return objects, errors


def collect_hydra_objects(paths: ObjectLocations) -> tuple[list[dict], list[str]]:
    objects: list[dict] = []
    errors: list[str] = []
    for path in object_metadata_paths(paths):
        obj, error = extract_hydra_object(path, paths)
        if error:
            errors.append(error)
        if obj:
            objects.append(obj)
        if not error:
            sidecar_objects, sidecar_errors = extract_sidecar_objects(path, paths)
            objects.extend(sidecar_objects)
            errors.extend(sidecar_errors)
    return objects, errors
