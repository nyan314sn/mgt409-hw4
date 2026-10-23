import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Same-origin /api calls keep the HttpOnly session cookie simple (no CORS).
    // xfwd adds X-Forwarded-For, so the API can apply per-network-address limits.
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', xfwd: true },
      '/data/products': { target: 'http://127.0.0.1:8000', xfwd: true }, // product photos
    },
  },
})
