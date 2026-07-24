# Deployment & Operations — RossijskijFeatrDB

This document covers two distinct things:

1. **[Development & Testing Deployment](#development--testing-deployment)** — how the
   local `docker-compose.yml` stack is configured, seeded, and reset. This is the
   detailed reference behind the lean [Quick Start](../README.md#quick-start) in the root
   README (which covers only the commands to get running).
2. **[Production Deployment](#production-deployment-work-in-progress)** — the intended
   production design and its **work-in-progress** status. There is no working production
   deployment yet; that section is an implementation plan, not a runbook.

---

## Development & Testing Deployment

The development and testing stack is the `docker-compose.yml` at the repository root. Get
it running with the [Quick Start](../README.md#quick-start); the sections below document
the configuration knobs, the data-reset modes, and the seed sources it uses.

### Configuration

All backend settings are loaded from environment variables. No defaults are hardcoded in
the Python source; the backend fails fast with a clear validation error if a required
variable is missing or has the wrong type.

Configuration source of truth:

- Runtime wiring: `docker-compose.yml`
- Backend settings model: `backend/core/config.py`
- Backend dependency set: `backend/pyproject.toml`

For Docker Compose, edit the `environment:` block in `docker-compose.yml`. `OXIGRAPH_URL`
uses the Docker-internal hostname since backend and store are separate services;
`SCHEMA_PATH`/`VOCAB_PATH`/`DATA_PATH` are container paths backed by the `volumes:` mounts
(change both together).

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

The S3/object-storage (`S3_*`) and Garage (`GARAGE_RPC_SECRET`) variables consumed by the
compose file are generated into `.env` by `scripts/env-init.sh`; see the
[Quick Start](../README.md#quick-start). Backend log/troubleshooting details are in
[development.md](development.md).

### Data reset modes

Startup behavior is controlled by `RESET_DATA_ON_STARTUP`.

**Clean slate (empty store)** — clears all triples from `DATA_GRAPH_URI` before seeding.

```bash
RESET_DATA_ON_STARTUP=true docker compose up --build
```

**Preserve existing data (default)** — keeps existing triples and merges new seed data on top.

```bash
docker compose up --build
```

In both modes, the controlled vocabulary from `data/vocab.ttl` is loaded on every startup
(idempotent) when `SEED_VOCAB_ON_STARTUP=true`. Test fixture data from `data/data.ttl` is
loaded only when `SEED_TEST_DATA_ON_STARTUP=true` (off by default outside test
environments).

### Data seeding

The application distinguishes between controlled vocabulary and test fixture data. Default
policy: seed vocabulary on, seed test data off, preserve existing data on.

- `data/vocab.ttl` is the canonical seed source for controlled vocabulary (core types and role types).
- `dcterms:LinguisticSystem` vocabulary relies on [Glottolog v5.3](https://glottolog.org/meta/downloads) data, imported from `data/glottolog_language.ttl`. Prefix normalization is already applied to the committed file. Only if you re-download a fresh version from glottolog.org, replace `geo1:` with `geo:`:

  ```bash
  sed -i '' 's/geo1:/geo:/g' data/glottolog_language.ttl
  ```

- `data/data.ttl` is test-only fixture data.

---

## Production Deployment (Work in Progress)

> **Status — not production ready.** A hardened production deployment is **planned but not
> yet functional.** `docker-compose.prod.yml` exists as a draft, but the pieces it depends
> on are missing (see [Open gaps](#open-gaps) below) and it also predates the object-storage
> subsystem. Do not deploy this stack to a public or shared environment. This section
> documents the intended design and the work remaining, not a procedure you can run today.

### Target topology

A single Docker host running `docker-compose.prod.yml`:

- A **`proxy`** service (Caddy) terminates TLS and reverse-proxies `/` to the frontend and
  `/api` to the backend; it is the only service that publishes ports (80/443).
- **`oxigraph`**, **`backend`**, and **`frontend`** run on an internal network with no
  published ports — reachable only through the proxy.
- Automatic HTTPS via Caddy/ACME (Let's Encrypt), so the domain's DNS must resolve to the
  host's public IP before the proxy starts.
- The only stateful volume is `oxigraph_data`; back it up on a schedule.

### Open gaps

These must be built before the production stack can run:

- **`proxy/Caddyfile` does not exist.** Needs the real domain and routing rules (frontend
  for `/`, backend for `/api`).
- **The production `frontend/Dockerfile` build stage does not exist.** The current
  Dockerfile only runs the Vite dev server; production needs a stage that runs
  `npm run build` and serves `dist/` from a static web server (e.g. nginx).
- **Object storage (Garage) is absent from `docker-compose.prod.yml`.** The dev stack
  depends on Garage for digital-copy (PDF) uploads, but the prod compose file defines only
  oxigraph/backend/frontend/proxy and no `S3_*` configuration. Digital-copy upload and
  retrieval would be non-functional until a production object-storage service and its
  bootstrap/secret handling are added.
- **`.env.prod` scope is incomplete.** `.env.prod.example` currently covers only
  `CORS_ORIGINS`, `VITE_API_BASE`, `READ_ONLY`, and `LOG_LEVEL`; it needs the object-storage
  credentials and any other secrets once the gap above is closed.
- **Log rotation.** `/app/logs/app.jsonl` (in the `backend_logs` volume) is not rotated by
  Docker; a rotation/cleanup job or a switch to stdout-only logging is needed.

### Planned procedure

Once the gaps above are closed, the intended deployment procedure is roughly:

1. **Host prerequisites** — Docker Engine + Compose v2 (`docker compose version` shows v2.x).
   Firewall: allow inbound 80/443 only; explicitly close 7878/8000/5173 if a prior dev
   deployment opened them.
2. **Get the files onto the host** — clone the repo; `chmod o+r -R schema data` (the backend
   runs as uid 1001 and mounts them read-only). Decide whether to reuse or discard any
   existing `oxigraph_data` volume from prior dev runs.
3. **Write the missing pieces** — the production `frontend/Dockerfile` build stage and
   `proxy/Caddyfile` (see [Open gaps](#open-gaps)).
4. **Configure environment** — `cp .env.prod.example .env.prod`, fill in real values. The
   compose file refuses to start if `CORS_ORIGINS` or `VITE_API_BASE` are unset.
   `READ_ONLY_SHAPES` is hardcoded consistently in both compose files, so it needs no
   env-file knob.
5. **Build and start** — `docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build`.
6. **Verify** — all services healthy (`docker compose -f docker-compose.prod.yml ps`);
   `curl -I https://<domain>` and `https://<domain>/api/health` succeed; confirm from
   outside the host that 7878/8000/5173 are unreachable.

### Ongoing operations (once live)

- **Redeploy after code changes**: `git pull`, then repeat step 5 — `--build` rebuilds only
  changed images.
- **Back up `oxigraph_data`** on a schedule matching your data-loss tolerance:

  ```bash
  docker run --rm -v rfdb_oxigraph_data:/data -v $(pwd):/backup \
    alpine tar czf /backup/oxigraph_data_$(date +%F).tar.gz -C /data .
  ```

- **`docker compose down -v` destroys `oxigraph_data`** (and, in the dev stack, the Garage
  volumes). Use `docker compose down` without `-v` for routine stop/start.
