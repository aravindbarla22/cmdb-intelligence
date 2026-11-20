"""Synthetic CMDB estate generator with labeled, injected problems.

Everything here is fictional. Names are invented and no employer data is used.
The generator is deterministic for a given seed, so results are reproducible.

It produces:
  cis            - configuration items (business apps, app services, servers)
  relationships  - parent/child links between CIs
  baseline       - approved configuration for each server
  ground_truth   - the problems that were injected, for scoring detectors
"""
import argparse
import json
import random
from datetime import date, timedelta
from pathlib import Path

PREFIXES = [
    "Apex", "Bluefin", "Cedar", "Delta", "Ember", "Falcon", "Granite", "Harbor",
    "Ion", "Juniper", "Kestrel", "Lumen", "Meridian", "Nimbus", "Orbit",
    "Pioneer", "Quartz", "Ridge", "Summit", "Tidal",
]
KINDS = [
    "Billing", "Payroll", "Inventory", "Ticketing", "Analytics",
    "Scheduler", "Gateway", "Portal", "Vault", "Registry",
]
NOISE_SUFFIXES = ["App", "Application", "Prod", "Production", "Inc"]
OS_VERSIONS = ["ubuntu-22.04", "ubuntu-24.04", "rhel-8.9", "rhel-9.3", "win-2019", "win-2022"]
AGENT_VERSIONS = ["1.4.2", "1.5.0", "1.5.1"]
REFERENCE_DATE = date(2026, 1, 1)  # fixed so output is reproducible


def _iso(d):
    return d.isoformat()


def _drop_letter(name, rng):
    """Delete one letter, never the first character."""
    letters = [i for i in range(1, len(name)) if name[i].isalpha()]
    i = rng.choice(letters)
    return name[:i] + name[i + 1:]


def _mutate_name(name, rng, hard=False):
    """Return a variant of an application name that a person would treat as the same app.

    Easy mode only produces noise the baseline normalizer is built to remove
    and never changes the first character. Hard mode adds reordered words,
    abbreviations, version suffixes and double typos, which the baseline
    is expected to miss in part.
    """
    easy = ["case", "punct", "noise_suffix", "the_prefix", "typo", "spacing"]
    hard_kinds = ["reorder", "abbrev", "version", "double_typo"]
    kind = rng.choice(easy + (hard_kinds if hard else []))
    if kind == "reorder":
        return " ".join(reversed(name.split()))
    if kind == "abbrev":
        parts = name.split()
        parts[-1] = parts[-1][:4]
        return " ".join(parts)
    if kind == "version":
        return f"{name} v{rng.randint(2, 4)}"
    if kind == "double_typo":
        return _drop_letter(_drop_letter(name, rng), rng)
    if kind == "case":
        return name.upper() if rng.random() < 0.5 else name.lower()
    if kind == "punct":
        return name.replace(" ", rng.choice(["-", "_"]))
    if kind == "noise_suffix":
        return f"{name} {rng.choice(NOISE_SUFFIXES)}"
    if kind == "the_prefix":
        return f"The {name}"
    if kind == "spacing":
        return name.replace(" ", "  ")
    return _drop_letter(name, rng)  # typo


def generate(seed=42, n_apps=100, n_servers=60, dup_rate=0.15,
             stale_rate=0.08, missing_rel_rate=0.05, drift_rate=0.10,
             difficulty="easy", decoy_rate=0.10):
    """difficulty: "easy" or "hard". Hard adds tougher name variants and decoys:
    pairs of distinct, similarly named apps (for example "Apex Billing 1" and
    "Apex Billing 2") that must NOT be reported as duplicates."""
    hard = difficulty == "hard"
    rng = random.Random(seed)
    names = [f"{p} {k}" for p in PREFIXES for k in KINDS]
    rng.shuffle(names)
    n_apps = min(n_apps, len(names))

    cis, rels = [], []

    apps = []
    for i in range(n_apps):
        created = REFERENCE_DATE - timedelta(days=rng.randint(200, 1500))
        apps.append({
            "id": f"app-{i:04d}", "class": "business_app", "name": names[i],
            "created": _iso(created),
            "last_seen": _iso(REFERENCE_DATE - timedelta(days=rng.randint(0, 30))),
        })
    cis.extend(apps)

    servers, baseline = [], {}
    for j in range(n_servers):
        attrs = {
            "os_version": rng.choice(OS_VERSIONS),
            "agent_version": rng.choice(AGENT_VERSIONS),
            "ssh_root_login": False,
        }
        sid = f"srv-{j:04d}"
        servers.append({
            "id": sid, "class": "server", "name": sid,
            "created": _iso(REFERENCE_DATE - timedelta(days=rng.randint(100, 1200))),
            "last_seen": _iso(REFERENCE_DATE - timedelta(days=rng.randint(0, 30))),
            "attrs": dict(attrs),
        })
        baseline[sid] = dict(attrs)
    cis.extend(servers)

    services = []
    for i, app in enumerate(apps):
        svc = {
            "id": f"svc-{i:04d}", "class": "app_service", "name": f"{app['name']} Service",
            "created": app["created"], "last_seen": app["last_seen"],
        }
        services.append(svc)
        rels.append({"parent": app["id"], "child": svc["id"], "type": "has_service"})
        for srv in rng.sample(servers, k=min(len(servers), rng.randint(1, 2))):
            rels.append({"parent": svc["id"], "child": srv["id"], "type": "runs_on"})
    cis.extend(services)

    truth = {"duplicate_pairs": [], "stale": [], "missing_relationships": [], "drift": []}

    # 1. Duplicate applications: a later record with a variant of the name.
    for k, master in enumerate(rng.sample(apps, k=int(n_apps * dup_rate))):
        created = date.fromisoformat(master["created"]) + timedelta(days=rng.randint(10, 150))
        dup = {
            "id": f"app-d{k:04d}", "class": "business_app",
            "name": _mutate_name(master["name"], rng, hard=hard),
            "created": _iso(created),
            "last_seen": _iso(REFERENCE_DATE - timedelta(days=rng.randint(0, 30))),
        }
        cis.append(dup)
        truth["duplicate_pairs"].append({"master": master["id"], "duplicate": dup["id"]})

    # 1b. Decoys (hard mode): distinct apps with confusable names; not duplicates.
    if hard:
        for k, base in enumerate(names[n_apps:n_apps + int(n_apps * decoy_rate)]):
            for n in (1, 2):
                cis.append({
                    "id": f"app-x{k:04d}{n}", "class": "business_app", "name": f"{base} {n}",
                    "created": _iso(REFERENCE_DATE - timedelta(days=rng.randint(200, 1500))),
                    "last_seen": _iso(REFERENCE_DATE - timedelta(days=rng.randint(0, 30))),
                })

    # 2. Stale records: not seen for a long time.
    for ci in rng.sample(apps + servers, k=int((n_apps + n_servers) * stale_rate)):
        ci["last_seen"] = _iso(REFERENCE_DATE - timedelta(days=rng.randint(150, 400)))
        truth["stale"].append(ci["id"])

    # 3. Missing relationships: remove some runs_on links.
    runs_on = [r for r in rels if r["type"] == "runs_on"]
    for r in rng.sample(runs_on, k=int(len(runs_on) * missing_rel_rate)):
        rels.remove(r)
        truth["missing_relationships"].append(dict(r))

    # 4. Configuration drift: servers whose current state differs from baseline.
    for srv in rng.sample(servers, k=int(n_servers * drift_rate)):
        for field in rng.sample(["os_version", "agent_version", "ssh_root_login"], k=rng.randint(1, 2)):
            old = srv["attrs"][field]
            if field == "ssh_root_login":
                new = True
            elif field == "os_version":
                new = rng.choice([v for v in OS_VERSIONS if v != old])
            else:
                new = rng.choice([v for v in AGENT_VERSIONS if v != old])
            srv["attrs"][field] = new
            truth["drift"].append({"ci_id": srv["id"], "field": field, "baseline": old, "current": new})

    rng.shuffle(cis)
    return {"cis": cis, "relationships": rels, "baseline": baseline, "ground_truth": truth}


def write(estate, outdir):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    for key, value in estate.items():
        (out / f"{key}.json").write_text(json.dumps(value, indent=2))


def main():
    ap = argparse.ArgumentParser(description="Generate a synthetic CMDB estate.")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--apps", type=int, default=100)
    ap.add_argument("--servers", type=int, default=60)
    ap.add_argument("--difficulty", choices=["easy", "hard"], default="easy")
    ap.add_argument("--out", default="out/synthetic")
    args = ap.parse_args()
    estate = generate(seed=args.seed, n_apps=args.apps, n_servers=args.servers,
                      difficulty=args.difficulty)
    write(estate, args.out)
    print(f"Wrote {len(estate['cis'])} CIs to {args.out}")


if __name__ == "__main__":
    main()
