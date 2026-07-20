# Testing

## Running Tests

```bash
cd backend
source .venv/bin/activate
# -c pyproject.toml: pytest can't auto-discover backend/ config from ../tests/.
python -m pytest -c pyproject.toml ../tests/ -v
```

## Test Structure

```text
tests/
├── test_backend_api_data.py
├── test_backend_app_startup.py
├── test_schema_constraints.py
└── ...
```

## Test Docstrings

Test functions should include concise docstrings describing the intent and expected behavior.

## Before Committing

1. Run backend tests.
2. Run frontend lint/build when frontend code changed.
3. Check working tree state with `git status`.

## Hook Notes

The repo tracks `.pre-commit-config.yaml` (ruff lint + format, scoped to `backend/*.py`). It is **opt-in**: run `pre-commit install` once per clone to activate the git hook, and `pre-commit run --all-files` to run it manually — it is not enforced automatically. See `git-workflow.md` → "Hook Notes" for why the hook runs from `backend/`.
