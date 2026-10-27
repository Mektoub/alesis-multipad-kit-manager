import { describe, expect, it } from "vitest";

import { LANGUAGES, resolveLanguage, translate } from "./i18n.js";
import { MESSAGES } from "./messages.js";

const placeholders = (text) => [...JSON.stringify(text).matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

describe("langue de l'interface", () => {
  it("préférence : langue choisie, ou celle du système (français, sinon anglais)", () => {
    expect(resolveLanguage("fr", ["en-US"])).toBe("fr");
    expect(resolveLanguage("en", ["fr-FR"])).toBe("en");
    expect(resolveLanguage("system", ["fr-FR", "en"])).toBe("fr");
    expect(resolveLanguage("system", ["en-GB", "fr"])).toBe("en");
    expect(resolveLanguage("system", ["de-DE", "fr"])).toBe("en");
    expect(resolveLanguage("system", [])).toBe("en");
  });

  it("mêmes textes et mêmes valeurs insérées dans les deux langues", () => {
    expect(LANGUAGES).toEqual(Object.keys(MESSAGES));
    expect(Object.keys(MESSAGES.fr).sort()).toEqual(Object.keys(MESSAGES.en).sort());
    for (const key of Object.keys(MESSAGES.en)) {
      expect(placeholders(MESSAGES.fr[key]), key).toEqual(placeholders(MESSAGES.en[key]));
      expect(typeof MESSAGES.fr[key], key).toBe(typeof MESSAGES.en[key]);
    }
  });

  it("valeurs insérées, pluriel selon n, clé inconnue", () => {
    expect(translate("fr", "kitMoved", { source: "001", target: "005" })).toBe("Kit 001 déplacé en 005.");
    expect(translate("en", "kitMoved", { source: "001", target: "005" })).toBe("Kit 001 moved to 005.");
    expect(translate("en", "recentCount", { n: 1 })).toBe("1 recent file");
    expect(translate("en", "recentCount", { n: 0 })).toBe("0 recent files");
    expect(translate("fr", "recentCount", { n: 0 })).toBe("0 fichier récent");
    expect(translate("fr", "recentCount", { n: 3 })).toBe("3 fichiers récents");
    expect(translate("fr", "inconnue")).toBe("inconnue");
  });
});
