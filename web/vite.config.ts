import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

const API_ORIGIN = 'http://127.0.0.1:8080'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // One .env at the repository root serves the API, the eval suite and the web app;
  // only VITE_* variables reach the browser.
  envDir: '..',
  server: {
    port: 5173,
    // `make dev` runs two processes; proxying keeps the browser on one origin, as in production.
    proxy: {
      '/api': API_ORIGIN,
      '/healthz': API_ORIGIN,
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
  },
})
