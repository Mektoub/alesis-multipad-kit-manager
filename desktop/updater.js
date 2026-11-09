// Mises à jour de l'application de bureau (electron-updater) : recherche de la
// dernière version publiée sur GitHub (fichiers latest*.yml des releases), au
// démarrage si la préférence `check_updates` l'autorise, ou à la demande (menu
// Aide › Rechercher des mises à jour…). Sans dépendance directe à Electron
// (`updater`, `dialog`, `shell` sont fournis) pour pouvoir le tester.
//
// Deux modes, selon le paquet installé (updateMode) :
//   install  installateur Windows (NSIS) et paquet .deb : téléchargement, puis
//            installation au redémarrage (Windows : aussi en quittant) ;
//   notify   macOS (sans signature Apple, Squirrel.Mac refuse la mise à jour)
//            et archive .zip de Windows : la nouvelle version est signalée, avec
//            un lien vers sa page de release.
// Aucun mode en développement, sauf avec KITMANAGER_UPDATE_URL (serveur de test,
// voir docs/*/desktop-app.md).

import { existsSync } from "node:fs";
import path from "node:path";

// "install", "notify" ou null (pas de mise à jour) ; `feed` : serveur de test.
export function updateMode({ platform, packaged, execPath, resourcesPath, productName, feed, exists = existsSync }) {
  if (!packaged) return feed ? "notify" : null;
  if (platform === "win32") {
    // l'installateur NSIS dépose son désinstalleur à côté de l'exécutable
    return exists(path.join(path.dirname(execPath), `Uninstall ${productName}.exe`)) ? "install" : "notify";
  }
  // paquet .deb : fichier package-type écrit par electron-builder, lu par electron-updater
  if (platform === "linux") return exists(path.join(resourcesPath, "package-type")) ? "install" : "notify";
  return "notify";
}

// "Mektoub/alesis-multipad-kit-manager" depuis l'adresse GitHub du projet.
export function githubRepo(homepage) {
  const [, owner, repo] = new URL(homepage).pathname.split("/");
  return { owner, repo };
}

// `win()` : fenêtre parente des boîtes de dialogue (ou null) ; `t()` : fonction
// de traduction en cours ; `releaseUrl(version)` : page de la release ;
// `beforeInstall()` : confirme la fermeture (modifications non enregistrées),
// renvoie false pour annuler ; `installFailed()` : l'installation n'a pas pu
// être lancée, l'application reprend (ou quitte, voir main.js).
export function createUpdates({ updater, mode, dialog, shell, platform, win, t, releaseUrl, beforeInstall, installFailed }) {
  let state = "idle"; // idle | checking | downloading | downloaded | installing
  let version = null; // version trouvée

  if (updater) {
    updater.autoDownload = false;
    // Windows : installation silencieuse en quittant ; .deb : pas de demande de
    // mot de passe inattendue en quittant, seulement sur « Redémarrer »
    updater.autoInstallOnAppQuit = platform === "win32";
    updater.logger = { info() {}, warn: console.warn, error: console.error };
    // les erreurs de recherche et de téléchargement arrivent aussi par les
    // promesses ; celles de l'installation (dpkg refusé…) seulement ici
    updater.on("error", (err) => {
      if (state !== "installing") return;
      state = "downloaded";
      show({ type: "error", message: t("updateInstallFailed"), detail: err.message, buttons: ["OK"] }).then(installFailed);
    });
  }

  const show = (options) => {
    const parent = win();
    return parent ? dialog.showMessageBox(parent, options) : dialog.showMessageBox(options);
  };
  const info = (message, detail) => show({ type: "info", message, detail, buttons: ["OK"] });
  const progress = (value) => win()?.setProgressBar(value);

  // `manual` : demandée par l'utilisateur, qui voit aussi « à jour » et les erreurs.
  async function check({ manual = false } = {}) {
    if (!mode) {
      if (manual) await info(t("updatesUnavailable"), t("updatesUnavailableDetail"));
      return;
    }
    if (state === "downloaded") return askRestart();
    if (state !== "idle") {
      if (manual) await info(t("updateInProgress"));
      return;
    }
    state = "checking";
    let result;
    try {
      result = await updater.checkForUpdates();
    } catch (err) {
      state = "idle";
      if (manual) await show({ type: "error", message: t("updateCheckFailed"), detail: err.message, buttons: ["OK"] });
      return;
    }
    state = "idle";
    if (!result?.isUpdateAvailable) {
      if (manual) await info(t("upToDate", { version: updater.currentVersion.version }));
      return;
    }
    version = result.updateInfo.version;
    return offer();
  }

  async function offer() {
    const page = releaseUrl(version);
    if (mode === "notify") {
      const { response } = await show({
        type: "info",
        message: t("updateAvailable", { version }),
        detail: t("updateNotifyDetail"),
        buttons: [t("openReleasePage"), t("later")],
        defaultId: 0,
        cancelId: 1,
        noLink: true,
      });
      if (response === 0) shell.openExternal(page);
      return;
    }
    const { response } = await show({
      type: "info",
      message: t("updateAvailable", { version }),
      detail: t(platform === "linux" ? "updateInstallDetailLinux" : "updateInstallDetail"),
      buttons: [t("downloadUpdate"), t("releaseNotes"), t("later")],
      defaultId: 0,
      cancelId: 2,
      noLink: true,
    });
    if (response === 1) shell.openExternal(page);
    if (response === 0) return download();
  }

  async function download() {
    state = "downloading";
    const onProgress = ({ percent }) => progress(percent / 100);
    updater.on("download-progress", onProgress);
    try {
      progress(2); // indéterminé jusqu'au premier pourcentage
      await updater.downloadUpdate();
    } catch (err) {
      state = "idle";
      await show({ type: "error", message: t("updateDownloadFailed"), detail: err.message, buttons: ["OK"] });
      return;
    } finally {
      updater.off("download-progress", onProgress);
      progress(-1);
    }
    state = "downloaded";
    return askRestart();
  }

  async function askRestart() {
    const { response } = await show({
      type: "info",
      message: t("updateDownloaded", { version }),
      detail: t(platform === "win32" ? "updateLaterDetail" : "updateLaterDetailLinux"),
      buttons: [t("restartAndInstall"), t("later")],
      defaultId: 0,
      cancelId: 1,
      noLink: true,
    });
    if (response !== 0 || !(await beforeInstall())) return;
    state = "installing";
    // installation silencieuse (Windows) puis relance de l'application ; .deb :
    // dpkg, avec demande du mot de passe administrateur, avant de quitter
    updater.quitAndInstall(true, true);
  }

  return { check, state: () => state };
}
