// Modèle du menu de l'application (Menu.buildFromTemplate), sans dépendance à
// Electron pour pouvoir le tester.
//
// Sous macOS, le premier menu devient le menu de l'application (affiché sous son
// nom) : on y met À propos, Masquer… et Quitter (Cmd+Q), et on les retire de
// Fichier et d'Aide pour éviter les doublons. Linux et Windows gardent Fichier
// en tête, avec Quitter, et Aide › À propos.
//
// `about` : affiche la boîte À propos ; `send(nom)` : fonction qui transmet la
// commande `nom` à l'interface.

export function menuTemplate({ platform, appName, about, send }) {
  const mac = platform === "darwin";
  const file = [
    { label: "&Ouvrir…", accelerator: "CmdOrCtrl+O", click: send("open") },
    { label: "&Enregistrer", accelerator: "CmdOrCtrl+S", click: send("save") },
    { label: "Enregistrer &sous…", accelerator: "CmdOrCtrl+Shift+S", click: send("save-as") },
  ];
  if (!mac) file.push({ type: "separator" }, { label: "&Quitter", accelerator: "CmdOrCtrl+Q", role: "quit" });

  const appMenu = {
    label: appName,
    submenu: [
      { label: `À propos de ${appName}`, click: about },
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
    // sous macOS, Aide ne contiendrait plus rien : À propos est dans le menu de l'application
    ...(mac ? [] : [{ label: "Ai&de", submenu: [{ label: "À &propos", click: about }] }]),
  ];
}
