import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// Build/dev configuration only — no application logic.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    // Proxy API calls to the FastAPI backend (API connection structure).
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        // Forward WebSocket upgrades too (Stage 4.7 wake-word /voice/ws).
        ws: true,
      },
    },
  },
});
