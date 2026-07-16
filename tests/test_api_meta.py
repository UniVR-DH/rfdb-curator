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


# ---------------------------------------------------------------------------
# GET /api/meta/graphs
# ---------------------------------------------------------------------------

GRAPH_A = "https://rosfeatr.eu/rdf/graph/"
GRAPH_B = "https://rosfeatr.eu/rdf/vocab/"


class _StubOxigraph:
    """Minimal Oxigraph double that routes the three meta/graphs queries by content.

    ``named_rows`` is a list of per-graph dicts with string cells:
    ``{"g", "count", "subjects", "objects", "literals"}``. The stub reshapes them
    into the count/distinct grouped query and the literals grouped query, and
    answers the default-graph count separately.
    """

    def __init__(self, named_rows, default_count="0", totals=None, raise_exc=None):
        self._named_rows = named_rows
        self._default_count = default_count
        self._totals = totals or {"subjects": "0", "objects": "0", "literals": "0"}
        self._raise_exc = raise_exc

    def query(self, sparql: str):
        if self._raise_exc is not None:
            raise self._raise_exc
        grouped = "GROUP BY ?g" in sparql
        if "isLiteral" in sparql:
            if grouped:  # per-graph distinct literals
                return [
                    {"g": r["g"], "literals": r.get("literals", "0")}
                    for r in self._named_rows
                ]
            return [{"literals": self._totals["literals"]}]  # store-wide distinct literals
        if "COUNT(DISTINCT ?s)" in sparql:
            if grouped:  # per-graph count + distinct subjects/objects
                return [
                    {
                        "g": r["g"],
                        "count": r.get("count", "0"),
                        "subjects": r.get("subjects", "0"),
                        "objects": r.get("objects", "0"),
                    }
                    for r in self._named_rows
                ]
            return [  # store-wide distinct subjects/objects
                {"subjects": self._totals["subjects"], "objects": self._totals["objects"]}
            ]
        return [{"count": self._default_count}]  # default-graph triple count


def _make_graphs_app(oxigraph) -> FastAPI:
    """Build a minimal FastAPI app with the meta router and a stub oxigraph client."""
    from api.meta import router

    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.state.oxigraph = oxigraph
    return app


def _set_active_graph(monkeypatch: pytest.MonkeyPatch, value) -> None:
    """Point settings.data_graph_uri at ``value`` for the duration of a test."""
    from core.config import settings

    monkeypatch.setattr(settings, "data_graph_uri", value)


def test_get_graphs_returns_expected_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Response is 200 with exactly the documented top-level keys."""
    _set_active_graph(monkeypatch, GRAPH_A)
    ox = _StubOxigraph([{"g": GRAPH_A, "count": "1234"}, {"g": GRAPH_B, "count": "87"}])
    res = TestClient(_make_graphs_app(ox)).get("/api/meta/graphs")
    assert res.status_code == 200
    assert set(res.json()) == {
        "activeGraph",
        "graphs",
        "totalTriples",
        "totalSubjects",
        "totalObjects",
        "totalLiterals",
        "warnings",
    }


def test_get_graphs_marks_active_sorts_and_casts(monkeypatch: pytest.MonkeyPatch) -> None:
    """graphs[] is sorted by URI, counts are ints, and the active graph is flagged once."""
    _set_active_graph(monkeypatch, GRAPH_A)
    ox = _StubOxigraph([{"g": GRAPH_B, "count": "87"}, {"g": GRAPH_A, "count": "1234"}])
    body = TestClient(_make_graphs_app(ox)).get("/api/meta/graphs").json()

    assert body["activeGraph"] == GRAPH_A
    assert [g["uri"] for g in body["graphs"]] == sorted([GRAPH_A, GRAPH_B])
    active = [g for g in body["graphs"] if g["active"]]
    assert len(active) == 1
    assert active[0]["uri"] == GRAPH_A
    assert active[0]["count"] == 1234
    assert not body["warnings"]  # active graph present + non-empty, default empty


def test_get_graphs_reports_per_graph_distinct_terms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each graph row carries its own distinct subject/object/literal counts as ints."""
    _set_active_graph(monkeypatch, GRAPH_A)
    ox = _StubOxigraph(
        [{"g": GRAPH_A, "count": "10", "subjects": "7", "objects": "12", "literals": "5"}]
    )
    body = TestClient(_make_graphs_app(ox)).get("/api/meta/graphs").json()
    row = body["graphs"][0]
    assert row["count"] == 10
    assert row["subjects"] == 7
    assert row["objects"] == 12
    assert row["literals"] == 5


def test_get_graphs_totals_are_store_wide_distinct(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Footer totals use store-wide distinct counts, not the sum of per-graph columns."""
    _set_active_graph(monkeypatch, GRAPH_A)
    ox = _StubOxigraph(
        [
            {"g": GRAPH_A, "count": "10", "subjects": "7", "objects": "12", "literals": "5"},
            {"g": GRAPH_B, "count": "4", "subjects": "3", "objects": "5", "literals": "2"},
        ],
        totals={"subjects": "8", "objects": "15", "literals": "6"},
    )
    body = TestClient(_make_graphs_app(ox)).get("/api/meta/graphs").json()
    # Deduplicated store-wide totals are below the per-graph column sums (10, 17, 7).
    assert body["totalSubjects"] == 8
    assert body["totalObjects"] == 15
    assert body["totalLiterals"] == 6


def test_total_triples_sums_named_and_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """totalTriples is the sum of every named-graph count plus the default graph."""
    _set_active_graph(monkeypatch, GRAPH_A)
    ox = _StubOxigraph(
        [{"g": GRAPH_A, "count": "1234"}, {"g": GRAPH_B, "count": "87"}],
        default_count="5",
    )
    body = TestClient(_make_graphs_app(ox)).get("/api/meta/graphs").json()
    assert body["totalTriples"] == 1234 + 87 + 5


def test_warning_when_active_graph_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """A configured active graph missing from the store surfaces a warning."""
    _set_active_graph(monkeypatch, "https://rosfeatr.eu/rdf/unused/")
    ox = _StubOxigraph([{"g": GRAPH_A, "count": "1234"}])
    body = TestClient(_make_graphs_app(ox)).get("/api/meta/graphs").json()
    assert any("empty or absent" in w for w in body["warnings"])


def test_warning_when_default_graph_populated(monkeypatch: pytest.MonkeyPatch) -> None:
    """Triples in the default graph (invisible to the scoped editor) warn."""
    _set_active_graph(monkeypatch, GRAPH_A)
    ox = _StubOxigraph([{"g": GRAPH_A, "count": "10"}], default_count="3")
    body = TestClient(_make_graphs_app(ox)).get("/api/meta/graphs").json()
    assert any("default graph" in w for w in body["warnings"])


def test_get_graphs_returns_503_when_store_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A store transport error becomes a 503 (matching api/data.py), not a 500."""
    _set_active_graph(monkeypatch, GRAPH_A)
    ox = _StubOxigraph([], raise_exc=RuntimeError("store down"))
    res = TestClient(_make_graphs_app(ox)).get("/api/meta/graphs")
    assert res.status_code == 503
