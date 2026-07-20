# Production Deployment — RossijskijFeatrDB

## Assumptions made in `docker-compose.prod.yml`

This file will not run as-is. It assumes the following:

- **`frontend/Dockerfile` has a production build stage.** The compose
  file builds an image via `build.args` (`VITE_API_BASE`) expecting a
  stage that runs `npm run build` and serves the resulting `dist/`
  with a real web server. If your current Dockerfile only runs the
  Vite dev server, this needs to be added first.
- **`proxy/Caddyfile` exists.** The `proxy` service mounts
  `./proxy/Caddyfile` read-only. It isn't included — you need one with
  your actual domain and routing rules (frontend for `/`, backend for
  `/api` or similar) before `docker compose up` will do anything useful
  on 80/443.
- **`.env.prod` exists**, populated from `.env.prod.example`, with real
  values for `CORS_ORIGINS`, `VITE_API_BASE`, `READ_ONLY`, `LOG_LEVEL`.
  `.env.prod.example` is currently untracked in this repo (`git status`
  shows it as `??`) — commit it before relying on step 4 below on a
  fresh clone, or recreate it there with the four variables above.
- **You're running Compose v2** (the `docker compose` plugin, not the
  legacy Python `docker-compose` binary). `deploy.resources.limits` is
  only honored outside Swarm by v2.
- **Single Docker host**, not Swarm or Kubernetes. This is a plain
  compose file; nothing here handles multi-node scheduling or secrets
  distribution.
- **DNS for your domain already points at the VM's public IP** before
  you bring `proxy` up — Caddy's automatic HTTPS (ACME/Let's Encrypt)
  fails otherwise.
- **`schema/`, `data/` on the host are populated and world-readable**
  (`chmod o+r`), since the backend container runs as uid 1001 and
  mounts them read-only.

If any of these aren't true yet, fix those first — the steps below
assume they are.

## 1. Host prerequisites

```bash
# Docker Engine + Compose v2 plugin
docker --version
docker compose version   # must show a v2.x
```

Firewall / cloud security group: allow inbound 80 and 443 only. Do not
open 7878, 8000, or 5173 — the compose file doesn't publish them, but
if a prior dev deployment opened those at the security-group level,
close them explicitly; they're not implicitly closed just because this
compose file stopped mapping them.

## 2. Get the files onto the VM

```bash
git clone <your-repo-url> rfdb
cd rfdb
chmod o+r -R schema data
```

If `oxigraph_data` was previously created by a dev `docker compose up`
on this same host, decide whether prod should reuse that volume or
start clean. Reusing dev data in prod is usually not what you want:

```bash
docker volume ls | grep oxigraph_data
# if it's dev data you don't want, remove it before first prod run:
docker volume rm rfdb_oxigraph_data
```

## 3. Write the missing pieces

- `frontend/Dockerfile`: add a build stage (`npm run build`, then copy
  `dist/` into an nginx or similar static-serving base image).
- `proxy/Caddyfile`: minimal example —

```
rfdb.example.com {
    handle /api/* {
        reverse_proxy backend:8000
    }
    handle {
        reverse_proxy frontend:80
    }
}
```

Adjust the backend path prefix and frontend's internal port to match
whatever your prod frontend image actually listens on.

## 4. Configure environment

```bash
cp .env.prod.example .env.prod
$EDITOR .env.prod
```

Fill in `CORS_ORIGINS`, `VITE_API_BASE`, `READ_ONLY`, `LOG_LEVEL` with
real values — the compose file will refuse to start if `CORS_ORIGINS`
or `VITE_API_BASE` are left unset.

`READ_ONLY_SHAPES` locks the seeded Glottolog language vocabulary
against edits; it's hardcoded the same way in both `docker-compose.yml`
(dev) and `docker-compose.prod.yml`, so this stays consistent across
environments without an env-file knob.

## 5. Build and start

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

## 6. Verify

```bash
docker compose -f docker-compose.prod.yml ps
# all services should show "healthy" once start_period elapses

docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f proxy

curl -I https://rfdb.example.com
curl -I https://rfdb.example.com/api/health
```

Confirm from outside the VM (not just `curl localhost` on the VM
itself) that 7878, 8000, and 5173 are unreachable:

```bash
nc -zv <vm-public-ip> 7878   # should time out / refuse
nc -zv <vm-public-ip> 8000
nc -zv <vm-public-ip> 5173
```

## 7. Ongoing operations

- **Redeploy after code changes**: `git pull`, then repeat step 5 —
  `--build` rebuilds the changed image(s) only.
- **`/app/logs/app.jsonl` (in the `backend_logs` named volume) is not rotated by Docker.**
  The `logging:` block in the compose file bounds Docker's own captured
  stdout/stderr, not this app-level file. Inspect volume logs with:

```bash
docker run --rm -v rfdb_backend_logs:/logs alpine ls -l /logs
docker run --rm -v rfdb_backend_logs:/logs alpine tail -n 200 /logs/app.jsonl
```

  If needed, add a periodic cleanup/rotation job for `backend_logs`, or
  switch the app to stdout-only logging and drop `LOG_FILE` so Docker's
  json-file driver handles rotation.
- **Back up `oxigraph_data`** on whatever schedule matches your
  tolerance for data loss — it's the only stateful volume:

```bash
docker run --rm -v rfdb_oxigraph_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/oxigraph_data_$(date +%F).tar.gz -C /data .
```

- **`docker compose down -v` destroys `oxigraph_data`.** Use
  `docker compose down` (no `-v`) for routine stop/start; reserve `-v`
  for cases where you deliberately want a clean store.