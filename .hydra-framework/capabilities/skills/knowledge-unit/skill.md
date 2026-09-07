# Knowledge Unit Skill

## Capability

Write one knowledge-package unit, a durable, addressable answer to one
operational question, or revalidate an existing one against its source of
truth. A unit is a Markdown object under a package's `units/` directory with
`kind: knowledge-unit`; its `reads:` resolve into real `compile-context`
candidates and its `requires` edges are budget-exempt, so it is a compiler
input, not documentation.

## Trigger

- A ledger row, intake note, or task already names a knowledge-package
  destination for one bounded piece of durable meaning.
- An existing unit needs re-checking because its cited paths, commands, or
  claims may have drifted from the tree.

Do **not** trigger this skill to decide *whether* something belongs in a
knowledge space at all. That classification is not this skill's job. See
Boundaries.

## Inputs

- The target package's `routing.yaml`, `state.md`, and (if present) its
  matching route or context pack.
- The source material: a ledger row's staged file, a verified repository
  fact, or the unit's own existing content for revalidation.
- `repo/knowledge/certainty-model.md` for the `certainty:` vocabulary.

## Output

- One `units/<slug>.md` file with a complete `knowledge-unit` envelope, or a
  corrected/updated existing one.
- For a revalidation that finds drift too ambiguous to fix directly: a
  `unit_kind: divergence` unit instead, or a `problems.md` entry.
- A `validate-package-docs` and `ref check` pass for the touched package.

## Procedure

1. **Destination guard, not classification.** If the source material does not
   already name a knowledge-package destination, stop and return to
   `capabilities/workflows/material-migration.md` step 6, which owns the
   eight-way verdict (`repo/knowledge/`, `core/`, `project-wiki/`,
   `capabilities/`, `evolution/`, `tasks/`, `kept-private`, `rejected`). Do not
   restate that taxonomy here. That duplication is exactly how the two would
   drift apart.
2. **Route before reading widely.** Read the package's `routing.yaml`, then
   `state.md`, then the matching route or context pack. These exist to answer
   "where does this belong" without a broad search of the tree.
3. **One question.** State it in frontmatter, ending with `?`, at most 120
   characters. If answering it needs "and", it is two units. Split before
   writing either.
4. **Verify before writing.** Every path, type, endpoint, field, enum, and
   command the unit will cite must resolve in the *current* tree, or carry an
   explicit `certainty` marker from `certainty-model.md` (`unresolved` for
   unshipped work, not a prose caveat). Re-derive against the live tree.
   never copy a worked example from stale source material without re-checking
   every path it cites still exists.
5. **Answer-first.** `## Answer` is the first body section, two to four
   sentences: a cheap agent reading only the frontmatter plus `## Answer`
   should be able to act, or know it needs to expand. Everything else is
   expansion, in whatever sections the content actually needs.
6. **`requires` vs `see_also`.** Ask: would acting on this unit alone, without
   that other one, likely be wrong? Yes: `requires`. Anything else:
   `see_also`. `requires` is budget-exempt and therefore expensive to
   over-use. State this in the unit's own review, not just here.
7. **Divergence, not resolution.** When the source of truth and the
   implementation disagree, write a `unit_kind: divergence` unit
   (`certainty: conflicting`, both sides named, `effect_on_agents` stated) and
   add it to the relevant route's `requires` once routes exist. Never pick
   the reading that makes the unit easier to write. A finding that is not a
   divergence but is still out of this unit's scope goes to `problems.md`
   with evidence and a next action, not into the unit as a tangent.
8. **Route only if the entry changed.** Adding a unit does not automatically
   need a `routing.yaml` edit.
9. **Validate and hand off.**
   ```bash
   python3 .hydra-framework/scripts/hydra.py ref index
   python3 .hydra-framework/scripts/hydra.py validate-package-docs --package <slug>
   python3 .hydra-framework/scripts/hydra.py ref check
   ```
   Update `state.md` as a pointer only (≤ 40 lines); add one handoff line and
   drop the oldest if the package keeps a handoff section.

**The floor:** below roughly five durable questions, a package should not
have units at all. A single `overview.md` is correct. Do not manufacture
units to reach a target count.

## Revalidation Mode

Starts from an existing unit instead of a ledger row: run steps 4-9 only,
plus:

- Correct drift directly in the unit when the source of truth is unambiguous.
- Record a divergence (step 7) when it is not. Drift silently "cleaned up"
  against an ambiguous source is how a package acquires confident wrong
  facts.
- If a source in `provenance.sources` has changed more recently than
  `checked_on`, that is the signal to revalidate, not a reason to bump
  `checked_on` without re-checking.
- After re-reading the cited sources and updating the unit prose, run
  `python3 .hydra-framework/scripts/hydra.py knowledge fingerprint --unit <hydra-id>`
  for that one unit so `provenance.source_digests` records the checked source
  content. Do not use or create package-wide or bulk fingerprint refreshes.

## Boundaries

- Classification into the eight-way verdict is owned by
  `capabilities/workflows/material-migration.md` step 6, and its ledger
  records it per row. This skill enforces the destination guard; it does not
  duplicate the taxonomy, and it does not decide a row's verdict itself.
- Do not start or resume a bulk ledger triage from this skill. It writes or
  revalidates units one at a time, on request or per a row already routed
  here.
- Do not invent a unit for content nothing will point at. A unit with no
  route and no `requires` naming it is wiki material, not a unit.
- Do not add `max_tokens`, a `context_shape` field, or any per-unit token cap.
  The context compiler's `--budget` already owns that at the caller.

## Validation Expectations

`validate-package-docs --package <slug>` and `ref check` clean after every
change. A new or edited unit that fails either is not done.

## Related

- `.hydra-framework/capabilities/workflows/material-migration.md`
- `.hydra-framework/core/knowledge-architecture.md`
- `.hydra-framework/repo/knowledge/certainty-model.md`
- `.hydra-framework/capabilities/skills/repository-inspection/skill.md`
