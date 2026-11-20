"""Command line for the ServiceNow adapter.

    python3 -m adapters.servicenow load      # dry run: prints requests, sends nothing
    python3 -m adapters.servicenow load --execute
    python3 -m adapters.servicenow check | export | evaluate | cleanup

Credentials come from environment variables, never from arguments:
    SN_INSTANCE (for example dev12345), SN_USER, SN_PASSWORD
"""
import argparse
import json
import os
import sys
from pathlib import Path

from core.drift import detect_drift_policy
from core.match import find_duplicate_pairs
from data.synth import generate
from eval.metrics import drift_metrics, duplicate_metrics

from .client import Client, ServiceNowError
from .mapping import PREFIX, REL_TYPES, TABLES
from .sync import cleanup, export_estate, load_estate


def _client(args, writes):
    dry_run = writes and not args.execute
    instance, user, password = (os.environ.get(k) for k in ("SN_INSTANCE", "SN_USER", "SN_PASSWORD"))
    if not dry_run and not (instance and user and password):
        sys.exit("Set SN_INSTANCE, SN_USER and SN_PASSWORD in your environment first.")
    return Client(instance, user, password, dry_run=dry_run, allow_non_pdi=args.allow_non_pdi)


def cmd_check(client, args):
    print(f"Instance: {client.base}")
    for cls, table in TABLES.items():
        print(f"  {table:<28} total={client.count(table)}  ours={client.count(table, 'correlation_idSTARTSWITH' + PREFIX)}")
    for key, name in REL_TYPES.items():
        found = client.get_all("cmdb_rel_type", f"name={name}", ["sys_id"])
        print(f"  relationship type '{name}': {'found' if found else 'MISSING'}")


def cmd_load(client, args):
    estate = generate(seed=args.seed, n_apps=args.apps, difficulty=args.difficulty)
    print(("DRY RUN: nothing is sent. " if client.dry_run else "") +
          f"Loading seed={args.seed} difficulty={args.difficulty}")
    print(load_estate(client, estate))
    client.summary()
    if client.dry_run:
        print("Review the output above, then add --execute to write to your instance.")


def cmd_export(client, args):
    exported = export_estate(client)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for key, value in exported.items():
        (out / f"{key}.json").write_text(json.dumps(value, indent=2))
    print(f"Exported {len(exported['cis'])} CIs and {len(exported['relationships'])} relationships to {out}")


def cmd_evaluate(client, args):
    estate = generate(seed=args.seed, n_apps=args.apps, difficulty=args.difficulty)
    exported = export_estate(client)
    key = lambda c: (c["id"], c["class"], c["name"], c["created"], c["last_seen"], json.dumps(c.get("attrs", {}), sort_keys=True))
    round_trip = sorted(map(key, estate["cis"])) == sorted(map(key, exported["cis"]))
    rel = lambda r: (r["parent"], r["child"], r["type"])
    rels_ok = sorted(map(rel, estate["relationships"])) == sorted(map(rel, exported["relationships"]))
    truth = estate["ground_truth"]
    pairs = find_duplicate_pairs(exported["cis"])
    drift = detect_drift_policy(exported["cis"], estate["baseline"], estate["policy"])
    print(json.dumps({
        "round_trip_cis_identical": round_trip,
        "round_trip_relationships_identical": rels_ok,
        "duplicate_detection_on_instance_data": duplicate_metrics(pairs, truth["duplicate_pairs"]),
        "drift_detection_on_instance_data": drift_metrics(drift, truth["drift"]),
    }, indent=2))
    if not (round_trip and rels_ok):
        print("The data read back from the instance differs from what was generated. "
              "Check field mappings in adapters/servicenow/mapping.py.")


def cmd_cleanup(client, args):
    print(("DRY RUN: nothing is deleted. " if client.dry_run else "") + "Removing project records")
    print(cleanup(client))
    client.summary()
    if client.dry_run:
        print("Add --execute to delete the records this project created.")


COMMANDS = {"check": (cmd_check, False), "load": (cmd_load, True), "export": (cmd_export, False),
            "evaluate": (cmd_evaluate, False), "cleanup": (cmd_cleanup, True)}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python3 -m adapters.servicenow")
    ap.add_argument("command", choices=COMMANDS)
    ap.add_argument("--execute", action="store_true", help="perform writes (default is a dry run)")
    ap.add_argument("--allow-non-pdi", action="store_true",
                    help="allow instances other than dev<digits>.service-now.com")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--apps", type=int, default=100)
    ap.add_argument("--difficulty", choices=["easy", "hard"], default="hard")
    ap.add_argument("--out", default="out/servicenow")
    args = ap.parse_args(argv)
    func, writes = COMMANDS[args.command]
    try:
        func(_client(args, writes), args)
    except (ServiceNowError, RuntimeError, ValueError) as err:
        sys.exit(f"Error: {err}")


if __name__ == "__main__":
    main()
