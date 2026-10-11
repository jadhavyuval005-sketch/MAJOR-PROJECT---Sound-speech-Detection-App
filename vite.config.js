import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the Flask API runs on :5000; /api calls are proxied to it,
// so the browser sees one origin and no CORS setup is needed.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://localhost:5000" } },
});
