"""Entity autocomplete search route used by relation (EntitySearch) fields.

When a user types into a relation field (e.g., `core:hasPlace`) the frontend
calls `GET /api/entities/search?shape=PlaceShape&query=<text>` and renders
the results as dropdown options.  The search fires on an empty query too, so
the dropdown is pre-populated when the field receives focus.

SPARQL strategy: a nested SELECT / GROUP BY deduplicates entities that carry
multiple `rdfs:label` values, then a BIND+FILTER applies the text match on
the sampled label so the outer query stays readable.
"""

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter()


@router.get("/entities/search")
def search_entities(
    request: Request,
    shape: str = Query(..., description="Shape label or full URI (e.g. PlaceShape)"),
    query: str = Query("", description="Partial label or IRI to match"),
    limit: int = Query(10, ge=1, le=100),
):
    """Search for entities that conform to a given SHACL shape.

    The `shape` parameter accepts either the full shape URI or just the local
    name suffix (e.g., `"PlaceShape"`) for convenience.  The target class is
    resolved from the shape metadata so the SPARQL query is always correct.

    Text matching is case-insensitive regex over both the primary label and
    the entity URI, so users can paste a partial IRI directly into the field.
    An empty `query` string returns all entities up to `limit` (used for the
    initial dropdown population on field focus).
    """
    extractor = request.app.state.schema_extractor

    # Resolve shape by label suffix if a full URI is not provided
    all_shapes = extractor.get_all_shapes()
    matched = next(
        (s for s in all_shapes if s["id"] == shape or s["id"].endswith(shape)),
        None,
    )
    if matched is None:
        raise HTTPException(status_code=404, detail=f"Shape '{shape}' not found")

    target_class = matched.get("targetClassUri")
    if not target_class:
        return []

    safe_query = query.replace('"', "").replace("\\", "")
    filter_clause = (
        f'FILTER(regex(COALESCE(str(?label), ""), "{safe_query}", "i") || regex(str(?uri), "{safe_query}", "i"))'
        if safe_query
        else ""
    )

    # SPARQL note: FROM does not propagate into subqueries (SPARQL 1.1 §8.2).
    # Flattening the OPTIONAL label lookup into the outer WHERE ensures it
    # runs inside the FROM-scoped dataset.
    oxigraph = request.app.state.oxigraph
    sparql = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?uri ?label
        {oxigraph.from_clause()}
        WHERE {{
            ?uri a <{target_class}> .
            OPTIONAL {{ ?uri rdfs:label ?label . }}
            {filter_clause}
        }}
        ORDER BY ?label
        LIMIT {limit}
    """

    try:
        rows = oxigraph.query(sparql)
    except Exception:
        return []

    return [
        {"uri": r["uri"], "label": r.get("label", r["uri"])}
        for r in rows
        if r.get("uri")
    ]
