import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // VITE_BASE_PATH: must be set to /sns/ when building for AWS/Azure/GCP staging deployment
  // e.g.  VITE_BASE_PATH=/sns/ npm run build
  // Omit (defaults to '/') for local dev server only
  base: process.env.VITE_BASE_PATH || "/",
  server: {
    // dev server: proxy API paths to local backend
    proxy: {
      "/posts": { target: "http://localhost:8000", changeOrigin: true },
      "/profile": { target: "http://localhost:8000", changeOrigin: true },
      "/uploads": { target: "http://localhost:8000", changeOrigin: true },
      "/health": { target: "http://localhost:8000", changeOrigin: true },
      "/storage": {
        target: "http://localhost:9000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/storage/, ""),
      },
    },
  },
  // Remove tailwind/postcss — we use app.css from frontend_web directly
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      exclude: ["src/test/**", "src/main.tsx", "src/vite-env.d.ts"],
    },
  },
});
