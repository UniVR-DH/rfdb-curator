# RFDB Curator — Data Model

This document records the **design principles and modeling decisions** behind the RFDB
data model: which vocabularies are used and for what, how the WEMI layering and the
bridge-node pattern work, and the literal/language/date/IRI policies that the SHACL
schema alone cannot explain.

It is **not** a per-shape field reference. The active schema at
[`schema/schema.ttl`](../schema/schema.ttl) is the single source of truth for record
types, fields, cardinalities, datatypes, and relations — do not duplicate that here, or
this file will need editing on every schema tweak. To answer "what fields does shape X
have?", read the schema or query the live metadata endpoints (below). For how shapes
become forms and how validation runs, see [architecture.md](architecture.md).

---

## Where to look for the mechanical detail

| Question | Source of truth |
|---|---|
| Which shapes exist, their fields, cardinalities, datatypes, relations | [`schema/schema.ttl`](../schema/schema.ttl) |
| The same, resolved into form/field descriptors | `GET /api/shapes`, `GET /api/forms?shapeId=...` |
| The active prefix → namespace map | schema `@prefix` declarations, [`backend/core/prefixes.py`](../backend/core/prefixes.py), `GET /api/meta/prefixes` |

Because everything downstream (forms, validation, autocomplete, export) is derived from
the schema at runtime, the schema is the only place a field or prefix is *defined*. This
document explains the reasoning; the schema holds the facts.

---

## Vocabularies used, and for what

The model reuses established vocabularies rather than minting local terms wherever a
suitable one exists. Each is chosen for a specific category of thing; the "used for"
column is the durable contract, not an exhaustive property list (query `/api/meta/prefixes`
for the current namespace bindings).

| Prefix | Vocabulary | Used for |
|---|---|---|
| `rfdb:` / `rfdbs:` | RFDB local namespaces | `rfdb:` for instance data IRIs, `rfdbs:` for SHACL shapes. The schema defines **no custom predicates** — all properties are reused from the vocabularies below. |
| `lrmoo:` | [LRMoo](https://cidoc-crm.org/lrmoo/) | The WEMI spine: Work / Expression / Manifestation / Item classes and the links between levels (embodies, exemplifies), plus Performance. |
| `cidoc:` | [CIDOC CRM](https://cidoc-crm.org/) | Cultural-heritage relations LRMoo does not cover: subjects, ownership/custody, the Work↔Expression component link, and performance-to-manifestation evidence. |
| `core:` | [Polifonia Core](https://github.com/polifonia-project/core-ontology) | People, roles, places, organizations, source/document types, and the Agent-Role bridge that binds an agent to a role. |
| `mm:` | [Polifonia Music Meta](https://github.com/polifonia-project/music-meta-ontology) | The music-domain typing of a Musical Work (`mm:MusicEntity`). |
| `source:` | [Polifonia Source](https://github.com/polifonia-project/source-ontology) | The Source/Item as a physical or documentary copy held by an institution. |
| `dcterms:` | [Dublin Core Terms](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) | Dates, language references, identifiers (shelfmarks), the Language controlled-vocabulary class, and the digital-copy contributor/donor link. |
| `prism:` | [PRISM](https://www.w3.org/submissions/prism/) | Publication dates for Manifestations and Sources. |
| `foaf:` | [FOAF](http://xmlns.com/foaf/spec/) | Donor/provenance agents (Contributor), kept deliberately distinct from `core:` creative agents — see [Intentional modeling decisions](#intentional-modeling-decisions). |
| `schema:` | [Schema.org](https://schema.org/) | Digital-copy (PDF scan) metadata: filename, MIME type, download URL, byte size, checksum, page count. |
| `glottolog:` | [Glottolog](https://glottolog.org/) | Stable language-identifier IRIs seeded as the Language controlled vocabulary. |
| `skos:` | [SKOS](https://www.w3.org/TR/skos-reference/) | Alternate and preferred labels. |
| `owl:` / `wdt:` / `rdfs:` | OWL / [Wikidata](https://www.wikidata.org/) direct props / RDFS | External authority links (`owl:sameAs`, `wdt:P214` VIAF), `rdfs:seeAlso` references, and core `rdfs:label`/`rdfs:comment` annotations. |
| `rdf:` / `xsd:` / `sh:` | RDF / XSD / [SHACL](https://www.w3.org/TR/shacl12-core/) | Typing, datatypes, and the shape language itself. |

---

## WEMI layering and link direction

The core records follow a layered **Work → Expression → Manifestation → Item** (WEMI)
structure, each level more concrete than the one above:

- **Musical Work** — the abstract work.
- **Expression** — an intellectual realization (e.g. a libretto).
- **Manifestation** — an edition or product type.
- **Source / Item** — a specific physical or documentary copy.

**Design decision — links point child → parent.** Every WEMI link is asserted on the
more concrete record and points up to its parent (Expression → Work via
`cidoc:P148i_is_component_of`, Manifestation → Expression via `lrmoo:R4_embodies`,
Item → Manifestation via `lrmoo:R7_exemplifies`). The practical consequence is
**editorial order: create parents before children**, because a child's form needs an
existing parent to reference. This one-directional convention keeps the graph acyclic
and the create/edit flow predictable.

---

## Standalone entities vs. helper/bridge nodes

Shapes fall into two roles, and the distinction is **derived from the schema, never
hardcoded per class**:

- **Standalone entity** — a shape that declares an `rdfs:label` property. It has its own
  identity and lifecycle and is created/searched as a top-level record (Work, Person,
  Place, Organization, …).
- **Helper/bridge node** — a shape with no `rdfs:label`. It only makes sense inline as
  part of a parent (e.g. `AgentRole`, which binds a Person to a Role). The editor renders
  these inline and blocks top-level editing.

The canonical bridge is **Agent Role**: contributor attribution (composer, librettist,
conductor, …) is not a direct property but a small `core:AgentRole` node linking a Person
to a Role, attached to a Work/Expression/Performance via `core:hasAgentRole`. This lets
one person hold different roles across records without collapsing identity into role.

See [architecture.md](architecture.md#helperbridge-shape-classification) for how this
classification drives the UI.

---

## Class-targeted validation requires explicit `@type`

Shapes use `sh:targetClass`, so a shape's constraints only run against a node that
declares the matching RDF class. **Payloads must therefore carry explicit `@type`
values** — most importantly bridge nodes, which the schema validates by class (an
`AgentRole` payload must include `core:AgentRole` in its `@type`). Omitting `@type` can
silently skip constraints.

For the validation-graph merge that makes incremental top-down editing work despite
class-targeting, see [architecture.md](architecture.md).

---

## Controlled vocabularies and reference data

Some records are reference data curators browse and select rather than author:

- **Language** records target `dcterms:LinguisticSystem` and are seeded from Glottolog
  (e.g. `glottolog:russ1263`). They are normally locked against create/update/delete via
  `READ_ONLY_SHAPES` — they are external reference data, not editorial content.
- **Role** and **Source Type** are typically curated as small controlled sets
  (composer, librettist, translator; libretto, score, …), though the schema does not lock
  them by default.

Seeding sources and reset behavior are documented in the
[deployment guide](deployment.md#data-seeding).

---

## Literal, language-tag, and date policies

These are **principles the UI and export must honor**; the exact per-field datatype for
any property lives in the schema.

- **Literal kinds are distinguished, not flattened.** A field is one of: plain string,
  language-tagged string (`rdf:langString`), full date, year-only date, year-month date,
  or IRI. The editor renders and validates each accordingly.
- **Language tags are first-class.** Where a field is `rdf:langString`, the tag is
  entered, validated, preserved through JSON-LD and RDF export, and — where the schema
  sets `sh:uniqueLang true` — enforced as unique per language.
- **Date precision is preserved.** The schema permits `xsd:date`, `xsd:gYear`, and
  `xsd:gYearMonth`. A year-only value must **not** be silently promoted to a full date;
  the curator's chosen precision is the datum.

---

## IRI policy

Every persisted resource has a stable subject IRI in the `rfdb:` (data) or `rfdbs:`
(shape) namespace. The rules:

- existing IRIs are never silently changed;
- new IRIs follow a consistent generation policy (helper/bridge IRIs are regular named
  nodes, not blank nodes, so they survive updates);
- both full and prefixed IRIs are accepted on input;
- invalid IRIs are rejected before persistence.

---

## Intentional modeling decisions

These choices in `schema/schema.ttl` are deliberate and should be preserved unless there
is an explicit migration plan — they encode semantics a reviewer might otherwise "simplify"
away:

1. **Performance → Manifestation uses two distinct properties, by evidentiary strength.**
   `cidoc:P19_was_intended_use_of` is the *strong* claim (the manifestation was created
   for this performance); `cidoc:P16_used_specific_object` is the *weak* claim (it was
   merely present or used). Do not merge them — they carry different evidence and
   different CIDOC-CRM domain/range fit.

2. **Digital-copy donors use `dcterms:contributor`, not ownership or agent-role.**
   This keeps donor/provider attribution separate from legal ownership
   (`cidoc:P51_has_former_or_current_owner`) and from the open creative-role vocabulary
   (`core:hasAgentRole`). CIDOC-CRM offers no simple donor shortcut short of a full
   acquisition event, so `dcterms:contributor` is the chosen reuse point.

3. **Contributors are `foaf:*`, not `core:*`.** `rfdbs:ContributorShape` constrains a
   contributor to `foaf:Person` or `foaf:Organization` (surfaced as a type-selection
   dropdown). This is a schema-level guardrail keeping donor/provenance identities
   structurally separate from composers, librettists, and holding institutions.

---

## Naming across layers

Keep three naming levels distinct in code, UI, and docs — conflating them loses either
readability or RDF precision:

- **User-facing labels** — "Musical Work", "Source", "Holding Organization".
- **SHACL shape names** — `rfdbs:MusicalWorkShape`, `rfdbs:SourceShape`.
- **RDF classes and predicates** — `mm:MusicEntity`, `lrmoo:F2_Expression`,
  `core:hasAgentRole`.

---

## Model alignment policy

The model is SHACL-driven. Consequently:

- the active SHACL schema is the single source of truth;
- the frontend makes no hard-coded ontology assumptions;
- ontology-specific behavior stays isolated in schema parsing and mapping code;
- backend validation semantics stay consistent with the extracted shape metadata.
