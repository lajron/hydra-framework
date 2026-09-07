---
hydra_id: "hydra://knowledge-unit/hydra-framework/build-status"
uid: "b01fff6c-38ac-4bde-92c3-98890aac83bb"
schema_version: "3"
kind: "knowledge-unit"
unit_kind: "status"
title: "Hydra Framework Build Status"
status: "active"
scope: "base-seed"
owners:
  team: "hydra"
relations:
  - type: "relates-to"
    target: "hydra://knowledge-space/hydra-framework"
provenance:
  sources:
    - ".hydra-framework/scripts/hydra.py"
    - ".hydra-framework/core/placement-rules.md"
    - ".hydra-framework/repo/telemetry/README.md"
    - ".hydra-framework/engine/src/hydra_engine/cli/command_metadata.py"
    - ".hydra-framework/engine/src/hydra_engine/knowledge/context_providers.py"
  source_digests:
    - source: ".hydra-framework/scripts/hydra.py"
      digest: "sha256:b15fd376ec9ef5287fa4fd27e946d682fc73abf57e74b3c7bd3d058be7c795ed"
    - source: ".hydra-framework/core/placement-rules.md"
      digest: "sha256:88eeb340d945e3fbc85be7a291becd87a1f64f4d26b4fa9e37d1bb1a38613f43"
    - source: ".hydra-framework/repo/telemetry/README.md"
      digest: "sha256:b7ccc03875de6ebcd7b1dee48e59d804eaee3043b8840085aa6eee5e9a71c97c"
    - source: ".hydra-framework/engine/src/hydra_engine/cli/command_metadata.py"
      digest: "sha256:125719f126770bbcb6d7517cb7c45ed32f8986c8eb772ceb5b0d0f8bc9153349"
    - source: ".hydra-framework/engine/src/hydra_engine/knowledge/context_providers.py"
      digest: "sha256:f8a2e2f80283f039bc2dc38ab61ade4a94c17703ee161d3c9108457760fda7f1"
question: "What is actually built in this framework, per capability?"
group: "framework-state"
certainty: "confirmed"
checked_on: "2026-08-30"
verify:
  - "python3 .hydra-framework/scripts/hydra.py selftest"
  - "python3 .hydra-framework/scripts/hydra.py ref check"
  - "python3 .hydra-framework/scripts/hydra.py command-metadata --json"
---

# Hydra Framework Build Status

## Answer

Trust this table over any plan document: plans describe intent, this
describes the build. Verify a row with its own command before relying on it.

## Status

Verified against the tree and the CLI on 2026-08-30. Trust this table over any
plan document: the base upgrade plan describes intent, this describes the build.

| Capability | Status | How to verify |
| --- | --- | --- |
| Readable `hydra://` identity | built | `hydra.py ref resolve/check/index` reports the current object inventory |
| Frontmatter + sidecar metadata, aliases | built | `hydra.py ref check` |
| Derived registry, YAML export | built | `cognition/graph/registry.yaml` |
| Move detection, classified by uid + path + digest | built | `hydra.py ref check` after a manual `mv` |
| Context compiler over knowledge spaces | built | `hydra.py compile-context` |
| Compilable knowledge units (`reads:` resolved, `requires` budget-exempt) | built | `hydra.py compile-context`; `hydra_engine/knowledge/units.py` |
| Engine boundary, `hydra_engine` package plus compatibility shim | built | `hydra.py command-metadata --json` exposes the registered command surface through `hydra_engine.cli.dispatch`; `selftest` remains shim-resident |
| Enforced module bounds (size cap, acyclic imports, layer direction, in-degree cap, test-per-module) | built | `hydra.py validate`; `selftest` includes negative probes for module-size, import-cycle, upward-import, in-degree, missing-test, and banned-name violations |
| `.migrations/` staging, inventory, ledger | built | `hydra.py migration inventory` |
| Envelope `schema_version` and upgrade path | built | `hydra.py schema upgrade`, `engine/migrations.py`; three migration steps; all objects at `schema_version: 3` |
| `diff-base` envelope-version drift detection | built | `hydra.py diff-base` classifies a base ahead on `schema_version` as explained, not unexplained |
| Opaque `uid` | built, enforced from `schema_version` 2 | every object carries a UUID4 `uid`; `validate_object_references` fails any object at `schema_version` >= 2 with no `uid` |
| Mandatory envelope: `kind`, `title`, `status`, `scope`, `owners`, `relations`, `provenance.sources` | built, enforced from `schema_version` 3 | `build_hydra_object` defaults none of them; `validate_object_references` fails any object at `schema_version` >= 3 that lacks one. `relations` and `provenance.sources` must be present and may be `[]`; the other five must carry a value |
| Operational query store (SQLite) | all four stages built | `hydra.py ref check` collapsed from 3 object scans to 1; `is_relative_to` and the `objects/moves.py` O(n²) rescan fixed; SQLite store (`documents`/`refs`/`objects`/`aliases`/`relations`/`provenance`/`tasks`) built and self-maintaining via `ref store rebuild`/`--verify-digests` and post-checkout/post-merge hooks; `ref rdeps`, `ref impact --depth`, indexed `ref resolve`, and `board --owner/--blocked/--stale` all read through it with scan/absent-store fallback where one exists. Needs no concurrency design of its own — the store's write path is not where single-writer concurrency gets solved |
| `move-object` command | built | `hydra.py move-object <src> <dst> [--dry-run]` |
| Engine extension registries: object families | built, enforced | `hydra_engine/identity/object_families.py`; `ref check` fails an unregistered `hydra://` prefix or `kind` |
| Engine extension registries: validators | built | `hydra_engine/checks/validator_registry.py`; `cli/dispatch.py`'s `_validate_checks` is `validator_registry.checks_for(ctx)` |
| Engine extension registries: providers | built | `hydra_engine/providers/capabilities.py`'s `PROVIDERS`; `adapter_plan.planned_adapter_files` reads `Provider.build_agent_wrapper`, no `if provider == "codex":` branch left |
| Engine extension registries: command handlers / command-output reducers | built | command handlers are registry-shaped via `cli/dispatch.py`'s `COMMAND_MODULES`; command-output reducers are registered explicitly in `hydra_engine/command_output/registry.py` with reducer files under `command_output/reducers/<tool>/<case>.py` |
| Object handlers by document form (`.md`/`.yaml`/`.py`) | built | `hydra_engine/objects/object_handlers.py`; the suffix switch is gone from `objects/discovery.py` |
| Runtime/Engine object family | built, registered | the `engine-module` prefix and kind resolve to `Runtime/Engine` |
| Telemetry | local capture, gate, reporting, and evidence packages built; shared default flipped to evidence packages, never raw capture | `repo/knowledge/telemetry-redaction-contract.md`; `repo/telemetry/README.md`; unified writer in `hydra_engine/telemetry/writer.py`; redaction in `hydra_engine/telemetry/redaction.py`; `hydra_engine/telemetry/reporting.py`; `hydra_engine/telemetry/evidence.py`/`evidence_mint.py`; `hydra.py telemetry gate`/`report`/`evidence create` |
| Telemetry object family | built, registered | `hydra_engine/identity/object_families.py`'s `telemetry-evidence` prefix and kind resolve to `Telemetry` |
| Takeover scan and `integrate` | built | `hydra.py takeover scan`; `hydra.py integrate scan/identify/map/status` |
| `explain-path` | built | `hydra.py explain-path <path> [--json]`; composed from object lookup, provider-surface classification, and reverse citations, no hand-authored path-ownership file |
| Context compiler across all object families | built | `hydra_engine/knowledge/context_providers.py`'s `CONTEXT_PROVIDERS` registry (Knowledge, Capability, Work, Source, Runtime/Engine, Telemetry), each filtering the shared search index by family; `hydra.py compile-context --include-family/--exclude-family/--family-cap` |

Telemetry's provider-neutral redaction contract, local append-only capture,
Claude command-output capture, transcript-derived session aggregate capture,
and `telemetry gate` command are built. What "shared" means is settled: a
governed telemetry evidence package under `repo/telemetry/packages/`, never
raw capture and never a shared event log. Capture stays local-only
permanently; read `repo/telemetry/README.md` before filing or absorbing a
package.
The engine boundary (`core/placement-rules.md`'s Engine Code section),
extension registries, and envelope schema versioning are all built and
closed — see Git history for the evidence trail, not this table.

## Rules

One sequencing constraint remains:

- Telemetry capture is local-only, permanently. A telemetry evidence package
  is the only shared shape; it must carry
  a `verdict: pass` `gate-attestation.json` and must not cite private corpus
  paths.

Adding an engine module to the object graph is a deliberate act: do not add
one as a side effect of an unrelated edit, because every one changes
`ref check`'s object count and the derived registry.

Current architectural constraints are documented in their canonical owners:
the engine boundary in `core/placement-rules.md`, the telemetry contract in
`repo/telemetry/README.md`, and executable engine modules and tests.
