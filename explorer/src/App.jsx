/**
 * RFDB Explorer — read-only lineage & relationship graph over the backend.
 *
 * App owns all state and the graph model. It hydrates the prefix map + shape
 * list once, then builds the graph incrementally: each node the user opens is
 * fetched from GET /api/graph/node (schema-defined inbound/outbound relations),
 * its neighbours are added as collapsed nodes, and clicking one expands it in
 * turn. A ?id=<iri> query param deep-links straight to a node — the editor uses
 * this to "open in Explorer".
 *
 * Child components are presentational: GraphView renders the model with React
 * Flow + elk; Inspector shows the selected node; SourcePicker seeds it.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api/client.js'
import GraphView from './components/GraphView.jsx'
import Inspector from './components/Inspector.jsx'
import SourcePicker from './components/SourcePicker.jsx'
import { compactIri, hydratePrefixes } from './utils/prefixes.js'
import { entityKind, predicateLabel } from './utils/types.js'

function stubNode(id) {
  return {
    id,
    label: compactIri(id),
    types: [],
    kind: 'default',
    typeLabel: 'Entity',
    expanded: false,
    loading: false,
    edgeCount: 0,
  }
}

function errMessage(err) {
  return err?.response?.data?.detail || err?.message || 'Request failed'
}

export default function App() {
  const [ready, setReady] = useState(false)
  const [shapes, setShapes] = useState([])
  const [nodesMap, setNodesMap] = useState({})
  const [edgesMap, setEdgesMap] = useState({})
  const [selectedId, setSelectedId] = useState(null)
  const [error, setError] = useState(null)
  const requested = useRef(new Set())

  // Fetch one node and merge it (plus its neighbours) into the graph model.
  // Guarded by `requested` so each node is fetched at most once.
  const loadNode = useCallback((id) => {
    if (!id || requested.current.has(id)) return
    requested.current.add(id)
    setNodesMap((prev) => ({ ...prev, [id]: { ...(prev[id] || stubNode(id)), loading: true } }))
    api
      .getNode(id)
      .then((data) => {
        const kind = entityKind(data.types)
        setNodesMap((prev) => {
          const next = { ...prev }
          next[id] = {
            id,
            label: data.label || compactIri(id),
            types: data.types,
            kind: kind.kind,
            typeLabel: kind.label,
            expanded: true,
            loading: false,
            edgeCount: data.edges.length,
            details: { literals: data.literals, externalLinks: data.externalLinks },
          }
          for (const e of data.edges) {
            const nb = e.neighbor
            if (!next[nb.id]) {
              const nk = entityKind(nb.types)
              next[nb.id] = {
                id: nb.id,
                label: nb.label || compactIri(nb.id),
                types: nb.types,
                kind: nk.kind,
                typeLabel: nk.label,
                expanded: false,
                loading: false,
                edgeCount: 0,
              }
            }
          }
          return next
        })
        setEdgesMap((prev) => {
          const next = { ...prev }
          for (const e of data.edges) {
            const source = e.direction === 'in' ? e.neighbor.id : id
            const target = e.direction === 'in' ? id : e.neighbor.id
            const eid = `${source}|${e.predicate}|${target}`
            if (!next[eid]) {
              next[eid] = { id: eid, source, target, predicate: e.predicate, label: predicateLabel(e.predicate) }
            }
          }
          return next
        })
      })
      .catch((err) => {
        requested.current.delete(id) // allow a later retry
        setNodesMap((prev) => (prev[id] ? { ...prev, [id]: { ...prev[id], loading: false } } : prev))
        setError(errMessage(err))
      })
  }, [])

  const activate = useCallback(
    (id) => {
      setError(null)
      setSelectedId(id)
      loadNode(id)
    },
    [loadNode]
  )

  const clearGraph = useCallback(() => {
    requested.current = new Set()
    setNodesMap({})
    setEdgesMap({})
    setSelectedId(null)
    setError(null)
  }, [])

  // Startup: hydrate prefixes + shapes, then honour a ?id= deep link.
  useEffect(() => {
    let cancelled = false
    Promise.all([api.getPrefixes(), api.getShapes()])
      .then(([prefixes, allShapes]) => {
        if (cancelled) return
        hydratePrefixes(prefixes)
        setShapes(allShapes.filter((s) => s.shapeRole === 'standalone-entity'))
        setReady(true)
        const id = new URLSearchParams(window.location.search).get('id')
        if (id) activate(id)
      })
      .catch((err) => {
        if (!cancelled) setError(errMessage(err))
      })
    return () => {
      cancelled = true
    }
  }, [activate])

  const nodes = useMemo(() => Object.values(nodesMap), [nodesMap])
  const edges = useMemo(() => Object.values(edgesMap), [edgesMap])
  const hasGraph = nodes.length > 0
  const defaultShapeId = useMemo(
    () => shapes.find((s) => s.id.endsWith('SourceShape'))?.id || shapes[0]?.id,
    [shapes]
  )

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1 className="app-title">RFDB Explorer</h1>
          <p className="app-subtitle">Lineage &amp; relationships</p>
        </div>
        {hasGraph && ready && (
          <SourcePicker
            shapes={shapes}
            defaultShapeId={defaultShapeId}
            onPick={activate}
            variant="header"
          />
        )}
        <div className="spacer" />
        {hasGraph && (
          <button className="btn btn-ghost" onClick={clearGraph}>
            Clear
          </button>
        )}
      </header>

      <div className="app-body">
        {error && <div className="banner-error">{error}</div>}

        {!hasGraph ? (
          <div className="intro">
            <div className="intro-card">
              <h2>Explore the graph</h2>
              <p>
                Pick a source (or any record) to see its lineage — the work it belongs to, its
                people and roles, performances, and more. Click any node to expand it.
              </p>
              {ready ? (
                <SourcePicker
                  shapes={shapes}
                  defaultShapeId={defaultShapeId}
                  onPick={activate}
                  variant="intro"
                />
              ) : (
                <p className="picker-loading">Loading…</p>
              )}
            </div>
          </div>
        ) : (
          <>
            <GraphView
              nodes={nodes}
              edges={edges}
              selectedId={selectedId}
              onSelect={setSelectedId}
              onExpand={loadNode}
            />
            {selectedId && nodesMap[selectedId] && (
              <Inspector
                node={nodesMap[selectedId]}
                edges={edges}
                nodesById={nodesMap}
                onSelectNeighbor={activate}
                onClose={() => setSelectedId(null)}
              />
            )}
          </>
        )}
      </div>
    </div>
  )
}
