# backend/Dockerfile
#
# Development image for the FastAPI + uvicorn backend.
#
# This image is used by docker-compose.yml with a source bind-mount
# (./backend:/app) and uvicorn --reload for hot-reloading.
# It is NOT a hardened production image — for production, remove --reload,
# add a non-writable filesystem, and consider a multi-stage build to
# exclude build tools from the final image.

# Pin the full patch version so `docker build` is fully reproducible.
# Update deliberately when you want to take a new Python release.
FROM python:3.12-slim

# PYTHONUNBUFFERED: sends stdout/stderr straight to docker logs without
#   stdio buffering.  Without this, uvicorn output can be held in the buffer
#   and never appear if the process crashes before flushing.
#
# PYTHONDONTWRITEBYTECODE: stops Python from writing .pyc bytecode cache
#   files to disk.  Correct for this dev image because:
#     - The compose bind-mount (./backend:/app) means any .pyc files
#       written inside the container land on the HOST filesystem, owned by
#       uid 1001 (appuser).  Your host user cannot easily delete them.
#     - uvicorn --reload restarts the process on every file change anyway,
#       so the compile-vs-read-cache saving is unmeasurable in practice.
#   PRODUCTION NOTE: remove this flag in a production image and instead
#   pre-compile explicitly during the build with:
#     `RUN python -m compileall -q .`
#   This bakes bytecode into the image layers so cold starts are fast,
#   without polluting any mounted filesystem.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1


WORKDIR /app


# Copy and install dependencies before the source so this layer is cached
# as long as requirements.txt does not change.
#
# Security note: for stronger supply-chain guarantees, generate your
# requirements.txt with `pip-compile --generate-hashes` and add
# `--require-hashes` here so the build fails if any package has been
# tampered with since the lockfile was created.
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source.  In development the compose bind-mount overlays
# this at runtime; this layer makes the image self-contained if run
# without a mount (e.g. in CI or production).
COPY backend/ .

# Drop to a non-root user for defence-in-depth.
# python:slim does not ship a pre-created app user, so we create one
# explicitly with a fixed uid/gid for auditability.
RUN addgroup --system --gid 1001 appgroup && \
    adduser  --system --uid 1001 --ingroup appgroup --no-create-home appuser

USER appuser

EXPOSE 8000

# Production-safe default: no --reload.
# docker-compose.yml overrides this with --reload for local development.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
