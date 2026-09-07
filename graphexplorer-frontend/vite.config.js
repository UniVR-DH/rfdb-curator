import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// Read-only Explorer dev server. The browser only ever talks to this origin —
// the Vite server (Node) proxies both prefixes onward — so CORS is a non-issue
// in dev and nothing browser-facing has to name the host.
//
// Both prefixes share one upstream, because everything this app touches is a
// read. They stay separate rules because they are separate contracts (the same
// two proxy/Caddyfile routes): /api/v1/dataexplorer is the versioned
// operational surface, /rdf is the public permanent data space.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  // Evaluated by the Vite dev server (Node), not the browser — so this uses the
  // Docker service name. Override with VITE_PROXY_TARGET when running the
  // backend elsewhere (e.g. http://localhost:8001 on host).
  const read = env.VITE_PROXY_TARGET || 'http://dataexplorer-backend:8001'

  return {
    plugins: [react()],
    // Public path the built assets are requested from. `/` in dev and for a
    // standalone deploy at a domain root; production serves this app under
    // `/explorer/` behind the edge proxy, and Vite bakes asset URLs against
    // this value at build time — so it is a build arg (see the Dockerfile),
    // not something the running server can decide.
    base: env.VITE_BASE_PATH || '/',
    server: {
      port: 5174,
      proxy: {
        '/api': { target: read, changeOrigin: true },
        // Entity HTML pages and file content, reached by page navigation.
        '/rdf': { target: read, changeOrigin: true },
      },
    },
  }
})
