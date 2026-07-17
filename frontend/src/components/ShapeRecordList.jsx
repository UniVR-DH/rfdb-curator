/**
 * Scrollable list of stored entities for the active SHACL shape.
 *
 * Fetches from GET /api/data/list whenever shape, query, or refreshKey changes.
 * refreshKey is incremented by the parent after a successful save so the list
 * updates without a full page reload.
 *
 * Records with multiple rdfs:label values are deduplicated server-side;
 * each row shows one compact IRI, the primary label, and an optional lang chip.
 *
 * Props:
 *   shape       {object}       - Active SHACL shape descriptor from /api/shapes
 *   selected    {object|null}  - Currently selected record (used for highlight)
 *   refreshKey  {number}       - Increment to trigger a data re-fetch
 *   onSelect    {function}     - Called with the clicked record object
 *
 * --- AUDIT: ShapeRecordList ---
 * - Only lists records and triggers edit/view actions.
 * - Does not manage @id or form state directly.
 * - Passes selected record's id to ShapeForm for editing.
 * - No direct bug risk for create/update distinction here.
 */
import { useEffect, useState } from 'react'
import { apiClient } from '../api/client.js'
import { compactIri } from '../utils/prefixes.js'
 
import Icon from './Icon.jsx'
import './ShapeRecordList.css'

/**
 * Props:
 *   shape       {object}
 *   selected    {object|null}
 *   refreshKey  {number}
 *   onEdit      {function} - called with record to edit (loads in form)
 *   onView      {function} - called with record to view (shows in inspector only)
 */
export default function ShapeRecordList({
  shape,
  selected,
  refreshKey = 0,
  onEdit,
  onView,
  onDelete,
}) {
  const [records, setRecords] = useState([])
  const [total, setTotal] = useState(0)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [deletingId, setDeletingId] = useState(null)

  useEffect(() => {
    if (!shape) return
    setLoading(true)
    apiClient
      .listData(shape.id, { q: query })
      .then((res) => {
        setRecords(res.items ?? [])
        setTotal(res.total ?? 0)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [shape, query, refreshKey])

  const handleDelete = async (rec) => {
    if (!window.confirm('Delete this record? This cannot be undone.')) return
    setDeletingId(rec.id)
    try {
      await apiClient.deleteEntity(rec.id, shape?.id)
      setRecords((prev) => prev.filter((r) => r.id !== rec.id))
      setTotal((t) => t - 1)
      onDelete?.() // notify parent to refresh counts
    } catch (err) {
      alert('Delete failed: ' + (err?.response?.data?.detail || err.message))
    } finally {
      setDeletingId(null)
    }
  }

  // Hide edit/delete for read-only reference vocab AND for helper-bridge shapes
  // (AgentRole, DigitalCopy) — those are managed only from their parent's form,
  // so the Records list is browse/view-only.
  const isReadOnly = shape?.readOnly === true || shape?.shapeRole === 'helper-bridge'

  return (
    <div className="record-list">
      <div className="record-list-header">
        <span className="record-list-count">{total} records</span>
        <input
          className="record-list-search"
          type="search"
          placeholder="Filter…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      {loading && <div className="record-list-loading">Loading…</div>}

      <ul className="record-list-items">
        {records.map((rec) => (
          <li key={rec.id} className={`record-item ${selected?.id === rec.id ? 'active' : ''}`}>
            <div className="record-row-flex">
              <div className="record-main">
                <span className="record-id mono">{compactIri(rec.id)}</span>
                <span className="record-label-row">
                  <span className="record-label">{rec.label ?? '—'}</span>
                  {rec.labelLang ? <span className="record-lang-tag">{rec.labelLang}</span> : null}
                </span>
                {rec.status && rec.status !== 'unknown' && (
                  <span className={`record-status status-${rec.status}`}>{rec.status}</span>
                )}
              </div>
              <span className="record-actions">
                {!isReadOnly && (
                  <button
                    className="record-action-btn"
                    title="Edit"
                    onClick={(e) => {
                      e.stopPropagation()
                      onEdit?.(rec)
                    }}
                  >
                    <Icon name="Pencil" aria-label="Edit" />
                  </button>
                )}
                <button
                  className="record-action-btn"
                  title="See details"
                  onClick={(e) => {
                    e.stopPropagation()
                    onView?.(rec)
                  }}
                >
                  <Icon name="Eye" aria-label="See details" />
                </button>
                {!isReadOnly && (
                  <button
                    className="record-action-btn"
                    title="Delete"
                    disabled={deletingId === rec.id}
                    onClick={(e) => {
                      e.stopPropagation()
                      handleDelete(rec)
                    }}
                  >
                    <Icon name="Trash" aria-label="Delete" />
                  </button>
                )}
              </span>
            </div>
          </li>
        ))}
        {!loading && records.length === 0 && <li className="record-empty">No records found</li>}
      </ul>
    </div>
  )
}
