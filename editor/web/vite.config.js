import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

// En développement, `npm run dev` relaie /api vers le serveur FastAPI (python -m editor).
export default defineConfig({
  plugins: [svelte()],
  server: {
    proxy: { "/api": "http://127.0.0.1:8765" },
  },
  build: { outDir: "dist", emptyOutDir: true },
});
