import { readFileSync } from "node:fs";
import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

// Noms de l'application (../../app-names.json) : __APP_NAMES__ dans le code,
// %APP_LONG_NAME% dans index.html.
const names = JSON.parse(readFileSync(new URL("../../app-names.json", import.meta.url), "utf8"));

// En développement, `npm run dev` relaie /api vers le serveur FastAPI (python -m editor).
export default defineConfig({
  plugins: [
    svelte(),
    { name: "app-names", transformIndexHtml: (html) => html.replaceAll("%APP_LONG_NAME%", names.long) },
  ],
  define: { __APP_NAMES__: JSON.stringify(names) },
  server: {
    proxy: { "/api": "http://127.0.0.1:8765" },
  },
  build: { outDir: "dist", emptyOutDir: true },
});
