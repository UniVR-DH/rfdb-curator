# Runtime Diagnostics

## Purpose

Procedures for diagnosing, starting, and monitoring the standalone runtime stack (backend + frontend + Oxigraph + Garage) via Docker Compose.

## Scope

- Focus on `backend`, `frontend`, `oxigraph`, and `garage` services.
- `garage` is the S3-compatible object store for digital copies; the backend depends on it only when file-upload features are exercised.
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

## Browser Verification (Mandatory)

Never open, launch, or drive a browser (Playwright, Puppeteer, headless Chrome, or similar) to verify frontend changes. Do not install or invoke browser-automation tooling for this purpose.

Instead: verify what is verifiable without a browser (API responses via `curl`, backend tests, lint/build), then tell the user the change is ready for them to test manually in their own browser and report back what they see.

## Previewing an inline SVG (e.g. the WelcomeGuide WEMI diagram)

To eyeball an SVG that lives inside a React component (no browser needed), render
it to PNG with macOS Quick Look and Read the PNG:

```bash
qlmanage -t -s 1000 -o <scratchpad-dir> diagram.svg   # writes diagram.svg.png
```

Two gotchas, both one-time:

- **Quick Look emits a square `s×s` thumbnail.** Portrait content fit to width
  overflows and the bottom is cropped. Fix: pad the standalone SVG's `viewBox`
  (and `width`/`height`) to roughly square/landscape so nothing is cut — this is
  preview-only; leave the real component's viewBox alone.
- **Component SVGs use CSS classes from a stylesheet**, so a standalone copy
  renders unstyled (lines have no stroke → invisible). Inline a `<style>` block
  with concrete values (copy from the component's `.css`), and add a dark
  background `<rect>` when the UI is dark-themed. Then paste the component's
  `<g>/<line>/<text>` markup verbatim.

No install needed (`qlmanage` ships with macOS). Do NOT rasterize via a headless
browser — same rule as Browser Verification above.

## Troubleshooting Tips

- **Frontend proxy errors (`/api` 502/504):** inspect backend health and logs.
- **Hot reload not picking up changes:** verify bind mounts in `docker-compose.yml`.
- **CORS errors:** verify backend `CORS_ORIGINS` and frontend API base/proxy settings.
- **Oxigraph startup delays:** backend startup includes readiness retries before seeding.
