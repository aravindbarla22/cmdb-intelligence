# Architecture

```
Synthetic estate  ->  Platform adapter  ->  Canonical CI model  ->  Core engine
(known problems)      (ServiceNow,          (plain JSON)            normalize, match,
                       NetBox, ...)                                  infer, drift
                                                                          |
        Human approval  <-  Proposed fixes  <-----------------------------+
```

## Principles

1. **The core knows nothing about any vendor.** It reads and writes a plain
   canonical format. Adapters translate to and from each platform.
2. **Propose, never apply.** Remediation produces proposals. A person approves
   each one in the platform's own workflow before anything changes.
3. **Everything is scored.** Every method is measured against injected ground
   truth and against simple baselines, and results are reproducible from a seed.

## Canonical CI record

```json
{"id": "app-0001", "class": "business_app", "name": "Apex Billing",
 "created": "2024-03-01", "last_seen": "2025-12-20", "attrs": {}}
```

Relationships: `{"parent": "...", "child": "...", "type": "runs_on"}`.
Baselines: `{ "<server id>": {"os_version": "...", "agent_version": "...", ...} }`.

## Evaluation

| Capability | Metrics |
| --- | --- |
| Duplicate reconciliation | precision, recall, F1, master-selection accuracy |
| Relationship inference | precision and recall of recovered links |
| Drift detection | recall, false-positive rate, time to detect |
| Remediation | share of proposals that restore baseline when applied in simulation |

## Benchmarking against native tooling

For each platform adapter, compare results with that platform's built-in
reconciliation, duplicate and health tooling on the same data, and report where
each approach wins or loses.
