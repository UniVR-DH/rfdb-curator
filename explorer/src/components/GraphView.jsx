/**
 * React Flow canvas for the entity graph.
 *
 * App owns the graph model (plain node/edge arrays); this component maps them to
 * React Flow, runs elk auto-layout when the *structure* changes (node/edge
 * count), and patches node data / selection styling without relaying out. Node
 * positions are remembered in a ref so data patches and drags survive re-renders.
 *
 * Interaction: clicking a node selects it and asks App to expand it (fetch its
 * neighbours); clicking the pane clears the selection.
 */
import { useEffect, useRef } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  useEdgesState,
  useNodesState,
} from 'reactflow'
import 'reactflow/dist/style.css'
import EntityNode from './EntityNode.jsx'
import { applyElkLayout } from '../utils/layout.js'
import { kindColor } from '../utils/types.js'

const nodeTypes = { entity: EntityNode }

const EDGE_DEFAULT = '#c7bfb0'
const EDGE_ACTIVE = '#6b4c7a'

function toData(model, selectedId) {
  return {
    label: model.label,
    kind: model.kind,
    typeLabel: model.typeLabel,
    expanded: model.expanded,
    loading: model.loading,
    edgeCount: model.edgeCount,
    selected: model.id === selectedId,
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

export default function GraphView({ nodes, edges, selectedId, onSelect, onExpand }) {
  const [rfNodes, setRfNodes, onNodesChange] = useNodesState([])
  const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState([])
  const positions = useRef(new Map())

  const structureKey = `${nodes.length}:${edges.length}`

  // Layout: recompute positions only when the graph's structure changes.
  useEffect(() => {
    let cancelled = false
    const base = nodes.map((n) => ({
      id: n.id,
      type: 'entity',
      position: positions.current.get(n.id) || { x: 0, y: 0 },
      data: toData(n, selectedId),
    }))
    const rfe = edges.map((e) =>
      styleEdge({ id: e.id, source: e.source, target: e.target, label: e.label }, selectedId)
    )

    // If every node already has a remembered position, avoid a re-layout so the
    // graph doesn't reshuffle when nodes were only patched (not added/removed).
    if (nodes.length > 0 && nodes.every((n) => positions.current.has(n.id))) {
      setRfNodes(base)
      setRfEdges(rfe)
      return
    }

    applyElkLayout(base, edges).then((laid) => {
      if (cancelled) return
      laid.forEach((n) => positions.current.set(n.id, n.position))
      setRfNodes(laid)
      setRfEdges(rfe)
    })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [structureKey])

  // Patch node data + selection styling in place (no re-layout).
  useEffect(() => {
    setRfNodes((cur) =>
      cur.map((rn) => {
        const model = nodes.find((n) => n.id === rn.id)
        return model ? { ...rn, data: toData(model, selectedId) } : rn
      })
    )
    setRfEdges((cur) => cur.map((re) => styleEdge(re, selectedId)))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, selectedId])

  return (
    <ReactFlow
      nodes={rfNodes}
      edges={rfEdges}
      nodeTypes={nodeTypes}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onNodeClick={(_, n) => {
        onSelect(n.id)
        onExpand(n.id)
      }}
      onNodeDragStop={(_, n) => positions.current.set(n.id, n.position)}
      onPaneClick={() => onSelect(null)}
      minZoom={0.15}
      fitView
    >
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
