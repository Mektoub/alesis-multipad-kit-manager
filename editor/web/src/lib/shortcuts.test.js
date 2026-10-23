import { describe, expect, it } from "vitest";

import { isTextField, shortcut } from "./shortcuts.js";

const key = (k, mods = {}) => ({ key: k, ctrlKey: false, metaKey: false, shiftKey: false, altKey: false, ...mods });

describe("raccourcis Annuler / Rétablir", () => {
  it("Ctrl+Z annule ; Ctrl+Y et Ctrl+Maj+Z rétablissent ; Cmd comme Ctrl", () => {
    expect(shortcut(key("z", { ctrlKey: true }))).toBe("undo");
    expect(shortcut(key("y", { ctrlKey: true }))).toBe("redo");
    expect(shortcut(key("Z", { ctrlKey: true, shiftKey: true }))).toBe("redo");
    expect(shortcut(key("z", { metaKey: true }))).toBe("undo");
    expect(shortcut(key("z", { metaKey: true, shiftKey: true }))).toBe("redo");
  });

  it("autres touches ignorées", () => {
    expect(shortcut(key("z"))).toBeNull();
    expect(shortcut(key("z", { ctrlKey: true, altKey: true }))).toBeNull();
    expect(shortcut(key("y", { ctrlKey: true, shiftKey: true }))).toBeNull();
    expect(shortcut(key("s", { ctrlKey: true }))).toBeNull();
  });

  it("champs de saisie : ceux où l'on tape du texte", () => {
    const el = (html) => {
      document.body.innerHTML = html;
      return document.body.firstElementChild;
    };
    expect(isTextField(el('<input type="text">'))).toBe(true);
    expect(isTextField(el('<input type="number">'))).toBe(true);
    expect(isTextField(el("<input>"))).toBe(true);
    expect(isTextField(el("<textarea></textarea>"))).toBe(true);
    expect(isTextField(el('<input type="range">'))).toBe(false);
    expect(isTextField(el('<input type="checkbox">'))).toBe(false);
    expect(isTextField(el("<select></select>"))).toBe(false);
    expect(isTextField(el("<button></button>"))).toBe(false);
    expect(isTextField(null)).toBe(false);
  });
});
