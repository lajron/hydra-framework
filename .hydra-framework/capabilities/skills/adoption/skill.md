# Hydra Adoption Skill

## Capability

Integrate Hydra into a repository it was just copied into, and keep the integration incremental. This is the entry point when `.hydra-framework/` appears in a repository that has never used it.

Hydra spreads by copy: someone drops `.hydra-framework/` plus the entry files into a repository, then asks an agent to wire it up. This skill is that wiring procedure.

## Procedure

1. Establish where you are. Run `python3 .hydra-framework/scripts/hydra.py adopt` for a machine-checked report of what is present, what is missing, and what the host repository looks like. Do not hand-inspect first; the report is cheaper.
2. Confirm the framework is intact. If `adopt` reports missing required paths, the copy is incomplete; stop and report exactly which paths are missing rather than recreating them from memory.
3. Record lineage. If `manifest.yaml` has no `lineage.adopted_into` value, set it with `hydra.py adopt --record --repo <slug>`. Without lineage, a later `diff-base` cannot tell local adaptation from base drift.
4. Wire the provider surfaces the host repository actually uses:
   - Run `hydra.py export-adapters` to generate skill and subagent wrappers.
   - Create or update the provider entry file (`CLAUDE.md`, `AGENTS.md`) so it imports `AGENTS.md` and stays small.
   - Add hook and permission wiring only for runtimes the team uses.
5. Create the host repository's own review mapping for `.hydra-framework/` and `project-wiki/` in `.github/CODEOWNERS` or the code host's equivalent. The seed does not copy reviewer identities between repositories.
6. Do not document the whole repository. Pick the one or two areas where AI work already repeats, and create a knowledge space for those only. Everything else stays undocumented until repeated use justifies it.
7. Leave the host repository's existing docs in place. Treat them as source material to cite, not as content to migrate. Adoption is non-destructive. If the team later wants a source area cleared, that is a separate opt-in effort under `capabilities/workflows/material-migration.md`; name it as a follow-up rather than starting it here.
8. Validate: `hydra.py doctor` and `hydra.py selftest`. Record the commands and results.
9. Create a task record only if adoption will span more than one session.

## Boundaries

- Do not delete or rewrite the host repository's existing documentation, CI, or agent config.
- Do not create knowledge spaces, wiki pages, or task records speculatively. Adoption should add the smallest working surface.
- Do not copy provider secrets, machine paths, or personal settings into shared Hydra state.
- If the host repository already has a different AI framework, report the overlap. Use the framework-takeover skill and material migration workflow only after the owner explicitly scopes the takeover.

## Output

Report: what was already present, what was generated, what lineage was recorded, which areas were deliberately left undocumented, and the validation evidence.
