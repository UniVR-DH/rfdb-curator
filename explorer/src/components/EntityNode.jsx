/**
 * Custom React Flow node for one RDF entity.
 *
 * Reads its display fields from `data` (built in App.jsx via GraphView): the
 * coloured type header, the label, and — while the node is still collapsed — an
 * explicit "Expand" button that loads its links (clicking the node body only
 * selects it). Top/bottom handles let React Flow route relation edges.
 */
import { Handle, Position } from 'reactflow'
import { kindColor } from '../utils/types.js'

export default function EntityNode({ id, data }) {
  return (
    <div className={`entity-node${data.selected ? ' selected' : ''}`}>
      <Handle type="target" position={Position.Top} />
      <div className="entity-node__type" style={{ background: kindColor(data.kind) }}>
        {data.typeLabel}
      </div>
      <div className="entity-node__body">
        <div className="entity-node__label">{data.label}</div>
        {data.loading && <div className="entity-node__hint">loading…</div>}
        {data.expanded && data.edgeCount > 0 && (
          <span className="entity-node__count">
            {data.edgeCount}
            {data.truncated ? '+' : ''} {data.edgeCount === 1 ? 'link' : 'links'}
          </span>
        )}
      </div>
      {!data.expanded &&
        !data.loading &&
        (data.edgeCount === 0 ? (
          <div className="entity-node__nolinks">No links</div>
        ) : (
          <button
            type="button"
            className="entity-node__expand nodrag"
            onClick={() => data.onExpand?.(id)}
          >
            {typeof data.edgeCount === 'number'
              ? `${data.edgeCount}${data.truncated ? '+' : ''} ${data.edgeCount === 1 ? 'link' : 'links'}`
              : 'Expand'}
          </button>
        ))}
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
}
