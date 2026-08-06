/**
 * API client for the read-only Explorer.
 *
 * In dev, BASE_URL is '' so /api/* goes through the Vite proxy (see
 * vite.config.js), which targets **dataexplorer-backend** — every route this app
 * uses is a read. In a built deploy, VITE_API_BASE should point at that same read
 * service; the explorer never needs the curator, which is what lets it keep
 * working with the write tier stopped.
 *
 * Routes are namespaced by owning service (`/api/v1/dataexplorer/…`, per D8), so a
 * misconfigured base fails with a clean 404 instead of a 405 from a path that
 * happens to exist on the writer for a different method.
 *
 * `getShapes` now returns the same payload the curator serves, `readOnly` flags
 * included (D11 — it used to be deliberately unstamped). This app still ignores
 * those flags: nothing here writes.
 *
 * Every method returns the unwrapped response body.
 */
import axios from 'axios'

const BASE_URL = import.meta.env.DEV ? '' : (import.meta.env.VITE_API_BASE ?? '')
const API = '/api/v1/dataexplorer'

const http = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

export const api = {
  /** CURIE prefix → namespace map (hydrates compaction at startup). */
  getPrefixes: () => http.get(`${API}/meta/prefixes`).then((r) => r.data.prefixes),

  /** All SHACL shapes (used to populate the entity-type picker). */
  getShapes: () => http.get(`${API}/shapes`).then((r) => r.data),

  /** Autocomplete entities of a shape by label/IRI substring (empty = first N). */
  searchEntities: (shape, query, limit = 25) =>
    http.get(`${API}/entities/search`, { params: { shape, query, limit } }).then((r) => r.data),

  /** One node's own data + schema-defined inbound/outbound relation edges. */
  getNode: (id) => http.get(`${API}/graph/node`, { params: { id } }).then((r) => r.data),
}
