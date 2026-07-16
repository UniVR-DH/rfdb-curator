"""Meta routes: schema-level information not tied to individual shapes or entities.

Currently exposes:
  GET /api/meta/prefixes — curated CURIE prefix map (core/prefixes.py).
  GET /api/meta/graphs   — active/named graphs, triple counts, config warnings.

These back the read-only Data Context Panel (see TODO.md).
"""

from fastapi import APIRouter, HTTPException, Request

from core.config import settings
from core.prefixes import PREFIXES

router = APIRouter()


@router.get("/meta/prefixes")
def get_prefixes():
    """Return the curated CURIE prefix→namespace map.

    Served from the hand-maintained ``core.prefixes.PREFIXES`` (the union of the
    ``@prefix`` declarations across schema/data/vocab/glottolog), **not** the rdflib
    schema graph — the latter also carries ~29 unrelated well-known vocabularies
    (``brick``, ``dcat``, …) that rdflib pre-binds into every ``Graph`` and would
    otherwise leak into the map. See ``core/prefixes.py`` for the maintenance note
    and the manual sanity check.

    Returns:
        ``{"prefixes": {"cidoc": "http://…", "xsd": "http://…", …}}``

    The frontend consumes this at startup to hydrate its prefix map for IRI
    compaction and the Data Context Panel.
    """
    return {"prefixes": dict(PREFIXES)}


def _count(rows: list[dict], key: str = "count") -> int:
    """Cast a SPARQL ``COUNT`` cell (a string, or None/missing) to int."""
    if not rows:
        return 0
    return int(rows[0].get(key) or 0)


@router.get("/meta/graphs")
def get_graphs(request: Request):
    """Return the runtime graph context: active graph, named graphs + triple
    counts, a store-wide total, and lightweight configuration warnings.

    Read-only and store-wide. Unlike normal route handlers, the two SPARQL
    queries run **unscoped** (no ``from_clause()``) so the panel can see every
    named graph, not just the configured data graph.

    Returns:
        ``{"activeGraph": str | None,
           "graphs": [{"uri", "count", "subjects", "objects", "literals", "active"}],
           "totalTriples": int, "totalSubjects": int, "totalObjects": int,
           "totalLiterals": int, "warnings": [str]}``

    Per-graph ``subjects``/``objects``/``literals`` are distinct-term counts within
    that graph. The ``total*`` distinct fields are counted once store-wide, so they
    can be smaller than the sum of the per-graph columns (a term can recur).

    Raises:
        HTTPException 503: when Oxigraph is unreachable (matches ``api/data.py``).
    """
    active_graph = settings.data_graph_uri or None
    oxigraph = request.app.state.oxigraph

    try:
        # Per-named-graph triple count + distinct subjects/objects, one grouped query.
        count_rows = oxigraph.query(
            "SELECT ?g (COUNT(*) AS ?count) (COUNT(DISTINCT ?s) AS ?subjects) "
            "(COUNT(DISTINCT ?o) AS ?objects) "
            "WHERE { GRAPH ?g { ?s ?p ?o } } GROUP BY ?g"
        )
        # Distinct literals per graph needs a FILTER, so a second grouped query.
        literal_rows = oxigraph.query(
            "SELECT ?g (COUNT(DISTINCT ?o) AS ?literals) "
            "WHERE { GRAPH ?g { ?s ?p ?o } FILTER(isLiteral(?o)) } GROUP BY ?g"
        )
        default_count = _count(
            oxigraph.query("SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }")
        )
        # Store-wide distinct totals for the footer. The UNION spans the default
        # graph and every named graph, deduplicating terms shared across graphs —
        # so these can be smaller than the sum of the per-graph columns.
        total_distinct_rows = oxigraph.query(
            "SELECT (COUNT(DISTINCT ?s) AS ?subjects) (COUNT(DISTINCT ?o) AS ?objects) "
            "WHERE { { ?s ?p ?o } UNION { GRAPH ?g { ?s ?p ?o } } }"
        )
        total_literal_rows = oxigraph.query(
            "SELECT (COUNT(DISTINCT ?o) AS ?literals) "
            "WHERE { { ?s ?p ?o } UNION { GRAPH ?g { ?s ?p ?o } } FILTER(isLiteral(?o)) }"
        )
    except Exception as exc:  # store unreachable / malformed response
        raise HTTPException(status_code=503, detail="Store unavailable") from exc

    literals_by_graph = {
        row["g"]: int(row.get("literals") or 0) for row in literal_rows if row.get("g")
    }
    graphs = sorted(
        (
            {
                "uri": row["g"],
                "count": int(row.get("count") or 0),
                "subjects": int(row.get("subjects") or 0),
                "objects": int(row.get("objects") or 0),
                "literals": literals_by_graph.get(row["g"], 0),
                "active": row["g"] == active_graph,
            }
            for row in count_rows
            if row.get("g")
        ),
        key=lambda item: item["uri"],
    )
    total_triples = sum(g["count"] for g in graphs) + default_count

    # Lightweight, advisory-only consistency hints (no severity/codes).
    warnings: list[str] = []
    if active_graph is None:
        warnings.append(
            "No DATA_GRAPH_URI configured; reads and writes target the default graph."
        )
    else:
        active_row = next((g for g in graphs if g["uri"] == active_graph), None)
        if active_row is None or active_row["count"] == 0:
            warnings.append(
                f"Active data graph <{active_graph}> is empty or absent in the store."
            )
    if default_count > 0:
        scope = f"<{active_graph}>" if active_graph else "the default graph"
        warnings.append(
            f"{default_count} triples live in the default graph and are invisible to "
            f"the editor (all reads are scoped to {scope})."
        )

    return {
        "activeGraph": active_graph,
        "graphs": graphs,
        "totalTriples": total_triples,
        "totalSubjects": _count(total_distinct_rows, "subjects"),
        "totalObjects": _count(total_distinct_rows, "objects"),
        "totalLiterals": _count(total_literal_rows, "literals"),
        "warnings": warnings,
    }
