/**
 * Details panel for the selected node: its literal fields, its relations (both
 * directions, click to jump), and any external-authority links. Relation rows
 * resolve the neighbour's label from the shared node map so they read naturally.
 */
import { compactIri } from '../utils/prefixes.js'
import { kindColor, predicateLabel } from '../utils/types.js'

export default function Inspector({ node, edges, nodesById, onSelectNeighbor, onClose }) {
  if (!node) return null
  const rels = edges.filter((e) => e.source === node.id || e.target === node.id)
  const literals = node.details?.literals ?? []
  const externals = node.details?.externalLinks ?? []

  return (
    <aside className="inspector">
      <div className="inspector-header">
        <button className="inspector-close" onClick={onClose} aria-label="Close">
          ×
        </button>
        <span className="inspector-type" style={{ background: kindColor(node.kind) }}>
          {node.typeLabel}
        </span>
        <h3 className="inspector-title">{node.label}</h3>
        <div className="inspector-iri">{compactIri(node.id)}</div>
      </div>

      <div className="inspector-body">
        {node.loading && <p className="picker-loading">Loading…</p>}

        {literals.length > 0 && (
          <>
            <div className="inspector-section-title">Fields</div>
            {literals.map((lit, i) => (
              <div className="kv" key={`${lit.predicate}-${i}`}>
                <div className="k">
                  {compactIri(lit.predicate)}
                  {lit.language ? ` @${lit.language}` : ''}
                </div>
                <div className="v">{lit.value}</div>
              </div>
            ))}
          </>
        )}

        {rels.length > 0 && (
          <>
            <div className="inspector-section-title">Relations</div>
            {rels.map((e) => {
              const outgoing = e.source === node.id
              const otherId = outgoing ? e.target : e.source
              const other = nodesById[otherId]
              return (
                <div className="rel-row" key={e.id} onClick={() => onSelectNeighbor(otherId)}>
                  <span className="rel-dir">{outgoing ? '→' : '←'}</span>
                  <span className="rel-pred">{predicateLabel(e.predicate)}</span>
                  <span className="rel-target">{other?.label || compactIri(otherId)}</span>
                </div>
              )
            })}
          </>
        )}

        {externals.length > 0 && (
          <>
            <div className="inspector-section-title">External links</div>
            {externals.map((x, i) => (
              <div className="kv" key={`${x.predicate}-${i}`}>
                <div className="k">{compactIri(x.predicate)}</div>
                <div className="v">
                  <a href={x.target} target="_blank" rel="noreferrer">
                    {compactIri(x.target)}
                  </a>
                </div>
              </div>
            ))}
          </>
        )}

        {!node.expanded && !node.loading && (
          <p className="picker-empty">Click this node in the graph to load its relations.</p>
        )}
      </div>
    </aside>
  )
}
