# explorer/Dockerfile
#
# Development image for the Vite + React read-only Explorer.
#
# Used by docker-compose.yml with a source bind-mount (./explorer:/app) and the
# Vite dev server (npm run dev). NOT a production build image — for a hardened
# deploy, add a multi-stage build that runs `npm run build` and serves dist/
# from a static host (nginx/Caddy).

# Pin the full patch version so `docker build` is reproducible.
FROM node:20.20-bookworm-slim

# npm ci skips devDependencies when NODE_ENV=production, and vite is a
# devDependency — pin development so the dev server installs correctly.
ENV NODE_ENV=development \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    NPM_CONFIG_FUND=false

WORKDIR /app

# Copy manifests first so `npm ci` is cached while the lockfile is unchanged.
COPY --chown=node:node explorer/package.json explorer/package-lock.json ./

# WORKDIR creates /app as root; hand it to node so it can write node_modules.
RUN chown node:node /app

USER node

RUN npm ci --no-audit

# Copy the rest; the compose bind-mount overlays this at runtime. Requires
# explorer/.dockerignore excluding node_modules so a host node_modules can't
# clobber the container's native binaries.
COPY --chown=node:node explorer/ .

EXPOSE 5174
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
