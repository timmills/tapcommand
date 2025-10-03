import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://100.93.158.19:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  }
})
