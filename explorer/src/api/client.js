/**
 * API client for the read-only Explorer.
 *
 * In dev, BASE_URL is '' so /api/* goes through the Vite proxy (see
 * vite.config.js). In a built deploy, VITE_API_BASE can point at the backend.
 * Every method returns the unwrapped response body.
 */
import axios from 'axios'

const BASE_URL = import.meta.env.DEV ? '' : (import.meta.env.VITE_API_BASE ?? '')

const http = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

export const api = {
  /** CURIE prefix → namespace map (hydrates compaction at startup). */
  getPrefixes: () => http.get('/api/meta/prefixes').then((r) => r.data.prefixes),

  /** All SHACL shapes (used to populate the entity-type picker). */
  getShapes: () => http.get('/api/shapes').then((r) => r.data),

  /** Autocomplete entities of a shape by label/IRI substring (empty = first N). */
  searchEntities: (shape, query, limit = 25) =>
    http.get('/api/entities/search', { params: { shape, query, limit } }).then((r) => r.data),

  /** One node's own data + schema-defined inbound/outbound relation edges. */
  getNode: (id) => http.get('/api/graph/node', { params: { id } }).then((r) => r.data),
}
