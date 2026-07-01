# frontend/Dockerfile
#
# Development image for the Vite + React frontend.
#
# This image is used by docker-compose.yml with a source bind-mount
# (./frontend:/app) and the Vite dev server (npm run dev).
# It is NOT a production build image — for production, add a separate
# multi-stage build that runs `npm run build` and serves the dist/ folder
# via nginx or a static host.

# Pin the full patch version so `docker build` is fully reproducible.
# Update deliberately when you want to take a new Node release.
FROM node:20.20-bookworm-slim

# Ensures logs appear immediately in `docker logs` (no stdio buffering).
ENV NODE_ENV=development \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    NPM_CONFIG_FUND=false

WORKDIR /app

# Copy manifests first so that the `npm ci` layer is cached as long as
# package-lock.json does not change — source changes do not bust this layer.
COPY frontend/package.json frontend/package-lock.json ./

# `npm ci` installs exactly what is in package-lock.json and fails if the
# lockfile is out of sync with package.json.  It is faster and safer than
# `npm install` inside Docker because it never mutates the lockfile.
RUN npm ci

# Copy the rest of the source.  In development the compose bind-mount
# overlays this at runtime, so this layer primarily serves the production
# build path and makes the image self-contained if run without a mount.
COPY frontend/ .

# Ensure correct ownership when switching user (important if no bind mount)
RUN chown -R node:node /app

# Drop to a non-root user for defence-in-depth.  If a dependency or the
# dev server is compromised, the attacker is unprivileged inside the container.
# `node:slim` ships the `node` user (uid 1000) for exactly this purpose.
USER node


EXPOSE 5173
# `--host 0.0.0.0` makes the dev server reachable from outside the container.
# The compose `command:` key can override this if needed.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
