"""The restricted YAML subset Hydra metadata uses.

This subset gained one capability: a block sequence whose
items are themselves mappings (`- key: value` optionally followed by more
`key: value` lines indented under it), needed for a unit's or a
package-routing-v2 route's `expand_when` list. Every item in such a sequence
was previously read as one opaque scalar string; `LIST_ITEM_KEY_RE` is the
one addition that tells "this list item opens a mapping" apart from "this
list item is a bare scalar that happens to contain a colon" (an
`hydra://...` reference, for instance) -- checked against the whole tracked
tree before landing, since a false positive here would silently reinterpret
existing data.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from hydra_engine.documents.tokens import (
    HydraYamlError,
    display_path,
    read_text,
    reject_unsupported_yaml,
    yaml_scalar,
)

# A list item opens a mapping only when its first key looks like a plain
# identifier immediately followed by `:` and then whitespace-or-end -- never
# merely "contains a colon somewhere", which an `hydra://...` scalar also
# does. `hydra://x` fails this because the character right after `:` is `/`,
# not whitespace/end.
LIST_ITEM_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(\s|$)")


def _assign_mapping_value(container: dict, key: str, value: str, *, indent: int, entries: list, index: int, path: Path, root: Path, number: int) -> object | None:
    """Assign one already-split `key`/`value` pair into `container`.

    Returns the freshly opened child (list or dict) when `value` was empty
    and a nested block follows, so the caller can push it onto the indent
    stack; `None` when the assignment was a scalar or an inline `[]`/`{}`
    and there is nothing further to push.
    """
    if value in {"[]", "{}"}:
        container[key] = [] if value == "[]" else {}
        return None
    if value:
        reject_unsupported_yaml(path, number, value, root)
        container[key] = yaml_scalar(value)
        return None
    child: object = {}
    for next_indent, next_text, _next_number in entries[index + 1:]:
        if next_indent <= indent:
            break
        child = [] if next_text.startswith("-") else {}
        break
    container[key] = child
    return child


def parse_yaml_text(text: str, path: Path, root: Path) -> dict:
    """Parse the restricted YAML subset Hydra metadata uses."""
    entries: list[tuple[int, str, int]] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        if "\t" in raw:
            raise HydraYamlError(f"{display_path(path, root)}:{number}: tabs are not valid YAML indentation")
        stripped = raw.strip()
        if not stripped or stripped.startswith("#") or stripped in {"---", "..."}:
            continue
        entries.append((len(raw) - len(raw.lstrip(" ")), stripped, number))

    root_map: dict = {}
    stack: list[tuple[int, object]] = [(-1, root_map)]

    for index, (indent, text, number) in enumerate(entries):
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        container = stack[-1][1]

        if text == "-" or text.startswith("- "):
            if not isinstance(container, list):
                raise HydraYamlError(f"{display_path(path, root)}:{number}: list item outside a list")
            if text == "-":
                raise HydraYamlError(f"{display_path(path, root)}:{number}: empty list items are not supported")
            value = text[2:].strip()
            if value in {"[]", "{}"}:
                container.append([] if value == "[]" else {})
                continue
            match = LIST_ITEM_KEY_RE.match(value)
            if match:
                item: dict = {}
                container.append(item)
                stack.append((indent, item))
                key = match.group(1)
                rest = value[match.end():].strip()
                child = _assign_mapping_value(item, key, rest, indent=indent, entries=entries, index=index, path=path, root=root, number=number)
                if child is not None:
                    stack.append((indent + 2, child))
                continue
            reject_unsupported_yaml(path, number, value, root)
            container.append(yaml_scalar(value))
            continue

        if ":" not in text:
            raise HydraYamlError(f"{display_path(path, root)}:{number}: expected `key: value` or `- item`")
        if not isinstance(container, dict):
            raise HydraYamlError(f"{display_path(path, root)}:{number}: mapping key inside a list is not supported")

        key, _, value = text.partition(":")
        key = key.strip()
        value = value.strip()
        if not key:
            raise HydraYamlError(f"{display_path(path, root)}:{number}: empty mapping key")

        child = _assign_mapping_value(container, key, value, indent=indent, entries=entries, index=index, path=path, root=root, number=number)
        if child is not None:
            stack.append((indent, child))

    return root_map


def parse_yaml(path: Path, root: Path, *, required: bool = False) -> dict:
    """Parse the restricted YAML subset Hydra metadata uses."""
    if not path.exists():
        if required:
            raise HydraYamlError(f"{display_path(path, root)}: file not found")
        return {}
    return parse_yaml_text(read_text(path), path, root)


def yaml_list(value: object) -> list[str]:
    """Coerce a parsed YAML value to a list of strings."""
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str) and value.strip():
        return [part.strip() for part in value.split(",") if part.strip()]
    return []


def yaml_map(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def yaml_str(value: object, fallback: str = "") -> str:
    return value if isinstance(value, str) else fallback


def yaml_int(value: object, fallback: int = 0) -> int:
    if isinstance(value, bool):
        return fallback
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    return fallback


def yaml_quote(value: str) -> str:
    return json.dumps(value)
