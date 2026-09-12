"""Holds most of `validate`/`doctor`'s checks. This composition used to live in `scripts/hydra.py`'s own thin wrapper
(`validate_checks()`), the last place still playing composition root for
anything; it moved here once no test called these `validate_*` functions at
the `hydra.` module level any more, and is now named data that
`checks.validator_registry` (the third explicit extension registry)
registers in the check order that module owns and explains.

Split into two modules (this one and `checks.package_and_task_findings`)
because the full set of ~10 domain modules `validate`/`doctor` compose is
well over check 5's fan-out cap of 8 for any module that is not the single
declared composition root -- `cli.dispatch` is that root and could absorb
the imports directly, but its own 200-line cap means the actual composition
logic has to live in ordinary, fan-out-capped modules instead. This module
sat at that cap exactly (8 imports) before
`object_model_check`'s two-scan `references`+`registry` pair folded into
`registry.validate_object_model`, freeing one import slot; `NAMED_CHECKS`
below stays a plain tuple of `(name, function)` pairs rather than a
`Validator` dataclass instance regardless, since importing that dataclass
would still be worth avoiding for the same reason. This module
holds the seven checks that only ever need a `RepoContext`-shaped object
(duck-typed, no import of `cli.dispatch.RepoContext` -- matching the
established convention already used for `ObjectLocations`/`WorkPaths`
elsewhere); `module_metadata_check` reads `ctx.module_metadata_entries`
directly rather than taking it as a second parameter, since every entry in
`NAMED_CHECKS` shares the same one-argument shape `validator_registry` relies
on.
"""

from __future__ import annotations

from hydra_engine.checks import architecture_check, module_metadata, task_contract_docs
from hydra_engine.objects import registry
from hydra_engine.providers import capabilities, selection
from hydra_engine.seed import adaptations
from hydra_engine.work import tiers


def module_metadata_check(ctx) -> list:
    return module_metadata.validate_module_metadata(ctx.module_metadata_entries, ctx.root)


def capability_maps_check(ctx) -> list:
    return capabilities.validate_capability_maps(ctx.providers_paths())


def capability_profiles_check(ctx) -> list:
    return selection.validate_capability_profiles(ctx.providers_paths())


def task_contract_docs_check(ctx) -> list:
    return task_contract_docs.validate_task_contract_docs(ctx.hydra, ctx.root, task_contract_docs.REQUIRED_TASK_SECTIONS)


def adaptations_ledger_check(ctx) -> list:
    return adaptations.validate_adaptations_ledger(ctx.adaptation_ledger, ctx.root)


def tier_boundaries_check(ctx) -> list:
    return tiers.validate_tier_boundaries(ctx.work_paths())


def private_tier_documented_check(ctx) -> list:
    return tiers.validate_private_tier_documented(ctx.work_paths())


def architecture_check_(ctx) -> list:
    package_root = ctx.hydra / "engine" / "src" / "hydra_engine"
    findings = list(architecture_check.validate_architecture(
        package_root=package_root,
        test_unit_root=ctx.hydra / "engine" / "tests" / "unit",
        hydra_shim=ctx.hydra / "scripts" / "hydra.py",
        repo_root=ctx.hydra,
        composition_root="hydra_engine.cli.dispatch",
    ))
    findings.extend(architecture_check.validate_no_checks_import_store(package_root=package_root))
    return findings


def object_model_check(ctx) -> list:
    return registry.validate_object_model(ctx.resolver_paths())


# Order matches `scripts/hydra.py`'s pre-step-14 `validate_checks()` exactly
# (byte-identical goldens depend on it -- `command_validate` prints findings
# in check order, not sorted). `checks.validator_registry` splices this tuple
# into the full ten-check order verbatim; it is the reason this stays a plain
# `(name, function)` tuple instead of a list this module mutates.
NAMED_CHECKS = (
    ("module-metadata", module_metadata_check),
    ("capability-maps", capability_maps_check),
    ("capability-profiles", capability_profiles_check),
    ("task-contract-docs", task_contract_docs_check),
    ("adaptations-ledger", adaptations_ledger_check),
    ("tier-boundaries", tier_boundaries_check),
    ("private-tier-documented", private_tier_documented_check),
    ("architecture", architecture_check_),
    ("object-model", object_model_check),
)
