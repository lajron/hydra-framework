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


def write_rows(writes: dict[str, str], modes: dict[str, int], sources: dict[str, str]) -> list[dict]:
    return [
        {
            "path": rel,
            "digest": text_digest(content),
            "mode": f"{modes.get(rel, 0o644):04o}",
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
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return json.dumps(str(value), ensure_ascii=True)


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
                for index, (child_key, child) in enumerate(item.items()):
                    if index == 0:
                        if isinstance(child, (dict, list)):
                            lines.append(f"{prefix}- {child_key}:")
                            emit(child, indent + 4)
                        else:
                            lines.append(f"{prefix}- {child_key}: {_quoted(child)}")
                    else:
                        emit(child, indent + 2, str(child_key))
            else:
                lines.append(f"{prefix}- {_quoted(item)}")

    for top_key, top_value in data.items():
        emit(top_value, 0, str(top_key))
    return "\n".join(lines) + "\n"
