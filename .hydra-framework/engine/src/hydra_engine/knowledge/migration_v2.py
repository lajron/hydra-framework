"""Review-gated, deterministic Knowledge v2 to v3 migration.

This module is the sole legacy reader.  Active Knowledge discovery never calls
it.  The review manifest contains digests and decisions, not duplicate file
payloads; apply rebuilds the plan and verifies the exact reviewed digest before
the first write.  Git checkpoint commits are the rollback boundary.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from hydra_engine.documents.yaml_documents import parse_yaml, parse_yaml_text, yaml_list, yaml_map, yaml_str
from hydra_engine.knowledge import migration_format, migration_git, migration_templates

MIGRATION_SCHEMA = "hydra-framework.knowledge-migration.v1"
SPACES_SCHEMA = "hydra-framework.knowledge-spaces.v1"
NODE_SCHEMA = "hydra-framework.knowledge-node.v1"
LEGACY_ROUTING_SCHEMA = "hydra-framework.package-routing.v2"


class MigrationError(ValueError):
    pass


@dataclasses.dataclass(frozen=True)
class MigrationPlan:
    manifest: dict
    writes: dict[str, str]
    modes: dict[str, int]
    deletes: tuple[str, ...]
    originals: dict[str, str]


def _frontmatter(text: str, path: Path, root: Path) -> tuple[dict | None, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    try:
        end = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration as error:
        raise MigrationError(f"unterminated frontmatter: {path.relative_to(root)}") from error
    data = parse_yaml_text("\n".join(lines[1:end]), path, root)
    return data, "\n".join(lines[end + 1:]).lstrip("\n")


def _typed_relations(value: object, package: str) -> list[dict]:
    relations: list[dict] = []
    for item in value if isinstance(value, list) else []:
        if isinstance(item, dict):
            relation_type = yaml_str(item.get("type"))
            target = yaml_str(item.get("target"))
        else:
            relation_type = "relates-to"
            target = str(item)
        if target == f"hydra://knowledge-package/{package}":
            target = f"hydra://knowledge-space/{package}"
        relations.append({"type": relation_type or "relates-to", "target": target})
    return relations


def _rewrite_refs(text: str, package: str, route_names: tuple[str, ...] = ()) -> str:
    old_root = f".hydra-framework/repo/knowledge/knowledge-packages/{package}"
    new_root = f".hydra-framework/repo/knowledge/spaces/{package}"
    rewritten = (
        text.replace(old_root, new_root)
        .replace(f"hydra://knowledge-package/{package}", f"hydra://knowledge-space/{package}")
        .replace(f"hydra://knowledge-slice/{package}/routing", f"hydra://knowledge-space/{package}")
    )
    for name in route_names:
        rewritten = rewritten.replace(
            f"{package}:{name}",
            f"hydra://knowledge-route/{package}/{name.replace('_', '-')}",
        )
    return rewritten


def _rewrite_moved_document(
    text: str,
    source: Path,
    root: Path,
    package: str,
    route_names: tuple[str, ...],
    *,
    overview: bool = False,
) -> str:
    data, body = _frontmatter(text, source, root)
    if data is None:
        return _rewrite_refs(text, package, route_names).replace("](routing.yaml)", "](space.yaml)")
    if overview:
        data["hydra_id"] = f"hydra://knowledge-slice/{package}/overview"
        data["kind"] = "knowledge-slice"
    data["relations"] = _typed_relations(data.get("relations"), package)
    data.pop("expand_when", None)
    rendered = "---\n" + migration_format.emit_yaml(data) + "---\n"
    if body:
        rendered += "\n" + body.rstrip() + "\n"
    return _rewrite_refs(rendered, package, route_names).replace("](routing.yaml)", "](space.yaml)")


def _converted_expansions(package_root: Path, routing: dict, root: Path) -> tuple[dict[str, list[dict]], list[dict], list[str]]:
    routes = yaml_map(routing.get("routes"))
    additions: dict[str, list[dict]] = {}
    evidence: list[dict] = []
    unresolved: list[str] = []
    for unit_path in sorted((package_root / "units").glob("*.md")) if (package_root / "units").is_dir() else []:
        data, _body = _frontmatter(unit_path.read_text(encoding="utf-8"), unit_path, root)
        raw = data.get("expand_when") if data else None
        if raw in (None, [], ""):
            continue
        entries = [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []
        unit_id = yaml_str(data.get("hydra_id")) if data else ""
        owners = [
            name for name, route_value in routes.items()
            if unit_id in {*yaml_list(yaml_map(route_value).get("priority_units")), *yaml_list(yaml_map(route_value).get("requires"))}
        ]
        convertible = entries and all(
            yaml_list(entry.get("when_paths")) and yaml_list(entry.get("read")) and yaml_str(entry.get("why"))
            for entry in entries
        )
        if not convertible or len(owners) != 1:
            unresolved.append(
                f"{unit_path.relative_to(root)} expand_when requires one owning route and when_paths/read/why"
            )
            continue
        additions.setdefault(owners[0], []).extend(entries)
        evidence.append({"unit": unit_id, "route": f"{package}:{owners[0]}", "count": len(entries)})
    return additions, evidence, unresolved


def _space_document(routing: dict, package: str, additions: dict[str, list[dict]]) -> str:
    routes: dict = {}
    for name, raw in sorted(yaml_map(routing.get("routes")).items()):
        route = yaml_map(raw)
        converted = {
            "use_when": yaml_list(route.get("use_when")),
            "priority_units": yaml_list(route.get("priority_units")),
            "requires": yaml_list(route.get("requires")),
            "avoid_by_default": yaml_list(route.get("avoid_by_default")),
            "verify": yaml_list(route.get("verify")),
            "expand_when": [*([item for item in route.get("expand_when", []) if isinstance(item, dict)] if isinstance(route.get("expand_when"), list) else []), *additions.get(name, [])],
        }
        if yaml_str(route.get("overrides")):
            converted["overrides"] = yaml_str(route.get("overrides"))
        routes[name] = converted
    node = {
        "schema": NODE_SCHEMA,
        "node": package,
        "hydra_id": f"hydra://knowledge-space/{package}",
        "uid": yaml_str(routing.get("uid")),
        "schema_version": 3,
        "kind": "knowledge-space",
        "title": yaml_str(routing.get("title"), package),
        "status": yaml_str(routing.get("status"), "active"),
        "scope": yaml_str(routing.get("scope"), "repo-local"),
        "owners": yaml_map(routing.get("owners")),
        "relations": _typed_relations(routing.get("relations"), package),
        "provenance": yaml_map(routing.get("provenance")),
        "role": "accountability-root",
        "routable": True,
        "state": "./state.md",
        "overview": "./overview.md",
        "keywords": yaml_list(routing.get("keywords")),
        "defaults": {},
        "routes": routes,
    }
    return migration_format.emit_yaml(node)


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def build_plan(root: Path, checkpoint_commit: str | None = None) -> MigrationPlan:
    root = root.resolve()
    knowledge = root / ".hydra-framework/repo/knowledge"
    legacy = knowledge / "knowledge-packages"
    spaces = knowledge / "spaces"
    package_roots = sorted(
        item for item in legacy.iterdir()
        if item.is_dir() and item.name != "templates"
    ) if legacy.is_dir() else []
    legacy_files = legacy.is_dir() and any(path.is_file() for path in legacy.rglob("*"))
    if not package_roots and not legacy_files and (knowledge / "spaces.yaml").is_file():
        payload = {
            "schema": MIGRATION_SCHEMA,
            "source_version": 2,
            "target_version": 3,
            "checkpoint_commit": checkpoint_commit or migration_git.checkpoint(root),
            "status": "already-v3",
            "packages": [], "writes": [], "deletes": [], "reference_rewrites": [],
            "preserved_uids": [], "identity_rewrites": [], "route_rewrites": [],
            "expand_when_conversions": [], "binding_candidates": [], "unresolved": [],
            "confidence": "high",
        }
        digest = migration_format.payload_digest(payload)
        return MigrationPlan({**payload, "plan_digest": digest, "review": {"approved": False, "approved_digest": "", "reviewer": "", "evidence": ""}}, {}, {}, (), {})

    writes: dict[str, str] = {}
    modes: dict[str, int] = {}
    originals: dict[str, str] = {}
    deletes: list[str] = []
    migration_templates.plan(legacy, knowledge, root, writes, modes, originals, deletes)
    package_rows: list[dict] = []
    package_routes: dict[str, tuple[str, ...]] = {}
    preserved_uids: list[dict] = []
    identity_rewrites: list[dict] = []
    route_rewrites: list[dict] = []
    conversions: list[dict] = []
    binding_candidates: set[tuple[str, str]] = set()
    unresolved: list[str] = []

    for package_root in package_roots:
        package = package_root.name
        routing_path = package_root / "routing.yaml"
        if not routing_path.is_file():
            unresolved.append(f"{_relative(package_root, root)} has no routing.yaml")
            continue
        routing = parse_yaml(routing_path, root, required=True)
        if yaml_str(routing.get("schema")) != LEGACY_ROUTING_SCHEMA:
            unresolved.append(f"{_relative(routing_path, root)} is not {LEGACY_ROUTING_SCHEMA}")
            continue
        declared = yaml_str(routing.get("package"))
        if declared != package:
            unresolved.append(f"{_relative(routing_path, root)} declares package `{declared}`, expected `{package}`")
            continue
        additions, converted, conversion_errors = _converted_expansions(package_root, routing, root)
        conversions.extend(converted)
        unresolved.extend(conversion_errors)
        target_root = spaces / package
        space_rel = _relative(target_root / "space.yaml", root)
        if (target_root / "space.yaml").exists():
            unresolved.append(f"target already exists: {space_rel}")
            continue
        writes[space_rel] = _space_document(routing, package, additions)
        modes[space_rel] = 0o644
        preserved_uids.append({"uid": yaml_str(routing.get("uid")), "from": yaml_str(routing.get("hydra_id")), "to": f"hydra://knowledge-space/{package}"})
        identity_rewrites.extend([
            {"from": f"hydra://knowledge-package/{package}", "to": f"hydra://knowledge-space/{package}", "use": "references"},
            {"from": f"hydra://knowledge-package/{package}", "to": f"hydra://knowledge-slice/{package}/overview", "use": "overview object"},
            {"from": f"hydra://knowledge-slice/{package}/routing", "to": f"hydra://knowledge-space/{package}", "use": "routing object"},
        ])
        route_names = tuple(sorted(yaml_map(routing.get("routes"))))
        package_routes[package] = route_names
        for route_name in route_names:
            route_rewrites.append({"from": f"{package}:{route_name}", "to": f"hydra://knowledge-route/{package}/{route_name.replace('_', '-')}"})

        for source in sorted(path for path in package_root.rglob("*") if path.is_file() and path != routing_path):
            target = target_root / source.relative_to(package_root)
            content = source.read_text(encoding="utf-8")
            originals[_relative(source, root)] = content
            rewritten = _rewrite_moved_document(
                content,
                source,
                root,
                package,
                route_names,
                overview=source.name == "overview.md",
            )
            writes[_relative(target, root)] = rewritten
            modes[_relative(target, root)] = source.stat().st_mode & 0o777
            data, _body = _frontmatter(content, source, root)
            if data and yaml_str(data.get("uid")):
                preserved_uids.append({"uid": yaml_str(data.get("uid")), "from": yaml_str(data.get("hydra_id")), "to": yaml_str(_frontmatter(rewritten, target, root)[0].get("hydra_id"))})
            if data:
                for raw in yaml_list(yaml_map(data.get("provenance")).get("sources")) + yaml_list(data.get("reads")):
                    if raw and not raw.startswith(("hydra://", "@")):
                        binding_candidates.add((_relative(target, root), raw))
            deletes.append(_relative(source, root))
        deletes.append(_relative(routing_path, root))
        originals[_relative(routing_path, root)] = routing_path.read_text(encoding="utf-8")
        package_rows.append({"package": package, "space": package, "source": _relative(package_root, root), "target": _relative(target_root, root), "confidence": "high"})

    spaces_config = {
        "schema": SPACES_SCHEMA,
        "default_depth": 3,
        "max_depth": 4,
        "spaces": [row["space"] for row in package_rows],
    }
    writes[_relative(knowledge / "spaces.yaml", root)] = migration_format.emit_yaml(spaces_config)
    modes[_relative(knowledge / "spaces.yaml", root)] = 0o644
    bindings_manifest = knowledge / "bindings/manifest.yaml"
    if not bindings_manifest.exists():
        writes[_relative(bindings_manifest, root)] = migration_format.emit_yaml({"schema": "hydra-framework.bindings-manifest.v1", "fragments": []})
        modes[_relative(bindings_manifest, root)] = 0o644

    moved_sources = set(deletes)
    reference_rewrites: list[dict] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file() and ".git" not in item.parts and ".hydra-framework.local" not in item.parts):
        rel = _relative(path, root)
        if rel in moved_sources or rel in writes:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rewritten = content
        for row in package_rows:
            package = row["package"]
            rewritten = _rewrite_refs(rewritten, package, package_routes[package])
        rewritten = migration_templates.rewrite_references(rewritten)
        if rewritten != content:
            writes[rel] = rewritten
            modes[rel] = path.stat().st_mode & 0o777
            originals[rel] = content
            reference_rewrites.append({"path": rel, "before": migration_format.text_digest(content), "after": migration_format.text_digest(rewritten)})

    write_rows = []
    for rel, content in sorted(writes.items()):
        source_match = next((item for item in deletes if item.endswith("/" + Path(rel).name)), "")
        write_rows.append({
            "path": rel,
            "digest": migration_format.text_digest(content),
            "mode": f"{modes.get(rel, 0o644):04o}",
            "source": source_match,
        })
    payload = {
        "schema": MIGRATION_SCHEMA,
        "source_version": 2,
        "target_version": 3,
        "checkpoint_commit": checkpoint_commit or migration_git.checkpoint(root),
        "status": "planned" if package_rows or deletes else "blocked",
        "packages": package_rows,
        "writes": write_rows,
        "deletes": [
            {"path": rel, "digest": migration_format.text_digest(originals[rel])}
            for rel in sorted(set(deletes))
        ],
        "reference_rewrites": reference_rewrites,
        "preserved_uids": sorted(preserved_uids, key=lambda row: (row["uid"], row["from"])),
        "identity_rewrites": sorted(identity_rewrites, key=lambda row: (row["from"], row["use"])),
        "route_rewrites": route_rewrites,
        "expand_when_conversions": conversions,
        "binding_candidates": [
            {"source": source, "path": path, "confidence": "candidate-only"}
            for source, path in sorted(binding_candidates)
        ],
        "unresolved": sorted(unresolved),
        "confidence": "high" if (package_rows or deletes) and not unresolved else "requires-review",
    }
    digest = migration_format.payload_digest(payload)
    manifest = {**payload, "plan_digest": digest, "review": {"approved": False, "approved_digest": "", "reviewer": "", "evidence": ""}}
    return MigrationPlan(manifest, writes, modes, tuple(sorted(set(deletes))), originals)


def apply_reviewed_plan(root: Path, reviewed_manifest: dict) -> MigrationPlan:
    if reviewed_manifest.get("schema") != MIGRATION_SCHEMA:
        raise MigrationError(f"review manifest schema must be `{MIGRATION_SCHEMA}`")
    review = reviewed_manifest.get("review") if isinstance(reviewed_manifest.get("review"), dict) else {}
    plan_digest = str(reviewed_manifest.get("plan_digest") or "")
    if review.get("approved") is not True or review.get("approved_digest") != plan_digest:
        raise MigrationError("migration manifest is not explicitly approved for its exact plan_digest")
    recomputed_digest = migration_format.payload_digest(migration_format.manifest_payload(reviewed_manifest))
    if recomputed_digest != plan_digest:
        raise MigrationError(
            f"review manifest payload digest mismatch: declared `{plan_digest}`, computed `{recomputed_digest}`"
        )
    if not str(review.get("reviewer") or "").strip() or not str(review.get("evidence") or "").strip():
        raise MigrationError("migration approval requires reviewer and evidence")
    if reviewed_manifest.get("unresolved"):
        raise MigrationError("migration manifest has unresolved decisions")
    checkpoint = str(reviewed_manifest.get("checkpoint_commit") or "")
    try:
        migration_git.require_clean(root, checkpoint)
    except ValueError as error:
        raise MigrationError(str(error)) from error
    current = build_plan(root, checkpoint_commit=checkpoint)
    if current.manifest["plan_digest"] != plan_digest:
        raise MigrationError(
            f"migration plan changed after review: reviewed `{plan_digest}`, current `{current.manifest['plan_digest']}`"
        )
    for rel, original in sorted(current.originals.items()):
        path = root / rel
        if not path.is_file() or path.read_text(encoding="utf-8") != original:
            raise MigrationError(f"source changed before apply: {rel}")
    for rel in current.writes:
        target = root / rel
        if target.exists() and rel not in current.originals:
            existing = target.read_text(encoding="utf-8")
            if existing != current.writes[rel]:
                raise MigrationError(f"target changed before apply: {rel}")
    for rel, content in sorted(current.writes.items()):
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        target.chmod(current.modes.get(rel, 0o644))
    for rel in current.deletes:
        path = root / rel
        if path.is_file():
            path.unlink()
    legacy = root / ".hydra-framework/repo/knowledge/knowledge-packages"
    if legacy.is_dir():
        for directory in sorted((item for item in legacy.rglob("*") if item.is_dir()), key=lambda item: len(item.parts), reverse=True):
            if not any(directory.iterdir()):
                directory.rmdir()
        if not any(legacy.iterdir()):
            legacy.rmdir()
    return current
