"""Data CRUD routes: list, inspect, create/update RDF entities.

Validation merge planning lives in :mod:`core.validation_merge`.
This module keeps the route handlers and the small request-scoped helpers they need.
"""

import json
import logging
import re
from fastapi import APIRouter, HTTPException, Query, Request, status
from rdflib import Literal, URIRef, Graph

from models.data import (
    DataCreateResponse,
    DataListResponse,
    EntityData,
    ValidationResult,
)
from core.blank_node_handler import assign_entity_id, skolemize
from core.validation_merge import _build_validation_construct

router = APIRouter()
logger = logging.getLogger(__name__)

_IRI_UNSAFE = re.compile(r'[<>"{}|\\^`\s]')
_VOCAB_PREFIXES = (
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "http://www.w3.org/2000/01/rdf-schema#",
    "http://www.w3.org/2002/07/owl#",
    "http://www.w3.org/2001/XMLSchema#",
    "http://www.w3.org/ns/shacl#",
)
_RDF_TYPE = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
_CORE_HAS_AGENT_ROLE = URIRef("https://w3id.org/polifonia/ontology/core/hasAgentRole")
_CORE_AGENT_ROLE = URIRef("https://w3id.org/polifonia/ontology/core/AgentRole")
_CORE_HAS_AGENT = URIRef("https://w3id.org/polifonia/ontology/core/hasAgent")
_CORE_HAS_ROLE = URIRef("https://w3id.org/polifonia/ontology/core/hasRole")


# ---------------------------------------------------------------------------
# IRI validation
# ---------------------------------------------------------------------------


def _validate_iri(entity_id: str) -> None:
    """Reject non-http(s) or unsafe IRIs before interpolating them in SPARQL."""
    if not entity_id.startswith("http://") and not entity_id.startswith("https://"):
        raise HTTPException(status_code=400, detail=f"Invalid IRI: {entity_id}")
    if _IRI_UNSAFE.search(entity_id):
        raise HTTPException(
            status_code=400, detail=f"IRI contains unsafe characters: {entity_id}"
        )


def _is_non_vocab_iri(value: str) -> bool:
    return not any(value.startswith(prefix) for prefix in _VOCAB_PREFIXES)


def _log_agent_role_completeness(validation_graph: Graph) -> None:
    """Emit debug diagnostics for AgentRole nodes seen via core:hasAgentRole."""
    for role_node in sorted(
        {
            obj
            for obj in validation_graph.objects(predicate=_CORE_HAS_AGENT_ROLE)
            if isinstance(obj, URIRef)
        },
        key=str,
    ):
        has_type = (role_node, _RDF_TYPE, _CORE_AGENT_ROLE) in validation_graph
        has_agent = any(
            validation_graph.objects(subject=role_node, predicate=_CORE_HAS_AGENT)
        )
        has_role = any(
            validation_graph.objects(subject=role_node, predicate=_CORE_HAS_ROLE)
        )
        logger.debug(
            "Validation AgentRole node=%s has_type=%s hasAgent=%s hasRole=%s",
            role_node,
            has_type,
            has_agent,
            has_role,
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/data/list", response_model=DataListResponse)
def list_data(
    request: Request,
    shapeId: str = Query(..., description="Full URI of the SHACL NodeShape"),
    q: str = Query("", description="Filter by label or ID prefix"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Return a paginated list of entities that conform to a given SHACL shape.

    Entities are retrieved from the configured named graph and ordered by IRI.
    When ``q`` is provided, results are filtered by case-insensitive regex over
    both the primary ``rdfs:label`` and the entity IRI.

    Args:
        shapeId: Full URI of a NodeShape defined in ``schema/schema.ttl``.
        q: Optional free-text filter applied to label and IRI.
        limit: Maximum number of items to return (1–500, default 50).
        offset: Number of items to skip for pagination (default 0).

    Returns:
        A ``DataListResponse`` with ``total`` (unpaged count) and ``items``
        (the current page).  Each item carries ``id``, ``label``,
        ``labelLang``, and ``status``.

    Raises:
        404: When ``shapeId`` is not found in the schema.
    """
    extractor = request.app.state.schema_extractor
    shape = extractor.get_shape(shapeId)
    if shape is None:
        raise HTTPException(status_code=404, detail=f"Shape '{shapeId}' not found")

    target_class = shape.get("targetClassUri")
    if not target_class:
        return DataListResponse(shapeId=shapeId, total=0, items=[])

    escaped_q = q.replace("\\", "\\\\").replace('"', '\\"')
    filter_clause = (
        f'FILTER(regex(COALESCE(str(?label_raw), ""), "{escaped_q}", "i") || regex(str(?id), "{escaped_q}", "i"))'
        if q
        else ""
    )

    oxigraph = request.app.state.oxigraph

    # SPARQL note: FROM does not propagate into subqueries (SPARQL 1.1 §8.2).
    # The GROUP BY is kept in a subquery only for deduplication; the OPTIONAL
    # label lookup is moved to the outer WHERE so it runs inside the FROM scope.
    sparql = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?id (SAMPLE(?label_raw) AS ?label) (SAMPLE(?lang) AS ?labelLang)
        {oxigraph.from_clause()}
        WHERE {{
            ?id a <{target_class}> .
            OPTIONAL {{
                ?id rdfs:label ?label_raw .
                BIND(LANG(?label_raw) AS ?lang)
            }}
            {filter_clause}
        }}
        GROUP BY ?id
        ORDER BY ?id
        LIMIT {limit}
        OFFSET {offset}
    """

    try:
        rows = oxigraph.query(sparql)
    except Exception:
        rows = []

    items = [
        {
            "id": r["id"],
            "label": r.get("label"),
            "labelLang": r.get("labelLang") or None,
            "status": "unknown",
        }
        for r in rows
        if r.get("id")
    ]

    count_sparql = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?id) AS ?total)
        {oxigraph.from_clause()}
        WHERE {{
            ?id a <{target_class}> .
            OPTIONAL {{ ?id rdfs:label ?label_raw . }}
            {filter_clause}
        }}
    """

    try:
        count_rows = oxigraph.query(count_sparql)
        total = int(count_rows[0]["total"]) if count_rows else 0
    except Exception:
        total = len(items)

    return DataListResponse(shapeId=shapeId, total=total, items=items)


@router.get("/data/counts")
def count_data_by_shape(request: Request):
    """Return the number of stored entities for every SHACL shape.

    Iterates all shapes from the schema, runs a ``COUNT(DISTINCT ?id)`` query
    for each one's ``sh:targetClass``, and returns a single dict.  Shapes
    without a ``targetClass`` are included with count 0.  Query errors for
    any individual shape are silently treated as 0 so a single broken shape
    does not block the sidebar from rendering.

    Returns:
        ``{"counts": {<shapeUri>: <int>, ...}}``
    """
    extractor = request.app.state.schema_extractor
    oxigraph = request.app.state.oxigraph

    counts: dict[str, int] = {}
    for shape in extractor.get_all_shapes():
        shape_id = shape.get("id")
        target_class = shape.get("targetClassUri")

        if not shape_id:
            continue

        if not target_class:
            counts[shape_id] = 0
            continue

        sparql = f"""
            SELECT (COUNT(DISTINCT ?id) AS ?total)
            {oxigraph.from_clause()}
            WHERE {{
                ?id a <{target_class}> .
            }}
        """

        try:
            rows = oxigraph.query(sparql)
            counts[shape_id] = int(rows[0]["total"]) if rows else 0
        except Exception:
            counts[shape_id] = 0

    return {"counts": counts}


@router.get("/data/{entity_id:path}")
def get_entity(entity_id: str, request: Request):
    """Fetch all triples for a single entity by IRI.

    Issues a SPARQL CONSTRUCT scoped to the configured named graph and returns
    every ``(predicate, object)`` pair as a JSON array.  Literal objects carry
    ``datatype`` and ``language`` metadata so the frontend form can reconstruct
    the original RDF values faithfully.

    Args:
        entity_id: Full IRI of the entity (URL-path-encoded by FastAPI).

    Returns:
        ``{"id": <iri>, "triples": [{predicate, object, objectType,
        datatype, language}, ...]}`` sorted by predicate then object.

    Raises:
        404: When no triples are found for ``entity_id``.
        503: When Oxigraph is unreachable.
    """
    _validate_iri(entity_id)
    oxigraph = request.app.state.oxigraph

    sparql = f"""
        CONSTRUCT {{
            <{entity_id}> ?predicate ?object .
        }}
        {oxigraph.from_clause()}
        WHERE {{
            <{entity_id}> ?predicate ?object .
        }}
    """

    try:
        graph = oxigraph.construct(sparql)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Store unavailable") from exc

    if len(graph) == 0:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found")

    triples = []
    subject = URIRef(entity_id)

    for _, predicate, obj in graph.triples((subject, None, None)):
        triples.append(
            {
                "predicate": str(predicate),
                "object": str(obj),
                "objectType": "literal" if isinstance(obj, Literal) else "iri",
                "datatype": str(obj.datatype)
                if isinstance(obj, Literal) and obj.datatype
                else None,
                "language": obj.language if isinstance(obj, Literal) else None,
            }
        )

    triples.sort(key=lambda t: (t["predicate"], t["object"]))
    return {"id": entity_id, "triples": triples}


@router.post("/data", response_model=DataCreateResponse)
def create_or_update_entity(payload: EntityData, request: Request):
    """Create or update an entity (RDF resource) from JSON-LD payload.

        SHACL targeting nuance:
        - Constraints attached to class-targeted shapes (sh:targetClass) are
            evaluated only for nodes that declare that class.
        - If a node is missing its expected RDF type, those class-targeted
            constraints may not be evaluated for that node.
        - Callers should therefore emit explicit @type values for entities and
            bridge/helper nodes whenever schema constraints depend on class targeting.

        Validation scope:
        - The full merged validation graph is validated (incoming payload +
            referenced entities merged from store), so nested linked-node
            constraint violations are rejected within the same write request.
    """
    data = payload.data
    provided_id = data.get("@id")
    if isinstance(provided_id, str):
        _validate_iri(provided_id)

    data = assign_entity_id(data, payload.shapeId)
    entity_id = data.get("@id", "")
    data = skolemize(data, entity_id)

    oxigraph = request.app.state.oxigraph
    existing_entity_graph = None
    delete_executed = False

    if entity_id and payload.originalTriples:
        _validate_iri(entity_id)
        try:
            existing_entity_graph = oxigraph.construct(
                f"""
                CONSTRUCT {{ <{entity_id}> ?p ?o }}
                {oxigraph.from_clause()}
                WHERE {{ <{entity_id}> ?p ?o }}
                """
            )
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Store unavailable") from exc

    # Parse JSON-LD payload into an rdflib Graph.
    data_graph = Graph()
    try:
        data_graph.parse(data=json.dumps(data), format="json-ld")
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid JSON-LD: {exc}") from exc

    entity_uri = URIRef(entity_id) if entity_id.startswith("http") else None

    # Collect seed IRIs for shape-driven merge planning.
    # Include the entity IRI itself only on create flows so root-shape chains
    # can anchor from the entity node (e.g. Manifestation -> R4_embodies ->
    # Expression) even before that node exists in store.
    #
    # On updates, avoid seeding with entity IRI to prevent old store triples of
    # the entity from masking payload intent (e.g. preserving removed fields or
    # causing false maxCount violations via stale values).
    include_root_entity = bool(entity_uri is not None and not payload.originalTriples)
    seed_iris = {str(entity_uri)} if include_root_entity else set()
    seed_iris |= {
        str(obj)
        for obj in data_graph.objects()
        if isinstance(obj, URIRef) and _is_non_vocab_iri(str(obj))
    }
    logger.debug(
        "Validation merge seed IRIs (%d): %s", len(seed_iris), sorted(seed_iris)
    )

    # Build the validation graph by merging the payload with the referenced
    # entities fetched from Oxigraph.
    #
    # The fetch plan is derived from the shape dependency graph.  See
    # core.validation_merge for the query-planning logic.
    #
    # Fail closed: if the referenced graph cannot be resolved, do not proceed
    # with an incomplete validation graph.  A partial merge is worse than a
    # clean 503 because it may silently pass constraints that should fail.
    if seed_iris:
        dep_graph = request.app.state.shape_dep_graph
        construct_query = _build_validation_construct(
            dep_graph=dep_graph,
            root_shape_id=payload.shapeId,
            seed_iris=seed_iris,
            from_clause=oxigraph.from_clause(),
        )
        try:
            referenced_graph = (
                oxigraph.construct(construct_query) if construct_query else Graph()
            )
            validation_graph = referenced_graph + data_graph
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Related-entity merge failed: {exc}",
            ) from exc
        logger.debug(
            "Validation merge graph triple counts data=%d referenced=%d merged=%d",
            len(data_graph),
            len(referenced_graph),
            len(validation_graph),
        )
        _log_agent_role_completeness(validation_graph)
    else:
        validation_graph = data_graph
        logger.debug(
            "Validation merge graph triple counts data=%d referenced=0 merged=%d",
            len(data_graph),
            len(data_graph),
        )
        _log_agent_role_completeness(validation_graph)

    # Validate the merged graph against the SHACL schema.
    # Full-graph validation is intentional so nested linked-node violations
    # (e.g. missing required fields inside referenced structures) are surfaced
    # and rejected in the same write request.
    validator = request.app.state.shacl_validator
    report = validator.validate(validation_graph)

    if not report["conforms"]:
        assert not delete_executed, "Delete must not execute before validation success"
        logger.warning(
            "SHACL validation failed for entity %s (shape=%s, violations=%d)",
            entity_id,
            payload.shapeId,
            len(report.get("violations", [])),
        )
        return DataCreateResponse(
            success=False,
            entityId=entity_id,
            validationReport=ValidationResult(**report),
        )

    # Validation passed.  Delete the predicates that are being updated before
    # writing the new triples.
    if entity_id and payload.originalTriples:
        predicates_to_delete = {t.predicate for t in payload.originalTriples}
        wc = oxigraph.with_clause()
        for pred_uri in predicates_to_delete:
            _validate_iri(pred_uri)
            oxigraph.update(
                f"""
                {wc}
                DELETE {{ <{entity_id}> <{pred_uri}> ?o . }}
                WHERE  {{ <{entity_id}> <{pred_uri}> ?o . }}
                """
            )
            delete_executed = True

    # Serialize to Turtle and bulk-load into Oxigraph.
    # On write failure, attempt to restore the pre-existing entity graph if
    # one was captured above.
    turtle_data = data_graph.serialize(format="turtle")

    try:
        request.app.state.oxigraph.load_turtle(turtle_data)
    except Exception as exc:
        if existing_entity_graph is not None and len(existing_entity_graph) > 0:
            try:
                request.app.state.oxigraph.load_turtle(
                    existing_entity_graph.serialize(format="turtle")
                )
            except Exception as restore_exc:
                raise HTTPException(
                    status_code=503,
                    detail=f"Store write failed and rollback failed: {restore_exc}",
                ) from restore_exc
        raise HTTPException(
            status_code=503, detail=f"Store write failed: {exc}"
        ) from exc

    return DataCreateResponse(
        success=True,
        entityId=entity_id,
        validationReport=ValidationResult(**report),
    )


@router.delete("/data/{entity_id:path}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entity(entity_id: str, request: Request):
    """Delete all triples for a given entity IRI."""
    _validate_iri(entity_id)
    oxigraph = request.app.state.oxigraph

    # TODO: Delete also triples where this entity is the object and related
    #   blank/helper nodes (e.g. skolemized AgentRole nodes exclusively owned
    #   by this entity).  Orphaned helper nodes left behind here will cause
    #   SHACL validation failures on unrelated entities that trigger a merge
    #   including those IRIs.  Deletion of helper nodes must happen before the
    #   entity delete to avoid leaving orphans if a partial failure occurs.
    #   Guard with FILTER NOT EXISTS to avoid deleting shared helper nodes.
    delete_query = f"""
        {oxigraph.with_clause()}
        DELETE {{ <{entity_id}> ?p ?o . }}
        WHERE  {{ <{entity_id}> ?p ?o . }}
    """

    oxigraph.update(delete_query)
    return
