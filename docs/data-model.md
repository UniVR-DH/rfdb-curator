# RFDB Curator — Data Model

This is the RDF/SHACL modeling reference for `rfdb-curator`: the prefix map, the
ontologies and vocabularies in use, per-shape field definitions, the WEMI layering,
the bridge-node pattern, and the policies governing literals, language tags, dates,
and IRIs.

The active SHACL schema at `schema/schema.ttl` is the single source of truth. Where
this document and the schema diverge, the schema (and the implementation) take
precedence. For how these shapes become forms and how validation runs, see
[architecture.md](architecture.md).

---

## Current Prefix Map

The active schema currently declares these prefixes:

```turtle
@prefix cidoc:   <http://www.cidoc-crm.org/cidoc-crm/> .
@prefix core:    <https://w3id.org/polifonia/ontology/core/> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix foaf:    <http://xmlns.com/foaf/0.1/> .
@prefix glottolog: <http://glottolog.org/resource/languoid/id/> .
@prefix lrmoo:   <http://iflastandards.info/ns/lrm/lrmoo/> .
@prefix mm:      <https://w3id.org/polifonia/ontology/music-meta/> .
@prefix owl:     <http://www.w3.org/2002/07/owl#> .
@prefix prism:   <http://prismstandard.org/namespaces/basic/2.0/> .
@prefix rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix rfdb:    <https://rosfeatr.eu/rdf/data/> .
@prefix rfdbs:   <https://rosfeatr.eu/rdf/schema/> .
@prefix schema:  <http://schema.org/> .
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

## Ontologies and Vocabularies Used

### RFDB Namespace

```text
rfdb: <https://rosfeatr.eu/rdf/data/>
rfdbs:   <https://rosfeatr.eu/rdf/schema/> .
```

`rfdb:` is used for local RFDB data resources; `rfdbs:` is used for SHACL shapes.

Examples:

```text
rfdbs:MusicalWorkShape
rfdbs:ExpressionShape
rfdbs:SourceShape
rfdbs:PlaceShape
rfdb:PrintedLibretto
rfdb:SanPietroburgo
```

The current schema does not define custom `rfdb:` predicates.

---

### LRMoo

```text
lrmoo: <http://iflastandards.info/ns/lrm/lrmoo/>
```

Classes used:

```text
lrmoo:F1_Work
lrmoo:F2_Expression
lrmoo:F3_Manifestation
lrmoo:F5_Item
lrmoo:F31_Performance
```

Properties used:

```text
lrmoo:R4_embodies
lrmoo:R7_exemplifies
lrmoo:R80_performed
```

Usage:

- Musical Works align with `lrmoo:F1_Work`.
- Expressions target `lrmoo:F2_Expression`.
- Manifestations target `lrmoo:F3_Manifestation`.
- Sources/Items target `lrmoo:F5_Item`.
- Manifestations embody Expressions through `lrmoo:R4_embodies`.
- Sources/Items exemplify Manifestations through `lrmoo:R7_exemplifies`.
- Performances target `lrmoo:F31_Performance`.
- Performances reference the performed Work through `lrmoo:R80_performed`.

---

### CIDOC CRM

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
cidoc:P138i_has_representation
cidoc:P19_was_intended_use_of
cidoc:P16_used_specific_object
```

Usage:

- Subjects are modeled as `cidoc:E89_Propositional_Object`.
- Musical Works can point to subjects through `cidoc:P129_is_about`.
- Sources point to holding organizations through `cidoc:P51_has_former_or_current_owner`.
- Sources point to their digital copies through `cidoc:P138i_has_representation`.
- Performances link to manifestations through `cidoc:P19_was_intended_use_of` (strong claim) and `cidoc:P16_used_specific_object` (weak claim).

---

### Polifonia Core

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
cidoc:P148i_is_component_of
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
- `cidoc:P148i_is_component_of` connects an Expression up to its parent Musical Work (libretto, score, etc.); this is the canonical Work↔Expression link, defined in `ExpressionShape` (inverse of `cidoc:P148_has_component`, giving one child→parent direction across the WEMI chain).
- `core:hasAgentRole` connects Works or Expressions to AgentRole records.
- `core:hasAgent` and `core:hasRole` define AgentRole internals.
- `core:hasPlace` links Sources and Organizations to Places.
- `core:hasType` classifies Sources.
- `core:text` stores title-page transcription.

---

### Polifonia Music Meta

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

### Polifonia Source

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

### Dublin Core Terms

```text
dcterms: <http://purl.org/dc/terms/>
```

Class used:

```text
dcterms:LinguisticSystem
```

Properties used:

```text
dcterms:date
dcterms:language
dcterms:identifier
dcterms:contributor
```

Usage:

- `dcterms:LinguisticSystem` is the target class for controlled-vocabulary Language records (from Glottolog).
- `dcterms:date` is used for Work dates.
- `dcterms:language` is used for Source/Item language IRIs.
- `dcterms:identifier` is used for shelfmarks or call numbers.
- `dcterms:contributor` records the donor/provider of a Source's digital copy.

The schema suggests Glottolog IRIs for language values, for example:

```text
https://glottolog.org/resource/languoid/id/russ1263
```

---

### PRISM

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

### FOAF

```text
foaf: <http://xmlns.com/foaf/0.1/>
```

Classes used:

```text
foaf:Agent
foaf:Person
foaf:Organization
```

Property used:

```text
foaf:name
```

Usage:

- `foaf:Agent` is the Contributor target class; a Contributor is further constrained to `foaf:Person` or `foaf:Organization`.
- `foaf:name` holds the contributor's full name.
- FOAF is used deliberately in place of `core:Person`/`core:Organization` to keep donor/provenance identities separate from creative/editorial agents.

---

### Schema.org

```text
schema: <http://schema.org/>
```

Class used:

```text
schema:DigitalDocument
```

Properties used:

```text
schema:name
schema:encodingFormat
schema:contentUrl
schema:contentSize
schema:sha256
schema:numberOfPages
```

Usage:

- `schema:DigitalDocument` is the Digital Copy target class (a PDF scan of a Source).
- `schema:name`, `schema:encodingFormat`, `schema:contentUrl`, `schema:contentSize`, `schema:sha256`, and `schema:numberOfPages` carry the digital copy's filename, MIME type, download path, byte size, checksum, and page count.

---

### Glottolog

```text
glottolog: <http://glottolog.org/resource/languoid/id/>
```

Usage:

- Provides the language-identifier IRIs used as `dcterms:language` values on Sources/Items (e.g. `glottolog:russ1263`), seeded into `dcterms:LinguisticSystem` Language records.

---

### RDF, RDFS, OWL, SKOS, WDT, XSD

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

SKOS properties:

```text
skos:altLabel
skos:prefLabel
```

Wikidata direct property:

```text
wdt:P214
```

XSD datatypes:

```text
xsd:string
xsd:integer
xsd:anyURI
xsd:date
xsd:gYear
xsd:gYearMonth
```

---

## Shape-Specific Notes

### Place

Shape:

```text
rfdbs:PlaceShape
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

### Subject

Shape:

```text
rfdbs:SubjectShape
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

### Source Type

Shape:

```text
rfdbs:SourceTypeShape
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

### Language

Shape:

```text
rfdbs:LanguageShape
```

Target class:

```text
dcterms:LinguisticSystem
```

Main fields:

- `rdfs:label`: required, at least one language-tagged label (`rdf:langString`)
- `skos:prefLabel`: repeatable language-tagged preferred labels (`rdf:langString`)

Controlled-vocabulary reference data (browse and select only), seeded from Glottolog. Language records are typically locked against create/update/delete via `READ_ONLY_SHAPES`.

---

### Musical Work

Shape:

```text
rfdbs:MusicalWorkShape
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

### Expression

Shape:

```text
rfdbs:ExpressionShape
```

Target class:

```text
lrmoo:F2_Expression
```

Main fields:

- `rdfs:label`: required, exactly one
- `skos:altLabel`: repeatable alternate labels
- `cidoc:P148i_is_component_of`: optional, at most one link up to the parent Musical Work (inverse of `cidoc:P148_has_component`)
- `core:hasAgentRole`: repeatable links to AgentRole records
- `rdfs:comment`: optional, at most one plain string

---

### Manifestation

Shape:

```text
rfdbs:ManifestationShape
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

### Source / Item

Shape:

```text
rfdbs:SourceShape
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
- `dcterms:contributor`: optional, at most one link to a Contributor (donor/provider of the digital copy, when distinct from the physical owner)
- `cidoc:P138i_has_representation`: repeatable links to Digital Copy records (managed via the file-upload panel, not the generic form)

---

### Digital Copy

Shape:

```text
rfdbs:DigitalCopyShape
```

Target class:

```text
schema:DigitalDocument
```

Main fields:

- `schema:name`: required, exactly one plain string — original filename of the uploaded PDF
- `schema:encodingFormat`: required, exactly one, fixed to `application/pdf` (via `sh:hasValue`)
- `schema:contentUrl`: required, exactly one `xsd:anyURI` — stable backend-relative download path
- `schema:contentSize`: required, exactly one `xsd:integer` — file size in bytes
- `schema:sha256`: required, exactly one `xsd:string` — SHA-256 checksum for integrity and dedup
- `schema:numberOfPages`: optional, at most one `xsd:integer` — page count from pypdf

This is a helper/bridge shape: it has no `rdfs:label` property, so it is edited inline rather than as a standalone record. It is referenced from `rfdbs:SourceShape` via `sh:node` on `cidoc:P138i_has_representation`, and its fields are machine-filled by the upload flow. For how the PDF bytes are staged and stored, see the [Storage and Runtime Stack](architecture.md#storage-and-runtime-stack) and [File Storage Metadata](architecture.md#file-storage-metadata) sections of architecture.md.

---

### Performance

Shape:

```text
rfdbs:PerformanceShape
```

Target class:

```text
lrmoo:F31_Performance
```

Main fields:

- `rdfs:label`: required, exactly one
- `lrmoo:R80_performed`: required, one or more links to the performed Musical Work
- `dcterms:date`: optional, at most one date (`xsd:date`, `xsd:gYear`, or `xsd:gYearMonth`)
- `core:hasPlace`: optional, at most one Place (performance venue)
- `core:hasAgentRole`: repeatable links to Agent Role records (conductor, director, cast, etc.)
- `cidoc:P19_was_intended_use_of`: repeatable links to Manifestation records — STRONG claim, the manifestation was created specifically for this performance
- `cidoc:P16_used_specific_object`: repeatable links to Manifestation records — WEAK claim, the manifestation was merely present or used at this performance
- `owl:sameAs`: repeatable external event identifiers (e.g. Corago ID)

The two Manifestation links encode different evidentiary strength and must be kept distinct; see [Performance and Contributor Modeling](#performance-and-contributor-modeling) for the P19-vs-P16 rationale.

---

### Person

Shape:

```text
rfdbs:PersonShape
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

### Role

Shape:

```text
rfdbs:RoleShape
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

### Agent Role

Shape:

```text
rfdbs:AgentRoleShape
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

### Holding Organization

Shape:

```text
rfdbs:HoldingOrganizationShape
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

### Contributor

Shape:

```text
rfdbs:ContributorShape
```

Target class:

```text
foaf:Agent
```

Main fields:

- `rdfs:label`: required, exactly one
- `foaf:name`: required, exactly one

The shape is constrained at the shape level by `sh:or ( [ sh:class foaf:Person ] [ sh:class foaf:Organization ] )`, which surfaces a `typeOptions` dropdown in the UI so the curator picks the concrete class at creation time. It deliberately uses `foaf:*` rather than `core:*` to keep donor/provenance identities structurally separate from composers, librettists, and holding institutions; see [Performance and Contributor Modeling](#performance-and-contributor-modeling) for the rationale.

---

## Linked-Entity Fields

Important linked fields and expected UI behavior:

```text
cidoc:P148i_is_component_of
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

dcterms:language
    Source / Item → Language

dcterms:contributor
    Source / Item → Contributor

cidoc:P138i_has_representation
    Source / Item → Digital Copy
```

The frontend should support:

- lookup by label
- display of compact IRI
- selection of existing records
- optional creation of linked records, depending on workflow
- preservation of exact linked IRIs in submitted JSON-LD

---

## Literal Field Handling

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

## Language-Tagged Values

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

## Date Precision

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

## IRI Policy

Every persisted RDF resource must have a stable subject IRI.

Use the two prefixes declared in the schema above: `rfdb:` and `rfdbs:`.

Requirements:

- existing IRIs must not be silently changed
- new IRIs should follow a consistent generation policy
- helper/bridge IRIs should be preserved during updates
- full IRIs and prefixed IRIs should both be accepted where appropriate
- invalid IRIs should be rejected before persistence

---

## Class-Targeted Shape Nuance

Many shapes use `sh:targetClass`.

This means validation constraints apply only when the node declares the corresponding RDF class.

Important consequence:

- if a JSON-LD payload omits required `@type` values, some shape constraints may not run
- bridge/helper nodes should always include explicit `@type` values when the schema relies on class-targeted validation

For example, AgentRole payloads should include `core:AgentRole` among their `@type` values.

For the validation-graph merge behavior that makes incremental top-down editing work,
see [architecture.md](architecture.md).

---

## Performance and Contributor Modeling

Two modeling choices in `schema/schema.ttl` are intentional and should be preserved unless there is an explicit migration plan:

- Performance links use both `cidoc:P19_was_intended_use_of` (strong: the manifestation was made for this performance) and `cidoc:P16_used_specific_object` (weak: the manifestation was merely present or used there). Do not merge these into one property; they encode different evidentiary strength and exact CIDOC-CRM domain/range fit.
- Source donor/provenance uses `dcterms:contributor`, not `cidoc:P51_has_former_or_current_owner` and not `core:hasAgentRole`. This keeps digital-copy contributor attribution separate from legal ownership and from the open Role vocabulary used for creative/performance attribution. CIDOC-CRM has no simple donor shortcut outside the full acquisition event, so `dcterms:contributor` is the chosen reuse point.

Contributor nodes are constrained via `rfdbs:ContributorShape` to `foaf:Person` or `foaf:Organization`. This is a schema-level guardrail against accidental reuse of `core:Person`/`core:Organization` entities in donor/provenance assertions.

---

## Model Alignment Policy

The active model is SHACL-driven and aligned with current schema definitions.

Project policy:

- rely on the active SHACL schema as the single source of truth
- avoid hard-coded ontology assumptions in frontend behavior
- keep ontology-specific behavior isolated in schema parsing and mapping code
- ensure backend validation semantics stay consistent with extracted shape metadata

---

## Naming Conventions Across Layers

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
rfdbs:MusicalWorkShape
rfdbs:ExpressionShape
rfdbs:SourceShape
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
