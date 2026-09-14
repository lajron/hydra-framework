# Phase 1 -- Current-State Reconstruction

Part of [`repository-intelligence-review`](../repository-intelligence-review.md).
Deliverable A of the task record
`.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-14-repository-intelligence-and-wiki-projections.md`.

Reconstructed 2026-09-14 on `main` at 7801b1d from implementation, tests,
command metadata, schemas and registries only. Per D6, no README, no wiki page,
and no knowledge unit was used as evidence of current behavior; where those
sources disagree with the code, section 7 records the disagreement.

Every claim below names the module, command, or test that establishes it.
Claims that could not be established are in section 8.

Reproduce the measurements with:

```bash
python3 .hydra-framework/scripts/hydra.py command-metadata --json
python3 .hydra-framework/scripts/hydra.py ref index
python3 .hydra-framework/scripts/hydra.py ref store rebuild
python3 .hydra-framework/scripts/hydra.py ref store status
python3 .hydra-framework/scripts/hydra.py ref check
python3 .hydra-framework/scripts/hydra.py knowledge stale
python3 .hydra-framework/scripts/hydra.py validate
python3 .hydra-framework/scripts/hydra.py selftest
```

## 0. Corrections to D1-D7

Six first-pass findings are wrong or incomplete. Each is corrected in place in
the task record's Confirmed Decisions; the evidence is here.

| Decision | First-pass claim | Measured | Where |
| --- | --- | --- | --- |
| D1, D2 | "The registry holds 44 objects" | **57** objects | `ref index` prints `Indexed 57 objects`; `ref check` prints `ok (57 objects)`; `grep -c '^  hydra://' .hydra-framework/cognition/graph/registry.yaml` = 57 |
| D1 | "`project-wiki/` is outside object discovery entirely" | True for *envelope* discovery; **false for sidecars and for provenance**. `objects/discovery.py:48` already resolves a sidecar `path:` beginning `project-wiki/`, and `ref check` already existence-checks a `project-wiki/` path cited as `provenance.sources` | §2.4, §7.1 |
| Phase-1 prompt, D2 | "the 5 families in `identity/object_families.py`" | **6** families. Telemetry is registered and has a context provider; it simply has no member object today | §2.1 |
| D2 | Relation type "is discarded before it reaches any query" -- attributed to the store | The type is discarded **one layer earlier**, in `objects/envelopes.py:129`, before the registry export exists. The store never sees it | §3.3 |
| D2, D3 | "`source-map.md`, roughly 20 claim rows. All 16 cited paths resolve; nothing checks that" | 19 rows, **41** distinct non-wiki paths, all resolving, and `validate-wiki` **does** check every one of them -- they are root-relative Markdown links, not backtick citations (`wiki/links.py:44`) | §5.1, §7.2 |
| D2 | "Knowledge units carry `provenance.sources` + `source_digests` + `checked_on` + `verify`" (implying date-based staleness) | All 27 sources across all 7 units are digested, so the date rule at `knowledge/freshness.py:311` is **never exercised** by this corpus. `knowledge stale`'s own message says "committed after checked_on", which is wrong for 100% of its current output | §4.5, §7.3 |

D3's other two measurements reproduce exactly: 5 of 70 registered commands are
absent from `command-surface.md`, and `knowledge stale` reports 2 of 7 units
stale. D4, D5 and D7 are unaffected by anything in this reconstruction.

## 1. Capability inventory

### 1.1 What "70 commands" actually counts

`command-metadata --json` emits 70 entries. That is **not** the CLI's command
count. `cli/command_metadata.py:340` builds its parser from `COMMAND_MODULES`
alone, with no `extra` callback, so three commands registered directly in
`cli/dispatch.py:179-184` -- `validate`, `doctor`, `command-metadata` -- and one
registered by the shim at `scripts/hydra.py:48` -- `selftest` -- are invisible to
it.

**The CLI dispatches 74 commands. `command-metadata` reports 70 of them.**
Verify: `hydra.py validate` runs and is absent from the JSON.

`main` itself uses the *full* parser for `ctx.command_ids`
(`cli/dispatch.py:195`), so the engine's internal command list and its published
one differ. Nothing tests that difference.

43 of the 70 carry hand-authored safety metadata (`side_effects`,
`confirmation`, `privacy`) from `SIDE_EFFECT_COMMANDS`
(`cli/command_metadata.py:35`); the other 27 are mechanical-only by design
(`cli/command_metadata.py:5-8`). `unit/cli/test_command_metadata.py:78` asserts
every overlay key is a live registered command -- but nothing asserts the
converse, that every side-effecting command has an entry.

### 1.2 Inventory by subsystem

Owning module is the `COMMAND_MODULES` member whose `register()` creates the
subparser (`cli/dispatch.py:43`, iterated by `cli/parser.py:28`). "Tests" names
the test module that exercises the command's own `command_*` function.

#### Object model and query store -- `commands/references.py`, `commands/store.py`, `commands/object_moves.py`, `commands/schema.py`

| Command | Does | Tests |
| --- | --- | --- |
| `ref resolve <id>` | Prints one object's envelope, aliases, relations, provenance sources. Store-backed when fresh, full-tree scan otherwise; prints `source=sqlite`/`source=scan` on stderr (`commands/references.py:53-92`) | `unit/commands/test_references.py`, golden `object-ref-resolve*.json` |
| `ref check` | `validate_object_references` then registry freshness, sharing one scan (`commands/references.py:151`) | `unit/commands/test_references.py`, golden `object-ref-check.json` |
| `ref index` | Rewrites `cognition/graph/registry.yaml` after a clean reference check (`commands/references.py:172`) | `unit/commands/test_references.py`, `unit/commands/test_knowledge_migration.py`, golden `object-ref-index.json` |
| `ref rdeps <id>` | One-hop reverse over the `relations` table. **Hard-requires** a fresh store; exits 1 otherwise (`commands/references.py:95-102`) | `unit/commands/test_references.py`. **No contract golden** |
| `ref impact <id> [--depth]` | Transitive *outbound* reachability, default depth 5 (`commands/references.py:122`, `objects/store_queries.py:115`). Hard-requires the store | `unit/commands/test_references.py`. **No contract golden** |
| `ref store status` | Freshness, schema, build date, and a row count per table (`commands/store.py:27`) | `unit/commands/test_store.py`. No golden |
| `ref store rebuild [--if-exists] [--verify-digests]` | Full atomic rebuild, or in-place digest repair for a store restored across machines (`commands/store.py:63`) | `unit/commands/test_store.py`. No golden |
| `move-object <src> <dst> [--dry-run]` | Relocates a canonical object, rewrites a sidecar `path:`, refuses on missing uid, existing destination, suffix change, tier change, or broken references, and reverts a half-applied move (`commands/object_moves.py:48-140`) | `unit/commands/test_object_moves.py`, 8 `object-move-object-*` goldens |
| `schema upgrade` | Applies `objects/schema_upgrades.py`'s named idempotent envelope migrations | `unit/commands/test_schema.py`, `object-schema-upgrade*.json` |
| `explain-path <path> [--json]` | Derives what owns any repository path: tier, object (if any), reverse citations by relation, citers by provenance source, directory owner, provider-surface status. Degrades to a scan; never requires the store (`commands/explain_path.py:18-20`) | `unit/commands/test_explain_path.py`, 4 `explain-path-*` goldens |

#### Knowledge -- `commands/knowledge.py`, `commands/knowledge_docs.py`, `commands/knowledge_fingerprint.py`, `commands/knowledge_migration.py`, `commands/knowledge_bindings.py`, `commands/context.py`, `cli/route_prompt.py`

| Command | Does | Tests |
| --- | --- | --- |
| `knowledge stale` | Every knowledge unit under every discovered node whose `provenance.sources` are stale (`commands/knowledge.py:185`, `knowledge/candidates.py:92`) | `unit/commands/test_knowledge.py`. **No contract golden** |
| `knowledge fingerprint --unit <id>` | Rewrites one unit's `provenance.source_digests` block from current file digests (`commands/knowledge_fingerprint.py:96`) | `unit/commands/test_knowledge_fingerprint.py`, `unit/commands/test_knowledge.py`. No golden |
| `knowledge migrate-v2 [--output] [--apply]` | Review-gated v2→v3 knowledge migration | `unit/commands/test_knowledge_migration.py`. No golden |
| `knowledge-search <text>` | Ranked, cited, budgeted lexical snippets from the private index | `unit/commands/test_knowledge.py` |
| `delegation-brief <text>` | Shapes search results into a subagent read-first brief with stop rules | `unit/commands/test_knowledge.py` |
| `hook-reindex-knowledge [--if-exists]` | Refreshes the private FTS5/substring index under `.hydra-framework.local/index/` | `unit/commands/test_knowledge.py` |
| `measure-context` | Token estimate over prompt and adapter surfaces; `--fail-over` exits 2 | `unit/commands/test_knowledge.py`, `knowledge-measure-context*.json` |
| `validate-package-docs` | Knowledge v3 node document gate, §5.2 | `unit/commands/test_knowledge.py`, 5 `knowledge-validate-package-docs*.json` |
| `compile-context` | Bounded Knowledge v3 context packet across the six family providers | `unit/commands/test_context.py`, 3 `knowledge-compile-context*.json` |
| `route-prompt [--prompt]` | Emits node pointers for a prompt; records private hit/miss counters | `unit/cli/test_route_prompt.py`, 2 `knowledge-route-prompt*.json` |
| `bindings list [--name]` | Logical `@ns/key` bindings with verified state (`knowledge/bindings.py:18-21`) | `unit/commands/test_knowledge_bindings.py`. No golden |
| `bindings verify [--name] [--accept]` | Verifies binding assertions against targets | `unit/commands/test_knowledge_bindings.py`. No golden |

#### Validation and repository health -- `commands/validation.py` (via `cli/dispatch.py`), `commands/wiki.py`, `commands/hooks.py`

| Command | Does | Tests |
| --- | --- | --- |
| `validate` | Runs the 19 registered validators in locked order, then prints advisory notes after the verdict (`commands/validation.py:24`, `checks/validator_registry.py:94-106`) | `unit/commands/test_validation.py`, `unit/checks/test_validator_registry.py`, `core-validate.json`, `validation-validate-every-failure.json` |
| `doctor` | Required paths, task counts, owner, private tier, cache lifecycle, provider surfaces, lineage -- then delegates the verdict to `validate` (`commands/validation.py:39-120`) | `core-doctor.json`, `validation-doctor-missing-required-paths.json` |
| `validate-wiki [--path]` | Markdown links, traversal links, Obsidian links, §5.1 | `unit/commands/test_wiki.py`, 4 `wiki-validate-wiki-*` goldens, `unit/wiki/test_links.py` |
| `wiki scaffold <project>` | Writes `home.md` and `sources.md` under `project-wiki/<slug>/` | `unit/commands/test_wiki.py`, 3 `wiki-scaffold*` goldens |
| `hook-post-edit [--render]` | Package-local gates for edited knowledge files; optionally renders `diagrams/*.dot` | `unit/commands/test_hooks.py`, 3 `agent-hooks-hook-post-edit*` goldens |
| `selftest [--verbose]` | Discovers and runs the 207 bundled test modules (`scripts/hydra.py:40-46`) | Not itself tested |

#### Work and task records -- `commands/work.py`

`board`, `note`, `migrate-state`, `task start`, `task checkpoint`, `task handoff`,
`task complete`. All in `unit/commands/test_work.py`; 17 `work-*` goldens.
`board` reads the store's `tasks` table when fresh and falls back to a scan
(`work/task_store.py:113-140`).

#### Providers and capabilities -- `commands/providers.py`, `commands/capability.py`, `commands/subagents.py`

`export-adapters`, `profile list|show|select`, `reclaim`, `capability
scaffold-skill`, `capability scaffold-agent`, `hook-subagent-start`. Tests:
`unit/commands/test_providers.py`, `unit/commands/test_capability.py`,
`unit/commands/test_subagents.py`; goldens `providers-*`, `capability-*`.

#### Agent hooks and output reduction -- `commands/agent_hooks.py`

`summarize-log`, `retry-guard`, `hook-command-output`,
`hook-codex-command-output`, `hook-retry-guard`, `hook-codex-retry-guard`,
`hook-token pre-context`, `hook-token command-result`. All in
`unit/commands/test_agent_hooks.py`; 7 `agent-hooks-*` goldens. Every one writes
only under `.hydra-framework.local/`.

#### Installation, seed and evolution -- `commands/installation.py`, `commands/private_tier.py`, `commands/seed.py`

`adopt`, `init`, `install-hooks`, `init-local`, `diff-base`, `evolution record`.
Tests: `unit/commands/test_installation.py`, `unit/commands/test_private_tier.py`,
`unit/commands/test_seed.py`, `unit/seed/test_envelope_drift.py`; goldens
`installation-*`, `seed-*`.

#### Intake, integration and takeover -- `commands/intake.py`, `commands/integrate.py`, `commands/takeover.py`

`migration inventory|ledger|request-stage|propose|validate-batch|request-close|decide|status`,
`integrate scan|identify|map|status`, `takeover scan`. Tests:
`unit/commands/test_intake.py`, `unit/commands/test_integrate.py`,
`unit/commands/test_takeover.py`; goldens `intake-*`, `integrate-*`, `takeover-*`.

#### Telemetry -- `commands/telemetry.py`

`telemetry gate`, `telemetry report`, `telemetry evidence create`. Tests:
`unit/commands/test_telemetry.py`. No goldens.

### 1.3 Commands with no direct command-function test

Six of the 70 have no test that calls their own `command_*` function:

| Command | Underlying logic tested? |
| --- | --- |
| `migration status` | No -- `approval.batch_status` has no test hit |
| `migration validate-batch` | Indirectly -- `approval.record_validation` in `unit/intake/test_approval.py`, `test_approval_actions.py`, `contract/goldens/test_intake.py` |
| `migration request-close` | Indirectly -- `approval.request_closure`, same three modules |
| `integrate status` | No -- `integration_status` has no test hit |
| `telemetry report` | Indirectly -- `reporting.build_report` in `unit/telemetry/test_reporting.py` |
| `telemetry evidence create` | Partially -- `run_gate` and `package_dir_name` are tested; `mint_evidence_package` has **no** test hit |

`migration status` and `integrate status` are the two commands with no test
coverage at any layer.

## 2. Object model as built

### 2.1 Six families, not five

`identity/object_families.py:89-143` registers six `ObjectFamily` entries:

| Family | `id_prefixes` | `kinds` | Line | Objects today |
| --- | --- | --- | --- | --- |
| Knowledge | `knowledge-package`, `knowledge-slice`, `knowledge-template`, `knowledge-unit`, `knowledge-space`, `knowledge-node`, `knowledge-view`, `knowledge-route` | the same minus `knowledge-route` | 91 | 29 |
| Capability | `capability` | `capability`, `agent`, `skill`, `workflow`, `tool-capability-registry`, `capability-profile-policy` | 102 | 23 |
| Work | `work`, `migration-ledger` | `work`, `migration-ledger` | 111 | 1 |
| Source | `source`, `integration-ledger`, `promotion-record` | `source`, `source-integration`, `integration-ledger`, `promotion-record` | 116 | 1 |
| Runtime/Engine | `engine-module` | `engine-module` | 128 | 3 |
| **Telemetry** | `telemetry-evidence` | `telemetry-evidence` | 139 | **0** |

The Telemetry family is real, not aspirational: `knowledge/context_providers.py:28`
lists it in `SEARCH_FAMILIES` and `:274-277` gives it a context provider
alongside the other five. It has no member object because no bounded telemetry
evidence package exists in `repo/telemetry/packages/` today.

`family_for` resolves prefix-first across the whole registry, then `kind`, then
returns the literal `"Unknown"` (`identity/object_families.py:146-163`).
`unregistered_family_tokens` (`:166`) is what makes an unregistered token a
`ref check` finding rather than a silent `family: Unknown` export
(`objects/references.py:86-93`). `unit/identity/test_object_families.py:42`
asserts no token is claimed by two families -- the invariant `family_for`'s
two-pass resolution depends on.

Counts by family from the export:
`grep '^    family:' .hydra-framework/cognition/graph/registry.yaml | sort | uniq -c`.

### 2.2 Three handlers and their roots

`objects/object_handlers.py:97-124`:

| Handler | Suffixes | Envelope location | Roots | Exclusions | Line |
| --- | --- | --- | --- | --- | --- |
| Markdown | `.md` | YAML frontmatter; title falls back to the first `# ` heading | whole `.hydra-framework/` tree | any path component `.git`, `node_modules`, `dist`, `build`, `.hydra-framework.local` | 98 |
| YAML | `.yaml`, `.yml` | top-level document keys; `title`\|`name`, `hydra_object_kind`\|`kind` | whole tree | the top-level `cognition/` directory (derived state) | 107 |
| Python | `.py` | module docstring frontmatter | **`engine/src` only** | `__pycache__` | 115 |

**Scanned:** everything under `.hydra-framework/` matching a handler suffix,
minus the exclusions above.

**Not scanned:** `.hydra-framework/cognition/` YAML (the export itself);
`.hydra-framework.local/` (the private tier); `.hydra-framework/scripts/hydra.py`
(deliberately, as a compatibility surface -- `objects/object_handlers.py:38`);
`.hydra-framework/engine/tests/` (deliberately: fixtures author example
`hydra://` ids that `ref check` would demand resolve -- `:40-43`); **every file
outside `.hydra-framework/`**, including all 40 `project-wiki/*.md` pages,
`AI_SYSTEM.md`, `README.md`, and the host repository's own source tree.

`object_document_paths(hydra_root)` (`objects/object_handlers.py:145`) takes the
`.hydra-framework/` directory and `rglob`s under it. That single parameter is the
whole of D1's gap. Nothing else in the object model is root-scoped.

A file in a claimed form becomes an object only if it declares a `hydra_id`:
`objects/envelopes.py:112-114` returns `(None, None)` otherwise. The Python
handler turned 3 of the ~200 engine modules into objects, not all of them.

### 2.3 The envelope contract

`objects/envelopes.py:103-166` builds every object the same way regardless of
handler. The record is:

`id`, `uid`, `aliases`, `kind`, `family`, `title`, `status`, `scope`,
`schema_version`, `tier`, `owners`, `relations`, `provenance_sources`, `path`,
`envelope_path`, `digest`, `missing_envelope_fields`, `unregistered_family_tokens`.

Rules the code enforces:

- **No defaults.** An absent field stays absent; it is never filled with
  `"active"`, `"unspecified"`, or a kind read back out of the `hydra_id`
  (`objects/envelopes.py:132-138`).
- **Mandatory, must carry a value:** `kind`, `title`, `status`, `scope`, `owners`
  (`identity/schema_versions.py:35`). `owners` is waived for `knowledge-node`
  objects, which inherit it up the accountability chain
  (`objects/envelopes.py:90-95`).
- **Mandatory, may be empty:** `relations`, `provenance.sources`
  (`identity/schema_versions.py:42`). Absence is a finding whose message
  explicitly says an empty list is the right answer, so an agent does not invent
  filler (`objects/references.py:69-78`).
- **Tier** is derived from location, never declared: `private` under
  `.hydra-framework.local/`, `personal` under `tasks/personal/`, `shared` under
  `.hydra-framework/`, `external` anywhere else (`objects/envelopes.py:27-34`).
  A `project-wiki/` file would be `external`.
- **Digest** is `normalized_digest(path)` over the object's own file, not its
  envelope file (`objects/envelopes.py:156`).

### 2.4 The sidecar mechanism

`objects/discovery.py:65-111`. A YAML file whose top-level
`schema: hydra-framework.object-sidecar.v1` (`:19`) declares objects for files
that cannot carry an envelope. Each `objects.<name>` entry supplies the full
envelope plus a `path`.

Path resolution (`objects/discovery.py:44-50`):

1. absolute paths are used as-is;
2. a path beginning `.hydra-framework/`, `.hydra-framework.local/`, **or
   `project-wiki/`** resolves from the repository root;
3. anything else resolves relative to the sidecar file.

**`project-wiki/` is already a recognized sidecar root.** This is a correction
to D1: the prefix is hardcoded at `objects/discovery.py:48`, and nothing in
`build_hydra_object` rejects an `external`-tier path. What is missing is a
sidecar file naming wiki pages, not the mechanism to resolve one.

Two constraints a wiki sidecar would hit, both real:

- `extract_sidecar_objects` is only reached for files already returned by
  `object_metadata_paths` (`objects/discovery.py:117-126`), so the sidecar
  itself must live under `.hydra-framework/`.
- `ref check` requires every `hydra://` reference in a **scanned** file to
  resolve (`objects/references.py:121-136`). A sidecar-registered wiki page is
  not itself scanned for references -- only the sidecar is -- so registering wiki
  pages this way does **not** put wiki prose under the reference-resolution
  requirement. That is the opposite of what D7's Phase 3 question 1 assumes
  about blast radius.

The repository's one sidecar is `.hydra-framework/repo/object-sidecars.yaml`,
holding 13 `knowledge-template` objects, all under
`repo/knowledge/templates/space/` -- including `space.yaml.template` and
`scripts/check.sh`, two forms no handler claims.

### 2.5 `schema_version` 3

`identity/schema_versions.py:12-42`. `CURRENT_SCHEMA_VERSION = 3` (`:13`).
Requirements are gated on *the object's own* declared version, never on the
current one, so a downstream copy that has not run `schema upgrade` cannot fail
for someone else's lag:

- `UID_REQUIRED_FROM_SCHEMA_VERSION = 2` (`:20`)
- `ENVELOPE_REQUIRED_FROM_SCHEMA_VERSION = 3` (`:29`)
- version `0` means "written before the field existed", not an error (`:12`)

`ref check` prints a pending-upgrade count when any object is below 3
(`commands/references.py:164-168`). All 57 objects are at 3 today: `ref check`
prints `ok (57 objects)` with no pending clause.

## 3. Query store as built

Rebuilt with `ref store rebuild`; Git-ignored and absent on a fresh clone.
Measured state on 2026-09-14 (`ref store status`):

```
status: fresh   schema: hydra-framework.object-store.v1   built: 2026-09-14
export digest: agrees with the export      size: 286720 bytes
documents: 364   refs: 97   objects: 57   aliases: 1
relations: 30    provenance: 50            tasks: 1
```

### 3.1 The eight tables

`objects/store_schema.py:16-41`.

| Table | Columns | Derived from | Freshness model | Read by |
| --- | --- | --- | --- | --- |
| `documents` | `path, mtime_ns, size, digest, handler, envelope_json, scanned_at` | per-file scan | `(mtime_ns, size)`, or content digest under `--verify-digests` | nothing, except `repair_stale_documents`'s own staleness check |
| `refs` | `src_path, dst_ref, line` | `hydra_refs_by_line` per file | same as `documents` | **nothing** |
| `objects` | `hydra_id, uid, path, digest, family, kind, status, tier, scope, schema_version, title, envelope_path` | the validated export | wholesale rebuild, keyed to export digest | `resolve`, `by_uid`, `by_path`, `by_digest` |
| `aliases` | `alias, hydra_id` | export | same | `_canonical_id`, `resolve` |
| `relations` | `src_id, dst_id` | export | same | `citers_of`, `impact`, `resolve` |
| `provenance` | `hydra_id, source_path` | export | same | `citers_of_source_path`, `resolve` |
| `tasks` | `path, owner, name, status, updated, goal, blocked_on, mtime_ns, size` | personal task records | `(mtime_ns, size)` | `board_rows_from_store` |
| `meta` | `key, value` | build | n/a | schema and export-digest checks |

**`refs` is written and indexed but never read.** `store_schema.py:23` creates
`idx_refs_dst_ref`; `store_build.py:108,186` insert rows; no query function in
`objects/store_queries.py` selects from it, and no engine module outside
`store_build.py` names `dst_ref` (only `unit/objects/test_store_build.py:115,185`
do). 97 rows of citation-site data with no consumer. `commands/references.py:96-98`
describes `ref rdeps` as serving "the search `refs`'s index exists to avoid",
but `command_ref_rdeps` queries `relations`, not `refs`.

`documents.envelope_json` is likewise written and never read back.

### 3.2 What `ref rdeps` and `ref impact` can and cannot answer

Both hard-require a fresh store and report rather than degrade
(`commands/references.py:96-102`, `:123-129`). `open_fresh_store`
(`objects/store_queries.py:27-47`) returns `None` -- and therefore both commands
fail -- when the store is missing, schema-stale, export-digest-mismatched, or when
`HYDRA_QUERY_STORE=off` (`ports/sqlite_db.py:26-32`).

**Can answer:**

- `ref rdeps <id>`: every object whose declared `relations` name `<id>`, one hop,
  alias-resolved (`objects/store_queries.py:95-102`). Measured: `ref rdeps
  hydra://knowledge-space/hydra-framework` returns 14 citers.
- `ref impact <id> [--depth N]`: every object transitively reachable by
  **outbound** relations within N hops, default 5, cycle-guarded by a
  path-membership test in the recursive CTE (`objects/store_queries.py:115-136`).

**Cannot answer:**

- *What breaks if I change X.* `impact` walks outbound edges -- the direction
  `rdeps` reverses. There is no transitive reverse walk. `ref impact
  hydra://engine-module/validator-registry` returns the two registries it cites,
  not the things that depend on it.
- *What cites this file, and where.* That is the `refs` table, which has no
  query (§3.1). `explain-path` answers a narrower version -- which objects name a
  path as `provenance.sources` -- via `citers_of_source_path`
  (`objects/store_queries.py:105-112`).
- *Anything about a non-object.* `citers_of` and `impact` both return `[]`
  immediately when `_canonical_id` misses (`:99-101`, `:119-121`). A wiki page is
  not an object, so both return empty rather than an error.
- *Anything with an edge type.* §3.3.
- *Anything about provenance freshness.* The `provenance` table stores
  `(hydra_id, source_path)` only. No digest, no date, no declared-order column --
  `commands/references.py:28-31` records that the store cannot preserve declared
  order, which is why both `ref resolve` paths sort.

### 3.3 Where the relation type is actually lost

`knowledge/contracts.py:6` defines six types:

```python
RELATION_TYPES = ("relates-to", "governs", "implements", "tests", "operates", "supersedes")
```

They are enforced on Knowledge v3 nodes (`knowledge/nodes.py:341`) and on
knowledge units (`knowledge/checks.py:72-74`), and `knowledge/checks.py:69-71`
requires v3 unit relations to be **typed mappings**, not bare strings.

The loss happens at `objects/envelopes.py:125-130`:

```python
raw_relations = data.get("relations")
relation_values = raw_relations if isinstance(raw_relations, list) else yaml_list(raw_relations)
relations: list[str] = []
for value in relation_values:
    relation_text = yaml_str(value.get("target")) if isinstance(value, dict) else str(value)
    relations.extend(hydra_refs_in_text(envelope_path, relation_text))
```

A typed mapping is reduced to its `target` string here -- **before** the export is
written, before the store exists. The registry itself carries an untyped list
(`cognition/graph/registry.yaml:273-274` shows
`relations:\n      - hydra://capability/skill/reflection-absorb`), and
`store_build.py:65-66` inserts `(hydra_id, relation)` from that already-flattened
list. Widening `relations(src_id, dst_id)` alone would change nothing: there
would be no type to put in the column.

Two authoring shapes coexist, and the registry cannot tell them apart:

- typed mappings (`- type: … / target: …`), used by Knowledge v3 nodes and units;
- bare `hydra://` strings, used by capability `metadata.yaml` files and by the
  three engine-module docstring envelopes (`identity/object_families.py:11-12`).

**What is lost today is nothing.** All 23 typed relations authored anywhere in
`.hydra-framework/` are `relates-to`. `governs`, `implements`, `tests`,
`operates` and `supersedes` are authored **zero** times, in source and in tests
alike:

```bash
for t in relates-to governs implements tests operates supersedes; do
  echo -n "$t: "; grep -rn "type: \"\?$t" --include=*.md --include=*.yaml .hydra-framework/ | wc -l
done
# relates-to: 23, everything else: 0
```

The type column would carry one constant value. That is the accurate statement
of D2's "one structural gap": the vocabulary exists and is validated, the
authoring discipline that would make it informative does not, and the flattening
point is one layer above where D2 placed it.

## 4. Knowledge model as built

### 4.1 Spaces, nodes, slices, units

`knowledge/nodes.py:15-16` defines two schemas:
`hydra-framework.knowledge-spaces.v1` for `repo/knowledge/spaces.yaml`, and
`hydra-framework.knowledge-node.v1` for every node document.

- **Space**: a `space.yaml` at `repo/knowledge/spaces/<name>/`, listed in
  `spaces.yaml`. One exists: `hydra-framework`
  (`repo/knowledge/spaces.yaml`, 5 lines). It is `role: accountability-root`,
  `routable: true`, and declares 5 routes.
- **Node**: a `space.yaml` or any `node.yaml` beneath it
  (`knowledge/nodes.py:172-182`). Depth is bounded by `default_depth: 3` /
  `max_depth: 4` (`knowledge/contracts.py:3-4`). This repository has **one node
  and no child nodes** -- the recursive model is built and exercised only by test
  fixtures.
- **Slice**: a Markdown file beside the node carrying `kind: knowledge-slice`
  (`repo/knowledge/spaces/hydra-framework/state.md:5`). 8 exist: `overview`,
  `state`, `glossary`, `sources`, `problems`, `definition-of-done`,
  `architecture-graph`, `provider-export-example`. **`knowledge-slice` has no
  engine behavior**: it appears in `identity/object_families.py:93` and nowhere
  else in `hydra_engine/` except a comment. A slice is an object and a file the
  node points at; it is not a thing the engine dispatches on.
- **Unit**: a Markdown file under a node's `units/` with
  `kind: knowledge-unit` (`knowledge/units.py:62-74`). 7 exist. A second,
  package-local `unit_kind` -- `answer | rule | map | divergence | status`
  (`knowledge/units.py:27`) -- drives the validation profile and is deliberately
  kept separate from the object-family `kind` (`knowledge/units.py:1-17`).

Inheritance (`knowledge/nodes.py:238-270`) merges `owners`, `defaults`,
`avoid_by_default` and `routes` down the parent chain, recording a per-key trace
of which ancestor supplied each value.

### 4.2 Bindings

`knowledge/bindings.py:18-21`. A manifest at `repo/knowledge/bindings/manifest.yaml`
with `schema: hydra-framework.bindings-manifest.v1`, fragments declaring
`@namespace/key` logical names (`LOGICAL_RE`, `:21`) resolving to a `file`,
`directory`, or `glob` target with assertions and an accepted fingerprint.

**Declared today: none.** `manifest.yaml` is two lines, `fragments: []`, and
`bindings list` prints `Hydra bindings: none declared`. Route `expand_when`
patterns are required to be logical bindings (`knowledge/checks.py:84-90`), and
no route in this repository declares an `expand_when`, so the requirement is
currently vacuous.

### 4.3 Views

`knowledge/views.py:15` defines `hydra-framework.knowledge-view.v1`; views live
at `repo/knowledge/views/*.view.yaml` (`:61-62`, `:196`). **The directory does
not exist.** `discover_views` returns `[]`, `validate_views` finds nothing, and
`view_routing.select_and_compose_views` composes an empty set. Views are built,
tested (`unit/knowledge/test_views.py`, `test_view_routing.py`), and unused.

### 4.4 Routing

`knowledge/routing.py:25-28` sets `MIN_ROUTE_MATCH_SCORE = 2` and
`MAX_ROUTED_NODES = 2` over a stopword-filtered term match against node
`keywords` and route `use_when`. `route-prompt` emits node pointers; the
UserPromptSubmit hook in this session routed to
`spaces/hydra-framework/state.md` then `overview.md`, which is the mechanism
working end to end.

`compile-context` runs six family providers
(`knowledge/context_providers.py:274-277`): one Knowledge provider that walks
nodes, routes and units, plus one lexical-search collector per remaining family
(`:28`). `--include-family`/`--exclude-family` filter them (`:293`).

### 4.5 The provenance / `source_digests` / `checked_on` / `verify` contract

The four fields are all frontmatter on a knowledge unit. `knowledge/units.py:30-48`
is the only dataclass carrying `source_digests` and `checked_on`.

`knowledge/freshness.py:287-314` is the whole staleness rule:

```python
for raw in sources:
    path = resolve_source_path(raw, paths)
    if raw in digest_by_source:                                  # 305
        if path.exists() and path.is_file() and normalized_digest(path) != digest_by_source[raw]:
            stale.append(raw)
        continue                                                 # 308
    if not path.exists():
        continue
    commit_date = git_port.last_commit_iso(paths.root, raw)[:10] # 311
    if commit_date and commit_date > checked_on:
        stale.append(raw)
```

Two rules, and a digested source **never** reaches the date rule (`:308`).

`verify` is a list of commands on the unit; nothing in `hydra_engine/` executes
it. It is instruction to a human or agent, not a mechanism.

`knowledge fingerprint --unit <id>` (`commands/knowledge_fingerprint.py:96-127`)
is what writes `source_digests`: it re-hashes every listed source and rewrites
the block in place, refusing if any source is not exactly one existing file.

### 4.6 What `knowledge stale` covers, and what it structurally cannot

`commands/knowledge.py:185` calls `knowledge/candidates.py:92`, which iterates
`discover_knowledge_nodes` → `discover_node_unit_paths` → `read_unit`. Measured
output on 2026-09-14:

```
Checked units: 7
- .../units/add-module.md: providers/capabilities.py, providers/adapter_plan.py
- .../units/build-status.md: cli/command_metadata.py, knowledge/context_providers.py
```

**Covers:** `provenance.sources` on Markdown files under a discovered node's
`units/` directory whose `kind` is `knowledge-unit`. Seven files. All 27 of their
sources are digested, so all detection today is by content digest.

**Structurally cannot cover:**

- **Anything that is not a unit.** `read_unit` returns `None` for any other
  `kind` (`knowledge/units.py:74`). 22 of the 57 registered objects declare at
  least one `provenance.sources` entry; only the 7 units are checked. The other
  15 -- 4 knowledge slices, 6 capabilities, the 3 engine modules, and 2 ledgers --
  declare sources that nothing compares against anything.
- **Anything outside a node's `units/`.** `discover_unit_paths` globs
  `units/*.md` under a node root only (`knowledge/units.py:55-59`).
- **A source that is a directory.** The digest branch requires `path.is_file()`
  (`freshness.py:306`); the date branch calls `git log` on the path. The
  `overview` slice cites `.hydra-framework/engine/src/hydra_engine/` and
  `.hydra-framework/engine/tests/`, both directories -- unchecked twice over,
  once for not being a unit and once for not being a file.
- **A source outside Git.** The date branch depends on `git log`; a path with no
  commit yields `""` and is silently not stale (`freshness.py:311-313`).
- **Any wiki page.** No `project-wiki/` file is a unit, and no unit cites one as
  a source. `hydra://capability/skill/wiki-authoring` cites
  `project-wiki/hydra-framework/reference/documentation-authoring.md` as
  provenance, but a capability is not a unit, so `knowledge stale` never looks.
- **Dependency in the other direction.** The model records *what a unit reads*.
  Nothing records *what reads a unit*, or what reads a wiki page.

Staleness is advisory by construction and cannot become a `validate` failure.
`knowledge/package_checks.py:148-156` states the reason outright: every `Finding`
makes `validate` exit nonzero, there is no warning tier, and an intentionally
stale unit must not be a hard failure. `validate_unit_source_digests`
(`knowledge/package_checks.py:47-108`) therefore validates digest-entry *shape*
-- list-of-mappings, `sha256:<64 hex>`, source listed in `sources`, no duplicates,
source resolves to one file -- and never compares a digest to current content.

## 5. Documentation validation and CI

### 5.1 `validate-wiki`

`commands/wiki.py:15-26` → `wiki/links.py:108-112`. Three checks over every
Markdown file under the wiki root:

1. `validate_markdown_links` (`wiki/links.py:31-50`): every `[text](target)`
   must resolve. A target starting `/` resolves from the **repository root**
   (`:44`); anything else from the file's own directory. Anchors, empty targets
   and anything matching a URI scheme are skipped (`:37-40`).
2. `validate_root_relative_markdown_links` (`:53-65`): `../` traversal links are
   rejected outright.
3. `validate_obsidian_links` (`:90-105`): every `[[wiki-link]]` must resolve
   against the file's directory, the wiki root, or a bare-name `rglob` across the
   wiki (`:73-87`). A missing wiki root is itself a finding (`:91-93`).

**Not checked:** backtick path citations, `hydra://` references, provenance,
staleness, or whether a linked file's *content* still supports the claim.

This corrects D2 and D3 on `source-map.md`. The page has 19 rows citing **41**
distinct non-wiki paths, every one a root-relative Markdown link, every one
resolving -- and `validate_markdown_links:44` checks all 41 on every CI run.
`validate-wiki` passes today.

The genuinely unchecked citations are backticks. Across all 40 wiki pages there
are 151 backtick path-shaped strings; 94 are root-anchored and unambiguous, and
93 of those resolve. The one that does not --
`.hydra-framework.local/capabilities/active.yaml` in
`extending-hydra/capabilities.md` -- names the Git-ignored private tier, where
absence is correct. The remaining 57 are relative fragments (`cli/dispatch.py`,
`objects/`) or placeholders (`project-wiki/<project-name>/`) with **no defined
resolution rule at all**, which is the concrete reason `validate-wiki` cannot
check them rather than merely does not.

### 5.2 `validate-package-docs`

`commands/knowledge_docs.py:57-83` → `knowledge/package_checks.py:289-309`, per
discovered node root. Three checks plus one optional side effect:

- `validate_markdown_links` -- the same function `validate-wiki` uses, applied to
  the node tree.
- `validate_units_dir` (`knowledge/package_checks.py:138-259`): unit
  recognizability; `unit_kind` in `UNIT_KINDS`; `question` present, ending in
  `?`, under the length cap, flagged when it contains " and "; `rule` requires
  non-empty `provenance.sources`; `status` requires `checked_on`; `divergence`
  requires `certainty: conflicting` and the phrase "effect on agents";
  `source_digests` shape; `reads:` paths resolve unless
  `certainty: unresolved`; `requires` / `see_also` / `expand_when[].read` are
  well-shaped `hydra://` ids; `requires` cycles.
- `validate_package_file_sizes` (`:261-287`): any Markdown file over the
  8000-token ceiling.
- `--render` writes `images/*.svg` and `*.png` from `diagrams/*.dot`.

Existence of a `hydra://` target is explicitly **not** checked here -- it is left
to `ref check`'s whole-tree scan (`knowledge/package_checks.py:141-147`).

### 5.3 `doctor` and `validate`

`validate` (`commands/validation.py:24-36`) runs the 19 validators in
`checks/validator_registry.py:94-106` in locked order, prints findings and exits
1, or prints `ok` and then advisory notes **after** the verdict so a note never
reads as a failure:

1 task-records · 2 provider-surfaces · 3 module-metadata · 4 capability-maps ·
5 capability-profiles · 6 task-contract-docs · 7 adaptations-ledger ·
8 tier-boundaries · 9 private-tier-documented · 10 architecture ·
11 object-model · 12 config-policy · 13 flat-knowledge · 14 knowledge-node-docs ·
15 knowledge-v3 · 16 capability-callers · 17 reflection-queue ·
18 candidate-queue · 19 telemetry-evidence

Validator 11, `object-model`, is `objects/registry.py:225-235`:
`validate_object_references` then, if clean, registry freshness -- the same pair
`ref check` runs. **`validate` therefore already enforces the whole object model,
and CI gets it through `doctor`.**

`doctor` (`commands/validation.py:39-120`) first prints required paths, task
counts, owner resolution, private-tier status, cache lifecycle (knowledge index
and object store freshness, with rebuild hints), provider surfaces, and adoption
lineage, then delegates the verdict to `command_validate`. It exits 1 early on
missing required paths (`:55-59`), a not-effectively-ignored private tier
(`:83-85`), and no materialized provider surfaces when a plan is active
(`:100-105`).

Advisory notes (`cli/dispatch.py:133-145`) cover stale tasks, the reflection and
candidate queues, telemetry evidence age, provider verification age, retry-state
growth, knowledge-event growth, and config. All are printed, none fail.

### 5.4 `reclaim`

`providers/reclaim.py:98-146` classifies every `.md`/`.toml` under the six
provider roots (`:33-40`) into `generated`, `drifted`, `stale`, or `orphaned`, by
reading each file's `.hydra-adapter*.yaml` sidecar and comparing against the
planned adapter output. `--promote` moves orphaned files into canonical Hydra
(marked `certainty: inferred`, `scope: repo-local`);
`--fail-on-findings` exits nonzero. The same classification feeds validator 2
and `doctor`'s surface report.

### 5.5 What CI runs

`.github/workflows/hydra.yml`, on push to `main`, every pull request, and manual
dispatch. Python 3.11, no dependencies.

| Step | Command | Line | Enforcing? |
| --- | --- | --- | --- |
| Bootstrap capability adapters | `export-adapters` | 33 | yes (nonzero fails the job) |
| Selftest | `selftest` | 36 | yes |
| Doctor | `doctor` | 39 | yes -- carries all 19 validators, including the full object model |
| Private state is not tracked | `git ls-files` guard | 44-53 | yes, deliberately duplicating validator 8 so a violation names itself |
| Unmanaged provider surfaces | `reclaim --fail-on-findings` | 56 | yes |
| Knowledge package gates | `validate-package-docs` | 59 | yes |
| Wiki links | `validate-wiki` | 62 | yes |
| Context surface size | `measure-context` | 67 | **advisory** -- no `--fail-over`, by an in-file comment saying the team has picked no budget |

**Not run in CI:** `knowledge stale`, `ref store rebuild`/`status`,
`bindings verify`, `export-adapters --check` (removed deliberately -- the comment
at `:28-31` explains that a drift gate is meaningless once nothing is tracked),
and `ref check`/`ref index` as standalone steps (covered transitively by
validator 11).

**Nothing in CI asks whether any documentation is stale.** The only staleness
mechanism in the repository is the one command CI does not run.

## 6. Surface model as built

### 6.1 The contract

`.hydra-framework/surfaces/README.md`, 105 lines. Surfaces are "audience-facing
or interface-specific views of knowledge"; the directory "records surface
contracts -- whether a surface is canonical, derived, synchronized, private,
generated, or hand-maintained", and "the pages themselves live outside
`.hydra-framework/`" (`:3-6`).

Four surfaces are described: **Wiki** (`:13-86`), **Developer Docs** (`:88-91`),
**Obsidian** (`:93-99`, role deliberately undecided, deferred to
`core/unresolved-questions.md`), and the rule for adding one (`:101-105`): "Add a
section here describing the contract, not an empty directory."

The wiki surface names three sub-surfaces (`:15-19`): `project-wiki/home.md`,
`project-wiki/hydra-framework/`, and `project-wiki/<project-name>/`.

**The whole contract is prose.** `.hydra-framework/surfaces/` contains exactly
one file, `README.md`, and that file has no frontmatter and no `hydra_id`, so it
is not an object -- it is scanned by the Markdown handler and discarded by
`objects/envelopes.py:112-114`. Nothing machine-readable exists at any surface
boundary today. This is consistent with `:101-105`, which asks for a contract
section rather than a directory, but it means "the surface contract" is not
currently queryable, verifiable, or addressable.

### 6.2 Audiences table

`surfaces/README.md:44-51`, four rows: New teammates (orientation, vocabulary,
boundaries, a path into daily use); Daily AI-agent users (operating guides saying
what to read, run, update, validate); Framework maintainers (source maps,
boundaries, gap lists, style rules); Reviewers and adopters (presentation-ready
summaries, diagrams, adoption flow, source links).

Nothing in the engine reads this table, and no wiki page declares which row it
serves.

### 6.3 Citation rules

`surfaces/README.md:53-79`:

- Every durable claim needs an inline link or a nearby `Sources` section pointing
  at the canonical owner (`:55-56`).
- Good targets: canonical `.hydra-framework/` files, code and tests that own
  behavior, task records for in-flight work, validation output for
  command-dependent claims, external owners when Git does not own the state
  (`:58-62`).
- Never cite `.hydra-framework.local/` from a shared page; inline origin, date
  checked, source owner and the promoted claim instead -- explicitly the one case
  where naming a check's origin and date belongs in prose (`:64-68`).
- Citing means linking, not narrating. Command-plus-date sentences, "a search
  found nothing" notes, and trailing "Source Notes" sections are process log, and
  process log belongs in a task record's continuation notes (`:70-76`).
- If wiki and canonical source disagree, **update the canonical source first**
  (`:78-79`).
- `:83-86` states that `validate-wiki` checks Markdown and Obsidian links "and
  does not validate backtick path citations" -- accurate, and confirmed at
  `wiki/links.py:108-112`.

### 6.4 The wiki-authoring skill

`.hydra-framework/capabilities/skills/wiki-authoring/skill.md`, 50 lines;
metadata at `metadata.yaml`, `hydra://capability/skill/wiki-authoring`,
`kind: procedure`, `scope: common-seed`, `maturity: seed`,
`provider_requirements: read_files, edit_files, run_local_commands`.

Eight procedure steps (`skill.md:11-32`): read canonical sources first; update
the canonical file first; keep pages short and link rules rather than restate
them; cite near durable claims and never cite the private tier; record gaps
explicitly; write as an engineer, not as a research log (no command-plus-date
sentences, no "Source Notes", no em dashes); run `validate-wiki` after edits and
`validate` if `.hydra-framework/` was touched; one page at a time unless a plan
is approved.

Its `provenance.sources` are `.hydra-framework/surfaces/README.md` and
`project-wiki/hydra-framework/reference/documentation-authoring.md`
(`metadata.yaml:21-23`) -- the **only** declared dependency anywhere in
`.hydra-framework/` on a `project-wiki/` file. Two consequences, both measured:

- `ref check` existence-checks that wiki path on every run, through
  `objects/references.py:95-102`. A wiki page **can** already break `validate`
  today, by being deleted or moved.
- `explain-path project-wiki/hydra-framework/reference/documentation-authoring.md`
  returns `Tier: external`, `Object: none`, `Cited as provenance by:
  hydra://capability/skill/wiki-authoring`.

So the repository can already answer "which Hydra objects depend on this wiki
page". It cannot answer the inverse -- "which sources does this wiki page depend
on, and did any change" -- because no wiki page has an envelope to declare
`provenance.sources` in.

## 7. Where documentation and code disagree

Each row is a second finding in its own right, per the phase's rule.

### 7.1 `.hydra-framework/scripts/README.md`

`:129-135` describes sidecar path resolution as "resolved from the sidecar file
unless they start with a repository root such as `.hydra-framework/`". The code
(`objects/discovery.py:48`) accepts exactly three prefixes:
`.hydra-framework/`, `.hydra-framework.local/`, `project-wiki/`. The README's
"such as" hides the fact that `project-wiki/` is already a first-class sidecar
root.

### 7.2 `project-wiki/hydra-framework/reference/source-map.md`

Its own Review Rule says "Backtick paths are useful for readers but are not link
validation, so verify every path against the repository when this map changes."
The page contains **zero** backtick path citations -- all 41 canonical citations
are root-relative Markdown links that `validate-wiki` already checks. The warning
is correct about the repository in general and wrong about the page it appears
on.

### 7.3 `knowledge stale`'s own output

`commands/knowledge.py:194` hardcodes `": {sources} committed after checked_on"`
for every row, regardless of which of the two rules in
`knowledge/freshness.py:305-313` fired. All 27 sources across all 7 units are
digested, so the date rule never runs, and **every** line the command currently
prints states a reason that did not apply. Confirmed: `command_metadata.py`'s
current digest is `sha256:de8fb166…`, the unit records `sha256:7045a3aa…`, and
its last commit is 2026-09-12 -- after the unit's `checked_on: 2026-09-10`, so
both rules would agree on the verdict, but only one was consulted.

### 7.4 In-code docstrings that no longer match

- `cli/parser.py:12-13`: "how `scripts/hydra.py` registers the ten commands still
  dispatched through its own globals". It registers one, `selftest`
  (`scripts/hydra.py:48-51`).
- `checks/validator_registry.py:21,35,47`: "`validate`/`doctor`'s ten checks",
  "the full ten-check order". There are 19 (`VALIDATORS`, `:94-106`).
- `objects/object_handlers.py:45-47`: "it turned the two that declare one into
  objects". Three engine modules declare an envelope today:
  `object-family-registry`, `object-handler-registry`, `validator-registry`.
- `commands/references.py:96-98`: describes `ref rdeps` as serving the `refs`
  index. It queries `relations`; nothing queries `refs`.

None of these change behavior. All four are exactly the class of drift this
review exists to make detectable, occurring inside the engine rather than in the
wiki -- which is evidence that the problem is not wiki-specific.

## 8. Unestablished

Recorded rather than softened or omitted.

1. **Whether `refs` and `documents.envelope_json` are dead by intent or by
   oversight.** No consumer exists in `hydra_engine/`. Both are populated on every
   rebuild and incrementally repaired (`store_build.py:184-190`). No task record
   or test states a planned consumer. Not established either way.
2. **Whether any downstream Hydra copy authors a non-`relates-to` relation
   type.** Measured only in this repository. `RELATION_TYPES` is `base-seed`
   vocabulary, so a downstream copy could be using it; this reconstruction cannot
   see one.
3. **The blast radius of registering `project-wiki/` pages as sidecar objects on
   `ref check`.** §2.4 establishes that sidecar-registered files are not
   themselves scanned for `hydra://` references, so prose is not put under the
   resolution requirement. What is *not* established is whether
   `explain-path`, `move-object`, `reclaim`'s surface classification, or
   `measure-context` behave correctly on an `external`-tier object -- no such
   object exists today, and no test constructs one.
4. **Whether `validate-package-docs` in CI covers the whole knowledge tree or
   only nodes.** `node_roots_from_args` (`commands/knowledge_docs.py:15-27`)
   returns every discovered node when no selector is given, and
   `_node_document_findings` (`:34-54`) adds findings belonging to no node. With
   one node, the two are indistinguishable. The multi-node behavior is tested
   only in fixtures.
5. **Why `migration status` and `integrate status` have no test at any layer.**
   Both are read-only reporting commands over state other tested commands write,
   which is a plausible reason, but no record states it.
6. **The 364-row `documents` count against the 57-object count.** 364 files under
   `.hydra-framework/` match a registered handler suffix; 57 declare an envelope.
   The ratio is consistent with `objects/object_handlers.py:45-47`'s design, but
   no test or record asserts an expected ratio, so nothing would notice if it
   moved.

## 9. Gate evidence

- `hydra.py ref index` → `Indexed 57 objects`
- `hydra.py ref check` → `Hydra references: ok (57 objects)`
- `hydra.py ref store rebuild` → `rebuilt from 57 object(s)`
- `hydra.py ref store status` → `status: fresh`, `export digest: agrees with the export`
- `hydra.py knowledge stale` → `Checked units: 7`, 2 stale
- `hydra.py validate-wiki` → `Hydra wiki docs: ok`
- `hydra.py validate` → `Hydra validate: ok`, 5 advisory notes
