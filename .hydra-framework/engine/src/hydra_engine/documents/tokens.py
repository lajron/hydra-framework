"""Raw YAML token shapes and path/text primitives.

The line-level tokenizer `yaml_documents.py` parses on top of, plus the
handful of path-and-text primitives every other document module needs. Kept
free of any internal import so it can carry high in-degree without tripping
the widely-imported-vocabulary check (check 4): a module reached by more than
ten others must either import nothing internally or stay under 150 lines.
This one does both.

`write_text` is the concurrent-write-correctness chokepoint (Hydra roadmap
item 2's append-only amendment): a temp file in the same directory is
written in full, then `os.replace` swaps it into place atomically, so a
concurrent reader always sees a complete old or new file, never a truncated
one, and a process that dies mid-write leaves only a stray `.hydra-tmp-*`
file rather than a corrupted target. `_before_replace` is a test-only seam
(same pattern as `ports.clock`/`ports.uids`): tests patch it to inject a
callback between the temp-write and the replace to reproduce an exact
crash or competing-writer interleaving deterministically, with no threads.
"""

from __future__ import annotations

import functools
import os
import re
from pathlib import Path
from typing import Callable

_before_replace: Callable[[Path], None] | None = None


class HydraYamlError(ValueError):
    """A Hydra YAML file uses a construct this parser cannot represent."""


BLOCK_SCALAR_RE = re.compile(r"^[|>][-+]?\d*$")
YAML_ALIAS_RE = re.compile(r"^\*[A-Za-z_][\w-]*$")
BRACE_SET_RE = re.compile(r"\{([^{}]+)\}")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.hydra-tmp-{os.getpid()}")
    try:
        tmp.write_text(content, encoding="utf-8")
        if _before_replace is not None:
            _before_replace(path)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


@functools.lru_cache(maxsize=None)
def _resolved(path: Path) -> Path:
    # `object_display_path`/`object_state_tier` call `is_relative_to` several
    # times per object against the same few tier roots (`paths.root`,
    # `paths.hydra`, `paths.local`); resolving each of those roots freshly on
    # every call re-pays `Path.resolve()`'s filesystem work for a value that
    # cannot change within one `hydra.py` invocation.
    return path.resolve()


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        _resolved(path).relative_to(_resolved(parent))
        return True
    except ValueError:
        return False


def display_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix() if is_relative_to(path, root) else str(path)


def expand_brace_sets(pattern: str) -> list[str]:
    match = BRACE_SET_RE.search(pattern)
    if not match:
        return [pattern]
    expanded: list[str] = []
    for option in match.group(1).split(","):
        candidate = pattern[: match.start()] + option.strip() + pattern[match.end():]
        expanded.extend(expand_brace_sets(candidate))
    return expanded


def cited_source_path_missing(raw: str, citation_dir: Path, repo_root: Path) -> bool:
    """Whether a cited repository path fails to resolve."""
    base = citation_dir if raw.startswith("./") or raw.startswith("../") else repo_root
    first = expand_brace_sets(raw)[0].split("/")[0]
    if not (base / first).exists():
        return False
    for candidate in expand_brace_sets(raw):
        wants_dir = candidate.endswith("/")
        candidate = candidate.rstrip("/")
        if not candidate:
            return True
        if "*" in candidate:
            if not any(base.glob(candidate)):
                return True
            continue
        target = base / candidate
        if wants_dir:
            if not target.is_dir():
                return True
        elif not target.exists():
            return True
    return False


def yaml_scalar(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    return text


def reject_unsupported_yaml(path: Path, number: int, value: str, root: Path) -> None:
    """Fail loudly on YAML this parser would otherwise misread."""
    if value.startswith("&"):
        raise HydraYamlError(f"{display_path(path, root)}:{number}: YAML anchors are not supported")
    if YAML_ALIAS_RE.match(value):
        raise HydraYamlError(f"{display_path(path, root)}:{number}: YAML aliases are not supported")
    if BLOCK_SCALAR_RE.match(value):
        raise HydraYamlError(f"{display_path(path, root)}:{number}: block scalars (`|`, `>`) are not supported")
    if value[:1] in "\"'" and not (len(value) >= 2 and value[-1] == value[0]):
        raise HydraYamlError(f"{display_path(path, root)}:{number}: unterminated quoted value")
    if (value.startswith("[") and value.endswith("]")) or (value.startswith("{") and value.endswith("}")):
        raise HydraYamlError(f"{display_path(path, root)}:{number}: non-empty YAML flow collections are not supported")
