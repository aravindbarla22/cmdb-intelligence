"""Minimal ServiceNow Table API client (standard library only).

Safety properties:
  * Dry run is the default for writes: requests are printed and nothing is
    sent, and no network access or credentials are needed.
  * Only personal developer instances (dev<digits>.service-now.com) are allowed
    unless explicitly overridden, to keep this away from employer instances.
  * Credentials are never printed.
"""
import base64
import json
import re
import urllib.error
import urllib.parse
import urllib.request

PDI_HOST = re.compile(r"^dev\d+\.service-now\.com$")
SHOW_FIRST = 5  # dry run prints this many requests, then only counts


class ServiceNowError(RuntimeError):
    pass


def normalize_instance(instance, allow_non_pdi=False):
    """Accept "dev12345" or a full https URL and return "https://dev12345.service-now.com"."""
    inst = instance.strip()
    if "://" not in inst:
        inst = f"https://{inst}" if "." in inst else f"https://{inst}.service-now.com"
    parsed = urllib.parse.urlparse(inst)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https":
        raise ValueError("The instance URL must use https.")
    if not allow_non_pdi and not PDI_HOST.match(host):
        raise ValueError(
            f"Refusing to use '{host}': only personal developer instances "
            "(dev<digits>.service-now.com) are allowed. Use --allow-non-pdi to override "
            "only if you own and control that instance.")
    return f"https://{host}"


def urllib_transport(method, url, headers, body):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
            return response.status, dict(response.headers), (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as err:
        raw = err.read()
        try:
            parsed = json.loads(raw) if raw else {}
        except ValueError:
            parsed = {}
        return err.code, dict(err.headers), parsed


class Client:
    def __init__(self, instance=None, user=None, password=None, dry_run=True,
                 transport=None, allow_non_pdi=False, out=print):
        self.dry_run = dry_run
        self.out = out
        self.transport = transport or urllib_transport
        self.counts = {"GET": 0, "POST": 0, "DELETE": 0}
        self._shown = 0
        if instance:
            self.base = normalize_instance(instance, allow_non_pdi)
        elif dry_run:
            self.base = "https://<your-instance>.service-now.com"
        else:
            raise ValueError("No instance configured.")
        if not dry_run and not (user and password):
            raise ValueError("Credentials are required.")
        token = base64.b64encode(f"{user}:{password}".encode()).decode() if user else ""
        self._headers = {"Authorization": f"Basic {token}", "Accept": "application/json",
                         "Content-Type": "application/json"}

    # -- internals -----------------------------------------------------
    def _url(self, table, sys_id=None, params=None):
        url = f"{self.base}/api/now/table/{table}" + (f"/{sys_id}" if sys_id else "")
        return url + ("?" + urllib.parse.urlencode(params) if params else "")

    def _say(self, text):
        self._shown += 1
        if self._shown <= SHOW_FIRST:
            self.out(text)

    def _call(self, method, url, body=None):
        self.counts[method] += 1
        status, headers, data = self.transport(method, url, self._headers, body)
        if status >= 400:
            message = (data.get("error") or {}).get("message", "") if isinstance(data, dict) else ""
            raise ServiceNowError(f"{status} {method} {url.split('?')[0]}: {message}")
        return status, {k.lower(): v for k, v in headers.items()}, data

    # -- reads (skipped in dry run) -------------------------------------
    def get_all(self, table, query="", fields=None, page=500):
        if self.dry_run:
            self.counts["GET"] += 1
            self._say(f"GET {self._url(table, params={'sysparm_query': query})}")
            return []
        rows, offset = [], 0
        while True:
            params = {"sysparm_query": query, "sysparm_limit": page, "sysparm_offset": offset,
                      "sysparm_exclude_reference_link": "true"}
            if fields:
                params["sysparm_fields"] = ",".join(fields)
            _, _, data = self._call("GET", self._url(table, params=params))
            batch = data.get("result", [])
            rows.extend(batch)
            if len(batch) < page:
                return rows
            offset += page

    def count(self, table, query=""):
        if self.dry_run:
            return 0
        params = {"sysparm_query": query, "sysparm_limit": 1, "sysparm_fields": "sys_id"}
        _, headers, data = self._call("GET", self._url(table, params=params))
        return int(headers.get("x-total-count", len(data.get("result", []))))

    # -- writes (printed only in dry run) -------------------------------
    def post(self, table, record):
        if self.dry_run:
            self.counts["POST"] += 1
            self._say(f"POST {self._url(table)}\n  {json.dumps(record, sort_keys=True)}")
            return {"sys_id": f"dryrun-{self.counts['POST']:05d}"}
        _, _, data = self._call("POST", self._url(table), record)
        return data["result"]

    def delete(self, table, sys_id):
        if self.dry_run:
            self.counts["DELETE"] += 1
            self._say(f"DELETE {self._url(table, sys_id)}")
            return
        self._call("DELETE", self._url(table, sys_id))

    def summary(self):
        writes = self.counts["POST"] + self.counts["DELETE"]
        if self.dry_run and writes > SHOW_FIRST:
            self.out(f"... plus {writes - min(writes, SHOW_FIRST)} more requests not shown")
        return dict(self.counts)
