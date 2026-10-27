// Processus principal de l'application de bureau : lance le serveur Python de
// l'éditeur avec un jeton aléatoire, ouvre la fenêtre sur ce serveur, fournit
// les boîtes de dialogue natives et le menu, confirme la fermeture quand des
// modifications ne sont pas enregistrées, et arrête le serveur en quittant.
//
// En développement : ./dev.sh start [--frozen] [FICHIER], ou npm start [-- FICHIER]
// une fois le venv et l'interface prêts (Python du .venv du dépôt, ou le serveur
// figé désigné par KITMANAGER_SERVER).
//
// Les préférences (preferences.json) sont gérées par le serveur, dans le dossier
// de configuration de l'application (KITMANAGER_CONFIG) ; la taille et la
// position de la fenêtre sont gardées ici (window-state.js). Les menus et les
// boîtes de dialogue suivent la langue de l'interface (messages.js).

import { randomBytes } from "node:crypto";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { app, BrowserWindow, dialog, ipcMain, Menu, screen, shell } from "electron";

import { menuTemplate } from "./menu.js";
import { LANGUAGES, languagePreference, resolveLanguage, translator } from "./messages.js";
import { fileArgument, serverCommand, serverProblem, startServer } from "./server.js";
import { readWindowState, windowBounds, writeWindowState } from "./window-state.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const PROJECT = path.resolve(here, "..");
// Noms de l'application : ajoutés au package.json une fois empaquetée
// (electron-builder.config.mjs), lus dans ../app-names.json en développement.
const readJson = (file) => JSON.parse(readFileSync(file, "utf8"));
const NAMES = readJson(path.join(here, "package.json")).appNames ?? readJson(path.join(PROJECT, "app-names.json"));
const TITLE = NAMES.long; // fenêtres et boîtes de dialogue
app.setName(NAMES.config); // dossier de configuration : ~/.config/<config>

// Sauvegarde passée en argument ; `npm start` lance Electron depuis desktop/,
// le chemin est donc relatif au dossier d'où la commande a été tapée (INIT_CWD).
const launchFile = fileArgument(process.argv, process.env.INIT_CWD ?? process.cwd(), app.isPackaged ? 1 : 2);

// <id> --version : affiche la version et quitte, sans fenêtre ni serveur (sous
// Windows, une application graphique n'a pas de console : rien ne s'affiche).
// Une seule instance : une deuxième transmet son fichier à la première.
if (process.argv.includes("--version")) {
  process.stdout.write(`${NAMES.id} ${NAMES.version}\n`);
  app.exit(0);
} else if (!app.requestSingleInstanceLock({ file: launchFile })) {
  app.quit();
} else {
  run();
}

function run() {
  const token = randomBytes(24).toString("base64url");
  let server = null;
  let origin = "";
  let win = null;
  let dirty = false; // dernier état signalé par l'interface (setDirty)
  let quitting = false;
  let lastDir = launchFile ? path.dirname(launchFile) : app.getPath("documents");
  let recent = []; // fichiers récents, donnés par l'interface (préférences)
  // langue des menus et des boîtes de dialogue : celle de l'interface une fois
  // chargée ; d'ici là, celle des préférences ou du système (voir whenReady)
  let lang = "en";
  let t = translator(lang);

  // --- Commandes vers l'interface (menu, fichier à ouvrir, fermeture) --------
  // Envoyées une fois l'interface prête (onCommand) ; chacune attend la réponse.
  let rendererReady = false;
  let nextId = 0;
  const queue = [];
  const waiting = new Map();

  function command(name, extra = {}, timeoutMs = 0) {
    return new Promise((resolve, reject) => {
      const id = ++nextId;
      let timer;
      if (timeoutMs) timer = setTimeout(() => waiting.delete(id) && reject(new Error("pas de réponse")), timeoutMs);
      waiting.set(id, (result) => {
        clearTimeout(timer);
        resolve(result);
      });
      const message = { id, command: name, ...extra };
      if (rendererReady) win.webContents.send("kitmanager:command", message);
      else queue.push(message);
    });
  }

  // Seule la page servie par le serveur local peut utiliser le pont.
  const trusted = (event) => Boolean(origin) && (event.senderFrame?.url ?? "").startsWith(`${origin}/`);

  ipcMain.on("kitmanager:token", (event) => {
    event.returnValue = trusted(event) ? token : "";
  });
  ipcMain.on("kitmanager:ready", (event) => {
    if (!trusted(event)) return;
    rendererReady = true;
    for (const message of queue.splice(0)) win.webContents.send("kitmanager:command", message);
  });
  ipcMain.on("kitmanager:command-done", (event, id, result) => {
    if (!trusted(event)) return;
    waiting.get(id)?.(result);
    waiting.delete(id);
  });
  ipcMain.on("kitmanager:dirty", (event, value) => {
    if (trusted(event)) dirty = Boolean(value);
  });
  ipcMain.on("kitmanager:recent", (event, files) => {
    if (!trusted(event)) return;
    recent = files;
    Menu.setApplicationMenu(buildMenu());
  });
  ipcMain.on("kitmanager:language", (event, value) => {
    if (!trusted(event) || !LANGUAGES.includes(value) || value === lang) return;
    setLanguage(value);
    Menu.setApplicationMenu(buildMenu());
  });
  // `defaultDir` : dossier du dernier fichier ouvert (préférences), sinon celui
  // de cette session
  ipcMain.handle("kitmanager:open-file", async (event, defaultDir) => {
    if (!trusted(event)) return null;
    const { canceled, filePaths } = await dialog.showOpenDialog(win, {
      title: t("openTitle"),
      defaultPath: defaultDir || lastDir,
      properties: ["openFile"],
      filters: [
        { name: t("backups"), extensions: ["bkf", "fac"] },
        { name: t("allFiles"), extensions: ["*"] },
      ],
    });
    if (canceled || !filePaths.length) return null;
    lastDir = path.dirname(filePaths[0]);
    return filePaths[0];
  });
  ipcMain.handle("kitmanager:save-file", async (event, defaultPath) => {
    if (!trusted(event)) return null;
    const ext = path.extname(defaultPath).slice(1).toLowerCase();
    const { canceled, filePath } = await dialog.showSaveDialog(win, {
      title: t("saveAsTitle"),
      defaultPath: defaultPath || lastDir,
      properties: ["showOverwriteConfirmation", "createDirectory"],
      filters: ext ? [{ name: t("backupExt", { ext }), extensions: [ext] }] : [],
    });
    if (canceled || !filePath) return null;
    lastDir = path.dirname(filePath);
    return filePath;
  });

  app.on("second-instance", (_event, _argv, _cwd, data) => {
    if (!win) return;
    if (win.isMinimized()) win.restore();
    win.focus();
    if (data?.file) command("open-file", { path: data.file });
  });

  // --- Fenêtre -----------------------------------------------------------------
  const windowStateFile = path.join(app.getPath("userData"), "window-state.json");

  function createWindow() {
    const saved = readWindowState(windowStateFile);
    win = new BrowserWindow({
      ...windowBounds(saved, screen.getAllDisplays().map((d) => d.workArea)),
      minWidth: 800,
      minHeight: 500,
      title: TITLE,
      show: false,
      autoHideMenuBar: true, // barre de menus masquée ; Alt l'affiche (raccourcis toujours actifs)
      webPreferences: {
        preload: path.join(here, "preload.cjs"),
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: true,
      },
    });
    // taille et position du dernier lancement ; maximisée au premier (maximize()
    // affiche aussi la fenêtre), Restaurer la ramène alors à 1400×900
    win.once("ready-to-show", () => (saved.maximized ? win.maximize() : win.show()));

    // Navigation limitée au serveur local ; les liens externes s'ouvrent dans le navigateur.
    const external = (url) => {
      if (/^https?:\/\//.test(url) && !url.startsWith(`${origin}/`)) shell.openExternal(url);
    };
    win.webContents.on("will-navigate", (event, url) => {
      if (!url.startsWith(`${origin}/`)) {
        event.preventDefault();
        external(url);
      }
    });
    win.webContents.setWindowOpenHandler(({ url }) => {
      external(url);
      return { action: "deny" };
    });
    // Recharger la page réinitialise le pont.
    win.webContents.on("did-start-navigation", ({ isMainFrame, isSameDocument }) => {
      if (isMainFrame && !isSameDocument) rendererReady = false;
    });

    let closing = false;
    let allowClose = false;
    win.on("close", async (event) => {
      writeWindowState(windowStateFile, win.getNormalBounds(), win.isMaximized() || win.isFullScreen());
      if (allowClose || !rendererReady) return;
      event.preventDefault();
      if (closing) return;
      closing = true;
      try {
        if (await confirmClose()) {
          allowClose = true;
          win.close();
        } else {
          quitting = false;
        }
      } finally {
        closing = false;
      }
    });
    win.on("closed", () => {
      win = null;
    });

    if (launchFile) command("open-file", { path: launchFile });
    win.loadURL(`${origin}/`);
  }

  // Avec des modifications non enregistrées : Enregistrer (dans le fichier
  // ouvert), Quitter sans enregistrer ou Annuler. Renvoie true pour fermer.
  async function confirmClose() {
    // l'interface envoie d'abord une modification encore en attente
    const state = await command("prepare-close", {}, 3000).catch(() => ({ dirty }));
    if (!state?.dirty) return true;
    const { response } = await dialog.showMessageBox(win, {
      type: "warning",
      title: TITLE,
      message: t("unsaved"),
      detail: t("unsavedDetail"),
      buttons: [t("saveButton"), t("quitWithoutSaving"), t("cancel")],
      defaultId: 0,
      cancelId: 2,
      noLink: true,
    });
    if (response === 1) return true;
    if (response === 2) return false;
    const result = await command("save-before-close", {}, 120000).catch(() => null);
    return result?.saved === true; // en cas d'échec, l'erreur est affichée dans la fenêtre
  }

  // --- À propos ----------------------------------------------------------------
  function about() {
    const options = {
      type: "info",
      title: t("aboutTitle", { app: NAMES.short }),
      message: NAMES.long,
      detail: t("aboutDetail", { version: NAMES.version }),
      buttons: ["OK"],
    };
    return win ? dialog.showMessageBox(win, options) : dialog.showMessageBox(options);
  }

  // --- Menu --------------------------------------------------------------------
  function setLanguage(value) {
    lang = value;
    t = translator(lang);
  }

  function buildMenu() {
    const send = (name) => () => win && command(name);
    const openRecent = (file) => () => win && command("open-file", { path: file });
    return Menu.buildFromTemplate(
      menuTemplate({ platform: process.platform, appName: NAMES.short, about, send, recent, openRecent, lang }),
    );
  }

  // --- Cycle de vie --------------------------------------------------------------
  app.on("before-quit", () => {
    quitting = true;
  });
  app.on("window-all-closed", () => app.quit());

  // Le serveur est arrêté avant de quitter (fermeture de son entrée standard).
  let serverStopped = false;
  app.on("will-quit", (event) => {
    if (!server || serverStopped) return;
    event.preventDefault();
    server.stop().finally(() => {
      serverStopped = true;
      app.quit();
    });
  });

  app.whenReady().then(async () => {
    setLanguage(resolveLanguage(languagePreference(path.join(app.getPath("userData"), "preferences.json")), app.getLocale()));
    Menu.setApplicationMenu(buildMenu());
    const launch = serverCommand({
      projectDir: PROJECT,
      packaged: app.isPackaged,
      resourcesPath: process.resourcesPath,
      serverName: `${NAMES.id}-server`,
    });
    const problem = serverProblem({ ...launch, t });
    if (problem) {
      dialog.showErrorBox(TITLE, problem);
      app.quit();
      return;
    }
    try {
      // préférences dans le dossier de configuration d'Electron
      const env = { ...process.env, KITMANAGER_CONFIG: app.getPath("userData") };
      server = await startServer({ ...launch, token, env, t });
    } catch (err) {
      dialog.showErrorBox(TITLE, t("serverFailed", { reason: err.message }));
      app.quit();
      return;
    }
    origin = `http://127.0.0.1:${server.port}`;
    server.exited.then((code) => {
      serverStopped = true;
      if (quitting) return;
      dialog.showErrorBox(TITLE, t("serverStopped", { code }));
      win?.destroy(); // sans serveur, rien ne peut plus être enregistré
      app.quit();
    });
    createWindow();
  });
}
