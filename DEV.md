# RFDB Editor — Development Workflow

This document covers development workflow for the standalone `rfdb-editor` project. 

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

Docker Compose is the preferred way to run backend + frontend + Oxigraph together during development:

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

---

## 5. Data Change Workflow

- `data/vocab.ttl` — canonical seed data for controlled vocabulary. Seeding should normally be **enabled**.
- `data/data.ttl` — test-only fixture data. Seeding should normally be **disabled** outside dev/test.

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

Runtime logs: `backend/logs/app.jsonl` on the host. Container stdout/stderr:

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

Backend structured logs are written to `backend/logs/app.jsonl`.

Start with broad error scan:

```bash
rg -n -i 'error|exception|traceback|validation|shacl|httpexception' backend/logs/app.jsonl
```

Check whether POST `/api/data` was hit at all:

```bash
rg -n 'POST|/api/data|create_or_update_entity|validationReport' backend/logs/app.jsonl
```

Target your example payload text (`Expression 1`, `en`):

```bash
rg -n -i 'Expression 1|"en"|rdfs:label|core:text|langString' backend/logs/app.jsonl
```

Live-tail only relevant lines while retrying submit in UI:

```bash
tail -f backend/logs/app.jsonl | rg --line-buffered -i 'POST|/api/data|Expression 1|validation|error|exception|shacl'
```

If using Docker and file logs look empty, check container logs too:

```bash
docker compose logs -f backend | rg --line-buffered -i 'POST|/api/data|validation|error|exception|shacl|Expression 1'
```

Tip: if no `POST /api/data` pattern appears when clicking save, the request likely never left the browser (frontend-side issue). If POST appears with SHACL or validation errors, it is a backend/schema rejection.

