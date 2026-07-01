"""Startup data seeder for the Oxigraph triple store.

The seeder runs once inside the FastAPI lifespan on every startup.  Its job
is to ensure the store contains the baseline controlled-vocabulary triples
that relation fields (EntitySearch) rely on for autocomplete.

Design notes:
  - `vocab.ttl` is idempotent: Oxigraph merges triples rather than replacing,
    so re-seeding on every restart is safe.
  - `data.ttl` is for development and testing only; it is never seeded in
    production unless explicitly enabled via `SEED_TEST_DATA_ON_STARTUP=true`.
"""

from __future__ import annotations

from pathlib import Path


def _seed_turtle_file(oxigraph, file_path: str) -> dict:
    """Load a single Turtle file into Oxigraph and return a status dict.

    Returns ``{'path': ..., 'loaded': False, 'reason': 'missing'}`` when the
    file does not exist rather than raising, so the startup report remains
    informative even in environments where some files are absent.
    """
    path = Path(file_path)
    if not path.exists():
        return {"path": str(path), "loaded": False, "reason": "missing"}

    turtle_data = path.read_text(encoding="utf-8")
    oxigraph.load_turtle(turtle_data)
    return {"path": str(path), "loaded": True}


def seed_store(
    oxigraph,
    vocab_path: str,
    test_data_path: str,
    seed_vocab: bool,
    seed_test_data: bool,
) -> dict:
    """Seed Oxigraph on startup.

    Policy:
    - vocab.ttl is canonical and should be seeded by default.
    - data.ttl is test fixture and is optional/off by default.
    """
    report = {
        "seedVocab": bool(seed_vocab),
        "seedTestData": bool(seed_test_data),
        "results": [],
    }

    if seed_vocab:
        report["results"].append(_seed_turtle_file(oxigraph, vocab_path))

    if seed_test_data:
        report["results"].append(_seed_turtle_file(oxigraph, test_data_path))

    return report
