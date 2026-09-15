"""---
hydra_id: hydra://engine-module/object-handler-registry
uid: 01d1a598-c313-445e-a594-e8330c58a537
schema_version: 3
kind: engine-module
title: Object Handler Registry
status: active
scope: base-seed
owners:
  team: hydra
relations:
  - hydra://engine-module/object-family-registry
provenance:
  sources:
    - .hydra-framework/core/architecture.md
---

The object-handler registry is the second explicit extension registry.

An object handler answers, for one document form, the two questions
`objects.discovery` used to answer with a suffix switch: which files are
candidate object metadata, and where the envelope sits inside one. Before
this, `object_metadata_paths` hardcoded `*.md` plus `*.yaml`/`*.yml` with a
different exclusion rule inlined for each, and `extract_hydra_object`
branched on `path.suffix` again to choose a parser and the authored spellings
of `title` and `kind`. Adding a document form meant editing both, in two
different shapes -- an Open/Closed failure.

Boring data plus small functions: an explicit tuple
reviewed as code, no import-time scanning for handlers, and no handler
loaded merely because something was found on disk. Every field below is
populated by at least two of the three real handlers; nothing is here for a
hypothetical fourth.

The Python handler closes the Runtime/Engine
registration gap, and it is deliberately narrow in two ways:

- Its root is `engine/src` only. `scripts/hydra.py` is excluded because
  the architecture defines it as a compatibility surface rather than
  architecture, and the engine test tree is excluded because test fixtures
  author example `hydra://` ids on purpose -- 47 distinct ones today, none of
  them objects -- and `objects.references` requires every reference in a
  scanned file to resolve.
- A module is an object only if it declares an envelope, exactly as a
  Markdown file is. Registering this form did not turn all 103 engine
  modules into objects; envelope declarations currently live in three modules:
  `identity/object_families.py`, `objects/object_handlers.py`, and
  `checks/validator_registry.py`.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from pathlib import Path

from hydra_engine.documents.frontmatter_blocks import (
    first_declared_string,
    markdown_frontmatter,
    python_docstring_frontmatter,
    yaml_document_frontmatter,
)
from hydra_engine.documents.markdown import first_markdown_heading
from hydra_engine.documents.tokens import is_relative_to


@dataclasses.dataclass(frozen=True)
class ObjectHandler:
    """One document form and everything discovery needs to know about it.

    `title_keys` and `kind_keys` are ordered alternate authored spellings,
    read by `documents.frontmatter_blocks.first_declared_string`.
    `title_fallback` is the one place a title may come from outside the
    envelope: a Markdown document's own `# ` heading is a title a human
    wrote about it. A file name is not, so no handler has a fallback past
    that.

    `roots` are paths under `.hydra-framework/` this form may be authored in,
    empty meaning the whole tree. `excluded_roots` and `excluded_parts` are
    both here because the two rules the previous suffix switch inlined were
    genuinely different: YAML skipped exactly the top-level `cognition/`
    directory (derived state), while Markdown skipped any path component
    named `.git`, `node_modules`, `dist`, `build`, or `.hydra-framework.local`
    wherever it appeared.
    """

    name: str
    suffixes: tuple[str, ...]
    read_envelope: Callable[[Path, Path], dict]
    title_keys: tuple[str, ...]
    kind_keys: tuple[str, ...]
    title_fallback: Callable[[Path], str] | None = None
    roots: tuple[str, ...] = ()
    excluded_roots: tuple[str, ...] = ()
    excluded_parts: tuple[str, ...] = ()


OBJECT_HANDLERS = (
    ObjectHandler(
        name="Markdown",
        suffixes=(".md",),
        read_envelope=markdown_frontmatter,
        title_keys=("title",),
        kind_keys=("kind",),
        title_fallback=first_markdown_heading,
        excluded_parts=(".git", "node_modules", "dist", "build", ".hydra-framework.local"),
    ),
    ObjectHandler(
        name="YAML",
        suffixes=(".yaml", ".yml"),
        read_envelope=yaml_document_frontmatter,
        title_keys=("title", "name"),
        kind_keys=("hydra_object_kind", "kind"),
        excluded_roots=("cognition",),
    ),
    ObjectHandler(
        name="Python",
        suffixes=(".py",),
        read_envelope=python_docstring_frontmatter,
        title_keys=("title",),
        kind_keys=("kind",),
        roots=("engine/src",),
        excluded_parts=("__pycache__",),
    ),
)


def handler_for(path: Path) -> ObjectHandler | None:
    """The handler claiming this file's suffix, or None if no form claims it.

    None is a real answer, not an error: a sidecar may name a `.txt` or `.sh`
    file as an object, and such a file has no envelope of its own to read.
    """
    for handler in OBJECT_HANDLERS:
        if path.suffix in handler.suffixes:
            return handler
    return None


def _excluded(path: Path, hydra_root: Path, handler: ObjectHandler) -> bool:
    if any(part in handler.excluded_parts for part in path.parts):
        return True
    return any(is_relative_to(path, hydra_root / root) for root in handler.excluded_roots)


def object_document_paths(hydra_root: Path) -> list[Path]:
    """Every file under `.hydra-framework/` that some registered form claims."""
    found: set[Path] = set()
    for handler in OBJECT_HANDLERS:
        for root in handler.roots or ("",):
            base = hydra_root / root if root else hydra_root
            if not base.is_dir():
                continue
            for suffix in handler.suffixes:
                found.update(
                    path
                    for path in base.rglob(f"*{suffix}")
                    if not _excluded(path, hydra_root, handler)
                )
    return sorted(found)


def read_object_envelope(path: Path, root: Path) -> tuple[dict, str, str] | None:
    """`(data, title, kind)` for a file whose form is registered, else None.

    Raises `HydraYamlError` through the handler's reader, which the caller
    turns into a discovery error; the file existing in a claimed form but
    being unparseable is a different outcome from no form claiming it.
    """
    handler = handler_for(path)
    if handler is None:
        return None
    data = handler.read_envelope(path, root)
    title = first_declared_string(data, handler.title_keys)
    if not title and handler.title_fallback is not None:
        title = handler.title_fallback(path)
    return data, title, first_declared_string(data, handler.kind_keys)
