# Testing

## Running Tests

```bash
cd backend
source .venv/bin/activate
python -m pytest ../tests -v
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

No repository-managed hook configuration is currently present (no committed `.pre-commit-config.yaml` or `.githooks/`).
If hook automation is reintroduced, keep this file aligned with the tracked configuration.
