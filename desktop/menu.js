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
// `openRecent(chemin)` : fonction qui ouvre l'un d'eux.

export function menuTemplate({ platform, appName, about, send, recent = [], openRecent = () => () => {} }) {
  const mac = platform === "darwin";
  const recentMenu = recent.length
    ? [
        ...recent.map((file) => ({ label: file, click: openRecent(file) })),
        { type: "separator" },
        { label: "Effacer la liste", click: send("clear-recent") },
      ]
    : [{ label: "Aucun fichier récent", enabled: false }];
  const preferences = { label: "&Préférences…", accelerator: "CmdOrCtrl+,", click: send("preferences") };
  const file = [
    { label: "&Ouvrir…", accelerator: "CmdOrCtrl+O", click: send("open") },
    { label: "Ouvrir &récent", submenu: recentMenu },
    { label: "&Enregistrer", accelerator: "CmdOrCtrl+S", click: send("save") },
    { label: "Enregistrer &sous…", accelerator: "CmdOrCtrl+Shift+S", click: send("save-as") },
  ];
  if (!mac) file.push({ type: "separator" }, { label: "&Quitter", accelerator: "CmdOrCtrl+Q", role: "quit" });

  const appMenu = {
    label: appName,
    submenu: [
      { label: `À propos de ${appName}`, click: about },
      { type: "separator" },
      preferences,
      { type: "separator" },
      { label: `Masquer ${appName}`, role: "hide" },
      { label: "Masquer les autres", role: "hideOthers" },
      { label: "Tout afficher", role: "unhide" },
      { type: "separator" },
      { label: `Quitter ${appName}`, accelerator: "Cmd+Q", role: "quit" },
    ],
  };

  return [
    ...(mac ? [appMenu] : []),
    { label: "&Fichier", submenu: file },
    {
      label: "É&dition",
      submenu: [
        // Annuler / Rétablir : modifications de la sauvegarde, ou frappe dans un
        // champ de saisie (l'interface choisit). Hors macOS, le raccourci n'est
        // qu'affiché : l'interface le reçoit et gère aussi Ctrl+Maj+Z ; sous
        // macOS, le menu reçoit les touches avant la page.
        { label: "Annuler", accelerator: "CmdOrCtrl+Z", registerAccelerator: mac, click: send("undo") },
        {
          label: "Rétablir",
          accelerator: mac ? "Cmd+Shift+Z" : "Ctrl+Y",
          registerAccelerator: mac,
          click: send("redo"),
        },
        { type: "separator" },
        { label: "Couper", role: "cut" },
        { label: "Copier", role: "copy" },
        { label: "Coller", role: "paste" },
        { label: "Tout sélectionner", role: "selectAll" },
        // sous macOS, Préférences… est dans le menu de l'application
        ...(mac ? [] : [{ type: "separator" }, preferences]),
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
    // sous macOS, Aide ne contiendrait plus rien : À propos est dans le menu de l'application
    ...(mac ? [] : [{ label: "Ai&de", submenu: [{ label: "À &propos", click: about }] }]),
  ];
}
