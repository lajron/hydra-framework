# Knowledge Surfaces

Surfaces are audience-facing or interface-specific views of knowledge. This
directory records surface contracts — whether a surface is canonical, derived,
synchronized, private, generated, or hand-maintained. The pages themselves live
outside `.hydra-framework/`.

Avoid uncontrolled duplication between repository docs, wiki content, and
canonical Hydra knowledge. When a generated or curated page makes durable claims,
it must link back to verified code, project docs, task records,
or other source material.

## Wiki Surface

Human-readable wiki pages live under `project-wiki/`:

- `project-wiki/home.md` — human wiki hub.
- `project-wiki/hydra-framework/` — explains Hydra in this repository.
- `project-wiki/<project-name>/` — explains product systems, modules, features, and operations.

`.hydra-framework/` remains the AI/automation source for framework rules, tasks,
knowledge spaces, modules, adapters, scripts, and validation
evidence. Product teammates should understand product systems from
`project-wiki/<project-name>/` without browsing `.hydra-framework/`.

AI-generated wiki pages are allowed when they cite or link verified source
material. Do not copy live source-of-truth state into wiki prose when the owning
system should be linked instead.

Scaffold a new area with `hydra.py wiki scaffold`; validate links with
`hydra.py validate-wiki`.

### Purpose

The wiki should help readers onboard into Hydra without first reading
framework internals, share vocabulary across humans and AI agents, support
reviews, presentations, and adoption conversations, and navigate to canonical
files when exact rules, validation behavior, or source ownership matters.

The wiki explains and routes. Canonical rules, reusable procedures,
task records, validation behavior, provider adapter policy, and framework
evolution remain under `.hydra-framework/`.

### Audiences

| Audience | What They Need From The Wiki |
| --- | --- |
| New teammates | Orientation, vocabulary, boundaries, and a path into day-to-day use. |
| Daily AI-agent users | Operating guides that say what to read, run, update, and validate. |
| Framework maintainers | Source maps, boundaries, gap lists, and style rules for coherent updates. |
| Reviewers and adopters | Presentation-ready summaries, diagrams, adoption flow, and source links. |

### Citation Rules

Every durable claim should have either an explicit inline link or a nearby
`Sources` section that points to the canonical owner. Good source targets are:

- canonical Hydra files under `.hydra-framework/`
- code and tests that own behavior
- task records when the claim is about in-flight work
- validation output when the claim depends on a checked command
- external owners when Git does not own the state

Never cite `.hydra-framework.local/` from a shared wiki page. If private
source material supports a shared claim, inline the durable content needed by
the reader: origin, date checked, source owner, and the claim promoted. That
is the one case where naming a check's origin and date belongs in the prose,
because the reader has no source link to trace it themselves.

Citing a source means linking it, not narrating how it was checked. State the
fact directly, then attach a `Canonical source` link or `Sources` list.
Sentences that describe the checking process itself — a command and the date
it was run, a note that a search found nothing, a trailing "Source Notes"
section listing what an agent looked at while drafting — are not citations,
they are process log, and process log belongs in the task record's
continuation notes, not in reader-facing prose.

If the wiki and a canonical source disagree, update the canonical source
first, then update the wiki.

### Sync And Validation Expectations

`hydra.py validate-wiki` checks Markdown links and Obsidian-style `[[links]]`
against the wiki root; it does not validate backtick path citations. Run it
after any page move or rename. Agent authoring procedure for wiki pages lives
in `capabilities/skills/wiki-authoring/skill.md`.

## Developer Docs Surface

Developer-facing documentation aligned with canonical repository knowledge. If a
document is derived, it must state its canonical source.

## Obsidian Surface

Obsidian is not canonical. Its role is deliberately undecided — see
`core/unresolved-questions.md`. Candidate roles: generated view of canonical
knowledge, shared repository workspace, private developer workspace, or a mixed
surface with explicit boundaries. No vault structure is created until that role
is chosen. `.obsidian/workspace.json` is gitignored as machine-local state.

## Adding A Surface

Add a section here describing the contract, not an empty directory. A surface
directory is created only when it holds real contract metadata or sync
configuration.
