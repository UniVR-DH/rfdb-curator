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

# Explorer — standalone read-only graph visualizer (its own Vite app)
cd ../explorer
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

**Never start or restart the Docker daemon / Docker Desktop yourself** (no
`open -a Docker`, no `systemctl start docker`, no launchd tricks). If the
daemon is unreachable, stop and ask the user to start it. Managing `docker
compose` services is fine; managing the Docker engine itself is the user's
prerogative.

## Validation and Tests

```bash
# Backend tests — run FROM backend/. `-c pyproject.toml` points pytest at the
# backend project's [tool.pytest.ini_options]; pytest can't auto-discover it
# from ../tests/ because backend/ is not an ancestor of tests/.
cd backend
uv run python -m pytest -c pyproject.toml ../tests/ -v

# Frontend checks
cd ../frontend
npm run lint
npm run build

# Explorer checks (mirrors the frontend; CI runs these as `explorer-checks`)
cd ../explorer
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

There is a single Python project, `backend/` — the repo root has no `pyproject.toml`, `uv.lock`, or `.venv` (root `requirements.txt` is documentation only). Ruff (`ruff==0.14.5`) and its config live in `backend/pyproject.toml`. CI runs the lint with `working-directory: backend`, so always match that:

```bash
# Backend — run FROM backend/, mirrors CI exactly
cd backend
uv run ruff check .          # CI: "Ruff lint"
uv run ruff format --check . # CI: "Ruff format check"

# Frontend
cd ../frontend
npm run lint

# Explorer
cd ../explorer
npm run lint
```

### Gotcha: `ruff: command not found` / `pyenv: ruff`

If you see `pyenv: ruff: command not found (exists in 3.8.14)` you ran ruff from the **wrong directory**. Diagnosis and rules:

- The only Python env is `backend/.venv`; `backend/.venv/bin/ruff` is the sole ruff install. The repo root has no project or venv.
- Running `uv run ruff` from the **repo root** fails: there's no project there, so PATH falls through to the pyenv `ruff` shim, which only has ruff for Python 3.8.14 — hence the misleading error. **Fix: `cd backend` first.**
- A stale `VIRTUAL_ENV` (e.g. a previously-activated `<repo-root>/.venv`, now deleted) triggers a harmless `VIRTUAL_ENV does not match` warning; uv ignores it and uses `backend/.venv`. Run `deactivate` to clear it.
- `uv run ruff check .` from `backend/` needs no manual `source .venv/bin/activate` — uv resolves the backend env itself.

## Notes

- Do not rely on a root Python package named `rfdbtools`; this repository is a standalone editor stack.
- The `explorer/` app (read-only graph visualizer) is an active, first-class frontend — set it up, lint, and build it alongside `frontend/` (see the sections above). Treat only commands referencing Excel generation or ontology download pipelines as legacy unless explicitly reintroduced.
