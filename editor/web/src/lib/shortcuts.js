// Raccourcis Annuler / Rétablir : Ctrl+Z ; Ctrl+Y ou Ctrl+Maj+Z (Cmd sous macOS).
//
// Dans un champ de saisie, les raccourcis restent ceux du champ (annulation de
// la frappe) : seules les autres zones de la page annulent les modifications.

const NOT_TEXT = new Set(["button", "checkbox", "color", "file", "radio", "range", "reset", "submit"]);

export const isMac = typeof navigator !== "undefined" && /^Mac/.test(navigator.platform);

// L'élément est-il un champ où l'on tape du texte ?
export function isTextField(el) {
  if (!el) return false;
  if (el.isContentEditable || el.tagName === "TEXTAREA") return true;
  return el.tagName === "INPUT" && !NOT_TEXT.has(el.type);
}

// "undo", "redo" ou null pour un événement keydown.
export function shortcut(e) {
  if (!(e.ctrlKey || e.metaKey) || e.altKey) return null;
  const key = e.key.toLowerCase();
  if (key === "z") return e.shiftKey ? "redo" : "undo";
  if (key === "y" && !e.shiftKey) return "redo";
  return null;
}

// Libellés des infobulles.
export const SHORTCUTS = isMac
  ? { undo: "⌘Z", redo: "⌘⇧Z ou ⌘Y" }
  : { undo: "Ctrl+Z", redo: "Ctrl+Y ou Ctrl+Maj+Z" };
