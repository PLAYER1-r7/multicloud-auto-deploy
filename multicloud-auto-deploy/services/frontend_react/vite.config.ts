import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // VITE_BASE_PATH: 本番ビルドのサブパス指定 (例: /sns/)
  // 未設定時は '/' (standalone モード)
  base: process.env.VITE_BASE_PATH || '/',
  server: {
    // dev server: /posts /profiles /uploads → API (localhost:8000)
    proxy: {
      '/posts': { target: 'http://localhost:8000', changeOrigin: true },
      '/profiles': { target: 'http://localhost:8000', changeOrigin: true },
      '/uploads': { target: 'http://localhost:8000', changeOrigin: true },
      '/health': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
