"""`validate`/`doctor` command decisions.

`command_validate` used to import every validator domain module directly to
aggregate its errors -- around 11 distinct sources, well past check 5's
fan-out cap of 8 if this module did the same. Instead it takes a
precomputed `list[checks.aggregation.Check]`: whoever builds the concrete
list (`cli/dispatch.py`, the composition root) imports
the domain modules; this module imports only `checks.aggregation` itself.
`command_doctor`'s own informational report (paths, task counts, owner,
provider surfaces, lineage) is not part of the `validate_*` family -- it
keeps printing plain data computed once by the same caller, for the same
fan-out reason, and delegates its own final verdict to `command_validate`
so the two commands share one aggregation path.
"""

from __future__ import annotations

from pathlib import Path

from hydra_engine.checks.aggregation import Check, run_checks
from hydra_engine.commands import CommandResult


def command_validate(checks: list[Check], notes: list[str]) -> CommandResult:
    findings = run_checks(checks)
    if findings:
        print("Hydra validate: failed")
        for finding in findings:
            print(f"- {finding}")
        return CommandResult(1)

    # Advisory, and printed after the verdict so it never reads as a failure.
    print("Hydra validate: ok")
    for note in notes:
        print(f"note: {note}")
    return CommandResult(0)


def command_doctor(
    *,
    missing_required_paths: list[str],
    tasks: list[Path],
    owner: str | None,
    local_exists: bool,
    private_tier: dict,
    hooks_installed: bool,
    knowledge_index_status: str,
    object_store_status: str,
    surfaces: list[dict[str, str]],
    desired_plan_nonempty: bool,
    lineage: dict,
    checks: list[Check],
    notes: list[str],
) -> CommandResult:
    if missing_required_paths:
        print("Hydra doctor: missing required paths")
        for path in missing_required_paths:
            print(f"- {path}")
        return CommandResult(1)

    print("Hydra doctor: core paths present")

    owners = sorted({path.parent.name for path in tasks})
    if tasks:
        print(f"Active task records: {len(tasks)} across {len(owners)} owner(s): {', '.join(owners)}")
    else:
        print("Active task records: none tracked")
    if owner is not None:
        print(f"Your owner slug: {owner}")
    else:
        print("Owner: UNRESOLVED. Set `git config user.email` or HYDRA_OWNER before `task start`.")

    print("Private tier:")
    print(f"- gitignore rule: {'present' if private_tier['gitignore_rule_present'] else 'missing'}")
    print(f"- ignored by Git: {'yes' if private_tier['ignored'] else 'no'}")
    print(f"- directory: {'present' if private_tier['directory_exists'] else 'absent'}")
    if private_tier["seeded_areas_present"]:
        print("- seeded areas: present")
    else:
        print(f"- seeded areas: {len(private_tier['missing_seeded_areas'])} missing")
    if not local_exists:
        print("Note: private tier directory is absent; run `hydra.py init-local` to seed it.")
    if not private_tier["gitignore_rule_present"] or not private_tier["ignored"]:
        print("Hydra doctor: private tier is not effectively ignored")
        return CommandResult(1)

    print("Cache lifecycle:")
    print(f"- git hooks installed: {'yes' if hooks_installed else 'no'}")
    if not hooks_installed:
        print("  hint: run `hydra.py install-hooks` for optional per-clone refresh hooks.")
    print(f"- knowledge.db: {knowledge_index_status}")
    if knowledge_index_status != "fresh":
        print("  hint: run `hydra.py hook-reindex-knowledge` to build or refresh it.")
    print(f"- object-store.db: {object_store_status}")
    if object_store_status != "fresh":
        print("  hint: run `hydra.py ref store rebuild` to build or refresh it.")

    generated = sum(1 for item in surfaces if item["status"] == "generated")
    unmanaged = [item for item in surfaces if item["status"] != "generated"]
    if not surfaces:
        if desired_plan_nonempty:
            print("Hydra doctor: no provider surfaces are materialized")
            print("  Generated adapters are untracked and must be regenerated after every fresh clone.")
            print("  Run `python3 .hydra-framework/scripts/hydra.py export-adapters` first.")
            return CommandResult(1)
        print("Note: no provider surfaces found. Run `hydra.py export-adapters` when adapters are needed.")
        print("  Preview a capability profile first with `hydra.py profile list` and `hydra.py export-adapters --profile <name> --dry-run`.")
    else:
        print(f"Provider surfaces: {generated} generated, {len(unmanaged)} unmanaged")
    for item in unmanaged:
        print(f"- {item['status']}: {item['path']}")
    if unmanaged:
        print("Run `hydra.py reclaim` for the promotion plan.")

    if lineage:
        print(f"Lineage: base {lineage.get('base_seed_version', 'unknown')} -> {lineage.get('adopted_into', 'unknown')}")
    else:
        print("Note: no lineage recorded. Run `hydra.py adopt --record` in an adopting repository.")

    return command_validate(checks, notes)
