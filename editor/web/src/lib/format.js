// Affichage des valeurs : libellés, pan L/C/R, Off.

export function formatValue(def, v) {
  if (v == null) return "";
  if (def.labels) return def.labels[v] ?? `Valeur ${v}`;
  if (def.name === "pan") return v === 15 ? "C" : v < 15 ? `L${15 - v}` : `R${v - 15}`;
  if ((def.name === "fixed_level" || def.name?.startsWith("fade_")) && v === 0) return "Off";
  return String(v);
}

// Infobulle : description, puis valeur par défaut de l'emplacement affiché.
export function tooltip(description, def, defaultValue) {
  if (defaultValue == null) return description ?? "";
  return `${description ?? ""}\nPar défaut : ${formatValue(def, defaultValue)}`;
}
