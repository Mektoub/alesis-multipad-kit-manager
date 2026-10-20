// Lancement du serveur Python de l'éditeur, sans dépendance à Electron (testé
// avec node:test).
//
// Le serveur reçoit le jeton par STRIKE_TOKEN, choisit un port libre (--port 0)
// et annonce `{"ready": true, "port": N}` sur sa sortie standard une fois à
// l'écoute. Avec --watch-stdin, il s'arrête quand son entrée standard se ferme :
// il ne survit donc pas à l'application, même si elle plante.

import { spawn } from "node:child_process";
import path from "node:path";

// Interpréteur du venv du dépôt, en développement.
export function pythonCommand(projectDir, platform = process.platform) {
  return platform === "win32"
    ? path.join(projectDir, ".venv", "Scripts", "python.exe")
    : path.join(projectDir, ".venv", "bin", "python");
}

// Serveur à lancer : { command, args, cwd }.
//   - STRIKE_SERVER : exécutable figé désigné explicitement (essai en développement) ;
//   - application empaquetée : serveur figé de ses ressources (strike-server/) ;
//   - sinon : Python du .venv du dépôt (python -m editor).
export function serverCommand({ projectDir, packaged, resourcesPath, env = process.env, platform = process.platform }) {
  const exe = platform === "win32" ? "strike-server.exe" : "strike-server";
  if (env.STRIKE_SERVER) return { command: path.resolve(env.STRIKE_SERVER), args: [], cwd: undefined };
  if (packaged) return { command: path.join(resourcesPath, "strike-server", exe), args: [], cwd: undefined };
  return { command: pythonCommand(projectDir, platform), args: ["-m", "editor"], cwd: projectDir };
}

// Port annoncé par une ligne de la sortie du serveur, ou null.
export function readyPort(line) {
  try {
    const msg = JSON.parse(line);
    return msg?.ready === true && Number.isInteger(msg.port) ? msg.port : null;
  } catch {
    return null;
  }
}

// Sauvegarde passée en argument (`electron . FICHIER`, ou `app FICHIER` une fois
// empaquetée) : le dernier argument qui n'est pas une option, en chemin absolu.
// `skip` : arguments à ignorer en tête (exécutable, et dossier de l'application
// en développement).
export function fileArgument(argv, cwd, skip) {
  const args = argv.slice(skip).filter((a) => !a.startsWith("-"));
  return args.length ? path.resolve(cwd, args.at(-1)) : null;
}

// Démarre le serveur et attend qu'il soit prêt. Renvoie { port, child, stop,
// exited } ; `exited` est une promesse du code de sortie. Échoue si le serveur
// s'arrête ou ne répond pas avant `timeoutMs`, avec la fin de sa sortie
// d'erreur dans le message.
export function startServer({ command, args = [], cwd, token, env = process.env, timeoutMs = 30000 }) {
  const child = spawn(command, [...args, "--port", "0", "--watch-stdin"], {
    cwd,
    env: { ...env, STRIKE_TOKEN: token },
    stdio: ["pipe", "pipe", "pipe"],
  });
  let stderr = "";
  child.stderr.setEncoding("utf8");
  child.stderr.on("data", (chunk) => {
    stderr = (stderr + chunk).slice(-4000);
    process.stderr.write(chunk); // visible dans le terminal en développement
  });
  const exited = new Promise((resolve) => child.on("exit", (code, signal) => resolve(code ?? signal)));
  const tail = () => stderr.trim().split("\n").slice(-8).join("\n");

  function stop(graceMs = 3000) {
    if (child.exitCode !== null || child.signalCode !== null) return exited;
    child.stdin.end(); // --watch-stdin : arrêt propre
    const timer = setTimeout(() => child.kill("SIGTERM"), graceMs);
    const killer = setTimeout(() => child.kill("SIGKILL"), graceMs * 2);
    return exited.finally(() => {
      clearTimeout(timer);
      clearTimeout(killer);
    });
  }

  return new Promise((resolve, reject) => {
    let buffer = "";
    const timer = setTimeout(() => {
      fail(`le serveur n'a pas répondu en ${Math.round(timeoutMs / 1000)} s`);
      child.kill("SIGKILL");
    }, timeoutMs);
    function fail(reason) {
      clearTimeout(timer);
      const details = tail();
      reject(new Error(details ? `${reason}\n\n${details}` : reason));
    }
    child.on("error", (err) => fail(`lancement impossible (${command}) : ${err.message}`));
    child.on("exit", (code, signal) => fail(`le serveur s'est arrêté (${code ?? signal})`));
    child.stdout.setEncoding("utf8");
    child.stdout.on("data", function onData(chunk) {
      buffer += chunk;
      let i;
      while ((i = buffer.indexOf("\n")) >= 0) {
        const port = readyPort(buffer.slice(0, i));
        buffer = buffer.slice(i + 1);
        if (port) {
          clearTimeout(timer);
          child.stdout.off("data", onData);
          child.stdout.resume(); // la suite de la sortie est ignorée
          resolve({ port, child, stop, exited });
          return;
        }
      }
    });
  });
}
