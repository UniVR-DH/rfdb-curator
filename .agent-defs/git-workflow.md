# Git Workflow

## Commit Pattern

Every commit must include the `[BOT]` flag:

```bash
git commit -m "[BOT] <area>: <description>"
```

**Commit Categories**

```
[BOT] schema: Add optional fabio:isPortrayalOf to SourceShape
[BOT] data: Update L11a example with publication metadata
[BOT] refactor: Reorganize validator module
[BOT] test: Add SHACL validation tests
[BOT] docs: Update README with Core ontology examples
[BOT] fix: Correct prefix in schema.ttl
```

## Grouping Rules

- **Same topic → one commit** (e.g., all schema changes together)
- **Different topics → separate commits** (e.g., docs commit ≠ schema commit)
- **Extensive changes → group by area** (all Python code, then all schema, then docs)

## Non-Interactive Mode (REQUIRED)

```bash
# ALWAYS use --no-edit for rebase
git rebase --continue --no-edit

# NEVER open interactive editor (vim, nano)
# NEVER use `git commit` without -m flag
```

## Before Every Commit

```bash
# Verify working directory is the repository root
pwd

# Check for uncommitted changes in critical files
git status | grep -E "schema/|.pre-commit-config.yaml"

# Run tests and validation (with venv prefix)
source .venv/bin/activate && python -m pytest tests/ -v
source .venv/bin/activate && python -m rfdbtools.run validate --schema schema/schema.ttl --data data/data.ttl
```

## Pre-commit Hook

The `.pre-commit-config.yaml` enforces ruff and prettier on every commit. Check for changes before editing it.

## Tag Discipline

Always check Git tags before choosing an Excel `--tag` and increment consistently:

```bash
git tag -l --sort=version:refname
```

Never derive tags from existing filenames alone.
