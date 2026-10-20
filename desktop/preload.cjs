// Pont entre la fenêtre et le processus principal : expose window.strikeDesktop,
// le seul accès de l'interface à l'application (voir editor/web/src/lib/desktop.js).
// Préchargement isolé (contextIsolation, sandbox) : CommonJS, module electron seul.
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("strikeDesktop", {
  token: ipcRenderer.sendSync("strike:token"),
  openFile: () => ipcRenderer.invoke("strike:open-file"),
  saveFile: (defaultPath) => ipcRenderer.invoke("strike:save-file", String(defaultPath ?? "")),
  setDirty: (dirty) => ipcRenderer.send("strike:dirty", Boolean(dirty)),
  // Commandes du menu et de l'application ({ command, path? }) ; la valeur
  // renvoyée par `handler` (éventuellement une promesse) est transmise en réponse.
  onCommand: (handler) => {
    ipcRenderer.on("strike:command", async (_event, { id, command, path }) => {
      let result;
      try {
        result = (await handler({ command, path })) ?? null;
      } catch (err) {
        result = { error: String(err?.message ?? err) };
      }
      ipcRenderer.send("strike:command-done", id, result);
    });
    ipcRenderer.send("strike:ready");
  },
});
