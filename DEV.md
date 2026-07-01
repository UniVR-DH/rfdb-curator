# RFDB EDITOR DEVELOPMENT WORKFLOW

This document contains development-workflow material relevant to the standalone `rfdb-editor` project.

It intentionally excludes legacy parent-repository workflows that are not part of this standalone codebase.

---

## 1. Backend Dependency Management

Backend dependencies are managed with `uv`.

From the repository root:

```bash
cd backend
uv sync --all-extras --dev
source .venv/bin/activate
```

Use this backend virtual environment for backend development, tests, linting, and local scripts.

The full application runtime should normally be started with Docker Compose from the repository root:

```bash
docker compose up --build
```

---

## 2. Frontend Dependency Management

Frontend dependencies are managed with `npm`.

From the repository root:

```bash
cd frontend
npm ci
npm run dev
```

The Vite development server runs on:

```text
http://localhost:5173
```

---

## 3. Recommended Code Quality Tools

The project should use a lightweight, multi-tool quality setup.

Recommended tools:

- Ruff for Python linting and formatting
- ESLint for React and JavaScript linting
- Prettier for frontend formatting
- pre-commit for basic file hygiene and automated checks before commits

Recommended pre-commit checks:

- detect unresolved merge-conflict markers
- validate TOML files
- validate YAML files
- validate JSON files
- normalize final newlines
- remove trailing whitespace
- run Ruff on backend Python code
- run frontend linting or formatting checks where practical

---

## 4. Suggested Local Quality Commands

If the repository provides a `Makefile`, recommended targets are:

```bash
make check       # Run all available checks
make lint        # Run linting
make lint-fix    # Auto-fix linting issues where possible
make format      # Format code
```

If no `Makefile` is available, run backend and frontend checks directly.

Backend:

```bash
cd backend
ruff check .
ruff format .
python -m pytest
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

---

## 5. Pre-Commit Setup

If the repository includes `.pre-commit-config.yaml`, install and enable pre-commit hooks with:

```bash
uv tool install pre-commit
pre-commit install
```

To run all hooks manually:

```bash
pre-commit run --all-files
```

Pre-commit should be used to catch formatting and hygiene issues before code reaches CI.

---

## 6. CI/CD Expectations

A CI workflow for `rfdb-editor` should check both backend and frontend quality.

Recommended backend checks:

- install backend dependencies with `uv`
- run Ruff linting
- run Ruff formatting check
- run backend tests
- verify the SHACL schema can be parsed
- optionally validate seed data against the active SHACL schema

Recommended frontend checks:

- install dependencies with `npm ci`
- run ESLint
- run the production build

Recommended integration checks, if practical:

- start Oxigraph
- start backend
- check `/health`
- check `/api/shapes`
- run a dry-run validation request

---

## 7. Schema Change Workflow

To add or change a form in the editor, update the active SHACL schema:

```text
schema/schema.ttl
```

Each new record type should be represented as a `sh:NodeShape`.

When adding or changing shapes, verify:

- `sh:targetClass`
- `rdfs:label`
- `sh:description`
- `sh:property`
- `sh:path`
- `sh:minCount`
- `sh:maxCount`
- `sh:datatype`
- `sh:nodeKind`
- `sh:class`
- `sh:node`
- `sh:or`
- `sh:hasValue`
- `sh:closed`
- `sh:uniqueLang`

The editor should discover updated shapes through the backend schema extractor and expose them through:

```text
GET /api/shapes
GET /api/forms?shapeId=...
```

---

## 8. Data Change Workflow

Controlled vocabulary should be added to:

```text
data/vocab.ttl
```

Test fixture data should be added to:

```text
data/data.ttl
```

Current policy:

- `data/vocab.ttl` is canonical seed data for controlled vocabulary.
- `data/data.ttl` is test-only fixture data.
- Vocabulary seeding should normally be enabled.
- Test data seeding should normally be disabled outside development or test environments.

---

## 9. Validation Troubleshooting

If SHACL validation fails, check the following first:

- missing required fields
- wrong literal datatypes
- invalid IRIs
- missing `@type` values
- broken links to referenced entities
- cardinality violations
- language-tag issues
- duplicate language tags where `sh:uniqueLang true` is used
- missing linked records required by `sh:class` or `sh:node`
- closed-shape violations when `sh:closed true` is used

Important validation nuance:

Shapes using `sh:targetClass` apply only to nodes that explicitly declare the corresponding RDF class. For JSON-LD payloads, this means required `@type` values must be preserved, especially for helper or bridge nodes such as `core:AgentRole`.

---

## 10. Recommended Commit Workflow

Before committing:

```bash
# Backend checks
cd backend
ruff check .
ruff format .
python -m pytest
cd ..

# Frontend checks
cd frontend
npm run lint
npm run build
cd ..

# Optional, if pre-commit is configured
pre-commit run --all-files
```

Then commit:

```bash
git add .
git commit -m "Describe the change"
```

A good pull request should describe:

- what changed
- whether the SHACL schema changed
- whether seed data changed
- whether validation behavior changed
- whether frontend form behavior changed
- any migration or compatibility implications

---

## 11. What Was Intentionally Excluded

This file intentionally excludes older parent-repository workflows, including:

- legacy CLI commands that are no longer shipped here
- spreadsheet generation or conversion pipelines
- legacy API-doc generation flows
- ontology download/conversion pipelines from the previous repository layout
- instructions that depend on a root Python virtual environment

Those workflows are not part of the standalone `rfdb-editor` project unless reintroduced explicitly.
