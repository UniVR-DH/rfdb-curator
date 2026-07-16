/**
 * Read-only Data Context Panel.
 *
 * Surfaces the runtime graph configuration so curators/operators can answer
 * "which named graph am I editing?", "how many triples are loaded?", and
 * "does the configured graph match what Oxigraph holds?" without a SPARQL
 * client. Strictly informational — it performs no writes and offers no
 * DROP/CLEAR/delete, so it is safe under the read-only editor flag.
 *
 * Data sources:
 *   - Graphs / counts / warnings: GET /api/meta/graphs (fetched lazily on open,
 *     refetched via the Refresh button).
 *   - Prefixes: the already-hydrated prefixMap from utils/prefixes.js (no fetch).
 */
import { useCallback, useEffect, useState } from 'react'
import { apiClient } from '../api/client.js'
import { compactIri, prefixMap } from '../utils/prefixes.js'
import Icon from './Icon.jsx'
import './DataContextPanel.css'

/** Locale-aware thousands separators for a triple count. */
function fmt(n) {
  const value = Number(n ?? 0)
  return Number.isFinite(value) ? value.toLocaleString('en-US') : '0'
}

export default function DataContextPanel() {
  const [context, setContext] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    apiClient
      .getGraphs()
      .then(setContext)
      .catch((err) => {
        setContext(null)
        setError(
          err?.response?.data?.detail || err?.message || 'Failed to load graph context.'
        )
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  // prefixMap is hydrated at startup; sort for a stable, scannable table.
  const prefixEntries = Object.entries(prefixMap).sort(([a], [b]) => a.localeCompare(b))

  return (
    <div className="data-context">
      <header className="dc-header">
        <div>
          <h2 className="dc-title">Data context</h2>
          <p className="dc-subtitle">Read-only view of the runtime graph configuration.</p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={load} disabled={loading}>
          <Icon name="RefreshCw" size={14} />
          Refresh
        </button>
      </header>

      <section className="dc-section">
        <h3 className="dc-section-title">Graphs</h3>
        {loading ? (
          <p className="dc-muted">Loading graph context…</p>
        ) : error ? (
          <p className="dc-error" role="alert">
            {error}
          </p>
        ) : context ? (
          <>
            <p className="dc-active">
              Active data graph:{' '}
              {context.activeGraph ? (
                <span className="mono">{compactIri(context.activeGraph)}</span>
              ) : (
                <em>default graph (unnamed)</em>
              )}
            </p>
            <table className="dc-table">
              <thead>
                <tr>
                  <th>Named graph</th>
                  <th className="dc-num">Triples</th>
                  <th className="dc-num">Subjects</th>
                  <th className="dc-num">Objects</th>
                  <th className="dc-num">Literals</th>
                </tr>
              </thead>
              <tbody>
                {context.graphs.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="dc-muted">
                      No named graphs in the store.
                    </td>
                  </tr>
                ) : (
                  context.graphs.map((g) => (
                    <tr key={g.uri} className={g.active ? 'dc-row-active' : ''}>
                      <td className="mono">
                        {compactIri(g.uri)}
                        {g.active && <span className="dc-badge">active</span>}
                      </td>
                      <td className="dc-num">{fmt(g.count)}</td>
                      <td className="dc-num">{fmt(g.subjects)}</td>
                      <td className="dc-num">{fmt(g.objects)}</td>
                      <td className="dc-num">{fmt(g.literals)}</td>
                    </tr>
                  ))
                )}
              </tbody>
              <tfoot>
                <tr>
                  <td>Total</td>
                  <td className="dc-num">{fmt(context.totalTriples)}</td>
                  <td className="dc-num">{fmt(context.totalSubjects)}</td>
                  <td className="dc-num">{fmt(context.totalObjects)}</td>
                  <td className="dc-num">{fmt(context.totalLiterals)}</td>
                </tr>
              </tfoot>
            </table>
            <p className="dc-muted dc-table-note">
              Per-graph subjects / objects / literals are distinct terms within each graph.
              The totals are counted once across the whole store, so they can be smaller
              than the column sums (a term can appear in more than one graph).
            </p>
          </>
        ) : null}
      </section>

      {!loading && !error && context && (
        <section className="dc-section">
          <h3 className="dc-section-title">Warnings</h3>
          {context.warnings.length === 0 ? (
            <p className="dc-ok">No issues detected.</p>
          ) : (
            <ul className="dc-warnings">
              {context.warnings.map((w) => (
                <li key={w} className="dc-warning">
                  {w}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <section className="dc-section">
        <h3 className="dc-section-title">Prefixes</h3>
        {prefixEntries.length === 0 ? (
          <p className="dc-muted">Prefix map not loaded.</p>
        ) : (
          <table className="dc-table">
            <thead>
              <tr>
                <th>Prefix</th>
                <th>Namespace</th>
              </tr>
            </thead>
            <tbody>
              {prefixEntries.map(([prefix, ns]) => (
                <tr key={prefix}>
                  <td className="mono">{prefix}:</td>
                  <td className="mono dc-ns">{ns}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}
