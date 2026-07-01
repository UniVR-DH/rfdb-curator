"""Dry-run validation route: validate JSON-LD without persisting anything.

Used by the frontend `ValidationPanel` when the user wants to preview SHACL
errors before committing a save.  Unlike `POST /api/data`, this endpoint does
not merge referenced entities from the store, so it validates only what is
explicitly in the payload.
"""

import json

from fastapi import APIRouter, HTTPException, Request
from rdflib import Graph

from models.data import EntityData, ValidationResult

router = APIRouter()


@router.post("/validate", response_model=ValidationResult)
def validate_entity(payload: EntityData, request: Request):
    """Validate a JSON-LD entity against the SHACL schema without storing it.

    Returns the same `ValidationResult` structure as the write endpoint so
    the frontend can display violations identically in both cases.
    """
    data_graph = Graph()
    try:
        data_graph.parse(data=json.dumps(payload.data), format="json-ld")
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid JSON-LD: {exc}") from exc

    result = request.app.state.shacl_validator.validate(data_graph)
    return ValidationResult(**result)
