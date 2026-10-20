import assert from "node:assert/strict";
import { existsSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";

import { fileArgument, pythonCommand, readyPort, serverCommand, serverProblem, startServer } from "../server.js";

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
  it("double-clic dans le gestionnaire de fichiers : URL file:// (%U)", () => {
    assert.equal(fileArgument(["/opt/app", "file:///home/moi/Strike%20Backup/B.bkf"], "/", 1), "/home/moi/Strike Backup/B.bkf");
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

describe("serveur à lancer", () => {
  const base = { projectDir: "/p", resourcesPath: "/opt/app/resources", serverName: "app-server", platform: "linux" };
  it("développement : Python du .venv", () => {
    assert.deepEqual(serverCommand({ ...base, packaged: false, env: {} }), {
      command: "/p/.venv/bin/python",
      args: ["-m", "editor"],
      cwd: "/p",
    });
  });
  it("empaquetée : serveur figé des ressources", () => {
    const { command, args } = serverCommand({ ...base, packaged: true, env: {} });
    assert.deepEqual([command, args], ["/opt/app/resources/app-server/app-server", []]);
  });
  it("STRIKE_SERVER désigne un serveur figé", () => {
    for (const packaged of [false, true]) {
      const { command, args } = serverCommand({ ...base, packaged, env: { STRIKE_SERVER: "/b/app-server" } });
      assert.deepEqual([command, args], ["/b/app-server", []]);
    }
  });
});

describe("serveur impossible à lancer", () => {
  const dev = { command: "/p/.venv/bin/python", cwd: "/p" };
  const only = (...paths) => (p) => paths.includes(p);
  it("développement prêt", () => {
    assert.equal(serverProblem({ ...dev, exists: only(dev.command, "/p/editor/web/dist/index.html") }), null);
  });
  it("venv absent", () => {
    assert.match(serverProblem({ ...dev, exists: only() }), /Python du \.venv introuvable.*\.\/dev\.sh start/);
  });
  it("interface non construite", () => {
    assert.match(serverProblem({ ...dev, exists: only(dev.command) }), /Interface non construite.*\.\/dev\.sh start/);
  });
  it("serveur figé absent", () => {
    assert.equal(serverProblem({ command: "/b/app-server", exists: only() }), "Serveur introuvable : /b/app-server.");
    assert.equal(serverProblem({ command: "/b/app-server", exists: only("/b/app-server") }), null);
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

// Test de fumée : ouvre la sauvegarde de référence, lit un kit et un WAV, sert
// l'interface ; l'accès sans jeton est refusé.
async function smoke(options) {
  const ref = path.join(project, "tests", "ressources", "Backup001.bkf");
  // --allow : la sauvegarde de référence peut être hors du dossier personnel (HOME du test)
  const args = [...(options.args ?? []), "--open", ref, "--allow", path.dirname(ref)];
  const server = await startServer({ ...options, args, token: "t" });
  try {
    const base = `http://127.0.0.1:${server.port}`;
    const get = (url) => fetch(base + url, { headers: { "X-Strike-Token": "t" } });
    assert.equal((await fetch(`${base}/api/state`)).status, 403);
    assert.equal((await (await get("/api/state")).json()).path, ref);
    assert.equal((await (await get("/api/kits/031")).json()).name, "WhereIs");
    const wav = await get("/api/samples/8071/wav");
    assert.deepEqual([wav.status, wav.headers.get("content-type")], [200, "audio/wav"]);
    const page = await (await fetch(`${base}/`)).text();
    assert.match(page, /<div id="app">/, "interface non servie");
  } finally {
    assert.equal(await server.stop(), 0);
  }
}

const python = pythonCommand(project);
describe("serveur réel (fumée)", { skip: !existsSync(python) && "pas de .venv" }, () => {
  it("Python du .venv", () => smoke({ command: python, args: ["-m", "editor"], cwd: project }));
});

// Serveur figé (./dev.sh freeze) : lancé hors du dépôt, avec un environnement
// minimal, pour vérifier qu'il ne dépend ni du .venv ni des sources.
const frozen = process.env.STRIKE_SERVER;
describe("serveur figé (fumée)", { skip: !(frozen && existsSync(frozen)) && "STRIKE_SERVER absent" }, () => {
  it("exécutable autonome", () => {
    const cwd = mkdtempSync(path.join(tmpdir(), "strike-fige-"));
    return smoke({ command: frozen, cwd, env: { PATH: "/usr/bin:/bin", HOME: cwd } }).finally(() =>
      rmSync(cwd, { recursive: true, force: true }),
    );
  });
});
