import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: VITE_API_BASE_URL,
        changeOrigin: true,
      },
      '/media': {
        target: VITE_API_BASE_URL,
        changeOrigin: true,
      }
    }
  }
})
