import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // VITE_BASE_PATH: 本番ビルドのサブパス指定 (例: /sns/)
  // 未設定時は '/' (standalone モード)
  base: process.env.VITE_BASE_PATH || '/',
  server: {
    // dev server: /posts /profiles /uploads /storage → ローカルサービスに転送
    proxy: {
      '/posts': { target: 'http://localhost:8000', changeOrigin: true },
      '/profiles': { target: 'http://localhost:8000', changeOrigin: true },
      '/uploads': { target: 'http://localhost:8000', changeOrigin: true },
      '/health': { target: 'http://localhost:8000', changeOrigin: true },
      // MinIO 画像プロキシ—プレサインド URL の /storage/{bucket}/{key}を
      // フロントエンド開発時に直接 MinIO へ転送する
      '/storage': { target: 'http://localhost:9000', changeOrigin: true,
        rewrite: (path) => path.replace(/^\/storage/, '') },
    },
  },
  test: {
    // Vitest 設定
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      exclude: ['src/test/**', 'src/main.tsx', 'src/vite-env.d.ts'],
    },
  },
})
