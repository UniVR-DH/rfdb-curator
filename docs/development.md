# RFDB Curator — Development Workflow

This document covers development workflow for the standalone `rfdb-curator` project
(package names `rfdb-editor-backend` / `rfdb-editor` internally in `backend/pyproject.toml`
and `frontend/package.json`).

---

## 1. Environment Setup

### Backend

Dependencies are managed with `uv`.

```bash
cd backend
uv sync --all-extras --dev
source .venv/bin/activate
```

Use this virtual environment for backend development, tests, linting, and local scripts.

### Frontend

Dependencies are managed with `npm`.

```bash
cd frontend
npm ci
npm run dev
```

Vite dev server runs on `http://localhost:5173`.

### Running the full application

Docker Compose is the preferred way to run backend + frontend + Oxigraph + Garage together during development.

On a fresh checkout, do the one-time setup first (requires OpenSSL): generate the gitignored `.env` and bootstrap Garage. Compose fails fast without `.env` (missing `GARAGE_RPC_SECRET`), and file uploads fail until Garage is bootstrapped.

```bash
# One-time, from the repository root
scripts/env-init.sh          # generate .env with fresh dev secrets
docker compose up -d --build
scripts/garage-init.sh        # bootstrap Garage layout/bucket/key (re-run after any `down -v`)
```

Both scripts are idempotent. After setup, ordinary runs need only:

```bash
docker compose up --build
```

### Hot reload

Both services use bind-mounts in Docker Compose, so source changes reload automatically without rebuilding images:

- Backend: uvicorn `--reload` watches `/app`
- Frontend: Vite dev server watches `/app`

---

## 2. Code Quality

### Tools

- **Ruff** — Python linting and formatting
- **ESLint** — React/JS linting
- **Prettier** — frontend formatting
- **pre-commit** — file hygiene and pre-commit checks

Recommended pre-commit checks: detect unresolved merge-conflict markers, validate TOML/YAML/JSON, normalize final newlines, strip trailing whitespace, run Ruff on backend code, run frontend lint/format checks.

### Local commands


Run directly:

```bash
# Backend
cd backend
ruff check .
ruff format .
python -m pytest

# Frontend
cd frontend
npm run lint
npm run build
```

### pre-commit setup

If `.pre-commit-config.yaml` is present:

```bash
uv tool install pre-commit
pre-commit install
```

Run all hooks manually:

```bash
pre-commit run --all-files
```

pre-commit is meant to catch formatting/hygiene issues before CI does.

---

## 3. CI/CD Expectations

**Backend checks:**
- install deps with `uv`
- Ruff lint
- Ruff format check
- run tests
- verify SHACL schema parses
- (optional) validate seed data against the active SHACL schema

**Frontend checks:**
- `npm ci`
- ESLint
- production build

**Integration checks (if practical):**
- start Oxigraph
- start backend
- check `/health`
- check `/api/shapes`
- run a dry-run validation request

---

## 4. Schema Change Workflow

To add or change a form in the editor, update the active SHACL schema at `schema/schema.ttl`. 
Each new record type is a `sh:NodeShape`.

When adding/changing shapes, verify:

`sh:targetClass`, `rdfs:label`, `sh:description`, `sh:property`, `sh:path`, `sh:minCount`, `sh:maxCount`, `sh:datatype`, `sh:nodeKind`, `sh:class`, `sh:node`, `sh:or`, `sh:hasValue`, `sh:closed`, `sh:uniqueLang`

The editor discovers updated shapes through the backend schema extractor, exposed via:

```
GET /api/shapes
GET /api/forms?shapeId=...
```

Two behaviors matter when adding or changing a shape, and both are documented elsewhere:

- **Helper/bridge vs. external-entity classification** — whether a shape renders as a top-level record or as a nested inline editor is derived from the schema (whether it declares an `rdfs:label` property), not hardcoded per class name. Check both the SHACL shape and the resulting `/api/shapes` metadata before changing frontend code. See [architecture.md](architecture.md#helperbridge-shape-classification).
- **Performance and contributor modeling rationale** — the deliberate use of `cidoc:P19_was_intended_use_of` vs `cidoc:P16_used_specific_object`, and of `dcterms:contributor` with `rfdbs:ContributorShape`, should be preserved unless there is an explicit migration plan. See [data-model.md](data-model.md#performance-and-contributor-modeling).

---

## 5. Data Change Workflow

- `data/vocab.ttl` — canonical seed data for controlled vocabulary. Seeding should normally be **enabled**.
- `data/data.ttl` — test-only fixture data. Seeding should normally be **disabled** outside dev/test.

### Namespace hardcoding map

When the RFDB namespaces change, update these locations together:

- `schema/schema.ttl` — authoritative Turtle prefixes and SHACL shape IRIs. Shape IRIs use `rfdbs:` (`https://rosfeatr.eu/rdf/schema/`); data resources use `rfdb:` (`https://rosfeatr.eu/rdf/data/`).
- `data/vocab.ttl` and `data/data.ttl` — authoritative Turtle data prefixes for seeded and fixture data.
- `backend/core/blank_node_handler.py` — generated entity IDs use the hardcoded `RFDB_BASE` data namespace.
- `backend/models/data.py` and `backend/core/config.py` — backend doc examples reference shape/data IRIs.
- `tests/` Python files — many tests assert full shape or entity IRIs directly; search for `rosfeatr.eu/rdf/` before and after any namespace migration.

Quick check from repo root:

```bash
rg -n 'https://rosfeatr\.eu/rdf/|https://rfdb\.it/data/' schema data backend tests docs AGENTS.md .agent-defs
```

---

## 6. Troubleshooting

### Oxigraph not ready

```bash
docker compose logs oxigraph
docker compose ps
```

Confirm port `7878` is free and the container is `healthy`.

### Backend refuses to start

```bash
docker compose logs backend
```

Check that all required environment variables are present and valid.

### CORS errors

`CORS_ORIGINS` must include the frontend origin, e.g.:

```json
["http://localhost:5173"]
```

Do not use `*` when credentials are enabled — the app rejects `CORS_ORIGINS=["*"]` when `allow_credentials=True`.

### Seed failures

- Confirm `SCHEMA_PATH`, `VOCAB_PATH`, `DATA_PATH` resolve correctly inside the container.
- Confirm the `schema/` and `data/` bind-mounts are present in `docker-compose.yml`.
- Host files must be world-readable if your umask is restrictive.

### SHACL validation failures

Check, in order:

- missing required fields
- wrong literal datatypes
- invalid IRIs
- missing `@type` values
- broken links to referenced entities
- cardinality violations
- language-tag issues, incl. duplicate tags where `sh:uniqueLang true`
- missing linked records required by `sh:class`/`sh:node`
- closed-shape violations where `sh:closed true`

**Nuance:** shapes using `sh:targetClass` only apply to nodes that explicitly declare the matching RDF class. For JSON-LD payloads, this means required `@type` values must be preserved — especially on helper/bridge nodes such as `core:AgentRole`.

### Log locations

Runtime logs: `/app/logs/app.jsonl` inside the backend container
(persisted in the `backend_logs` named volume). Container stdout/stderr:

```bash
docker compose logs backend
docker compose logs frontend
```

---

## 7. Commit Workflow

Before committing:

```bash
cd backend && ruff check . && ruff format . && python -m pytest && cd ..
cd frontend && npm run lint && npm run build && cd ..
pre-commit run --all-files   # if configured
```

Then:

```bash
 # Never use `git add .` — always review changes first
git add [ ...files... ]  
git commit -m "Describe the change"
```

A good PR description covers: what changed, whether the SHACL schema changed, whether seed data changed, whether validation behavior changed, whether frontend form behavior changed, and any migration/compatibility implications.

---

## 8. Quick Regex Log Checks (when UI submit appears to do nothing)

Backend structured logs are written to `/app/logs/app.jsonl` inside the
`backend_logs` volume. You can query them without entering a container:

```bash
docker run --rm -v rfdb_backend_logs:/logs alpine ls -l /logs
```

Start with broad error scan:

```bash
docker run --rm -v rfdb_backend_logs:/logs alpine sh -lc \
	"rg -n -i 'error|exception|traceback|validation|shacl|httpexception' /logs/app.jsonl"
```

Check whether POST `/api/data` was hit at all:

```bash
docker run --rm -v rfdb_backend_logs:/logs alpine sh -lc \
	"rg -n 'POST|/api/data|create_or_update_entity|validationReport' /logs/app.jsonl"
```

Target your example payload text (`Expression 1`, `en`):

```bash
docker run --rm -v rfdb_backend_logs:/logs alpine sh -lc \
	"rg -n -i 'Expression 1|\"en\"|rdfs:label|core:text|langString' /logs/app.jsonl"
```

Live-tail only relevant lines while retrying submit in UI:

```bash
docker run --rm -v rfdb_backend_logs:/logs alpine sh -lc \
	"tail -f /logs/app.jsonl" | rg --line-buffered -i 'POST|/api/data|Expression 1|validation|error|exception|shacl'
```

If using Docker and file logs look empty, check container logs too:

```bash
docker compose logs -f backend | rg --line-buffered -i 'POST|/api/data|validation|error|exception|shacl|Expression 1'
```

Tip: if no `POST /api/data` pattern appears when clicking save, the request likely never left the browser (frontend-side issue). If POST appears with SHACL or validation errors, it is a backend/schema rejection.

