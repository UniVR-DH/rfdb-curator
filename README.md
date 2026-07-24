# RFDB Curator

Standalone SHACL-driven curation application.
Forms are generated dynamically and automatically from the active SHACL schema, so **the schema is the source of truth** for record types, fields, constraints, datatypes, and relations. 
Swap the schema and the whole editor follows — see [The Schema](#the-schema).
The web application provides shape-aware CRUD, validation, autocomplete, and record inspection for RDF instance data.

The current use case is the curation of `RossijskijFeatrDB`, developed within the [Rossiysky Θeatr: Music Sources of the Russian Empire](https://rosfeatr.eu/) project.
The current schema features record types for musical works, expressions, manifestations, sources/items, digital copies, persons, roles, agent-role assignments, places, subjects, source types, holding organizations, performances, and controlled-vocabulary languages.
[SHACL shapes](https://www.w3.org/TR/shacl12-core/) are aligned with the [Polifonia Core Ontology](https://github.com/polifonia-project/core-ontology) and [LRMoo](https://cidoc-crm.org/lrmoo/) to support the FRBR-based work–expression–manifestation–item (WEMI) hierarchy.


This repository is self-contained: backend, frontend, schema, data, and the Docker Compose runtime are all maintained at the repository root.
For deeper topic guides, see the [documentation](#documentation).


---

## Core Features

- Dynamic form generation from SHACL `sh:NodeShape` definitions
- Shape-aware create, read, update, and delete operations
- RDF instance data stored in [Oxigraph](https://github.com/oxigraph/oxigraph)
- SHACL validation with [pySHACL](https://github.com/RDFLib/pySHACL)
- Autocomplete for linked RDF resources
- Record inspection through RDF triples
- Controlled-vocabulary seeding from Turtle files
- Digital-copy uploads (e.g. PDF scans) held in S3-compatible object storage, with RDF as the source of truth
- Docker Compose deployment

## Tech Stack

- **Backend:** [FastAPI](https://fastapi.tiangolo.com/) + [uvicorn](https://uvicorn.dev/)
- **Frontend:** [React](https://react.dev/) + [Vite](https://vite.dev/)
- **RDF Store:** [Oxigraph](https://github.com/oxigraph/oxigraph), using [SPARQL](https://www.w3.org/TR/sparql11-query/) and [Graph Store Protocol](https://www.w3.org/TR/sparql11-http-rdf-update/)
- **Object Storage:** [Garage](https://garagehq.deuxfleurs.fr/) (S3-compatible), via [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) — holds digital-copy files
- **Validation:** [pySHACL](https://github.com/RDFLib/pySHACL)
- **RDF/Data Model:** [rdflib](https://rdflib.readthedocs.io/), [Turtle](https://www.w3.org/TR/turtle/), [JSON-LD](https://www.w3.org/TR/json-ld11/)
- **Runtime:** [Docker Compose](https://docs.docker.com/compose/)

---

## Quick Start

### Prerequisites

- Docker
- Docker Compose
- OpenSSL (for the one-time secret generation step below)

### First-time setup

The stack needs a repo-root `.env` (Garage RPC secret + the S3 credentials shared by Garage and the backend) and a one-time Garage bootstrap (cluster layout, bucket, access key). 
Both are handled by helper scripts. `.env` is gitignored, so a fresh checkout has none.
Compose fails at startup if `GARAGE_RPC_SECRET` is missing, while uploads fail until Garage is bootstrapped.

From the repository root:

```bash
# 1. Generate .env with fresh dev secrets (refuses to clobber an existing .env)
scripts/env-init.sh

# 2. Build and start the stack
docker compose up -d --build

# 3. Bootstrap Garage — run ONCE, after the first `up` (and again after any `down -v`)
scripts/garage-init.sh
```

Both scripts are idempotent and documented in their file headers.

### Run

Once set up, ordinary runs need only Compose:

```bash
# First run of a session or after Dockerfile changes
docker compose up --build

# Subsequent runs
docker compose up
```

Stop services:

```bash
docker compose down
```

Remove volumes and clear all data (destructive — wipes Oxigraph triples **and** Garage layout/bucket/key). After this you must re-run `scripts/garage-init.sh`:

```bash
docker compose down -v
```

### Service URLs

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend | http://localhost:8000 |
| Oxigraph | http://localhost:7878 |
| Garage (S3 API) | http://localhost:3900 |

Startup seeding, data-reset modes, and the full environment-variable reference live in the [development & testing deployment guide](docs/deployment.md#development--testing-deployment).

---

## The Schema

The active SHACL schema lives in `schema/schema.ttl` and is the single source of truth: every record type, form field, constraint, datatype, and relation is derived from it at runtime. **To experiment with a different model, replace `schema/schema.ttl`** (or repoint `SCHEMA_PATH`) — forms, validation, and the record-type list all follow automatically, with no code changes.

### Data Model

The active model uses [LRMoo](https://cidoc-crm.org/lrmoo/) (rather than the older FRBR/FaBiO model) and draws on [LRMoo](https://cidoc-crm.org/lrmoo/), [CIDOC CRM](https://cidoc-crm.org/), the Polifonia [Core](https://github.com/polifonia-project/core-ontology) / [Music Meta](https://github.com/polifonia-project/music-meta-ontology) / [Source](https://github.com/polifonia-project/source-ontology) ontologies, [Dublin Core Terms](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/), [PRISM](https://www.w3.org/submissions/prism/), [SKOS](https://www.w3.org/TR/skos-reference/), [FOAF](http://xmlns.com/foaf/spec/), [Schema.org](https://schema.org/), [Wikidata](https://www.wikidata.org/) direct properties, and RDF/RDFS/OWL/XSD.

LRMoo hierarchy: a **Musical Work** is the abstract work; an **Expression** is an intellectual realization (e.g. a libretto); a **Manifestation** is an edition or product type; a **Source / Item** is a specific physical or documentary copy. Each level refines the one above it, from Work through Expression and Manifestation to Source/Item, and every WEMI link points from the more concrete record up to its parent — so create parents before children.

### Main SHACL Shapes

The current schema includes these primary record types:

- `rfdbs:MusicalWorkShape`: musical work, targeting `mm:MusicEntity`, constrained as `lrmoo:F1_Work`
- `rfdbs:ExpressionShape`: expression, targeting `lrmoo:F2_Expression`
- `rfdbs:ManifestationShape`: manifestation, targeting `lrmoo:F3_Manifestation`
- `rfdbs:SourceShape`: source/item, targeting `source:Source` and `lrmoo:F5_Item`
- `rfdbs:DigitalCopyShape`: digital copy (PDF scan) of a source, targeting `schema:DigitalDocument` (helper shape, managed via the file-upload panel)
- `rfdbs:PersonShape`: person, targeting `core:Person`
- `rfdbs:RoleShape`: role, targeting `core:Role`
- `rfdbs:AgentRoleShape`: agent-role assignment, targeting `core:AgentRole`
- `rfdbs:PlaceShape`: place, targeting `core:Place`
- `rfdbs:SubjectShape`: subject, targeting `cidoc:E89_Propositional_Object`
- `rfdbs:SourceTypeShape`: source type, targeting `core:Type`
- `rfdbs:HoldingOrganizationShape`: holding organization, targeting `core:Organization`
- `rfdbs:ContributorShape`: donor/contributor record for digital-copy provenance
- `rfdbs:PerformanceShape`: staged performance, targeting `lrmoo:F31_Performance`
- `rfdbs:LanguageShape`: controlled-vocabulary language record, targeting `dcterms:LinguisticSystem` (seeded from Glottolog, see [Data Seeding](docs/deployment.md#data-seeding))

### Form Generation

Each `sh:NodeShape` becomes a form type and each `sh:property` becomes a form field. The generator derives required fields from `sh:minCount`, cardinality from `sh:maxCount`, datatypes from `sh:datatype`, IRI-valued fields from `sh:nodeKind`, linked target classes from `sh:class`, nested forms from `sh:node`, alternatives from `sh:or`, fixed values from `sh:hasValue`, help text from `sh:description`, and closed-shape behavior from `sh:closed`.

Shapes with a `sh:property` on `rdfs:label` are treated as standalone entities; shapes without one are helper/bridge nodes rendered inline when referenced by a parent (e.g. `rfdbs:AgentRoleShape`). Shapes whose shape-level `sh:or` branches into multiple `sh:class` alternatives (e.g. `rfdbs:ContributorShape`, `foaf:Person` or `foaf:Organization`) surface a type-selection dropdown at creation time.

> Modeling principles and design decisions — the vocabularies used and for what, WEMI layering and link direction, the Agent Role bridge pattern, and the literal/language/date/IRI policies — are in [docs/data-model.md](docs/data-model.md). Per-shape fields and cardinalities live in the schema itself (`schema/schema.ttl`, or `GET /api/shapes`). The schema-driven extraction and validation pipeline is described in [docs/architecture.md](docs/architecture.md).

---

## Configuration

All backend settings are loaded from environment variables; the backend fails fast if a required variable is missing or malformed. The source of truth is the `environment:` block in `docker-compose.yml`, the settings model in `backend/core/config.py`, and `backend/pyproject.toml`.

The full environment-variable reference, data-reset modes, and seed sources (controlled vocabulary + Glottolog languages) are documented in the [development & testing deployment guide](docs/deployment.md#development--testing-deployment). Production deployment is **work in progress** — see [docs/deployment.md](docs/deployment.md#production-deployment-work-in-progress).

---

## API Reference

The backend is FastAPI, so the complete, always-current reference is generated from the running app. With the stack up, open **<http://localhost:8000/docs>** for interactive Swagger UI (raw schema at `/openapi.json`).

The core of the schema-driven pipeline is just a handful of endpoints:

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/shapes` | Available SHACL NodeShapes with metadata and field descriptors |
| `GET` | `/api/forms?shapeId=...` | Generated form schema for one shape |
| `POST` | `/api/data` | Create or update an entity (JSON-LD → SHACL validate → Turtle load) |
| `POST` | `/api/validate` | Dry-run SHACL validation without persisting |
| `GET` | `/api/data/{entityId}` | All triples for one entity |

The full endpoint table (data listing, autocomplete, file staging, and the metadata API) is in [docs/architecture.md](docs/architecture.md#api-reference).

---

## Documentation

The root README is the entry point (overview, setup, schema, API, configuration). These topic guides go deeper; where any document and the implementation diverge, the implementation and the active `schema/schema.ttl` take precedence.

| Document | Covers |
|---|---|
| [docs/getting-started.md](docs/getting-started.md) | What the editor is for, the WEMI data model in brief, and how to run it locally and in production. |
| [docs/data-model.md](docs/data-model.md) | Modeling principles and design decisions: the vocabularies used and for what, WEMI layering, the bridge-node pattern, and the literal/language/date/IRI policies. Per-shape fields live in `schema/schema.ttl`. |
| [docs/architecture.md](docs/architecture.md) | System design: the schema-driven pipeline, backend/frontend responsibilities, the API endpoint reference, SHACL extraction, validation and delete behavior, the metadata API, and the storage stack. |
| [docs/development.md](docs/development.md) | Development workflow: environment setup, code quality, CI, schema and data change workflows, troubleshooting, and the commit checklist. |
| [docs/deployment.md](docs/deployment.md) | Deployment & operations: the development/testing configuration, data-reset modes, and seed sources; plus the production deployment plan and its work-in-progress status. |

The live task list lives in the root `TODO.md`.

---

## Repository Structure

```text
rfdb-curator/
├── backend/
│   ├── api/                      # Route handlers (data, entities, files, shapes, validate, meta)
│   ├── core/                     # Core services (config, Oxigraph client, schema extractor,
│   │                             #   SHACL validator, validation merge, seeder, file storage)
│   ├── models/                   # Pydantic request/response schemas
│   ├── app.py                    # FastAPI app + lifespan (startup seeding + settings init)
│   ├── Dockerfile
│   └── pyproject.toml
│
├── frontend/
│   ├── src/                      # React components, API client, JSON-LD/prefix utils
│   ├── Dockerfile
│   ├── vite.config.js            # Dev server + proxy config (/api → backend:8000)
│   └── package.json
│
├── schema/schema.ttl             # Active SHACL schema (source of truth)
├── data/                         # vocab.ttl (controlled vocabulary) + data.ttl (test fixtures)
├── docs/                         # Topic documentation (see the Documentation section)
├── docker-compose.yml
├── garage.toml                   # Object-storage (Garage) configuration
├── scripts/                      # Host-side helpers (garage-init.sh, env-init.sh)
├── AGENTS.md / .agent-defs/      # Agent instructions
├── tests/                        # Backend/API validation and integration tests
├── TODO.md
└── README.md
```

---

## Copyright & License

Copyright © 2026 University of Verona — Digital Humanities.

Developed within the [Rossiysky Θeatr: Music Sources of the Russian Empire](https://rosfeatr.eu/) project.

This program is free software: you can redistribute it and/or modify it under the terms of the [GNU General Public License v3.0](LICENSE) as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version. This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the [LICENSE](LICENSE) file for the full text.
