# Overview

## Project Purpose

RossijskijFeatrDB (rfdb-curator) is a standalone SHACL-driven RDF curation project focused on Russian theatrical works and libretti. The repository ships a full editing stack for schema-aware CRUD operations, validation, and data inspection.

## Users

- Musicologists and theatre historians curating records
- Data curators managing linked RDF entities
- Developers maintaining backend, frontend, and schema behavior

## Main Features

1. **SHACL schema** (`schema/schema.ttl`) drives forms and validation.
2. **Backend API** (`backend/`) provides shape extraction, CRUD, linked-entity search, and validation.
3. **Frontend editor** (`frontend/`) renders dynamic forms and record workflows.
4. **RDF data** (`data/vocab.ttl`, `data/data.ttl`) seeds vocabulary and optional fixtures.
5. **Validation pipeline** (pySHACL + merged validation graph) enforces schema constraints.
6. **Object storage** (Garage, S3-compatible) holds source digital copies (PDF scans); metadata lives in RDF, bytes in Garage.
7. **Docker runtime** (`docker-compose.yml`) runs frontend, backend, Oxigraph, and Garage together.

## Business Goals

- Keep RFDB curation schema-driven and adaptable to model evolution.
- Maintain data quality through SHACL validation before persistence.
- Provide a practical editorial interface over standards-compliant RDF.

## Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, uvicorn, pydantic-settings, rdflib, pyshacl |
| Frontend | React, Vite |
| RDF store | Oxigraph |
| Object storage | Garage (S3-compatible), boto3 client |
| Runtime | Docker Compose |
| Testing | pytest |
| CI/CD | GitHub Actions |
