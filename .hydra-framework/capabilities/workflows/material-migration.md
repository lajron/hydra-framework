---
hydra_id: hydra://capability/workflow/material-migration
uid: 821d266e-30ed-48ef-8e96-f574a88b4ef1
schema_version: 3
kind: workflow
title: Transferred Material Migration
status: active
scope: base-seed
owners:
  team: hydra
relations:
  - hydra://migration-ledger/intake-migrations
provenance:
  sources:
    - .hydra-framework/repo/knowledge/intake-lifecycle.md
    - .hydra-framework/core/placement-rules.md
---

# Workflow: Transferred Material Migration

## Objective

Clear a source area of untriaged material, such as a transferred docs folder,
an inherited wiki, or a per-developer notes pile, into its correct canonical owners,
and reach a state where the migration is finished rather than perpetually open.

Use this when the material is large enough that per-item intake cannot answer
"what is left." For a single source, use ordinary intake instead.

## Preconditions

- Hydra is adopted in the host repository.
- The source area is identified and bounded.
- `.hydra-framework.local/` is confirmed ignored by Git before using private
  staging.

## Procedure

1. **Bound the effort.** Name the source roots. Count items and measure size per
   root. Do not read contents yet. A migration whose scope is not written down
   grows until it is abandoned.

2. **Determine who owns the history, and route the staging destination.** For
   each source root, check whether Git tracks it:

   ```
   git ls-files <root> | wc -l
   git check-ignore -v <root>
   ```

   If Git tracks it and the material was already shared, stage it in the tracked
   repository root under `.migrations/<source-slug>/`. Moving already-shared
   material into another shared, tracked source area exposes nothing new and
   keeps migration evidence citeable from shared Hydra records.

   If Git does not track it, or the material is private, sensitive, ignored, or
   never committed, move it to private staging under
   `.hydra-framework.local/migrations/<slug>/originals/`. In that case the
   working copy is the only copy, and step 4 becomes the sole undo. Record which
   case applies per source root.

3. **Request the bounded staging action.** The agent inventories the named
   source roots read-only, records their Git/private state, classifications,
   exact staging destinations, and reversible move plan, then creates one
   staging approval request for the coherent source-area batch:

   ```bash
   python3 .hydra-framework/scripts/hydra.py migration request-stage <slug> <batch> \
     --source <root> --route <shared|private> \
     --worker-instance <instance-id> --capability-class <class>
   ```

   Risk signals, uncertain Git state, and ambiguous classification stay visible
   as approval reasons. The command writes audit state only; it does not move a
   source. Create a task record when the effort will span sessions, and link it.

4. **Approve the staging move before promoting anything.** A human reviews the
   bounded request and records `approve`, `reject`, or `revise`:

   ```bash
   python3 .hydra-framework/scripts/hydra.py migration decide <slug> <batch> approve
   ```

   Approval immediately applies the exact recorded move and continues by
   creating the workspace ledger. Rejection requires a terminal rationale.
   Revision requires guidance, retains the batch identity, and resubmits after
   the agent updates the action. Do not bypass this gate with a manual move.

   **Already-shared source:** create `.migrations/` if needed, then move each
   source root under a simple source slug, preserving relative paths:

   ```
   mkdir -p .migrations/<source-slug>
   ```

   Use one source root per staged input. The staged material is source, not
   canonical Hydra knowledge; drain it through the shared ledger before treating
   any claim as adopted.

   **Private or never-committed source:** the private tier is seeded by
   `hydra.py init-local`. Run it first if the migration staging area is absent:


   ```bash
   python3 .hydra-framework/scripts/hydra.py init-local
   git check-ignore -v .hydra-framework.local/migrations/<slug>/originals
   ```

   The `check-ignore` call must return a matching `.gitignore` line. Run it after
   the `mkdir`, because a directory-only ignore pattern cannot match a path that
   does not exist yet. Checking first and seeing no match is the false negative
   that leads to committing private material.

   Then move each source root under `originals/`, preserving relative paths.

   **Both cases:** move, do not copy: leaving both means two divergent piles and
   an unclear authority. This single step drains the repository and creates the
   undo. Everything after it is recoverable.

   When Git never tracked the source, `originals/` is now the only copy of it and
   Git is not protecting it. Confirm the move landed before deleting anything, and
   arrange a backup if the material matters. This risk does not apply to tracked
   `.migrations/<source-slug>/` staging, because Git already held the material.

5. **Inventory into the ledger.** One row per item, status `pending`. Group rows
   for sets that share a verdict and destination, and group rather than enumerate
   when filenames are themselves sensitive.

6. **Triage per row.** Assign a verdict and destination:

   - reusable procedure, convention, architecture fact → `repo/knowledge/`
   - a durable rule or rationale → its canonical `core/`, `repo/knowledge/`,
     `capabilities/`, `evolution/`, or code owner
   - human-facing explanation → `project-wiki/<project>/`
   - reusable agent, skill, workflow, tool → `capabilities/`
   - framework improvement → `evolution/`
   - active work or follow-up → `tasks/`
   - private, machine-specific, or credential-bearing → stays in staging, `kept-private`
   - no durable meaning → `rejected`, with a one-line reason

   Route anything needing full provenance or a privacy review through `raw/` and
   `triage/` and link it from the row. Small obvious items need only the row.

7. **Propose in batches by destination, not in source order.** All rows headed
   for one knowledge space at once. The agent writes a bounded proposal
   manifest and drafts under the batch workspace. New package boundaries,
   conflicts, sensitive/private material, and ambiguous classifications become
   reasons on the same coherent batch approval rather than separate per-unit
   approvals.

   A fresh independent validator agent instance, selected by provider-neutral
   capability class, must validate the proposal without drafting-chain context.
   Its evidence is digest-bound to the proposal and includes at least
   `validate-package-docs --path <proposal>` and a reference check. Record the
   proposal and evidence with `migration propose` and
   `migration validate-batch`; the latter prepares the publication request.

8. **Approve publication.** A human records `approve`, `reject`, or `revise` on
   the publication request. Approval verifies the proposal, draft, validation,
   and target digests again, applies the already-validated canonical writes,
   and continues automatically. Reject records a terminal rationale. Revise
   keeps the same batch, invalidates the old evidence, incorporates guidance,
   revalidates with a fresh independent instance, and resubmits. Set terminal
   status per ledger row as it lands and write a promotion record under
   `intake/promoted/` for substantial batches.

9. **Leave a redirect where people will look.** One stub at the old root pointing
   at the new authority and the ledger. One stub per root, not per file.

10. **Close through the removal gate.** Reconcile every inventoried item to
    `promoted`, `redirected`, `rejected`, or `kept-private`, then request close
    with the exact staged paths proposed for removal. The request refuses
    missing or non-terminal items. Human approval rechecks freshness and removes
    only those exact staged originals; the ledger, batch state, validation
    evidence, decision history, and workspace remain as the audit trail. Reject
    records a terminal rationale; revise keeps the same batch and resubmits the
    corrected reconciliation.

11. **Validate.** `hydra.py validate`, plus `hydra.py doctor` if adapter surfaces
    changed. Record commands and results in the task record.

## Boundaries

- Do not delete a source file as the first action on it. Move first.
- Do not move, publish, or remove originals before the corresponding human gate
  is approved. One approval covers one bounded source-area/package batch.
- Canonical proposals require a fresh independent validator agent instance with
  no drafting-chain context. Canonical workflow state names capability classes,
  never provider or model names.
- Do not promote unverified claims to canonical status to empty the ledger faster.
  `rejected` and `kept-private` are correct outcomes; a wrong knowledge file is not.
- Do not commit previously-ignored material into the shared repository to create
  an archive. Private staging is the archive.
- Do not migrate as part of adoption. Adoption is non-destructive; this workflow
  is a separate opt-in effort the team asks for.
- Do not let one migration cover every source root in a large repository. Bound
  it, finish it, start another.

## Failure Modes

- **Private staging not ignored.** Verify with `git check-ignore` after creating
  the directory and before the move. A dir-only `.gitignore` pattern cannot match
  a path that does not exist, so a check run before `mkdir` reports no match
  whether or not the pattern is present.
- **Private staging never created.** `hydra.py init-local` creates and seeds the
  private tier without overwriting local files; `hydra.py doctor` reports when it
  is absent.
- **No undo.** Draining a Git-ignored source root without moving it first is
  unrecoverable. Step 2 exists to catch this.
- **Perpetual migration.** Without the counts block, the effort has no visible
  end and stalls half-done, leaving two authorities for the same subject.
- **Leaked filenames.** A ledger row can disclose what a private file is about
  even when its contents stay private. Group those rows.

## Related

- `.hydra-framework/intake/migrations/README.md`
- `.hydra-framework/intake/templates/migration-workspace/`
- `.hydra-framework/repo/knowledge/intake-lifecycle.md`
- `.hydra-framework/repo/knowledge/archive-and-supersession.md`
- `.hydra-framework/capabilities/workflows/task-lifecycle.md`
