# RFDB Editor

SHACL-driven data-entry application for the RossijskijFeatrDB. Provides shape-aware CRUD, validation, autocomplete, and record inspection for RDF instance data.

The repository already has `explorer/` for graph exploration and shape inspection. This app is the complementary write-oriented surface.

## Tech Stack

- **Backend:** FastAPI + uvicorn
- **Frontend:** React + Vite
- **RDF Store:** Oxigraph (SPARQL + Graph Store Protocol)
- **Validation:** pyshacl (SHACL)
- **Data Model:** rdflib (Turtle / RDF)
- **Runtime:** Docker Compose (development)

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Repository contains `editor/docker-compose.yml` (already configured)

### Run

From the repository root:

```bash
# First run or after Dockerfile changes
docker compose up --build

# Subsequent runs
docker compose up
```

Stop:

```bash
docker compose down
```

Remove volumes (destructive — clears all Oxigraph data):

```bash
docker compose down -v
```

### Service URLs

| Service  | URL                  |
|----------|----------------------|
| Frontend | http://localhost:5173 |
| Backend  | http://localhost:8000 |
| Oxigraph | http://localhost:7878 |

### Data reset modes

The backend can start either with a clean slate or by preserving existing data, controlled by the `RESET_DATA_ON_STARTUP` environment variable.

**Clean slate (empty store)**

Clears all triples from the named data graph before seeding. Use this when you want to reset the editor to its initial state.

Docker Compose:

```bash
RESET_DATA_ON_STARTUP=true docker compose up --build
```

Local `.env`:

```
RESET_DATA_ON_STARTUP=true
```

> Warning: This is destructive. All instance data is permanently lost on startup.

**Preserve existing data (default)**

Keeps existing triples in the store and merges new seed data on top. Use this for normal development when you want to retain previously entered data.

Docker Compose:

```bash
docker compose up --build
```

Local `.env`:

```
RESET_DATA_ON_STARTUP=false
```

### Seeding behavior

In both modes, the controlled vocabulary from `data/vocab.ttl` is loaded on every startup (idempotent). Test fixture data from `data/data.ttl` is loaded only when `SEED_TEST_DATA_ON_STARTUP=true` (off by default outside of test environments).

## Folder Structure

```
rfdb-curator/
├── backend/
│   ├── api/                  # Route handlers (data, entities, shapes, validate)
│   ├── core/                 # Core services
│   │   ├── config.py         # Pydantic settings (env var loading)
│   │   ├── logging_config.py # Structured JSON-lines + console logger
│   │   ├── oxigraph_client.py # Oxigraph HTTP client (SPARQL + bulk load)
│   │   ├── schema_extractor.py # SHACL schema index (fields, shape roles, ordering)
│   │   ├── shacl_validator.py  # SHACL validation wrapper
│   │   ├── validation_merge.py # Shape dependency graph + merged validation
│   │   ├── blank_node_handler.py # Blank-node skolemization (stable IRIs)
│   │   └── seeder.py           # Startup data seeder (vocab + optional test data)
│   ├── models/               # Pydantic request/response schemas
│   ├── app.py                # FastAPI app + lifespan (startup seeding + settings init)
│   ├── Dockerfile            # Python 3.12 + dependencies runner
│   ├── .env.example          # Local development environment template
│   ├── pyproject.toml        # Backend dependencies (exact pins via uv)
│   └── logs/                 # Runtime JSON-lines logs (gitignored, kept via .gitkeep)
│
└── frontend/
    ├── src/
    │   ├── components/       # React components (ShapeForm, ShapeRecordList, etc.)
    │   ├── api/              # API client methods
    │   └── utils/            # JSON-LD helpers, prefix maps
    ├── Dockerfile            # Node 20 + npm build runner
    ├── vite.config.js        # Vite dev server + proxy config (/api → backend:8000)
    └── package.json          # Frontend dependencies (exact pins)
```

## Configuration

All backend settings are loaded from environment variables. No defaults are hardcoded in the Python source. There are two ways to supply them.

### Docker Compose (recommended)

The `environment:` block in `editor/docker-compose.yml` is the authoritative config for Docker-based deployments. Edit values there.

### Local development (without Docker)

Copy the example file and fill in values:

```bash
cp editor/backend/.env.example editor/backend/.env
# then edit editor/backend/.env
```

The backend reads `.env` automatically on startup (via pydantic-settings). `.env` is gitignored — never commit it.

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OXIGRAPH_URL` | ✅ | Base URL of the Oxigraph HTTP endpoint, no trailing slash. Use `http://localhost:7878` locally or `http://oxigraph:7878` inside Docker. |
| `DATA_GRAPH_URI` | ✅ | Named graph URI where all instance data is stored and queried. Every SPARQL read uses `FROM <uri>` and every Turtle load targets `?graph=<uri>`. Change per deployment to isolate data sets. |
| `SCHEMA_PATH` | ✅ | Path to `schema.ttl` relative to the backend working directory. Docker mounts it at `/app/schema/schema.ttl`. |
| `VOCAB_PATH` | ✅ | Path to `vocab.ttl` (controlled-vocabulary seed). Loaded at startup when `SEED_VOCAB_ON_STARTUP=true`. |
| `DATA_PATH` | ✅ | Path to `data.ttl` (test fixture data). Loaded at startup only when `SEED_TEST_DATA_ON_STARTUP=true`. |
| `RESET_DATA_ON_STARTUP` | ✅ | `true`/`false`. **Destructive.** Clears the named graph before seeding on every startup. Must be `false` in production. Set `true` only during development to get a clean slate. |
| `SEED_VOCAB_ON_STARTUP` | ✅ | `true`/`false`. Load `VOCAB_PATH` into Oxigraph on every startup. Should be `true` in all environments. |
| `SEED_TEST_DATA_ON_STARTUP` | ✅ | `true`/`false`. Load `DATA_PATH` on startup. Set `true` in dev/test only. |
| `CORS_ORIGINS` | ✅ | JSON array string of allowed CORS origins, e.g. `["http://localhost:5173"]`. Include every origin the frontend is served from. |
| `LOG_FILE` | optional | Path to the JSON-lines log file. Default: `logs/app.jsonl`. Parent directory is created automatically. |
| `LOG_LEVEL` | optional | Minimum log level for both file and console handlers. Default: `INFO`. Accepted: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |

The `editor/backend/logs/` directory stays in the repository with a `.gitkeep` placeholder so the folder exists, but generated runtime logs such as `app.jsonl` remain ignored.

> The application will **refuse to start** and print a clear validation error
> if any of these variables is missing or has the wrong type.

## API Reference

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness/readiness check (Oxigraph status + seed report) |
| `GET` | `/api/shapes` | All SHACL NodeShapes with metadata and field descriptors |
| `GET` | `/api/forms?shapeId=...` | Field schema for a single shape |
| `GET` | `/api/data/list` | Paginated entity list for a shape, with text filter |
| `GET` | `/api/data/counts` | Per-shape entity counts (used by sidebar pills) |
| `GET` | `/api/data/{entityId}` | All triples for a single entity |
| `POST` | `/api/data` | Create or update an entity (JSON-LD → SHACL validate → Turtle load) |
| `DELETE` | `/api/data/{entityId}` | Delete all triples for an entity |
| `GET` | `/api/entities/search` | Autocomplete search for relation fields |
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

## Data Insert Flow

### Recommended order

The canonical domain dependency chain is:

1. Musical Work (`lrmoo:F1_Work`, `mm:MusicEntity`)
2. Expression (`lrmoo:F2_Expression`) with `core:isPartOf -> Work`
3. Manifestation (`lrmoo:F3_Manifestation`) with `lrmoo:R4_embodies -> Expression`
4. Source / Item (`source:Source`, `lrmoo:F5_Item`) with `lrmoo:R7_exemplifies -> Manifestation`

Use **top-down incremental insertion** in normal editorial work:

1. Create the Work first.
2. Create the Expression linked to that Work.
3. Create the Manifestation linked to that Expression.
4. Create the Source linked to that Manifestation.

This keeps identifiers stable, makes errors easier to localize, and aligns with shape semantics.

**Backend note:** `POST /api/data` validates against a merged graph that includes referenced entities already present in the store. Merge expansion is transitive and depth-bounded, so helper nodes (for example `AgentRole` → `Person`/`Role`) linked behind referenced Work/Expression nodes are included during validation. This avoids false SHACL negatives in top-down incremental flows when nested linked nodes are not repeated in every later payload.

### Editing existing entities

For updates, always preserve:

1. Existing stable IRIs (`@id`) for the entity being edited.
2. Required class types (`@type`) for all class-targeted shapes.
3. Required labels and required relation links (`minCount` fields).

Do not regenerate helper/bridge node IRIs during an update unless the old node is being intentionally replaced.

### Validation nuance

- Class-targeted shapes (for example, shapes using `sh:targetClass`) apply only to nodes that actually declare the corresponding RDF class.
- If a payload omits a required class type, constraints from that class-targeted shape may not run for that node.
- For bridge/helper nodes, always emit explicit `@type` values when the schema relies on class-targeted constraints.

## Data Seeding Policy

- `data/vocab.ttl` is the canonical seed source for controlled vocabulary (core types and role types).
- `data/data.ttl` is treated as test-only fixture data at this stage.
- Backend defaults: seed vocab = on, seed test data = off.

## Development

### Backend

```bash
cd editor/backend
uv sync --all-extras --dev
source .venv/bin/activate
python -m pytest
```

Docker Compose is used for the running service. Do not start uvicorn manually when Docker Compose is available.

### Frontend

```bash
cd editor/frontend
npm ci
npm run dev
```

The Vite dev server runs on `http://localhost:5173` and proxies `/api` to the backend container (`http://backend:8000`).

### Hot Reload

Both backend and frontend use bind-mounts in Docker Compose, so source changes trigger automatic reloads without rebuilding images.

- Backend: uvicorn `--reload` watches `/app`
- Frontend: Vite dev server watches `/app`

### Lint

```bash
# Frontend
cd editor/frontend && npm run lint

# Or from repo root via Makefile
make lint
```

## Troubleshooting

### Oxigraph not ready

If the backend health check fails or `oxigraph` shows as `down`:

```bash
docker compose logs oxigraph
```

Ensure port `7878` is free and the container is in `healthy` state:

```bash
docker compose ps
```

### Backend refuses to start

The backend exits immediately if any required environment variable is missing or has the wrong type. Check the logs:

```bash
docker compose logs backend
```

Confirm all variables listed in the Configuration section are present in the Docker Compose `environment:` block or in `editor/backend/.env`.

### CORS errors

If the browser blocks API requests, verify `CORS_ORIGINS` includes the frontend origin:

```json
["http://localhost:5173"]
```

Do not use `*` — the app explicitly rejects `CORS_ORIGINS=["*"]` when `allow_credentials=True`.

### Seed failures

If the backend logs show seed errors:

- Confirm `SCHEMA_PATH`, `VOCAB_PATH`, and `DATA_PATH` resolve correctly inside the container.
- Confirm the bind-mounts for `../schema` and `../data` are present in `editor/docker-compose.yml` (relative to the `editor/` directory).
- Host files must be world-readable if your umask is restrictive.

### Log locations

Runtime logs are written to `editor/backend/logs/app.jsonl` (on the host). Container stdout/stderr is also available via:

```bash
docker compose logs backend
docker compose logs frontend
```

## Known Gaps

1. Expand vocab seed set and add integrity checks for required concepts.
2. Complete shape-role policy (`external-entity` vs `helper-bridge`) across all nested shapes.
3. `DELETE /api/data/{id}` currently removes only triples where the entity is the **subject**. Orphaned bridge entities (e.g., `AgentRole` nodes linked only from the deleted parent) are not cleaned up. Add a cascade or a separate cleanup pass.
4. Improve JSON-LD coverage for edge cases in nested forms and repeated multilang values with non-standard datatypes.
5. Add SPARQL-level pagination cursor (currently uses OFFSET; may be slow on large graphs).

## Roadmap: Namespace & Graph Console (Planned)

### Goal

Add a first-class UI surface that exposes:

- full namespace/prefix mapping used by the editor (`@context` + schema prefixes)
- active data graph configuration (`DATA_GRAPH_URI`)
- available named graphs in Oxigraph with lightweight stats

This is intended as an operator-facing transparency feature, not a debugging hack.

### UX Concept

Add a dedicated "Data Context" panel accessible from the left sidebar (below shape navigation), with two tabs:

1. **Prefixes**
   - Table columns: Prefix, Namespace IRI, Source (`schema`, `jsonld-context`, `runtime`).
   - Search box (prefix or namespace substring).
   - Copy actions:
     - copy full namespace IRI
     - copy Turtle prefix line (`@prefix foo: <...> .`)
   - Consistency warnings when a prefix exists in one source but not the others.

2. **Named Graphs**
   - Header card showing configured write/read graph (`DATA_GRAPH_URI`).
   - Table columns: Graph IRI, Triple Count, Status (`active`, `non-empty`, `empty`).
   - Badge for "active data graph".
   - Read-only mode for first release (no destructive actions from UI).

### Backend API Plan

Introduce read-only metadata endpoints under `/api/meta`:

- `GET /api/meta/prefixes`
  - response:
    - `prefixes`: array of `{prefix, namespace, source}`
    - `warnings`: array of consistency warning strings

- `GET /api/meta/graphs`
  - response:
    - `activeGraph`: string (`DATA_GRAPH_URI`)
    - `graphs`: array of `{graph, tripleCount, status}`

Implementation notes:
- Prefixes should be merged from:
  - schema graph namespace manager
  - frontend JSON-LD context map (served from backend to avoid duplication drift)
- Graph list should be computed with SPARQL over `GRAPH ?g { ?s ?p ?o }` plus per-graph counts.

### Frontend Integration Plan

- Add a new component group:
  - `DataContextPanel.jsx`
  - `PrefixesTable.jsx`
  - `GraphsTable.jsx`
- Add corresponding API client methods:
  - `getPrefixesMeta()`
  - `getGraphsMeta()`
- Keep panel state independent from shape/form state to avoid accidental re-renders of editor workflows.
- Use the same visual language as existing inspector/list panels (cards, compact mono IRIs, copy buttons).

### Rollout Phases

**Phase 1: Read-only visibility**
- Show prefix table + active graph + graph counts.
- Add consistency warnings in Prefixes tab.

**Phase 2: Operational guardrails**
- Add health indicators (store reachable, metadata freshness timestamp).
- Add "schema/context mismatch" diagnostics with actionable hints.

**Phase 3: Advanced operations (optional, gated)**
- Only after explicit approval: controlled graph utilities (e.g., export graph snapshot).
- No delete/clear actions unless separately designed and approved.

### Acceptance Criteria

- User can inspect complete prefix mapping without leaving the editor UI.
- User can see exactly which named graph is active and whether other graphs contain data.
- Any prefix drift between schema/context/runtime is surfaced as an explicit warning.
- The panel remains read-only in baseline deployment and does not affect save/validation flows.
