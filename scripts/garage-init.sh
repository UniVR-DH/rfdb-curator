#!/usr/bin/env bash
# scripts/garage-init.sh — DEV Garage bootstrap (runs on the HOST).
#
# WHEN TO RUN
#   Once, after the FIRST `docker compose up` on a fresh Garage volume:
#     • the very first time you bring the dev stack up, or
#     • any time after `docker compose down -v` (that destroys garage_data +
#       garage_meta, so the cluster is empty again).
#   Idempotent — safe to re-run; every step is a no-op if already done.
#
#   You do NOT run it on ordinary `up`/`down` (without -v): the named volumes
#   survive, so the layout, bucket, and key are still there.
#
# WHY IT EXISTS
#   Garage keeps its cluster layout, buckets, and access keys in its metadata
#   DB — none of them can be declared in garage.toml. A fresh volume therefore
#   needs these four steps run once. The Garage image is distroless (no shell,
#   no coreutils — only the /garage binary), so this script runs on the host
#   and drives the CLI through `docker compose exec`.
#
# PREREQUISITES
#   • A `garage` service defined in docker-compose.yml and currently up.
#   • S3_ACCESS_KEY_ID / S3_SECRET_ACCESS_KEY (and optionally S3_BUCKET) set in
#     the repo-root .env — the SAME predefined creds the backend reads, so
#     there is no generated secret to copy back.
#
# PROD: do not use this file as-is (different compose file, env file, network,
#   and hardening). See .temp/temp-garage-prod-bootstrap-20260716.md.

set -euo pipefail

cd "$(dirname "$0")/.."          # repo root, so `docker compose` finds the file + .env

# Read a var from the current environment first, else from .env. We extract
# only the three keys we need rather than sourcing .env, because .env may hold
# values (JSON arrays, spaces) that are not safe to `source` in bash.
from_env() {
  local v="${!1-}"
  [ -n "$v" ] && { printf '%s' "$v"; return; }
  grep -E "^$1=" .env 2>/dev/null | tail -n1 | cut -d= -f2-
}

S3_BUCKET="$(from_env S3_BUCKET)"; : "${S3_BUCKET:=sources}"
S3_ACCESS_KEY_ID="$(from_env S3_ACCESS_KEY_ID)"
S3_SECRET_ACCESS_KEY="$(from_env S3_SECRET_ACCESS_KEY)"
[ -n "$S3_ACCESS_KEY_ID" ]     || { echo "✗ S3_ACCESS_KEY_ID not set (env or .env)";     exit 1; }
[ -n "$S3_SECRET_ACCESS_KEY" ] || { echo "✗ S3_SECRET_ACCESS_KEY not set (env or .env)"; exit 1; }

# Every Garage command is one exec of the distroless binary (-T: no TTY).
g() { docker compose exec -T garage /garage "$@"; }

echo "› waiting for garage RPC…"
tries=0
until g status >/dev/null 2>&1; do
  tries=$((tries + 1))
  [ "$tries" -gt 60 ] && { echo "✗ garage not reachable via 'docker compose exec garage' — is the service defined and up?"; exit 1; }
  sleep 1
done

echo "› cluster layout"
# `node id -q` prints the FULL 64-hex pubkey ("<hex>@host:port"); `layout show`
# prints only the 16-hex short prefix. Match on that prefix so a re-run sees the
# already-applied role and skips (re-assigning + `apply --version 1` would fail
# with "Invalid new layout version" once version 1 already exists).
NODE_ID="$(g node id -q | cut -d@ -f1 | tr -d '\r')"
if ! g layout show | grep -q "${NODE_ID:0:16}"; then
  g layout assign -z dc1 -c 1GB "$NODE_ID"   # -c is a balancing weight, not a quota
  g layout apply --version 1                 # first (and only) layout version is 1
fi

echo "› bucket: $S3_BUCKET"
g bucket info "$S3_BUCKET" >/dev/null 2>&1 || g bucket create "$S3_BUCKET"

echo "› access key"
# import (not create) so the key matches the predefined creds in .env — nothing
# to copy back into the backend's environment.
g key info "$S3_ACCESS_KEY_ID" >/dev/null 2>&1 || \
  g key import --yes -n rfdb-backend "$S3_ACCESS_KEY_ID" "$S3_SECRET_ACCESS_KEY"

echo "› grant read+write on $S3_BUCKET"
g bucket allow "$S3_BUCKET" --key "$S3_ACCESS_KEY_ID" --read --write

echo "✓ garage dev bootstrap complete"
