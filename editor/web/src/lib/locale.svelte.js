// Langue en cours de l'interface, réactive : les textes affichés avec t() se
// mettent à jour quand elle change (setLanguage, depuis les préférences).
// Elle est aussi envoyée au serveur (api.js) pour ses messages.

import { resolveLanguage, translate } from "./i18n.js";

const current = $state({ lang: resolveLanguage("system") });
document.documentElement.lang = current.lang;

export function language() {
  return current.lang;
}

export function setLanguage(lang) {
  current.lang = lang;
  document.documentElement.lang = lang;
}

export function t(key, params) {
  return translate(current.lang, key, params);
}
