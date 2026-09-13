"""CLI orchestration for reviewed Knowledge v2 migration."""

from __future__ import annotations

import sys
from pathlib import Path

from hydra_engine.commands import references
from hydra_engine.knowledge import migration_format, migration_v2, search_index
from hydra_engine.ports import lock as lock_port

# `apply_reviewed_plan` writes and deletes an arbitrary number of governed
# files as one logical transform with no atomic worktree boundary between
# them. This is the one lock both ends of the Phase 6 quiescence bracket
# share: held here for the whole multi-file write, tried non-blocking by
# `refresh_knowledge_index` below (see `command_hook_reindex_knowledge`), so
# a hook-triggered reindex cannot index a torn mix of already-written and
# not-yet-written paths as one snapshot.
KNOWLEDGE_WRITE_LOCK_REL = ".hydra-framework.local/locks/knowledge-write.lock"


def refresh_knowledge_index(paths, resolver_paths, local: Path, command_ids: tuple[str, ...] = ()):
    """Eager, best-effort reindex for `post-commit`/`post-checkout`/
    `post-merge`/`post-rewrite`. Backs off under a contended
    `KNOWLEDGE_WRITE_LOCK_REL` rather than indexing a torn mid-write
    snapshot, and is never load-bearing for correctness: `search()` detects
    and repairs staleness on its own, so a hook that never runs, fails, or
    loses the lock race only costs the next read the update it would
    otherwise have done inline. Returns the `build_index` result on a first
    build, otherwise `None` -- an already-published index is warmed in place
    via `search()`'s own incremental-update decision, with nothing new to
    report.
    """
    try:
        with lock_port.try_acquire(paths.root / KNOWLEDGE_WRITE_LOCK_REL, timeout=0.0):
            if search_index.default_db_path(local) is None:
                return search_index.build_index(paths, resolver_paths, local, command_ids)
            search_index.search("", paths=paths, resolver_paths=resolver_paths, local=local, command_ids=command_ids, limit=1)
            return None
    except lock_port.LockUnavailableError:
        return None


def command_migrate_v2(args, ctx) -> int:
    if not args.apply:
        try:
            plan = migration_v2.build_plan(ctx.root)
            output = Path(args.output)
            if not output.is_absolute():
                output = ctx.root / output
            migration_format.write_review_manifest(plan.manifest, output)
        except (migration_v2.MigrationError, OSError, ValueError) as error:
            print(f"Hydra Knowledge v2 migration dry-run failed: {error}", file=sys.stderr)
            return 1
        print(f"Hydra Knowledge v2 migration dry-run: {plan.manifest['status']}")
        print(f"Review manifest: {output.relative_to(ctx.root) if output.is_relative_to(ctx.root) else output}")
        print(f"Plan digest: {plan.manifest['plan_digest']}")
        print(f"Unresolved decisions: {len(plan.manifest['unresolved'])}")
        return 0 if not plan.manifest["unresolved"] else 2

    manifest_path = Path(args.apply)
    if not manifest_path.is_absolute():
        manifest_path = ctx.root / manifest_path
    try:
        reviewed = migration_format.load_review_manifest(manifest_path)
        with lock_port.acquire(ctx.root / KNOWLEDGE_WRITE_LOCK_REL):
            plan = migration_v2.apply_reviewed_plan(ctx.root, reviewed)
    except (migration_v2.MigrationError, OSError, ValueError) as error:
        print(f"Hydra Knowledge v2 migration apply failed: {error}", file=sys.stderr)
        return 1
    ref_result = references.command_ref_index(args, ctx.resolver_paths())
    if ref_result.exit_code:
        print("Hydra Knowledge v2 migration stopped after file apply: registry rebuild failed", file=sys.stderr)
        return ref_result.exit_code
    try:
        search_index.build_index(ctx.context_compiler_paths(), ctx.resolver_paths(), ctx.local, ctx.command_ids)
    except (OSError, ValueError) as error:
        print("Hydra Knowledge v2 migration stopped after registry rebuild: search index rebuild failed", file=sys.stderr)
        print(str(error), file=sys.stderr)
        return 1
    print(f"Hydra Knowledge v2 migration applied: {len(plan.manifest['packages'])} package(s)")
    print("Rollback boundary: " + plan.manifest["checkpoint_commit"])
    return 0
