"""Tests for the ServiceNow adapter against an in-memory simulation of the Table API.

The simulation only implements what the adapter uses. Passing these tests shows
the adapter's logic is consistent; it does not prove behavior on a real
instance, whose schema and rules can differ.
"""
import io
import unittest
import urllib.parse

from adapters.servicenow.client import Client, ServiceNowError, normalize_instance
from adapters.servicenow.mapping import PREFIX, REL_TYPES, TABLES
from adapters.servicenow.sync import cleanup, export_estate, existing_count, load_estate
from core.drift import detect_drift_policy
from core.match import find_duplicate_pairs
from data.synth import generate
from eval.metrics import drift_metrics, duplicate_metrics


class FakeServiceNow:
    """Callable transport that behaves like a tiny Table API."""

    def __init__(self):
        self.tables = {t: {} for t in list(TABLES.values()) + ["cmdb_rel_ci", "cmdb_rel_type"]}
        for i, name in enumerate(REL_TYPES.values()):
            self.tables["cmdb_rel_type"][f"rt{i}"] = {"sys_id": f"rt{i}", "name": name}
        self.n = 0
        self.calls = 0

    def _ci(self, sys_id):
        for table in TABLES.values():
            if sys_id in self.tables[table]:
                return self.tables[table][sys_id]
        return {}

    def _select(self, table, query):
        rows = list(self.tables[table].values())
        if table == "cmdb_rel_type":
            return [r for r in rows if r["name"] == query.split("=", 1)[1]]
        if table == "cmdb_rel_ci":
            def tagged(r):
                parent = self._ci(r["parent"]).get("correlation_id", "")
                child = self._ci(r["child"]).get("correlation_id", "")
                if "^OR" in query:
                    return parent.startswith(PREFIX) or child.startswith(PREFIX)
                return parent.startswith(PREFIX)
            return [r for r in rows if tagged(r)]
        return [r for r in rows if r.get("correlation_id", "").startswith(PREFIX)]

    def _project(self, table, row, fields):
        out = {}
        for field in fields or []:
            if field == "parent.correlation_id":
                out[field] = self._ci(row["parent"]).get("correlation_id", "")
            elif field == "child.correlation_id":
                out[field] = self._ci(row["child"]).get("correlation_id", "")
            elif field == "type.name":
                out[field] = self.tables["cmdb_rel_type"][row["type"]]["name"] if row["type"] in self.tables["cmdb_rel_type"] else ""
            else:
                out[field] = row.get(field, "")
        return out

    def __call__(self, method, url, headers, body):
        self.calls += 1
        parsed = urllib.parse.urlparse(url)
        parts = parsed.path.strip("/").split("/")
        table = parts[3]
        params = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
        if method == "POST":
            self.n += 1
            sys_id = f"id{self.n:05d}"
            self.tables[table][sys_id] = dict(body, sys_id=sys_id)
            return 201, {}, {"result": {"sys_id": sys_id}}
        if method == "DELETE":
            self.tables[table].pop(parts[4], None)
            return 204, {}, {}
        rows = self._select(table, params.get("sysparm_query", ""))
        limit, offset = int(params["sysparm_limit"]), int(params.get("sysparm_offset", 0))
        fields = params.get("sysparm_fields", "").split(",") if params.get("sysparm_fields") else None
        page = rows[offset:offset + limit]
        return 200, {"X-Total-Count": str(len(rows))}, {"result": [self._project(table, r, fields) for r in page]}


def make_client(fake, **kwargs):
    return Client("dev12345", "user", "secret", dry_run=False, transport=fake, **kwargs)


class AdapterTests(unittest.TestCase):
    def test_only_personal_developer_instances_are_allowed(self):
        self.assertEqual(normalize_instance("dev12345"), "https://dev12345.service-now.com")
        self.assertEqual(normalize_instance("https://dev987.service-now.com/"),
                         "https://dev987.service-now.com")
        for bad in ("acme", "https://acme.service-now.com", "http://dev1.service-now.com"):
            with self.assertRaises(ValueError):
                normalize_instance(bad)
        self.assertEqual(normalize_instance("acme", allow_non_pdi=True),
                         "https://acme.service-now.com")

    def test_dry_run_sends_nothing_and_needs_no_credentials(self):
        def boom(*args):
            raise AssertionError("network used in dry run")
        out = io.StringIO()
        client = Client(dry_run=True, transport=boom, out=lambda s: out.write(s + "\n"))
        summary = load_estate(client, generate(seed=1))
        self.assertEqual(summary["cis"], len(generate(seed=1)["cis"]))
        self.assertIn("POST", out.getvalue())
        self.assertNotIn("secret", out.getvalue())

    def test_round_trip_preserves_the_estate(self):
        for difficulty in ("easy", "hard"):
            estate = generate(seed=42, difficulty=difficulty)
            fake = FakeServiceNow()
            client = make_client(fake)
            load_estate(client, estate)
            exported = export_estate(client)
            key = lambda c: (c["id"], c["class"], c["name"], c["created"], c["last_seen"], sorted(c.get("attrs", {}).items()))
            self.assertEqual(sorted(map(key, estate["cis"])), sorted(map(key, exported["cis"])))
            rel = lambda r: (r["parent"], r["child"], r["type"])
            self.assertEqual(sorted(map(rel, estate["relationships"])),
                             sorted(map(rel, exported["relationships"])))

    def test_detection_results_match_after_round_trip(self):
        estate = generate(seed=42, difficulty="hard")
        fake = FakeServiceNow()
        client = make_client(fake)
        load_estate(client, estate)
        exported = export_estate(client)
        truth = estate["ground_truth"]
        local = duplicate_metrics(find_duplicate_pairs(estate["cis"]), truth["duplicate_pairs"])
        remote = duplicate_metrics(find_duplicate_pairs(exported["cis"]), truth["duplicate_pairs"])
        self.assertEqual(local, remote)
        d = drift_metrics(detect_drift_policy(exported["cis"], estate["baseline"], estate["policy"]), truth["drift"])
        self.assertEqual((d["precision"], d["recall"]), (1.0, 1.0))

    def test_load_refuses_when_records_already_exist(self):
        fake = FakeServiceNow()
        client = make_client(fake)
        load_estate(client, generate(seed=1))
        with self.assertRaises(RuntimeError):
            load_estate(client, generate(seed=1))

    def test_cleanup_removes_only_project_records(self):
        fake = FakeServiceNow()
        fake.tables["cmdb_ci_server"]["keep1"] = {"sys_id": "keep1", "name": "prod-db", "correlation_id": "other:1"}
        client = make_client(fake)
        load_estate(client, generate(seed=1))
        removed = cleanup(client)
        self.assertGreater(removed["cis"], 0)
        self.assertEqual(existing_count(client), 0)
        self.assertIn("keep1", fake.tables["cmdb_ci_server"])
        self.assertEqual(len(fake.tables["cmdb_rel_ci"]), 0)

    def test_missing_relationship_type_gives_a_clear_error(self):
        fake = FakeServiceNow()
        fake.tables["cmdb_rel_type"].clear()
        with self.assertRaises(RuntimeError) as ctx:
            load_estate(make_client(fake), generate(seed=1))
        self.assertIn("REL_TYPES", str(ctx.exception))

    def test_http_errors_raise_without_leaking_credentials(self):
        def deny(method, url, headers, body):
            return 401, {}, {"error": {"message": "User Not Authenticated"}}
        client = Client("dev1", "user", "secret", dry_run=False, transport=deny)
        with self.assertRaises(ServiceNowError) as ctx:
            client.count("cmdb_ci_server")
        self.assertNotIn("secret", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
