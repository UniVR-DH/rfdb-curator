# Testing

## Running Tests

```bash
source .venv/bin/activate && python -m pytest tests/ -v
```

Or via Makefile:

```bash
make test
```

## Test Structure

```
tests/
├── test_rfdbtools.py            # Core validator and round-trip tests
└── test_excel_generator.py      # Excel generation tests
```

## Test Docstrings (Required)

Every test function must include a minimal docstring. State the test purpose and the expected semantic behavior — what should happen and why.

Keep docstrings concise (one sentence is usually enough) and specific to the assertion intent.

```python
def test_source_shape_validation():
    """Validate source data against schema"""
    from rfdbtools.validator import validate_shacl
    report = validate_shacl('schema/schema.ttl', 'data/data.ttl')
    assert report.conforms, f"Validation failed: {report}"

def test_bfs_shape_edges_is_deterministic_and_cycle_safe():
    """BFS path discovery is stable and terminates even with cycles."""
    ...
```

## Before Committing

1. Run full test suite: `source .venv/bin/activate && python -m pytest tests/ -v`
2. Check no uncommitted changes: `git status`
3. Verify venv is active: `source .venv/bin/activate && echo $VIRTUAL_ENV`

## Pre-commit Requirements

Tests and validation must pass before any commit. The pre-commit hook enforces ruff and prettier formatting.
