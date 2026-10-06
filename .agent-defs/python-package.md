# Python package conventions

- Type hints on public functions. `X | None` unions, not `Optional[X]`.
- `logging.getLogger(__name__)` per module. No `print()` in package code; CLI
  progress output is the exception.
- Config comes from `os.environ.get("NAME", default)` at module level, with the
  default matching what the deployment config sets.
- Private helpers are `_prefixed`. Module docstrings explain why the module
  exists.
- Blocking CPU work called from an `async def` route goes through a thread pool,
  never inline.

## Dependencies and the lockfile

**No new runtime dependency without asking.** `pyproject.toml` and the lockfile
are edited through the package manager (uv add / uv lock), never by hand.

Regenerate the lockfile with the version CI pins. An older local tool can
silently rewrite the lockfile format and turn a one-line version bump into a
whole-file diff.

## Checks

```bash
uv run --offline ruff check .
uv run --offline pytest -q
```

`--offline` stops a moved lockfile from turning a test run into a download. If
it fails for a missing package, ask before syncing.

Run them, and still reason about correctness explicitly rather than treating
green as proof. Say plainly when a change is unverified.

## Version bumps

A version lives in more than one place in a Python project: the manifest, any
deployment manifest, the lockfile. Confirm the exact resulting number before
touching any of them, because a wrong guess means re-editing all of them and
throwing the work away.
