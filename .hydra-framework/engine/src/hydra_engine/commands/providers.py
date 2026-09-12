"""providers command decisions."""

from __future__ import annotations

from datetime import date
import json
import sys

from hydra_engine.commands import CommandResult
from hydra_engine.config import ConfigError
from hydra_engine.documents.tokens import HydraYamlError, display_path
from hydra_engine.providers.adapter_plan import LockUnavailableError, acquire_export_lock, apply_reconcile_plan, planned_adapter_files
from hydra_engine.providers import capabilities
from hydra_engine.providers import reclaim
from hydra_engine.providers.paths import ProvidersPaths
from hydra_engine.providers.reclaim import classify_surfaces, promote_surface
from hydra_engine.providers.selection import capability_profiles, resolve_capability_selection, write_active_selection

_PROVIDER_VERIFICATION_MAX_AGE_DAYS = 30


def provider_verification_notes(
    paths: ProvidersPaths,
    today: str,
    max_age_days: int = _PROVIDER_VERIFICATION_MAX_AGE_DAYS,
) -> list[str]:
    """Report provider runtime evidence and flag old compatibility checks."""
    notes: list[str] = []
    try:
        today_date = date.fromisoformat(today)
    except ValueError:
        return notes

    for path in sorted((paths.hydra / "adapters/providers").glob("*/capability-map.yaml")):
        try:
            data = capabilities.parse_yaml(path, paths.root)
        except HydraYamlError:
            continue
        provider = capabilities.yaml_str(data.get("provider"), path.parent.name)
        runtime = capabilities.yaml_str(data.get("runtime"), "unknown runtime")
        provider_version = capabilities.yaml_str(data.get("provider_version"))
        verified = capabilities.yaml_str(data.get("verified"))
        if not verified:
            continue
        try:
            age_days = max((today_date - date.fromisoformat(verified)).days, 0)
        except ValueError:
            continue
        runtime_label = runtime if not provider_version else f"{runtime} {provider_version}"
        note = f"provider `{provider}`: {runtime_label}; compatibility verified {verified}"
        if age_days > max_age_days:
            note += f" ({age_days} days old; recheck provider compatibility)"
        notes.append(note)
    return notes


def _report_pending(paths: ProvidersPaths, plan: reclaim.ReconcilePlan, verb_created: str, verb_changed: str, verb_removed: str) -> None:
    for path in plan.created:
        print(f"- {verb_created}: {display_path(path, paths.root)}")
    for path in plan.changed:
        print(f"- {verb_changed}: {display_path(path, paths.root)}")
    for unit in plan.removable:
        for member in unit.members:
            print(f"- {verb_removed}: {display_path(member, paths.root)}")
    for label, reason in plan.kept:
        print(f"- kept: {label}: {reason}")


def resolve_active_plan(paths: ProvidersPaths) -> dict:
    """The plan a no-`--profile` `export-adapters` would use: the active
    profile's plan once this checkout has adopted profiles, else the full
    catalog. Shared with `doctor`'s bootstrap check, which needs to know
    whether *something* should be materialized without also running the
    heavier ownership/orphan checks `reconcile_export` does."""
    if (paths.hydra / "capabilities/profiles.yaml").exists():
        selection = resolve_capability_selection(paths)
        return planned_adapter_files(paths, selection.skills)
    return planned_adapter_files(paths)


def command_export_adapters(args, paths: ProvidersPaths) -> CommandResult:
    try:
        profile_name = getattr(args, "profile", None)
        if profile_name and not args.dry_run:
            print("Hydra export failed: `--profile` is preview-only; use it with `--dry-run`", file=sys.stderr)
            return CommandResult(1)
        if profile_name and args.check:
            print("Hydra export failed: `--profile` cannot be combined with `--check`", file=sys.stderr)
            return CommandResult(1)
        if profile_name:
            selection = resolve_capability_selection(paths, profile_name)
        elif (paths.hydra / "capabilities/profiles.yaml").exists():
            # No profile named on the command line: reconcile using whatever
            # this checkout has actually selected (`active.yaml`, or
            # `default_profile` if it never has). A repo that never adopted
            # a profile at all has no `profiles.yaml`, so it never reaches
            # this branch and gets exactly today's full-catalog behavior.
            selection = resolve_capability_selection(paths)
        else:
            selection = None
        plan = reclaim.reconcile_export(paths, selection.skills if selection else None)
    except (HydraYamlError, ConfigError) as error:
        print(f"Hydra export failed: {error}", file=sys.stderr)
        return CommandResult(1)

    if selection is not None and not selection.skills:
        tags = ", ".join(selection.effective_tags) or "none"
        print(f"Warning: profile `{selection.name}` selects no skills (effective tags: {tags}).")

    if plan.abort_reason:
        print(f"Hydra export failed: {plan.abort_reason}", file=sys.stderr)
        return CommandResult(1)

    if not plan.contents:
        print("No Hydra skills or agents found to export.")
        return CommandResult(0)

    pending = bool(plan.created or plan.changed or plan.removable)

    if args.check:
        if not pending:
            print(f"Hydra adapters: up to date ({len(plan.contents)} generated files)")
            return CommandResult(0)
        print("Hydra adapters: drift detected")
        _report_pending(paths, plan, "missing", "stale", "obsolete")
        print("Run `hydra.py export-adapters` to regenerate.")
        return CommandResult(1)

    if args.dry_run:
        if not pending:
            print(f"Hydra adapters: no changes ({len(plan.contents)} generated files)")
            return CommandResult(0)
        print("Hydra adapters: would write")
        _report_pending(paths, plan, "create", "update", "remove")
        return CommandResult(0)

    try:
        with acquire_export_lock(paths):
            apply_reconcile_plan(plan)
    except LockUnavailableError as error:
        print(f"Hydra export failed: {error}", file=sys.stderr)
        return CommandResult(1)

    if selection is not None:
        tags = ", ".join(selection.effective_tags) or "none"
        print(f"Hydra capability profile: {selection.name} (effective tags: {tags})")

    if not pending:
        print(f"Hydra adapters: already current ({len(plan.contents)} generated files)")
        return CommandResult(0)
    removed = sum(len(unit.members) for unit in plan.removable)
    summary = f"Hydra adapters: wrote {len(plan.created) + len(plan.changed)} of {len(plan.contents)} generated files"
    if removed:
        summary += f", removed {removed}"
    print(summary)
    _report_pending(paths, plan, "create", "update", "remove")
    if plan.removable:
        print("Restart your Claude/Codex session: it composed its skill list at start and will not see this change until then.")
    return CommandResult(0)


def command_profile_select(args, paths: ProvidersPaths) -> CommandResult:
    """Record and materialize a capability profile.

    Four steps, in order, held under one lock: (1) acquire the lock; (2)
    resolve the profile and build the whole plan in memory, no file touched;
    (3) atomically write `active.yaml` -- the commit point; (4) apply the
    planned adapter changes. A crash after step 3 leaves the checkout
    recoverable by an ordinary `export-adapters`: it recomputes this same
    plan from `active.yaml` plus canonical sources on every run, so nothing
    here needs its own repair path.
    """
    try:
        with acquire_export_lock(paths):
            try:
                selection = resolve_capability_selection(paths, args.name)
                plan = reclaim.reconcile_export(paths, selection.skills)
            except HydraYamlError as error:
                print(f"Hydra profile select failed: {error}", file=sys.stderr)
                return CommandResult(1)
            if plan.abort_reason:
                print(f"Hydra profile select failed: {plan.abort_reason}", file=sys.stderr)
                return CommandResult(1)
            write_active_selection(paths, args.name)
            apply_reconcile_plan(plan)
    except LockUnavailableError as error:
        print(f"Hydra profile select failed: {error}", file=sys.stderr)
        return CommandResult(1)

    tags = ", ".join(selection.effective_tags) or "none"
    removed = sum(len(unit.members) for unit in plan.removable)
    print(f"Hydra profile selected: {args.name} (effective tags: {tags})")
    print(f"Selected skills: {len(selection.skills)}")
    print(f"Created {len(plan.created)}, updated {len(plan.changed)}, removed {removed}, kept-and-reported {len(plan.kept)}.")
    for label, reason in plan.kept:
        print(f"- kept: {label}: {reason}")
    print("Restart your Claude/Codex session: it composed its skill list at start and will not see this change until then.")
    return CommandResult(0)


def command_profile_list(paths: ProvidersPaths) -> CommandResult:
    try:
        profiles = capability_profiles(paths)
    except HydraYamlError as error:
        print(f"Hydra profile failed: {error}", file=sys.stderr)
        return CommandResult(1)
    print("Hydra capability profiles:")
    for profile, source in profiles:
        tags = ", ".join(profile.tags) or "none"
        print(f"- {profile.name}: {tags} ({source})")
    return CommandResult(0)


def command_profile_show(args, paths: ProvidersPaths) -> CommandResult:
    try:
        selection = resolve_capability_selection(paths, args.profile)
    except HydraYamlError as error:
        print(f"Hydra profile failed: {error}", file=sys.stderr)
        return CommandResult(1)
    tags = ", ".join(selection.effective_tags) or "none"
    print(f"Hydra capability profile: {selection.name}")
    print(f"Effective tags: {tags}")
    print(f"Selected skills: {len(selection.skills)}")
    for skill in selection.skills:
        print(f"- {skill.name}: {', '.join(selection.reasons[skill])}")
    if not selection.skills:
        print(f"Warning: profile `{selection.name}` selects no skills (effective tags: {tags}).")

    selected_names = {skill.name for skill in selection.skills}
    dependencies: set[str] = set()
    modules = list(selection.skills) + sorted(path for path in paths.agents_root().glob("*") if (path / "agent.md").exists())
    for module in modules:
        data = capabilities.parse_yaml(module / "metadata.yaml", paths.root)
        dependencies.update(capabilities.yaml_list(capabilities.yaml_map(data.get("dependencies")).get("skills")))
    missing = sorted(dependencies - selected_names)
    if missing:
        print("Unmaterialized declared skill dependencies (informational):")
        for name in missing:
            print(f"- {name}")
    if args.untagged:
        untagged = []
        for skill in sorted(path for path in paths.skills_root().glob("*") if (path / "skill.md").exists()):
            if not capabilities.yaml_list(capabilities.parse_yaml(skill / "metadata.yaml", paths.root).get("tags")):
                untagged.append(skill.name)
        print(f"Untagged skills: {len(untagged)}")
        for name in untagged:
            print(f"- {name}")
    return CommandResult(0)


def command_reclaim(args, paths: ProvidersPaths) -> CommandResult:
    """Report, and optionally promote, provider files Hydra does not own."""
    items = classify_surfaces(paths)
    if args.json:
        print(json.dumps(items, indent=2))
        return CommandResult(0)

    buckets: dict[str, list[dict[str, str]]] = {}
    for item in items:
        buckets.setdefault(item["status"], []).append(item)

    generated = len(buckets.get("generated", []))
    orphaned = buckets.get("orphaned", [])
    drifted = buckets.get("drifted", [])
    stale = buckets.get("stale", [])

    print(f"Hydra provider surfaces: {len(items)} file(s)")
    print(f"- generated and current: {generated}")
    for label, group in [("orphaned", orphaned), ("drifted", drifted), ("stale", stale)]:
        print(f"- {label}: {len(group)}")
        for item in group:
            print(f"  {item['path']}: {item['detail']}")

    if not orphaned and not drifted and not stale:
        print("\nAll provider files are generated from canonical Hydra sources.")
        return CommandResult(0)

    if args.promote and orphaned:
        promoted: list = []
        skipped: list[str] = []
        for item in orphaned:
            target = promote_surface(paths, item)
            if target is None:
                skipped.append(item["path"])
            else:
                promoted.append(target)
        print("")
        for target in promoted:
            print(f"promoted: {display_path(target, paths.root)}")
        for path in skipped:
            print(f"skipped (canonical target already exists): {path}")
        if promoted:
            print("\nReview each promoted file, then run `hydra.py export-adapters`.")
            print("Promoted metadata is marked `certainty: inferred` and `scope: repo-local`.")
        return CommandResult(0)

    print("\nWhat to do:")
    if orphaned:
        print("- orphaned: someone authored these directly in a provider directory.")
        print("  Promote with `hydra.py reclaim --promote`, then review and re-export.")
    if drifted:
        print("- drifted: the generated wrapper was edited instead of its canonical source.")
        print("  Move the edit into the canonical file, then run `hydra.py export-adapters`.")
    if stale:
        print("- stale: canonical source is gone or no longer exported. Delete the wrapper.")
    return CommandResult(1 if args.fail_on_findings else 0)


def register(subparsers) -> None:
    """Add `export-adapters`, `profile` (`list`/`show`/`select`), and `reclaim`."""
    export = subparsers.add_parser(
        "export-adapters",
        help="Generate provider skill and subagent wrappers from canonical Hydra capabilities",
    )
    export.add_argument("--check", action="store_true", help="Exit non-zero if any generated surface is missing or stale")
    export.add_argument("--dry-run", action="store_true", help="Report what would be written without writing")
    export.add_argument("--profile", help="Preview one capability profile (requires --dry-run)")
    export.set_defaults(func=_dispatch_export_adapters)

    profile = subparsers.add_parser("profile", help="Inspect, or select, this checkout's active capability profile")
    profile_subparsers = profile.add_subparsers(dest="profile_command", required=True)
    profile_list = profile_subparsers.add_parser("list", help="List shared and local capability profiles")
    profile_list.set_defaults(func=_dispatch_profile_list)
    profile_show = profile_subparsers.add_parser("show", help="Show skills selected by a capability profile")
    profile_show.add_argument("--profile", help="Profile name (defaults to the checkout default)")
    profile_show.add_argument("--untagged", action="store_true", help="Also list canonical skills without tags")
    profile_show.set_defaults(func=_dispatch_profile_show)
    profile_select = profile_subparsers.add_parser("select", help="Select and materialize a capability profile for this checkout")
    profile_select.add_argument("name", help="Profile name: a shared preset, a local profile, or `full`")
    profile_select.set_defaults(func=_dispatch_profile_select)

    reclaim = subparsers.add_parser(
        "reclaim",
        help="Find provider files Hydra does not own and plan their promotion into canonical Hydra",
    )
    reclaim.add_argument("--promote", action="store_true", help="Move hand-authored provider files into canonical Hydra")
    reclaim.add_argument("--json", action="store_true", help="Emit machine-readable output")
    reclaim.add_argument("--fail-on-findings", action="store_true", help="Exit non-zero when unmanaged files exist")
    reclaim.set_defaults(func=_dispatch_reclaim)


def _dispatch_export_adapters(args, ctx) -> int:
    return command_export_adapters(args, ctx.providers_paths()).exit_code


def _dispatch_profile_list(args, ctx) -> int:
    return command_profile_list(ctx.providers_paths()).exit_code


def _dispatch_profile_show(args, ctx) -> int:
    return command_profile_show(args, ctx.providers_paths()).exit_code


def _dispatch_profile_select(args, ctx) -> int:
    return command_profile_select(args, ctx.providers_paths()).exit_code


def _dispatch_reclaim(args, ctx) -> int:
    return command_reclaim(args, ctx.providers_paths()).exit_code
