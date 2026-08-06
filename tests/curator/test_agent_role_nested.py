"""Nested AgentRole editing: the bridge node is validated and written intact.

AgentRole is a helper/bridge shape (no rdfs:label). It is created inline as part
of its parent (Work/Expression) and must carry an explicit ``core:AgentRole``
@type to be validated (class-targeting) and to reference exactly one Person and
one Role. These tests create a Work with a nested AgentRole and confirm the
bridge node keeps its stable IRI in the written Turtle — the property that lets
an update re-reference it instead of regenerating it — and that dropping the
explicit @type is rejected.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schema" / "schema.ttl"
BACKEND_DIR = ROOT / "curator-backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from api.data import create_or_update_entity  # noqa: E402
from core.shacl_validator import ShaclValidator  # noqa: E402
from models.data import EntityData  # noqa: E402

CORE = "https://w3id.org/polifonia/ontology/core/"
DATA = "https://rosfeatr.eu/rdf/data/"
WORK_SHAPE = "https://rosfeatr.eu/rdf/schema/MusicalWorkShape"

HAS_AGENT_ROLE = URIRef(CORE + "hasAgentRole")
HAS_AGENT = URIRef(CORE + "hasAgent")
HAS_ROLE = URIRef(CORE + "hasRole")
AGENT_ROLE = URIRef(CORE + "AgentRole")


class _CapturingOxigraph:
    """Oxigraph double: validates via the real SHACL validator and captures the
    Turtle that would be written."""

    def __init__(self) -> None:
        self.loaded_turtle = ""

    def from_clause(self) -> str:
        """Empty SPARQL FROM clause for tests."""
        return ""

    def construct(self, _sparql: str) -> Graph:
        """No pre-existing triples for the payload under test."""
        return Graph()

    def load_turtle(self, turtle: str) -> None:
        """Capture the Turtle that would be loaded into Oxigraph."""
        self.loaded_turtle = turtle


def _request(oxigraph: _CapturingOxigraph) -> SimpleNamespace:
    """Minimal request object expected by create_or_update_entity."""
    return SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                store=oxigraph,
                shape_dep_graph={},
                shacl_validator=ShaclValidator(str(SCHEMA_PATH)),
            )
        )
    )


def _work_with_agent_role() -> EntityData:
    """A Work with one inline AgentRole linking a Person to a Role, all named."""
    return EntityData(
        shapeId=WORK_SHAPE,
        data={
            "@context": {
                "mm": "https://w3id.org/polifonia/ontology/music-meta/",
                "lrmoo": "http://iflastandards.info/ns/lrm/lrmoo/",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                "core": CORE,
            },
            "@id": DATA + "nested_work",
            "@type": ["mm:MusicEntity", "lrmoo:F1_Work"],
            "rdfs:label": {"@value": "Nested Work", "@language": "en"},
            "core:hasAgentRole": {
                "@id": DATA + "nested_work_ar_0",
                "@type": "core:AgentRole",
                "core:hasAgent": {
                    "@id": DATA + "person_x",
                    "@type": "core:Person",
                    "rdfs:label": {"@value": "Composer X", "@language": "en"},
                },
                "core:hasRole": {
                    "@id": DATA + "role_composer",
                    "@type": "core:Role",
                    "rdfs:label": {"@value": "Composer", "@language": "en"},
                },
            },
        },
        originalTriples=None,
    )


def test_nested_agent_role_validates_and_is_written_intact() -> None:
    """A Work with an inline AgentRole conforms and the bridge triples persist."""
    oxigraph = _CapturingOxigraph()
    response = create_or_update_entity(_work_with_agent_role(), _request(oxigraph))
    assert response.success is True
    assert response.validationReport.conforms is True

    written = Graph().parse(data=oxigraph.loaded_turtle, format="turtle")
    work = URIRef(DATA + "nested_work")
    agent_role = URIRef(DATA + "nested_work_ar_0")

    # The bridge node keeps its stable IRI (a named node, not a blank/regenerated one).
    assert (work, HAS_AGENT_ROLE, agent_role) in written
    assert (agent_role, RDF.type, AGENT_ROLE) in written
    assert (agent_role, HAS_AGENT, URIRef(DATA + "person_x")) in written
    assert (agent_role, HAS_ROLE, URIRef(DATA + "role_composer")) in written


def test_agent_role_without_type_is_rejected() -> None:
    """Dropping the explicit core:AgentRole @type makes the write fail: the parent
    link's sh:class/sh:node require a conforming AgentRole, which a node with no
    type cannot be."""
    payload = _work_with_agent_role()
    del payload.data["core:hasAgentRole"]["@type"]
    response = create_or_update_entity(payload, _request(_CapturingOxigraph()))
    assert response.success is False
