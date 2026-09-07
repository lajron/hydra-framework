"""---
hydra_id: hydra://engine-module/object-family-registry
uid: 1eb7694e-2810-4fbf-a0f2-f4f4f2ee284a
schema_version: 3
kind: engine-module
title: Object Family Registry
status: active
scope: base-seed
owners:
  team: hydra
relations:
  - hydra://engine-module/object-handler-registry
provenance:
  sources:
    - .hydra-framework/core/architecture.md
---

The object-family registry is the first explicit extension registry.

The engine architecture requires that adding an object handler, validator, command
handler, command-result reducer, provider, or context/route provider be one
explicit registration rather than edits spread across central switchboards.
Object families went first because they were the only one of those six that
was *silently unenforced* — the reasoning is recorded in the slice's task
record. What was here before was a flat `token -> display name` dict consulted
for both an `hydra://` id prefix and a `kind`, so it could not say which
tokens a family actually claims, and:

- Four `kind` values this repository really authors — `agent`, `skill`,
  `workflow`, `tool-capability-registry` — were absent from it entirely. They
  resolved to `Capability` only because their ids begin `hydra://capability/`,
  so a misspelled `kind` was invisible.
- An unregistered family resolved to the literal string `"Unknown"`,
  `ref check` passed, and `ref index` exported `family: Unknown`.

Boring data plus two small functions: an explicit tuple
reviewed as code, no import-time scanning of the tree, and no family loaded
merely because something was found on disk. `family_for` keeps the previous
prefix-then-kind resolution and the `"Unknown"` fallback unchanged; what is
new is `unregistered_family_tokens`, which is what makes the registry
enforceable at all.

Runtime/Engine is registered as of the object-handler slice, which closed
the Runtime/Engine registration gap by making `.py` a document form
`objects.object_handlers` claims. Its token is `engine-module` rather than
`runtime-module` for two reasons: `runtime-module` is what the test suite uses as its canonical
*unregistered* prefix, so claiming it would quietly turn two negative tests
into passing positives; and `runtime` is a banned path stem under
architecture check 7, so it is the wrong word to promote into canonical
vocabulary. The family keeps the established name.

This module is itself one of the two objects in that family, which is why the
docstring above opens with an envelope. The registry is therefore addressable
in the same object graph it validates.
"""

from __future__ import annotations

import dataclasses

from hydra_engine.identity.hydra_ids import hydra_id_prefix

# Returned when no registered family claims either token. Kept as a real
# value rather than `None` because it is exported into the derived registry
# and printed by `ref resolve`; validation is what makes it visible now.
UNKNOWN_FAMILY = "Unknown"


@dataclasses.dataclass(frozen=True)
class ObjectFamily:
    """One family and the tokens it claims.

    Two tuples, not one, because the two positions are different questions:
    `id_prefixes` is matched against the first segment of an `hydra://` id,
    `kinds` against the object's declared `kind`. The flat map this replaced
    could not distinguish them, which is exactly why four real kinds went
    unregistered without anything noticing.
    """

    name: str
    id_prefixes: tuple[str, ...]
    kinds: tuple[str, ...]


# The ten tokens the flat map carried appear in *both* tuples of their family.
# That preserves the prior resolver behavior: the map accepted each of them in
# either position. Tokens added by this slice are placed only where they are
# actually true.
OBJECT_FAMILIES = (
    ObjectFamily(
        name="Knowledge",
        id_prefixes=(
            "knowledge-package", "knowledge-slice", "knowledge-template", "knowledge-unit",
            "knowledge-space", "knowledge-node", "knowledge-view", "knowledge-route",
        ),
        kinds=(
            "knowledge-package", "knowledge-slice", "knowledge-template", "knowledge-unit",
            "knowledge-space", "knowledge-node", "knowledge-view",
        ),
    ),
    ObjectFamily(
        name="Capability",
        # `agent`, `skill`, `workflow`, and `tool-capability-registry` are the
        # four kinds this repository authors under `hydra://capability/`. They
        # are kinds only: no object is identified as `hydra://agent/...`, so
        # listing them as prefixes would be inventing a shape nothing uses.
        id_prefixes=("capability",),
        kinds=("capability", "agent", "skill", "workflow", "tool-capability-registry"),
    ),
    ObjectFamily(
        name="Work",
        id_prefixes=("work", "migration-ledger"),
        kinds=("work", "migration-ledger"),
    ),
    ObjectFamily(
        name="Source",
        id_prefixes=("source", "integration-ledger", "promotion-record"),
        kinds=("source", "source-integration", "integration-ledger", "promotion-record"),
    ),
    ObjectFamily(
        # Runtime/Engine is an object family alongside Knowledge, Work,
        # Capability, Source, and Telemetry, not a Capability subtype. One
        # token is enough for the discoverable form, rather than mirroring the
        # full list of what the family covers (commands, reducers, validators,
        # providers, adapters, registries, resolvers, context services,
        # extension contracts): the discoverable unit is a Python module, and
        # a kind per role would be nine tokens with two real members.
        name="Runtime/Engine",
        id_prefixes=("engine-module",),
        kinds=("engine-module",),
    ),
    ObjectFamily(
        # Telemetry is a first-class object family. This registry settles
        # its one member: a bounded evidence package's `overview.md`.
        # `metrics.json` and
        # `gate-attestation.json` are plain JSON, claimed by no handler in
        # `objects.object_handlers`, so they never become objects at all --
        # the same reasoning that keeps Runtime/Engine to one token.
        name="Telemetry",
        id_prefixes=("telemetry-evidence",),
        kinds=("telemetry-evidence",),
    ),
)


def family_for(hydra_id: str, kind: str) -> str:
    """The family name for an object, by id prefix first and `kind` second.

    Prefix wins across the whole registry before any family's `kinds` is
    consulted, matching the previous flat-map resolution order exactly. No
    family may claim a token another family claims (asserted by this module's
    mirror test), so within each pass the answer does not depend on order.
    """
    prefix = hydra_id_prefix(hydra_id)
    if prefix:
        for family in OBJECT_FAMILIES:
            if prefix in family.id_prefixes:
                return family.name
    if kind:
        for family in OBJECT_FAMILIES:
            if kind in family.kinds:
                return family.name
    return UNKNOWN_FAMILY


def unregistered_family_tokens(hydra_id: str, kind: str) -> list[str]:
    """Which of this object's family tokens no registered family claims.

    Rendered fragments rather than structured pairs, so a caller can emit one
    finding each — the same shape `envelopes.missing_envelope_fields` returns,
    for the same reason: the list is consumed once, by validation.

    An absent `kind` produces nothing here. It is already reported as a
    missing mandatory envelope field, and saying it twice would push a reader
    toward inventing a value to silence the second message.
    """
    problems: list[str] = []
    prefix = hydra_id_prefix(hydra_id)
    if prefix and not any(prefix in family.id_prefixes for family in OBJECT_FAMILIES):
        problems.append(f"hydra_id family prefix `{prefix}`")
    if kind and not any(kind in family.kinds for family in OBJECT_FAMILIES):
        problems.append(f"kind `{kind}`")
    return problems
