# Wiki Authoring Skill

## Capability

Draft or update one human-facing `project-wiki/` page as an AI agent. Give a
defined reader a useful answer before framework internals, while keeping the
wiki a traceable map over canonical Hydra sources rather than a second source
of truth.

## Procedure

1. State the page's one audience, reader goal, and page type before drafting.
   Select an orientation for a first explanation and route onward, a tutorial
   for guided learning, a how-to for an already-known task, an explanation for
   a mental model, or reference for exact lookup. Do not make one page perform
   all five jobs.
2. Read and re-verify the canonical sources that own each durable claim. For a
   new or changed page, declare those source files in its wiki sidecar before
   fingerprinting. Update the canonical owner first when a rule or behavior
   needs to change.
3. Draft for the reader's question: answer it in the opening, give a concrete
   situation or small example before abstraction, then introduce required Hydra
   terms with a plain-language translation. Defer advanced detail behind a
   clearly labelled route. Use Mermaid only when it explains a relationship,
   process, dependency, or state change more clearly than short prose; never
   add a decorative diagram. Use the page template below when it helps preserve
   that order.
4. Keep one reader job per page. Separate orientation, tutorial, how-to,
   explanation, and reference material by linking to the appropriate page
   instead of accumulating an internal index. Give the reader one clear next
   action.
5. Cite canonical sources near durable claims with an inline link or nearby
   `Sources` list. Never cite `.hydra-framework.local/`. Do not invent command
   output, metrics, screenshots, capabilities, or unverified behavior. If a
   fact is missing or conflicts with its owner, state the gap and its next
   action honestly.
6. Keep important ownership, safety, and uncertainty boundaries accurate, but
   lead with the useful answer unless the boundary changes the immediate
   decision. Write direct, concrete prose, not a drafting log. Do not add
   command-and-date narratives, a "Source Notes" section, em dashes, or
   self-referential AI language such as "as an AI", prompt commentary, or
   claims about how the page was generated.
7. Reader-test the draft as its declared audience: can they find the answer,
   understand every necessary term, recognize the concrete situation, and take
   the next action without reading linked reference first? Revise failures
   before validation.
8. Re-verify every declared source immediately before running
   `hydra.py wiki fingerprint --page <hydra-id>`. Then run
   `hydra.py wiki audit` after content changes and resolve findings honestly;
   fingerprinting does not replace review. Run `hydra.py validate-wiki` after
   page edits and `hydra.py validate` when `.hydra-framework/` changes.
9. Build or repair one page at a time unless an approved plan authorizes a
   larger set. Never hand-edit generated provider adapters; regenerate them
   with `hydra.py export-adapters` from this canonical skill.

## Output

Report pages changed; audience and reader goal; canonical sources used; known
gaps; and validation evidence.

## Boundaries

- Do not let the wiki become a second source of truth. Update its canonical source first when behavior changes.
- Do not cite `.hydra-framework.local/` from a shared wiki page. Inline the safe durable content instead.
- Do not claim a source was checked when it was not, or use fingerprinting to hide a stale finding.
- Do not expose AI drafting, prompting, or generation process in reader-facing prose.
- Do not rewrite several pages without an approved plan. Build or repair one page at a time.

## Page Template

Use this for a new or materially restructured page. Remove the drafting prompts
before publishing. The page's wiki sidecar, not this template, declares its
canonical sources.

```text
# <Reader Question>

Audience: <one reader with relevant starting knowledge>
Reader goal: <what the reader can decide, understand, or do>
Page type: <orientation | tutorial | how-to | explanation | reference>

## Answer
Give the answer or outcome in plain language and name the next action.

## A concrete situation
Show one realistic situation, small example, or familiar comparison.

## What to do or understand
Use only the structure that fits the selected page type. Define necessary
technical terms at first use, then use them consistently.

## Important boundary
State only a boundary that changes the reader's decision. Link to detail.

## Next action
Tell the reader exactly where to go or what to do next.

## Sources
Link canonical owners. Never cite private local files.
```

## Related

See `.hydra-framework/surfaces/README.md` (Wiki Surface) for the citation
rules and audience contract this procedure implements, and
`project-wiki/hydra-framework/reference/documentation-authoring.md` for
visual grammar and color/state conventions.
