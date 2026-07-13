# TODO for RossijskijFeatrDB

## Known Gaps

- Expand the controlled-vocabulary seed set.
- Complete shape-role policy for nested shapes and helper records.
- Add cleanup for orphaned bridge entities after delete operations.
- Improve JSON-LD handling for nested forms and repeated multilingual values.
- Replace OFFSET-based pagination with cursor-based SPARQL pagination for large graphs.

---

## Planned Feature: Data Context Panel

A future read-only panel should expose:

- active prefix mapping
- active data graph from `DATA_GRAPH_URI`
- available named graphs in Oxigraph
- lightweight graph statistics
- prefix consistency warnings between schema, JSON-LD context, and runtime configuration

Planned endpoints:

- `GET /api/meta/prefixes`
- `GET /api/meta/graphs`

The baseline version should remain read-only and must not expose destructive graph operations.

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
- [ ] HIGH PRIORITY/REQUIRES PLANNING: Hydrate `data/glottolog_language.ttl` into Oxigraph and connect it to `rfdb:Source` language handling via `sh:path dcterms:language ; sh:nodeKind sh:IRI ;` in `rfdb:SourceShape`
- [ ] HIGH PRIORITY/REQUIRES PLANNING: Language field in Source form should be a dropdown of available languages, not free text, check above
- [ ] Auto-refresh entity lists (e.g. "has place" relations) when backend data changes behind the scenes
- [ ] Implement records pagination with default page size 20
- [ ] Implement smarter search ranking that favors edit distance without relying on server-side cap or limit
- [ ] Preserve current form/page state on browser reload (survive refresh)
- [ ] REQUIRES PLANNING: Comment / description fields should use a larger textarea instead of single-line input (need to brainstorm how to derive that from SHACL shapes, maybe some predicates are treated as "long text" fields by default)
- [ ] Dropdown selections should display both label and comment (not just label)
- [ ] For shapes using `sh:or` with alternative `sh:class` constraints, render a class-selection dropdown so users can explicitly choose which class branch they are filling
- [x] READ_ONLY FLAG: add a flag to make the editor read-only and refuse with a message if the user tries to edit (for demo or presentation mode)
- [ ] File upload  of digital copy for Source entities (need to define which properties to use for this, and how to store the files, e.g. in a local `uploads/` folder with unique filenames and a mapping in the RDF data)


### b. Advanced Features (from roadmap)

- [ ] Real-time validation (debounced SHACL checking on blur/change)
- [ ] Bulk import (CSV → RDF)
- [ ] Data export (RDF, JSON-LD, CSV)
- [ ] Entity relationship graph visualization
- [ ] Audit trail / change history
- [ ] Cascade delete for orphaned bridge entities (AgentRole, etc.)
- [ ] SPARQL-level pagination cursor
- [ ] valdity check on dates between MusicalWork, Expression, and Manifestation (e.g. creation date of Expression should be after creation date of Work)
- [ ] for all same-as fields check if other records already have it and if so, warn the user 



### c. Development and Deployment

- [x] fix  warning  Unused eslint-disable directive 
- [ ] setup auto release to GitHub releases and github package registry
- [ ] verify versioning and commit tagging works correctly with GitHub Actions and automatic release based on tagged commits
- [ ] configure Docker Compose to run in production mode with Nginx reverse proxy and SSL termination
- [x] check closely in README.md the Repository Structure
- [ ] consider a pre-commit hook configuration (.pre-commit-config.yaml)