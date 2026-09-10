---
paths:
  - ".claude/**/*.md"
  - ".claude/**/*.yaml"
  - ".agents/**/*.md"
  - ".codex/**/*"
---

# Provider Directories Are Generated

<!-- Generated-surface guard. Canonical source: .hydra-framework/core/placement-rules.md -->

Files under `.claude/`, `.agents/`, and `.codex/` are adapter surfaces exported
from `.hydra-framework/`. Editing them directly is almost always the wrong move:
`hydra.py export-adapters` overwrites the file and the change is lost.

## Before adding a skill, subagent, or rule here

Add it to the canonical module instead, then export:

| You want | Canonical location | Then run |
| --- | --- | --- |
| A reusable procedure or `/command` | `.hydra-framework/capabilities/skills/<slug>/skill.md` + `metadata.yaml` | `hydra.py export-adapters` |
| A subagent role | `.hydra-framework/capabilities/agents/<slug>/agent.md` + `metadata.yaml` | `hydra.py export-adapters` |
| A repeatable coordination pattern | `.hydra-framework/capabilities/workflows/<slug>.md` | — |

Set `kind: command` in skill metadata when only a human should trigger it; the
exporter turns that into `disable-model-invocation: true`.

## If a provider-native file is already here

For one isolated skill or agent added where its runtime expects it, reclaim it
rather than deleting it:

```bash
python3 .hydra-framework/scripts/hydra.py reclaim            # classify and plan
python3 .hydra-framework/scripts/hydra.py reclaim --promote  # move into canonical Hydra
python3 .hydra-framework/scripts/hydra.py export-adapters    # regenerate wrappers
```

Promoted metadata is marked `scope: repo-local` and `certainty: inferred`. Review
it: set a real capability class and effort, and decide whether the module belongs
in the shared seed or stays repository-local.

If provider-native modules are part of a broader legacy agentic setup, use the
framework-takeover skill and `capabilities/workflows/material-migration.md`.
That workflow preserves the setup's relationships and source history; reclaim
is only the mechanical route for isolated modules.

## Not generated

`.claude/settings.json`, `.claude/settings.local.json`, `.claude/rules/`, and
`README.md` files are hand-maintained adapter configuration. Edit those in place.
Keep secrets, machine paths, and personal preferences out of them — those belong
in `.hydra-framework.local/` or user-level provider config.
