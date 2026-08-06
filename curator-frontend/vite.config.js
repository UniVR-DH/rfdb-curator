import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  // Load environment variables from:
  // - process environment (Docker Compose)
  // - .env files (if present)
  //
  // The third argument '' means:
  //   load ALL variables, not just those prefixed with VITE_
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],

    server: {
      port: 5173,

      proxy: {
        '/api': {
          // ------------------------------------------------------------------
          // Proxy target (server-side, runs inside Docker)
          // ------------------------------------------------------------------
          // This is evaluated by the Vite dev server (Node.js), NOT the browser.
          //
          // Therefore:
          // - Must use Docker service name ("curator-backend")
          // - Must NOT use localhost (would point to this container)
          //
          // Resolution flow:
          //   Browser → Vite (/api)
          //   Vite → curator-backend container via proxy
          //
          target: env.VITE_PROXY_TARGET || 'http://curator-backend:8000',

          changeOrigin: true,

          // Optional but often useful if backend does not expect /api prefix
          // rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
  }
})
