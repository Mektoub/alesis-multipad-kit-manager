// Tests de l'interface (npm test) : environnement navigateur simulé par jsdom.
// Le greffon Svelte compile les modules .svelte.js (runes), comme locale.svelte.js.
import { defineConfig } from "vitest/config";
import { svelte } from "@sveltejs/vite-plugin-svelte";

export default defineConfig({
  plugins: [svelte()],
  resolve: { conditions: ["browser"] },
  test: { environment: "jsdom", include: ["src/**/*.test.js"] },
});
