# Build Commands

## Python Environment Setup

The repo is a **uv workspace**: the root `pyproject.toml` declares the members
(`rfdb-core`, `curator-backend`, `dataexplorer-backend`), and uv keeps **one lockfile
and one virtualenv at the repo root** for all of them. One sync installs everything;
an edit to `rfdb-core` is picked up by both services with no reinstall.

```bash
uv sync --all-extras --dev      # from the repo root — installs every member
source .venv/bin/activate       # the venv is at the ROOT, not curator-backend/.venv
```

`cd curator-backend && uv sync …` works identically — uv walks up to the workspace root — so
either is fine. Use this one environment for all Python checks.

> If you have a stale `curator-backend/.venv` or `curator-backend/uv.lock` from before the workspace
> existed, they are dead weight; uv ignores both. Delete them at your leisure.

## Frontend Environment Setup

```bash
cd curator-frontend
npm ci

# Explorer — standalone read-only graph visualizer (its own Vite app)
cd ../graphexplorer-frontend
npm ci
```

## Docker Compose Lifecycle (Preferred Runtime)

Run from repository root. Lifecycle only — `ps`, `logs`, `restart` and health checks live in
[editor-runtime.md](editor-runtime.md).

```bash
docker compose up --build
docker compose up
docker compose down
docker compose down -v   # DROPS the Oxigraph and Garage volumes — destroys all stored data
```

`down -v` is a deletion: never run it to "clean up" without explicit approval (`AGENTS.md` §7).
It also un-bootstraps Garage — a fresh volume has no layout, bucket or key, so
`scripts/garage-init.sh` must be re-run once afterwards (it is idempotent).

**Two modes.** Base services (`oxigraph`, `garage`, `dataexplorer-backend`,
`graphexplorer-frontend`) carry no `profiles:` key and start in every mode; `curator-backend`
and `curator-frontend` are `full`-only. So a bare `docker compose up` is the **read-only**
stack — no editor, no writer — and the whole stack needs `COMPOSE_PROFILES=full` in `.env`
(what `scripts/env-init.sh` writes) or `--profile full` per invocation. When a write route
refuses connections, check this first — [editor-runtime.md](editor-runtime.md) → "Compose
Commands" has the diagnosis, [../docs/deployment.md](../docs/deployment.md) the full detail.

Never start or restart the Docker daemon / Docker Desktop yourself (`AGENTS.md` §0.6) — if it
is unreachable, stop and ask the user. Managing `docker compose` services is fine.

## Seeding and Data Reset

How triples get into the store — the thing to check first when reads come back empty.

- **On startup:** `curator-backend` seeds `data/vocab.ttl` because compose sets
  `SEED_VOCAB_ON_STARTUP=true`. Test fixtures (`data/data.ttl`) are `SEED_TEST_DATA_ON_STARTUP`
  and default to off.
- **One-shot, no web server:** `docker compose run --rm curator-backend python scripts/seed.py`
  — the same `core.seeder.bootstrap_store()` the lifespan runs. This is how a **read-only**
  deployment gets populated: no writer process is up to seed on startup.
- **Idempotent.** `vocab.ttl` merges rather than replaces, so re-running is safe.

**`RESET_DATA_ON_STARTUP=true` is destructive** — it clears the named graph before every seed,
and it must stay `false` in production. Treat setting it, like `docker compose down -v`, as a
deletion requiring explicit approval (`AGENTS.md` §7). Back up volumes first; the tarball
procedure is in [../docs/deployment.md](../docs/deployment.md) → "Ongoing operations".

Full configuration matrix, reset modes, and the read-only population path:
[../docs/deployment.md](../docs/deployment.md).

## Validation and Tests

**Python tests: one run per workspace member, as CI does.** The three commands and the reason
they cannot be collapsed into one live in [testing.md](testing.md) → "Running Tests". That is
the canonical copy; do not paste a fourth one here.

```bash
# Frontend checks
cd curator-frontend
npm run lint
npm run build

# Explorer checks (mirrors the frontend; CI runs these as `graphexplorer-frontend-checks`)
cd ../graphexplorer-frontend
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

There are three Python projects, all uv workspace members: `rfdb-core/` (the shared
library), `curator-backend/` (writes) and `dataexplorer-backend/` (reads). Ruff is
pinned in **each member's `[dependency-groups] dev`** (the workspace resolves one
version for all three), but **its config lives in the root `pyproject.toml`** — one
`[tool.ruff]` for every member, plus `tests/`. The version is deliberately not repeated
here: this file said `ruff==0.14.5` for two releases after the pin moved on.

Run ruff **from the repo root**, which is what CI does:

```bash
# Python — run FROM THE REPO ROOT, mirrors CI exactly.
# Covers every member and tests/ in one pass.
uv run ruff check .          # CI: "Ruff lint"
uv run ruff format --check . # CI: "Ruff format check"

# Frontend
cd curator-frontend
npm run lint

# Explorer
cd ../graphexplorer-frontend
npm run lint
```

The root config sets `src = ["curator-backend", "dataexplorer-backend", "rfdb-core"]`.
That is load-bearing: ruff's isort infers first-party packages from `src`, so without it
`core`, `api`, `models` and `scripts` would be classified as third-party and ruff would
demand they merge into the `fastapi`/`rdflib` import block. **Add any new member to that
list** — the symptom of forgetting is a batch of I001 errors in the new service only.

### Gotcha: `ruff: command not found` / `pyenv: ruff`

If you see `pyenv: ruff: command not found (exists in 3.8.14)`, uv did not resolve
the workspace environment:

- The one Python env is the **root** `.venv`, and `.venv/bin/ruff` is the sole ruff
  install. `uv run` finds it from the root or from any member directory, since uv
  walks up to the workspace root.
- A stale `VIRTUAL_ENV` pointing at a deleted venv triggers a harmless
  `VIRTUAL_ENV does not match` warning; uv ignores it. Run `deactivate` to clear it.
- `uv run ruff check .` needs no manual `source .venv/bin/activate` — uv resolves
  the environment itself. If it still fails, run `uv sync --all-extras --dev`.
- Historical note: ruff genuinely could not run from the repo root before the
  workspace existed, because there was no project there. That is no longer true, and
  running from the root is now the *correct* invocation — it is the only one that
  also checks `rfdb-core/`.

## Notes

- Do not rely on a root Python package named `rfdbtools`; this repository is a standalone editor stack.
- The `graphexplorer-frontend/` app (read-only graph visualizer) is an active, first-class frontend — set it up, lint, and build it alongside `curator-frontend/` (see the sections above). Treat only commands referencing Excel generation or ontology download pipelines as legacy unless explicitly reintroduced.
