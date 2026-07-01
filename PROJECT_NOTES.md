# RFDB CURATOR PROJECT NOTES

This document collects implementation details, modeling notes, operational plans, and roadmap items that are useful for `rfdb-editor` but intentionally kept out of the main `README.md` to keep that file concise.

The main README should remain the entry point for setup, core architecture, and daily development. This file can be used as a reference for contributors working on schema extraction, validation behavior, linked-record modeling, metadata panels, and future backend or frontend extensions.

Status of this document:

- it is a technical reference for contributors
- it complements, but does not replace, `README.md`
- when behavior in notes and implementation diverges, implementation and README take precedence

---

## 1. Purpose of This Document

The main README focuses on the essential project information:

- what the app does
- how to run it
- the core architecture
- the main API endpoints
- the SHACL-driven form-generation principle
- the primary data model

This document keeps the remaining useful project-specific information:

- detailed ontology usage
- shape-specific behavior
- richer form-generation rules
- validation nuances
- planned metadata APIs
- graph and prefix console design
- operational constraints
- known gaps and follow-up work

---

## 2. Core Architectural Principle

`rfdb-editor` should remain schema-driven.

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

## 3. Detailed Backend Responsibilities

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

## 4. Detailed Frontend Responsibilities

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

## 5. SHACL Extraction Details

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

## 6. Current Prefix Map

The active schema currently declares these prefixes:

```turtle
@prefix cidoc:   <http://www.cidoc-crm.org/cidoc-crm/> .
@prefix core:    <https://w3id.org/polifonia/ontology/core/> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix lrmoo:   <http://iflastandards.info/ns/lrm/lrmoo/> .
@prefix mm:      <https://w3id.org/polifonia/ontology/music-meta/> .
@prefix owl:     <http://www.w3.org/2002/07/owl#> .
@prefix prism:   <http://prismstandard.org/namespaces/basic/2.0/> .
@prefix rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix rfdb:    <https://rfdb.it/data/> .
@prefix sh:      <http://www.w3.org/ns/shacl#> .
@prefix skos:    <http://www.w3.org/2004/02/skos/core#> .
@prefix source:  <https://w3id.org/polifonia/ontology/source/> .
@prefix wdt:     <http://www.wikidata.org/prop/direct/> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
```

The editor should use this prefix map for:

- compact IRI display
- full IRI expansion
- RDF export
- JSON-LD context generation
- autocomplete display
- field labels and diagnostics
- prefix-consistency checks

---

## 7. Ontologies and Vocabularies Used

### 7.1 RFDB Namespace

```text
rfdb: <https://rfdb.it/data/>
```

Used for local RFDB resources and SHACL shapes.

Examples:

```text
rfdb:MusicalWorkShape
rfdb:ExpressionShape
rfdb:SourceShape
rfdb:PlaceShape
rfdb:PrintedLibretto
rfdb:SanPietroburgo
```

The current schema does not define custom `rfdb:` predicates.

---

### 7.2 LRMoo

```text
lrmoo: <http://iflastandards.info/ns/lrm/lrmoo/>
```

Classes used:

```text
lrmoo:F1_Work
lrmoo:F2_Expression
lrmoo:F3_Manifestation
lrmoo:F5_Item
```

Properties used:

```text
lrmoo:R4_embodies
lrmoo:R7_exemplifies
```

Usage:

- Musical Works align with `lrmoo:F1_Work`.
- Expressions target `lrmoo:F2_Expression`.
- Manifestations target `lrmoo:F3_Manifestation`.
- Sources/Items target `lrmoo:F5_Item`.
- Manifestations embody Expressions through `lrmoo:R4_embodies`.
- Sources/Items exemplify Manifestations through `lrmoo:R7_exemplifies`.

---

### 7.3 CIDOC CRM

```text
cidoc: <http://www.cidoc-crm.org/cidoc-crm/>
```

Class used:

```text
cidoc:E89_Propositional_Object
```

Properties used:

```text
cidoc:P129_is_about
cidoc:P51_has_former_or_current_owner
```

Usage:

- Subjects are modeled as `cidoc:E89_Propositional_Object`.
- Musical Works can point to subjects through `cidoc:P129_is_about`.
- Sources point to holding organizations through `cidoc:P51_has_former_or_current_owner`.

---

### 7.4 Polifonia Core

```text
core: <https://w3id.org/polifonia/ontology/core/>
```

Classes used:

```text
core:Place
core:Type
core:Person
core:Role
core:AgentRole
core:Organization
```

Properties used:

```text
core:isPartOf
core:hasAgentRole
core:hasAgent
core:hasRole
core:hasPlace
core:hasType
core:text
```

Usage:

- `core:Place` for places.
- `core:Type` for source/document types.
- `core:Person` for persons.
- `core:Role` for roles.
- `core:AgentRole` for bridge records connecting agents and roles.
- `core:Organization` for holding institutions.
- `core:isPartOf` connects Expressions to parent Musical Works.
- `core:hasAgentRole` connects Works or Expressions to AgentRole records.
- `core:hasAgent` and `core:hasRole` define AgentRole internals.
- `core:hasPlace` links Sources and Organizations to Places.
- `core:hasType` classifies Sources.
- `core:text` stores title-page transcription.

---

### 7.5 Polifonia Music Meta

```text
mm: <https://w3id.org/polifonia/ontology/music-meta/>
```

Class used:

```text
mm:MusicEntity
```

Usage:

- Musical Works target `mm:MusicEntity`.
- Musical Works are also constrained as LRMoo works through `lrmoo:F1_Work`.

---

### 7.6 Polifonia Source

```text
source: <https://w3id.org/polifonia/ontology/source/>
```

Class used:

```text
source:Source
```

Usage:

- Sources target both `source:Source` and `lrmoo:F5_Item`.
- A Source is a particular physical or documentary copy held by an institution.

---

### 7.7 Dublin Core Terms

```text
dcterms: <http://purl.org/dc/terms/>
```

Properties used:

```text
dcterms:date
dcterms:language
dcterms:identifier
```

Usage:

- `dcterms:date` is used for Work dates.
- `dcterms:language` is used for Source/Item language IRIs.
- `dcterms:identifier` is used for shelfmarks or call numbers.

The schema suggests Glottolog IRIs for language values, for example:

```text
https://glottolog.org/resource/languoid/id/russ1263
```

---

### 7.8 PRISM

```text
prism: <http://prismstandard.org/namespaces/basic/2.0/>
```

Property used:

```text
prism:publicationDate
```

Usage:

- Manifestation publication dates.
- Source/Item publication dates.

Allowed date datatypes:

```text
xsd:date
xsd:gYear
xsd:gYearMonth
```

---

### 7.9 RDF, RDFS, OWL, SKOS, WDT, XSD

RDF terms:

```text
rdf:type
rdf:langString
```

RDFS properties:

```text
rdfs:label
rdfs:comment
rdfs:seeAlso
```

OWL property:

```text
owl:sameAs
```

SKOS property:

```text
skos:altLabel
```

Wikidata direct property:

```text
wdt:P214
```

XSD datatypes:

```text
xsd:string
xsd:date
xsd:gYear
xsd:gYearMonth
```

---

## 8. Shape-Specific Notes

### 8.1 Place

Shape:

```text
rfdb:PlaceShape
```

Target class:

```text
core:Place
```

Main fields:

- `rdfs:label`: required, exactly one
- `skos:altLabel`: repeatable language-tagged alternate labels
- `owl:sameAs`: repeatable external authority IRIs

---

### 8.2 Subject

Shape:

```text
rfdb:SubjectShape
```

Target class:

```text
cidoc:E89_Propositional_Object
```

Main fields:

- `rdfs:label`: required, exactly one
- `skos:altLabel`: repeatable language-tagged alternate labels

Subjects can represent themes, stories, plots, characters, narrative elements, or conceptual topics.

---

### 8.3 Source Type

Shape:

```text
rfdb:SourceTypeShape
```

Target class:

```text
core:Type
```

Main fields:

- `rdfs:label`: required, exactly one
- `skos:altLabel`: repeatable language-tagged alternate labels
- `rdfs:comment`: optional, at most one plain string

---

### 8.4 Musical Work

Shape:

```text
rfdb:MusicalWorkShape
```

Target class:

```text
mm:MusicEntity
```

Additional class constraint:

```text
lrmoo:F1_Work
```

Main fields:

- `rdfs:label`: required, exactly one
- `skos:altLabel`: repeatable alternate titles
- `dcterms:date`: optional, at most one date
- `owl:sameAs`: repeatable external authority IRIs
- `cidoc:P129_is_about`: repeatable links to Subject records
- `core:hasAgentRole`: repeatable links to AgentRole records

---

### 8.5 Expression

Shape:

```text
rfdb:ExpressionShape
```

Target class:

```text
lrmoo:F2_Expression
```

Main fields:

- `rdfs:label`: required, exactly one
- `skos:altLabel`: repeatable alternate labels
- `core:isPartOf`: required, exactly one link to a Musical Work
- `core:hasAgentRole`: repeatable links to AgentRole records
- `rdfs:comment`: optional, at most one plain string

---

### 8.6 Manifestation

Shape:

```text
rfdb:ManifestationShape
```

Target class:

```text
lrmoo:F3_Manifestation
```

Main fields:

- `rdfs:label`: required, exactly one
- `lrmoo:R4_embodies`: required, exactly one link to an Expression
- `prism:publicationDate`: optional, at most one date
- `rdfs:comment`: optional, at most one plain string

---

### 8.7 Source / Item

Shape:

```text
rfdb:SourceShape
```

Target classes:

```text
source:Source
lrmoo:F5_Item
```

Main fields:

- `rdfs:label`: required, exactly one
- `skos:altLabel`: repeatable alternate labels
- `prism:publicationDate`: optional, at most one date
- `dcterms:language`: repeatable language IRIs
- `core:hasPlace`: optional, at most one Place
- `core:hasType`: required, exactly one Source Type
- `cidoc:P51_has_former_or_current_owner`: required, exactly one Holding Organization
- `dcterms:identifier`: optional, at most one shelfmark or call number
- `core:text`: optional, at most one language-tagged title-page transcription
- `rdfs:seeAlso`: repeatable external reference IRIs
- `rdfs:comment`: optional, at most one note
- `lrmoo:R7_exemplifies`: optional, at most one Manifestation

---

### 8.8 Person

Shape:

```text
rfdb:PersonShape
```

Target class:

```text
core:Person
```

Main fields:

- `rdfs:label`: required, exactly one
- `skos:altLabel`: repeatable alternate labels
- `owl:sameAs`: repeatable external authority IRIs
- `wdt:P214`: optional, at most one VIAF link

---

### 8.9 Role

Shape:

```text
rfdb:RoleShape
```

Target class:

```text
core:Role
```

Main fields:

- `rdfs:label`: required, exactly one
- `skos:altLabel`: repeatable alternate labels

Roles are usually controlled records, for example composer, librettist, translator, arranger, or publisher.

---

### 8.10 Agent Role

Shape:

```text
rfdb:AgentRoleShape
```

Target class:

```text
core:AgentRole
```

Main fields:

- `rdf:type`: must include `core:AgentRole`
- `core:hasAgent`: required, exactly one Person
- `core:hasRole`: required, exactly one Role

This shape is closed. The editor must avoid adding unsupported properties unless the schema changes.

---

### 8.11 Holding Organization

Shape:

```text
rfdb:HoldingOrganizationShape
```

Target class:

```text
core:Organization
```

Main fields:

- `rdfs:label`: required, exactly one
- `skos:altLabel`: repeatable alternate labels
- `owl:sameAs`: repeatable authority IRIs
- `wdt:P214`: optional, at most one VIAF link
- `core:hasPlace`: required, exactly one Place

---

## 9. Linked-Entity Fields

Important linked fields and expected UI behavior:

```text
core:isPartOf
    Expression → Musical Work

lrmoo:R4_embodies
    Manifestation → Expression

lrmoo:R7_exemplifies
    Source / Item → Manifestation

core:hasAgentRole
    Musical Work or Expression → Agent Role

core:hasAgent
    Agent Role → Person

core:hasRole
    Agent Role → Role

core:hasPlace
    Source / Item or Holding Organization → Place

core:hasType
    Source / Item → Source Type

cidoc:P51_has_former_or_current_owner
    Source / Item → Holding Organization

cidoc:P129_is_about
    Musical Work → Subject
```

The frontend should support:

- lookup by label
- display of compact IRI
- selection of existing records
- optional creation of linked records, depending on workflow
- preservation of exact linked IRIs in submitted JSON-LD

---

## 10. Literal Field Handling

Common literal field patterns:

```text
rdfs:label
    rdf:langString or xsd:string

skos:altLabel
    rdf:langString

rdfs:comment
    xsd:string

dcterms:identifier
    xsd:string

core:text
    rdf:langString

dcterms:date
    xsd:date, xsd:gYear, or xsd:gYearMonth

prism:publicationDate
    xsd:date, xsd:gYear, or xsd:gYearMonth
```

The frontend should distinguish:

- plain strings
- language-tagged strings
- full dates
- year-only dates
- year-month dates
- IRI values

---

## 11. Language-Tagged Values

Fields such as `rdfs:label`, `skos:altLabel`, and `core:text` may require or allow language-tagged strings.

Example:

```turtle
rdfs:label "La forza dell'amore e dell'odio"@it .
```

The UI should support:

- entering a string value
- assigning a language tag
- validating the language tag
- enforcing `sh:uniqueLang true` where present
- preserving language tags in JSON-LD and RDF export

---

## 12. Date Precision

The schema supports multiple date precisions:

```text
xsd:date
xsd:gYear
xsd:gYearMonth
```

Examples:

```turtle
"1736-01-01"^^xsd:date
"1736"^^xsd:gYear
"1736-05"^^xsd:gYearMonth
```

The UI should allow users to preserve the intended precision. Avoid converting a year-only value into a full date unless explicitly required.

---

## 13. IRI Policy

Every persisted RDF resource must have a stable subject IRI.

Main project namespace:

```text
https://rfdb.it/data/
```

Compact form:

```text
rfdb:EntityID
```

Expanded form:

```text
https://rfdb.it/data/EntityID
```

Requirements:

- existing IRIs must not be silently changed
- new IRIs should follow a consistent generation policy
- helper/bridge IRIs should be preserved during updates
- full IRIs and prefixed IRIs should both be accepted where appropriate
- invalid IRIs should be rejected before persistence

---

## 14. Validation Merge Behavior

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

## 15. Class-Targeted Shape Nuance

Many shapes use `sh:targetClass`.

This means validation constraints apply only when the node declares the corresponding RDF class.

Important consequence:

- if a JSON-LD payload omits required `@type` values, some shape constraints may not run
- bridge/helper nodes should always include explicit `@type` values when the schema relies on class-targeted validation

For example, AgentRole payloads should include `core:AgentRole` among their `@type` values.

---

## 16. Delete Behavior and Orphaned Helper Nodes

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

## 17. Shape-Role Policy

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

## 18. Planned Data Context Panel

A future read-only UI panel should expose operational context for curators and developers.

Suggested name:

```text
Data Context
```

Suggested placement:

```text
Left sidebar, below shape navigation
```

The panel should include two tabs:

1. Prefixes
2. Named Graphs

---

## 19. Prefixes Tab

The Prefixes tab should show the complete namespace map used by the editor.

Columns:

- Prefix
- Namespace IRI
- Source

Possible sources:

- `schema`
- `jsonld-context`
- `runtime`

Features:

- search by prefix
- search by namespace substring
- copy namespace IRI
- copy Turtle prefix declaration
- warn when prefix mappings differ between schema, JSON-LD context, and runtime configuration

Example copy output:

```turtle
@prefix rfdb: <https://rfdb.it/data/> .
```

---

## 20. Named Graphs Tab

The Named Graphs tab should show graph-level operational status.

Header card:

- active graph from `DATA_GRAPH_URI`

Columns:

- Graph IRI
- Triple count
- Status

Possible statuses:

- `active`
- `non-empty`
- `empty`

The first version should be read-only. It must not expose delete, clear, or destructive graph actions.

---

## 21. Planned Metadata API

Planned read-only metadata endpoints:

```text
GET /api/meta/prefixes
GET /api/meta/graphs
```

### 21.1 Prefix Metadata

Endpoint:

```text
GET /api/meta/prefixes
```

Example response:

```json
{
  "prefixes": [
    {
      "prefix": "rfdb",
      "namespace": "https://rfdb.it/data/",
      "source": "schema"
    }
  ],
  "warnings": []
}
```

Prefix metadata should be merged from:

- schema graph namespace manager
- JSON-LD context map
- runtime configuration

The backend should serve this merged metadata to avoid frontend/backend drift.

### 21.2 Graph Metadata

Endpoint:

```text
GET /api/meta/graphs
```

Example response:

```json
{
  "activeGraph": "https://rfdb.it/graph/data",
  "graphs": [
    {
      "graph": "https://rfdb.it/graph/data",
      "tripleCount": 1234,
      "status": "active"
    }
  ]
}
```

Graph list should be computed through SPARQL over named graphs, including per-graph counts.

---

## 22. Planned Frontend Components for Data Context

Suggested components:

```text
DataContextPanel.jsx
PrefixesTable.jsx
GraphsTable.jsx
```

Suggested API client methods:

```text
getPrefixesMeta()
getGraphsMeta()
```

UI principles:

- read-only by default
- compact monospace IRI display
- copy buttons for IRIs and prefix declarations
- visible warning messages for prefix drift
- no side effects on form state
- no destructive actions in baseline deployment

---

## 23. Data Context Rollout Phases

### Phase 1: Read-Only Visibility

- show prefix table
- show active data graph
- show graph counts
- show prefix consistency warnings

### Phase 2: Operational Guardrails

- show store health indicators
- show metadata freshness timestamp
- show schema/context mismatch diagnostics
- include actionable hints when possible

### Phase 3: Advanced Operations

Optional and gated.

Possible additions:

- graph snapshot export
- non-destructive graph diagnostics
- controlled operational utilities

Do not add delete or clear actions unless separately designed and approved.

---

## 24. Data Context Acceptance Criteria

- Users can inspect the complete prefix mapping without leaving the editor UI.
- Users can see exactly which named graph is active.
- Users can see whether other named graphs contain data.
- Prefix drift between schema, JSON-LD context, and runtime is surfaced as an explicit warning.
- The panel remains read-only in baseline deployment.
- The panel does not affect save, edit, validation, or export flows.

---

## 25. Model Alignment Policy

The active model is SHACL-driven and aligned with current schema definitions.

Project policy:

- rely on the active SHACL schema as the single source of truth
- avoid hard-coded ontology assumptions in frontend behavior
- keep ontology-specific behavior isolated in schema parsing and mapping code
- ensure backend validation semantics stay consistent with extracted shape metadata

---

## 26. Documentation Policy

Documentation should distinguish three levels:

### User-facing entity labels

```text
Musical Work
Expression
Manifestation
Source
Person
Role
Place
Subject
Source Type
Holding Organization
```

### SHACL shape names

```text
rfdb:MusicalWorkShape
rfdb:ExpressionShape
rfdb:SourceShape
```

### RDF classes and predicates

```text
mm:MusicEntity
lrmoo:F2_Expression
source:Source
core:hasAgentRole
lrmoo:R4_embodies
cidoc:P51_has_former_or_current_owner
```

This separation keeps the UI understandable while preserving precise RDF semantics in validation and export.

---

## 27. Implementation Priorities

Recommended short-term priorities:

1. Keep the README concise and operational.
2. Keep this file as a deeper technical reference.
3. Stabilize the SHACL schema extraction format exposed by `/api/forms`.
4. Ensure every saved entity preserves stable `@id` and required `@type` values.
5. Define shape-role policy for helper bridges versus reusable external entities.
6. Add tests for class-targeted validation behavior.
7. Add tests for date datatype preservation.
8. Add tests for language-tagged literals and `sh:uniqueLang`.
9. Add tests for nested AgentRole editing and update preservation.
10. Add safe diagnostics before implementing any graph operations.
