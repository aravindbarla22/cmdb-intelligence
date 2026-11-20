# cmdb-intelligence

An open, vendor-neutral reference implementation and benchmark for keeping
configuration management databases (CMDBs) accurate: duplicate reconciliation,
relationship inference, configuration drift detection, and policy-governed
remediation with human approval.

**Status: early scaffold.** Only the deterministic duplicate-detection baseline,
the synthetic data generator and the scoring code exist today. Everything else
is planned (see the roadmap). Nothing here has been validated on real
environments, and the numbers below come from synthetic data only.

## Why a benchmark first

CMDB research is hard to compare because real CMDBs are private. This repo
generates fictional estates with **known, labeled problems** (duplicates,
stale records, missing relationships, drift), so any method can be scored
against ground truth and anyone can reproduce the results.

## Quick start

Requires Python 3.9+ and nothing else (standard library only).

```bash
python3 run_demo.py                          # generate, detect, score
python3 data/synth.py --difficulty hard      # write a synthetic estate to out/synthetic
python3 -m unittest discover -s tests -t .   # run tests
```

## Layout

```
core/         vendor-neutral engine: normalize, match, (infer, drift, remediate: planned)
data/         synthetic estate generator with injected ground truth
eval/         metrics against ground truth
adapters/     connectors to specific platforms (servicenow, netbox: planned)
servicenow-app/  scoped app for proposals and approvals (planned)
docs/         architecture and roadmap
```

## Baseline results (synthetic data only)

Seed 42, 100 applications, duplicate detection with a 0.92 name-similarity threshold:

| Difficulty | Precision | Recall |
| --- | --- | --- |
| Easy (noise the normalizer removes) | 1.00 | 1.00 |
| Hard (reordered words, abbreviations, version suffixes, look-alike distinct apps) | 0.55 | 0.80 |

The easy setting is solved by the baseline and exists as a sanity check. The
hard setting is the target to improve on. These figures describe a baseline on
fictional data. They are not a validation of any method on real systems.

## Known limitations of the baseline

- Candidates are grouped by the first character of the normalized name, so a
  change to the first character is missed.
- Matching uses a plain string similarity ratio and ignores attributes and relationships.
- Numbered instances such as "Billing 1" and "Billing 2" are false positives.

## Roadmap

- [x] Synthetic estate generator with labeled ground truth
- [x] Name normalization, baseline duplicate matcher, master-record selection
- [x] Precision, recall and F1 scoring
- [ ] Attribute- and relationship-aware matching
- [ ] Relationship inference with evaluation
- [ ] Baseline snapshots and drift detection with time-to-detect
- [ ] Policy-governed remediation planner (propose only, human approval)
- [ ] ServiceNow adapter and benchmark against native tooling
- [ ] Second platform adapter (NetBox or iTop)

## Independence

All data and code in this repository are original and fictional. No employer
code, data, configurations or table names are used.

## License

MIT. See LICENSE.
