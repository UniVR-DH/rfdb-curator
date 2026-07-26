/**
 * Prefix compaction for display. The backend returns full IRIs everywhere; this
 * maps them to compact CURIEs (e.g. https://…/data/Src_1 -> rfdb:Src_1). The map
 * is hydrated once at startup from GET /api/meta/prefixes.
 */

/** @type {Record<string, string>} CURIE prefix -> namespace URI. */
export const prefixMap = {}

/** Populate the prefix map from the backend response (call once at startup). */
export function hydratePrefixes(map) {
  Object.assign(prefixMap, map)
}

/**
 * Compact a full IRI to its CURIE form. Returns the value unchanged when it is
 * not a string, already looks like a CURIE, or matches no known namespace.
 */
export function compactIri(value) {
  if (!value || typeof value !== 'string') return value
  if (value.includes(':') && !value.startsWith('http://') && !value.startsWith('https://')) {
    return value
  }
  for (const [prefix, ns] of Object.entries(prefixMap)) {
    if (value.startsWith(ns)) {
      return `${prefix}:${value.slice(ns.length)}`
    }
  }
  return value
}

/** Last path/fragment segment of an IRI (fallback display when no prefix matches). */
export function localName(uri) {
  if (!uri || typeof uri !== 'string') return uri
  const parts = uri.split(/[#/]/)
  return parts[parts.length - 1] || uri
}
