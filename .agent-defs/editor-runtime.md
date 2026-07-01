# Runtime Diagnostics

## Purpose

Procedures for diagnosing, starting, and monitoring the standalone runtime stack (backend + frontend + Oxigraph) via Docker Compose.

## Scope

- Focus on `backend`, `frontend`, and `oxigraph` services.
- Include additional services only when they are direct dependencies.
- Use Docker Compose as the primary runtime interface.

## Preflight Checks

```bash
docker info
docker compose version
```

## Compose Commands

Run from repository root:

```bash
docker compose up
docker compose up --build
docker compose down
docker compose logs -f
docker compose ps
docker compose restart
```

## Startup Report

When starting the web app, report:

1. Startup result: started or blocked
2. Frontend URL: `http://localhost:5173`
3. Backend health URL: `http://localhost:8000/health`

## Log Examination

```bash
docker compose logs --tail=100 backend
docker compose logs --tail=100 frontend
docker compose logs --tail=50
```

## Health Verification

```bash
curl http://localhost:8000/health
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173
```

## Troubleshooting Tips

- **Frontend proxy errors (`/api` 502/504):** inspect backend health and logs.
- **Hot reload not picking up changes:** verify bind mounts in `docker-compose.yml`.
- **CORS errors:** verify backend `CORS_ORIGINS` and frontend API base/proxy settings.
- **Oxigraph startup delays:** backend startup includes readiness retries before seeding.
