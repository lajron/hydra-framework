"""Namespaced Knowledge v3 logical-resource bindings and freshness checks."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from hydra_engine.documents.tokens import HydraYamlError, display_path, is_relative_to, read_text
from hydra_engine.documents.frontmatter_blocks import parse_yaml, yaml_list, yaml_map, yaml_str
from hydra_engine.finding import Finding
from hydra_engine.knowledge.nodes import KnowledgeNode, knowledge_root
from hydra_engine.knowledge.packages import ContextCompilerPaths

MANIFEST_SCHEMA = "hydra-framework.bindings-manifest.v1"
BINDINGS_SCHEMA = "hydra-framework.bindings.v1"
BINDING_KINDS = ("file", "directory", "glob")
LOGICAL_RE = re.compile(r"^@[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*(?:/[a-z0-9][a-z0-9-]*)*$")


@dataclasses.dataclass(frozen=True)
class Binding:
    logical_name: str
    namespace: str
    key: str
    target: str
    kind: str
    assertions: dict
    accepted_fingerprint: str
    source_path: Path


@dataclasses.dataclass(frozen=True)
class BindingStatus:
    binding: Binding
    state: str
    fingerprint: str
    errors: tuple[str, ...]


class BindingResolutionError(ValueError):
    pass


def bindings_root(paths: ContextCompilerPaths) -> Path:
    return knowledge_root(paths) / "bindings"


def _manifest_fragments(paths: ContextCompilerPaths) -> list[Path]:
    manifest = bindings_root(paths) / "manifest.yaml"
    data = parse_yaml(manifest, paths.root, required=True)
    if yaml_str(data.get("schema")) != MANIFEST_SCHEMA:
        raise HydraYamlError(f"{display_path(manifest, paths.root)} schema must be `{MANIFEST_SCHEMA}`")
    return [bindings_root(paths) / value for value in yaml_list(data.get("fragments"))]


def load_bindings(paths: ContextCompilerPaths) -> dict[str, Binding]:
    result: dict[str, Binding] = {}
    namespaces: set[str] = set()
    for path in _manifest_fragments(paths):
        data = parse_yaml(path, paths.root, required=True)
        if yaml_str(data.get("schema")) != BINDINGS_SCHEMA:
            raise HydraYamlError(f"{display_path(path, paths.root)} schema must be `{BINDINGS_SCHEMA}`")
        namespace = yaml_str(data.get("namespace"))
        if namespace in namespaces:
            raise BindingResolutionError(f"duplicate binding namespace `{namespace}`")
        namespaces.add(namespace)
        for key, raw in sorted(yaml_map(data.get("bindings")).items()):
            entry = yaml_map(raw)
            logical_name = f"@{namespace}/{key}"
            if logical_name in result:
                raise BindingResolutionError(f"duplicate logical binding `{logical_name}`")
            result[logical_name] = Binding(
                logical_name=logical_name,
                namespace=namespace,
                key=key,
                target=yaml_str(entry.get("target")),
                kind=yaml_str(entry.get("kind")),
                assertions=yaml_map(entry.get("assertions")),
                accepted_fingerprint=yaml_str(entry.get("accepted_fingerprint")),
                source_path=path,
            )
    return result


def _json_pointer(data: object, pointer: str) -> object:
    current = data
    for part in pointer.strip("/").split("/") if pointer.strip("/") else []:
        part = part.replace("~1", "/").replace("~0", "~")
        current = current[int(part)] if isinstance(current, list) else current[part]
    return current


def _yaml_selector(data: object, selector: str) -> object:
    current = data
    for part in selector.strip("/").replace("/", ".").split("."):
        if not part:
            continue
        if not isinstance(current, dict):
            raise KeyError(part)
        current = current[part]
    return current


def _identity_value(path: Path, fmt: str, selector: str, repo_root: Path) -> object:
    if fmt == "json":
        return _json_pointer(json.loads(read_text(path)), selector)
    if fmt == "yaml":
        return _yaml_selector(parse_yaml(path, repo_root, required=True), selector)
    if fmt == "xml":
        found = ET.parse(path).getroot().find(selector)
        if found is None:
            raise KeyError(selector)
        return found.text or ""
    if fmt == "text":
        text = read_text(path)
        match = re.search(selector, text)
        if not match:
            raise KeyError(selector)
        return match.group(1) if match.lastindex else match.group(0)
    raise ValueError(f"unsupported identity format `{fmt}`")


def verify_binding(binding: Binding, paths: ContextCompilerPaths) -> BindingStatus:
    errors: list[str] = []
    evidence: dict[str, object] = {"logical_name": binding.logical_name, "kind": binding.kind, "target": binding.target}
    target = (paths.root / binding.target).resolve()
    if not is_relative_to(target, paths.root):
        errors.append("target escapes repository root")
    if binding.kind not in BINDING_KINDS:
        errors.append(f"kind `{binding.kind}` is not one of {BINDING_KINDS}")
    matches: list[Path]
    if binding.kind == "glob":
        matches = sorted(path for path in paths.root.glob(binding.target) if path.exists())
        if not matches:
            errors.append("glob target has no matches")
        evidence["matches"] = [display_path(path, paths.root) for path in matches]
    else:
        matches = [target] if target.exists() else []
        if not matches:
            errors.append("target does not exist")
        elif binding.kind == "file" and not target.is_file():
            errors.append("target is not a file")
        elif binding.kind == "directory" and not target.is_dir():
            errors.append("target is not a directory")

    if matches:
        primary = matches[0]
        filename = yaml_str(binding.assertions.get("filename"))
        if filename:
            evidence["filename"] = primary.name
            if primary.name != filename:
                errors.append(f"filename assertion failed: expected `{filename}`, got `{primary.name}`")
        contains = yaml_list(binding.assertions.get("contains"))
        if contains:
            if not primary.is_dir():
                errors.append("contains assertion requires a directory target")
            else:
                evidence["contains"] = contains
                for marker in contains:
                    if not (primary / marker).exists():
                        errors.append(f"contains assertion failed: `{marker}` is missing")
        identity_evidence: list[dict[str, object]] = []
        raw_identity = binding.assertions.get("identity")
        identity_entries = [item for item in raw_identity if isinstance(item, dict)] if isinstance(raw_identity, list) else []
        for entry in identity_entries:
            source = yaml_str(entry.get("source"))
            fmt = yaml_str(entry.get("format"))
            selector = yaml_str(entry.get("selector"))
            expected = entry.get("equals")
            source_path = primary / source if primary.is_dir() else primary.parent / source
            try:
                actual = _identity_value(source_path, fmt, selector, paths.root)
            except (OSError, ValueError, KeyError, json.JSONDecodeError, ET.ParseError, HydraYamlError) as error:
                errors.append(f"identity assertion failed for `{source}`: {error}")
                continue
            identity_evidence.append({"source": source, "format": fmt, "selector": selector, "value": actual})
            if str(actual) != str(expected):
                errors.append(f"identity assertion failed for `{source}` `{selector}`: expected `{expected}`, got `{actual}`")
        if identity_evidence:
            evidence["identity"] = identity_evidence

    fingerprint = "sha256:" + hashlib.sha256(
        json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if errors:
        state = "unresolved" if not matches else "stale"
    elif not binding.accepted_fingerprint or binding.accepted_fingerprint != fingerprint:
        state = "stale"
        errors.append("assertion fingerprint is unreviewed or changed; run bindings verify --accept")
    else:
        state = "verified"
    return BindingStatus(binding, state, fingerprint, tuple(errors))


def record_accepted_fingerprint(binding: Binding, fingerprint: str, paths: ContextCompilerPaths) -> None:
    """Write one reviewed assertion fingerprint back into its fragment.

    A line-anchored edit rather than a re-serialisation, so accepting one
    binding never reformats the rest of a hand-authored fragment.
    """
    lines = binding.source_path.read_text(encoding="utf-8").splitlines()
    anchor = next(
        (index for index, line in enumerate(lines) if line.strip() == f"{binding.key}:" and line.startswith("  ")),
        None,
    )
    if anchor is None:
        raise BindingResolutionError(
            f"cannot record fingerprint: `{binding.key}` not found in {display_path(binding.source_path, paths.root)}"
        )
    indent = len(lines[anchor]) - len(lines[anchor].lstrip(" "))
    field_indent = " " * (indent + 2)
    end = anchor + 1
    while end < len(lines) and (not lines[end].strip() or len(lines[end]) - len(lines[end].lstrip(" ")) > indent):
        end += 1
    replacement = f'{field_indent}accepted_fingerprint: "{fingerprint}"'
    for index in range(anchor + 1, end):
        stripped = lines[index].strip()
        if stripped.startswith("accepted_fingerprint:") and len(lines[index]) - len(lines[index].lstrip(" ")) == indent + 2:
            lines[index] = replacement
            break
    else:
        lines.insert(anchor + 1, replacement)
    binding.source_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def resolve_binding(logical_name: str, bindings: dict[str, Binding], paths: ContextCompilerPaths) -> Path:
    binding = bindings.get(logical_name)
    if binding is None:
        raise BindingResolutionError(f"unresolved logical binding `{logical_name}`")
    status = verify_binding(binding, paths)
    if status.state != "verified":
        raise BindingResolutionError(f"binding `{logical_name}` is {status.state}: {'; '.join(status.errors)}")
    return (paths.root / binding.target).resolve()


def bound_nodes_for_paths(
    raw_paths: list[str], nodes: list[KnowledgeNode], bindings: dict[str, Binding], paths: ContextCompilerPaths,
) -> dict[str, str]:
    candidates: list[tuple[Path, str, str]] = []
    for node in nodes:
        if not node.binding:
            continue
        target = resolve_binding(node.binding, bindings, paths)
        candidates.append((target, node.logical_id, node.binding))
    result: dict[str, str] = {}
    for raw in raw_paths:
        path = (paths.root / raw).resolve() if not Path(raw).is_absolute() else Path(raw).resolve()
        matches = [(len(str(target)), node_id, logical) for target, node_id, logical in candidates if is_relative_to(path, target)]
        if not matches:
            continue
        best_length = max(item[0] for item in matches)
        best = sorted(item for item in matches if item[0] == best_length)
        if len(best) > 1:
            raise BindingResolutionError(f"ambiguous path binding for `{raw}`: {', '.join(item[2] for item in best)}")
        result[raw] = best[0][1]
    return result


def validate_bindings(paths: ContextCompilerPaths) -> list[Finding]:
    code = "knowledge-v3-binding"
    try:
        bindings = load_bindings(paths)
    except (HydraYamlError, BindingResolutionError) as error:
        return [Finding(path=".hydra-framework/repo/knowledge/bindings", code=code, detail=str(error))]
    findings: list[Finding] = []
    for logical_name, binding in sorted(bindings.items()):
        rel = display_path(binding.source_path, paths.root)
        if not LOGICAL_RE.match(logical_name):
            findings.append(Finding(path=rel, code=code, detail=f"invalid logical binding name `{logical_name}`"))
        status = verify_binding(binding, paths)
        for error in status.errors:
            findings.append(Finding(path=rel, code=code, detail=f"{logical_name}: {error}"))
    return findings
