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
    assert.equal(file.length, 3);
  });

  it("les commandes de Fichier passent par `send`", () => {
    const file = items(template("linux"), "&Fichier");
    assert.deepEqual(
      file.filter((i) => i.click).map((i) => i.click()),
      ["open", "save", "save-as"],
    );
  });
});
