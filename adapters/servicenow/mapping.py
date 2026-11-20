"""Mapping between the canonical CI format and ServiceNow records.

Everything that depends on your instance's schema is defined here so it can be
adjusted in one place. Run `python3 -m adapters.servicenow check` to confirm
the tables and relationship types below exist on your instance.
"""
import json

# Marks records created by this project so they can be found and removed safely.
PREFIX = "cmdbi:"

# Canonical class -> ServiceNow table. Verify against your instance.
TABLES = {
    "business_app": "cmdb_ci_business_app",
    "app_service": "cmdb_ci_service_auto",
    "server": "cmdb_ci_server",
}

# Canonical relationship type -> ServiceNow relationship type name. Verify on your instance.
REL_TYPES = {
    "has_service": "Contains::Contained by",
    "runs_on": "Runs on::Runs",
}

# Server attributes are stored as JSON in this existing field so no schema change
# is needed. A dedicated custom field would be cleaner; change this to use one.
ATTRS_FIELD = "short_description"

CI_FIELDS = ["sys_id", "name", "correlation_id", "install_date", "last_discovered",
             "sys_created_on", ATTRS_FIELD]


def _stamp(day):
    return f"{day} 00:00:00" if day else ""


def to_record(ci):
    """Canonical CI -> ServiceNow record. The creation date is carried in
    install_date because sys_created_on is set by the platform at load time."""
    record = {
        "name": ci["name"],
        "correlation_id": PREFIX + ci["id"],
        "install_date": _stamp(ci.get("created")),
        "last_discovered": _stamp(ci.get("last_seen")),
    }
    if ci.get("attrs"):
        record[ATTRS_FIELD] = json.dumps(ci["attrs"], sort_keys=True)
    return record


def from_record(cls, row):
    """ServiceNow row -> canonical CI."""
    attrs = {}
    raw = row.get(ATTRS_FIELD) or ""
    if raw.startswith("{"):
        try:
            attrs = json.loads(raw)
        except ValueError:
            attrs = {}
    ci = {
        "id": row["correlation_id"][len(PREFIX):],
        "class": cls,
        "name": row.get("name", ""),
        "created": (row.get("install_date") or row.get("sys_created_on") or "")[:10],
        "last_seen": (row.get("last_discovered") or "")[:10],
    }
    if cls == "server":
        ci["attrs"] = attrs
    return ci
