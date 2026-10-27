// Pont entre la fenêtre et le processus principal : expose window.kitManagerDesktop,
// le seul accès de l'interface à l'application (voir editor/web/src/lib/desktop.js).
// Préchargement isolé (contextIsolation, sandbox) : CommonJS, module electron seul.
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("kitManagerDesktop", {
  token: ipcRenderer.sendSync("kitmanager:token"),
  openFile: (defaultDir) => ipcRenderer.invoke("kitmanager:open-file", String(defaultDir ?? "")),
  saveFile: (defaultPath) => ipcRenderer.invoke("kitmanager:save-file", String(defaultPath ?? "")),
  setDirty: (dirty) => ipcRenderer.send("kitmanager:dirty", Boolean(dirty)),
  setRecent: (files) => ipcRenderer.send("kitmanager:recent", Array.from(files ?? [], String)),
  // Commandes du menu et de l'application ({ command, path? }) ; la valeur
  // renvoyée par `handler` (éventuellement une promesse) est transmise en réponse.
  onCommand: (handler) => {
    ipcRenderer.on("kitmanager:command", async (_event, { id, command, path }) => {
      let result;
      try {
        result = (await handler({ command, path })) ?? null;
      } catch (err) {
        result = { error: String(err?.message ?? err) };
      }
      ipcRenderer.send("kitmanager:command-done", id, result);
    });
    ipcRenderer.send("kitmanager:ready");
  },
});
