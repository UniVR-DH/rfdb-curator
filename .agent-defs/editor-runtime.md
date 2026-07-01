# Editor Runtime Diagnostics

## Purpose

Procedures for diagnosing, starting, and monitoring the editor stack (`editor/` — FastAPI backend + React frontend) via Docker Compose.

## Scope

- Focus by default on editor frontend and backend services.
- Include additional compose services only when they are direct dependencies or clearly implicated by logs/status.
- Use Docker Compose as the primary runtime interface.

## Constraints

- Do not redesign architecture or change compose configuration unless explicitly asked.
- Do not edit source code unless explicitly asked for a fix.
- Keep repository interactions strict read-only (no file edits, no config changes) unless starting/stopping services.
- Prefer read-only diagnostics first; run recovery commands only when needed to restore service health.
- Avoid destructive operations (e.g. volume removal) unless explicitly asked.

## Preflight Checks

Run before any compose command:

```bash
docker info
docker compose version
```

## Compose Commands

```bash
cd editor
docker compose up          # start in background
docker compose up --build  # rebuild and start
docker compose down        # stop
docker compose logs -f     # follow logs
docker compose ps          # service status
docker compose restart     # restart services
```

## Startup Report

When starting the editor web app:

1. Run preflight checks.
2. Start services: `docker compose up --build`
3. After startup, provide a report with:
   - **Startup Result:** started / blocked
   - **Test URL:** `http://localhost:3000` (frontend)
   - **Secondary URL:** `http://localhost:8000/api/health` (backend health check)

## Diagnostic Workflow

1. Identify the compose project context (run `pwd`, then `docker compose ps`).
2. Inspect container status, health, and recent lifecycle events.
3. Gather focused logs for relevant services (tail limits with timestamps).
4. Correlate frontend and backend failures (e.g. proxy errors matching API failures).
5. Report findings with root cause, confidence level (high/medium/low), and minimal-risk next steps.

## Log Examination

```bash
# Backend logs
docker compose logs --tail=100 backend

# Frontend logs
docker compose logs --tail=100 frontend

# All services
docker compose logs --tail=50
```

## Health Verification

```bash
# Backend API
curl http://localhost:8000/api/health

# Frontend
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
```

## Troubleshooting Tips

- **Frontend proxy errors** (`/api` 502/504) → check backend container health and logs.
- **Hot reload not picking up changes** → verify volume mounts in `editor/docker-compose.yml`.
- **CORS errors** → check backend `CORS_ORIGINS` setting and frontend `VITE_API_URL`.
- **Oxigraph not ready** → backend logs will show SPARQL connection failures; wait for full startup.
