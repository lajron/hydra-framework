# Documentation Authoring

Status: reference

Use this contract to make a Hydra wiki page understandable before it is
complete. A page should answer one reader's question, then route that reader to
the exact owner of durable detail. The wiki explains and navigates; canonical
Hydra files own rules, procedures, task state, validation behavior, and live
framework facts.

## Start with the reader

Before drafting, write down one audience and one reader goal. For example:

> A developer new to Hydra needs to understand where verified repository facts
> live, so they can choose where to record a finding.

Open with the answer the reader came for. Give a concrete situation or a small
example before introducing an abstraction. Translate a necessary framework term
when it first appears: "canonical source" means the version-controlled owner
that agents and people should trust. Then use that term consistently.

Write direct, familiar language. Technical precision matters, but framework
vocabulary is not an explanation by itself. Put important safety, ownership,
or uncertainty boundaries where they affect a decision; do not begin with a
defensive list of non-goals unless the boundary is the answer. Do not use em
dashes or self-referential AI language, prompt commentary, or claims about how
the page was generated.

## Choose one page job

| Page type | Reader need | Shape |
| --- | --- | --- |
| Orientation | "What is this and where do I begin?" | Short answer, situation, and route onward. |
| Tutorial | "Help me learn this safely." | A guided, successful path with context and expected evidence. |
| How-to | "Help me complete this known task." | Prerequisites, steps, evidence, and stop conditions. |
| Explanation | "Help me form a useful mental model." | Concrete situation, model, consequences, and links to detail. |
| Reference | "What is the exact contract or value?" | Scannable facts, definitions, limits, and canonical links. |

Do not combine a tutorial, operating procedure, concept explainer, and complete
reference into one long page. Link to the page that owns the other reader job.
Reveal advanced detail after the initial answer, using link labels that say what
the reader will find.

## Editorial rubric

A good Hydra article passes every applicable check.

| Check | Reader-first standard |
| --- | --- |
| Audience and goal | Names one audience and one reader goal during drafting; the published structure serves that job. |
| Opening | Answers the reader's question early and gives one clear next action. |
| Language | Uses plain language before framework terminology, translates every necessary technical term at first use, and contains no em dashes or AI drafting, prompt, or generation commentary. |
| Understanding | Gives a concrete situation, small example, or familiar comparison before abstraction. |
| Information architecture | Keeps orientation, tutorial, how-to, explanation, and reference material separate, with useful routes between them. |
| Boundaries | Preserves material safety, ownership, and uncertainty boundaries without leading with defensive caveats that do not change the immediate decision. |
| Evidence | Cites canonical Hydra owners near durable claims and never cites `.hydra-framework.local/`. |
| Honesty | Does not invent command output, metrics, screenshots, capabilities, or behavior. States known gaps and their next action. |
| Source ownership | Does not turn the wiki into a second source of truth. A changed rule belongs in its canonical owner first. |
| Review | A reader test confirms that the intended reader can find the answer, understand the necessary terms, recognize the situation, and take the next action. |

## Source declaration and freshness

Every new or changed managed page needs declared canonical source files in its
wiki sidecar at `.hydra-framework/surfaces/wiki/<wiki>.yaml`. Re-verify each
declared source immediately before running:

```bash
python3 .hydra-framework/scripts/hydra.py wiki fingerprint --page <hydra-id>
```

Fingerprinting records current source digests and the date checked. It does not
prove that the prose is understandable or that a source still supports the
claim. After content changes, run `hydra.py wiki audit`; repair stale, missing,
or unverifiable findings by updating the page, its source declaration, or both.
Do not erase a finding by fingerprinting a source that was not re-verified.

Then run `hydra.py validate-wiki`; run `hydra.py validate` whenever the change
also affects `.hydra-framework/`. The canonical workflow and reusable page
template are in `.hydra-framework/capabilities/skills/wiki-authoring/skill.md`.

## Visual grammar

Use a table, diagram, or worked example only when it makes a relationship easier
to understand than short prose. Visuals are explanations, not evidence: put
the durable fact in nearby text with a canonical link. Pair icons and color with
text labels; color alone must not carry state. Prefer a vertical Mermaid flow
for a process, a table for precise comparisons, and a curated tree for layout.

## Author output

Report pages changed, audience and reader goal, canonical sources used, known
gaps, and validation evidence. Do not hand-edit generated provider adapters;
regenerate them from the canonical skill.

## Routes

Use [Reference](/project-wiki/hydra-framework/reference/reference.md) for the
glossary and source map. Use [Operations](/project-wiki/hydra-framework/operations/operations.md)
for validation and troubleshooting.
