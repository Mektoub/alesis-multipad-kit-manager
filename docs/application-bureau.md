# Application de bureau

Application Electron autour de l'éditeur : la même interface, dans sa propre
fenêtre, avec les boîtes de dialogue du système. Elle n'est pas encore
empaquetée : elle se lance depuis le dépôt et utilise le Python du `.venv`.

## Lancement (développement)

Prérequis : Python 3 et Node.js, comme pour [l'éditeur web](editeur-web.md).

```bash
cd desktop && npm ci             # la première fois
npm start                        # écran d'accueil, puis Fichier > Ouvrir…
npm start -- ../Backups/Backup001.bkf
```

Le chemin passé en argument est relatif au dossier d'où la commande est tapée.
`npm start` prépare d'abord ce qui manque, comme `editeur.sh`
(`scripts/preparer.sh` : venv, dépendances, build de l'interface). Au premier
lancement, Electron télécharge son exécutable.

## Fonctionnement

- **Serveur** : l'application lance `python -m editor --port 0 --watch-stdin`
  avec un jeton aléatoire (`STRIKE_TOKEN`), attend la ligne
  `{"ready": true, "port": N}` (30 s au plus), puis ouvre la fenêtre sur
  `http://127.0.0.1:N`. Si le serveur ne démarre pas, une boîte d'erreur affiche
  la fin de sa sortie d'erreur.
- **Arrêt** : en quittant, l'application ferme l'entrée standard du serveur, qui
  s'arrête (puis `SIGTERM`, `SIGKILL` au besoin). Si l'application plante,
  l'entrée standard se ferme aussi : le serveur ne lui survit pas. S'il s'arrête
  de lui-même, l'application le signale et se ferme.
- **Une seule instance** : relancer l'application avec un fichier l'ouvre dans la
  fenêtre existante.
- **Menu** : *Fichier* (Ouvrir… `Ctrl+O`, Enregistrer `Ctrl+S`, Enregistrer
  sous… `Ctrl+Maj+S`, Quitter `Ctrl+Q`), *Édition*, *Affichage* (zoom, outils de
  développement).
- **Fermeture** : avec des modifications non enregistrées, une boîte propose
  *Enregistrer* (dans le fichier ouvert, avec la copie `.bak` habituelle),
  *Quitter sans enregistrer* ou *Annuler*. Une modification encore en attente
  d'envoi au serveur est comptée.
- **Sécurité** : la page n'a pas accès à Node (`contextIsolation`, `sandbox`) ;
  le préchargement (`desktop/preload.cjs`) n'expose que `window.strikeDesktop`
  (voir [Mode bureau](editeur-web.md#mode-bureau)), à la seule page du serveur
  local. La navigation est limitée à ce serveur ; les liens externes s'ouvrent
  dans le navigateur.

## Fichiers

| Chemin | Rôle |
|---|---|
| `desktop/main.js` | processus principal : serveur, fenêtre, menu, boîtes de dialogue, fermeture |
| `desktop/preload.cjs` | pont `window.strikeDesktop` |
| `desktop/server.js` | lancement du serveur Python, sans dépendance à Electron |
| `desktop/test/` | tests `node:test` (`npm test`) ; un faux serveur simule les cas d'erreur |

`npm test` vérifie la lecture de la ligne « prêt », les arguments, les échecs
(serveur arrêté, muet, introuvable) et l'arrêt ; un test de fumée lance le vrai
serveur sur la sauvegarde de référence quand `.venv` existe.

## Dépannage

- Sous Wayland, Chromium écrit des erreurs Vulkan au démarrage
  (`'--ozone-platform=wayland' is not compatible with Vulkan`) : elles sont sans
  conséquence.
