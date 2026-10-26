// Captures d'écran de la documentation (docs/images/), prises dans l'application
// de bureau (Playwright, Electron du dépôt) sur une copie de la sauvegarde de
// référence des tests : ./dev.sh screenshots les régénère après un changement
// de l'interface.
//
// Rendu fixe : thème clair, zone de la fenêtre de 1400×900, échelle 1. Les
// fenêtres de dialogue sont rognées sur leur contenu, avec une marge.
//
// Prérequis : .venv et interface construite (./dev.sh screenshots les prépare).
// La fenêtre s'affiche le temps des captures : ne pas taper au clavier pendant
// ce temps. Sous Linux sans affichage : xvfb-run.

import { copyFileSync, mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import electronPath from "electron";
import { _electron as electron } from "playwright-core";

const here = path.dirname(fileURLToPath(import.meta.url));
const desktop = path.resolve(here, "..");
const reference = path.resolve(desktop, "..", "tests", "ressources", "Backup001.bkf");
const out = path.resolve(process.argv[2] ?? path.join(desktop, "..", "docs", "images"));

const WIDTH = 1400;
const HEIGHT = 900;
const MARGIN = 16; // autour d'une fenêtre de dialogue rognée

// Dossier personnel temporaire : la sauvegarde y est dans la zone autorisée par
// défaut, et la configuration de l'application (~/.config) y reste. Nom fixe :
// le chemin de la sauvegarde est affiché dans la colonne des kits.
const home = path.join(tmpdir(), "alesis-kit-manager");
rmSync(home, { recursive: true, force: true });
mkdirSync(path.join(home, "Sauvegardes"), { recursive: true });
const file = path.join(home, "Sauvegardes", "Backup001.bkf");
copyFileSync(reference, file);
mkdirSync(out, { recursive: true });

const app = await electron.launch({
  executablePath: electronPath,
  args: ["--force-device-scale-factor=1", desktop, file],
  cwd: desktop,
  env: { ...process.env, HOME: home, USERPROFILE: home, XDG_CONFIG_HOME: path.join(home, ".config") },
});

try {
  const page = await app.firstWindow();
  await page.getByRole("button", { name: /031\s*WhereIs/ }).waitFor();
  // la fenêtre s'ouvre maximisée : la taille ne se fixe qu'une fois restaurée
  await app.evaluate(({ BrowserWindow, nativeTheme }) => {
    nativeTheme.themeSource = "light";
    BrowserWindow.getAllWindows()[0].unmaximize();
  });
  await page.waitForTimeout(500);
  await app.evaluate(
    ({ BrowserWindow }, [width, height]) => BrowserWindow.getAllWindows()[0].setContentSize(width, height),
    [WIDTH, HEIGHT],
  );
  await page.waitForFunction(([w, h]) => globalThis.innerWidth === w && globalThis.innerHeight === h, [WIDTH, HEIGHT]);

  const button = (name) => page.getByRole("button", { name, exact: true });
  const close = async () => {
    await page.keyboard.press("Escape");
    await page.locator(".backdrop").waitFor({ state: "detached" });
  };

  // Fenêtre entière, ou zone autour des éléments donnés (union de leurs cadres).
  async function shot(name, ...locators) {
    const target = path.join(out, `${name}.png`);
    await page.mouse.move(0, HEIGHT - 1); // pas de survol ni d'infobulle
    await page.waitForTimeout(300); // fin des transitions
    if (!locators.length) return page.screenshot({ path: target });
    const boxes = await Promise.all(locators.map((l) => l.boundingBox()));
    const x = Math.max(0, Math.min(...boxes.map((b) => b.x)) - MARGIN);
    const y = Math.max(0, Math.min(...boxes.map((b) => b.y)) - MARGIN);
    const right = Math.min(WIDTH, Math.max(...boxes.map((b) => b.x + b.width)) + MARGIN);
    const bottom = Math.min(HEIGHT, Math.max(...boxes.map((b) => b.y + b.height)) + MARGIN);
    return page.screenshot({ path: target, clip: { x, y, width: right - x, height: bottom - y } });
  }
  const dialog = () => page.locator(".dialog");

  // Vue d'ensemble : kit d'usine « Ham & Beans », pad P1
  await page.getByRole("button", { name: /040\s*Ham & Beans/ }).click();
  const kitName = page.getByRole("textbox", { name: "Nom" });
  while ((await kitName.inputValue()) !== "Ham & Beans") await page.waitForTimeout(50);
  await shot("overview");

  // Fenêtres d'action du pad et du kit
  for (const [label, name] of [
    ["Copier vers…", "copy-dialog"],
    ["Valeurs par défaut…", "reset-dialog"],
    ["Modifier plusieurs pads…", "bulk-edit-dialog"],
    ["Déplacer / copier le kit…", "kit-transfer-dialog"],
  ]) {
    await button(label).click();
    await shot(name, dialog());
    await close();
  }

  // Choix d'un sample (wave A du pad affiché)
  await page.getByTitle("Choisir un sample").first().click();
  await shot("sample-picker", dialog());
  await close();

  // Historique : trois modifications, une annulée, puis la liste déroulante
  await kitName.fill("Ham & Beans 2");
  await page.waitForTimeout(2000); // étapes distinctes (envois rapprochés fusionnés)
  await page.getByRole("combobox").first().selectOption({ index: 2 });
  await page.waitForTimeout(2000);
  await page.locator("input[type=range]").nth(1).fill("10");
  await page.waitForTimeout(2000);
  await kitName.blur();
  await page.getByRole("button", { name: "Annuler", exact: true }).click();
  await page.waitForTimeout(500);
  await page.locator(".toast button").click(); // message de l'annulation fermé
  await page.getByRole("button", { name: "Historique" }).click();
  const menu = page.getByRole("menu", { name: "Historique des modifications" });
  await shot("history-menu", menu, page.getByRole("button", { name: "Annuler", exact: true }));
  await page.keyboard.press("Escape");

  // Alerte avant une action hors historique (suppression du kit)
  await button("Supprimer le kit…").click();
  await shot("history-alert", page.getByRole("alertdialog"));
  await page.getByRole("alertdialog").getByRole("button", { name: "Annuler" }).click();

  console.log(`Captures enregistrées dans ${out}`);
} finally {
  // Les captures ont modifié la sauvegarde : à la fermeture, la boîte « Des
  // modifications ne sont pas enregistrées » reçoit d'office « Quitter sans
  // enregistrer » (bouton 1) au lieu d'attendre une réponse.
  await app
    .evaluate(({ dialog }) => {
      dialog.showMessageBox = async () => ({ response: 1, checkboxChecked: false });
    })
    .catch(() => {});
  await app.close();
  rmSync(home, { recursive: true, force: true });
}
