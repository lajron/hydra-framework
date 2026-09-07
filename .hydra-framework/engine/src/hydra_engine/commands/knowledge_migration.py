"""CLI orchestration for reviewed Knowledge v2 migration."""

from __future__ import annotations

import sys
from pathlib import Path

from hydra_engine.commands import references
from hydra_engine.knowledge import migration_v2, search_index


def command_migrate_v2(args, ctx) -> int:
    if not args.apply:
        try:
            plan = migration_v2.build_plan(ctx.root)
            output = Path(args.output)
            if not output.is_absolute():
                output = ctx.root / output
            migration_v2.write_review_manifest(plan, output)
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
        reviewed = migration_v2.load_review_manifest(manifest_path)
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
