import { describe, expect, it } from "vitest";
import { applyTheme } from "./theme.js";

describe("applyTheme", () => {
  it("clair ou sombre : attribut data-theme ; système : attribut retiré", () => {
    const root = document.createElement("html");
    applyTheme("dark", root);
    expect(root.getAttribute("data-theme")).toBe("dark");
    applyTheme("light", root);
    expect(root.getAttribute("data-theme")).toBe("light");
    applyTheme("system", root);
    expect(root.hasAttribute("data-theme")).toBe(false);
  });
});
