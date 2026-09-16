# Evidence and Telemetry

For canonical ownership and maintainer evidence, see the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).

Status: operating guide

Use this page to separate evidence that can support review from telemetry that
must remain private. It also distinguishes the implemented redaction and
evidence mechanisms from capture work that still needs real provider-traffic
validation.

## Evidence Boundary

Keep review evidence proportional and reproducible: the command, its exit
result, and its relevant output path or verdict. Validation demonstrates
deterministic contracts, while human review still evaluates scope, clarity,
and whether an asserted behavior is actually implemented. See
[Validation](/project-wiki/hydra-framework/operations/validation.md#evidence-for-review) for the normal evidence route.

Telemetry is different. Local capture belongs under the private tier. Shared
state may contain a governed telemetry evidence package with derived aggregate
metrics and a redaction-gate attestation, but never raw events, prompts,
transcript text, command output, or a private local path.

## Choose a channel

Use the channel that matches the kind of evidence you have. A reflection is a
sanitized observation about using Hydra. Telemetry evidence answers a measured
runtime question. Neither channel is a shortcut around owner review.

| Situation | Channel | Required boundary |
| --- | --- | --- |
| A rule, workflow, or page caused repeatable friction, confusion, or a confirmed gap, but there is no measured corpus to share | Reflection packet | File one short sanitized packet, or keep a half-formed thought private with `hydra.py note`; do not include raw logs or transcripts. |
| A question needs counts or other runtime aggregates | Telemetry evidence package | Run the redaction gate, use aggregate report output, and keep raw events in the private tier. |
| A deterministic contract or source declaration needs checking | Validation or wiki audit output | Keep the command, exit result, finding path, or report verdict; do not turn a report into a claim of semantic completeness. |

## Reflection lifecycle

The [reflection queue contract](/.hydra-framework/evolution/reflections/README.md)
defines two non-terminal states: `open` and `held`. An `open` packet is a
sanitized observation awaiting an outcome. A `held` packet also carries a
dated `Held-Until:` because one more observation is needed. The queue's
terminal outcomes delete the packet because Git history is the archive.

Use the [session reflection skill](/.hydra-framework/capabilities/skills/session-reflection/skill.md)
to decide whether the observation is durable and to write at most one packet
from already-loaded context. Use the [reflection absorb skill](/.hydra-framework/capabilities/skills/reflection-absorb/skill.md)
to list and select packets, propose deletion, a task follow-up, a candidate,
an evolution record, or an owner-approved canonical edit. Owner approval is
required before changing shared state, including deleting a packet. `validate`
checks packet shape, while queue age and depth are advisory notes rather than
blocking failures.

## Implemented Mechanisms

The current telemetry surface provides a field-classification and redaction
contract, local append-only capture, a gate that uses poisoned fixtures, an
aggregate report, and a governed evidence-package queue. Use these commands
when a measured question needs a shareable review artifact:

```bash
python3 .hydra-framework/scripts/hydra.py telemetry gate
python3 .hydra-framework/scripts/hydra.py telemetry report --json
python3 .hydra-framework/scripts/hydra.py telemetry evidence create --slug <slug> --question "<question>"
```

`telemetry report` is report-only and emits derived aggregates. `telemetry gate`
returns failure when field classification, poison handling, spillover limits,
or minimum event thresholds fail. The evidence command refuses to create a
package when the gate verdict fails. When it succeeds, it creates the package
structure, but the question, findings, and method still need a reviewed
explanation. `hydra.py validate` then checks the package as part of its normal
telemetry-evidence validation.

Telemetry packages use `open`, `absorbed`, `superseded`, and `rejected` status
values. Terminal packages remain in the queue as the durable record of a
measurement, unlike reflection packets. Only `open` packages create drain
pressure, and stale or deep queues are advisory notes.

## Deferred Provider-Traffic Capture

The redaction contract and evidence queue do not prove that every provider's
live traffic is captured. Hydra's package state records capture against real
provider traffic as deferred until a future task consumes the contract. Treat
that as a routing boundary: do not claim provider-traffic coverage from a gate
attestation, and create a scoped follow-up task when such integration is ready
to be implemented and validated.

For a review handoff, retain the measured question, the gate verdict, the
aggregate report command, the package path, and the validation result. A clean
gate proves the redaction contract for the rows it examined; it does not prove
that an unobserved provider or an undeclared data source was captured.
