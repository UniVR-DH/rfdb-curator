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
cd backend && source .venv/bin/activate && python -m pytest ../tests -v
cd ../frontend && npm run lint
```

Adjust checks to changed areas (for example frontend-only updates).

## Hook Notes

The repository currently does not track a hook configuration file. Do not assume pre-commit hooks are installed unless the user configured them locally.
