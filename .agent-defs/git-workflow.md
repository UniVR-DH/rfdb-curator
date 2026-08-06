# Git Workflow

## Commit Pattern

Every bot-generated commit should include `[BOT]`:

```bash
git commit -m "[BOT] <area>: <description>"
```

## Grouping Rules

- Same topic -> one commit
- Different topics -> separate commits
- Large changes -> group by area (backend, frontend, docs)

### Shared files across commits (Mandatory)

If a proposed multi-commit split would put edits to the **same file** into two
different commits, **STOP and ask the user** how to proceed. Do not try to
separate the changes yourself.

- The default resolution is simple: **assign the shared file to one of the two
  commits, or make a single combined commit.** The user picks.
- **Never** perform manual hunk-splitting workarounds — no backup→revert→
  re-apply, no `git checkout HEAD -- <file>` then re-add, no hand-authored
  partial patches, no per-region reverts to fake a clean split. Interactive
  `git add -p` is unavailable in this environment, and these substitutes are
  error-prone and have caused rework.
- Only ever attempt such a split process on a **double-confirmed, explicit**
  user request that names the process — otherwise ask and take the simple path.

## Non-Interactive Mode

```bash
git rebase --continue --no-edit
```

Never rely on interactive editors during automated flows.

## Before Every Commit

```bash
git status --short
uv run ruff check . && uv run ruff format --check .        # from the repo ROOT
cd curator-frontend && npm run lint                        # when frontend code changed
```

Plus the three Python suites — one run per workspace member, commands in
[testing.md](testing.md) → "Running Tests".

Adjust checks to changed areas (for example frontend-only updates). One exception: a
change to `rfdb-core/` affects **both** services, so run all three suites.

## Destructive Commands and File Deletion (Mandatory)

In `AGENTS.md` §7, alongside the staging rules — same scoping, one place. It covers data as
well as files: `docker compose down -v`, `RESET_DATA_ON_STARTUP=true` and a loose
`DELETE WHERE` are deletions too.

## Hook Notes

The repo tracks `.pre-commit-config.yaml` (ruff lint + format, scoped to every Python workspace member plus `tests/`). It is **opt-in** — each clone must run `pre-commit install` once to activate the git hook; it is not enforced automatically. Run manually with `pre-commit run --all-files`.

The hooks run `uv run ruff …` **from the repo root**, matching CI. That used to require `cd backend`, because ruff inferred first-party imports from the working directory; since `[tool.ruff]` moved to the root `pyproject.toml` with an explicit `src = ["curator-backend", "rfdb-core"]`, the classification no longer depends on cwd — and running from the root is the only invocation that also covers `rfdb-core/` and `tests/`. The ruff version comes from curator-backend's dev dependency, resolved through the workspace's single root `.venv`. The hook drops any stale `VIRTUAL_ENV` (`env -u`) so `uv` resolves that venv without a warning.
