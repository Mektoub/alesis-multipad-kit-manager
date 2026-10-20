// Analyse de l'interface : règles recommandées JavaScript et Svelte.
import js from "@eslint/js";
import svelte from "eslint-plugin-svelte";
import globals from "globals";

export default [
  { ignores: ["dist/", "node_modules/"] },
  js.configs.recommended,
  ...svelte.configs.recommended,
  {
    languageOptions: {
      // __APP_NAMES__ : noms de l'application, définis par vite.config.js
      globals: { ...globals.browser, __APP_NAMES__: "readonly" },
    },
    rules: {
      // `_` : variable volontairement ignorée, ex. {#each { length: n } as _, i}
      "no-unused-vars": ["error", { varsIgnorePattern: "^_", argsIgnorePattern: "^_" }],
    },
  },
];
