import { fileURLToPath, URL } from "node:url";

import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vitest/config";

// The API base. In dev we proxy /v1, /health and /metrics to the local API
// (uvicorn on :8000 via `make run`) so the browser never hits a cross-origin
// wall. In other environments set VITE_API_BASE to an absolute origin and the
// typed client talks to it directly (see src/api/client.ts).
const API_TARGET = process.env.VITE_API_PROXY ?? "http://localhost:8000";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/v1": { target: API_TARGET, changeOrigin: true },
      "/health": { target: API_TARGET, changeOrigin: true },
      "/metrics": { target: API_TARGET, changeOrigin: true },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    include: ["src/**/*.{test,spec}.ts"],
    setupFiles: ["./vitest.setup.ts"],
  },
});
