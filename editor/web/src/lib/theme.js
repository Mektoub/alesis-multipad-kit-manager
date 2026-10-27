// Thème de l'interface (préférence `theme`) : "light" ou "dark" fixent l'attribut
// data-theme de la page (voir app.css) ; "system" le retire, la page suit
// alors le réglage du système (prefers-color-scheme).

export function applyTheme(theme, root = document.documentElement) {
  if (theme === "light" || theme === "dark") root.dataset.theme = theme;
  else delete root.dataset.theme;
}
