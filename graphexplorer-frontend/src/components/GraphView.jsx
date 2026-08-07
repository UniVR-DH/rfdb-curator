/**
 * React Flow canvas for the entity graph.
 *
 * App owns the graph model (plain node/edge arrays); this component maps them to
 * React Flow. On the first load it runs elk auto-layout over the whole graph; on
 * each expand it places *only the new neighbours* on a ring around their parent
 * and leaves already-placed nodes fixed, so the graph grows outward instead of
 * reshuffling. A "Re-layout" control re-runs elk over everything on demand. Node
 * positions are remembered in a ref so data patches and drags survive re-renders.
 *
 * Interaction: clicking a node selects it and asks App to expand it (fetch its
 * neighbours); clicking the pane clears the selection.
 */
import { useEffect, useRef, useState } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  Panel,
  useEdgesState,
  useNodesInitialized,
  useNodesState,
  useReactFlow,
} from 'reactflow'
import 'reactflow/dist/style.css'
import EntityNode from './EntityNode.jsx'
import { applyElkLayout, placeNewNodes } from '../utils/layout.js'
import { kindColor } from '../utils/types.js'

const nodeTypes = { entity: EntityNode }

const EDGE_DEFAULT = '#c7bfb0'
const EDGE_ACTIVE = '#6b4c7a'

// `model.edgeCount` is the entity's total incident-edge count from the API — it
// includes the edge that already brought this node onto the canvas (drawn when
// its parent was expanded). The expand button/badge should only advertise links
// still worth revealing, so we subtract edges already present in the rendered
// graph (`edges`) to get `pendingCount`.
function toData(model, edges, selectedId, onExpand) {
  const incident = edges.reduce(
    (n, e) => n + (e.source === model.id || e.target === model.id ? 1 : 0),
    0
  )
  const pendingCount =
    typeof model.edgeCount === 'number' ? Math.max(0, model.edgeCount - incident) : null
  return {
    label: model.label,
    kind: model.kind,
    typeLabel: model.typeLabel,
    isBridge: model.isBridge,
    expanded: model.expanded,
    loading: model.loading,
    edgeCount: model.edgeCount,
    pendingCount,
    truncated: model.truncated,
    selected: model.id === selectedId,
    onExpand,
  }
}

function styleEdge(edge, selectedId) {
  const active = selectedId && (edge.source === selectedId || edge.target === selectedId)
  const color = active ? EDGE_ACTIVE : EDGE_DEFAULT
  return {
    ...edge,
    animated: !!active,
    labelStyle: { fontSize: 10, fill: '#6b6459', fontFamily: 'var(--font-mono)' },
    labelBgStyle: { fill: '#f5f1e8', fillOpacity: 0.85 },
    style: { stroke: color, strokeWidth: active ? 2.5 : 1.5 },
    markerEnd: { type: MarkerType.ArrowClosed, width: 15, height: 15, color },
  }
}

// Frames the graph once its freshly-laid nodes have been measured, capping the
// zoom so a lone seed node never fills the screen. Keyed on `layoutTick` so it
// only re-fits on first load / re-layout / the seed's first expansion — never on
// deeper expands, which deliberately grow the graph outward in place.
function FitOnLayout({ layoutTick }) {
  const initialized = useNodesInitialized()
  const { fitView } = useReactFlow()
  const fitted = useRef(-1)
  useEffect(() => {
    if (initialized && fitted.current !== layoutTick) {
      fitted.current = layoutTick
      fitView({ maxZoom: 1, padding: 0.2 })
    }
  }, [initialized, layoutTick, fitView])
  return null
}

export default function GraphView({ nodes, edges, selectedId, onSelect, onExpand }) {
  const [rfNodes, setRfNodes, onNodesChange] = useNodesState([])
  const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState([])
  const positions = useRef(new Map())
  const [relayoutTick, setRelayoutTick] = useState(0)
  const [fitTick, setFitTick] = useState(0)

  const structureKey = `${nodes.length}:${edges.length}`

  // Drop remembered positions and re-run a full elk layout over everything.
  const relayout = () => {
    positions.current = new Map()
    setRelayoutTick((t) => t + 1)
  }

  // Layout: place new nodes incrementally; run full elk only on first load or an
  // explicit re-layout. Keyed on structure changes + the re-layout counter, not
  // on data patches (selection/label) which the patch effect below handles.
  useEffect(() => {
    let cancelled = false
    const rfe = edges.map((e) =>
      styleEdge({ id: e.id, source: e.source, target: e.target, label: e.label }, selectedId)
    )
    const buildBase = () =>
      nodes.map((n) => ({
        id: n.id,
        type: 'entity',
        position: positions.current.get(n.id) || { x: 0, y: 0 },
        data: toData(n, edges, selectedId, onExpand),
      }))

    const fresh = nodes.filter((n) => !positions.current.has(n.id))
    const placedCount = nodes.length - fresh.length

    // No new nodes (edge-only change or pure re-render): keep positions as-is.
    if (fresh.length === 0) {
      setRfNodes(buildBase())
      setRfEdges(rfe)
      return
    }

    // First layout / re-layout: lay the whole graph out with elk.
    if (placedCount === 0) {
      applyElkLayout(buildBase(), edges).then((laid) => {
        if (cancelled) return
        laid.forEach((n) => positions.current.set(n.id, n.position))
        setRfNodes(laid)
        setRfEdges(rfe)
        setFitTick((t) => t + 1)
      })
      return () => {
        cancelled = true
      }
    }

    // Incremental: keep placed nodes fixed, ring the new ones around their parent.
    const added = placeNewNodes(fresh, edges, positions.current)
    added.forEach((pos, id) => positions.current.set(id, pos))
    setRfNodes(buildBase())
    setRfEdges(rfe)
    // Frame the seed's first expansion (lone node → its neighbour ring); deeper
    // expands keep the camera put so the user stays oriented on what they clicked.
    if (placedCount === 1) setFitTick((t) => t + 1)
  }, [structureKey, relayoutTick])

  // Patch node data + selection styling in place (no re-layout).
  useEffect(() => {
    setRfNodes((cur) =>
      cur.map((rn) => {
        const model = nodes.find((n) => n.id === rn.id)
        return model ? { ...rn, data: toData(model, edges, selectedId, onExpand) } : rn
      })
    )
    setRfEdges((cur) => cur.map((re) => styleEdge(re, selectedId)))
  }, [nodes, selectedId])

  return (
    <ReactFlow
      nodes={rfNodes}
      edges={rfEdges}
      nodeTypes={nodeTypes}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onNodeClick={(_, n) => onSelect(n.id)}
      onNodeDragStop={(_, n) => positions.current.set(n.id, n.position)}
      onPaneClick={() => onSelect(null)}
      minZoom={0.15}
    >
      <FitOnLayout layoutTick={fitTick} />
      <Panel position="top-right">
        <button className="btn" onClick={relayout} disabled={nodes.length === 0}>
          Re-layout
        </button>
      </Panel>
      <Background color="#d8d2c4" gap={22} />
      <Controls showInteractive={false} />
      <MiniMap
        pannable
        zoomable
        nodeColor={(n) => kindColor(n.data?.kind)}
        maskColor="rgba(45,55,72,0.12)"
      />
    </ReactFlow>
  )
}
