# Knowledge v3 Decision Gates

`enterprise-fixture.json` is a deterministic generative fixture with 216 leaf
nodes across six spaces and 36 accountability areas. It also declares
cross-space dependency edges, logical path bindings, and representative task
ground truth. Including space and area nodes, the materialized tree contains
258 nodes.

Run the gates with:

```bash
python3 .hydra-framework/validation/knowledge-v3/benchmark.py \
  --output .hydra-framework.local/knowledge-v3/gates.json
```

The checked-in fixture and benchmark are durable and reproducible. Raw timing
output remains private because latency varies by machine. Gate conclusions and
frozen policy values belong in canonical Knowledge v3 documentation after the
results have been reviewed.

The distribution fixture deterministically models two target profiles:
`base-seed` only and `base-seed` plus `common-seed`. It cannot substitute for a
real second repository; the report keeps that production gate pending.
