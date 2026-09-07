---
name: hydra-seed-reconciliation
description: Compare this repository's Hydra copy against its base seed and decide what should flow back. Use when reconciling a diverged .hydra-framework/, or deciding whether a local change belongs in the shared framework.
---

# Seed Reconciliation Skill

## Capability

Compare this repository's `.hydra-framework/` against the base seed it descends from, classify the differences, and decide which local changes should flow back into the base for future repositories.

This is the return path of Hydra's copy-based spread. Copies diverge; without reconciliation every repository forks permanently.

## Procedure

1. Read `evolution/adaptations.md` first. It records deliberate local changes, including deletions, and marks them `repo-local` or `promote-candidate`.
2. Get the machine diff: `python3 .hydra-framework/scripts/hydra.py diff-base --base <path-to-base-checkout>`. It compares by content hash and splits differences into `explained` and `unexplained` using the adaptation ledger.
3. Read `lineage` in `manifest.yaml` to learn which base version this copy descends from. A missing lineage block means the classification is less trustworthy. Say so.
4. Classify unexplained differences by intent, not just by content:
   - `promote`: solves a general problem any repository would hit. Candidate for the base seed.
   - `repo-local`: correct here, wrong or meaningless elsewhere (host-specific paths, one team's conventions, this repository's knowledge spaces).
   - `stale`: local copy is behind the base. The base version should win.
   - `conflicting`: both sides changed the same meaning. Needs a human decision.
5. For every `promote` candidate, require evidence before recommending it: the observed problem, the change, and some sign it worked. A change that only looks tidier is not a promotion candidate.
6. Never silently overwrite either side. Produce a recommendation; let a human or an explicit follow-up task apply it.
7. Write one improvement record per promotion candidate into `evolution/candidates/` using `evolution/templates/improvement-record.md`. Reference the base version and the local file.
8. For new deliberate local differences, append an adaptation record with `hydra.py evolution record` so the next reconciliation can separate intent from drift.
9. Leave explained `repo-local` differences alone and say why. Revisit explained `promote-candidate` entries only when the evidence still supports promoting them.

## Output

One line per unexplained differing path:

`<path>: <classification>: <what differs>. <recommendation>.`

Then a short summary: explained count, unexplained counts per classification, promotion candidates written, and anything needing a human decision.

## Boundaries

- Report and record; do not apply base-to-local or local-to-base overwrites unless explicitly asked.
- Do not promote repository-specific knowledge spaces, task records, wiki pages, or private local state into the seed.
- Do not treat a newer timestamp as authority. Content and stated intent decide, not mtime.
- If the base checkout is unavailable, say so and stop. Do not guess what the base contained.
