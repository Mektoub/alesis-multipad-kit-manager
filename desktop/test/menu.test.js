import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { menuTemplate } from "../menu.js";

const about = () => {};
const send = (name) => () => name;
const template = (platform) => menuTemplate({ platform, appName: "Alesis Kit Manager", about, send });
const labels = (menu) => menu.map((m) => m.label);
const items = (menu, label) => menu.find((m) => m.label === label).submenu;

describe("menu de l'application", () => {
  for (const platform of ["linux", "win32"]) {
    it(`${platform} : Fichier, Édition, Affichage, Aide ; Quitter et À propos présents`, () => {
      const menu = template(platform);
      assert.deepEqual(labels(menu), ["&Fichier", "É&dition", "&Affichage", "Ai&de"]);
      assert.ok(items(menu, "&Fichier").some((i) => i.role === "quit"));
      assert.equal(items(menu, "Ai&de")[0].click, about);
    });
  }

  it("macOS : menu de l'application en tête, sans doublons dans Fichier ni Aide", () => {
    const menu = template("darwin");
    assert.deepEqual(labels(menu), ["Alesis Kit Manager", "&Fichier", "É&dition", "&Affichage"]);
    const app = menu[0].submenu;
    assert.equal(app[0].label, "À propos de Alesis Kit Manager");
    assert.equal(app[0].click, about);
    assert.deepEqual(
      app.filter((i) => i.role).map((i) => i.role),
      ["hide", "hideOthers", "unhide", "quit"],
    );
    assert.equal(app.find((i) => i.role === "quit").accelerator, "Cmd+Q");
    const file = items(menu, "&Fichier");
    assert.ok(!file.some((i) => i.role === "quit"));
    assert.notEqual(file.at(-1).type, "separator"); // pas de séparateur orphelin
    assert.equal(file.length, 4);
  });

  it("Annuler / Rétablir passent par `send` ; raccourcis affichés, gérés par l'interface hors macOS", () => {
    for (const [platform, redo, registered] of [
      ["linux", "Ctrl+Y", false],
      ["win32", "Ctrl+Y", false],
      ["darwin", "Cmd+Shift+Z", true],
    ]) {
      const [undoItem, redoItem] = items(template(platform), "É&dition");
      assert.deepEqual([undoItem.click(), redoItem.click()], ["undo", "redo"], platform);
      assert.deepEqual([undoItem.accelerator, redoItem.accelerator], ["CmdOrCtrl+Z", redo], platform);
      assert.deepEqual([undoItem.registerAccelerator, redoItem.registerAccelerator], [registered, registered]);
      assert.ok(!undoItem.role && !redoItem.role, platform);
    }
  });

  it("Préférences… : Édition hors macOS, menu de l'application sous macOS", () => {
    const linux = items(template("linux"), "É&dition").at(-1);
    assert.deepEqual([linux.click(), linux.accelerator], ["preferences", "CmdOrCtrl+,"]);
    const mac = template("darwin");
    assert.ok(mac[0].submenu.some((i) => i.click?.() === "preferences"));
    assert.ok(!items(mac, "É&dition").some((i) => i.click?.() === "preferences"));
  });

  it("Ouvrir récent : un élément par fichier, puis Effacer la liste", () => {
    const openRecent = (file) => () => `ouvrir ${file}`;
    const menu = menuTemplate({ platform: "linux", appName: "A", about, send, recent: ["/a.bkf", "/b.fac"], openRecent });
    const sub = items(menu, "&Fichier").find((i) => i.label === "Ouvrir &récent").submenu;
    assert.deepEqual(
      sub.filter((i) => i.click).map((i) => i.click()),
      ["ouvrir /a.bkf", "ouvrir /b.fac", "clear-recent"],
    );
    const empty = items(template("linux"), "&Fichier").find((i) => i.label === "Ouvrir &récent").submenu;
    assert.deepEqual(empty, [{ label: "Aucun fichier récent", enabled: false }]);
  });

  it("les commandes de Fichier passent par `send`", () => {
    const file = items(template("linux"), "&Fichier");
    assert.deepEqual(
      file.filter((i) => i.click).map((i) => i.click()),
      ["open", "save", "save-as"],
    );
  });
});
