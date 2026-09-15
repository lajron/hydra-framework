"""---
hydra_id: hydra://engine-module/validator-registry
uid: 031b520a-a7b1-41b3-bc3b-f2cd5291d01c
schema_version: 3
kind: engine-module
title: Validator Registry
status: active
scope: base-seed
owners:
  team: hydra
relations:
  - hydra://engine-module/object-family-registry
  - hydra://engine-module/object-handler-registry
provenance:
  sources:
    - .hydra-framework/core/architecture.md
---

The validator registry is the third explicit extension registry.

Before this, `validate`/`doctor` checks existed as anonymous zero-arg
callables built in two places, and `cli.dispatch._validate_checks` was the only
place that wrote down their original order by manually interleaving calls into
both modules. Nothing named an individual check, and nothing but that one
function in the composition root recorded where a new validator's call had to
be spliced relative to the others. That is exactly the "editing several central
switchboards" failure the architecture avoids, even though the two source
modules were already split to respect check 5's fan-out cap.

This module is the deliberately simple registry: a `Validator` is
a name plus the same one-argument `check(ctx)` shape every validator already
had, and `VALIDATORS` is the one place the full 19-validator order is written
down. `cli.dispatch._validate_checks` now reads as `checks_for(ctx)` --
composing the registry, not authoring the order.

Registering here does not move where a validator is implemented.
`checks.repo_findings` and `checks.package_and_task_findings` stay split for
the reason recorded in `repo_findings`'s own docstring (check 5's fan-out
cap), and this module deliberately does not re-import their domain
dependencies (`module_metadata`, `capabilities`, `architecture_check`, and so
on) -- it only names the nine-entry `repo_findings.NAMED_CHECKS` tuple and the
five functions `package_and_task_findings` exports, which keeps its own
fan-out at two domain imports.

Order is locked by byte-identical `validate`/`doctor` contract goldens --
`command_validate` prints findings in this order, not sorted -- so
`VALIDATORS` reproduces the prior interleave explicitly rather than
concatenating the two source modules and sorting or renumbering anything.

This establishes where a
downstream-only extension is supposed to register: for this registry, as for
the two before it, the registry module *is* the documented extension
location. The architecture forbids the alternative -- "no magical
discovery, no import-time scanning of the tree, no plugin framework built
before there are plugins" -- so a downstream copy that authors a local
validator edits this tuple in its own fork, the same one-file, reviewable
edit `identity.object_families` and `objects.object_handlers` already ask
for. What this registry ends is edits spread across several
files with no single record of the order; it was never promising a
registration path that never touches engine source at all.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable

from hydra_engine.checks import capability_callers, package_and_task_findings, repo_findings
from hydra_engine import config as hydra_config
from hydra_engine.knowledge import checks as knowledge_checks
from hydra_engine.seed import candidate_queue
from hydra_engine.telemetry import evidence as telemetry_evidence


@dataclasses.dataclass(frozen=True)
class Validator:
    """One `validate`/`doctor` check and the name it registers under.

    `check` takes the same untyped `ctx` every check in this package already
    takes (a `cli.dispatch.RepoContext`, never imported here by name --
    `checks` sits below `cli` in the layer order, so naming it would be the
    upward import architecture check 3 forbids) and returns a `Finding` list.
    """

    name: str
    check: Callable[[object], list]


# The full check order keeps `cli.dispatch._validate_checks`'s prior manual
# interleave intact, then appends newer repository-wide validators so
# byte-identical goldens only change when a check emits a finding.
VALIDATORS = (
    Validator("task-records", package_and_task_findings.task_records_check),
    Validator("provider-surfaces", package_and_task_findings.provider_surfaces_check),
    *(Validator(name, check) for name, check in repo_findings.NAMED_CHECKS),
    Validator("config-policy", lambda ctx: hydra_config.validate_config(ctx.config_paths())),
    Validator("flat-knowledge", package_and_task_findings.flat_knowledge_check),
    Validator("knowledge-node-docs", package_and_task_findings.package_docs_check),
    Validator("knowledge-v3", knowledge_checks.validate_knowledge_v3),
    Validator("capability-callers", lambda ctx: capability_callers.validate_capability_callers(ctx.hydra, ctx.root)),
    Validator("reflection-queue", package_and_task_findings.reflection_queue_check),
    Validator("candidate-queue", lambda ctx: candidate_queue.validate_candidate_queue(ctx.hydra / "evolution" / "candidates", ctx.root)),
    Validator("telemetry-evidence", lambda ctx: telemetry_evidence.validate_telemetry_evidence_queue(ctx.hydra / "repo" / "telemetry" / "packages", ctx.root)),
)


def checks_for(ctx) -> list:
    """Zero-arg `checks.aggregation.Check`s, in the registry's locked order."""
    return [lambda validator=validator: validator.check(ctx) for validator in VALIDATORS]
