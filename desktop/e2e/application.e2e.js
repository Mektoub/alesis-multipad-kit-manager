// Test de bout en bout de l'application de bureau (Playwright, Electron du
// dépôt) : ouvre une copie de la sauvegarde de référence passée en argument,
// modifie le nom d'un kit, enregistre par le menu, relance l'application sur le
// fichier enregistré ; fermeture avec des modifications non enregistrées.
//
// Prérequis : .venv et interface construite (./dev.sh e2e les prépare), ou un
// serveur figé désigné par KITMANAGER_SERVER. Sous Linux sans affichage :
// xvfb-run. Les boîtes de dialogue natives sont remplacées dans le processus
// principal, sans affichage.

import assert from "node:assert/strict";
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { after, before, describe, it } from "node:test";
import { fileURLToPath } from "node:url";

import electronPath from "electron";
import { _electron as electron } from "playwright-core";

const here = path.dirname(fileURLToPath(import.meta.url));
const desktop = path.resolve(here, "..");
const names = JSON.parse(readFileSync(path.resolve(desktop, "..", "app-names.json"), "utf8"));
const reference = path.resolve(desktop, "..", "tests", "ressources", "Backup001.bkf");

// Dossier personnel temporaire : la sauvegarde y est dans la zone autorisée par
// défaut, et la configuration de l'application (~/.config) y reste. Interface
// en français (préférence `language`), quelle que soit la langue du système.
let home;
let file;
before(() => {
  home = mkdtempSync(path.join(tmpdir(), "kitmanager-e2e-"));
  mkdirSync(path.join(home, "Sauvegardes"));
  file = path.join(home, "Sauvegardes", "Backup001.bkf");
  const config = path.join(home, ".config", names.config);
  mkdirSync(config, { recursive: true });
  writeFileSync(path.join(config, "preferences.json"), JSON.stringify({ language: "fr" }));
});
after(() => rmSync(home, { recursive: true, force: true }));

function launch(target) {
  return electron.launch({
    executablePath: electronPath,
    args: [desktop, target],
    cwd: desktop,
    env: { ...process.env, HOME: home, USERPROFILE: home, XDG_CONFIG_HOME: path.join(home, ".config") },
  });
}

// Fenêtre de l'application, sauvegarde ouverte (premier kit non vide : 031 WhereIs).
async function opened(app) {
  const page = await app.firstWindow();
  await page.getByRole("button", { name: /031\s*WhereIs/ }).waitFor();
  return page;
}

// Remplace la boîte de dialogue de fermeture : `response` est l'indice du bouton
// (0 Enregistrer, 1 Quitter sans enregistrer, 2 Annuler) ; les messages
// affichés sont comptés dans globalThis.e2eDialogs.
function answerDialogs(app, response) {
  return app.evaluate(({ dialog }, response) => {
    globalThis.e2eDialogs ??= [];
    dialog.showMessageBox = async (_win, options) => {
      globalThis.e2eDialogs.push(options.message);
      return { response, checkboxChecked: false };
    };
  }, response);
}

const dialogs = (app) => app.evaluate(() => globalThis.e2eDialogs ?? []);
const closeWindow = (app) => app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0]?.close());
// Clic sur Fichier › `label` du menu de l'application.
const menu = (app, label) =>
  app.evaluate(({ Menu }, label) => {
    const item = Menu.getApplicationMenu()
      .items.flatMap((m) => m.submenu?.items ?? [])
      .find((i) => i.label.replaceAll("&", "") === label);
    item.click();
  }, label);

// Attend que `check()` soit vrai (5 s au plus).
async function until(check, timeoutMs = 5000) {
  const end = Date.now() + timeoutMs;
  while (!(await check())) {
    if (Date.now() > end) throw new Error("délai dépassé");
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
}

function exited(app) {
  const child = app.process();
  if (child.exitCode !== null || child.signalCode !== null) return Promise.resolve(child.exitCode);
  return new Promise((resolve) => child.once("exit", (code) => resolve(code)));
}

describe("application de bureau", { timeout: 60000 }, () => {
  it("ouvre, modifie, enregistre par le menu et relit la sauvegarde", async () => {
    copyFileSync(reference, file);
    const app = await launch(file);
    try {
      const page = await opened(app);
      assert.equal(await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].getTitle()), names.long);
      await page.getByRole("textbox", { name: "Nom" }).fill("E2eTest");
      await page.getByText("Modifications non enregistrées").waitFor();
      await menu(app, "Enregistrer");
      await page.getByText(`Enregistré dans ${file}`).waitFor();
      await page.getByText("À jour").waitFor();
    } finally {
      await app.close();
    }
    // copie .bak de l'original au premier enregistrement
    assert.deepEqual(readFileSync(`${file}.1.bak`), readFileSync(reference));
    assert.notDeepEqual(readFileSync(file), readFileSync(reference));

    const again = await launch(file);
    try {
      const page = await again.firstWindow();
      await page.getByRole("button", { name: /031\s*E2eTest/ }).waitFor();
      assert.equal(await page.getByRole("textbox", { name: "Nom" }).inputValue(), "E2eTest");
    } finally {
      await again.close();
    }
  });

  it("demande confirmation avant de fermer avec des modifications non enregistrées", async () => {
    copyFileSync(reference, file);
    rmSync(`${file}.1.bak`, { force: true });
    const app = await launch(file);
    try {
      const page = await opened(app);
      await page.getByRole("textbox", { name: "Nom" }).fill("Abandon");
      await page.getByText("Modifications non enregistrées").waitFor();

      await answerDialogs(app, 2); // Annuler : la fenêtre reste ouverte
      await closeWindow(app);
      await until(async () => (await dialogs(app)).length > 0);
      assert.deepEqual(await dialogs(app), ["Des modifications ne sont pas enregistrées."]);
      await page.getByText("Modifications non enregistrées").waitFor(); // la fenêtre répond toujours
      assert.equal(await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows().length), 1);

      await answerDialogs(app, 1); // Quitter sans enregistrer
      const done = exited(app);
      await closeWindow(app);
      await done;
    } finally {
      await app.close().catch(() => {});
    }
    assert.deepEqual(readFileSync(file), readFileSync(reference), "fichier modifié sans enregistrement");
    assert.equal(existsSync(`${file}.1.bak`), false);
  });
});
