"""FastAPI route handlers for the RossijskijFeatrDB data-entry API.

Routers
-------
shapes    GET /api/shapes, GET /api/forms  — shape metadata for sidebar and forms.
data      GET/POST/DELETE /api/data        — entity CRUD with SHACL validation.
entities  GET /api/entities/search         — autocomplete for relation fields.
validate  POST /api/validate               — dry-run SHACL validation.
"""
