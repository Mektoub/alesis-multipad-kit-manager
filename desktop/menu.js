// Modèle du menu de l'application (Menu.buildFromTemplate), sans dépendance à
// Electron pour pouvoir le tester.
//
// Sous macOS, le premier menu devient le menu de l'application (affiché sous son
// nom) : on y met À propos, Masquer… et Quitter (Cmd+Q), et on les retire de
// Fichier et d'Aide pour éviter les doublons. Linux et Windows gardent Fichier
// en tête, avec Quitter, et Aide › À propos.
//
// `about` : affiche la boîte À propos ; `send(nom)` : fonction qui transmet la
// commande `nom` à l'interface ; `recent` : fichiers récents (préférences),
// `openRecent(chemin)` : fonction qui ouvre l'un d'eux ; `lang` : langue des
// libellés (messages.js).

import { translator } from "./messages.js";

export function menuTemplate({ platform, appName, about, send, recent = [], openRecent = () => () => {}, lang = "en" }) {
  const t = translator(lang);
  const mac = platform === "darwin";
  const recentMenu = recent.length
    ? [
        ...recent.map((file) => ({ label: file, click: openRecent(file) })),
        { type: "separator" },
        { label: t("clearRecent"), click: send("clear-recent") },
      ]
    : [{ label: t("noRecent"), enabled: false }];
  const preferences = { label: t("preferences"), accelerator: "CmdOrCtrl+,", click: send("preferences") };
  const file = [
    { label: t("open"), accelerator: "CmdOrCtrl+O", click: send("open") },
    { label: t("openRecent"), submenu: recentMenu },
    { label: t("save"), accelerator: "CmdOrCtrl+S", click: send("save") },
    { label: t("saveAs"), accelerator: "CmdOrCtrl+Shift+S", click: send("save-as") },
  ];
  if (!mac) file.push({ type: "separator" }, { label: t("quit"), accelerator: "CmdOrCtrl+Q", role: "quit" });

  const appMenu = {
    label: appName,
    submenu: [
      { label: t("aboutApp", { app: appName }), click: about },
      { type: "separator" },
      preferences,
      { type: "separator" },
      { label: t("hideApp", { app: appName }), role: "hide" },
      { label: t("hideOthers"), role: "hideOthers" },
      { label: t("showAll"), role: "unhide" },
      { type: "separator" },
      { label: t("quitApp", { app: appName }), accelerator: "Cmd+Q", role: "quit" },
    ],
  };

  return [
    ...(mac ? [appMenu] : []),
    { label: t("file"), submenu: file },
    {
      label: t("edit"),
      submenu: [
        // Annuler / Rétablir : modifications de la sauvegarde, ou frappe dans un
        // champ de saisie (l'interface choisit). Hors macOS, le raccourci n'est
        // qu'affiché : l'interface le reçoit et gère aussi Ctrl+Maj+Z ; sous
        // macOS, le menu reçoit les touches avant la page.
        { label: t("undo"), accelerator: "CmdOrCtrl+Z", registerAccelerator: mac, click: send("undo") },
        {
          label: t("redo"),
          accelerator: mac ? "Cmd+Shift+Z" : "Ctrl+Y",
          registerAccelerator: mac,
          click: send("redo"),
        },
        { type: "separator" },
        { label: t("cut"), role: "cut" },
        { label: t("copy"), role: "copy" },
        { label: t("paste"), role: "paste" },
        { label: t("selectAll"), role: "selectAll" },
        // sous macOS, Préférences… est dans le menu de l'application
        ...(mac ? [] : [{ type: "separator" }, preferences]),
      ],
    },
    {
      label: t("view"),
      submenu: [
        { label: t("reload"), role: "reload" },
        { label: t("devTools"), role: "toggleDevTools" },
        { type: "separator" },
        { label: t("resetZoom"), role: "resetZoom" },
        { label: t("zoomIn"), role: "zoomIn" },
        { label: t("zoomOut"), role: "zoomOut" },
        { type: "separator" },
        { label: t("fullScreen"), role: "togglefullscreen" },
      ],
    },
    // sous macOS, Aide ne contiendrait plus rien : À propos est dans le menu de l'application
    ...(mac ? [] : [{ label: t("help"), submenu: [{ label: t("about"), click: about }] }]),
  ];
}
