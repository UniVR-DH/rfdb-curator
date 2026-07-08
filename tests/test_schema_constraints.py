"""Schema and form metadata coverage for editor-facing RDF constraints."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "editor" / "backend"
SCHEMA_PATH = ROOT / "schema" / "schema.ttl"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core.schema_extractor import SchemaExtractor  # noqa: E402


def _assert_conforms(data_graph: Graph) -> None:
    """Assert that a graph conforms to the project SHACL schema."""
    schema_graph = Graph().parse(str(SCHEMA_PATH), format="turtle")
    conforms, _, report_text = validate(
        data_graph=data_graph,
        shacl_graph=schema_graph,
        inference="rdfs",
        advanced=True,
        abort_on_first=False,
    )
    assert conforms, report_text


def _schema_field(shape_id: str, path: str) -> dict:
    """Return the extracted field descriptor for a shape path."""
    extractor = SchemaExtractor(str(SCHEMA_PATH))
    shape = extractor.get_shape(shape_id)
    assert shape is not None
    field = next((prop for prop in shape["properties"] if prop["path"] == path), None)
    assert field is not None
    return field


@pytest.mark.parametrize(
    "shape_id",
    [
        "https://rfdb.it/data/PlaceShape",
        "https://rfdb.it/data/MusicalWorkShape",
        "https://rfdb.it/data/PersonShape",
        "https://rfdb.it/data/HoldingOrganizationShape",
    ],
)
def test_owl_same_as_allows_multiple_values(shape_id: str) -> None:
    """owl:sameAs is unbounded for external authority fields."""
    field = _schema_field(shape_id, "owl:sameAs")

    assert field["maxCount"] is None
    assert field["nodeKind"] == "sh:IRI"
    assert field["type"] == "uri"


def test_place_plain_label_with_multiple_same_as_conforms() -> None:
    """A place accepts an untranslated label and multiple external authorities."""
    data_graph = Graph()
    data_graph.parse(
        data="""
@prefix core: <https://w3id.org/polifonia/ontology/core/> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix rfdb: <https://rfdb.it/data/> .

rfdb:TestPlace
  a core:Place ;
  rdfs:label "Test Place" ;
  owl:sameAs <https://example.org/place/1>, <https://example.org/place/2> .
""",
        format="turtle",
    )

    _assert_conforms(data_graph)


def test_manifestation_plain_comment_conforms() -> None:
    """A manifestation accepts an untranslated rdfs:comment literal."""
    data_graph = Graph()
    data_graph.parse(
        data="""
@prefix core:  <https://w3id.org/polifonia/ontology/core/> .
@prefix lrmoo: <http://iflastandards.info/ns/lrm/lrmoo/> .
@prefix mm:    <https://w3id.org/polifonia/ontology/music-meta/> .
@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .
@prefix rfdb:  <https://rfdb.it/data/> .

rfdb:TestManifestation
  a lrmoo:F3_Manifestation ;
  rdfs:label "Test Manifestation"@en ;
  rdfs:comment "Generic comment" ;
  lrmoo:R4_embodies rfdb:TestExpression .

rfdb:TestExpression
  a lrmoo:F2_Expression ;
  rdfs:label "Test Expression"@en ;
  core:isPartOf rfdb:TestWork .

rfdb:TestWork
  a mm:MusicEntity, lrmoo:F1_Work ;
  rdfs:label "Test Work"@en .
""",
        format="turtle",
    )

    _assert_conforms(data_graph)


def test_label_field_is_language_capable_with_string_option() -> None:
    """Label fields remain language-capable while accepting plain strings."""
    field = _schema_field("https://rfdb.it/data/PlaceShape", "rdfs:label")

    assert field["type"] == "lang-string"
    assert field["datatypeOptions"] == ["rdf:langString", "xsd:string"]


def test_language_shape_exists_with_correct_target_class() -> None:
    """rfdb:LanguageShape exists and targets dcterms:LinguisticSystem."""
    from rdflib import URIRef
    from rdflib.namespace import SH

    schema = Graph().parse(str(SCHEMA_PATH), format="turtle")
    shape_uri = URIRef("https://rfdb.it/data/LanguageShape")
    target = schema.value(shape_uri, SH.targetClass)
    assert target == URIRef("http://purl.org/dc/terms/LinguisticSystem"), (
        f"Expected dcterms:LinguisticSystem, got {target}"
    )


def test_source_shape_language_field_is_entity_search() -> None:
    """dcterms:language in SourceShape resolves to entity-search with correct class."""
    field = _schema_field(
        "https://rfdb.it/data/SourceShape", "dcterms:language"
    )
    assert field["type"] == "entity-search", f"Expected entity-search, got {field['type']}"
    assert field["nodeClass"] == "dcterms:LinguisticSystem", (
        f"Expected dcterms:LinguisticSystem, got {field['nodeClass']}"
    )
    assert field["nestedShape"] == "https://rfdb.it/data/LanguageShape", (
        f"Expected rfdb:LanguageShape, got {field['nestedShape']}"
    )
