import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import path from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";

import { fileArgument, pythonCommand, readyPort, startServer } from "../server.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const project = path.resolve(here, "..", "..");
const fake = path.join(here, "faux-serveur.js");

function startFake(mode, options = {}) {
  return startServer({
    command: process.execPath,
    args: [fake],
    token: "jeton",
    env: { ...process.env, FAKE_MODE: mode, FAKE_TOKEN: "jeton" },
    timeoutMs: 2000,
    ...options,
  });
}

describe("lecture de la ligne « prêt »", () => {
  it("donne le port annoncé", () => assert.equal(readyPort('{"ready": true, "port": 51234}'), 51234));
  it("ignore les autres lignes", () => {
    for (const line of ["", "Éditeur disponible", '{"ready": false, "port": 1}', '{"ready": true}', "[1]"]) {
      assert.equal(readyPort(line), null, line);
    }
  });
});

describe("fichier passé en argument", () => {
  it("en développement : electron . FICHIER", () => {
    assert.equal(fileArgument(["/x/electron", ".", "Backups/B.bkf"], "/projet", 2), "/projet/Backups/B.bkf");
  });
  it("empaquetée : app FICHIER, options ignorées", () => {
    assert.equal(fileArgument(["/opt/app", "--no-sandbox", "/d/B.fac"], "/ailleurs", 1), "/d/B.fac");
  });
  it("sans fichier", () => {
    assert.equal(fileArgument(["/x/electron", "."], "/projet", 2), null);
    assert.equal(fileArgument(["/opt/app", "--enable-logging"], "/projet", 1), null);
  });
});

describe("interpréteur Python", () => {
  it("venv du dépôt", () => {
    assert.equal(pythonCommand("/p", "linux"), "/p/.venv/bin/python");
    assert.equal(pythonCommand("C:\\p", "win32").endsWith(path.join(".venv", "Scripts", "python.exe")), true);
  });
});

describe("lancement du serveur", () => {
  it("attend la ligne « prêt », puis s'arrête à la fermeture de stdin", async () => {
    const server = await startFake("ready");
    assert.equal(server.port, 4321);
    assert.equal(await server.stop(), 0);
  });

  it("transmet le jeton (STRIKE_TOKEN) et les options, avec port libre et --watch-stdin", async () => {
    const server = await startFake("ready", { args: [fake, "--open", "/d/B.bkf"] });
    assert.deepEqual(server.child.spawnargs.slice(1), [fake, "--open", "/d/B.bkf", "--port", "0", "--watch-stdin"]);
    await server.stop();
    await assert.rejects(startFake("ready", { token: "autre" }), /jeton inattendu : autre/);
  });

  it("échoue avec la sortie d'erreur si le serveur s'arrête", async () => {
    await assert.rejects(startFake("crash"), (err) => {
      assert.match(err.message, /s'est arrêté \(2\)/);
      assert.match(err.message, /fichier illisible/);
      return true;
    });
  });

  it("échoue si le serveur ne répond pas à temps", async () => {
    await assert.rejects(startFake("silent", { timeoutMs: 300 }), /pas répondu/);
  });

  it("échoue si l'interpréteur est introuvable", async () => {
    await assert.rejects(startFake("ready", { command: "/inexistant/python" }), /lancement impossible/);
  });

  it("arrête un serveur qui ignore stdin (SIGTERM)", async () => {
    const server = await startFake("stubborn");
    assert.equal(await server.stop(100), "SIGTERM");
  });
});

const python = pythonCommand(project);
describe("serveur réel (fumée)", { skip: !existsSync(python) && "pas de .venv" }, () => {
  it("ouvre la sauvegarde de référence et répond avec le jeton", async () => {
    const ref = path.join(project, "tests", "ressources", "Backup001.bkf");
    const server = await startServer({ command: python, args: ["-m", "editor", "--open", ref], cwd: project, token: "t" });
    try {
      const url = `http://127.0.0.1:${server.port}/api/state`;
      assert.equal((await fetch(url)).status, 403);
      const state = await (await fetch(url, { headers: { "X-Strike-Token": "t" } })).json();
      assert.equal(state.path, ref);
    } finally {
      assert.equal(await server.stop(), 0);
    }
  });
});
