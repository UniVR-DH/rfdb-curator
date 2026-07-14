/**
 * Root application component.
 *
 * Layout (three columns):
 *   [< nav sidebar ]  [< tabbed form/records panel ]  [< inspector sidebar ]
 *
 * State machine:
 *   - `activeShape`       -- the currently selected SHACL NodeShape (drives both form and list)
 *   - `activeView`        -- `'form'` | `'records'` -- which tab is visible in the middle panel
 *   - `selectedRecord`    -- a record clicked in the records list; shown in the inspector
 *   - `validation`        -- the SHACL report returned after a form save
 *   - `shapeCounts`       -- {shapeId: count} map for the sidebar count pills
 *   - `recordsRefreshKey` -- increment to force ShapeRecordList + counts to re-fetch
 *
 * Main application logic:
 *
 * - activeShape: The currently selected SHACL shape (drives form and records list)
 * - activeView: 'form' or 'records' (which tab is visible)
 * - selectedRecord: The summary record selected from the list (id, label, etc.)
 * - loadedRecord: The full entity data fetched from the backend for editing
 * - recordLoading: True while fetching entity data for editing
 *
 * Edit flow:
 *   1. User clicks pencil (edit) button in records list.
 *   2. setSelectedRecord(record) and setActiveView('form') are called.
 *   3. useEffect triggers on selectedRecord, sets recordLoading=true, fetches entity data.
 *   4. While loading, show 'Loading record…' in the form panel.
 *   5. When loaded, setLoadedRecord(data), set recordLoading=false, render ShapeForm with loadedRecord.
 *
 * --- IMPORTANT: CREATE vs UPDATE ---
 * - When editing, App fetches the full entity and passes it as the record prop to ShapeForm.
 * - ShapeForm must ensure @id is included in the form state and payload for updates.
 * - If loadedRecord is null or fetch fails, the form should not be rendered for editing.
 *
 * View details flow:
 *   1. User clicks eye (see details) button in records list.
 *   2. setSelectedRecord(record) and setActiveView('records') are called.
 *   3. ValidationPanel shows details for selectedRecord in inspector sidebar.
 */

import { useCallback, useEffect, useState } from 'react'
import './App.css'
import { apiClient } from './api/client.js'
import Icon from './components/Icon.jsx'
import ShapeForm from './components/ShapeForm.jsx'
import ShapeRecordList from './components/ShapeRecordList.jsx'
import ValidationPanel from './components/ValidationPanel.jsx'
import { hydratePrefixes } from './utils/prefixes.js'

export default function App() {
  // --- Application state ---
  const [shapes, setShapes] = useState([]) // all SHACL shapes from /api/shapes
  const [shapesError, setShapesError] = useState(null) // visible sidebar error when shape fetch fails
  const [shapeCounts, setShapeCounts] = useState({}) // {shapeId: int} for sidebar pills
  const [activeShape, setActiveShape] = useState(null) // currently selected shape
  const [selectedRecord, setSelectedRecord] = useState(null) // summary record selected from list (id, label, etc.)
  const [loadedRecord, setLoadedRecord] = useState(null) // full entity data for editing (fetched from backend)
  const [validation, setValidation] = useState(null) // last SHACL report
  const [loadingShapes, setLoadingShapes] = useState(true)
  const [recordsRefreshKey, setRecordsRefreshKey] = useState(0) // bump to re-fetch list
  const [activeView, setActiveView] = useState('form') // 'form' | 'records'
  const [recordLoading, setRecordLoading] = useState(false) // true while fetching entity data for editing
  // In-memory, same-session draft cache keyed by `shape::<shapeId>`. Single slot per
  // shape form (last state wins), so unsaved input survives shape/record navigation
  // even though ShapeForm re-hydrates via reset() on every shape/record change.
  const [drafts, setDrafts] = useState({})

  // Draft key for the active shape form. Keyed by shape only (not record) so a draft
  // survives switching away and back; ShapeForm rebinds @id from the live record.
  const draftKey = activeShape ? `shape::${activeShape.id}` : null

  // Stable across renders (only closes over setDrafts) so ShapeForm's watch
  // subscription is not torn down and rebuilt on every keystroke-driven re-render.
  // Only new (create) forms keep a draft; editing an existing record always reloads
  // from that record, so drafts never carry an @id and can never turn into an update.
  const handleDraftChange = useCallback((key, value) => {
    setDrafts((prev) => ({ ...prev, [key]: value }))
  }, [])

  const handleDraftClear = useCallback((key) => {
    setDrafts((prev) => {
      if (!key || !(key in prev)) return prev
      const next = { ...prev }
      delete next[key]
      return next
    })
  }, [])

  /** Pull per-shape record counts from the backend and sync `shapeCounts`. */
  function refreshShapeCounts() {
    apiClient
      .getDataCounts()
      .then((data) => setShapeCounts(data?.counts ?? {}))
      .catch(() => setShapeCounts({}))
  }

  /** Format a raw count number with locale-aware thousands separators. */
  function formatCount(value) {
    const n = Number(value ?? 0)
    return Number.isFinite(n) ? Intl.NumberFormat('en-US').format(n) : '0'
  }

  function getShapeLoadErrorMessage(error) {
    const status = error?.response?.status
    const detail = error?.response?.data?.detail
    if (typeof detail === 'string' && detail.trim()) {
      return `Failed to load shapes (${status ?? 'error'}): ${detail}`
    }
    if (error?.message) {
      return `Failed to load shapes: ${error.message}`
    }
    return 'Failed to load shapes: unknown error.'
  }

  function loadShapes() {
    setLoadingShapes(true)
    setShapesError(null)
    apiClient
      .getShapes()
      .then((data) => {
        const sorted = [...data].sort((a, b) => (a.label || a.id).localeCompare(b.label || b.id))
        setShapes(sorted)
        if (sorted.length > 0) {
          setActiveShape(sorted[0])
          return
        }
        setActiveShape(null)
        setShapesError(
          'No shapes returned by /api/shapes. Check backend startup logs and schema/schema.ttl syntax.'
        )
      })
      .catch((error) => {
        setShapes([])
        setActiveShape(null)
        setShapesError(getShapeLoadErrorMessage(error))
      })
      .finally(() => setLoadingShapes(false))
  }

  useEffect(() => {
    loadShapes()

    refreshShapeCounts()

    // Hydrate prefix map in parallel with shape loading.
    // On failure degrade gracefully: IRI compaction and JSON-LD @context will be
    // empty until the next reload, but the app remains fully functional.
    apiClient.getPrefixes().then(hydratePrefixes).catch(() => {
      console.warn('Failed to fetch prefix map from /api/meta/prefixes; IRI compaction disabled.')
    })
  }, [])

  useEffect(() => {
    refreshShapeCounts()
  }, [recordsRefreshKey])

  // --- Handler: user selects a shape in the sidebar ---
  function handleShapeSelect(shape) {
    setActiveShape(shape)
    setSelectedRecord(null)
    setLoadedRecord(null)
    setValidation(null)
    setActiveView('form')
  }

  // --- Effect: when a record is selected for editing, fetch its full data from the backend ---
  // This ensures the form is only rendered with the correct data.
  useEffect(() => {
    if (!selectedRecord) {
      setLoadedRecord(null)
      setRecordLoading(false)
      return
    }
    setRecordLoading(true)
    apiClient
      .getEntity(selectedRecord.id)
      .then((res) => {
        setLoadedRecord(res)
        setRecordLoading(false)
      })
      .catch(() => {
        setLoadedRecord(null)
        setRecordLoading(false)
      })
  }, [selectedRecord])

  return (
    <div className="app-layout">
      {/* ── Left navigation ── */}
      <nav className="app-nav">
        <div>
          <p className="app-title">RossijskijFeatrDB</p>
          <p className="app-subtitle">Data Editor</p>
        </div>
        {loadingShapes ? (
          <p className="nav-loading">Loading shapes…</p>
        ) : shapesError ? (
          <div className="nav-error" role="alert">
            <p className="nav-error-text">{shapesError}</p>
            <button className="nav-error-retry" onClick={loadShapes}>
              Retry
            </button>
          </div>
        ) : (
          <ul className="shape-nav">
            {shapes.map((shape) => (
              <li key={shape.id}>
                <button
                  className={`nav-item ${activeShape?.id === shape.id ? 'active' : ''} ${shape.readOnly ? 'nav-item--readonly' : ''}`}
                  onClick={() => handleShapeSelect(shape)}
                >
                  <span className="nav-item-label">{shape.label}</span>
                  <span className="nav-item-right">
                    {shape.readOnly && (
                      <Icon name="Lock" size={11} className="nav-lock-icon" aria-label="Read-only" />
                    )}
                    <span className="nav-count-pill">{formatCount(shapeCounts[shape.id])}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </nav>

      {/* ── Main area with tabbed content + inspector ── */}
      <main className="app-main">
        {activeShape ? (
          <>
            <section className="panel-content">
              <div className="view-tabs" role="tablist" aria-label="Shape view tabs">
                <button
                  className={`view-tab ${activeView === 'form' ? 'active' : ''}`}
                  role="tab"
                  aria-selected={activeView === 'form'}
                  onClick={() => setActiveView('form')}
                >
                  Form
                </button>
                <button
                  className={`view-tab ${activeView === 'records' ? 'active' : ''}`}
                  role="tab"
                  aria-selected={activeView === 'records'}
                  onClick={() => setActiveView('records')}
                >
                  Records
                </button>
              </div>

              {activeView === 'form' ? (
                <div className="panel-form">
                  {/*
                    If editing an existing record, show a loading message until the full entity data is fetched.
                    Only render the form when not loading, or when creating a new record.
                  */}
                  {selectedRecord && recordLoading && (
                    <div className="form-loading">Loading record…</div>
                  )}
                  {/*
                    Bug risk: If loadedRecord is not set before rendering ShapeForm, update may fail or create new entity.
                    This is mitigated by only rendering ShapeForm when (!selectedRecord || !recordLoading) is true,
                    so loadedRecord is either null (create) or fully loaded (edit). If you change this logic, ensure
                    loadedRecord is always valid before rendering ShapeForm for edits.
                  */}
                  {(!selectedRecord || !recordLoading) && (
                    <ShapeForm
                      shape={activeShape}
                      allShapes={shapes}
                      record={loadedRecord}
                      draftKey={draftKey}
                      draftValue={draftKey ? drafts[draftKey] : undefined}
                      onDraftChange={handleDraftChange}
                      onValidation={setValidation}
                      onSaved={() => {
                        handleDraftClear(draftKey)
                        setSelectedRecord(null)
                        setLoadedRecord(null)
                        setRecordsRefreshKey((k) => k + 1)
                        setActiveView('records')
                      }}
                      onReset={() => {
                        handleDraftClear(draftKey)
                        setSelectedRecord(null)
                        setLoadedRecord(null)
                      }}
                    />
                  )}
                </div>
              ) : (
                <div className="panel-list">
                  <ShapeRecordList
                    shape={activeShape}
                    selected={selectedRecord}
                    refreshKey={recordsRefreshKey}
                    // --- Handler: user clicks pencil (edit) button ---
                    onEdit={(record) => {
                      setSelectedRecord(record)
                      setActiveView('form') // Switch to form for editing
                    }}
                    // --- Handler: user clicks eye (see details) button ---
                    onView={(record) => {
                      setSelectedRecord(record)
                      setActiveView('records') // Stay on records tab, just show details
                    }}
                    onDelete={() => {
                      setRecordsRefreshKey((k) => k + 1)
                    }}
                  />
                </div>
              )}
            </section>

            <aside className="panel-inspector">
              <ValidationPanel validation={validation} record={selectedRecord} />
            </aside>
          </>
        ) : (
          <div className="app-empty">
            <p className="app-empty-title">Select a shape to begin</p>
          </div>
        )}
      </main>
    </div>
  )
}
