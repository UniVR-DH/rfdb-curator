# RFDB Curator

Standalone SHACL-driven curation application for RossijskijFeatrDB. 
[SHACL shapes](https://www.w3.org/TR/shacl12-core/) are aligned with the Polifonia Core Ontology and LRMoo, and the application is designed to support the FRBR-based work-expression-manifestation-item hierarchy.
The web application provides shape-aware CRUD, validation, autocomplete, and record inspection for RDF instance data.

Forms are generated dynamically and automatically from the active SHACL schema, so the schema is the source of truth for record types, fields, constraints, datatypes, and relations.

This repository is self-contained: backend, frontend, schema, data, and Docker Compose runtime are all maintained at the repository root.

---

## Core Features

- Dynamic form generation from SHACL `sh:NodeShape` definitions
- Shape-aware create, read, update, and delete operations
- RDF instance data stored in Oxigraph
- SHACL validation with pySHACL
- Autocomplete for linked RDF resources (TODO)
- Record inspection through RDF triples
- Controlled-vocabulary seeding from Turtle files
- Docker Compose deployment

---

## Tech Stack

- **Backend:** FastAPI + uvicorn
- **Frontend:** React + Vite
- **RDF Store:** Oxigraph, using SPARQL and Graph Store Protocol
- **Validation:** pySHACL
- **RDF/Data Model:** rdflib, Turtle, JSON-LD
- **Runtime:** Docker Compose

---

## Repository Structure

```text
rfdb-curator/
├── backend/
│   ├── api/                      # Route handlers (data, entities, shapes, validate)
│   ├── core/                     # Core services
│   │   ├── config.py             # Pydantic settings (env var loading)
│   │   ├── logging_config.py     # Structured JSON-lines + console logger
│   │   ├── oxigraph_client.py    # Oxigraph HTTP client (SPARQL + bulk load)
│   │   ├── schema_extractor.py   # SHACL schema index (fields, shape roles, ordering)
│   │   ├── shacl_validator.py    # SHACL validation wrapper
│   │   ├── validation_merge.py   # Shape dependency graph + merged validation
│   │   ├── blank_node_handler.py # Blank-node skolemization (stable IRIs)
│   │   └── seeder.py             # Startup data seeder (vocab + optional test data)
│   ├── models/                   # Pydantic request/response schemas
│   │   ├── shapes.py             # Shape and field descriptors
│   │   └── data.py               # Entity list, counts, and single-entity payloads
│   ├── app.py                    # FastAPI app + lifespan (startup seeding + settings init)
│   ├── Dockerfile
│   ├── .env.example
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── components/           # React UI components (ShapeForm, ShapeRecordList, etc.)
│   │   ├── api/                  # API client methods
│   │   └── utils/                # JSON-LD and prefix helpers
│   ├── Dockerfile
│   ├── vite.config.js            # Dev server + proxy config (/api → backend:8000)
│   └── package.json
│
├── schema/
│   └── schema.ttl                # Active SHACL schema
│
├── data/
│   ├── vocab.ttl                 # Controlled-vocabulary seed data
│   └── data.ttl                  # Optional test fixture data
│
├── package.json                  # Root npm scripts/metadata
├── pyproject.toml                # Root Python project metadata
├── requirements.txt
├── docker-compose.yml
├── AGENTS.md                    # Root agent instructions
├── .agent-defs/                 # Project-specific agent instructions
├── tests/                       # Backend/API validation and integration tests
├── DEV.md
├── PROJECT_NOTES.md
├── TODO.md
└── README.md
```

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

---

## Service URLs

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend | http://localhost:8000 |
| Oxigraph | http://localhost:7878 |

---

## Configuration

All backend settings are loaded from environment variables. No defaults are hardcoded in the Python source. The backend fails fast with a clear validation error if a required variable is missing or has the wrong type.

Configuration source of truth:

- Runtime wiring: `docker-compose.yml`
- Backend settings model: `backend/core/config.py`
- Backend dependency set: `backend/pyproject.toml`

### Docker Compose (recommended)

Edit the `environment:` block in `docker-compose.yml`. 
`OXIGRAPH_URL` uses the Docker-internal hostname since backend and store are separate Compose services. 
`SCHEMA_PATH`/`VOCAB_PATH`/`DATA_PATH` are container paths backed by the `volumes:` mounts — change both together. 
`RESET_DATA_ON_STARTUP` wipes the store irreversibly; must stay `false` outside dev/test. `SEED_VOCAB_ON_STARTUP` should stay `true` or the store has no schema. 
`SEED_TEST_DATA_ON_STARTUP` is dev/test only. `READ_ONLY` turns the API into demo mode by rejecting create/update/delete requests with HTTP 403. 
`TRUNCATE_LOG_ON_STARTUP` clears logs on every restart (off by default, preserves crash history); `TRUNCATE_LOG_ON_FRESH_CONTAINER_START` clears logs only when a new container is created (on by default, avoids inheriting stale logs in the Docker volume).

Inspect backend file logs (Docker volume):

```bash
docker run --rm -v rfdb_backend_logs:/logs alpine ls -l /logs
docker run --rm -v rfdb_backend_logs:/logs alpine tail -n 200 /logs/app.jsonl
```

Use `docker compose logs -f backend` for stdout/stderr logs.


### Environment Variables

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
| `CORS_ORIGINS` | Yes | JSON array string of allowed CORS origins, e.g. `["http://localhost:5173"]`. |
| `LOG_FILE` | No | Path to the JSON-lines log file. Default: `logs/app.jsonl`. Parent directory created automatically. |
| `LOG_LEVEL` | No | Minimum log level for file and console handlers. Default: `INFO`. One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |

---

## Data Seeding

The application distinguishes between controlled vocabulary and test fixture data.

- `data/vocab.ttl` is the canonical seed source for controlled vocabulary (core types and role types).
- `dcterms:LinguisticSystem` vocabulary relies on [Glottolog v5.3](https://glottolog.org/meta/downloads) data from glottolog.org, imported from `data/glottolog_language.ttl`.
- Before using `data/glottolog_language.ttl`, normalize prefixes by replacing `geo1:` with `geo:`:

```bash
sed -i '' 's/geo1:/geo:/g' data/glottolog_language.ttl
```

- `data/data.ttl` is test-only fixture data.

Default policy: seed vocabulary on, seed test data off, preserve existing data on.

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

### Health Check Response

`GET /health` returns:

```json
{
  "status": "ok",
  "oxigraph": "up" | "down",
  "seed": { ... } | null
}
```

---

## SHACL-Driven Form Generation

The editor generates forms from the active SHACL schema. Each `sh:NodeShape` becomes a form type; each `sh:property` becomes a form field.

The form generator derives:

- field predicate from `sh:path`
- required fields from `sh:minCount`
- single-valued fields from `sh:maxCount 1`
- repeatable fields when no `sh:maxCount 1` is present
- literal datatype from `sh:datatype`
- IRI-valued fields from `sh:nodeKind sh:IRI`
- linked-resource target classes from `sh:class`
- linked form shape from `sh:node`
- alternatives from `sh:or`
- fixed values from `sh:hasValue`
- help text from `sh:description`
- closed-shape behavior from `sh:closed true`

The backend also infers a shape role from the schema. Shapes with a `sh:property` on `rdfs:label` are treated as standalone entities; shapes without one are treated as helper/bridge nodes and rendered inline when referenced by a parent shape. `rfdb:AgentRoleShape` follows this helper/bridge pattern.

---

## Current Data Model

The active schema uses the following main ontologies and vocabularies:

- LRMoo
- CIDOC CRM
- Polifonia Core Ontology
- Polifonia Music Meta Ontology
- Polifonia Source Ontology
- Dublin Core Terms
- PRISM
- RDF, RDFS, OWL
- SKOS
- Wikidata direct properties
- XML Schema datatypes

The active model uses LRMoo rather than the older FRBR/FaBiO model.

LRMoo hierarchy: a **Musical Work** is the abstract work; an **Expression** is an intellectual realization (e.g. a libretto); a **Manifestation** is an edition or product type; a **Source / Item** is a specific physical or documentary copy. Each level refines the one above it, from Work through Expression and Manifestation to Source/Item.

---

## Main SHACL Shapes

The current schema includes these primary record types:

- `rfdb:MusicalWorkShape`: musical work, targeting `mm:MusicEntity`, constrained as `lrmoo:F1_Work`
- `rfdb:ExpressionShape`: expression, targeting `lrmoo:F2_Expression`
- `rfdb:ManifestationShape`: manifestation, targeting `lrmoo:F3_Manifestation`
- `rfdb:SourceShape`: source/item, targeting `source:Source` and `lrmoo:F5_Item`
- `rfdb:PersonShape`: person, targeting `core:Person`
- `rfdb:RoleShape`: role, targeting `core:Role`
- `rfdb:AgentRoleShape`: agent-role assignment, targeting `core:AgentRole`
- `rfdb:PlaceShape`: place, targeting `core:Place`
- `rfdb:SubjectShape`: subject, targeting `cidoc:E89_Propositional_Object`
- `rfdb:SourceTypeShape`: source type, targeting `core:Type`
- `rfdb:HoldingOrganizationShape`: holding organization, targeting `core:Organization`
- `rfdb:ContributorShape`: donor/contributor record for digital-copy provenance
- `rfdb:PerformanceShape`: staged performance, targeting `lrmoo:F31_Performance`

---

## Important Modeling Patterns

### Work, Expression, Manifestation, Item

Recommended editorial insertion order:

1. Create the Musical Work (`lrmoo:F1_Work`, `mm:MusicEntity`).
2. Create the Expression (`lrmoo:F2_Expression`), linked to the Work via `core:isPartOf`.
3. Create the Manifestation (`lrmoo:F3_Manifestation`), linked to the Expression via `lrmoo:R4_embodies`.
4. Create the Source / Item (`source:Source`, `lrmoo:F5_Item`), linked to the Manifestation via `lrmoo:R7_exemplifies`.

This keeps identifiers stable and makes validation errors easier to localize. Use top-down incremental insertion in normal editorial work.

`POST /api/data` validates against a merged graph that includes referenced entities already present in the store. Merge expansion is transitive and depth-bounded, so helper nodes (e.g. `AgentRole` → `Person`/`Role`) linked behind referenced Work/Expression nodes are included during validation. This avoids false SHACL negatives in top-down incremental flows when nested linked nodes are not repeated in every later payload.

### Agent Role

The schema represents contributor roles through `core:AgentRole` bridge records:

```text
Work or Expression
    → core:hasAgentRole
        → Agent Role
            → core:hasAgent → Person
            → core:hasRole  → Role
```

The editor preserves stable IRIs for helper or bridge records during updates.

### Performance Modeling

Staged performances are modeled as `lrmoo:F31_Performance`, linked to a Work via `lrmoo:R80_performed`.
Date, venue, and personnel are attached on the performance itself, and personnel reuse the existing
`core:hasAgentRole` + `rfdb:AgentRoleShape` bridge pattern already used for composer/librettist attribution.

Performance-to-manifestation links intentionally keep two evidentiary strengths separate:

- `cidoc:P19_was_intended_use_of`: stronger claim, when a manifestation was created for that specific performance.
- `cidoc:P16_used_specific_object`: weaker claim, when a manifestation was used/present, without asserting why it was created.

These are distinct, standards-based CIDOC-CRM relations chosen for exact domain/range fit, rather than one convenient property stretched across two different evidentiary strengths.

### Donor/Contributor Modeling

Digital-copy donor/provenance attribution uses `dcterms:contributor` and is deliberately separate from:

- `cidoc:P51_has_former_or_current_owner` (legal ownership of the physical object)
- `core:hasAgentRole` contributor-role attribution used for creative/performance participation

`rfdb:ContributorShape` is constrained to `foaf:Person` or `foaf:Organization`. Since the core editorial entities
in this schema are typed with `core:*` classes, reuse requires deliberate visible retyping rather than accidental
cross-use between creative-role entities and donor/provenance entities. That separation is intentional because CIDOC-CRM
does not provide a simple donor shortcut outside the full acquisition event.

### Editing Existing Entities

For updates, always preserve:

1. Existing stable IRIs (`@id`) for the entity being edited.
2. Required class types (`@type`) for all class-targeted shapes.
3. Required labels and required relation links (`minCount` fields).

Do not regenerate helper/bridge node IRIs during an update unless the old node is being intentionally replaced.

---

## Validation

Validation happens at two levels.

### Client-side validation

The frontend enforces simple constraints derived from SHACL:

- required fields
- cardinality
- datatype checks
- IRI syntax checks
- language-tag checks
- linked-record consistency

### Backend SHACL validation

The backend validates submitted data against the active SHACL schema before persistence, against a merged graph that includes referenced entities already present in the store (see the merge-expansion note above).

Class-targeted shapes apply only to nodes that declare the corresponding RDF class. If a payload omits a required class type, constraints from that class-targeted shape may not run for that node. Submitted JSON-LD should include required `@type` values, especially for helper or bridge nodes.

---

## RDF and IRI Handling

Each RDF resource must have a stable subject IRI.

Main project namespace:

```text
https://rosfeatr.eu/rdf
```

Two main prefixes:
```ttl 
@prefix rfdb: <https://rosfeatr.eu/rdf/data/> .
@prefix rfdbs: <https://rosfeatr.eu/rdf/schema/> .
```

Compact form: `rfdb:EntityID`
Expanded form: `https://rosfeatr.eu/rdf/data/EntityID`

The editor supports:

- compact prefixed IRIs
- full IRIs
- prefix expansion and compaction
- stable IRI preservation during updates
- validation of IRI syntax
- Turtle export



