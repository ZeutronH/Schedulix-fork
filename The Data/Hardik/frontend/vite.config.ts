import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "fs";

const inDocker = fs.existsSync("/.dockerenv");
const defaultBackend = inDocker ? "http://backend:8000" : "http://127.0.0.1:8000";
const backendUrl = process.env.VITE_BACKEND_URL || defaultBackend;
const frontendPort = inDocker ? 5173 : parseInt(process.env.PORT || "5173", 10);

export default defineConfig({
  plugins: [react()],
  cacheDir: "/tmp/schedulix_vite_cache",

  server: {
    host: "0.0.0.0",
    port: frontendPort,
    strictPort: false,

    proxy: {
      "/api": {
        target: backendUrl,
        changeOrigin: true,
      },

      "/media": {
        target: backendUrl,
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      input: {
        main: "index.html",
        student: "student.html",
        faculty: "faculty.html",
      },
    },
  },
});
