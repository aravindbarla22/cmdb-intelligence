"""Configuration drift detection against an approved baseline.

Two detectors are provided so that results can be compared:
  * detect_drift_exact:  reports every difference from the baseline.
  * detect_drift_policy: ignores changes the policy explicitly approves and
    attaches a severity to the rest.

Limitations: both compare attribute values only. Neither uses change history,
so time to detect is not measured yet.
"""

SEVERITY = {"ssh_root_login": "critical"}


def _changes(cis, baseline, classes):
    for ci in cis:
        if ci["class"] not in classes or ci["id"] not in baseline:
            continue
        base, cur = baseline[ci["id"]], ci.get("attrs", {})
        for field in sorted(set(base) | set(cur)):
            if base.get(field) != cur.get(field):
                yield {"ci_id": ci["id"], "field": field,
                       "baseline": base.get(field), "current": cur.get(field)}


def detect_drift_exact(cis, baseline, classes=("server",)):
    return list(_changes(cis, baseline, classes))


def detect_drift_policy(cis, baseline, policy, classes=("server",)):
    approved = policy.get("approved_value_changes", {})
    findings = []
    for change in _changes(cis, baseline, classes):
        if change["current"] in approved.get(change["field"], []):
            continue
        change = dict(change)
        change["severity"] = SEVERITY.get(change["field"], "medium")
        findings.append(change)
    return findings
