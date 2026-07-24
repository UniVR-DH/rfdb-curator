"""Entity autocomplete search route used by relation (EntitySearch) fields.

When a user types into a relation field (e.g., `core:hasPlace`) the frontend
calls `GET /api/entities/search?shape=PlaceShape&query=<text>` and renders
the results as dropdown options.  The search fires on an empty query too, so
the dropdown is pre-populated when the field receives focus.

SPARQL strategy: a flat `GROUP BY ?uri` with `SAMPLE` collapses entities that
carry several `rdfs:label` / `rdfs:comment` values to one row each, and a FILTER
applies the case-insensitive text match on the label or the IRI. Each result
carries `uri`, `label`, and (when present) `comment` — the dropdown shows the
comment as a secondary line to help tell similarly-named entities apart.
"""

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter()


@router.get("/entities/search")
def search_entities(
    request: Request,
    shape: str = Query(..., description="Shape label or full URI (e.g. PlaceShape)"),
    query: str = Query("", description="Partial label or IRI to match"),
    limit: int = Query(50, ge=1, le=100),
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
        f'FILTER(regex(COALESCE(str(?label_raw), ""), "{safe_query}", "i") '
        f'|| regex(str(?uri), "{safe_query}", "i"))'
        if safe_query
        else ""
    )

    # SPARQL notes:
    #  - FROM does not propagate into subqueries (SPARQL 1.1 §8.2), so the query
    #    stays flat and the OPTIONAL lookups run inside the FROM-scoped dataset.
    #  - GROUP BY ?uri + SAMPLE collapses entities that carry several labels or
    #    comments to one row each; ordering by the grouping key keeps Oxigraph
    #    happy (the frontend re-sorts by label anyway).
    oxigraph = request.app.state.oxigraph
    sparql = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?uri (SAMPLE(?label_raw) AS ?label) (SAMPLE(?comment_raw) AS ?comment)
        {oxigraph.from_clause()}
        WHERE {{
            ?uri a <{target_class}> .
            OPTIONAL {{ ?uri rdfs:label ?label_raw . }}
            OPTIONAL {{ ?uri rdfs:comment ?comment_raw . }}
            {filter_clause}
        }}
        GROUP BY ?uri
        ORDER BY ?uri
        LIMIT {limit}
    """

    try:
        rows = oxigraph.query(sparql)
    except Exception:
        return []

    return [
        {"uri": r["uri"], "label": r.get("label", r["uri"]), "comment": r.get("comment")}
        for r in rows
        if r.get("uri")
    ]
