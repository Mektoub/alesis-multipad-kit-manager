// Analyse de l'application de bureau : règles recommandées JavaScript.
import js from "@eslint/js";
import globals from "globals";

export default [
  { ignores: ["node_modules/", "dist/", "build/"] },
  js.configs.recommended,
  {
    languageOptions: { globals: { ...globals.node } },
    rules: {
      "no-unused-vars": ["error", { varsIgnorePattern: "^_", argsIgnorePattern: "^_" }],
    },
  },
  { files: ["**/*.cjs"], languageOptions: { sourceType: "commonjs" } },
];
