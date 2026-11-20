# cmdb-intelligence

An open, vendor-neutral reference implementation and benchmark for keeping
configuration management databases (CMDBs) accurate: duplicate reconciliation,
relationship inference, configuration drift detection, and policy-governed
remediation with human approval.

**Status: early scaffold.** The synthetic data generator, a duplicate-detection
baseline, two drift detectors and the scoring code exist today. Everything else
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
core/         vendor-neutral engine: normalize, match, drift (infer, remediate: planned)
data/         synthetic estate generator with injected ground truth
eval/         metrics against ground truth
adapters/     connectors to specific platforms (servicenow: built, untested on a real instance; netbox: planned)
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

### Drift detection (seed 42, 60 servers, synthetic data only)

Drift means a difference from the approved baseline that the policy does not
permit. In hard mode, agent upgrades to approved versions are allowed, so they
are not drift.

| Difficulty | Detector | Precision | Recall |
| --- | --- | --- | --- |
| Easy (no approved changes) | Exact difference | 1.00 | 1.00 |
| Easy | Policy-aware | 1.00 | 1.00 |
| Hard (12 approved changes among 8 true drift findings) | Exact difference | 0.40 | 1.00 |
| Hard | Policy-aware | 1.00 | 1.00 |

The policy-aware detector applies the same policy that defines the ground
truth, so its score is a reference ceiling, not evidence of performance. What
the table shows is that flagging every difference produces many false alarms
once routine, approved changes exist. Real environments have messier policies;
measuring that is future work.

## Known limitations

- Duplicate candidates are grouped by the first character of the normalized
  name, so a change to the first character is missed.
- Duplicate matching uses a plain string similarity ratio and ignores attributes and relationships.
- Numbered instances such as "Billing 1" and "Billing 2" are false positives.
- Drift detectors compare current attribute values only. They use no change
  history, so time to detect is not measured yet.

## Roadmap

- [x] Synthetic estate generator with labeled ground truth
- [x] Name normalization, baseline duplicate matcher, master-record selection
- [x] Precision, recall and F1 scoring
- [ ] Attribute- and relationship-aware matching
- [ ] Relationship inference with evaluation
- [x] Baseline comparison and policy-aware drift detection with severity
- [ ] Change history and time-to-detect for drift
- [ ] Learned (non-rule) drift and anomaly detection on noisier policies
- [ ] Policy-governed remediation planner (propose only, human approval)
- [x] ServiceNow adapter (load, export, evaluate, cleanup), tested against a simulation only
- [ ] Run the adapter on a real instance and fix the mapping
- [ ] Benchmark against the platform's native duplicate tooling
- [ ] Second platform adapter (NetBox or iTop)

## Independence

All data and code in this repository are original and fictional. No employer
code, data, configurations or table names are used.

## License

MIT. See LICENSE.
