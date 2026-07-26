import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// Read-only Explorer dev server. Mirrors the editor frontend's proxy setup so
// the browser only ever talks to this origin and CORS is a non-issue in dev:
// the Vite server (Node) proxies /api to the backend container.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],
    server: {
      port: 5174,
      proxy: {
        '/api': {
          // Evaluated by the Vite dev server (Node), not the browser — so this
          // uses the Docker service name. Override with VITE_PROXY_TARGET when
          // running the backend elsewhere (e.g. http://localhost:8000 on host).
          target: env.VITE_PROXY_TARGET || 'http://backend:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
