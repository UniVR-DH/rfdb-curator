/**
 * Custom React Flow node for one RDF entity.
 *
 * Reads its display fields from `data` (built in App.jsx via GraphView): the
 * coloured type header, the label, and — while the node is still collapsed — an
 * explicit "Expand" button that loads its links (clicking the node body only
 * selects it). Top/bottom handles let React Flow route relation edges.
 *
 * `data.isBridge` (a helper-bridge shape, per the schema's shape-role policy —
 * see `isBridgeType` in utils/types.js) renders a much smaller badge instead:
 * these entities have no `rdfs:label`, so the full card's own label row would
 * only ever show a meaningless CURIE, and the card's bulk is wasted on a node
 * whose sole job is to connect two others.
 */
import { Handle, Position } from 'reactflow'
import { kindColor } from '../utils/types.js'

function BridgeBadge({ id, data }) {
  const totalLabel =
    typeof data.edgeCount === 'number' ? `${data.edgeCount}${data.truncated ? '+' : ''}` : null
  const pendingLabel =
    typeof data.pendingCount === 'number' ? `${data.pendingCount}${data.truncated ? '+' : ''}` : null
  return (
    <div className={`entity-node entity-node--bridge${data.selected ? ' selected' : ''}`}>
      <Handle type="target" position={Position.Top} />
      <div className="entity-node__bridge" style={{ background: kindColor(data.kind) }}>
        <span className="entity-node__bridge-label">{data.typeLabel}</span>
        {data.loading && <span className="entity-node__bridge-hint">…</span>}
        {!data.loading && !data.expanded && data.pendingCount > 0 && (
          <button
            type="button"
            className="entity-node__bridge-expand nodrag"
            onClick={() => data.onExpand?.(id)}
            title={`Expand ${pendingLabel} link${data.pendingCount === 1 ? '' : 's'}`}
          >
            +{pendingLabel}
          </button>
        )}
        {data.expanded && totalLabel && (
          <span
            className="entity-node__bridge-hint"
            title={`All ${totalLabel} link${data.edgeCount === 1 ? '' : 's'} shown`}
          >
            ✓ {totalLabel}
          </span>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
}

// The bottom banner covers every state a card can be in — no links, a button
// to reveal N pending ones, or (whether it got there by being expanded itself
// or by having nothing left to reveal) confirmation that all its links are
// shown. One element, one place, regardless of how the card got there.
function footer(id, data) {
  if (data.loading) return null
  if (data.edgeCount === 0) return <div className="entity-node__nolinks">No links</div>
  if (data.edgeCount == null) {
    if (data.expanded) return null
    return (
      <button type="button" className="entity-node__expand nodrag" onClick={() => data.onExpand?.(id)}>
        Expand
      </button>
    )
  }
  if (!data.expanded && data.pendingCount > 0) {
    return (
      <button type="button" className="entity-node__expand nodrag" onClick={() => data.onExpand?.(id)}>
        {data.pendingCount}
        {data.truncated ? '+' : ''} {data.pendingCount === 1 ? 'link' : 'links'}
      </button>
    )
  }
  return <div className="entity-node__nolinks">All links shown</div>
}

export default function EntityNode({ id, data }) {
  if (data.isBridge) return <BridgeBadge id={id} data={data} />

  return (
    <div className={`entity-node${data.selected ? ' selected' : ''}`}>
      <Handle type="target" position={Position.Top} />
      <div className="entity-node__type" style={{ background: kindColor(data.kind) }}>
        {data.typeLabel}
      </div>
      <div className="entity-node__body">
        <div className="entity-node__label">{data.label}</div>
        {data.loading && <div className="entity-node__hint">loading…</div>}
      </div>
      {footer(id, data)}
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
}
