# Testing

## Running Tests

One pytest run per Python workspace member — three commands, three interpreters. **This is the
canonical copy**; `AGENTS.md` §4 repeats it for quick reference, and nothing else should.

```bash
# `uv run` resolves the workspace venv at the REPO ROOT from any member directory —
# no manual `source .venv/bin/activate` needed.
cd rfdb-core               && uv run python -m pytest -c pyproject.toml ../tests/core -v
cd ../curator-backend      && uv run python -m pytest -c pyproject.toml ../tests/curator -v
cd ../dataexplorer-backend && uv run python -m pytest -c pyproject.toml ../tests/dataexplorer -v
```

`-c pyproject.toml` is needed because pytest cannot auto-discover a member's config
from `../tests/` — the member directory is not an ancestor of the test files. Each
member's `testpaths` also names its own subdirectory, so a bare `pytest` inside a
member picks up the right suite.

**Why three runs and not one.** curator-backend and dataexplorer-backend both own a
top-level `api` package. In a single process `from api.data import …` resolves to
whichever service was imported first and `sys.modules` caches it, so half the suite
would silently test the wrong service. Separate processes make that impossible
rather than merely unlikely. (Decision D2 in the modular-services refactor plan.)
CI mirrors this with one job per member.

## Test Structure

One subdirectory per component, each collected by that component's pytest config:

```text
tests/
├── conftest.py            # shared env: the BaseServiceSettings variables only
├── core/                  # rfdb-core — schema constraints, prefixes, store seam
│   ├── test_schema_constraints.py
│   ├── test_class_targeted_validation.py
│   └── test_triplestore_contract.py
├── curator/               # curator-backend — writes, validation, seeding, staging
│   ├── conftest.py        # writer-only env: VOCAB_PATH, SEED_*, RESET_*
│   ├── test_backend_api_data.py       # live HTTP; spans BOTH services (see below)
│   ├── test_backend_app_startup.py
│   ├── test_digital_copies.py         # staging, reconciliation, cleanup
│   └── ...
└── dataexplorer/          # dataexplorer-backend — reads, graph, meta
    ├── test_app_contract.py           # structural: no writes, 3 app.state entries
    ├── test_api_data_read.py          # list/counts/get, incl. empty-store tolerance
    ├── test_digital_copies_read.py    # download + /meta/files
    ├── test_api_graph.py
    └── test_api_meta.py
```

A test belongs to the component whose code it imports. Where a subject spans both
(the SHACL semantics the write path relies on, say), it goes to `tests/core/` if it
imports no service module.

`tests/curator/test_backend_api_data.py` is the exception worth knowing about: it
POSTs to curator-backend and reads back from dataexplorer-backend, so it needs both
services up and skips otherwise. Override `RFDB_API_BASE_URL` /
`RFDB_READ_API_BASE_URL` to point it at a deployed stack.

## Test Docstrings

Test functions should include concise docstrings describing the intent and expected behavior.

## Before Committing

1. Run all three Python suites (see *Running Tests*) — a change to `rfdb-core`
   affects both services, so running only one is not enough.
2. Run frontend lint/build when frontend code changed.
3. Check working tree state with `git status`.

## Hook Notes

Pre-commit hooks are ruff-only and **opt-in** (`pre-commit install` once per clone) — they do
not run the test suites, so the three commands above are still on you. Details:
[git-workflow.md](git-workflow.md) → "Hook Notes".
