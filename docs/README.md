# RFDB Curator — Documentation

Project documentation for `rfdb-curator`. The root `README.md` remains the entry point
for a quick overview, setup, the API reference, and the configuration variables; these
files go deeper on specific topics. Where any document and the implementation diverge,
the implementation and the active `schema/schema.ttl` take precedence.

| Document | Covers |
|---|---|
| [getting-started.md](getting-started.md) | What the editor is for, the WEMI data model in brief, and how to run it locally and in production. |
| [data-model.md](data-model.md) | RDF/SHACL modeling reference: prefix map, ontologies and vocabularies, per-shape field definitions, and the literal/language/date/IRI policies. |
| [architecture.md](architecture.md) | System design: the schema-driven pipeline, backend/frontend responsibilities, SHACL extraction, validation and delete behavior, the metadata API, and the Oxigraph/Garage storage stack. |
| [development.md](development.md) | Development workflow: environment setup, code quality, CI, schema and data change workflows, troubleshooting, logs, and the commit checklist. |
| [deployment.md](deployment.md) | Production deployment on a single Docker host behind Caddy: prerequisites, environment, build, verification, and ongoing operations. |
| [roadmap.md](roadmap.md) | Planned, not-yet-shipped work — chiefly the Data Context Panel — and short-term implementation priorities. |

The live task list lives in the root `TODO.md`.
