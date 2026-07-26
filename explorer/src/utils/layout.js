/**
 * Auto-layout via elkjs (runs in-browser). One ELK instance for the app.
 *
 * A force-directed profile suits an association/relationship graph (as opposed
 * to a strict hierarchy). Positions are mapped back onto the React Flow nodes;
 * a simple grid is used as a fallback if ELK throws.
 */
import ELK from 'elkjs/lib/elk.bundled.js'

const elk = new ELK()

const NODE_W = 220
const NODE_H = 92

const LAYOUT_OPTIONS = {
  'elk.algorithm': 'force',
  'elk.force.iterations': '120',
  'elk.force.repulsivePower': '2.0',
  'elk.spacing.nodeNode': '120',
  'elk.separateConnectedComponents': 'true',
}

/**
 * Compute positions for `nodes` given `edges` and return the nodes with a
 * `position` set. `nodes`/`edges` are React Flow shapes ({id}, {source,target}).
 */
export async function applyElkLayout(nodes, edges) {
  const graph = {
    id: 'root',
    layoutOptions: LAYOUT_OPTIONS,
    children: nodes.map((n) => ({ id: n.id, width: NODE_W, height: NODE_H })),
    edges: edges.map((e, i) => ({
      id: e.id || `e${i}`,
      sources: [e.source],
      targets: [e.target],
    })),
  }
  try {
    const laid = await elk.layout(graph)
    const pos = new Map((laid.children || []).map((c) => [c.id, { x: c.x, y: c.y }]))
    return nodes.map((n) => ({ ...n, position: pos.get(n.id) || n.position || { x: 0, y: 0 } }))
  } catch {
    return nodes.map((n, i) => ({
      ...n,
      position: { x: (i % 5) * 260, y: Math.floor(i / 5) * 170 },
    }))
  }
}
