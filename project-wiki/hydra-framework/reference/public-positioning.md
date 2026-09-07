# Public Positioning Brief

Status: first-pass positioning and evidence backlog

This page guides public-facing documentation. It translates the current Hydra
implementation for evaluators; it does not own framework rules or behavior.

Use the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence)
for maintainer evidence. The reader routes below explain the subjects without
requiring a walk through implementation files.

## Primary Audiences And Pain Points

1. **Software teams using AI agents across sessions or providers.** Durable
   context is often trapped in chats, provider-local memory, or duplicated
   instruction files. Work is rediscovered, ownership is unclear, and private
   scratch can be mistaken for shared fact.
2. **Maintainers introducing shared AI-work practices across repositories.** A
   copied framework can drift, provider surfaces can become competing sources,
   and repository-specific adaptation is hard to distinguish from stale base
   state without lineage and reconciliation.
3. **Technical evaluators and AI-infrastructure maintainers.** They need a
   source-traceable explanation of what exists today, what is mechanically
   checked, and what still lacks outcome evidence.

Audience priority remains an owner choice. This first pass leads with teams
already experiencing multi-session or multi-provider coordination pain.

## One-Sentence Promise

**Hydra gives a repository a provider-neutral, governed working layer for
AI-assisted engineering, so shared context, reusable capabilities, and
in-flight work live with the code instead of inside one chat or provider
surface.**

## Evidence-Backed Differentiators

1. **Repository-contained canonical state with explicit trust boundaries.**
   Shared framework and repository meaning is Git-tracked; owner-scoped task
   state is tracked for handoff; private thinking and machine state stay in an
   ignored local tier. See [State Tiers](/project-wiki/hydra-framework/concepts/state-tiers.md)
   for the reader-facing explanation.
2. **Deterministic local lexical retrieval plus bounded context compilation.**
   Search uses stable exact, route, lexical, graph, ID, and path ordering; it
   falls back to source scanning when the private SQLite index is absent.
   Context compilation reports selected and omitted candidates, token estimates,
   provenance freshness, and route-specific reminders. This does not make agent
   behavior deterministic. See [Object And Context Model](/project-wiki/hydra-framework/architecture/object-context-model.md)
   for the reader-facing explanation and evidence route.
3. **One canonical capability layer, generated into provider adapters.** Skills
   and agents are authored once under `.hydra-framework/capabilities/`; one
   planner generates provider-specific wrappers and provenance sidecars, and
   drift classification distinguishes generated, orphaned, drifted, and stale
   surfaces. See [Capabilities](/project-wiki/hydra-framework/extending-hydra/capabilities.md)
   and [Provider Adapters](/project-wiki/hydra-framework/extending-hydra/provider-adapters.md).
4. **Owner-scoped, Git-recoverable task lifecycle.** The board is computed from
   task records; lifecycle commands start, checkpoint, hand off, and complete
   work while enforcing owner and outcome boundaries. See [Task Lifecycle](/project-wiki/hydra-framework/working-with-hydra/task-lifecycle.md).
5. **Copy, adoption, and reconciliation are first-class workflows.** The copy
   plan excludes source-repository task records, adoption reports integrity and
   lineage, and `diff-base` classifies content differences against recorded
   adaptation. See [Seed And Adopt Hydra](/project-wiki/hydra-framework/start-here/adopt-a-repository.md)
   and [Evolution](/project-wiki/hydra-framework/evolution/evolution.md).

## Terminology

| Use | Meaning and boundary |
| --- | --- |
| **repository-contained AI-work infrastructure** | The public category: repository state, workflows, adapters, and validation for AI-assisted work. |
| **canonical shared state** | Git-tracked rules, knowledge, capabilities, and validation owned under `.hydra-framework/`. |
| **personal task state** | Git-tracked, owner-scoped, resumable work under `tasks/personal/<owner>/`; not a shared repository fact. |
| **private local state** | Ignored thinking, machine configuration, source staging, and scratch under `.hydra-framework.local/`; never shared authority. |
| **provider adapter** | A runtime discovery surface derived from canonical capabilities; not a source of truth. |
| **deterministic local lexical search** | The verified `knowledge-search` retrieval and ordering procedure only. Never shorten this to “deterministic Hydra.” |
| **bounded context compilation** | Selection of cited read pointers under a caller-supplied approximate token budget, with explicit overage and omission reporting. |
| **knowledge space** | A routed, validated local knowledge structure for one repository accountability boundary with enough durable complexity. |
| **adoption** | Copying and wiring Hydra into a repository while preserving existing host material. |
| **seed reconciliation** | Comparing an adapted copy with its base and classifying explained or unexplained differences. |
| **mechanical validation** | Checks over repository artifacts and contracts. It is not proof of security, correctness, or good agent judgment. |

Avoid describing Hydra as only “memory,” an autonomous engineering platform, a
security layer, or a deterministic agent system.

## Claims That Must Wait

Do not claim any of the following without published evidence appropriate to the
claim:

- faster retrieval, task completion, onboarding, or handoff
- higher productivity, lower cost, fewer tokens, or fewer tool calls
- more reliable or more correct agent output
- secure, safe, privacy-preserving, or compliant operation
- deterministic end-to-end behavior
- zero installation, zero configuration, or universal provider compatibility
- broad adoption, production readiness, testimonials, or sponsor readiness

Repository tests can support implementation claims. They cannot substitute for
comparative outcome evidence or external validation.

## Ordered Public-Documentation And Evidence Backlog

1. **Run the baseline-versus-Hydra retrieval benchmark.** Freeze a representative
   repository corpus and task set. Compare a baseline workflow using normal
   repository search and file reads with a Hydra workflow using
   `knowledge-search` and `compile-context`, under the same model, tool access,
   time limit, and starting prompt. Record relevant-source recall, irrelevant
   context loaded, input tokens, tool calls, wall time, completion, and blinded
   answer quality. Publish the corpus, protocol, raw results, failures, and
   limitations. Only then add a README proof section.
2. **Build a separate agent-correctness and safety fixture benchmark.** Use
   hermetic tasks that test private/shared placement, wrong-owner task edits,
   stale knowledge, generated-surface edits, adoption conflicts, and validation
   recovery. Score rule violations and successful recovery separately from
   retrieval performance.
3. **Record a short real-command demo.** Capture a reproducible terminal flow:
   `board`, `knowledge-search`, `compile-context`, `task start`, and a targeted
   `validate`. Produce a short GIF or a small set of screenshots with the exact
   commit and commands, avoiding staged or invented output.
4. **Add an evidence page and README proof section.** Explain benchmark design,
   publish versioned results, link raw artifacts, and state what the numbers do
   not establish. Keep volatile measurements out of canonical framework rules.
5. **Create a visual identity and icon plan.** Check name and mark availability,
   define a simple icon brief, accessibility and small-size requirements,
   monochrome variants, source-file ownership, and contributor licensing before
   generating assets.
6. **Establish public participation destinations.** Choose a license, contribution
   guide, code-of-conduct stance, issue or discussion route, maintainer contact,
   and vulnerability-reporting destination before adding contribution, contact,
   or security links.
7. **Prepare sponsorship only after evidence and governance exist.** Require a
   credible baseline benchmark, a published maintenance scope, named fund
   recipient, transparent use-of-funds statement, sponsor benefit boundaries,
   and a real destination. Do not add donation badges or placeholders before
   those are approved.
8. **Add external evidence as it becomes real.** Publish adopter case studies,
   compatibility notes, testimonials, and usage numbers only with permission,
   dates, methodology, and traceable sources.

## Canonical Routes

Use the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence)
to trace wiki claims and the [Hydra Framework](/project-wiki/hydra-framework/hydra-framework.md)
route for reader-facing context. Public wording should change when canonical
owners change, not the other way around.
