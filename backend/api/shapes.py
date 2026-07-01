"""Shape metadata routes used to build the sidebar nav and form schemas.

`GET /api/shapes` is called once at startup by the React app to populate the
shape list.  `GET /api/forms` is called each time the user selects a shape to
retrieve the ordered list of field definitions that drive form generation.
"""

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/shapes")
def list_shapes(request: Request):
    """Return all SHACL NodeShapes with metadata.

    Each item includes the shape URI, human-readable label (from `rdfs:label`),
    description, CURIE and full-URI forms of `sh:targetClass`, a `shapeRole`
    classification, and the list of property descriptors (same as `fields` in
    the forms response).
    """
    return request.app.state.schema_extractor.get_all_shapes()


@router.get("/forms")
def get_form_schema(shapeId: str, request: Request):
    """Return form field definitions for a SHACL shape.

    The `fields` array mirrors the `properties` list from `/api/shapes` but is
    returned alongside the parent `shape` object so the form component has
    everything it needs in one round-trip.  Field `type` values map directly to
    React components: `lang-string` → language-tagged text input, `entity-search`
    → async autocomplete, `nested` → `AnonymousEntityEditor`, etc.
    """
    shape = request.app.state.schema_extractor.get_shape(shapeId)
    if shape is None:
        raise HTTPException(status_code=404, detail=f"Shape '{shapeId}' not found")
    return {"shape": shape, "fields": shape["properties"]}
