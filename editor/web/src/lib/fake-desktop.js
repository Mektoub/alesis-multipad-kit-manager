// Bouchon de window.kitManagerDesktop pour tester le mode bureau dans le navigateur,
// sans Electron : en développement seulement (npm run dev), activé par
// « desktop=fake » dans l'adresse (#token=…&desktop=fake) et conservé pour
// l'onglet. Les boîtes natives sont remplacées par prompt(), et les commandes de
// l'application s'envoient depuis la console : await kitManagerFakeCommand("save").
// Absent du build.
//
// Ce module doit être importé avant api.js (premier import de main.js).

if (import.meta.env.DEV) {
  const KEY = "kitmanager-fake-desktop";
  try {
    if (new URLSearchParams(location.hash.slice(1)).get("desktop") === "fake") sessionStorage.setItem(KEY, "1");
    if (sessionStorage.getItem(KEY)) {
      window.kitManagerDesktop = {
        // pas de jeton : api.js le lit dans l'adresse, comme en lancement local
        openFile: async () => prompt("[bouchon] Ouvrir : chemin absolu") || null,
        saveFile: async (defaultPath) => prompt("[bouchon] Enregistrer sous : chemin absolu", defaultPath) || null,
        setDirty: (dirty) => {
          console.info(`[bouchon] setDirty(${dirty})`);
          document.title = `${dirty ? "● " : ""}${__APP_NAMES__.long}`;
        },
        onCommand: (handler) => {
          window.kitManagerFakeCommand = (command, path) => handler({ command, path });
        },
      };
      console.info("[bouchon] mode bureau simulé (window.kitManagerDesktop)");
    }
  } catch {
    // stockage indisponible : pas de bouchon
  }
}
