"""Deterministic restricted-YAML emitter used by Knowledge migration."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def text_digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def manifest_payload(manifest: dict) -> dict:
    return {key: value for key, value in manifest.items() if key not in {"plan_digest", "review"}}


def payload_digest(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return text_digest(canonical)


def review_manifest(payload: dict) -> dict:
    """Wrap a plan payload with its digest and an unapproved review block."""
    return {
        **payload,
        "plan_digest": payload_digest(payload),
        "review": {"approved": False, "approved_digest": "", "reviewer": "", "evidence": ""},
    }


def write_rows(writes: dict[str, str], modes: dict[str, int], sources: dict[str, str]) -> list[dict]:
    return [
        {
            "path": rel,
            "digest": text_digest(content),
            "mode": f"{modes[rel]:04o}" if rel in modes else "",
            "source": sources.get(rel, ""),
        }
        for rel, content in sorted(writes.items())
    ]


def write_review_manifest(manifest: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_review_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("migration review manifest must be a mapping")
    return data


def _quoted(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return json.dumps(str(value), ensure_ascii=True)


def _emit_sequence_mapping(emit, lines: list[str], item: dict, indent: int) -> None:
    """One mapping inside a sequence, first key merged onto the dash.

    The nested branch matters: emitting a mapping-valued first key through the
    sequence path dropped it silently, losing data with no unresolved entry and
    a plan digest that certified the loss as reviewed.
    """
    prefix = " " * indent
    for index, (child_key, child) in enumerate(item.items()):
        if index:
            emit(child, indent + 2, str(child_key))
            continue
        if isinstance(child, dict) and child:
            lines.append(f"{prefix}- {child_key}:")
            for nested_key, nested in child.items():
                emit(nested, indent + 4, str(nested_key))
        elif isinstance(child, list) and child:
            lines.append(f"{prefix}- {child_key}:")
            emit(child, indent + 4)
        elif isinstance(child, dict):
            lines.append(f"{prefix}- {child_key}: {{}}")
        elif isinstance(child, list):
            lines.append(f"{prefix}- {child_key}: []")
        else:
            lines.append(f"{prefix}- {child_key}: {_quoted(child)}")


def emit_yaml(data: dict) -> str:
    lines: list[str] = []

    def emit(value: object, indent: int, key: str | None = None) -> None:
        prefix = " " * indent
        if key is not None:
            if isinstance(value, dict):
                if not value:
                    lines.append(f"{prefix}{key}: {{}}")
                    return
                lines.append(f"{prefix}{key}:")
                for child_key, child in value.items():
                    emit(child, indent + 2, str(child_key))
                return
            if isinstance(value, list):
                if not value:
                    lines.append(f"{prefix}{key}: []")
                    return
                lines.append(f"{prefix}{key}:")
                emit(value, indent + 2)
                return
            lines.append(f"{prefix}{key}: {_quoted(value)}")
            return
        for item in value if isinstance(value, list) else []:
            if isinstance(item, dict):
                _emit_sequence_mapping(emit, lines, item, indent)
            elif isinstance(item, list):
                lines.append(f"{prefix}-")
                emit(item, indent + 2)
            else:
                lines.append(f"{prefix}- {_quoted(item)}")

    for top_key, top_value in data.items():
        emit(top_value, 0, str(top_key))
    return "\n".join(lines) + "\n"
