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

## Non-Interactive Mode

```bash
git rebase --continue --no-edit
```

Never rely on interactive editors during automated flows.

## Before Every Commit

```bash
git status
cd backend && uv run python -m pytest -c pyproject.toml ../tests/ -v
cd ../frontend && npm run lint
```

Adjust checks to changed areas (for example frontend-only updates).

## Destructive Commands and File Deletion (Mandatory)

A wrong-directory `rm` once deleted the backend project files. Never let it happen again:

1. **Never `rm` a tracked or real project file.** For tracked files use `git rm -- <explicit-path>` (reversible via `git restore`). Never `rm -rf` a path you did not create this session.
2. **Never rely on the shell's current directory.** The working directory drifts between calls. Always use absolute paths, and print `pwd` + `ls <target>` in the *same* command immediately before any removal.
3. **Confirm with the user before deleting any non-`.temp/` file**, tracked or untracked — show the exact absolute paths first.
4. Deletions are scoped like staging: only the exact paths the user approved, one reviewable step at a time. Never bulk-delete with globs or `find -delete`.

## Hook Notes

The repo tracks `.pre-commit-config.yaml` (ruff lint + format, scoped to `backend/*.py`). It is **opt-in** — each clone must run `pre-commit install` once to activate the git hook; it is not enforced automatically. Run manually with `pre-commit run --all-files`.

The hooks `cd backend` and run `uv run ruff …` — identical to CI's `working-directory: backend`. This matters because ruff infers first-party imports from the working directory: running from `backend/` (both hook and CI) agrees; running from the repo root does not. Running from `backend/` also means the ruff version comes from `backend/pyproject.toml`'s dev dependency, so there is no separate version to pin. The hook drops any stale `VIRTUAL_ENV` (`env -u`) so `uv` resolves `backend/.venv` without a warning.
