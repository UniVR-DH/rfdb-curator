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

# NODE_ENV=development is not cosmetic: npm ci skips devDependencies when
# NODE_ENV=production, and vite is a devDependency. Pinning it here means
# the dev server installs correctly regardless of the ambient environment.
ENV NODE_ENV=development \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    NPM_CONFIG_FUND=false

WORKDIR /app

# Copy manifests first so `npm ci` is cached as long as package-lock.json
# doesn't change. --chown avoids a root-owned tree that would otherwise
# need a separate `RUN chown -R` layer later (which duplicates node_modules
# on overlay2 storage drivers via copy-up).
COPY --chown=node:node frontend/package.json frontend/package-lock.json ./

# WORKDIR creates /app as root before any USER switch. COPY --chown only
# changes ownership of the files it copies, not the /app directory entry —
# node still can't write into it (e.g. mkdir node_modules) without this.
RUN chown node:node /app


# Drop root before installing — nothing in a dependency's install script
# needs root in the build environment, and node_modules ends up correctly
# owned from the start.
USER node

# npm ci installs exactly what's in the lockfile and fails if it's out of
# sync with package.json. --no-audit skips an unnecessary registry call.
RUN npm ci --no-audit

# Copy the rest of the source. In development the compose bind-mount
# overlays this at runtime; this layer mainly makes the image
# self-contained if it's ever run without the mount.
# Requires a frontend/.dockerignore excluding node_modules/dist/.git —
# otherwise a host node_modules (with host-arch native binaries, e.g.
# esbuild) will clobber the one just installed above.
COPY --chown=node:node frontend/ .

EXPOSE 5173
# --host 0.0.0.0 makes the dev server reachable from outside the container.
# The compose `command:` key can override this if needed.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]