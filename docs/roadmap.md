# RFDB Curator — Roadmap

Planned and not-yet-shipped work, kept separate from the descriptions of current
behavior in [architecture.md](architecture.md). For the live task list see the root
`TODO.md`.

---

## Data Context Panel

**Status: Phase 1 is shipped.** The read-only Data Context Panel
(`frontend/src/components/DataContextPanel.jsx`) is live, backed by the three
`/api/meta/*` endpoints (prefixes, graphs, files) documented in
[architecture.md](architecture.md). It surfaces the prefix map, the active and named
graphs with per-graph triple/subject/object/literal counts, digital-copy storage
stats, and advisory config warnings — all read-only, with no destructive graph
actions. The remaining phases below are enhancements on top of that baseline.

### Remaining enhancements

Prefixes:

- per-entry `source` attribution (`schema` / `jsonld-context` / `runtime`)
- explicit prefix-drift warnings when mappings differ between schema, JSON-LD context,
  and runtime configuration
- copy Turtle prefix declaration / copy namespace IRI, and search by prefix or
  namespace substring

Named graphs:

- richer per-graph status labels beyond the current active/count view

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
5. Define shape-role policy for helper bridges versus reusable standalone entities.
6. Add tests for class-targeted validation behavior.
7. Add tests for date datatype preservation.
8. Add tests for language-tagged literals and `sh:uniqueLang`.
9. Add tests for nested AgentRole editing and update preservation.
10. Add safe diagnostics before implementing any graph operations.
