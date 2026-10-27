import assert from "node:assert/strict";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { after, describe, it } from "node:test";

import { DEFAULT_STATE, readWindowState, windowBounds, writeWindowState } from "../window-state.js";

const dir = mkdtempSync(path.join(tmpdir(), "window-state-"));
after(() => rmSync(dir, { recursive: true, force: true }));

describe("état de la fenêtre", () => {
  it("par défaut (fichier absent ou abîmé) : maximisée, 1400×900", () => {
    assert.deepEqual(readWindowState(path.join(dir, "absent.json")), DEFAULT_STATE);
    const bad = path.join(dir, "bad.json");
    for (const content of ["{pas du json", '{"width": -5, "height": 900}', '{"width": "grand"}']) {
      writeFileSync(bad, content);
      assert.deepEqual(readWindowState(bad), DEFAULT_STATE, content);
    }
  });

  it("écrit puis relu", () => {
    const file = path.join(dir, "sous-dossier", "window-state.json");
    writeWindowState(file, { x: 10, y: 20, width: 1000, height: 700 }, false);
    assert.deepEqual(readWindowState(file), { x: 10, y: 20, width: 1000, height: 700, maximized: false });
  });

  it("position gardée seulement si le haut de la fenêtre est sur un écran", () => {
    const screens = [
      { x: 0, y: 0, width: 1920, height: 1040 },
      { x: 1920, y: 0, width: 1280, height: 1024 },
    ];
    const at = (x, y) => windowBounds({ x, y, width: 1000, height: 700, maximized: false }, screens);
    assert.deepEqual(at(100, 50), { x: 100, y: 50, width: 1000, height: 700 });
    assert.deepEqual(at(2500, 100), { x: 2500, y: 100, width: 1000, height: 700 }); // second écran
    assert.deepEqual(at(3500, 100), { width: 1000, height: 700 }); // écran débranché : centrée
    assert.deepEqual(at(100, -500), { width: 1000, height: 700 }); // barre de titre hors écran
    assert.deepEqual(windowBounds(DEFAULT_STATE, screens), { width: 1400, height: 900 });
  });
});
