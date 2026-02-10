import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true, // Listen on all addresses
    // Use API base from env when running in Docker, fallback to localhost
    // e.g., VITE_API_BASE_URL=http://backend:8000
    proxy: {
      '/api': {
        target: process.env.VITE_API_BASE_URL || 'http://backend:8000',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path,
      },
      '/health': {
        target: process.env.VITE_API_BASE_URL || 'http://backend:8000',
        changeOrigin: true,
        secure: false,
      },
      '/keyframe': {
        target: process.env.VITE_API_BASE_URL || 'http://backend:8000',
        changeOrigin: true,
        secure: false,
      }
    },
    watch: {
      usePolling: true, // Required for Docker hot-reload
      interval: 1000, // Poll interval in ms
    },
    hmr: {
      host: 'localhost', // HMR host
      port: 3000,
    },
  }
})

