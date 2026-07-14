# TODO for RossijskijFeatrDB

## Known Gaps

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
- [ ] active data graph from `DATA_GRAPH_URI` — via `GET /api/meta/graphs`
- [ ] available named graphs in Oxigraph — via `GET /api/meta/graphs`
- [ ] lightweight graph statistics (triple counts) — via `GET /api/meta/graphs`
- [ ] prefix / config consistency warnings — via `GET /api/meta/graphs`

Milestones:

- [x] Backend `GET /api/meta/prefixes` — **shipped** (resolved the prefix-map duplication gap above; `.temp/temp-DONE-prefix-consolidation-20260713.md`)
- [ ] Backend `GET /api/meta/graphs` — planned (Task 1 in the plan doc)
- [ ] Frontend read-only `DataContextPanel` — planned (Task 2 in the plan doc)

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
- [ ] REQUIRES PLANNING: Comment / description fields should use a larger textarea instead of single-line input (need to brainstorm how to derive that from SHACL shapes, maybe some predicates are treated as "long text" fields by default)
- [ ] Dropdown selections should display both label and comment (not just label) with ellipsis if longer than a certain length, e.g., 100 characters, when available 
- [x] For shapes using `sh:or` with alternative `sh:class` constraints, render a class-selection dropdown so users can explicitly choose which class branch they are filling
- [x] READ_ONLY FLAG: add a flag to make the editor read-only and refuse with a message if the user tries to edit (for demo or presentation mode)
- [ ] File upload  of digital copy for Source entities (need to define which properties to use for this, and how to store the files, e.g. in a local `uploads/` folder with unique filenames and a mapping in the RDF data)
- [ ] somehwere put the mapping from xsd language acronym (EN, IT...) to the name 
- [ ] for a Performance we need to select also the Venue not only the place, but keep the place because we not always know, and for venues consider coordinates

### b. Advanced Features (from roadmap)
- [ ] Welcome / onboarding page with simple guide on how to use the editor (should be possible to re-open again)
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


### c. Development and Deployment

- [x] fix  warning  Unused eslint-disable directive 
- [ ] setup auto release to GitHub releases and github package registry
- [ ] verify versioning and commit tagging works correctly with GitHub Actions and automatic release based on tagged commits
- [ ] configure Docker Compose to run in production mode with Nginx reverse proxy and SSL termination
- [x] check closely in README.md the Repository Structure
- [ ] consider a pre-commit hook configuration (.pre-commit-config.yaml)
- [ ] make a pre-flight check for the backend to ensure that the SHACL shapes are valid and consistent before starting the server and that they do not contain unsupported features or paradgims (e.g., shapes without a targetClass)