"""Global pytest bootstrap for backend environment variables.

This keeps test collection independent from external CI environment wiring.
"""

from __future__ import annotations

import os


def pytest_configure() -> None:
    """Provide defaults required by backend Settings at import time.

    Existing values from the shell/CI are preserved.
    """
    os.environ.setdefault("OXIGRAPH_URL", "http://localhost:7878")
    os.environ.setdefault("DATA_GRAPH_URI", "https://rfdb.it/graph/data")
    os.environ.setdefault("SCHEMA_PATH", "schema/schema.ttl")
    os.environ.setdefault("VOCAB_PATH", '["data/vocab.ttl"]')
    os.environ.setdefault("DATA_PATH", "data/data.ttl")
    os.environ.setdefault("RESET_DATA_ON_STARTUP", "false")
    os.environ.setdefault("SEED_VOCAB_ON_STARTUP", "false")
    os.environ.setdefault("SEED_TEST_DATA_ON_STARTUP", "false")
    os.environ.setdefault("CORS_ORIGINS", '["http://localhost:5173"]')
