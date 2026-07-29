# TODO — RossijskijFeatrDB

Open work grouped by area — **UI**, **Backend**, **DevOps** — with priority and
`REQUIRES BRAINSTORM` tags kept inline. Completed work is dropped once nothing open depends
on it; where an open task builds on something already shipped, that context is noted inline.
[Non-Goals](#non-goals) closes the file.

---

## UI

- [ ] Auto-refresh entity lists (e.g. "has place" relations) when backend data changes behind the scenes.
- [ ] Records pagination with a default page size of 20 (frontend side; pairs with cursor-based SPARQL pagination under [Backend](#backend)).
- [x] Entity relationship graph visualization — **shipped** as the read-only Graph Explorer (`explorer/`): a schema-driven lineage/relationship graph over `GET /api/graph/node`, with search-seeded entry, expand-on-demand (pre-fetched link counts), and an "Open in Explorer" deep-link from the editor. Deliberately a *simple* read-only visualizer, consistent with [Non-Goals](#non-goals) ("provide complex graph visualization") — not an interactive graph editor.
- [ ] Real-time validation — debounced SHACL checking on blur/change via `POST /api/validate`.
- [ ] Warn on duplicate `owl:sameAs`: when a same-as value is entered, check whether another record already has it and warn the user (needs a backend lookup).
- [ ] Data Context Panel enhancements on top of the shipped read-only baseline (the panel plus its metadata API — `GET /api/meta/prefixes`, `GET /api/meta/graphs` with per-graph active/empty status, `GET /api/meta/files`):
  - [ ] Prefixes: per-entry `source` attribution (`schema` / `jsonld-context` / `runtime`); explicit prefix-drift warnings when mappings differ across schema, JSON-LD context, and runtime; copy Turtle prefix declaration / copy namespace IRI; search by prefix or namespace substring.
  - [ ] Phase 2 — operational guardrails: store health indicators, metadata freshness timestamp, schema/context mismatch diagnostics, actionable hints.
  - [ ] Phase 3 (optional, gated) — advanced operations: graph snapshot export, non-destructive graph diagnostics, controlled operational utilities. Keep the panel read-only in the baseline deployment; do not add delete/clear actions unless separately designed and approved.

---

## Backend

### High priority

- [ ] **REQUIRES BRAINSTORM + USER APPROVAL — optimize startup bulk load of large vocab files.**
  The ~38 MB `data/glottolog_language.ttl` is re-loaded via `POST /store` on every startup
  ([backend/core/seeder.py](backend/core/seeder.py), [backend/core/oxigraph_client.py](backend/core/oxigraph_client.py) `load_turtle`).
  This is slow and previously timed out (mitigated for now by the configurable `OXIGRAPH_LOAD_TIMEOUT`,
  default 300s). Options to brainstorm: skip re-seeding when the graph already holds the vocab
  (idempotency check), one-time offline load into a persisted Oxigraph volume, Oxigraph
  bulk-loader / native import instead of HTTP, streaming/chunked upload, or splitting vocab from
  large reference data. Decide and get user sign-off before implementing. (The Glottolog
  vocabulary itself is already hydrated and wired to `rfdbs:SourceShape` `dcterms:language`;
  this task concerns only how it is loaded, not the feature.)

- [ ] **REQUIRES BRAINSTORM — manage Julian vs Gregorian calendar dates.** Historical sources
  (especially pre-1918 Russian material) record dates in the Julian calendar, but XSD date
  datatypes carry no calendar-system information, so a value like `prism:publicationDate "1736"`
  is ambiguous about which calendar it is in. Decide how to record the calendar system and how
  to relate the as-in-source (Julian) value to a normalized (Gregorian) one — e.g. a
  calendar-system qualifier property, dual Julian/Gregorian properties, or a reified date node —
  plus backend conversion between the two. Spans schema (SHACL date fields), backend
  (validation/conversion; ties into the cross-entity date-order check under
  [Modeling & schema](#modeling--schema)), and UI (date input picks a calendar; display can show
  both). Brainstorm the modeling and get user sign-off before implementing.

### Modeling & schema

- [ ] Complete the shape-role policy for nested shapes and helper records (see [architecture.md](docs/architecture.md#shape-role-policy)).
- [ ] Cleanup for orphaned bridge entities after delete (e.g. `AgentRole` nodes left after their only parent is removed): cascade delete, an explicit cleanup endpoint, or an orphan-detection job. See [architecture.md](docs/architecture.md#delete-behavior-and-orphaned-helper-nodes).
- [ ] Improve JSON-LD handling for nested forms and repeated multilingual values.
- [ ] Expand the controlled-vocabulary seed set.
- [ ] Support ruoli vocali / personaggi as AgentRoles in their own right.
- [ ] Performances need the participant roles: scenografo, coreografo, ballerini, cantanti/attori, musicisti.
- [ ] Performances need the Source that attests them, linked to the performance (not to the work or expression). Sometimes a manifestation is the source, sometimes another source such as an anthology.
- [ ] For a Performance, select the Venue too (not only the Place; keep Place, since it is not always known) and consider coordinates for venues.
- [ ] Validity check on dates between MusicalWork, Expression, and Manifestation (e.g. an Expression's creation date should be after the Work's).
- [ ] Model corago-style "Fonte Per": a work derived from another work.

### Data, search & export

- [ ] Replace OFFSET-based pagination with cursor-based SPARQL pagination for large graphs.
- [ ] Smarter search ranking that favours edit distance without relying on a server-side cap or limit.
- [ ] Bulk import (Excel/CSV → RDF).
- [ ] Data export (RDF, JSON-LD, CSV) — the triples-only export, distinct from the full snapshot below.
- [ ] **REQUIRES BRAINSTORM — full snapshot export (schema + data + files).** A consistent,
  restorable export of the whole curated state — SHACL schema graph, the data graph(s), and the
  Garage-stored digital-copy blobs — not just a triples dump. Leaning toward a background export
  script (`backend/scripts/`) producing versioned/timestamped snapshots rather than a UI feature.
  Open questions: bundle format (tar of `schema.ttl` + `data.ttl`/`data.nq` + `files/` + a manifest
  linking digital-copy IRIs → blob keys); point-in-time consistency across Oxigraph + Garage
  (snapshot ordering / brief read lock vs. reconcile-after); trigger (cron via the existing
  scheduler? on-demand CLI? both?); where snapshots land (local volume vs. a dedicated Garage
  bucket); whether it doubles as the backup/restore path; and a matching import/restore counterpart.
- [ ] Audit trail / change history.
- [ ] Pre-flight check: validate the SHACL shapes for consistency before the server starts, rejecting unsupported features/paradigms (e.g. shapes without a `targetClass`).

### Platform & future

- [ ] **FUTURE — multi-user editing.** The editor assumes a single concurrent curator. No optimistic
  locking or transactions: concurrent edits to the same entity can interleave (delete-then-insert
  update flow in `api/data.py`), and cross-store operations (Oxigraph triples + Garage objects) are
  not atomic. Needed before multiple curators work simultaneously: conflict detection (e.g.
  ETag/version triple per entity) and a saga/compensation pattern for file-upload + triple-write.
  File-id minting is already race-safe (random 8-hex suffixes, never reused).
- [ ] **FUTURE — storage.** Evaluate LanceDB for digital-copy storage once basic PDF upload (Garage)
  ships in production. Idea: store PDF text + page embeddings alongside blobs to make scanned
  sources semantically searchable, not just downloadable. Kept low-risk by the `core/file_storage.py`
  seam — a later, isolated swap. Trade-offs: embedded (no separate S3 service) and unlocks semantic
  search, but is not blob-first, has no S3 API, and needs an OCR/embedding pipeline.
- [ ] **REQUIRES BRAINSTORM — decouple the backend from the triplestore so Oxigraph can be swapped.**
  Today Oxigraph is reached directly via `backend/core/oxigraph_client.py` (HTTP SPARQL +
  `load_turtle`) from routes and seeders. Introduce a `TripleStore` interface
  (query / update / load / graph management) with Oxigraph as the first implementation — mirroring
  the `core/file_storage.py` seam that already isolates Garage — so another store (Fuseki/Jena,
  Blazegraph, GraphDB, Qlever, RDF4J, an embedded lib, …) can be dropped in via config. Open
  questions: how much to lean on plain SPARQL 1.1 vs. per-store adapters; the bulk-load path (ties
  into the startup bulk-load gap above); transaction/atomicity semantics that differ across stores;
  and a conformance test suite each backend must pass.

---

## DevOps

> Context — the digital-copy upload-first subsystem (staging → `registered/` promotion,
> `core/file_storage.py`, `scripts/cleanup_files.py`, `GET /api/meta/files`) is shipped and
> live-verified in dev. The first two items below cover its production deployment and operation.

- [ ] **OPERATIONAL — run the file-storage cleanup periodically:** `docker compose exec backend python scripts/cleanup_files.py` (add `--dry-run` to preview). Purges abandoned staged uploads (>24h), unreferenced registered files (>24h grace), and orphaned digital-copy nodes. The Data Context Panel "File storage" section shows when counts grow.
- [ ] Production digital-copy storage: add `garage` to `docker-compose.prod.yml` (internal-only, hardened), a Caddy `request_body max_size`, and the matching DEV/DEPLOY/README docs. See [deployment.md](docs/deployment.md#production-deployment-work-in-progress).
- [ ] Investigate what dominates build/deploy time (backend especially) and whether it can be sped up.
- [ ] Set up automated release to GitHub Releases and the GitHub package registry.
- [ ] Verify versioning and commit tagging work with GitHub Actions (automatic release from tagged commits).
- [ ] Configure Docker Compose for production: Caddy reverse proxy + TLS termination, internal-only triple/object stores. See the [production deployment plan](docs/deployment.md#production-deployment-work-in-progress).

---

## Non-Goals

The initial version does not aim to:

- implement a full ontology editor;
- replace SHACL authoring tools;
- provide complex graph visualization;
- automate ontology migration;
- infer inverse relations unless required by the schema;
- enforce constraints not present in SHACL;
- replace expert data curation.
