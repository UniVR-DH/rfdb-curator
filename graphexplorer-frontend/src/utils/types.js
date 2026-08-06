/**
 * Type & predicate presentation, derived entirely from the SHACL schema — no
 * class or predicate is named in this file, so the explorer works against any
 * SHACL-described dataset, not just one domain.
 *
 *   - a node's display type + label come from the shape whose `sh:targetClass`
 *     matches one of the node's `rdf:type`s (its `rdfs:label`);
 *   - a relation's label comes from that property's `sh:name`;
 *   - a node's colour is hashed deterministically from its type URI, so every
 *     type gets a stable, distinct hue with no palette to hand-maintain.
 *
 * Call `hydrateSchema(shapes)` once at startup with the `GET /api/v1/dataexplorer/shapes` body.
 */
import { localName } from './prefixes.js'

/** @type {Map<string,string>} full class URI -> human label (shape rdfs:label). */
let typeLabels = new Map()
/** @type {Map<string,string>} full predicate URI -> human label (property sh:name). */
let predLabels = new Map()

/** Build the label maps from `GET /api/v1/dataexplorer/shapes` (call once at startup). */
export function hydrateSchema(shapes = []) {
  typeLabels = new Map()
  predLabels = new Map()
  for (const shape of shapes) {
    if (shape.targetClassUri && shape.label) {
      typeLabels.set(shape.targetClassUri, shape.label)
    }
    for (const prop of shape.properties || []) {
      if (prop.pathUri && prop.name && !predLabels.has(prop.pathUri)) {
        predLabels.set(prop.pathUri, prop.name)
      }
    }
  }
}

/** A node's primary type: the first rdf:type the schema knows, else the first. */
function primaryType(types = []) {
  return types.find((t) => typeLabels.has(t)) || types[0] || null
}

/**
 * Resolve a node's class URIs to `{ kind, label }`. `kind` is the primary type
 * URI used only as a stable colour seed; `label` is the schema's human name for
 * that type, falling back to its local name.
 *
 * @param {string[]} types - Full RDF class URIs.
 * @returns {{kind: string|null, label: string}}
 */
export function entityKind(types = []) {
  const t = primaryType(types)
  if (!t) return { kind: null, label: 'Entity' }
  return { kind: t, label: typeLabels.get(t) || localName(t) }
}

/**
 * Stable, muted colour for a type URI. The hue is hashed from the URI; keeping
 * saturation/lightness fixed and dark-ish matches the scholarly palette and
 * keeps the cream node-header text readable across every hue.
 */
export function kindColor(kind) {
  if (!kind) return 'var(--kind-default)'
  let hue = 0
  for (let i = 0; i < kind.length; i++) hue = (hue * 31 + kind.charCodeAt(i)) % 360
  return `hsl(${hue}, 35%, 40%)`
}

/** Human label for a relation predicate (`sh:name`), else its local name. */
export function predicateLabel(uri) {
  return predLabels.get(uri) || localName(uri)
}
