# Knowledge v3 Decision Gates

`enterprise-fixture.json` is a deterministic generative fixture with 216 leaf
nodes across six spaces and 36 accountability areas. It also declares
cross-space dependency edges, logical path bindings, and representative task
ground truth. Including space and area nodes, the materialized tree contains
258 nodes.

Two harnesses read that one fixture, and they answer different questions.

## `benchmark.py`: why Option D was chosen

This is the original comparative evidence. It scores prototype routers,
including the flat v2 and hierarchical alternatives the engine never shipped,
so it stays as the record behind the frozen contract.

```bash
python3 .hydra-framework/validation/knowledge-v3/benchmark.py \
  --output .hydra-framework.local/knowledge-v3/gates.json
```

## `engine_gates.py`: whether the shipped engine still clears them

This materializes the same fixture as a real Knowledge v3 tree on disk and
drives the shipped `hydra_engine.knowledge` runtime over it: the node
validator, `route_nodes`, and the binding resolver. A routing regression in
the engine surfaces here rather than only in a prototype that no longer
reflects the code.

```bash
python3 .hydra-framework/validation/knowledge-v3/engine_gates.py \
  --output .hydra-framework.local/knowledge-v3/engine-gates.json
```

The report is byte-identical between runs. Latency is machine-dependent and is
therefore excluded unless `--timings` is passed.

The materialized 258-node tree passes `validate_knowledge_nodes` with zero
findings, and every fixture binding reaches `verified` after its assertion
fingerprint is accepted, so the gate exercises real path rerouting rather than
a simulated one.

### Shipped retrieval is below the prototype and above v2

| Metric | v2 prototype | v3 prototype | Shipped engine | Shipped, no hints |
| --- | --- | --- | --- | --- |
| recall@3 | 0.4921 | 0.6746 | 0.5952 | 0.4762 |
| precision@3 | 0.5397 | 0.8333 | 0.6905 | 0.5714 |
| false positive rate | 0.4444 | 0.1538 | 0.3095 | 0.4500 |
| mean pointer tokens | 28.33 | 24.71 | 26.10 | 24.52 |

**These columns are not a like-for-like comparison.** The prototypes score
their own scoring functions over their own in-memory corpus. `engine_gates.py`
drives the shipped router over a materialized tree and feeds it index hints
derived from the fixture's `indexed_hints` table rather than from the live
SQLite index, so the hint ranking is an oracle rather than a measurement of
retrieval quality. What the third column measures is how the shipped router
combines an index ranking with its own keyword score, not how well the index
ranks.

Read that way, two things hold. The Option D decision survives contact with
the shipped engine, and the prototype numbers overstate what shipped, so the
frozen contract's cold-start conclusion should be read against this table
rather than against the prototype alone.

The fourth column is the load-bearing one: with no index hints, the shipped
router lands in v2 territory. The index contribution, not node keywords, is
what carries v3's retrieval gain. It is emitted as
`retrieval_without_index_hints` in every report, so the claim is re-runnable
rather than quoted from a one-off experiment.

Path rerouting matches the prototype exactly: useful bindings for 21 of 21
workloads, two cold misses corrected, one bound node mean and max.

### Routing cost scales with tree size

Routing re-reads and re-parses the whole tree on every call, which is 25 ms of
the per-call cost at 258 nodes. This is the concern the `KnowledgeStore`
boundary exists to address and is not addressed here.

Measuring the gate also exposed a lookup that resolved every node root once
per search result, making routing cost scale with results times nodes. Caching
the resolved roots for the duration of one call cut fixture routing from about
152 ms to about 39 ms at p50 on one machine, with identical selections. Run
with `--timings` to measure that on yours.

The residual per-call cost is tracked as P4 in the `hydra-framework` space's
`problems.md`.

## Scope and limits

The checked-in fixture and both harnesses are durable and reproducible. Raw
timing output stays private because latency varies by machine. Gate
conclusions and frozen policy values belong in canonical Knowledge v3
documentation after the results have been reviewed.

The distribution fixture deterministically models two target profiles:
`base-seed` only and `base-seed` plus `common-seed`. It cannot substitute for a
real second repository; both harnesses keep that production gate pending.
