"""installation command decisions: adopt,
init, install-hooks.

`InstallationPaths`/`ProvidersPaths`/`ContextCompilerPaths` are bare
forward-reference type hints in `command_adopt`'s signature (no real
import): this module only calls methods on already-constructed instances,
matching the established codebase-wide convention for this shape (see
`hydra_engine.installation.adopt`'s own docstring).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from hydra_engine.commands import CommandResult
from hydra_engine.documents.tokens import display_path
from hydra_engine.installation.adopt import adoption_report, record_lineage
from hydra_engine.installation.git_hooks import executable_hook_files, hooks_path_matches, set_hooks_path, unset_hooks_path
from hydra_engine.installation.private_tier import ensure_gitignore_rule, ensure_private_tier
from hydra_engine.installation.seed_copy import planned_init_files

ADOPT_HOST_SIGNAL_REPORT_LIMIT = 4
RECLAIM_UNMANAGED_REPORT_LIMIT = 10
INIT_CONFLICT_REPORT_LIMIT = 10
INIT_DRY_RUN_REPORT_LIMIT = 20


def command_adopt(args, paths, providers_paths, context_compiler_paths, manifest: dict) -> CommandResult:
    """Report what integrating this Hydra copy into the host repository needs.

    `manifest` is the already-parsed `manifest.yaml` dict, computed by
    `hydra.py`'s thin wrapper: this module and `installation.adopt` never
    import `documents.yaml_documents` themselves, to avoid tripping check 4's
    in-degree cap on that module (see `installation.adopt`'s docstring).
    """
    if args.record:
        outcome = record_lineage(paths, manifest, args.repo or paths.root.name)
        if outcome["status"] == "missing-paths":
            print("Hydra adopt: refusing to record lineage while required paths are missing", file=sys.stderr)
            for path in outcome["missing"]:
                print(f"- {path}", file=sys.stderr)
            return CommandResult(1)
        if outcome["status"] == "already-recorded":
            print(f"Hydra adopt: lineage already recorded for `{outcome['adopted_into']}`")
            return CommandResult(0)
        print(f"Hydra adopt: recorded lineage for `{outcome['slug']}` in {display_path(outcome['manifest_path'], paths.root)}")
        return CommandResult(0)

    report = adoption_report(paths, providers_paths, context_compiler_paths, manifest)

    print("Hydra adoption report")
    print(f"Repository root: {paths.root}")
    print(f"Seed version: {report['seed_version']}")

    if report["missing"]:
        print("\nFramework integrity: INCOMPLETE COPY")
        for path in report["missing"]:
            print(f"- missing: {path}")
        print("Do not recreate these from memory. Re-copy them from the source repository.")
    else:
        print("\nFramework integrity: required paths present")

    private_tier = report["private_tier"]
    print("\nPrivate tier:")
    print(f"- gitignore rule: {'present' if private_tier['gitignore_rule_present'] else 'missing'}")
    print(f"- ignored by Git: {'yes' if private_tier['ignored'] else 'no'}")
    print(f"- directory: {'present' if private_tier['directory_exists'] else 'absent'}")
    if private_tier["seeded_areas_present"]:
        print("- seeded areas: present")
    else:
        print(f"- seeded areas: {len(private_tier['missing_seeded_areas'])} missing")

    print("\nLineage:")
    if report["lineage"]:
        for key in sorted(report["lineage"]):
            print(f"- {key}: {report['lineage'][key]}")
    else:
        print("- not recorded. Run `hydra.py adopt --record --repo <slug>`.")

    print("\nHost repository signals:")
    if report["host_stacks"]:
        for stack, hits in sorted(report["host_stacks"].items()):
            print(f"- {stack}: {', '.join(hits[:ADOPT_HOST_SIGNAL_REPORT_LIMIT])}")
    else:
        print("- no common build manifests found at the repository root")

    print("\nProvider surfaces:")
    for provider, label, target, count in report["provider_surfaces"]:
        state = f"{count} entries" if count else "absent"
        print(f"- {provider} {label} ({target}): {state}")
    print(f"- CLAUDE.md: {'present' if report['claude_md_present'] else 'absent'}")
    print(f"- .claude/settings.json: {'present' if report['settings_json_present'] else 'absent'}")

    nodes = report["knowledge_nodes"]
    print(f"\nKnowledge nodes: {len(nodes)}")
    for node in nodes:
        print(f"- {node.logical_id} ({node.scope})")
    if not nodes:
        print("- none. Create one only for a stable accountability boundary where AI work already repeats.")

    unmanaged = report["unmanaged_surfaces"]
    print(f"\nUnmanaged provider files: {len(unmanaged)}")
    for item in unmanaged[:RECLAIM_UNMANAGED_REPORT_LIMIT]:
        print(f"- {item['status']}: {item['path']}")
    if len(unmanaged) > RECLAIM_UNMANAGED_REPORT_LIMIT:
        print(f"- ... and {len(unmanaged) - RECLAIM_UNMANAGED_REPORT_LIMIT} more (run `hydra.py reclaim`)")

    print("\nSuggested next steps:")
    steps = []
    if report["missing"]:
        steps.append("Restore the missing framework paths listed above.")
    if not report["lineage"]:
        steps.append("Record lineage: `hydra.py adopt --record --repo <slug>`.")
    if not (
        private_tier["gitignore_rule_present"]
        and private_tier["ignored"]
        and private_tier["directory_exists"]
        and private_tier["seeded_areas_present"]
    ):
        steps.append("Run `hydra.py init-local`.")
    if unmanaged:
        steps.append("Reclaim unmanaged provider files: `hydra.py reclaim`.")
    steps.append("Generate provider surfaces with `hydra.py export-adapters` -- required every fresh clone, since generated adapters are Git-ignored, not tracked. Preview a capability profile first if needed: `hydra.py profile list`, then `hydra.py export-adapters --profile <name> --dry-run`.")
    if not report["claude_md_present"]:
        steps.append("Add a small CLAUDE.md that imports AGENTS.md.")
    steps.append("Validate: `hydra.py doctor` and `hydra.py selftest`.")
    for index, step in enumerate(steps, start=1):
        print(f"{index}. {step}")
    return CommandResult(0)


def command_init(args, paths) -> CommandResult:
    """Copy this Hydra framework into a target repository."""
    target_root = Path(args.target).expanduser().resolve()
    if not target_root.is_dir():
        print(f"Hydra init: target is not a directory: {target_root}", file=sys.stderr)
        return CommandResult(1)
    if target_root == paths.root.resolve():
        print("Hydra init: target is the current repository", file=sys.stderr)
        return CommandResult(1)

    planned = planned_init_files(paths.root, target_root)
    conflicts = [destination for _source, destination in planned if destination.exists()]

    if not planned:
        print("Hydra init: nothing to copy", file=sys.stderr)
        return CommandResult(1)

    if conflicts and not args.force:
        print(f"Hydra init: {len(conflicts)} file(s) already exist in the target")
        for path in conflicts[:INIT_CONFLICT_REPORT_LIMIT]:
            print(f"- {path}")
        if len(conflicts) > INIT_CONFLICT_REPORT_LIMIT:
            print(f"- ... and {len(conflicts) - INIT_CONFLICT_REPORT_LIMIT} more")
        print("Re-run with --force to overwrite, or copy into a clean target.")
        return CommandResult(1)

    if args.dry_run:
        print(f"Hydra init: would copy {len(planned)} file(s) into {target_root}")
        for _source, destination in planned[:INIT_DRY_RUN_REPORT_LIMIT]:
            print(f"- {destination.relative_to(target_root)}")
        if len(planned) > INIT_DRY_RUN_REPORT_LIMIT:
            print(f"- ... and {len(planned) - INIT_DRY_RUN_REPORT_LIMIT} more")
        return CommandResult(0)

    for source, destination in planned:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    local = target_root / ".hydra-framework.local"
    gitignore_status = ensure_gitignore_rule(target_root)
    seed = ensure_private_tier(target_root, local)

    print(f"Hydra init: copied {len(planned)} file(s) into {target_root}")
    print(
        "Private local state: "
        f"gitignore {gitignore_status}, "
        f"{len(seed['created'])} directories created, "
        f"{len(seed['seeded'])} seed files written."
    )
    print("Next, in the target repository:")
    print("1. python3 .hydra-framework/scripts/hydra.py adopt")
    print("2. python3 .hydra-framework/scripts/hydra.py adopt --record --repo <slug>")
    print("3. python3 .hydra-framework/scripts/hydra.py export-adapters")
    print("See .hydra-framework/repo/knowledge/state-tiers.md for the private tier shape.")
    return CommandResult(0)


def command_install_hooks(args, paths) -> CommandResult:
    """Point Git at the tracked hooks directory.

    Git hooks are not versioned, so a hook committed to `.git/hooks/` on one
    machine does not exist on anyone else's. `core.hooksPath` lets the hook live
    in the repository where it can be reviewed, at the cost of one command per
    clone.

    This is convenience, not the enforcement boundary. Every check the hook runs
    also runs in `validate`, which CI runs; nobody's correctness depends on
    having run this.
    """
    hooks_dir = paths.hooks_dir()
    if not hooks_dir.is_dir():
        print(f"Hydra install-hooks: no hooks directory at {display_path(hooks_dir, paths.root)}", file=sys.stderr)
        return CommandResult(1)

    hook_files = executable_hook_files(hooks_dir)
    relative = hooks_dir.relative_to(paths.root).as_posix()

    if args.uninstall:
        unset_hooks_path(paths.root)
        print("Hydra install-hooks: removed core.hooksPath; Git is back to .git/hooks/")
        return CommandResult(0)

    ok, error = set_hooks_path(paths.root, relative)
    if not ok:
        print(f"Hydra install-hooks: {error}", file=sys.stderr)
        return CommandResult(1)

    print(f"Hydra install-hooks: core.hooksPath -> {relative}")
    for hook in hook_files:
        print(f"- {hook.name}")
    print("This is per-clone and optional. CI runs the same checks regardless.")
    return CommandResult(0)


def register(subparsers) -> None:
    """Add `adopt`, `init`, and `install-hooks`."""
    adopt = subparsers.add_parser("adopt", help="Report what integrating this Hydra copy into the host repository needs")
    adopt.add_argument("--record", action="store_true", help="Record adoption lineage in manifest.yaml")
    adopt.add_argument("--repo", help="Repository slug to record (defaults to the directory name)")
    adopt.set_defaults(func=_dispatch_adopt)

    init = subparsers.add_parser("init", help="Copy this Hydra framework into a target repository")
    init.add_argument("--target", required=True, help="Path to the target repository root")
    init.add_argument("--dry-run", action="store_true", help="Report what would be copied without copying")
    init.add_argument("--force", action="store_true", help="Overwrite files that already exist in the target")
    init.set_defaults(func=_dispatch_init)

    hooks = subparsers.add_parser("install-hooks", help="Point Git at the tracked hooks directory (optional, per clone)")
    hooks.add_argument("--uninstall", action="store_true", help="Restore Git's default .git/hooks/")
    hooks.set_defaults(func=_dispatch_install_hooks)


def _dispatch_adopt(args, ctx) -> int:
    return command_adopt(args, ctx.installation_paths(), ctx.providers_paths(), ctx.context_compiler_paths(), ctx.manifest).exit_code


def _dispatch_init(args, ctx) -> int:
    return command_init(args, ctx.installation_paths()).exit_code


def _dispatch_install_hooks(args, ctx) -> int:
    return command_install_hooks(args, ctx.installation_paths()).exit_code
