import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    proxy: {
      // Vaibhav's triage API
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
      // Jaspreet's VulnArena environment API (now served by vaibhav's backend)
      '/reset': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
      '/step': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
      '/state': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
    },
  },
})
