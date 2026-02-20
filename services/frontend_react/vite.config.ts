import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// base: '/sns/' ensures asset paths are /sns/assets/... when served under /sns/ prefix
export default defineConfig({
  plugins: [react()],
  base: '/sns/',
})
