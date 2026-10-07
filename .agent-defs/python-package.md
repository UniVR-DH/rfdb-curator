# Python package conventions

`code-style.md` holds the general conventions, including type hints, private
helpers, configuration and dependencies. In Python:

- Type hints use `X | None` unions, not `Optional[X]`.
- `logging.getLogger(__name__)` per module. No `print()` in package code; CLI
  progress output is the exception.
- Configuration is read with `os.environ.get("NAME", default)` at module level.
- Module docstrings explain why the module exists.
- Blocking CPU work called from an `async def` route goes through a thread pool,
  never inline.
- The package manager is uv add / uv lock: `pyproject.toml` and the lockfile are
  edited through it.

## Checks

```bash
uv run --offline ruff check .
uv run --offline pytest -q
```

`--offline` stops a moved lockfile from turning a test run into a download. If
it fails for a missing package, ask before syncing.

These are the commands for a single package. In a uv workspace, where the root
`pyproject.toml` has a `[tool.uv.workspace]` table, run the tests per member
instead, `uv run --offline --directory <member> pytest -q`: pytest run from the
root collects every member under one rootdir, and two members shipping the
same top-level package name shadow each other. Where this repository's own
rules name its check commands, those win.

Run them, and still reason about correctness explicitly rather than treating
green as proof. Say plainly when a change is unverified.

## Version bumps

A bump here touches `pyproject.toml`, any deployment manifest and the lockfile,
which is why `code-style.md` asks for the exact number before any of them.
