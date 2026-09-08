# Knowledge v3 Architecture

Status: selected and contract-frozen from the checked-in enterprise gates on
2026-09-07.

## Purpose

Knowledge v3 separates containment, cross-cutting meaning, composition,
portability, and distribution. One structure must not pretend to solve all
five concerns.

- The tree contains stable accountability and policy boundaries.
- Typed relations carry topical and cross-space meaning.
- Views compose references into reading order without copying domain facts.
- Namespaced bindings map portable logical resources to one repository.
- Scope controls distribution independently of physical registry layout.

The deterministic fixture and gate procedure live under
`validation/knowledge-v3/`. The fixture has 216 leaves, 36 accountability
areas, six spaces, cross-space dependencies, path bindings, and 21 ground-truth
workloads. Global indexed node retrieval passed the cold-start gate. Flat v2
keyword scoring, identity-only global scoring, and mandatory space-first
pruning were rejected by evidence.

## Canonical Layout

```text
repo/knowledge/
  spaces.yaml
  spaces/
    <space>/
      space.yaml
      [state.md]
      [overview.md]
      [units/*.md]
      [<node>/node.yaml]
  bindings/
    manifest.yaml
    <namespace>.yaml
  views/
    <view>.view.yaml
```

`spaces.yaml` is the reviewed closed list. Discovery never treats a directory
as a space merely because it exists. A listed space has one `space.yaml`.
Every descendant directory that participates in the tree has one `node.yaml`.
Units are legal directly under any routable space or node. Empty structural
levels are forbidden.

The default topology is three levels including the space. The hard ceiling is
four levels including the space. A depth violation explains the legal choices:
attach the fact to its containing node, promote a real stable boundary, or use a
typed relation or view for a cross-cutting concern.

## Schemas And Identity

The schema identifiers are:

- `hydra-framework.knowledge-spaces.v1`
- `hydra-framework.knowledge-node.v1`
- `hydra-framework.knowledge-view.v1`
- `hydra-framework.bindings-manifest.v1`
- `hydra-framework.bindings.v1`
- `hydra-framework.context-packet.v2`
- `hydra-framework.knowledge-v2-migration.v1`

Canonical identities are:

- `hydra://knowledge-space/<space>`
- `hydra://knowledge-node/<space>/<node>[/<node>]`
- `hydra://knowledge-unit/<space>[/<node>]/<unit>`
- `hydra://knowledge-view/<view>`
- `hydra://knowledge-route/<space>[/<node>]/<route>`
- `hydra://knowledge-view-route/<view>/<route>`

Path segments describe stable system boundaries, never current team names.
Changing ownership does not change an identity. A genuine boundary rename
preserves the opaque UUID `uid`, rewrites every reference atomically, and may
retain the old identity as an explicit alias. Duplicate ids, UIDs, aliases, or
fully qualified route ids fail validation.

`space.yaml`, `node.yaml`, units, and views are normal Hydra objects and carry
the object envelope required by their schema version. The `node` or `space`
logical path must agree with the directory and `hydra_id`. UIDs are never
generated during ordinary validation or routing.

## Node Contract

Every space and node declares:

- schema, logical path, `hydra_id`, `uid`, `schema_version`, `kind`, title,
  status, scope, relations, and provenance; spaces declare owners and descendants
  declare an owner override only when accountability changes
- `routable: true|false`
- optional role, state, overview, binding, keywords, defaults, and routes

Space kind is `knowledge-space`; descendant kind is `knowledge-node`. Space
names come from the closed list. Descendants use the same node schema.
`state` and `overview` are node-relative paths unless they are logical bindings.
Repository-root absolute paths are invalid in node metadata.

Only a routable node may own units or routes. A structural node with neither a
child nor owned content is invalid because it has no accountability purpose.

## Field Inheritance

Inheritance is resolved from space to selected descendant and carries a source
trace for every effective value.

| Field | Operator |
| --- | --- |
| `owners` | recursive map merge; nearest key wins |
| `defaults` | recursive map merge; nearest key wins |
| `defaults.validation_profile` | nearest scalar replaces |
| `defaults.certainty_floor` | nearest scalar replaces |
| `defaults.routing` | recursive map merge |
| `defaults.avoid_by_default` | ancestor-first ordered union, de-duplicated |
| `routes` | inherited by local name; override requires an exact `overrides` route id |
| `scope` | never inherited; every addressable object declares its distribution behavior |
| `hydra_id`, `uid`, `kind`, `schema_version`, `title`, `status` | never inherited |
| `node`, `role`, `routable`, `state`, `overview`, `binding`, `keywords` | never inherited |
| `relations`, `provenance`, unit `certainty`, unit `checked_on` | never inherited |

Sibling values never override one another. Selecting siblings produces two
independent effective policies. If a composed operation needs one value and the
siblings disagree, it fails with both sources unless the governing view declares
an allowed explicit resolution.

## Routes And Two-Phase Routing

Route names are local and their global identity is the owning node identity plus
the route name. Every route declares `use_when`. It may declare
`priority_units`, `requires`, `avoid_by_default`, `verify`, and `expand_when`.

`expand_when` is canonical only on routes:

```yaml
expand_when:
  - when_paths:
      - "@product/service/checkout-api/**/Migrations/**"
    read:
      - hydra://knowledge-unit/platform/data/ef-migration-policy
    why: governed schema change
```

Unit-level `expand_when` is invalid in v3. Unconditional dependency is
`requires`; conditional selection is route `expand_when`.

Routing has two explicit phases:

1. Provisional prompt routing resolves explicit selectors, then ranks nodes
   globally using the unified index. Implicit routing emits at most two compact
   node pointers. A low-margin boundary is ambiguity, not a lexical choice.
2. Path-informed rerouting resolves known paths through verified bindings.
   Bound nodes are selected outright and may replace provisional false matches.
   Matching route `expand_when` clauses are then evaluated against the same
   resolved path set.

Explicit node, view, route, and bound-path selections are not capped. Every
selection records one or more reasons: explicit, index score, bound path, view,
requires closure, relation expansion, or route expansion.

`--package` remains a deprecated CLI alias for `--node`; `--domain` remains a
deprecated alias for `--space`. They do not invoke v2 discovery. Context packet
v2 names selected `nodes`, active `views`, source-traced `effective_policy`, and
selection reasons while retaining deterministic priority/rank/path ordering,
required overage, omissions, freshness, and diagnostics.

## Global Graph And Conflict Semantics

All selected units participate in one global id map before dependency closure.
`requires` is transitive across nodes and spaces. An unresolved target or cycle
is a hard failure with the full edge path. Diamonds are legal and de-duplicated.

Knowledge relations are mappings with a closed type and target:

```yaml
relations:
  - type: relates-to
    target: hydra://knowledge-node/qa/shared-harness
```

The initial closed relation types are `relates-to`, `governs`, `implements`,
`tests`, `operates`, and `supersedes`. String relations remain legal for
non-Knowledge object families and normalize to untyped registry edges; v3
Knowledge objects must use mappings.

`supersedes` is directional. When a selected unit supersedes another selected
unit, the target is omitted as superseded and diagnostics name the edge. Two
selected siblings that supersede the same target are a hard conflict. No path,
lexical order, view order, or discovery order chooses a winner.

## Bindings

`bindings/manifest.yaml` lists fragments and changes only when fragments are
added or removed. Each fragment owns one namespace. A logical name is
`@<namespace>/<key>` and the qualified name is globally unique.

Each binding declares a repository-relative target, kind (`file`, `directory`,
or `glob`), and assertions. Supported assertions are filename, contained marker
files, bounded text patterns, and selected JSON, YAML, or XML identity values.
Targets may not escape the repository.

Resolution uses longest matching verified target for path-to-node lookup. Equal
specificity is an explicit ambiguity. Missing targets or failed assertions are
`stale`. Stale or unresolved bindings fail validation and cannot drive automatic
path routing, route expansion, command execution, or provenance freshness.
Explicit node selection remains available. `bindings verify --accept` records a
reviewed assertion fingerprint; accepting is a write operation and is never
implicit in validation.

## Views

A view is a YAML object with `constraints.reference_only: true`, owner,
reviewers, provenance, includes, optional dynamic bound-path inclusion, and
routes. It may contain no domain prose or unit payload.

Includes reference spaces, nodes, units, or other views. View-reference cycles
fail. Simultaneous view matches union includes. Ordering compiles into a partial
order graph; a cycle is a hard conflict. Overlapping predicates and high fan-in
are diagnostics, not hard failures until measured thresholds justify one.

A view may resolve a sibling supersession conflict only by naming the exact
winner and every conflicting candidate. A resolution that names a non-candidate,
omits a candidate, or contradicts another active view fails.

## Distribution

The only legal scopes are:

- `base-seed`: framework definition; copied by `init` and compared during base
  reconciliation
- `common-seed`: portable shared material; copied only by a named distribution
  profile and compared only within that profile
- `repo-local`: belongs to one adopted repository; never copied outward or
  proposed for base promotion

One policy function is used by init, adoption reporting, seed comparison,
reconciliation, and export. A copied object brings its owned non-object files
only when those files are beneath its node/view/binding root. Cross-scope
references are legal only when every selected distribution profile either
includes the target or declares it as a required host binding.

The deterministic two-profile fixture passes with zero repo-local leaks. The
real second-repository gate remains pending and must not be represented as
passed.

## Storage Boundary

Knowledge discovery and resolution depend on a `KnowledgeStore` interface, not
on `cognition/graph/registry.yaml` or a shard path. The private unified SQLite
`knowledge.db` holds the rebuildable search corpus plus typed Knowledge-object
locators and relation edges. Its freshness check compares a governed stat-only
inventory; an absent, corrupt, disabled, or stale store falls back to canonical
discovery. Rebuild is atomic. Registry sharding must preserve identities, edges,
packets, and routing results and is a separate workstream.

The interface exposes objects by id/UID, typed outgoing and incoming relations,
node/path lookup, and deterministic iteration. Canonical files remain the source
of truth. Registry and SQLite data are derived and rebuildable. A stale index may
reduce recall but cannot authorize an invalid reference or stale binding because
selected content is re-read from canonical files.

## Migration And Failure Behavior

`knowledge migrate-v2` is the only legacy reader. Normal discovery, validation,
routing, and writes become v3-only once the live repository migration lands.
There is no permanent dual-read path.

Dry-run produces a deterministic review manifest with proposed moves, preserved
UIDs, id/reference/route rewrites, unit-level to route-level `expand_when`
conversion, binding candidates, confidence, and unresolved decisions. Apply
requires the exact reviewed manifest digest, zero unresolved decisions, and a
clean Git worktree at the recorded checkpoint commit. Ambiguity is never guessed.

Apply is all-or-fail at the command level: preconditions and rewrites are planned
before the first write, writes use deterministic order, registry/index rebuild
runs last, and any failure exits nonzero with the last completed operation. The
rollback mechanism is the recorded Hydra checkpoint and Git commit, not a second
backup tree. Re-running dry-run or apply after success is idempotent.

The live migration is complete only when the old `knowledge-packages/` tree and
active package-routing v2/collision code are gone, all refs and routes resolve,
the registry is rebuilt, packet snapshots are deterministic, and the full
validation plus independent review pass.
