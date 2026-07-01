# Overview

## Project Purpose

RossijskijFeatrDB (rfdb) is a curated RDF knowledge base of Russian theatrical works and their libretti, covering the FRBR hierarchy from abstract works down to physical sources (library copies). It provides Python tooling to validate that data, generate structured Excel workbooks for data entry, and convert filled workbooks back to RDF.

## Users

- Musicologists and theatre historians cataloguing Russian opera/theatre repertoire
- Data curators entering bibliographic records via Excel (non-technical)
- Developers and researchers querying or extending the RDF dataset

## Main Features

1. **RDF dataset** (`data/data.ttl`, `data/vocab.ttl`) — example musical works, libretto expressions/manifestations, agents, roles, and library sources modelled in Turtle.
2. **SHACL schema** (`schema/schema.ttl`) — LRMoo + CIDOC-CRM aligned shapes constraining works, librettos, persons, roles, agent-roles, sources, places, and holding organisations.
3. **SHACL validator** (`rfdbtools.validator`) — validates RDF data against the schema; run via `python -m rfdbtools.run validate`.
4. **Excel generator** (`rfdbtools.shacl_excel_generator`) — derives one sheet per SHACL shape and produces an `.xlsx` workbook with a Prefixes sheet, column annotations, and hyperlinks; run via `python -m rfdbtools.run get_excel`.
5. **Excel-to-RDF converter** (`rfdbtools.shacl_excel_converter`) — reads a filled workbook plus its mapping JSON and emits a valid Turtle file; run via `python -m rfdbtools.run get_rdf`.
6. **Ontology pipeline** (`rfdbtools.download_ontologies`, `rfdbtools.convert_ontologies`) — downloads and converts all referenced ontologies (FaBiO, LRMoo, CIDOC-CRM, Polifonia core/mm/source) to Turtle for local validation.
7. **Web explorer** (`explorer/`) — standalone React/Vite single-page app for browsing the dataset.
8. **Editor** (`editor/`) — full-stack SHACL-driven CRUD application with three-panel UI, dry-run SHACL validation, and autocomplete for relation fields.

## Business Goals

- Build a freely reusable, openly licensed RDF catalogue of Russian theatrical heritage linked to Wikidata and VIAF.
- Lower the barrier for domain experts to contribute data through a familiar Excel workflow while keeping the canonical representation in standards-compliant RDF.
- Ensure data quality through automated SHACL validation in CI/CD.
- Provide a reference implementation of LRMoo + CIDOC-CRM modelling for musical works and their textual sources.

## Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Main language | Python 3.12 |
| Package manager | `uv` (exact pins via `pyproject.toml` + `uv.lock`) |
| RDF/Ontologies | FaBiO, Music Meta (Polifonia), Core (Polifonia), Source (Polifonia), FRBR, LRMoo, Dublin Core |
| SHACL | pyshacl |
| Data tools | rdflib, pandas, openpyxl |
| Editor backend | FastAPI + uvicorn, pydantic-settings, httpx |
| Frontend | React 19 + Vite, lucide-react |
| Linting | ruff, ESLint, Prettier |
| Documentation | pdoc |
| CI/CD | GitHub Actions, pre-commit hooks |
