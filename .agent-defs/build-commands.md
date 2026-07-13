# Build Commands

## Backend Environment Setup

```bash
cd backend
uv sync --all-extras --dev
source .venv/bin/activate
```

Use this environment for backend tests and Python checks.

## Frontend Environment Setup

```bash
cd frontend
npm ci
```

## Docker Compose Runtime (Preferred)

Run from repository root:

```bash
docker compose up --build
docker compose up
docker compose down
docker compose down -v
```

## Validation and Tests

```bash
# Backend tests
cd backend
source .venv/bin/activate
python -m pytest ../tests -v

# Frontend checks
cd ../frontend
npm run lint
npm run build
```

### RDF Validation with Jena

Single file:

```bash
docker run --rm \
	--platform=linux/amd64 \
	-v "$PWD":/data \
	stain/jena:5.1.0 \
	riot --validate /data/data/corporate/prod-inst.ttl
```

Batch (all `.ttl` / `.nt` under `data/`):

```bash
docker run --rm \
	--platform=linux/amd64 \
	-v "$PWD":/data \
	stain/jena:5.1.0 \
	bash -euo pipefail -c '
		status=0
		while IFS= read -r -d "" f; do
			echo "==== Validating: $f ===="
			riot --validate "$f" || { echo "ERROR in $f" >&2; status=1; }
		done < <(find /data/data -type f \( -name "*.ttl" -o -name "*.nt" \) -print0)
		exit $status
	' 2>&1 | tee .temp/ttl-validation.log
```

## Linting and Formatting

```bash
# Backend (if ruff is installed in backend env)
cd backend
source .venv/bin/activate
ruff check .
ruff format .

# Frontend
cd ../frontend
npm run lint
```

## Notes

- Do not rely on a root Python package named `rfdbtools`; this repository is a standalone editor stack.
- Treat commands referencing Excel generation, explorer apps, or ontology download pipelines as legacy unless explicitly reintroduced.
