import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// Read-only Explorer dev server. The browser only ever talks to this origin, so
// CORS is a non-issue in dev: the Vite server (Node) proxies /api onward.
//
// Unlike the editor, a single proxy rule is sufficient here — the explorer issues
// nothing but reads, so every route it uses lives on dataexplorer-backend. The
// editor needs two bases precisely because it mixes reads and writes over the
// same paths; see the devnote in curator-frontend/src/api/client.js.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

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
        '/api': {
          // Evaluated by the Vite dev server (Node), not the browser — so this
          // uses the Docker service name. Override with VITE_PROXY_TARGET when
          // running the backend elsewhere (e.g. http://localhost:8001 on host).
          target: env.VITE_PROXY_TARGET || 'http://dataexplorer-backend:8001',
          changeOrigin: true,
        },
      },
    },
  }
})
