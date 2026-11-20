"""Load the synthetic estate into ServiceNow, read it back, and clean it up.

Records are tagged with a correlation_id prefix so cleanup only ever touches
records created by this project.
"""
from .mapping import (CI_FIELDS, PREFIX, REL_TYPES, TABLES, from_record, to_record)

_TAG = f"correlation_idSTARTSWITH{PREFIX}"


def existing_count(client):
    return sum(client.count(table, _TAG) for table in TABLES.values())


def _rel_type_ids(client):
    ids = {}
    for key, name in REL_TYPES.items():
        if client.dry_run:
            ids[key] = f"dryrun-reltype-{key}"
            continue
        rows = client.get_all("cmdb_rel_type", f"name={name}", ["sys_id", "name"])
        if not rows:
            raise RuntimeError(f"Relationship type '{name}' was not found on this instance. "
                               "Update REL_TYPES in adapters/servicenow/mapping.py.")
        ids[key] = rows[0]["sys_id"]
    return ids


def load_estate(client, estate):
    if not client.dry_run and existing_count(client):
        raise RuntimeError("Synthetic records already exist on this instance. "
                           "Run the cleanup command first.")
    sys_ids = {}
    for ci in estate["cis"]:
        sys_ids[ci["id"]] = client.post(TABLES[ci["class"]], to_record(ci))["sys_id"]
    type_ids = _rel_type_ids(client)
    for rel in estate["relationships"]:
        client.post("cmdb_rel_ci", {"parent": sys_ids[rel["parent"]],
                                    "child": sys_ids[rel["child"]],
                                    "type": type_ids[rel["type"]]})
    return {"cis": len(estate["cis"]), "relationships": len(estate["relationships"])}


def export_estate(client):
    cis = []
    for cls, table in TABLES.items():
        for row in client.get_all(table, _TAG, CI_FIELDS):
            cis.append(from_record(cls, row))
    by_name = {name: key for key, name in REL_TYPES.items()}
    rels = []
    query = f"parent.correlation_idSTARTSWITH{PREFIX}"
    fields = ["parent.correlation_id", "child.correlation_id", "type.name"]
    for row in client.get_all("cmdb_rel_ci", query, fields):
        rel_type = by_name.get(row.get("type.name"))
        if rel_type and row.get("child.correlation_id"):
            rels.append({"parent": row["parent.correlation_id"][len(PREFIX):],
                         "child": row["child.correlation_id"][len(PREFIX):],
                         "type": rel_type})
    return {"cis": cis, "relationships": rels}


def cleanup(client):
    removed = {"relationships": 0, "cis": 0}
    rel_query = f"parent.correlation_idSTARTSWITH{PREFIX}^ORchild.correlation_idSTARTSWITH{PREFIX}"
    for row in client.get_all("cmdb_rel_ci", rel_query, ["sys_id"]):
        client.delete("cmdb_rel_ci", row["sys_id"])
        removed["relationships"] += 1
    for table in TABLES.values():
        for row in client.get_all(table, _TAG, ["sys_id"]):
            client.delete(table, row["sys_id"])
            removed["cis"] += 1
    return removed
