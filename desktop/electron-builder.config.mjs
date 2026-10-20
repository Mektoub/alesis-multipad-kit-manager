// Configuration d'electron-builder (paquet .deb) : les noms viennent de
// ../app-names.json (nom long et court pour l'affichage, identifiant technique
// pour les chemins).
import { readFileSync } from "node:fs";

const names = JSON.parse(readFileSync(new URL("../app-names.json", import.meta.url), "utf8"));

export default {
  appId: `io.github.mektoub.${names.id}`,
  productName: names.id, // dossier d'installation : /opt/<id>
  executableName: names.id,
  // ajoutés au package.json de l'application empaquetée : main.js y lit les noms
  extraMetadata: { desktopName: `${names.id}.desktop`, appNames: names },
  directories: { output: "dist", buildResources: "build-resources" },
  files: ["main.js", "preload.cjs", "server.js", "package.json"],
  extraResources: [{ from: "build/strike-server", to: "strike-server" }],
  fileAssociations: [
    { ext: "bkf", name: "Sauvegarde Strike (kits et samples)", mimeType: "application/x-strike-bkf" },
    { ext: "fac", name: "Sauvegarde Strike (kits)", mimeType: "application/x-strike-fac" },
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
