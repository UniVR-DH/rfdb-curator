# Secrets and network access

## Secrets

- `.env` and friends are gitignored and stay that way. `.env.example` holds
  placeholder keys only, never real values.
- Never echo, log, or paste a secret value into a commit message, a document, a
  scratch file, or chat.
- A value that has ever been committed is compromised forever, whatever the
  current tree looks like. Never reproduce one anywhere, including in a
  deployment secret.
- Deployment secrets are created imperatively on the platform, never written to
  a file in this workspace, not even a gitignored one, because workspace files
  are read by editor extensions and agents.
- Never run any credential command: `docker login`, `aws configure`,
  `npm login`, `gh auth login`, `oc login`, `vercel login`, `netlify login`.
  Deployment against the real host is the user's to run, or CI's.
- Double-check file contents, not just filenames, before staging anything that
  looks credential-shaped.

## Network access

Reaching any host other than localhost is the user's call. Ask first, every
time, and wait for a yes. A yes covers the requests it was given for, not the
next ones.

Each request states:

- the exact URL or host, and what will be sent to it;
- why it is needed;
- whether it is required or nice to have. Required means the task cannot be
  finished without it. Nice to have means the task is done and the request
  would only add a check or a detail. Say what is lost if the user declines.

When a task needs several requests, such as a run of web searches, list them
together and ask once. The yes covers that list and nothing added to it later.

This covers every way of reaching the network:

- `curl`, `wget`, `ssh`, `scp`, `rsync`, `nc`;
- HTTP from code: `requests`, `urllib`, `pandas.read_csv` on a URL, any script
  that downloads;
- web fetch and web search tools, and any MCP tool backed by a remote service;
- `git fetch`, `git pull`, `git clone`, `git ls-remote`, `git push`, `gh`;
- package installs and syncs: `uv sync`, `uv add`, `uv lock`, `uv pip`, `uvx`,
  `pip install`, `npm install`, `npm ci`, `npx`, `pnpm`, `yarn`;
- image pulls: `docker pull`, and `docker compose pull`, `build` or `up` when an
  image is not already local.

It applies even when nothing private is sent, such as looking up a public
exchange rate: do the work offline, then propose the lookup.

Use a tool's offline mode where it has one. Plain `uv run` syncs the
environment, and downloads, whenever the lockfile has moved; `uv run --offline`
does not.

The permission rules in `.claude/settings.json` prompt for the common commands
above, but they cannot see a URL opened from inside a script. This rule covers
what they miss.
