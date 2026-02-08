import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import viteCompression from 'vite-plugin-compression'

export default defineConfig({
  plugins: [
    react(),
    // Gzip圧縮を有効化
    viteCompression({
      algorithm: 'gzip',
      ext: '.gz',
      threshold: 10240, // 10KB以上のファイルを圧縮
      deleteOriginFile: false,
    }),
    // Brotli圧縮も追加（より高圧縮率）
    viteCompression({
      algorithm: 'brotliCompress',
      ext: '.br',
      threshold: 10240,
      deleteOriginFile: false,
    }),
  ],
  root: 'frontend',
  build: {
    outDir: '../dist-frontend',
    emptyOutDir: true,
    // ソースマップを本番環境では無効化（セキュリティ向上）
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          // React関連を分割
          'react-vendor': ['react', 'react-dom', 'react-hot-toast'],
          // その他のユーティリティ
          'utils-vendor': [
            '@tanstack/react-query',
            'date-fns',
            'linkify-react',
            'linkifyjs',
            'react-icons',
            'react-use',
            'clsx',
            'immer',
            'nanoid',
            'zod',
          ],
        },
      },
    },
    // チャンクサイズ警告の閾値を上げる (1MB)
    chunkSizeWarningLimit: 1000,
  },
  server: {
    port: 3000,
    proxy: {
      '/posts': {
        target: 'https://br7ubkaet1.execute-api.ap-northeast-1.amazonaws.com/prod',
        changeOrigin: true,
        secure: true,
        rewrite: (path) => path
      }
    }
  }
})
