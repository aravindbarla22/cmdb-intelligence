# ServiceNow scoped application (planned)

Contents to build in your own PDI:

- A table for proposed fixes (type, target CIs, evidence, status).
- An approval flow so a person accepts or rejects each proposal.
- A scripted REST endpoint that receives proposals from the core engine.

Keep the machine-learning logic in the core engine. Put only deterministic,
platform-specific glue in this application.
