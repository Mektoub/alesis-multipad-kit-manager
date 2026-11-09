import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import path from "node:path";
import { describe, it } from "node:test";

import { translator } from "../messages.js";
import { createUpdates, githubRepo, updateMode } from "../updater.js";

describe("mode de mise à jour selon le paquet", () => {
  const win = { platform: "win32", packaged: true, execPath: "C:\\App\\app.exe", productName: "Kit Manager" };
  const uninstaller = path.join(path.dirname(win.execPath), "Uninstall Kit Manager.exe");

  it("Windows : installateur (désinstalleur présent) ou archive .zip", () => {
    assert.equal(updateMode({ ...win, exists: (p) => p === uninstaller }), "install");
    assert.equal(updateMode({ ...win, exists: () => false }), "notify");
  });

  it("Linux : paquet .deb (package-type) ; macOS : notification seulement", () => {
    const linux = { platform: "linux", packaged: true, resourcesPath: "/opt/app/resources" };
    assert.equal(updateMode({ ...linux, exists: (p) => p === "/opt/app/resources/package-type" }), "install");
    assert.equal(updateMode({ ...linux, exists: () => false }), "notify");
    assert.equal(updateMode({ platform: "darwin", packaged: true, exists: () => true }), "notify");
  });

  it("développement : aucune, sauf avec un serveur de test", () => {
    assert.equal(updateMode({ platform: "linux", packaged: false, exists: () => true }), null);
    assert.equal(updateMode({ platform: "linux", packaged: false, feed: "http://127.0.0.1:1/" }), "notify");
  });

  it("dépôt GitHub depuis l'adresse du projet", () => {
    assert.deepEqual(githubRepo("https://github.com/Mektoub/alesis-multipad-kit-manager"), {
      owner: "Mektoub",
      repo: "alesis-multipad-kit-manager",
    });
  });
});

// Faux electron-updater : `latest` est la version publiée, `fail` fait échouer
// l'étape donnée ("check", "download" ou "install").
function fakeUpdater({ latest = "1.0.0", fail = null } = {}) {
  const updater = new EventEmitter();
  updater.currentVersion = { version: "1.0.0" };
  updater.calls = [];
  updater.checkForUpdates = async () => {
    updater.calls.push("check");
    if (fail === "check") throw new Error("réseau");
    return { isUpdateAvailable: latest !== "1.0.0", updateInfo: { version: latest } };
  };
  updater.downloadUpdate = async () => {
    updater.calls.push("download");
    if (fail === "download") throw new Error("coupure");
    updater.emit("download-progress", { percent: 50 });
  };
  updater.quitAndInstall = (silent, runAfter) => {
    updater.calls.push(`install ${silent} ${runAfter}`);
    if (fail === "install") updater.emit("error", new Error("dpkg refusé"));
  };
  return updater;
}

// Boîtes de dialogue : `answers` donne l'indice du bouton choisi, dans l'ordre.
function setup({ mode = "install", platform = "win32", answers = [], confirm = true, ...options } = {}) {
  const updater = fakeUpdater(options);
  const shown = [];
  const opened = [];
  const progress = [];
  const events = [];
  const updates = createUpdates({
    updater,
    mode,
    platform,
    dialog: {
      showMessageBox: async (_win, o) => {
        shown.push(o);
        return { response: answers.shift() ?? 0 };
      },
    },
    shell: { openExternal: (url) => opened.push(url) },
    win: () => ({ setProgressBar: (v) => progress.push(v) }),
    t: translator("en"),
    releaseUrl: (v) => `https://example.org/v${v}`,
    beforeInstall: async () => (events.push("beforeInstall"), confirm),
    installFailed: () => events.push("installFailed"),
  });
  const messages = () => shown.map((o) => o.message);
  return { updater, updates, shown, messages, opened, progress, events };
}

describe("recherche et installation des mises à jour", () => {
  it("à jour : rien au démarrage, un message à la demande", async () => {
    const auto = setup();
    await auto.updates.check();
    assert.deepEqual(auto.shown, []);
    const manual = setup();
    await manual.updates.check({ manual: true });
    assert.deepEqual(manual.messages(), ["You have the latest version (1.0.0)."]);
  });

  it("erreur de recherche : silencieuse au démarrage, affichée à la demande", async () => {
    const auto = setup({ fail: "check" });
    await auto.updates.check();
    assert.deepEqual(auto.shown, []);
    assert.equal(auto.updates.state(), "idle");
    const manual = setup({ fail: "check" });
    await manual.updates.check({ manual: true });
    assert.equal(manual.shown[0].type, "error");
    assert.equal(manual.shown[0].detail, "réseau");
  });

  it("sans mode (développement) : explication à la demande, aucune recherche", async () => {
    const s = setup({ mode: null, latest: "2.0.0" });
    await s.updates.check();
    assert.deepEqual(s.shown, []);
    await s.updates.check({ manual: true });
    assert.deepEqual(s.updater.calls, []);
    assert.equal(s.messages()[0], "Updates are only available in the installed application.");
  });

  it("notification : lien vers la release, sans téléchargement", async () => {
    const s = setup({ mode: "notify", latest: "2.0.0", answers: [0] });
    await s.updates.check();
    assert.deepEqual(s.messages(), ["Version 2.0.0 is available."]);
    assert.deepEqual(s.opened, ["https://example.org/v2.0.0"]);
    assert.deepEqual(s.updater.calls, ["check"]);
  });

  it("installation : téléchargement avec progression, redémarrage, installation", async () => {
    const s = setup({ latest: "2.0.0", answers: [0, 0] });
    await s.updates.check();
    assert.deepEqual(s.messages(), ["Version 2.0.0 is available.", "Version 2.0.0 has been downloaded."]);
    assert.deepEqual(s.progress, [2, 0.5, -1]);
    assert.deepEqual(s.events, ["beforeInstall"]);
    assert.deepEqual(s.updater.calls, ["check", "download", "install true true"]);
    assert.equal(s.updater.autoDownload, false);
    assert.equal(s.updater.autoInstallOnAppQuit, true);
  });

  it("notes de version, Plus tard : rien n'est téléchargé", async () => {
    const s = setup({ latest: "2.0.0", answers: [1] });
    await s.updates.check();
    assert.deepEqual(s.opened, ["https://example.org/v2.0.0"]);
    assert.deepEqual(s.updater.calls, ["check"]);
  });

  it("Plus tard après le téléchargement, puis nouvelle demande : redémarrage proposé directement", async () => {
    const s = setup({ latest: "2.0.0", answers: [0, 1, 0] });
    await s.updates.check();
    assert.equal(s.updates.state(), "downloaded");
    await s.updates.check({ manual: true });
    assert.deepEqual(s.updater.calls, ["check", "download", "install true true"]);
  });

  it("fermeture annulée (modifications non enregistrées) : pas d'installation", async () => {
    const s = setup({ latest: "2.0.0", answers: [0, 0], confirm: false });
    await s.updates.check();
    assert.deepEqual(s.updater.calls, ["check", "download"]);
    assert.equal(s.updates.state(), "downloaded");
  });

  it("échec du téléchargement ou de l'installation : message, l'application reprend", async () => {
    const d = setup({ latest: "2.0.0", fail: "download", answers: [0] });
    await d.updates.check();
    assert.equal(d.shown.at(-1).message, "The update could not be downloaded.");
    assert.equal(d.updates.state(), "idle");
    assert.equal(d.progress.at(-1), -1);

    const i = setup({ platform: "linux", latest: "2.0.0", fail: "install", answers: [0, 0] });
    await i.updates.check();
    await new Promise(setImmediate); // message affiché, puis installFailed
    assert.equal(i.updater.autoInstallOnAppQuit, false); // .deb : pas de mot de passe demandé en quittant
    assert.deepEqual(i.events, ["beforeInstall", "installFailed"]);
    assert.equal(i.shown.at(-1).message, "The update could not be installed.");
    assert.equal(i.updates.state(), "downloaded");
  });
});
