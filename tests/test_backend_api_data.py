"""HTTP integration coverage for backend data routes.

This module is the canonical live HTTP integration suite for the backend data
routes. The tests exercise the running FastAPI service over HTTP, including
request parsing, route wiring, backend write/read logic, and Oxigraph
persistence.
"""

from __future__ import annotations

import os
import json
import uuid
from typing import Iterator
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

import pytest


API_BASE_URL = os.getenv("RFDB_API_BASE_URL", "http://localhost:8000")
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
LRMOO_F1_WORK = "http://iflastandards.info/ns/lrm/lrmoo/F1_Work"
LRMOO_F2_EXPRESSION = "http://iflastandards.info/ns/lrm/lrmoo/F2_Expression"
LRMOO_F3_MANIFESTATION = "http://iflastandards.info/ns/lrm/lrmoo/F3_Manifestation"
LRMOO_R4_EMBODIES = "http://iflastandards.info/ns/lrm/lrmoo/R4_embodies"
MM_MUSIC_ENTITY = "https://w3id.org/polifonia/ontology/music-meta/MusicEntity"
CORE_AGENT_ROLE = "https://w3id.org/polifonia/ontology/core/AgentRole"
CORE_HAS_AGENT = "https://w3id.org/polifonia/ontology/core/hasAgent"
CORE_HAS_AGENT_ROLE = "https://w3id.org/polifonia/ontology/core/hasAgentRole"
CORE_HAS_ROLE = "https://w3id.org/polifonia/ontology/core/hasRole"
CORE_IS_PART_OF = "https://w3id.org/polifonia/ontology/core/isPartOf"
CORE_PERSON = "https://w3id.org/polifonia/ontology/core/Person"
CORE_ROLE = "https://w3id.org/polifonia/ontology/core/Role"


def _make_suffix() -> str:
    return uuid.uuid4().hex[:8]


def _request_json(
    method: str, path: str, payload: dict | None = None
) -> tuple[int, dict]:
    url = f"{API_BASE_URL}{path}"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = UrlRequest(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if payload is not None else {},
    )

    try:
        with urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, json.loads(body) if body else {}
    except URLError as exc:  # pragma: no cover - environment guard
        raise RuntimeError(f"Unable to reach {url}: {exc}") from exc


def _request_text(method: str, path: str) -> tuple[int, str]:
    url = f"{API_BASE_URL}{path}"
    request = UrlRequest(url, method=method)

    try:
        with urlopen(request, timeout=20) as response:
            return response.status, response.read().decode("utf-8")
    except HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")
    except URLError as exc:  # pragma: no cover - environment guard
        raise RuntimeError(f"Unable to reach {url}: {exc}") from exc


@pytest.fixture(scope="session")
def api_client() -> Iterator[None]:
    """Skip the module when backend or Oxigraph is unavailable in compose stack."""
    try:
        status, health = _request_json("GET", "/health")
    except RuntimeError as exc:  # pragma: no cover - environment guard
        pytest.skip(f"Backend compose stack is not available at {API_BASE_URL}: {exc}")

    if status != 200 or health.get("oxigraph") != "up":
        pytest.skip(f"Backend health check reports unhealthy service: {health}")

    yield None


def _make_agent_role(
    person_id: str, person_label: str, role_id: str, role_label: str
) -> dict:
    return {
        "@id": f"https://rfdb.it/data/{_make_suffix()}_agentrole",
        "@type": CORE_AGENT_ROLE,
        CORE_HAS_AGENT: {
            "@id": person_id,
            "@type": CORE_PERSON,
            RDFS_LABEL: {"@value": person_label, "@language": "en"},
        },
        CORE_HAS_ROLE: {
            "@id": role_id,
            "@type": CORE_ROLE,
            RDFS_LABEL: {"@value": role_label, "@language": "en"},
        },
    }


def _make_manifestation_payload(
    *, suffix: str, include_work_label: bool = True
) -> dict:
    work = {
        "@id": f"https://rfdb.it/data/{suffix}_work",
        "@type": [MM_MUSIC_ENTITY, LRMOO_F1_WORK],
        CORE_HAS_AGENT_ROLE: [
            _make_agent_role(
                person_id=f"https://rfdb.it/data/{suffix}_person",
                person_label="Test Person",
                role_id=f"https://rfdb.it/data/{suffix}_role",
                role_label="Test Role",
            )
        ],
    }
    if include_work_label:
        work[RDFS_LABEL] = {"@value": "Test Work", "@language": "en"}

    return {
        "@id": f"https://rfdb.it/data/{suffix}_manifestation",
        "@type": LRMOO_F3_MANIFESTATION,
        RDFS_LABEL: {"@value": "Test Manifestation", "@language": "en"},
        LRMOO_R4_EMBODIES: {
            "@id": f"https://rfdb.it/data/{suffix}_expression",
            "@type": LRMOO_F2_EXPRESSION,
            RDFS_LABEL: {"@value": "Test Expression", "@language": "en"},
            CORE_IS_PART_OF: work,
        },
    }


def _make_work_payload(suffix: str) -> dict:
    return {
        "@id": f"https://rfdb.it/data/{suffix}_work",
        "@type": [MM_MUSIC_ENTITY, LRMOO_F1_WORK],
        RDFS_LABEL: {"@value": "Chain Work", "@language": "en"},
        CORE_HAS_AGENT_ROLE: [
            _make_agent_role(
                person_id=f"https://rfdb.it/data/{suffix}_person",
                person_label="Chain Person",
                role_id=f"https://rfdb.it/data/{suffix}_role",
                role_label="Chain Role",
            )
        ],
    }


def _make_expression_payload(suffix: str) -> dict:
    return {
        "@id": f"https://rfdb.it/data/{suffix}_expression",
        "@type": LRMOO_F2_EXPRESSION,
        RDFS_LABEL: {"@value": "Chain Expression", "@language": "en"},
        CORE_IS_PART_OF: {
            "@id": f"https://rfdb.it/data/{suffix}_work",
            "@type": [MM_MUSIC_ENTITY, LRMOO_F1_WORK],
            RDFS_LABEL: {"@value": "Chain Work", "@language": "en"},
            CORE_HAS_AGENT_ROLE: [
                _make_agent_role(
                    person_id=f"https://rfdb.it/data/{suffix}_person",
                    person_label="Chain Person",
                    role_id=f"https://rfdb.it/data/{suffix}_role",
                    role_label="Chain Role",
                )
            ],
        },
    }


def _make_manifestation_chain_payload(suffix: str) -> dict:
    return {
        "@id": f"https://rfdb.it/data/{suffix}_manifestation",
        "@type": LRMOO_F3_MANIFESTATION,
        RDFS_LABEL: {"@value": "Chain Manifestation", "@language": "en"},
        LRMOO_R4_EMBODIES: {
            "@id": f"https://rfdb.it/data/{suffix}_expression",
            "@type": LRMOO_F2_EXPRESSION,
            RDFS_LABEL: {"@value": "Chain Expression", "@language": "en"},
            CORE_IS_PART_OF: {
                "@id": f"https://rfdb.it/data/{suffix}_work",
                "@type": [MM_MUSIC_ENTITY, LRMOO_F1_WORK],
                RDFS_LABEL: {"@value": "Chain Work", "@language": "en"},
                CORE_HAS_AGENT_ROLE: [
                    _make_agent_role(
                        person_id=f"https://rfdb.it/data/{suffix}_person",
                        person_label="Chain Person",
                        role_id=f"https://rfdb.it/data/{suffix}_role",
                        role_label="Chain Role",
                    )
                ],
            },
        },
    }


def _make_source_payload(suffix: str, manifestation_id: str) -> dict:
    return {
        "@id": f"https://rfdb.it/data/{suffix}_source",
        "@type": [
            "https://w3id.org/polifonia/ontology/source/Source",
            "http://iflastandards.info/ns/lrm/lrmoo/F5_Item",
        ],
        RDFS_LABEL: {"@value": "Chain Source", "@language": "en"},
        "http://www.w3.org/2000/01/rdf-schema#seeAlso": {
            "@id": "https://example.org/catalog/chain"
        },
        "http://prismstandard.org/namespaces/basic/2.0/publicationDate": {
            "@value": "1736",
            "@type": "http://www.w3.org/2001/XMLSchema#gYear",
        },
        "https://w3id.org/polifonia/ontology/core/hasType": {
            "@id": f"https://rfdb.it/data/{suffix}_type",
            "@type": "https://w3id.org/polifonia/ontology/core/Type",
            RDFS_LABEL: {"@value": "Libretto a Stampa", "@language": "en"},
        },
        "http://purl.org/dc/terms/identifier": "Shelfmark-Chain",
        "http://www.cidoc-crm.org/cidoc-crm/P51_has_former_or_current_owner": {
            "@id": f"https://rfdb.it/data/{suffix}_owner",
            "@type": "https://w3id.org/polifonia/ontology/core/Organization",
            RDFS_LABEL: {"@value": "Chain Library", "@language": "en"},
            "https://w3id.org/polifonia/ontology/core/hasPlace": {
                "@id": f"https://rfdb.it/data/{suffix}_place",
                "@type": "https://w3id.org/polifonia/ontology/core/Place",
                RDFS_LABEL: {"@value": "Chain City", "@language": "en"},
            },
        },
        "http://iflastandards.info/ns/lrm/lrmoo/R7_exemplifies": {
            "@id": manifestation_id,
            "@type": LRMOO_F3_MANIFESTATION,
            RDFS_LABEL: {"@value": "Chain Manifestation", "@language": "en"},
            LRMOO_R4_EMBODIES: {
                "@id": f"https://rfdb.it/data/{suffix}_expression",
                "@type": LRMOO_F2_EXPRESSION,
                RDFS_LABEL: {"@value": "Chain Expression", "@language": "en"},
                CORE_IS_PART_OF: {
                    "@id": f"https://rfdb.it/data/{suffix}_work",
                    "@type": [MM_MUSIC_ENTITY, LRMOO_F1_WORK],
                    RDFS_LABEL: {"@value": "Chain Work", "@language": "en"},
                },
            },
        },
    }


def _make_manifestation_reference_only_payload(suffix: str) -> dict:
    return {
        "@id": f"https://rfdb.it/data/{suffix}_manifestation_ref_only",
        "@type": LRMOO_F3_MANIFESTATION,
        RDFS_LABEL: {"@value": "Chain Manifestation Ref Only", "@language": "en"},
        LRMOO_R4_EMBODIES: {
            "@id": f"https://rfdb.it/data/{suffix}_expression",
        },
    }


def _make_invalid_expression_payload(suffix: str) -> dict:
    payload = _make_manifestation_payload(suffix=suffix)
    work = payload[LRMOO_R4_EMBODIES][CORE_IS_PART_OF]
    work.pop(RDFS_LABEL, None)
    return payload


def _make_invalid_agent_role_payload(suffix: str) -> dict:
    payload = _make_manifestation_payload(suffix=suffix)
    agent_role = payload[LRMOO_R4_EMBODIES][CORE_IS_PART_OF][CORE_HAS_AGENT_ROLE][0]
    agent_role.pop(CORE_HAS_AGENT, None)
    agent_role.pop(CORE_HAS_ROLE, None)
    return payload


def _assert_entity_has_label_and_type(
    entity_id: str, expected_type: str, expected_label: str
):
    status, body = _request_json("GET", f"/api/data/{entity_id}")
    assert status == 200
    triples = body["triples"]
    assert any(
        t["predicate"] == RDFS_LABEL and t["object"] == expected_label for t in triples
    )
    assert any(
        t["predicate"] == RDF_TYPE and t["object"] == expected_type for t in triples
    )
    return triples


def test_positive_manifestation_insert_persists(api_client):
    """POST /api/data persists a valid manifestation with required links."""
    suffix = _make_suffix()
    payload = {
        "shapeId": "https://rfdb.it/data/ManifestationShape",
        "data": _make_manifestation_payload(suffix=suffix),
    }

    status, body = _request_json("POST", "/api/data", payload)
    assert status == 200

    assert body["success"] is True
    assert body["entityId"] == f"https://rfdb.it/data/{suffix}_manifestation"
    assert body["validationReport"]["conforms"] is True

    triples = _assert_entity_has_label_and_type(
        body["entityId"], LRMOO_F3_MANIFESTATION, "Test Manifestation"
    )
    assert any(t["predicate"] == LRMOO_R4_EMBODIES for t in triples)


def test_positive_work_insert_persists(api_client):
    """POST /api/data persists a standalone work with an agent-role relation."""
    suffix = _make_suffix()
    payload = {
        "shapeId": "https://rfdb.it/data/MusicalWorkShape",
        "data": {
            "@id": f"https://rfdb.it/data/{suffix}_work",
            "@type": [MM_MUSIC_ENTITY, LRMOO_F1_WORK],
            RDFS_LABEL: {"@value": "Standalone Work", "@language": "en"},
            CORE_HAS_AGENT_ROLE: [
                _make_agent_role(
                    person_id=f"https://rfdb.it/data/{suffix}_person",
                    person_label="Composer Person",
                    role_id=f"https://rfdb.it/data/{suffix}_role",
                    role_label="Composer Role",
                )
            ],
        },
    }

    status, body = _request_json("POST", "/api/data", payload)
    assert status == 200
    assert body["success"] is True

    triples = _assert_entity_has_label_and_type(
        body["entityId"], LRMOO_F1_WORK, "Standalone Work"
    )
    assert any(t["predicate"] == CORE_HAS_AGENT_ROLE for t in triples)


def test_positive_source_insert_persists(api_client):
    """POST /api/data persists a valid source including publication metadata."""
    suffix = _make_suffix()
    payload = {
        "shapeId": "https://rfdb.it/data/SourceShape",
        "data": {
            "@id": f"https://rfdb.it/data/{suffix}_source",
            "@type": [
                "https://w3id.org/polifonia/ontology/source/Source",
                "http://iflastandards.info/ns/lrm/lrmoo/F5_Item",
            ],
            RDFS_LABEL: {"@value": "Source Example", "@language": "en"},
            "http://www.w3.org/2000/01/rdf-schema#seeAlso": {
                "@id": "https://example.org/catalog/123"
            },
            "http://prismstandard.org/namespaces/basic/2.0/publicationDate": {
                "@value": "1736",
                "@type": "http://www.w3.org/2001/XMLSchema#gYear",
            },
            "https://w3id.org/polifonia/ontology/core/hasType": {
                "@id": f"https://rfdb.it/data/{suffix}_type",
                "@type": "https://w3id.org/polifonia/ontology/core/Type",
                RDFS_LABEL: {"@value": "Libretto a Stampa", "@language": "en"},
            },
            "http://purl.org/dc/terms/identifier": "Shelfmark-123",
            "http://www.cidoc-crm.org/cidoc-crm/P51_has_former_or_current_owner": {
                "@id": f"https://rfdb.it/data/{suffix}_owner",
                "@type": "https://w3id.org/polifonia/ontology/core/Organization",
                RDFS_LABEL: {"@value": "Test Library", "@language": "en"},
                "https://w3id.org/polifonia/ontology/core/hasPlace": {
                    "@id": f"https://rfdb.it/data/{suffix}_place",
                    "@type": "https://w3id.org/polifonia/ontology/core/Place",
                    RDFS_LABEL: {"@value": "Test City", "@language": "en"},
                },
            },
            "http://iflastandards.info/ns/lrm/lrmoo/R7_exemplifies": {
                "@id": f"https://rfdb.it/data/{suffix}_manifestation",
                "@type": LRMOO_F3_MANIFESTATION,
                RDFS_LABEL: {"@value": "Source Manifestation", "@language": "en"},
                LRMOO_R4_EMBODIES: {
                    "@id": f"https://rfdb.it/data/{suffix}_expression",
                    "@type": LRMOO_F2_EXPRESSION,
                    RDFS_LABEL: {"@value": "Source Expression", "@language": "en"},
                    CORE_IS_PART_OF: {
                        "@id": f"https://rfdb.it/data/{suffix}_work",
                        "@type": [MM_MUSIC_ENTITY, LRMOO_F1_WORK],
                        RDFS_LABEL: {"@value": "Source Work", "@language": "en"},
                    },
                },
            },
        },
    }

    status, body = _request_json("POST", "/api/data", payload)
    assert status == 200
    assert body["success"] is True

    triples = _assert_entity_has_label_and_type(
        body["entityId"],
        "https://w3id.org/polifonia/ontology/source/Source",
        "Source Example",
    )
    assert any(
        t["predicate"]
        == "http://prismstandard.org/namespaces/basic/2.0/publicationDate"
        for t in triples
    )


def test_full_stack_valid_insert_sequence(api_client):
    """Sequential Work->Expression->Manifestation->Source inserts stay valid end-to-end."""
    suffix = _make_suffix()

    work_payload = {
        "shapeId": "https://rfdb.it/data/MusicalWorkShape",
        "data": _make_work_payload(suffix),
    }
    work_status, work_body = _request_json("POST", "/api/data", work_payload)
    assert work_status == 200
    assert work_body["success"] is True
    _assert_entity_has_label_and_type(
        work_body["entityId"], LRMOO_F1_WORK, "Chain Work"
    )

    expression_payload = {
        "shapeId": "https://rfdb.it/data/ExpressionShape",
        "data": _make_expression_payload(suffix),
    }
    expression_status, expression_body = _request_json(
        "POST", "/api/data", expression_payload
    )
    assert expression_status == 200
    assert expression_body["success"] is True
    _assert_entity_has_label_and_type(
        expression_body["entityId"], LRMOO_F2_EXPRESSION, "Chain Expression"
    )

    manifestation_payload = {
        "shapeId": "https://rfdb.it/data/ManifestationShape",
        "data": _make_manifestation_chain_payload(suffix),
    }
    manifestation_status, manifestation_body = _request_json(
        "POST", "/api/data", manifestation_payload
    )
    assert manifestation_status == 200
    assert manifestation_body["success"] is True
    _assert_entity_has_label_and_type(
        manifestation_body["entityId"], LRMOO_F3_MANIFESTATION, "Chain Manifestation"
    )

    source_payload = {
        "shapeId": "https://rfdb.it/data/SourceShape",
        "data": _make_source_payload(suffix, manifestation_body["entityId"]),
    }
    source_status, source_body = _request_json("POST", "/api/data", source_payload)
    assert source_status == 200
    assert source_body["success"] is True

    triples = _assert_entity_has_label_and_type(
        source_body["entityId"],
        "https://w3id.org/polifonia/ontology/source/Source",
        "Chain Source",
    )
    assert any(
        t["predicate"] == "http://iflastandards.info/ns/lrm/lrmoo/R7_exemplifies"
        for t in triples
    )


def test_manifestation_reference_only_insert_uses_merged_context(api_client):
    """Reference-only manifestation insert succeeds via backend merge context fetch."""
    suffix = _make_suffix()

    work_payload = {
        "shapeId": "https://rfdb.it/data/MusicalWorkShape",
        "data": _make_work_payload(suffix),
    }
    work_status, work_body = _request_json("POST", "/api/data", work_payload)
    assert work_status == 200
    assert work_body["success"] is True

    expression_payload = {
        "shapeId": "https://rfdb.it/data/ExpressionShape",
        "data": _make_expression_payload(suffix),
    }
    expression_status, expression_body = _request_json(
        "POST", "/api/data", expression_payload
    )
    assert expression_status == 200
    assert expression_body["success"] is True

    manifestation_payload = {
        "shapeId": "https://rfdb.it/data/ManifestationShape",
        "data": _make_manifestation_reference_only_payload(suffix),
    }
    manifestation_status, manifestation_body = _request_json(
        "POST", "/api/data", manifestation_payload
    )
    assert manifestation_status == 200
    assert manifestation_body["success"] is True

    triples = _assert_entity_has_label_and_type(
        manifestation_body["entityId"],
        LRMOO_F3_MANIFESTATION,
        "Chain Manifestation Ref Only",
    )
    assert any(t["predicate"] == LRMOO_R4_EMBODIES for t in triples)


@pytest.mark.parametrize(
    "payload_factory",
    [
        _make_invalid_expression_payload,
        _make_invalid_agent_role_payload,
    ],
)
def test_negative_manifestation_insert_is_rejected(api_client, payload_factory):
    """Invalid manifestation payloads are rejected and not persisted in store."""
    suffix = _make_suffix()
    payload = {
        "shapeId": "https://rfdb.it/data/ManifestationShape",
        "data": payload_factory(suffix),
    }

    status, body = _request_json("POST", "/api/data", payload)
    assert status == 200
    assert body["success"] is False
    assert body["validationReport"]["conforms"] is False
    assert body["validationReport"]["violations"]

    stored_status, _ = _request_text("GET", f"/api/data/{payload['data']['@id']}")
    assert stored_status == 404


def test_negative_work_insert_without_label_is_rejected(api_client):
    """Work missing required label fails SHACL validation and is not stored."""
    suffix = _make_suffix()
    payload = {
        "shapeId": "https://rfdb.it/data/MusicalWorkShape",
        "data": {
            "@id": f"https://rfdb.it/data/{suffix}_work",
            "@type": [MM_MUSIC_ENTITY, LRMOO_F1_WORK],
            CORE_HAS_AGENT_ROLE: [
                _make_agent_role(
                    person_id=f"https://rfdb.it/data/{suffix}_person",
                    person_label="Composer Person",
                    role_id=f"https://rfdb.it/data/{suffix}_role",
                    role_label="Composer Role",
                )
            ],
        },
    }

    status, body = _request_json("POST", "/api/data", payload)
    assert status == 200
    assert body["success"] is False
    assert body["validationReport"]["conforms"] is False

    stored_status, _ = _request_text("GET", f"/api/data/{payload['data']['@id']}")
    assert stored_status == 404


def test_failed_update_keeps_existing_entity(api_client):
    """Failed update leaves previously persisted entity triples unchanged."""
    suffix = _make_suffix()
    entity_id = f"https://rfdb.it/data/{suffix}_manifestation"
    valid_payload = {
        "shapeId": "https://rfdb.it/data/ManifestationShape",
        "data": _make_manifestation_payload(suffix=suffix),
    }

    create_status, create_body = _request_json("POST", "/api/data", valid_payload)
    assert create_status == 200
    assert create_body["success"] is True

    invalid_update = {
        "shapeId": "https://rfdb.it/data/ManifestationShape",
        "data": _make_manifestation_payload(suffix=suffix, include_work_label=False),
        "originalTriples": [
            {
                "predicate": LRMOO_R4_EMBODIES,
                "object": f"https://rfdb.it/data/{suffix}_expression",
                "objectType": "iri",
            }
        ],
    }
    invalid_update["data"].pop(RDFS_LABEL, None)

    update_status, body = _request_json("POST", "/api/data", invalid_update)
    assert update_status == 200
    assert body["success"] is False
    assert body["validationReport"]["conforms"] is False

    stored_status, stored_body = _request_json("GET", f"/api/data/{entity_id}")
    assert stored_status == 200
    triples = stored_body["triples"]
    assert any(
        t["predicate"] == RDFS_LABEL and t["object"] == "Test Manifestation"
        for t in triples
    )
    assert any(t["predicate"] == LRMOO_R4_EMBODIES for t in triples)


def test_valid_update_replaces_label_without_dropping_type(api_client):
    """Valid update replaces label while preserving rdf:type and other structure."""
    suffix = _make_suffix()
    entity_id = f"https://rfdb.it/data/{suffix}_manifestation"
    create_payload = {
        "shapeId": "https://rfdb.it/data/ManifestationShape",
        "data": _make_manifestation_payload(suffix=suffix),
    }

    create_status, create_body = _request_json("POST", "/api/data", create_payload)
    assert create_status == 200
    assert create_body["success"] is True

    updated_data = json.loads(json.dumps(create_payload["data"]))
    updated_data[RDFS_LABEL] = {
        "@value": "Test Manifestation Updated",
        "@language": "en",
    }
    update_payload = {
        "shapeId": "https://rfdb.it/data/ManifestationShape",
        "data": updated_data,
        "originalTriples": [
            {
                "predicate": RDFS_LABEL,
                "object": "Test Manifestation",
                "objectType": "literal",
                "language": "en",
            }
        ],
    }

    update_status, update_body = _request_json("POST", "/api/data", update_payload)
    assert update_status == 200
    assert update_body["success"] is True

    triples = _assert_entity_has_label_and_type(
        entity_id, LRMOO_F3_MANIFESTATION, "Test Manifestation Updated"
    )
    assert not any(
        t["predicate"] == RDFS_LABEL and t["object"] == "Test Manifestation"
        for t in triples
    )
