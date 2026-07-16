# TODO for RossijskijFeatrDB

## Known Gaps

- **HIGH PRIORITY / REQUIRES BRAINSTORM + USER APPROVAL: Optimize startup bulk load of large vocab files.**
  The ~38 MB `data/glottolog_language.ttl` is re-loaded via `POST /store` on every
  startup ([backend/core/seeder.py](backend/core/seeder.py), [backend/core/oxigraph_client.py](backend/core/oxigraph_client.py) `load_turtle`). This is slow
  and previously timed out (mitigated for now by the configurable `OXIGRAPH_LOAD_TIMEOUT`,
  default 300s). Investigate a better load path — options to brainstorm: skip re-seeding
  when the graph already contains the vocab (idempotency check), one-time offline load
  into a persisted Oxigraph volume, Oxigraph bulk-loader / native import instead of HTTP,
  streaming/chunked upload, or splitting vocab from large reference data. Decide and get
  user sign-off before implementing.
- Expand the controlled-vocabulary seed set.
- Complete shape-role policy for nested shapes and helper records.
- Add cleanup for orphaned bridge entities after delete operations.
- Improve JSON-LD handling for nested forms and repeated multilingual values.
- Replace OFFSET-based pagination with cursor-based SPARQL pagination for large graphs.
- ~~**Prefix map duplication**~~ — resolved: `GET /api/meta/prefixes` (`backend/api/meta.py`) now serves the schema graph's namespace map, and `frontend/src/utils/prefixes.js` / `utils/jsonld.js` hydrate from it at startup (`frontend/src/App.jsx`). See `.temp/temp-DONE-prefix-consolidation-20260713.md` for the completed implementation plan.

---

## Planned Feature: Data Context Panel

A read-only panel exposing the runtime data context. Design and implementation plan:
`.temp/temp-data-context-panel-20260715.md`. The baseline version remains read-only and
must not expose destructive graph operations.

Exposed information:

- [x] active prefix mapping — served by `GET /api/meta/prefixes`, hydrated at startup
- [x] active data graph from `DATA_GRAPH_URI` — via `GET /api/meta/graphs`
- [x] available named graphs in Oxigraph — via `GET /api/meta/graphs`
- [x] lightweight graph statistics (triple counts) — via `GET /api/meta/graphs`
- [x] per-graph distinct subjects / objects / literals (columns in the graphs table) — via `GET /api/meta/graphs`
- [x] prefix / config consistency warnings — via `GET /api/meta/graphs`

Milestones:

- [x] Backend `GET /api/meta/prefixes` — **shipped** (resolved the prefix-map duplication gap above; `.temp/temp-DONE-prefix-consolidation-20260713.md`)
- [x] Backend `GET /api/meta/graphs` — **shipped** (`backend/api/meta.py`; 6 tests in `tests/test_api_meta.py`)
- [x] Frontend read-only `DataContextPanel` — **shipped** (`frontend/src/components/DataContextPanel.{jsx,css}`, wired in `App.jsx`). Live interactive smoke pending the stack run. Plan: `.temp/temp-data-context-panel-20260715.md`.

---

## Non-Goals

The initial version does not aim to:

- implement a full ontology editor
- replace SHACL authoring tools
- provide complex graph visualization
- automate ontology migration
- infer inverse relations unless required by the schema
- enforce constraints not present in SHACL
- replace expert data curation


---

## Editor Features

### a. Core features and bug fixes (from current development)
- [x] `RESET_DATA_ON_STARTUP=true` does not actually reset data when starting via Docker Compose
- [x] the `owl:sameAs` field allows multiple values (e.g. linking to multiple external authority records)
- [x] Allow `rdfs:label` / `rdfs:comment` without language tags for generic untranslated values
- [x] Expression form comment field renders as `[object Object]` instead of the actual string value
- [x] HIGH PRIORITY/REQUIRES PLANNING: Hydrate `data/glottolog_language.ttl` into Oxigraph and connect it to `rfdb:Source` language handling via `sh:path dcterms:language ; sh:nodeKind sh:IRI ;` in `rfdb:SourceShape`
- [x] HIGH PRIORITY/REQUIRES PLANNING: Language field in Source form should be a dropdown of available languages, not free text, check above
- [ ] Auto-refresh entity lists (e.g. "has place" relations) when backend data changes behind the scenes
- [ ] Implement records pagination with default page size 20
- [ ] Implement smarter search ranking that favors edit distance without relying on server-side cap or limit
- [ ] Preserve current form/page state on browser reload (survive refresh)
- [x] Comment / description fields use a larger textarea instead of single-line input — `longText` derived from SHACL in `schema_extractor.py`, rendered in `FormField.jsx` (fe848de)
- [ ] Dropdown selections should display both label and comment (not just label) with ellipsis if longer than a certain length, e.g., 100 characters, when available 
- [x] For shapes using `sh:or` with alternative `sh:class` constraints, render a class-selection dropdown so users can explicitly choose which class branch they are filling
- [x] READ_ONLY FLAG: add a flag to make the editor read-only and refuse with a message if the user tries to edit (for demo or presentation mode)
- [ ] File upload of digital copy (PDF) for Source entities — **planned**, design & implementation plan: `.temp/temp-source-pdf-upload-20260716.md`. Decided: Garage (S3-compatible) storage service, multiple PDFs per Source, PDF-only/no size cap, open access, RDF digital-copy node via `cidoc:P138i_has_representation` → `schema:DigitalDocument` (filename, sha256, byte size, page count). Milestones:
  - [ ] Garage service in Docker Compose (dev + prod)
  - [ ] Storage client + config (`core/file_storage.py`)
  - [ ] Schema `DigitalCopyShape` + `SourceShape` link property
  - [ ] Backend upload/list/download/delete routes (`api/files.py`)
  - [ ] Delete-lifecycle cleanup (purge files on Source delete)
  - [ ] Frontend `SourceFilesPanel` + client methods
  - [ ] Tests + docs
- [x] mapping from xsd language acronym (EN, IT...) to the name — `frontend/src/utils/languages.js` (fe848de)
- [ ] for a Performance we need to select also the Venue not only the place, but keep the place because we not always know, and for venues consider coordinates
- [ ] from the inspector sidebar link directly to record view for that entity

### b. Advanced Features (from roadmap)
- [~] Welcome / onboarding guide with simple guide on how to use the editor (should be possible to re-open again)
  - [x] First-time curator **WEMI overlay** — dismissible modal with a WEMI graph diagram (Work→Expression→Manifestation→Source, + Performance branch) and the ordered insertion steps; auto-opens on first visit (localStorage `rfdb.guideSeen`), re-openable via the "Getting started" button in the nav. Component: `frontend/src/components/WelcomeGuide.{jsx,css}`, wired in `frontend/src/App.jsx`. Plan: `.temp/temp-curator-welcome-guide-20260716.md`.
  - [ ] Optional follow-up: full field-level editor tour / bilingual (IT) copy.
- [ ] Real-time validation (debounced SHACL checking on blur/change)
- [ ] Bulk import (Excel/CSV → RDF)
- [ ] Data export (RDF, JSON-LD, CSV)
- [ ] Entity relationship graph visualization
- [ ] Audit trail / change history
- [ ] Cascade delete for orphaned bridge entities (AgentRole, etc.)
- [ ] SPARQL-level pagination cursor
- [ ] valdity check on dates between MusicalWork, Expression, and Manifestation (e.g. creation date of Expression should be after creation date of Work)
- [ ] for all same-as fields check if other records already have it and if so, warn the user 
- [ ] in the form, the dropdown selection for language and person should use the same UI component of the other selectors instead of the native HTML select, or at least a component with the same UI
- [ ] support ruoli vocali, personaggi as AgentRoles a part
- [ ]  for performances we need: scenografo, coreografo, ballerini, cantani/attori, musicisti 
- [ ] for performances we need to know the "source" that is telling us about the performance, and the source should be linked to the performance, not to the work or expression. Sometimes a manifestation is the source, sometimes is another source like an anthology 
- [ ] FUTURE / storage — evaluate LanceDB for digital-copy storage once basic PDF upload (Garage) ships. Idea: store PDF text + page embeddings alongside blobs to make scanned sources semantically searchable, not just downloadable.
  - Pros: embedded (no separate S3 service); metadata + vectors in one columnar store; unlocks semantic/full-text search & RAG over libretti; could unify "store file" + "make searchable".
  - Cons: not blob-first (large PDFs sit awkwardly next to vectors); no S3 API (backend still proxies downloads); needs an OCR/embedding pipeline (scope creep beyond storing a PDF); S3 is more operationally familiar for pure serving.
  - Kept low-risk by the `core/file_storage.py` seam introduced in the upload plan — a later, isolated swap.
- [ ] model as in corago "Fonte Per" meaning a work is derived from another work


### c. Development and Deployment
- [ ] verify why what is hogging the build and deploy time, especially in the backend, and if it is possible to speed up the build and deploy time
- [x] fix  warning  Unused eslint-disable directive 
- [ ] setup auto release to GitHub releases and github package registry
- [ ] verify versioning and commit tagging works correctly with GitHub Actions and automatic release based on tagged commits
- [ ] configure Docker Compose to run in production mode with Nginx reverse proxy and SSL termination
- [x] check closely in README.md the Repository Structure
- [x] pre-commit hook configuration (.pre-commit-config.yaml) — ruff lint + format, opt-in via `pre-commit install`
- [ ] make a pre-flight check for the backend to ensure that the SHACL shapes are valid and consistent before starting the server and that they do not contain unsupported features or paradgims (e.g., shapes without a targetClass)
- [ ] **prefix-map sanity check (manual)** — the CURIE map served by `GET /api/meta/prefixes` is a curated list in `backend/core/prefixes.py` (`PREFIXES`); it must be updated whenever a new `@prefix` is added to any TTL file (schema / data / vocab / glottolog). Run `cd backend && uv run python scripts/check_prefixes.py` to verify `PREFIXES` covers every declared prefix (reports missing / mismatched). Consider promoting this to an automated pre-flight/CI check later.