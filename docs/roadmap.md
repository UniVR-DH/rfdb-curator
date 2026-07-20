# RFDB Curator — Roadmap

Planned and not-yet-shipped work, kept separate from the descriptions of current
behavior in [architecture.md](architecture.md). The largest planned effort is the
**Data Context Panel**; the shipped first milestone of it (the prefix metadata
endpoint) is documented in [architecture.md](architecture.md). For the live task list
see the root `TODO.md`.

---

## Planned Data Context Panel

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

## Prefixes Tab

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

---

## Named Graphs Tab

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

## Graph Metadata — Planned

Endpoint:

```text
GET /api/meta/graphs
```

Example response:

```json
{
  "activeGraph": "https://rosfeatr.eu/rdf/graph/",
  "graphs": [
    {
      "graph": "https://rosfeatr.eu/rdf/graph/",
      "tripleCount": 1234,
      "status": "active"
    }
  ]
}
```

Graph list should be computed through SPARQL over named graphs, including per-graph counts.

(The already-shipped `GET /api/meta/prefixes` endpoint is documented in
[architecture.md](architecture.md).)

---

## Planned Frontend Components for Data Context

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

## Data Context Rollout Phases

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

## Data Context Acceptance Criteria

- Users can inspect the complete prefix mapping without leaving the editor UI.
- Users can see exactly which named graph is active.
- Users can see whether other named graphs contain data.
- Prefix drift between schema, JSON-LD context, and runtime is surfaced as an explicit warning.
- The panel remains read-only in baseline deployment.
- The panel does not affect save, edit, validation, or export flows.

---

## Implementation Priorities

Recommended short-term priorities:

1. Keep the README concise and operational.
2. Keep the reference docs as a deeper technical reference.
3. Stabilize the SHACL schema extraction format exposed by `/api/forms`.
4. Ensure every saved entity preserves stable `@id` and required `@type` values.
5. Define shape-role policy for helper bridges versus reusable external entities.
6. Add tests for class-targeted validation behavior.
7. Add tests for date datatype preservation.
8. Add tests for language-tagged literals and `sh:uniqueLang`.
9. Add tests for nested AgentRole editing and update preservation.
10. Add safe diagnostics before implementing any graph operations.
