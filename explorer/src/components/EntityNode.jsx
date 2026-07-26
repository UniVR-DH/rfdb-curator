/**
 * Custom React Flow node for one RDF entity.
 *
 * Reads its display fields from `data` (built in App.jsx): the coloured type
 * header, the label, and a hint that reflects whether the node has been expanded
 * yet. Top/bottom handles let React Flow route relation edges.
 */
import { Handle, Position } from 'reactflow'
import { kindColor } from '../utils/types.js'

export default function EntityNode({ data }) {
  return (
    <div className={`entity-node${data.selected ? ' selected' : ''}`}>
      <Handle type="target" position={Position.Top} />
      <div className="entity-node__type" style={{ background: kindColor(data.kind) }}>
        {data.typeLabel}
      </div>
      <div className="entity-node__body">
        <div className="entity-node__label">{data.label}</div>
        {data.loading ? (
          <div className="entity-node__hint">loading…</div>
        ) : data.expanded ? (
          data.edgeCount > 0 && (
            <span className="entity-node__count">
              {data.edgeCount} {data.edgeCount === 1 ? 'link' : 'links'}
            </span>
          )
        ) : (
          <div className="entity-node__hint">click to expand</div>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
}
