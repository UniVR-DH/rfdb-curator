# RFDB Curator

Standalone SHACL-driven curation application for RossijskijFeatrDB.
[SHACL shapes](https://www.w3.org/TR/shacl12-core/) are aligned with the Polifonia Core Ontology and LRMoo to support the FRBR-based work–expression–manifestation–item (WEMI) hierarchy.
The web application provides shape-aware CRUD, validation, autocomplete, and record inspection for RDF instance data.

Forms are generated dynamically and automatically from the active SHACL schema, so **the schema is the source of truth** for record types, fields, constraints, datatypes, and relations. Swap the schema and the whole editor follows — see [The Schema](#the-schema).

This repository is self-contained: backend, frontend, schema, data, and the Docker Compose runtime are all maintained at the repository root. For deeper topic guides, see the [documentation](#documentation).

---

## Core Features

- Dynamic form generation from SHACL `sh:NodeShape` definitions
- Shape-aware create, read, update, and delete operations
- RDF instance data stored in Oxigraph
- SHACL validation with pySHACL
- Autocomplete for linked RDF resources
- Record inspection through RDF triples
- Controlled-vocabulary seeding from Turtle files
- Digital-copy uploads (e.g. PDF scans) held in S3-compatible object storage, with RDF as the source of truth
- Docker Compose deployment

## Tech Stack

- **Backend:** FastAPI + uvicorn
- **Frontend:** React + Vite
- **RDF Store:** Oxigraph, using SPARQL and Graph Store Protocol
- **Object Storage:** Garage (S3-compatible), via boto3 — holds digital-copy files
- **Validation:** pySHACL
- **RDF/Data Model:** rdflib, Turtle, JSON-LD
- **Runtime:** Docker Compose

---

## Quick Start

### Prerequisites

- Docker
- Docker Compose

### Run

From the repository root:

```bash
# First run or after Dockerfile changes
docker compose up --build

# Subsequent runs
docker compose up
```

Stop services:

```bash
docker compose down
```

Remove volumes and clear all Oxigraph data (destructive):

```bash
docker compose down -v
```

### Data Reset Modes

Startup behavior is controlled by `RESET_DATA_ON_STARTUP`.

**Clean slate (empty store)** — clears all triples from `DATA_GRAPH_URI` before seeding.

```bash
RESET_DATA_ON_STARTUP=true docker compose up --build
```

**Preserve existing data (default)** — keeps existing triples and merges new seed data on top.

```bash
docker compose up --build
```

In both modes, the controlled vocabulary from `data/vocab.ttl` is loaded on every startup (idempotent) when `SEED_VOCAB_ON_STARTUP=true`.
Test fixture data from `data/data.ttl` is loaded only when `SEED_TEST_DATA_ON_STARTUP=true` (off by default outside test environments).

These and all other startup settings are listed under [Configuration](#configuration); seed sources are detailed under [Data Seeding](#data-seeding).

### Service URLs

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend | http://localhost:8000 |
| Oxigraph | http://localhost:7878 |

---

## The Schema

The active SHACL schema lives in `schema/schema.ttl` and is the single source of truth: every record type, form field, constraint, datatype, and relation is derived from it at runtime. **To experiment with a different model, replace `schema/schema.ttl`** (or repoint `SCHEMA_PATH`) — forms, validation, and the record-type list all follow automatically, with no code changes.

### Data Model

The active model uses LRMoo (rather than the older FRBR/FaBiO model) and draws on LRMoo, CIDOC CRM, the Polifonia Core / Music Meta / Source ontologies, Dublin Core Terms, PRISM, SKOS, FOAF, Schema.org, Wikidata direct properties, and RDF/RDFS/OWL/XSD.

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
- `rfdbs:LanguageShape`: controlled-vocabulary language record, targeting `dcterms:LinguisticSystem` (seeded from Glottolog, see [Data Seeding](#data-seeding))

### Form Generation

Each `sh:NodeShape` becomes a form type and each `sh:property` becomes a form field. The generator derives required fields from `sh:minCount`, cardinality from `sh:maxCount`, datatypes from `sh:datatype`, IRI-valued fields from `sh:nodeKind`, linked target classes from `sh:class`, nested forms from `sh:node`, alternatives from `sh:or`, fixed values from `sh:hasValue`, help text from `sh:description`, and closed-shape behavior from `sh:closed`.

Shapes with a `sh:property` on `rdfs:label` are treated as standalone entities; shapes without one are helper/bridge nodes rendered inline when referenced by a parent (e.g. `rfdbs:AgentRoleShape`). Shapes whose shape-level `sh:or` branches into multiple `sh:class` alternatives (e.g. `rfdbs:ContributorShape`, `foaf:Person` or `foaf:Organization`) surface a type-selection dropdown at creation time.

> Full modeling reference — per-shape fields, the prefix map, literal/language/date/IRI policies, and modeling patterns (WEMI editorial order, Agent Role, Performance, Donor/Contributor) — is in [docs/data-model.md](docs/data-model.md). The schema-driven extraction and validation pipeline is described in [docs/architecture.md](docs/architecture.md).

---

## Configuration

All backend settings are loaded from environment variables. No defaults are hardcoded in the Python source; the backend fails fast with a clear validation error if a required variable is missing or has the wrong type.

Configuration source of truth:

- Runtime wiring: `docker-compose.yml`
- Backend settings model: `backend/core/config.py`
- Backend dependency set: `backend/pyproject.toml`

For Docker Compose, edit the `environment:` block in `docker-compose.yml`. `OXIGRAPH_URL` uses the Docker-internal hostname since backend and store are separate services; `SCHEMA_PATH`/`VOCAB_PATH`/`DATA_PATH` are container paths backed by the `volumes:` mounts (change both together).

| Variable | Required | Description |
|---|---|---|
| `OXIGRAPH_URL` | Yes | Base URL of the Oxigraph HTTP endpoint, no trailing slash. `http://localhost:7878` locally, `http://oxigraph:7878` inside Docker. |
| `DATA_GRAPH_URI` | Yes | Named graph URI where instance data is stored and queried. Every SPARQL read uses `FROM <uri>`; every Turtle load targets `?graph=<uri>`. |
| `SCHEMA_PATH` | Yes | Path to `schema.ttl` relative to the backend working directory. Docker mounts it at `/app/schema/schema.ttl`. |
| `VOCAB_PATH` | Yes | Path to `vocab.ttl` (controlled-vocabulary seed). Loaded at startup when `SEED_VOCAB_ON_STARTUP=true`. |
| `DATA_PATH` | Yes | Path to `data.ttl` (test fixture data). Loaded at startup only when `SEED_TEST_DATA_ON_STARTUP=true`. |
| `RESET_DATA_ON_STARTUP` | Yes | `true`/`false`. Destructive: clears the named graph before seeding on every startup. Must be `false` in production. |
| `SEED_VOCAB_ON_STARTUP` | Yes | `true`/`false`. Load `VOCAB_PATH` on every startup. Should be `true` in all environments. |
| `SEED_TEST_DATA_ON_STARTUP` | Yes | `true`/`false`. Load `DATA_PATH` on startup. `true` in dev/test only. |
| `READ_ONLY` | No | `true`/`false`. When `true`, rejects `POST /api/data` and `DELETE /api/data/{entityId}` with HTTP 403 while keeping read endpoints available. Default: `false`. |
| `READ_ONLY_SHAPES` | No | JSON array string of shape IRIs to protect from create/update/delete even when `READ_ONLY` is `false`, e.g. `["https://rosfeatr.eu/rdf/schema/LanguageShape"]`. Default: `[]`. |
| `CORS_ORIGINS` | Yes | JSON array string of allowed CORS origins, e.g. `["http://localhost:5173"]`. |
| `LOG_FILE` | No | Path to the JSON-lines log file. Default: `logs/app.jsonl`. Parent directory created automatically. |
| `LOG_LEVEL` | No | Minimum log level for file and console handlers. Default: `INFO`. One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |

Backend log/troubleshooting details are covered in [docs/development.md](docs/development.md); production wiring (Caddy, `docker-compose.prod.yml`) is in [docs/deployment.md](docs/deployment.md).

---

## Data Seeding

The application distinguishes between controlled vocabulary and test fixture data. Default policy: seed vocabulary on, seed test data off, preserve existing data on.

- `data/vocab.ttl` is the canonical seed source for controlled vocabulary (core types and role types).
- `dcterms:LinguisticSystem` vocabulary relies on [Glottolog v5.3](https://glottolog.org/meta/downloads) data, imported from `data/glottolog_language.ttl`. Prefix normalization is already applied to the committed file. Only if you re-download a fresh version from glottolog.org, replace `geo1:` with `geo:`:

  ```bash
  sed -i '' 's/geo1:/geo:/g' data/glottolog_language.ttl
  ```

- `data/data.ttl` is test-only fixture data.

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness/readiness check (Oxigraph status + seed report) |
| `GET` | `/api/shapes` | Available SHACL NodeShapes with metadata and field descriptors |
| `GET` | `/api/forms?shapeId=...` | Generated form schema for one shape |
| `GET` | `/api/data/list` | Paginated entity list for a shape, with text filter |
| `GET` | `/api/data/counts` | Per-shape entity counts |
| `GET` | `/api/data/{entityId}` | All triples for one entity |
| `POST` | `/api/data` | Create or update an entity (JSON-LD → SHACL validate → Turtle load) |
| `DELETE` | `/api/data/{entityId}` | Delete triples where the entity is subject |
| `GET` | `/api/entities/search` | Autocomplete for linked-resource fields |
| `POST` | `/api/validate` | Dry-run SHACL validation without persisting |
| `POST` | `/api/files/staged` | Stage an uploaded digital copy (e.g. a PDF) before it is attached to a record |
| `GET` | `/api/files/{fileId}` | Fetch a staged or registered digital-copy file |
| `GET` | `/api/meta/prefixes` | Curated CURIE prefix-to-namespace map (from `core/prefixes.py`) |
| `GET` | `/api/meta/graphs` | Named graphs with triple/term counts and advisory config warnings |
| `GET` | `/api/meta/files` | Digital-copy storage stats (staged/registered/orphans) |

`GET /health` returns `{ "status": "ok", "oxigraph": "up" | "down", "seed": { ... } | null }`.

---

## Documentation

The root README is the entry point (overview, setup, schema, API, configuration). These topic guides go deeper; where any document and the implementation diverge, the implementation and the active `schema/schema.ttl` take precedence.

| Document | Covers |
|---|---|
| [docs/getting-started.md](docs/getting-started.md) | What the editor is for, the WEMI data model in brief, and how to run it locally and in production. |
| [docs/data-model.md](docs/data-model.md) | RDF/SHACL modeling reference: prefix map, ontologies, per-shape field definitions, and the literal/language/date/IRI policies. |
| [docs/architecture.md](docs/architecture.md) | System design: the schema-driven pipeline, backend/frontend responsibilities, SHACL extraction, validation and delete behavior, the metadata API, and the storage stack. |
| [docs/development.md](docs/development.md) | Development workflow: environment setup, code quality, CI, schema and data change workflows, troubleshooting, and the commit checklist. |
| [docs/deployment.md](docs/deployment.md) | Production deployment on a single Docker host behind Caddy. |
| [docs/roadmap.md](docs/roadmap.md) | Planned, not-yet-shipped work and short-term priorities. |

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
