# ServiceNow adapter (planned)

Purpose: move CIs between a ServiceNow instance and the canonical JSON format,
and write proposed fixes back for human approval.

Use a free Personal Developer Instance (PDI) you own. Do not point this at an
employer instance, and do not reuse employer scripts, table names or data.

## Planned work

1. **Load** synthetic CIs into the instance (Table API, or the Identification
   and Reconciliation API, so the platform's own reconciliation can be benchmarked).
2. **Export** CIs and relationships to the canonical format.
3. **Write back** proposals to a custom table in a scoped application.
4. **Approval** through a flow in that application; accepted proposals are applied.

## Things to verify against your own instance and ServiceNow's documentation

Table names, REST endpoints and licensed features vary by release and plan.
Confirm each one in your PDI before relying on it (for example the business
application, server and relationship tables, and which CMDB health and
duplicate-remediation features are available).

Also review the ServiceNow Developer Program terms before publishing code
that interacts with the platform.
