# ServiceNow adapter

Moves the synthetic estate into a ServiceNow instance, reads it back in the
canonical format, and removes it. It uses only the Python standard library.

**Status: not yet run against a real instance.** It is tested against an
in-memory simulation of the Table API (`tests/test_servicenow_adapter.py`).
Passing those tests shows the logic is consistent; it does not prove behavior
on a real instance, whose schema, business rules and licensed features can differ.

## Safety

- Use your own personal developer instance (PDI). Never an employer instance.
- The client only accepts `dev<digits>.service-now.com`. Anything else is refused
  unless you pass `--allow-non-pdi`.
- `load` and `cleanup` are **dry runs by default**: they print requests and send
  nothing. Add `--execute` to write.
- Every record is tagged with `correlation_id` starting `cmdbi:`. Cleanup only
  deletes records with that tag.
- Credentials come from environment variables and are never printed.

## Setup

```bash
export SN_INSTANCE=dev12345        # your instance name
export SN_USER=admin               # your PDI admin user
export SN_PASSWORD='...'           # do not share or commit this
```

On Windows PowerShell use `$env:SN_INSTANCE="dev12345"` and so on.

## Suggested first run

```bash
python3 -m adapters.servicenow load              # dry run, no credentials needed
python3 -m adapters.servicenow check             # read-only: tables and relationship types exist?
python3 -m adapters.servicenow load --execute    # writes the synthetic estate
python3 -m adapters.servicenow evaluate          # reads it back, checks the round trip, scores detectors
python3 -m adapters.servicenow cleanup           # dry run of removal
python3 -m adapters.servicenow cleanup --execute # removes only records tagged cmdbi:
```

`--seed`, `--apps` and `--difficulty` must match between `load` and `evaluate`.

## What to verify on your instance

Everything instance-specific is in `adapters/servicenow/mapping.py`:

| Setting | Default | Check |
| --- | --- | --- |
| Business application table | `cmdb_ci_business_app` | `check` shows a count |
| Application service table | `cmdb_ci_service_auto` | Confirm this is the table you use for application services |
| Server table | `cmdb_ci_server` | `check` shows a count |
| Relationship types | `Contains::Contained by`, `Runs on::Runs` | `check` reports found or MISSING |
| Attribute storage | JSON in `short_description` | A custom field is cleaner |
| Created date | `install_date` | `sys_created_on` is set by the platform at load time |

If `evaluate` reports that the round trip differs, a field is probably being
ignored or rewritten by your instance. Tell me what it prints and we will fix
the mapping.

## Notes

- Records are created through the Table API, which does not run the
  Identification and Reconciliation Engine. That is intentional: duplicates
  are loaded as-is so detection can be compared with the platform's own tools.
- Check the ServiceNow Developer Program terms before publishing anything that
  interacts with the platform.
