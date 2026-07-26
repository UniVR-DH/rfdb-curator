/**
 * Entity search box that seeds (or re-seeds) the graph.
 *
 * Defaults to searching Sources but offers a type dropdown of all standalone
 * entities, so exploration can start from any record. Calls the same
 * /api/entities/search endpoint the editor uses; picking a result hands its IRI
 * back to App via `onPick`.
 *
 * Props:
 *   shapes         [{id,label}]  standalone-entity shapes for the type dropdown
 *   defaultShapeId string        which shape to search first (usually SourceShape)
 *   onPick         fn(iri)       called with the chosen entity's IRI
 *   variant        'intro'|'header'  layout context
 */
import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { compactIri } from '../utils/prefixes.js'

export default function SourcePicker({ shapes, defaultShapeId, onPick, variant = 'intro' }) {
  const [shapeId, setShapeId] = useState(defaultShapeId || '')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(variant === 'intro')

  useEffect(() => {
    if (defaultShapeId && !shapeId) setShapeId(defaultShapeId)
  }, [defaultShapeId, shapeId])

  // Debounced search on (shape, query).
  useEffect(() => {
    if (!shapeId) return
    let cancelled = false
    setLoading(true)
    const t = setTimeout(() => {
      api
        .searchEntities(shapeId, query)
        .then((rows) => {
          if (cancelled) return
          setResults(rows)
          setLoading(false)
          setOpen(true)
        })
        .catch(() => {
          if (cancelled) return
          setResults([])
          setLoading(false)
        })
    }, 220)
    return () => {
      cancelled = true
      clearTimeout(t)
    }
  }, [shapeId, query])

  return (
    <div className={variant === 'header' ? 'header-picker' : ''}>
      <div className="picker">
        {shapes?.length > 0 && (
          <select
            className="picker-select"
            value={shapeId}
            onChange={(e) => setShapeId(e.target.value)}
          >
            {shapes.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        )}
        <input
          className="picker-input"
          placeholder="Search by name…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setOpen(true)}
        />
      </div>
      {open && (
        <div className="picker-results">
          {loading && <div className="picker-loading">Searching…</div>}
          {!loading && results.length === 0 && <div className="picker-empty">No matches</div>}
          {results.map((r) => (
            <div
              key={r.uri}
              className="picker-result"
              onClick={() => {
                onPick(r.uri)
                setOpen(variant === 'intro')
                if (variant === 'header') setQuery('')
              }}
            >
              <span className="r-label">{r.label || compactIri(r.uri)}</span>
              <span className="r-iri">{compactIri(r.uri)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
