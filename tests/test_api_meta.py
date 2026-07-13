"""Unit tests for GET /api/meta/prefixes.

Creates a minimal FastAPI app with a stubbed schema_extractor on app.state,
so no Oxigraph connection or full lifespan is needed.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from rdflib import Graph
from rdflib.namespace import NamespaceManager


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _make_test_app(graph: Graph) -> FastAPI:
    """Build a minimal FastAPI app with the meta router and a stub schema_extractor."""
    from api.meta import router

    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.state.schema_extractor = SimpleNamespace(graph=graph)
    return app


def _graph_with_prefixes(pairs: dict[str, str]) -> Graph:
    """Build an rdflib Graph pre-loaded with the given prefix-to-namespace pairs."""
    g = Graph()
    for prefix, ns in pairs.items():
        g.bind(prefix, ns)
    return g


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_get_prefixes_returns_200_with_prefixes_key() -> None:
    """Response is 200 and top-level JSON has a 'prefixes' key."""
    g = _graph_with_prefixes({"rfdb": "https://rosfeatr.eu/rdf/data/"})
    client = TestClient(_make_test_app(g))
    res = client.get("/api/meta/prefixes")
    assert res.status_code == 200
    assert "prefixes" in res.json()


def test_get_prefixes_contains_bound_prefixes() -> None:
    """Every explicitly bound prefix appears in the response."""
    pairs = {
        "rfdb": "https://rosfeatr.eu/rdf/data/",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    }
    g = _graph_with_prefixes(pairs)
    client = TestClient(_make_test_app(g))
    prefixes = client.get("/api/meta/prefixes").json()["prefixes"]

    for prefix, ns in pairs.items():
        assert prefix in prefixes, f"Expected prefix '{prefix}' in response"
        assert prefixes[prefix] == ns, f"Expected '{prefix}' → '{ns}', got '{prefixes[prefix]}'"


def test_get_prefixes_excludes_empty_string_key() -> None:
    """The empty-string base-IRI entry that rdflib always includes must not appear."""
    g = _graph_with_prefixes({"rfdb": "https://rosfeatr.eu/rdf/data/"})
    client = TestClient(_make_test_app(g))
    prefixes = client.get("/api/meta/prefixes").json()["prefixes"]
    assert "" not in prefixes


def test_get_prefixes_against_real_schema() -> None:
    """Against the actual schema.ttl, rfdb and xsd are present with correct namespaces."""
    schema_path = Path(__file__).resolve().parents[1] / "schema" / "schema.ttl"
    g = Graph().parse(str(schema_path), format="turtle")
    client = TestClient(_make_test_app(g))
    prefixes = client.get("/api/meta/prefixes").json()["prefixes"]

    assert "rfdb" in prefixes, "Expected 'rfdb' prefix from schema.ttl"
    assert prefixes["rfdb"] == "https://rosfeatr.eu/rdf/data/", (
        f"Unexpected rfdb namespace: {prefixes['rfdb']}"
    )
    assert "xsd" in prefixes
    assert prefixes["xsd"] == "http://www.w3.org/2001/XMLSchema#"
    assert "" not in prefixes


def test_get_prefixes_is_stable_across_calls() -> None:
    """Two calls to the same app return identical results (graph is not mutated)."""
    schema_path = Path(__file__).resolve().parents[1] / "schema" / "schema.ttl"
    g = Graph().parse(str(schema_path), format="turtle")
    client = TestClient(_make_test_app(g))

    first = client.get("/api/meta/prefixes").json()["prefixes"]
    second = client.get("/api/meta/prefixes").json()["prefixes"]
    assert first == second
