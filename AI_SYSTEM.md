# Hydra Operating Contract

## Checklist

1. Run `python3 .hydra-framework/scripts/hydra.py board` before substantial work, to see what is already in flight and who owns it.
2. Read `.hydra-framework/core/placement-rules.md` before adding shared framework knowledge, task state, or integrations.
3. Before broad repository search, query canonical knowledge instead of reading a directory: `hydra.py knowledge-search "<query>"` for ranked cited snippets, `hydra.py compile-context --task "<task>"` for a bounded read-first packet.
4. Reach for an existing Hydra skill, workflow, agent, or tool capability before improvising a procedure: scripts for deterministic work (validation, adapter export, migration), subagents for judgment work (research, review, summarization).
5. Keep private thinking, planning, source material, and machine state out of Git, in `.hydra-framework.local/`. `hydra.py note "<anything>"` is the zero-ceremony way in.
6. Before ending a session, record durable outcomes (decisions, facts, finished task steps) in their canonical shared location, not only in conversation.
7. Capability profiles are inspection-only until reconciliation is explicitly enabled: use `hydra.py profile list`, `hydra.py profile show`, and `hydra.py export-adapters --profile <name> --dry-run` to preview them; do not treat a preview as an active selection.
8. Generated provider adapters (`.claude/skills/hydra-*`, `.codex/agents/hydra-*`, and similar) are Git-ignored, not tracked: a fresh clone has none materialized. If a Hydra skill or subagent you expect is missing, run `python3 .hydra-framework/scripts/hydra.py export-adapters` before assuming it does not exist.
