// Textes de l'application de bureau (menus, boîtes de dialogue), en anglais et
// en français. La langue est celle de l'interface (préférence `language`,
// transmise par setLanguage) ; avant que l'interface ne la donne, celle du
// fichier des préférences, sinon celle du système.
//
// &x dans un libellé de menu : touche d'accès (Alt+x), hors macOS.

import { readFileSync } from "node:fs";

export const LANGUAGES = ["en", "fr"];

const MESSAGES = {
  en: {
    file: "&File",
    open: "&Open…",
    openRecent: "Open &Recent",
    clearRecent: "Clear the list",
    noRecent: "No recent file",
    save: "&Save",
    saveAs: "Save &As…",
    quit: "&Quit",
    edit: "&Edit",
    undo: "Undo",
    redo: "Redo",
    cut: "Cut",
    copy: "Copy",
    paste: "Paste",
    selectAll: "Select All",
    preferences: "&Preferences…",
    samples: "&Samples…",
    view: "&View",
    reload: "Reload",
    devTools: "Developer Tools",
    resetZoom: "Actual Size",
    zoomIn: "Zoom In",
    zoomOut: "Zoom Out",
    fullScreen: "Full Screen",
    help: "&Help",
    about: "&About",
    checkUpdates: "Check for &Updates…",
    aboutApp: "About {app}",
    hideApp: "Hide {app}",
    hideOthers: "Hide Others",
    showAll: "Show All",
    quitApp: "Quit {app}",
    // boîtes de dialogue
    openTitle: "Open a backup",
    backups: "Strike backups (.bkf, .fac)",
    allFiles: "All files",
    saveAsTitle: "Save as",
    backupExt: "Backup .{ext}",
    unsaved: "Some changes are not saved.",
    unsavedDetail: "“Save” writes them to the open file; on the first save, a .bak copy of the original is kept.",
    saveButton: "Save",
    quitWithoutSaving: "Quit without saving",
    cancel: "Cancel",
    aboutTitle: "About {app}",
    aboutDetail: "Version {version}\nEditor for the kits and samples of the Alesis Strike MultiPad.",
    serverFailed: "The editor server could not start: {reason}",
    serverStopped: "The editor server stopped ({code}). The application will close.",
    // lancement du serveur (server.js)
    devHint: "run ./dev.sh start from the root of the repository",
    pythonMissing: "Python of the .venv not found ({command}): {hint}.",
    serverMissing: "Server not found: {command}.",
    uiMissing: "Interface not built: {hint}.",
    noAnswer: "the server did not answer within {seconds} s",
    cannotLaunch: "cannot launch ({command}): {message}",
    exited: "the server stopped ({code})",
    // mises à jour (updater.js)
    updatesUnavailable: "Updates are only available in the installed application.",
    updatesUnavailableDetail: "In development, update the repository (git pull).",
    updateInProgress: "An update check or download is already in progress.",
    updateCheckFailed: "Could not check for updates.",
    upToDate: "You have the latest version ({version}).",
    updateAvailable: "Version {version} is available.",
    updateNotifyDetail: "Download it from its release page.",
    updateInstallDetail: "It will be downloaded, then installed when the application restarts.",
    updateInstallDetailLinux:
      "It will be downloaded, then installed when the application restarts; " +
      "the administrator password will be asked for.",
    openReleasePage: "Open the release page",
    downloadUpdate: "Download",
    releaseNotes: "Release notes",
    later: "Later",
    updateDownloadFailed: "The update could not be downloaded.",
    updateDownloaded: "Version {version} has been downloaded.",
    updateLaterDetail: "Restart now to install it, or it will be installed when you quit the application.",
    updateLaterDetailLinux: "Restart now to install it, or later from Help › Check for Updates.",
    restartAndInstall: "Restart and install",
    updateInstallFailed: "The update could not be installed.",
  },
  fr: {
    file: "&Fichier",
    open: "&Ouvrir…",
    openRecent: "Ouvrir &récent",
    clearRecent: "Effacer la liste",
    noRecent: "Aucun fichier récent",
    save: "&Enregistrer",
    saveAs: "Enregistrer &sous…",
    quit: "&Quitter",
    edit: "É&dition",
    undo: "Annuler",
    redo: "Rétablir",
    cut: "Couper",
    copy: "Copier",
    paste: "Coller",
    selectAll: "Tout sélectionner",
    preferences: "&Préférences…",
    samples: "&Samples…",
    view: "&Affichage",
    reload: "Recharger",
    devTools: "Outils de développement",
    resetZoom: "Taille réelle",
    zoomIn: "Zoom avant",
    zoomOut: "Zoom arrière",
    fullScreen: "Plein écran",
    help: "Ai&de",
    about: "À &propos",
    checkUpdates: "Rechercher des &mises à jour…",
    aboutApp: "À propos de {app}",
    hideApp: "Masquer {app}",
    hideOthers: "Masquer les autres",
    showAll: "Tout afficher",
    quitApp: "Quitter {app}",
    openTitle: "Ouvrir une sauvegarde",
    backups: "Sauvegardes Strike (.bkf, .fac)",
    allFiles: "Tous les fichiers",
    saveAsTitle: "Enregistrer sous",
    backupExt: "Sauvegarde .{ext}",
    unsaved: "Des modifications ne sont pas enregistrées.",
    unsavedDetail:
      "« Enregistrer » les écrit dans le fichier ouvert ; au premier enregistrement, " +
      "une copie .bak de l'original est conservée.",
    saveButton: "Enregistrer",
    quitWithoutSaving: "Quitter sans enregistrer",
    cancel: "Annuler",
    aboutTitle: "À propos de {app}",
    aboutDetail: "Version {version}\nÉditeur des kits et des samples de l'Alesis Strike MultiPad.",
    serverFailed: "Le serveur de l'éditeur n'a pas pu démarrer : {reason}",
    serverStopped: "Le serveur de l'éditeur s'est arrêté ({code}). L'application va se fermer.",
    devHint: "lancer ./dev.sh start depuis la racine du dépôt",
    pythonMissing: "Python du .venv introuvable ({command}) : {hint}.",
    serverMissing: "Serveur introuvable : {command}.",
    uiMissing: "Interface non construite : {hint}.",
    noAnswer: "le serveur n'a pas répondu en {seconds} s",
    cannotLaunch: "lancement impossible ({command}) : {message}",
    exited: "le serveur s'est arrêté ({code})",
    updatesUnavailable: "Les mises à jour ne sont disponibles que dans l'application installée.",
    updatesUnavailableDetail: "En développement, mettre à jour le dépôt (git pull).",
    updateInProgress: "Une recherche ou un téléchargement de mise à jour est déjà en cours.",
    updateCheckFailed: "Impossible de rechercher les mises à jour.",
    upToDate: "Vous avez la dernière version ({version}).",
    updateAvailable: "La version {version} est disponible.",
    updateNotifyDetail: "Téléchargez-la depuis sa page de release.",
    updateInstallDetail: "Elle sera téléchargée, puis installée au redémarrage de l'application.",
    updateInstallDetailLinux:
      "Elle sera téléchargée, puis installée au redémarrage de l'application ; " +
      "le mot de passe administrateur sera demandé.",
    openReleasePage: "Ouvrir la page de la release",
    downloadUpdate: "Télécharger",
    releaseNotes: "Notes de version",
    later: "Plus tard",
    updateDownloadFailed: "La mise à jour n'a pas pu être téléchargée.",
    updateDownloaded: "La version {version} a été téléchargée.",
    updateLaterDetail: "Redémarrez maintenant pour l'installer, sinon elle le sera en quittant l'application.",
    updateLaterDetailLinux: "Redémarrez maintenant pour l'installer, ou plus tard par Aide › Rechercher des mises à jour.",
    restartAndInstall: "Redémarrer et installer",
    updateInstallFailed: "La mise à jour n'a pas pu être installée.",
  },
};

export const messageKeys = (lang) => Object.keys(MESSAGES[lang]);

// Fonction de traduction t(clé, { valeurs }) pour la langue `lang`.
export function translator(lang) {
  const table = MESSAGES[lang] ?? MESSAGES.en;
  return (key, params = {}) =>
    (table[key] ?? key).replace(/\{(\w+)\}/g, (match, name) => (name in params ? String(params[name]) : match));
}

// Langue de la préférence `pref` ("system", "en" ou "fr") ; "system" : celle
// du système `locale` ("fr-FR"…), français ou anglais.
export function resolveLanguage(pref, locale) {
  if (LANGUAGES.includes(pref)) return pref;
  const lang = String(locale ?? "").slice(0, 2).toLowerCase();
  return LANGUAGES.includes(lang) ? lang : "en";
}

// Préférence `language` du fichier preferences.json (écrit par le serveur),
// "system" s'il est absent ou illisible.
export function languagePreference(file) {
  try {
    return JSON.parse(readFileSync(file, "utf8")).language ?? "system";
  } catch {
    return "system";
  }
}
