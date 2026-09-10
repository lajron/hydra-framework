---
name: hydra-framework-takeover
description: Take over an existing non-Hydra or legacy agentic setup by detecting foreign provider material, confirming scope, and draining it through the material migration workflow.
---

# Framework Takeover Skill

## Capability

Take over an existing non-Hydra or legacy agentic setup in a host repository and
drain its durable meaning into canonical Hydra state without treating provider
surfaces as sources of truth.

Use this for already-existing AI architecture such as `.claude/`, `.codex/`,
`.agents/`, `.cursor/`, `.windsurf/`, rule files like `.cursorrules` or
`.windsurfrules`, Copilot instructions, prompt libraries, old agent definitions,
or `docs/ai/` style documentation. This is a thin front door onto
`capabilities/workflows/material-migration.md`; it adds detection and scoping for
foreign agentic architecture, then reuses that workflow's staging, ledger,
triage, promotion, redirect, and validation rules.

This is opt-in and separate from adoption. Adoption stays non-destructive and
may name takeover as a follow-up, but it does not start one.

## Procedure

1. **Detect candidate roots.** Start with cheap checks:

   ```bash
   python3 .hydra-framework/scripts/hydra.py adopt
   python3 .hydra-framework/scripts/hydra.py reclaim
   ```

   Then check the repository root for common foreign agentic markers:

   | Source | Markers |
   | --- | --- |
   | Claude | `.claude/`, `CLAUDE.md` |
   | Codex | `.codex/`, `.agents/`, `AGENTS.md` |
   | Cursor | `.cursor/`, `.cursorrules` |
   | Windsurf | `.windsurf/`, `.windsurfrules` |
   | Copilot | `.github/copilot-instructions.md` |
   | Prompts | `prompts/` |
   | Docs | `docs/ai/`, `docs/agents/` |

   A raw marker is not enough. Hydra's generated adapter surfaces intentionally
   use some of the same paths. Classify each marker before moving anything:

   - `Hydra-owned`: generated adapter files with valid `.hydra-adapter*.yaml`
     sidecars and a live canonical source under `.hydra-framework/capabilities/`.
   - `Provider-native`: `hydra.py reclaim` reports it as `orphaned`, `drifted`,
     or `stale`, or it is a provider file outside Hydra's generated plan.
   - `Foreign entrypoint`: `CLAUDE.md`, `AGENTS.md`, or similar root rule files
     that are not this repository's thin Hydra adapter shape.
   - `Needs owner decision`: settings, ignored files, local config, secrets-like
     names, top-level `prompts/`, or anything whose ownership cannot be decided
     by shape alone.

   Report every candidate root and classification before proceeding.

2. **Confirm scope with the owner.** Ask which candidate roots to take over now.
   Do not default to all of them. Material migrations are bounded on purpose, and
   takeover has the same rule: bound it, finish it, then start another if needed.
   If a `.migrations/` source or intake migration workspace is already active for
   the same material, finish or explicitly bound that effort before opening a new
   one.

3. **Route staging by history ownership.** Follow
   `capabilities/workflows/material-migration.md` step 2 exactly:

   ```bash
   git ls-files <root>
   git check-ignore -v <root>
   ```

   If Git tracks the material and it was already shared, stage it under the
   tracked repository root at `.migrations/<source-slug>/`. If Git does not track
   it, or the material is private, sensitive, ignored, or never committed, stage
   it under `.hydra-framework.local/migrations/<slug>/originals/` after confirming
   that location is ignored.

4. **Create the migration workspace.** Use the material migration workflow's
   workspace and ledger under
   `.hydra-framework/intake/migrations/<YYYY-MM-DD>-<slug>/`. Name the confirmed
   source roots and link any task record that will carry the work across
   sessions.

5. **Move before promoting.** Move the confirmed roots to the staging destination
   from step 3, preserving relative paths. Do not copy. Leaving both the old root
   and the staged root creates two authorities for the same material.

6. **Inventory breadth-first.** Put one pending ledger row per item, grouping
   rows with the same verdict and destination when appropriate. Inventory in this
   order:

   1. Entry and rule files first, because they state the old system's intent.
   2. Top-level provider config next.
   3. Tool, command, skill, and agent directories by path depth.
   4. Deep per-feature docs and prompts last.

7. **Triage through the material migration vocabulary.** Use the workflow's
   `Destination` column for the canonical owner or terminal outcome:
   `repo/knowledge/`, `project-wiki/`, `capabilities/`,
   `evolution/`, `tasks/`, `kept-private`, or `rejected`. Use `Verdict` for the
   closed action vocabulary: `triage`, `private-review`,
   `promote`, `import`, `link`, `alias`, or `reject`.

8. **Promote in batches by destination.** Drain all rows for one canonical owner
   together so related rules do not become duplicate fragments in several files.

9. **Stub only after the source root is terminal.** Leave partially drained files
   in staging while work is in progress. When every row for a source root is
   terminal, leave one redirect stub where people will look, pointing to the new
   authority and the ledger.

10. **Validate and report.** Verify every source root is empty or stubbed, no
    ledger row is `pending`, and every `deferred` row names a follow-up owner.
    Run:

    ```bash
    python3 .hydra-framework/scripts/hydra.py validate
    python3 .hydra-framework/scripts/hydra.py doctor
    ```

    Preserve the validation evidence for the final report.

## Output

Report detected markers, classifications, owner-confirmed scope, workspace and
ledger path, promoted authorities, remaining follow-ups, and validation
evidence.

## Boundaries

- Do not start takeover without an explicit human request. Detection and a scope
  question come first; nothing moves before the owner confirms the roots.
- Do not run takeover as part of adoption. Adoption may report overlap and name
  this skill as the follow-up.
- Do not route already-shared material to private staging. The material
  migration workflow routes already-shared material to `.migrations/`.
- Do not commit ignored, private, sensitive, or never-shared material just to
  make a shared archive. Private staging is the archive for that case.
- Do not delete or rewrite old rule files first. Move first, drain by ledger,
  stub last.
- Do not use this skill for Hydra-to-Hydra reconciliation by default. When the
  source is another Hydra copy, use the seed-reconciliation workflow first;
  capability-level reconciliation may be the right unit instead of file-by-file
  takeover.
- Do not promise `takeover scan`, `integrate`, or `explain-path` commands until
  they exist. Today this skill uses `adopt`, `reclaim`, and `migration`
  commands plus the material migration workflow when those commands are not
  available.

## Related

- `.hydra-framework/capabilities/workflows/material-migration.md`
- `.hydra-framework/capabilities/skills/adoption/skill.md`
- `.hydra-framework/capabilities/skills/seed-reconciliation/skill.md`
