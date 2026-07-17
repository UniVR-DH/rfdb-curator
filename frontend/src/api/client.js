/**
 * Centralised API client used by all React components.
 *
 * Uses axios with a base URL resolved from the Vite environment:
 *   - In dev mode (Vite dev server) the base is empty string (`""`), so all
 *     `/api/...` requests go through the Vite proxy defined in `vite.config.js`
 *     (proxy target: `http://localhost:8000`).
 *   - In production the `VITE_API_BASE` env var can override the base URL.
 *
 * All methods return the unwrapped `data` field from the axios response so
 * callers work directly with the JSON payload.
 */
import axios from 'axios'

const BASE_URL = import.meta.env.DEV ? '' : import.meta.env.VITE_API_BASE ?? ''

const http = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

export const apiClient = {
  /** Fetch all SHACL NodeShapes.  Called once on app mount to populate the sidebar. */
  getShapes: () => http.get('/api/shapes').then((r) => r.data),

  /** Fetch form field definitions for a single shape. */
  getFormSchema: (shapeId) => http.get('/api/forms', { params: { shapeId } }).then((r) => r.data),

  /** List stored entities for a shape with optional text search and pagination. */
  listData: (shapeId, { q = '', limit = 50, offset = 0 } = {}) =>
    http.get('/api/data/list', { params: { shapeId, q, limit, offset } }).then((r) => r.data),

  /** Fetch per-shape record counts for the sidebar count pills. */
  getDataCounts: () => http.get('/api/data/counts').then((r) => r.data),

  /** Fetch all triples for a single entity (used by ValidationPanel inspector). */
  getEntity: (entityId) =>
    http.get(`/api/data/${encodeURIComponent(entityId)}`).then((r) => r.data),

  /** Create or update an entity.  Returns success flag + validation report. */
  createEntity: (payload) => http.post('/api/data', payload).then((r) => r.data),

  /**
   * Autocomplete search for entities of a given shape (relation field dropdown).
   * `query` may be empty to pre-populate the dropdown on field focus.
   */
  searchEntities: (shape, query, limit = 50) =>
    http.get('/api/entities/search', { params: { shape, query, limit } }).then((r) => r.data),

  /** Dry-run SHACL validation without persisting (used by ValidationPanel). */
  validateEntity: (payload) => http.post('/api/validate', payload).then((r) => r.data),

  /** Delete an entity by IRI. Pass shapeId to enable per-shape write protection on the backend. */
  deleteEntity: (entityId, shapeId = '') =>
    http.delete(`/api/data/${encodeURIComponent(entityId)}`, {
      params: shapeId ? { shapeId } : undefined,
    }),

  /**
   * Fetch the authoritative prefix-to-namespace map from the backend.
   * Returns a plain object keyed by prefix (e.g. { "rfdb": "https://…", … }).
   * Called once at app startup to hydrate utils/prefixes.js and utils/jsonld.js.
   */
  getPrefixes: () => http.get('/api/meta/prefixes').then((r) => r.data.prefixes),

  /**
   * Stage a PDF (upload-first flow). Returns the prefilled digital-copy node
   * ({id, fileId, name, contentUrl, contentSize, sha256, numberOfPages}) that
   * the FileField appends to form state; it becomes a bridge node in the
   * JSON-LD payload on submit. `file` is a browser File object.
   */
  stageFile: (file) => {
    const form = new FormData()
    form.append('file', file)
    return http
      .post('/api/files/staged', form, { headers: { 'Content-Type': 'multipart/form-data' } })
      .then((r) => r.data)
  },

  /**
   * Direct download URL for a stored PDF (for an <a href>).
   * In dev BASE_URL is '' so it routes through the Vite proxy.
   */
  fileDownloadUrl: (fileId) => `${BASE_URL}/api/files/${encodeURIComponent(fileId)}`,

  /** Digital-copy storage stats (staged/registered/orphans) for the Data Context Panel. */
  getFileStats: () => http.get('/api/meta/files').then((r) => r.data),

  /**
   * Fetch the runtime graph context for the read-only Data Context Panel:
   * active graph URI, named graphs with triple counts, a store-wide total,
   * and advisory config warnings. Store-wide (unscoped) — fetched lazily on
   * panel open, not at startup.
   */
  getGraphs: () => http.get('/api/meta/graphs').then((r) => r.data),
}
