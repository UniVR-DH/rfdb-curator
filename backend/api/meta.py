"""Meta routes: schema-level information not tied to individual shapes or entities.

Currently exposes:
  GET /api/meta/prefixes — namespace prefix map derived from schema.ttl at runtime.

This is the first milestone of the planned Data Context Panel (see TODO.md).
"""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/meta/prefixes")
def get_prefixes(request: Request):
    """Return the complete prefix-to-namespace map read from the active SHACL schema.

    Derived directly from the rdflib graph already cached by ``SchemaExtractor``,
    so no extra file I/O occurs after startup.  Empty-string prefixes (the base IRI
    convention used by rdflib) are excluded — they have no useful CURIE form.

    Returns:
        ``{"prefixes": {"cidoc": "http://…", "xsd": "http://…", …}}``

    The frontend consumes this response at startup to hydrate its prefix map,
    replacing the two previously hardcoded dictionaries in ``utils/prefixes.js``
    and ``utils/jsonld.js``.
    """
    prefixes = {
        prefix: str(ns)
        for prefix, ns in request.app.state.schema_extractor.graph.namespaces()
        if prefix  # skip the empty base-IRI entry rdflib always includes
    }
    return {"prefixes": prefixes}
