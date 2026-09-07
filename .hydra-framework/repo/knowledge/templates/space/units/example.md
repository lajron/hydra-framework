# Unit Examples

One worked example per `unit_kind`, so a real unit is a copy-and-fill rather
than a blank page. These are prose references, not live objects -- like
every other file in `templates/`, they carry no frontmatter envelope, so
`ref check` never resolves their placeholder `hydra://` ids or paths. Copy
one block into a real `units/<slug>.md` file (with a real envelope, `uid`,
and verified paths) rather than editing this file in place.

A knowledge space needs units only above roughly five durable questions; below
that, a single `overview.md` is correct (`repo/knowledge/../../core/knowledge-architecture.md`).

## `answer` -- most units

```markdown
---
hydra_id: hydra://knowledge-unit/<space-slug>/<slug>
uid: <fresh uuid4>
schema_version: 3
kind: knowledge-unit
unit_kind: answer
title: <Title>
status: active
scope: <repo-slug|base-seed|common-seed>
owners:
  team: <owner>
relations:
  - hydra://knowledge-package/<space-slug>
provenance:
  sources:
    - <path to the source of truth this answer was verified against>
question: "<one operational question, ending in '?', <= 120 chars>"
group: <optional grouping label, metadata only>
certainty: confirmed
checked_on: YYYY-MM-DD
reads:
  - <path resolved into a compile-context candidate when this unit is selected>
requires: []
see_also: []
verify:
  - <command that checks the claim below still holds>
---

# <Title>

## Answer

Two to four sentences. A cheap agent reading only the frontmatter plus this
section should be able to act, or know it needs to expand.
```

## `map` -- where the code for an area lives

The only kind allowed to be mostly a path list; every `reads:` entry must
resolve (`validate_units_dir` checks this for every kind, not just `map`,
but `map` is the kind whose whole job is naming paths).

```markdown
---
unit_kind: map
question: "Where does <area>'s code live?"
reads:
  - <path>
  - <path>
---

# <Title>

## Answer

<Area> lives under `<path>`. Entry point: `<path>`. Tests: `<path>`.
```

## `rule` -- a normative constraint from an owning authority

Must cite a non-empty `provenance.sources` naming the authority.

```markdown
---
unit_kind: rule
question: "What does <authority> require for <situation>?"
provenance:
  sources:
    - <the authority document or spec section>
---

# <Title>

## Answer

<The constraint, stated as a rule, with the authority's own wording where
it matters.>

## Rules

- <the concrete, checkable form of the constraint>
```

## `divergence` -- authority and implementation disagree

Must set `certainty: conflicting`, name both sides, and state the effect on
agents -- never resolve the disagreement by picking whichever reading makes
the unit easier to write.

```markdown
---
unit_kind: divergence
certainty: conflicting
question: "Where do <authority> and the implementation disagree on <topic>?"
---

# <Title>

## Answer

<Authority> says <X>. The implementation actually does <Y>.

## Effect On Agents

<What an agent must do differently because of this gap -- which side to
follow for which purpose, and what breaks if it follows the wrong one.>
```

## `status` -- what is built vs. not

Requires `checked_on`.

```markdown
---
unit_kind: status
checked_on: YYYY-MM-DD
---

# <Title>

## Answer

Trust this over any plan document: plans describe intent, this describes
the build.

## Status

| Capability | Status | How to verify |
| --- | --- | --- |
| <thing> | built / not started / decided, no code | <command> |
```
