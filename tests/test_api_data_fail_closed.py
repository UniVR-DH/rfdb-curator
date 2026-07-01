"""Unit-level fail-closed coverage for backend write logic.

This module executes ``api.data.create_or_update_entity`` directly with a fake
request/app.state and a controlled Oxigraph stub. It does not test HTTP routing;
it tests backend branch semantics when related-entity merge fails.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"


def _load_backend_symbols() -> SimpleNamespace:
    """Load backend symbols directly from backend/ for unit-level tests."""
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))

    from fastapi import HTTPException

    data_module = importlib.import_module("api.data")
    from api.data import create_or_update_entity
    from models.data import EntityData

    return SimpleNamespace(
        HTTPException=HTTPException,
        data_module=data_module,
        create_or_update_entity=create_or_update_entity,
        EntityData=EntityData,
    )


class _NoopValidator:
    """Validator stub that always reports conforming graphs."""

    def validate(self, _graph, focus_nodes=None):
        return {"conforms": True, "violations": []}


class _RejectingValidator:
    """Validator stub that forces non-conformance to avoid write side effects."""

    def validate(self, _graph, focus_nodes=None):
        return {
            "conforms": False,
            "violations": [
                {
                    "focusNode": "https://rfdb.it/data/focus",
                    "path": "http://www.w3.org/2000/01/rdf-schema#label",
                    "message": "forced test violation",
                }
            ],
        }


class _FailingConstructOxigraph:
    """Oxigraph stub that fails on CONSTRUCT and records side-effect calls."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def from_clause(self) -> str:
        return ""

    def construct(self, _sparql: str):
        self.calls.append("construct")
        raise RuntimeError("simulated construct failure")

    def update(self, _sparql: str) -> None:
        self.calls.append("update")

    def load_turtle(self, _ttl: str) -> None:
        self.calls.append("load_turtle")


class _NoopOxigraph:
    """Oxigraph stub for seed-composition tests without write operations."""

    def from_clause(self) -> str:
        return ""

    def construct(self, _sparql: str):
        self.calls.append("construct")
        return None

    def with_clause(self) -> str:
        return ""

    def update(self, _sparql: str) -> None:
        self.calls.append("update")

    def load_turtle(self, _ttl: str) -> None:
        self.calls.append("load_turtle")

    def __init__(self) -> None:
        self.calls: list[str] = []


def _fake_request(oxigraph: _FailingConstructOxigraph) -> SimpleNamespace:
    """Build the minimal request.app.state object expected by the route logic."""

    state = SimpleNamespace(
        oxigraph=oxigraph,
        shape_dep_graph={},
        shacl_validator=_NoopValidator(),
    )
    return SimpleNamespace(app=SimpleNamespace(state=state))


def _fake_request_with_validator(
    *, oxigraph: object, validator: object
) -> SimpleNamespace:
    """Build request.app.state with configurable validator and Oxigraph stubs."""

    state = SimpleNamespace(
        oxigraph=oxigraph,
        shape_dep_graph={},
        shacl_validator=validator,
    )
    return SimpleNamespace(app=SimpleNamespace(state=state))


def test_create_or_update_fails_closed_on_related_merge_error() -> None:
    """Related merge failures return 503 and do not execute write operations."""
    symbols = _load_backend_symbols()
    oxigraph = _FailingConstructOxigraph()
    request = _fake_request(oxigraph)

    payload = symbols.EntityData(
        shapeId="https://rfdb.it/data/ManifestationShape",
        data={
            "@context": {
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                "lrmoo": "http://iflastandards.info/ns/lrm/lrmoo/",
            },
            "@id": "https://rfdb.it/data/fail_closed_manifestation",
            "@type": "lrmoo:F3_Manifestation",
            "rdfs:label": {"@value": "Fail-Closed Test", "@language": "en"},
            "lrmoo:R4_embodies": {"@id": "https://rfdb.it/data/fail_closed_expression"},
        },
        originalTriples=None,
    )

    # This directly executes backend production logic in api.data, bypassing
    # HTTP transport so we can deterministically force construct() failure.
    with pytest.raises(symbols.HTTPException) as exc:
        symbols.create_or_update_entity(payload, request)

    assert exc.value.status_code == 503
    assert "Related-entity merge failed" in str(exc.value.detail)
    assert oxigraph.calls == ["construct"]


@pytest.mark.parametrize(
    ("payload_data", "expected_seed_iris"),
    [
        (
            {
                "@id": "https://rfdb.it/data/literals_only",
                "@type": "https://rfdb.it/data/LocalType",
                "http://www.w3.org/2000/01/rdf-schema#label": {
                    "@value": "Only literals",
                    "@language": "en",
                },
            },
            {
                "https://rfdb.it/data/literals_only",
                "https://rfdb.it/data/LocalType",
            },
        ),
        (
            {
                "@id": "https://rfdb.it/data/vocab_only",
                "@type": "https://rfdb.it/data/LocalType",
                "https://rfdb.it/data/pointsTo": {
                    "@id": "http://www.w3.org/2000/01/rdf-schema#label"
                },
            },
            {
                "https://rfdb.it/data/vocab_only",
                "https://rfdb.it/data/LocalType",
            },
        ),
        (
            {
                "@id": "https://rfdb.it/data/mixed_iris",
                "@type": "https://rfdb.it/data/LocalType",
                "https://rfdb.it/data/pointsTo": {
                    "@id": "https://rfdb.it/data/RelatedNode"
                },
                "https://rfdb.it/data/vocabRef": {
                    "@id": "http://www.w3.org/2001/XMLSchema#string"
                },
            },
            {
                "https://rfdb.it/data/mixed_iris",
                "https://rfdb.it/data/LocalType",
                "https://rfdb.it/data/RelatedNode",
            },
        ),
        (
            {
                "@id": "https://rfdb.it/data/repeated_non_vocab",
                "@type": "https://rfdb.it/data/LocalType",
                "https://rfdb.it/data/pointsTo": [
                    {"@id": "https://rfdb.it/data/DedupNode"},
                    {"@id": "https://rfdb.it/data/DedupNode"},
                ],
            },
            {
                "https://rfdb.it/data/repeated_non_vocab",
                "https://rfdb.it/data/LocalType",
                "https://rfdb.it/data/DedupNode",
            },
        ),
    ],
)
def test_create_or_update_seed_iri_composition(
    monkeypatch: pytest.MonkeyPatch,
    payload_data: dict,
    expected_seed_iris: set[str],
) -> None:
    """Seed IRIs include non-vocab @type/object IRIs and deduplicate repeats."""
    symbols = _load_backend_symbols()
    captured: dict[str, object] = {}

    def _capture_build_validation_construct(
        dep_graph, root_shape_id: str, seed_iris: set[str], from_clause: str
    ) -> str:
        captured["dep_graph"] = dep_graph
        captured["root_shape_id"] = root_shape_id
        captured["seed_iris"] = set(seed_iris)
        captured["from_clause"] = from_clause
        return ""

    monkeypatch.setattr(
        symbols.data_module,
        "_build_validation_construct",
        _capture_build_validation_construct,
    )

    payload = symbols.EntityData(
        shapeId="https://rfdb.it/data/TestShape",
        data=payload_data,
        originalTriples=None,
    )

    oxigraph = _NoopOxigraph()
    request = _fake_request_with_validator(
        oxigraph=oxigraph,
        validator=_RejectingValidator(),
    )

    response = symbols.create_or_update_entity(payload, request)

    assert response.success is False
    assert set(captured["seed_iris"]) == expected_seed_iris
    assert captured["root_shape_id"] == "https://rfdb.it/data/TestShape"
