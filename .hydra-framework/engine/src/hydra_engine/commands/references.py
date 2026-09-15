"""references command decisions:
ref resolve, ref check, ref index.

`resolver_paths: ObjectLocations` is a bare forward-reference type hint (no
real import), matching the established codebase-wide convention for this
exact parameter.
"""

from __future__ import annotations

import sys

from hydra_engine.commands import CommandResult
from hydra_engine.commands import store as store_commands
from hydra_engine.documents.tokens import display_path
from hydra_engine.identity.schema_versions import CURRENT_SCHEMA_VERSION
from hydra_engine.objects import store_queries
from hydra_engine.objects.discovery import collect_hydra_objects
from hydra_engine.objects.references import validate_object_references
from hydra_engine.objects.registry import validate_object_registry_freshness, write_object_registry

store_status = store_queries.store_status


def _print_resolution(obj: dict, target: str) -> None:
    """Shared by the store-backed and scan-backed `ref resolve` paths so the
    two are byte-identical. `provenance_sources` is sorted
    here regardless of source: the scan path preserves an object's declared
    order today, but the store has no column to remember that order (only
    `hydra_id`/`source_path` pairs), so a canonical sort is the one order
    both paths can produce identically."""
    for key in ["id", "family", "kind", "title", "status", "tier", "scope", "path", "digest"]:
        print(f"{key}: {obj[key]}")
    if target != obj["id"]:
        print(f"resolved_from_alias: {target}")
    if obj["aliases"]:
        print("aliases:")
        for alias in obj["aliases"]:
            print(f"- {alias}")
    if obj["envelope_path"] != obj["path"]:
        print(f"envelope_path: {obj['envelope_path']}")
    if obj["relations"]:
        print("relations:")
        for relation in obj["relations"]:
            print(f"- {relation}")
    provenance_sources = sorted(obj["provenance_sources"])
    if provenance_sources:
        print("provenance_sources:")
        for source in provenance_sources:
            print(f"- {source}")


def command_ref_resolve(args, resolver_paths) -> CommandResult:
    """Reads from the operational store when it is fresh,
    falling back to today's full-tree scan-and-filter otherwise. A fresh
    store's `objects`/`aliases` are rebuilt wholesale from the same validated
    export `ref check`/`validate` already trust, so "not found in a fresh
    store" is as authoritative as "not found in a scan" -- there is no third
    "maybe the store missed it" case to handle."""
    target = args.hydra_id.lower()

    conn = store_queries.open_fresh_store(resolver_paths, resolver_paths.local)
    if conn is not None:
        try:
            obj = store_queries.resolve(conn, target)
        finally:
            conn.close()
        if obj is None:
            print(f"Hydra object not found: {args.hydra_id}", file=sys.stderr)
            print("source=sqlite", file=sys.stderr)
            return CommandResult(1)
        _print_resolution({**obj, "id": obj["hydra_id"]}, target)
        print("source=sqlite", file=sys.stderr)
        return CommandResult(0)

    objects, errors = collect_hydra_objects(resolver_paths)
    if errors:
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return CommandResult(1)
    matches = [obj for obj in objects if obj["id"] == target or target in obj["aliases"]]
    if not matches:
        print(f"Hydra object not found: {args.hydra_id}", file=sys.stderr)
        print("source=scan", file=sys.stderr)
        return CommandResult(1)
    if len({obj["id"] for obj in matches}) > 1:
        print(f"Hydra object reference is ambiguous: {args.hydra_id}", file=sys.stderr)
        print("source=scan", file=sys.stderr)
        return CommandResult(1)
    _print_resolution(matches[0], target)
    print("source=scan", file=sys.stderr)
    return CommandResult(0)


def command_ref_rdeps(args, resolver_paths) -> CommandResult:
    """Reverse relations through the object store's `citers_of` query.

    The command does not query the store's `refs` table. A missing or stale
    store is reported rather than degraded to a scan because reverse relation
    lookup has no scan-based equivalent here.
    """
    conn = store_queries.open_fresh_store(resolver_paths, resolver_paths.local)
    if conn is None:
        print("Hydra ref store: not available (missing, stale, or disabled); run `hydra.py ref store rebuild`.", file=sys.stderr)
        return CommandResult(1)
    try:
        target = args.hydra_id.lower()
        obj = store_queries.resolve(conn, target)
        if obj is None:
            print(f"Hydra object not found: {args.hydra_id}", file=sys.stderr)
            return CommandResult(1)
        rdeps = store_queries.citers_of(conn, target)
    finally:
        conn.close()
    print(f"id: {obj['hydra_id']}")
    if rdeps:
        print("rdeps:")
        for citer in rdeps:
            print(f"- {citer}")
    else:
        print("rdeps: none")
    return CommandResult(0)


def command_ref_impact(args, resolver_paths) -> CommandResult:
    """Transitive impact radius over outbound relations, within `--depth`
    hops. No scan-based equivalent exists today, so a
    missing/stale store is reported rather than degraded to a scan."""
    conn = store_queries.open_fresh_store(resolver_paths, resolver_paths.local)
    if conn is None:
        print("Hydra ref store: not available (missing, stale, or disabled); run `hydra.py ref store rebuild`.", file=sys.stderr)
        return CommandResult(1)
    try:
        target = args.hydra_id.lower()
        obj = store_queries.resolve(conn, target)
        if obj is None:
            print(f"Hydra object not found: {args.hydra_id}", file=sys.stderr)
            return CommandResult(1)
        kwargs = {"depth": args.depth} if args.depth is not None else {}
        impacted = store_queries.impact(conn, target, **kwargs)
    finally:
        conn.close()
    print(f"id: {obj['hydra_id']}")
    print(f"depth: {args.depth if args.depth is not None else store_queries.DEFAULT_IMPACT_DEPTH}")
    if impacted:
        print("impact:")
        for hydra_id in impacted:
            print(f"- {hydra_id}")
    else:
        print("impact: none")
    return CommandResult(0)


def command_ref_check(_args, resolver_paths) -> CommandResult:
    # One scan shared by both checks and the pending-upgrade count below,
    # instead of three independent tree walks.
    objects_result = collect_hydra_objects(resolver_paths)
    objects, _ = objects_result
    findings = validate_object_references(resolver_paths, objects_result=objects_result)
    if not findings:
        findings = findings + validate_object_registry_freshness(resolver_paths, objects_result=objects_result)
    if findings:
        print("Hydra references: failed")
        for finding in findings:
            print(f"- {finding}")
        return CommandResult(1)
    pending = [obj for obj in objects if obj["schema_version"] < CURRENT_SCHEMA_VERSION]
    if pending:
        print(f"Hydra references: ok ({len(objects)} objects, {len(pending)} pending schema upgrade)")
    else:
        print(f"Hydra references: ok ({len(objects)} objects)")
    return CommandResult(0)


def command_ref_index(_args, resolver_paths) -> CommandResult:
    findings = validate_object_references(resolver_paths)
    if findings:
        print("Hydra references: failed", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        return CommandResult(1)
    count = write_object_registry(resolver_paths)
    if count is None:
        print("Hydra references: registry write refused (concurrent change detected); rerun `hydra.py ref index`", file=sys.stderr)
        return CommandResult(1)
    print(f"Indexed {count} objects: {display_path(resolver_paths.object_registry, resolver_paths.root)}")
    return CommandResult(0)


def register(subparsers) -> None:
    """Add `ref resolve`/`check`/`index`/`rdeps`/`impact`/`store status`/
    `store rebuild`. `store status`/
    `store rebuild` nest here rather than in their own `COMMAND_MODULES`
    entry, because they extend the `ref` subparsers this module already
    owns and argparse subparsers cannot be shared across two `register()`
    calls; the command bodies themselves live in `commands/store.py`, the
    same split `objects/registry.py` has from this module."""
    ref = subparsers.add_parser("ref", help="Resolve and index Hydra object references")
    ref_sub = ref.add_subparsers(dest="ref_command", required=True)

    resolve = ref_sub.add_parser("resolve", help="Explain the current object behind a hydra:// ID")
    resolve.add_argument("hydra_id")
    resolve.set_defaults(func=_dispatch_ref_resolve)

    ref_sub.add_parser("check", help="Validate Hydra object IDs and hydra:// references").set_defaults(func=_dispatch_ref_check)
    ref_sub.add_parser("index", help="Write the derived Hydra object registry").set_defaults(func=_dispatch_ref_index)

    rdeps = ref_sub.add_parser("rdeps", help="List every object that references a hydra:// ID (requires the store)")
    rdeps.add_argument("hydra_id")
    rdeps.set_defaults(func=_dispatch_ref_rdeps)

    impact = ref_sub.add_parser("impact", help="List every object transitively reachable from a hydra:// ID (requires the store)")
    impact.add_argument("hydra_id")
    impact.add_argument("--depth", type=int, default=None, help=f"Maximum relation hops (default {store_queries.DEFAULT_IMPACT_DEPTH})")
    impact.set_defaults(func=_dispatch_ref_impact)

    store_parser = ref_sub.add_parser("store", help="Inspect or rebuild the operational object query store")
    store_sub = store_parser.add_subparsers(dest="ref_store_command", required=True)
    store_sub.add_parser("status", help="Report the store's freshness against the export").set_defaults(func=_dispatch_ref_store_status)
    rebuild = store_sub.add_parser("rebuild", help="Rebuild the store from the current object registry")
    rebuild.add_argument("--if-exists", dest="if_exists", action="store_true", help="Do nothing until the store has been built once")
    rebuild.add_argument(
        "--verify-digests", dest="verify_digests", action="store_true",
        help="Repair documents/tasks by content digest instead of mtime (for a store restored on another machine)",
    )
    rebuild.set_defaults(func=_dispatch_ref_store_rebuild)


def _dispatch_ref_resolve(args, ctx) -> int:
    return command_ref_resolve(args, ctx.resolver_paths()).exit_code


def _dispatch_ref_check(args, ctx) -> int:
    return command_ref_check(args, ctx.resolver_paths()).exit_code


def _dispatch_ref_rdeps(args, ctx) -> int:
    return command_ref_rdeps(args, ctx.resolver_paths()).exit_code


def _dispatch_ref_impact(args, ctx) -> int:
    return command_ref_impact(args, ctx.resolver_paths()).exit_code


def _dispatch_ref_index(args, ctx) -> int:
    return command_ref_index(args, ctx.resolver_paths()).exit_code


def _dispatch_ref_store_status(args, ctx) -> int:
    return store_commands.command_ref_store_status(ctx.resolver_paths()).exit_code


def _dispatch_ref_store_rebuild(args, ctx) -> int:
    return store_commands.command_ref_store_rebuild(args, ctx.resolver_paths()).exit_code
