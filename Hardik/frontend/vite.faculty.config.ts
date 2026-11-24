import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "fs";

const inDocker = fs.existsSync("/.dockerenv");
const defaultBackend = inDocker ? "http://backend:8000" : "http://127.0.0.1:8000";
const backendUrl = process.env.VITE_BACKEND_URL || defaultBackend;

export default defineConfig({
  plugins: [
    react(),
    {
      name: "rewrite-root-to-faculty",
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          if (req.url === "/" || req.url === "/index.html") {
            req.url = "/faculty.html";
          }
          next();
        });
      },
    },
  ],
  cacheDir: "/tmp/schedulix_vite_faculty_cache",

  server: {
    host: "0.0.0.0",
    port: 5175,
    strictPort: true,

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
      input: "faculty.html",
    },
  },
});
