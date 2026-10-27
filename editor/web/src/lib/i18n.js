// Langue de l'interface : anglais ou français (préférence `language`, voir
// editor/preferences.py). "system" suit la langue du navigateur ou du système :
// français s'il est en tête des langues préférées, anglais sinon.
//
// Fonctions sans état, testables ; la langue en cours, réactive, est dans
// locale.svelte.js.

import { MESSAGES } from "./messages.js";

export const LANGUAGES = ["en", "fr"];

// Langue effective de la préférence `pref` ("system", "en" ou "fr").
export function resolveLanguage(pref, languages = navigator.languages ?? [navigator.language]) {
  if (LANGUAGES.includes(pref)) return pref;
  const first = (languages[0] ?? "").slice(0, 2).toLowerCase();
  return LANGUAGES.includes(first) ? first : "en";
}

// Texte `key` dans la langue `lang`, avec les valeurs de `params` ({nom}) ;
// un texte { one, other } est choisi selon params.n. Clé absente : en anglais,
// sinon la clé elle-même.
export function translate(lang, key, params = {}) {
  let text = MESSAGES[lang]?.[key] ?? MESSAGES.en[key] ?? key;
  if (typeof text === "object") text = text[new Intl.PluralRules(lang).select(params.n)] ?? text.other;
  return text.replace(/\{(\w+)\}/g, (match, name) => (name in params ? String(params[name]) : match));
}
