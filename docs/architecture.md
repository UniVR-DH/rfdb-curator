# RFDB Curator — Architecture

How the pieces fit together: the schema-driven pipeline, backend and frontend
responsibilities, how SHACL shapes are extracted into form and validation metadata,
how validation and delete behave, and the storage/runtime stack. For the RDF/SHACL
modeling itself (ontologies, shapes, prefixes) see [data-model.md](data-model.md); for
the day-to-day workflow of changing schema/data/code see [development.md](development.md).

---

## Core Architectural Principle

`rfdb-curator` should remain schema-driven.

The frontend should not contain hard-coded assumptions about the current RossijskijFeatrDB entity model unless those assumptions are necessary for usability and are clearly isolated.

The preferred flow is:

```text
schema/schema.ttl
    ↓
backend schema extractor
    ↓
normalized form schema
    ↓
React dynamic form rendering
    ↓
JSON-LD payload
    ↓
RDF graph generation
    ↓
SHACL validation
    ↓
Oxigraph persistence
```

This separation is important because the RFDB schema may evolve. The editor must remain adaptable when shapes, properties, labels, target classes, or ontology alignments change.

---

## Detailed Backend Responsibilities

The backend is responsible for turning RDF and SHACL semantics into stable API structures usable by the frontend.

Expected backend responsibilities include:

- loading the active SHACL schema from `schema/schema.ttl`
- extracting all `sh:NodeShape` definitions
- extracting field descriptors from `sh:property` blocks
- preserving shape labels and descriptions
- resolving prefixes and compact IRIs
- detecting target classes
- detecting field value kind: literal, IRI, linked entity, fixed value
- detecting cardinality
- detecting repeatability
- detecting datatype alternatives from `sh:or`
- detecting linked shapes from `sh:node`
- detecting expected target classes from `sh:class`
- validating submitted payloads with pySHACL
- merging referenced entities into validation graphs when needed
- loading RDF data into Oxigraph
- querying entities by shape
- providing autocomplete for linked-resource fields
- returning human-readable validation errors where possible
- exposing operational metadata, such as prefix maps and named graph status

---

## Detailed Frontend Responsibilities

The frontend is responsible for rendering usable editorial workflows from backend-provided shape metadata.

Expected frontend responsibilities include:

- listing available shapes in the navigation
- showing per-shape entity counts
- rendering dynamic forms from `/api/forms`
- showing required fields clearly
- distinguishing single-valued and repeatable fields
- supporting language-tagged literal inputs
- supporting date precision choices
- supporting IRI inputs and linked-record selectors
- supporting autocomplete for relation fields
- preserving `@id` and `@type` during editing
- showing compact IRIs alongside labels
- showing form-level and field-level validation errors
- supporting dry-run validation before save
- showing RDF triples for record inspection
- avoiding accidental regeneration of helper-node IRIs on update

---

## SHACL Extraction Details

The schema extractor should treat `sh:NodeShape` as the primary source for form definitions.

Important SHACL terms and expected behavior:

```text
sh:NodeShape
    Defines a record/form type.

sh:targetClass
    Defines the RDF class or classes targeted by a shape.

sh:class
    Defines the expected class of a linked resource or an additional class constraint.

sh:property
    Defines a form field.

sh:path
    Defines the RDF predicate for the field.

sh:minCount
    Defines required cardinality.

sh:maxCount
    Defines maximum cardinality. `sh:maxCount 1` means single-valued.

sh:datatype
    Defines literal datatype.

sh:nodeKind sh:IRI
    Defines IRI-valued fields.

sh:or
    Defines alternative constraints, often used for alternative literal datatypes.

sh:node
    Points to another shape, useful for generating linked-record selectors.

sh:description
    Provides field-level or shape-level help text.

sh:uniqueLang
    Prevents duplicate language tags for values of the same property.

sh:closed true
    Indicates that records should not contain properties outside the shape definition.

sh:hasValue
    Defines a fixed required value, for example a required `rdf:type`.
```

The extractor should preserve enough information for both rendering and validation feedback.

---

## Helper/Bridge Shape Classification

Shape behavior in the UI is schema-driven, not hardcoded per class name.

- If a shape declares a `sh:property` with `sh:path rdfs:label`, the backend classifies it as a standalone `external-entity`.
- If a shape has no `rdfs:label` property, the backend classifies it as a `helper-bridge` shape.
- If a parent property uses `sh:node` to point at a `helper-bridge` shape, the form generator exposes that field as a nested inline editor instead of a normal top-level linked entity form.

`rfdbs:AgentRoleShape` is the current example of this pattern. It is referenced from `core:hasAgentRole`, defines no `sh:property` whose `sh:path` is `rdfs:label`, and is therefore edited inline as a bridge between the parent Work/Expression and the linked `Person`/`Role` records.

When changing this behavior, check both the SHACL shape and the resulting `/api/shapes` metadata before changing frontend code. A shape can look label-like because it has a shape-level `rdfs:label` for display, but the classifier only cares whether the shape defines an RDF property with `sh:path rdfs:label`.

---

## Validation Merge Behavior

`POST /api/data` should validate against a graph that includes:

- the submitted payload
- relevant referenced entities already present in the store
- transitively linked helper nodes up to a bounded depth

This is necessary for incremental top-down editing.

Example:

```text
Work
    → AgentRole
        → Person
        → Role
```

If a later payload references the Work but does not repeat the AgentRole, Person, and Role nodes, validation should still have enough context to avoid false negatives.

---

## Delete Behavior and Orphaned Helper Nodes

Current planned behavior:

```text
DELETE /api/data/{entityId}
```

removes triples where the entity is the subject.

Known issue:

- bridge/helper nodes linked only from the deleted entity may remain orphaned
- common example: `AgentRole` nodes

Future options:

- cascade delete for helper nodes
- explicit cleanup endpoint
- orphan detection job
- UI warning before delete
- shape-role policy distinguishing external entities from helper bridges

---

## Shape-Role Policy

The editor needs a policy for nested shapes.

Important distinction:

```text
external entity
    A reusable entity with independent meaning and lifecycle.

helper bridge
    A structural node mainly meaningful in relation to another entity.
```

Examples:

- Person: external entity
- Role: external entity
- Place: external entity
- Holding Organization: external entity
- AgentRole: likely helper bridge

This distinction affects:

- creation UI
- deletion behavior
- update behavior
- autocomplete
- cascade cleanup
- validation graph expansion

---

## Metadata API

Read-only metadata endpoints:

```text
GET /api/meta/prefixes   — shipped
GET /api/meta/graphs     — planned
```

### Prefix Metadata — Shipped

Endpoint:

```text
GET /api/meta/prefixes
```

Implemented in `backend/api/meta.py`, registered in `backend/app.py`, tested in
`tests/test_api_meta.py`. This was the first milestone of the Data Context Panel
(see [roadmap.md](roadmap.md)) and also resolved the prefix-map duplication gap between
`utils/prefixes.js` and `utils/jsonld.js` on the frontend — both now hydrate from
this single endpoint at app startup (`frontend/src/App.jsx`).

Actual response shape (flatter than originally sketched — a plain object, not an
array with per-entry `source`/`warnings`):

```json
{
  "prefixes": {
    "rfdb": "https://rosfeatr.eu/rdf/data/",
    "xsd": "http://www.w3.org/2001/XMLSchema#"
  }
}
```

Derived directly from `request.app.state.schema_extractor.graph.namespaces()` —
i.e. the schema graph's namespace manager only. The richer shape below (merging
JSON-LD context and runtime config per-entry, with drift `warnings`) remains a
possible future enhancement for the [Prefixes tab](roadmap.md), not yet implemented:

```json
{
  "prefixes": [
    {
      "prefix": "rfdb",
      "namespace": "https://rosfeatr.eu/rdf/data/",
      "source": "schema"
    }
  ],
  "warnings": []
}
```

The planned `GET /api/meta/graphs` endpoint is described in [roadmap.md](roadmap.md).

---

## Storage and Runtime Stack

The application runs as a small set of Docker Compose services.

- **Backend** — FastAPI + uvicorn. Loads and extracts the SHACL schema, validates
  submitted JSON-LD with pySHACL, and reads/writes RDF through the Oxigraph HTTP API.
- **Frontend** — React + Vite. Renders forms from `/api/shapes` and `/api/forms`.
- **Oxigraph** — the RDF triple store. All instance data lives in a single named graph
  identified by `DATA_GRAPH_URI`; every SPARQL read uses `FROM <uri>` and every Turtle
  load targets `?graph=<uri>` via the Graph Store Protocol. It is the source of truth
  for the graph data and the only stateful volume that must be backed up
  (`oxigraph_data`).
- **Garage** — an S3-compatible object store for digital copies (uploaded PDFs and
  similar). A digital copy is modeled as a bridge node whose fields are machine-filled:
  a file is staged first (`POST /api/files/staged`), travels in the JSON-LD payload
  under its schema-declared predicate, and is promoted from `staged/` to `registered/`
  when the record is persisted. RDF remains the source of truth; object storage is
  reconciled against it. Garage is wired into dev Compose via `garage.toml` and the
  host-side `scripts/garage-init.sh`; production hardening lives in the deployment notes.

In production a reverse proxy (Caddy) terminates TLS and routes `/` to the frontend and
`/api` to the backend; Oxigraph and Garage stay internal-only. See
[deployment.md](deployment.md) for the production topology.
