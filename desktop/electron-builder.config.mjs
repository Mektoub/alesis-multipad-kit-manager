// Configuration d'electron-builder, paquets du système courant (.deb sous
// Linux, installateur NSIS et zip sous Windows, dmg et zip sous macOS) : les
// noms viennent de ../app-names.json (nom long et court pour l'affichage,
// identifiant technique pour les chemins).
import { readFileSync } from "node:fs";

import { githubRepo } from "./updater.js";

const names = JSON.parse(readFileSync(new URL("../app-names.json", import.meta.url), "utf8"));
const { homepage } = JSON.parse(readFileSync(new URL("package.json", import.meta.url), "utf8"));
const server = `${names.id}-server`; // serveur figé (./dev.sh freeze)
// paquets Windows et macOS : <id>-<version>-<win|mac>-<arch>.<ext>, sans espaces
// (macros d'electron-builder) ; le .deb garde le nom Debian <id>_<version>_<arch>.deb
const artifact = (suffix = "") => `${names.id}-\${version}-\${os}-\${arch}${suffix}.\${ext}`;

export default {
  appId: `io.github.mektoub.${names.id}`,
  // Linux : dossier d'installation /opt/<id> (sans espace, voir la doc) ;
  // Windows et macOS : nom court (Alesis Kit Manager.app, menu Démarrer)
  productName: process.platform === "linux" ? names.id : names.short,
  executableName: names.id,
  // ajoutés au package.json de l'application empaquetée : main.js y lit les noms
  extraMetadata: { desktopName: `${names.id}.desktop`, appNames: names },
  directories: { output: "dist", buildResources: "build-resources" },
  files: ["main.js", "menu.js", "messages.js", "preload.cjs", "server.js", "updater.js", "window-state.js", "package.json"],
  extraResources: [{ from: `build/${server}`, to: server }],
  // mises à jour (desktop/updater.js) : dist/latest.yml, latest-linux.yml et
  // latest-mac.yml (version, fichiers, empreintes sha512), joints aux releases
  // GitHub par release.yml ; `--publish never` : rien n'est envoyé d'ici
  publish: { provider: "github", ...githubRepo(homepage), releaseType: "release" },
  fileAssociations: [
    { ext: "bkf", name: "Sauvegarde Strike (kits et samples)", mimeType: "application/x-kitmanager-bkf" },
    { ext: "fac", name: "Sauvegarde Strike (kits)", mimeType: "application/x-kitmanager-fac" },
  ],
  linux: {
    target: ["deb"],
    icon: "build-resources/icon.png",
    category: "AudioVideo",
    synopsis: names.long,
    syncDesktopName: true,
    desktop: {
      entry: {
        Name: names.short, // menu des applications
        GenericName: names.long,
        Comment: "Éditer les kits et les samples de l'Alesis Strike MultiPad",
        Keywords: "Alesis;Strike;MultiPad;kit;sample;",
      },
    },
  },
  win: {
    target: ["nsis", "zip"],
    artifactName: artifact(),
    icon: "build-resources/icon.png",
  },
  // installation en un clic, pour l'utilisateur courant, sans droits administrateur
  // differentialPackage: false : mise à jour par téléchargement complet, sans
  // .blockmap (l'empreinte de latest.yml reste ainsi seule à recalculer si
  // l'installateur est signé après sa construction)
  nsis: { shortcutName: names.short, artifactName: artifact("-setup"), differentialPackage: false },
  mac: {
    target: [{ target: "dmg", arch: "arm64" }, { target: "zip", arch: "arm64" }],
    icon: "build-resources/icon.png",
    category: "public.app-category.music",
    artifactName: artifact(),
    // sans certificat Apple : signature ad hoc, indispensable sur Apple Silicon ;
    // le runtime durci refuserait les bibliothèques d'Electron signées par une autre équipe
    identity: "-",
    hardenedRuntime: false,
  },
  dmg: { artifactName: artifact() },
  deb: {
    packageName: names.id,
    packageCategory: "sound",
    // dépendances par défaut d'electron-builder, plus libasound2 (sans elle, Electron ne démarre pas)
    depends: [
      "libgtk-3-0",
      "libnotify4",
      "libnss3",
      "libxss1",
      "libxtst6",
      "xdg-utils",
      "libatspi2.0-0",
      "libuuid1",
      "libsecret-1-0",
      "libasound2t64 | libasound2",
    ],
  },
};
