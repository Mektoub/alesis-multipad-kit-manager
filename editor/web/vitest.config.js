// Tests de l'interface (npm test) : environnement navigateur simulé par jsdom.
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: { environment: "jsdom", include: ["src/**/*.test.js"] },
});
