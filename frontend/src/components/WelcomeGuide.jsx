/**
 * First-time curator welcome guide (modal overlay).
 *
 * Explains the WEMI / LRMoo layering the whole schema is built on and the order in
 * which a curator should insert records. Purely informational — never calls the API,
 * so it is safe under the read-only editor flag.
 *
 * Props:
 *   open     {boolean}   - whether the overlay is visible
 *   onClose  {function}  - called on backdrop click, Escape, or the primary button
 *
 * State (auto-open on first visit, re-openable via a Help button) lives in App.jsx.
 */
import { useEffect, useRef } from 'react'
import Icon from './Icon.jsx'
import './WelcomeGuide.css'

// The WEMI spine (LRMoo classes), source of truth: schema/schema.ttl.
// Kept in one array so the diagram and the step list can never drift apart.
const WEMI_STEPS = [
  {
    n: 1,
    tag: 'Start here',
    title: 'Supporting entities',
    detail:
      'Create the records other forms point at — Place, Person, Subject, Organization, and document Type. They populate the dropdowns used in later steps.',
  },
  {
    n: 2,
    tag: 'F2 · Expression',
    title: 'Expression',
    detail:
      'A specific intellectual realization of the Work — e.g. a Libretto is an Expression that is part of an opera. It only needs a label (plus optional roles), so create it before the Manifestation.',
  },
  {
    n: 3,
    tag: 'F3 · Manifestation',
    title: 'Manifestation',
    detail:
      'The product type — all physical copies of one published edition. It must embody exactly one Expression (lrmoo:R4_embodies), so that Expression has to exist first.',
  },
  {
    n: 4,
    tag: 'F5 · Item',
    title: 'Source',
    detail:
      'A physical copy of a printed work held by a library or archive; it exemplifies a Manifestation (lrmoo:R7_exemplifies) and requires a document Type and a holding Organization. One Manifestation can be exemplified by many Sources.',
  },
  {
    n: 5,
    tag: 'F1 · Work',
    title: 'Musical Work',
    detail:
      'The intellectual creation itself (an opera or composition). Create or complete it last and link it to its component Expressions via cidoc:P148_has_component. To record a staging, add a Performance (F31), which links to two levels: the Work it performed (lrmoo:R80_performed) and the Manifestation used at / made for it (cidoc:P16_used_specific_object / P19_was_intended_use_of).',
  },
]

/**
 * Inline SVG of the WEMI chain — no charting dependency.
 *
 * Arrows follow the *actual SHACL predicate direction* (subject → object, per each
 * shape's sh:path in schema/schema.ttl), which is deliberately NOT a single top-down
 * flow: the Work points down to its Expression, but a Manifestation points UP to its
 * Expression and a Source UP to its Manifestation. Performance links to two levels.
 */
function WemiDiagram() {
  const box = (x, y, f, label) => (
    <g>
      <rect x={x} y={y} width="140" height="48" rx="8" className="guide-node" />
      <text x={x + 12} y={y + 20} className="guide-node-tag">
        {f}
      </text>
      <text x={x + 12} y={y + 38} className="guide-node-label">
        {label}
      </text>
    </g>
  )
  // Predicate label: a small prefix line, then the full predicate name(s) below in
  // bigger, bold, lighter type. Pass one name for a single predicate, or several for
  // an edge that stands for more than one (e.g. Performance's P16 / P19).
  const edgeLabel = (x, y, prefix, ...names) => (
    <text x={x} y={y} className="guide-edge-label">
      <tspan x={x} dy="0">
        {prefix}
      </tspan>
      {names.map((name) => (
        <tspan key={name} x={x} dy="12" className="guide-edge-name">
          {name}
        </tspan>
      ))}
    </text>
  )
  return (
    <svg
      className="guide-diagram"
      viewBox="0 0 400 416"
      role="img"
      aria-label="WEMI model with SHACL predicate directions. Musical Work (F1) points down to Expression (F2) via cidoc P148 has_component. Manifestation (F3) points up to Expression via lrmoo R4 embodies. Source/Item (F5) points up to Manifestation via lrmoo R7 exemplifies. Performance (F31) links to two levels: to the Work via lrmoo R80 performed, and to the Manifestation via cidoc P16 used_specific_object or P19 was_intended_use_of."
    >
      <defs>
        <marker
          id="guide-arrow"
          viewBox="0 0 10 10"
          refX="8"
          refY="5"
          markerWidth="7"
          markerHeight="7"
          orient="auto-start-reverse"
        >
          <path d="M0,0 L10,5 L0,10 z" className="guide-arrowhead" />
        </marker>
      </defs>

      {/* Spine edges — direction matches each shape's sh:path (subject → object). */}
      {/* Work → Expression (down): cidoc:P148_has_component */}
      <line x1="78" y1="56" x2="78" y2="128" className="guide-edge" markerEnd="url(#guide-arrow)" />
      {edgeLabel(86, 80, 'cidoc:', 'P148_has_component')}
      {/* Manifestation → Expression (up): lrmoo:R4_embodies */}
      <line x1="78" y1="248" x2="78" y2="176" className="guide-edge" markerEnd="url(#guide-arrow)" />
      {edgeLabel(86, 200, 'lrmoo:', 'R4_embodies')}
      {/* Source → Manifestation (up): lrmoo:R7_exemplifies */}
      <line x1="78" y1="368" x2="78" y2="296" className="guide-edge" markerEnd="url(#guide-arrow)" />
      {edgeLabel(86, 320, 'lrmoo:', 'R7_exemplifies')}

      {/* Performance → Work (up): lrmoo:R80_performed — right-angle connector */}
      <polyline
        points="318,176 318,32 148,32"
        className="guide-edge guide-edge--branch"
        fill="none"
        markerEnd="url(#guide-arrow)"
      />
      {edgeLabel(180, 14, 'lrmoo:', 'R80_performed')}
      {/* Performance → Manifestation (down): cidoc:P16 / P19 — right-angle connector */}
      <polyline
        points="318,224 318,272 148,272"
        className="guide-edge guide-edge--branch"
        fill="none"
        markerEnd="url(#guide-arrow)"
      />
      {edgeLabel(172, 280, 'cidoc:', 'P16_used_specific_object', 'P19_was_intended_use_of')}

      {box(8, 8, 'F1 · Work', 'Musical Work')}
      {box(8, 128, 'F2 · Expression', 'Expression')}
      {box(8, 248, 'F3 · Manifestation', 'Manifestation')}
      {box(8, 368, 'F5 · Item', 'Source / Item')}
      {box(248, 176, 'F31 · Performance', 'Performance')}
    </svg>
  )
}

export default function WelcomeGuide({ open, onClose }) {
  const closeRef = useRef(null)

  // Escape closes; focus the close button when the dialog opens.
  useEffect(() => {
    if (!open) return
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    closeRef.current?.focus()
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="guide-backdrop" onClick={onClose}>
      <div
        className="guide-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="guide-title"
        // Clicks inside the dialog must not bubble to the backdrop (which closes it).
        onClick={(e) => e.stopPropagation()}
      >
        <button
          ref={closeRef}
          className="guide-close"
          onClick={onClose}
          aria-label="Close guide"
        >
          <Icon name="X" size={18} />
        </button>

        <header className="guide-header">
          <p className="guide-eyebrow">First-time curator guide</p>
          <h2 id="guide-title" className="guide-title">
            Guide to the Database Structure and Record Insertion
          </h2>
          <p className="guide-intro">
            Rossiysky Featr follows the <strong>WEMI</strong> model (<a target="_blank" rel="noopener noreferrer" href="https://cidoc-crm.org/lrmoo/short-intro-frbroo">LRMoo</a>).
            For a musical work, the flow is from the record describing the abstract idea down to the physical copy.
            The insertion process starts by recording all auxiliary entities (Place, Person, Subject, Organization, and document Type).
            Then, working from the document in hand, create the Expression (e.g. the libretto text),
            then its Manifestation (the published edition, which embodies that Expression),
            and then each Source (a physical copy held by a library, which exemplifies the Manifestation —
            one Manifestation can have many Sources).
            Finally, update the Musical Work record with the links to the Expressions you just created.
          </p>
        </header>

        <div className="guide-body">
          <div className="guide-diagram-wrap">
            <WemiDiagram />
            <p className="guide-diagram-note">
              The chain is not one-directional: a Manifestation points
              <em> up</em> to its Expression and a Source <em>up</em> to its Manifestation.
              Performance links to two levels — the Work and the Manifestation.
              Supporting entities (Place, Person → Agent Role, Subject) feed these forms via
              their dropdowns.
            </p>
          </div>

          <ol className="guide-steps">
            {WEMI_STEPS.map((s) => (
              <li key={s.n} className="guide-step">
                <span className="guide-step-num">{s.n}</span>
                <div>
                  <p className="guide-step-title">
                    {s.title} <span className="guide-step-tag">{s.tag}</span>
                  </p>
                  <p className="guide-step-detail">{s.detail}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>

        <footer className="guide-footer">
          <button className="btn btn-primary" onClick={onClose}>
            Got it — start curating
          </button>
        </footer>
      </div>
    </div>
  )
}
