# Build Commands

## 🚨 Virtual Environment Activation

NEVER assume venv is active. ALWAYS prefix Python/pip commands from the repository root:

```bash
source .venv/bin/activate && python <command>
```

Terminal context showing prior activation does NOT guarantee current state.

## Environment Setup

```bash
# Root environment (rfdbtools)
cd <repo-root>
uv sync --all-extras --dev
source .venv/bin/activate

# Editor backend (separate environment)
cd editor/backend
uv sync --dev
```

The repository uses a single root runtime environment for `rfdbtools`.

## Dependency Updates (Pinned + Current)

```bash
# 1) Check latest published versions before pinning
uvx --from pip pip index versions <package>

# 2) Pin exact versions in pyproject.toml (no open-ended specifiers)
# 3) Regenerate lockfile
uv lock
```

Never use `latest`, `*`, `>=`, `<=`, `~=` or other open-ended version tags.

## Docker / Docker Compose

If a service has a `Dockerfile` or `docker-compose.yml`, always prefer Docker to run it.

```bash
cd editor
docker compose up          # start
docker compose up --build  # rebuild and start
docker compose down        # stop
```

## Validation Commands

```bash
# SHACL validation (use rfdbtools.run CLI)
source .venv/bin/activate && python -m rfdbtools.run validate --schema schema/schema.ttl --data data/data.ttl

# Python syntax check
source .venv/bin/activate && python -m py_compile rfdbtools/*.py

# Ontology syntax/consistency check
source .venv/bin/activate && python -m rfdbtools.validate_ontologies --data data/data.ttl --ontologies schema/schema.ttl
```

## Testing Commands

```bash
# Run tests
source .venv/bin/activate && python -m pytest tests/ -v

# Targets in Makefile
make test
```

## Excel Generation

```bash
# REQUIRED: check existing Git tags before choosing export tag
git tag -l --sort=version:refname

# Generate workbook from SHACL schema
source .venv/bin/activate && python -m rfdbtools.run get_excel --schema schema/schema.ttl --output-dir excel_out --name workbook --tag v1

# Convert filled Excel back to RDF
source .venv/bin/activate && python -m rfdbtools.run get_rdf --excel excel_out/<file>.xlsx --mapping excel_out/<file>_mapping.json --output data.ttl
```

**Tag rule:** derive `--tag` from Git tags via `git tag -l --sort=version:refname`. Increment consistently (e.g. `v0.3` -> `v0.4`).

## Ontology Pipeline

```bash
make all
```

Downloads and converts all referenced ontologies to `.ontologies/` (gitignored).

## Documentation

```bash
source .venv/bin/activate && python -m pdoc --output-dir docs rfdbtools

# Or via Makefile
make docs
```

## Linting / Formatting

```bash
# Python
ruff check .
ruff format .

# JavaScript
prettier --write .

# Or via pre-commit
pre-commit run --all-files
```

## Make Targets

```bash
make all          # full ontology pipeline
make docs         # generate API docs
make test         # run pytest
make validate     # run SHACL validation
```
