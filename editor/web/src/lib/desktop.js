// Pont vers l'application de bureau : objet window.strikeDesktop exposé par le
// preload d'Electron. Absent dans le navigateur, où l'interface garde ses
// champs de chemin.
//
//   token                  jeton du serveur (en-tête X-Strike-Token)
//   openFile()             boîte native « Ouvrir » → Promise<chemin absolu | null>
//   saveFile(defaultPath)  boîte native « Enregistrer sous » → Promise<chemin | null> ;
//                          la boîte confirme elle-même l'écrasement d'un fichier
//   setDirty(dirty)        signale les modifications non enregistrées, pour que
//                          l'application confirme la fermeture de la fenêtre

export const desktop = window.strikeDesktop ?? null;
