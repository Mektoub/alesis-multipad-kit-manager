// Processus principal de l'application de bureau : lance le serveur Python de
// l'éditeur avec un jeton aléatoire, ouvre la fenêtre sur ce serveur, fournit
// les boîtes de dialogue natives et le menu, confirme la fermeture quand des
// modifications ne sont pas enregistrées, et arrête le serveur en quittant.
//
// En développement : ./dev.sh start [--frozen] [FICHIER], ou npm start [-- FICHIER]
// une fois le venv et l'interface prêts (Python du .venv du dépôt, ou le serveur
// figé désigné par KITMANAGER_SERVER).

import { randomBytes } from "node:crypto";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { app, BrowserWindow, dialog, ipcMain, Menu, shell } from "electron";

import { fileArgument, serverCommand, serverProblem, startServer } from "./server.js";

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
  ipcMain.handle("kitmanager:open-file", async (event) => {
    if (!trusted(event)) return null;
    const { canceled, filePaths } = await dialog.showOpenDialog(win, {
      title: "Ouvrir une sauvegarde",
      defaultPath: lastDir,
      properties: ["openFile"],
      filters: [
        { name: "Sauvegardes Strike (.bkf, .fac)", extensions: ["bkf", "fac"] },
        { name: "Tous les fichiers", extensions: ["*"] },
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
      title: "Enregistrer sous",
      defaultPath: defaultPath || lastDir,
      properties: ["showOverwriteConfirmation", "createDirectory"],
      filters: ext ? [{ name: `Sauvegarde .${ext}`, extensions: [ext] }] : [],
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
  function createWindow() {
    win = new BrowserWindow({
      width: 1400,
      height: 900,
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
    // ouverte maximisée (maximize() affiche aussi la fenêtre) ; Restaurer la
    // ramène à 1400×900
    win.once("ready-to-show", () => win.maximize());

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
      message: "Des modifications ne sont pas enregistrées.",
      detail:
        "« Enregistrer » les écrit dans le fichier ouvert ; au premier enregistrement, " +
        "une copie .bak de l'original est conservée.",
      buttons: ["Enregistrer", "Quitter sans enregistrer", "Annuler"],
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
      title: `À propos de ${NAMES.short}`,
      message: NAMES.long,
      detail: `Version ${NAMES.version}\nÉditeur des kits et des samples de l'Alesis Strike MultiPad.`,
      buttons: ["OK"],
    };
    return win ? dialog.showMessageBox(win, options) : dialog.showMessageBox(options);
  }

  // --- Menu --------------------------------------------------------------------
  function buildMenu() {
    const send = (name) => () => win && command(name);
    return Menu.buildFromTemplate([
      {
        label: "&Fichier",
        submenu: [
          { label: "&Ouvrir…", accelerator: "CmdOrCtrl+O", click: send("open") },
          { label: "&Enregistrer", accelerator: "CmdOrCtrl+S", click: send("save") },
          { label: "Enregistrer &sous…", accelerator: "CmdOrCtrl+Shift+S", click: send("save-as") },
          { type: "separator" },
          { label: "&Quitter", accelerator: "CmdOrCtrl+Q", role: "quit" },
        ],
      },
      {
        label: "É&dition",
        submenu: [
          { label: "Annuler", role: "undo" },
          { label: "Rétablir", role: "redo" },
          { type: "separator" },
          { label: "Couper", role: "cut" },
          { label: "Copier", role: "copy" },
          { label: "Coller", role: "paste" },
          { label: "Tout sélectionner", role: "selectAll" },
        ],
      },
      {
        label: "&Affichage",
        submenu: [
          { label: "Recharger", role: "reload" },
          { label: "Outils de développement", role: "toggleDevTools" },
          { type: "separator" },
          { label: "Taille réelle", role: "resetZoom" },
          { label: "Zoom avant", role: "zoomIn" },
          { label: "Zoom arrière", role: "zoomOut" },
          { type: "separator" },
          { label: "Plein écran", role: "togglefullscreen" },
        ],
      },
      {
        label: "Ai&de",
        submenu: [{ label: "À &propos", click: about }],
      },
    ]);
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
    Menu.setApplicationMenu(buildMenu());
    const launch = serverCommand({
      projectDir: PROJECT,
      packaged: app.isPackaged,
      resourcesPath: process.resourcesPath,
      serverName: `${NAMES.id}-server`,
    });
    const problem = serverProblem(launch);
    if (problem) {
      dialog.showErrorBox(TITLE, problem);
      app.quit();
      return;
    }
    try {
      server = await startServer({ ...launch, token });
    } catch (err) {
      dialog.showErrorBox(TITLE, `Le serveur de l'éditeur n'a pas pu démarrer : ${err.message}`);
      app.quit();
      return;
    }
    origin = `http://127.0.0.1:${server.port}`;
    server.exited.then((code) => {
      serverStopped = true;
      if (quitting) return;
      dialog.showErrorBox(TITLE, `Le serveur de l'éditeur s'est arrêté (${code}). L'application va se fermer.`);
      win?.destroy(); // sans serveur, rien ne peut plus être enregistré
      app.quit();
    });
    createWindow();
  });
}
