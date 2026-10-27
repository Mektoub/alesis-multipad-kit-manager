// Pont vers l'application de bureau : objet window.kitManagerDesktop exposé par le
// preload d'Electron. Absent dans le navigateur, où l'interface garde ses
// champs de chemin.
//
//   token                  jeton du serveur (en-tête X-KitManager-Token)
//   openFile(defaultDir)   boîte native « Ouvrir », dans defaultDir s'il est donné
//                          → Promise<chemin absolu | null>
//   saveFile(defaultPath)  boîte native « Enregistrer sous » → Promise<chemin | null> ;
//                          la boîte confirme elle-même l'écrasement d'un fichier
//   setDirty(dirty)        signale les modifications non enregistrées, pour que
//                          l'application confirme la fermeture de la fenêtre
//   setRecent(files)       fichiers récents, pour le menu Fichier › Ouvrir récent
//   onCommand(handler)     reçoit les commandes de l'application, { command, path? } ;
//                          la valeur renvoyée par handler (ou sa promesse) est la réponse :
//                            open, save, save-as   menu Fichier
//                            open-file (path)      fichier passé au lancement, ou fichier récent
//                            preferences           fenêtre Préférences
//                            clear-recent          vide la liste des fichiers récents
//                            prepare-close         → { dirty } après envoi des modifications en attente
//                            save-before-close     → { saved } (« Enregistrer » à la fermeture)

export const desktop = window.kitManagerDesktop ?? null;
