# Application de bureau

Application Electron autour de l'éditeur : la même interface, dans sa propre
fenêtre, avec les boîtes de dialogue du système. Elle s'installe par un
[paquet .deb](#paquet-deb), ou se lance depuis le dépôt en développement, avec le
Python du `.venv` ou le [serveur figé](#serveur-figé).

## Lancement (développement)

Prérequis : Python 3 et Node.js, comme pour [l'éditeur web](editeur-web.md).

```bash
./dev.sh start Backups/Backup001.bkf     # depuis la racine du dépôt
./dev.sh start                           # écran d'accueil, puis Fichier > Ouvrir…
```

Le chemin passé en argument est relatif au dossier d'où la commande est tapée.
`./dev.sh start` prépare d'abord ce qui manque, comme `./dev.sh serve` (venv,
dépendances, build de l'interface si une source a changé, paquets de `desktop/`),
puis lance `npm start` dans `desktop/`. Au premier lancement, Electron télécharge
son exécutable.

`npm start` (`npm start -- FICHIER`) lance directement Electron, sans rien
préparer : si le venv ou l'interface construite manquent, l'application le
signale et invite à lancer `./dev.sh start`.

### Ubuntu 24.04 et suivants : profil AppArmor

Ces versions d'Ubuntu interdisent par défaut les « user namespaces » non
privilégiés (`kernel.apparmor_restrict_unprivileged_userns = 1`). Or Chromium,
et donc Electron, s'en sert pour isoler ses processus. Sans autorisation,
Electron s'arrête au démarrage :

```
The SUID sandbox helper binary was found, but is not configured correctly.
```

Chrome et VS Code ont pour cela un profil AppArmor dans `/etc/apparmor.d`. Il en
faut un pour l'Electron de `desktop/node_modules`, à installer une fois :

```bash
desktop/apparmor.sh | sudo tee /etc/apparmor.d/strike-kit-editor-dev
sudo apparmor_parser -r /etc/apparmor.d/strike-kit-editor-dev
```

`desktop/apparmor.sh` affiche le profil, avec le chemin de l'exécutable de ce
dépôt. Ce chemin ne change pas avec `npm ci` ; il faut en revanche réinstaller le
profil si le dépôt est déplacé. Le profil n'ajoute aucune restriction
(`unconfined`) : il autorise seulement les user namespaces, et la sandbox de
Chromium reste active. Tant que le profil manque, `npm start` affiche un
avertissement avant de lancer Electron.

Autre solution, à refaire après chaque réinstallation d'Electron : donner
`chrome-sandbox` à root avec le mode 4755
(`sudo chown root:root desktop/node_modules/electron/dist/chrome-sandbox && sudo chmod 4755 desktop/node_modules/electron/dist/chrome-sandbox`).

## Serveur figé

PyInstaller fige le serveur Python dans un dossier autonome, sans besoin de
Python ni du `.venv` : l'exécutable, ses bibliothèques et l'interface construite.
C'est lui que le [paquet .deb](#paquet-deb) embarque.

```bash
./dev.sh freeze                  # → desktop/build/strike-server/ (ignoré par Git)
./dev.sh start --frozen Backups/Backup001.bkf
```

`./dev.sh start --frozen` reconstruit d'abord le serveur figé s'il manque ou si
une de ses sources a changé (sans relancer le test de fumée), puis lance
l'application avec `STRIKE_SERVER=desktop/build/strike-server/strike-server`.

`./dev.sh freeze` construit l'interface et le serveur figé, puis lance son test
de fumée : depuis un dossier temporaire, avec un environnement minimal,
l'exécutable doit ouvrir la sauvegarde de référence, servir un kit, un WAV et
l'interface, et refuser l'accès sans jeton. La CI fait de même (job « Serveur
figé »).

- Recette : `desktop/strike-server.spec`, point d'entrée `desktop/strike_server.py`
  (mêmes options que `python -m editor`).
- Les symboles de débogage sont retirés (`strip`) : avec un Python compilé
  localement (asdf, pyenv), le dossier passe de 73 à 33 Mo.
- Il est construit pour la plateforme et la version de Python de la machine qui
  le construit.

L'application lance le serveur désigné par `STRIKE_SERVER` s'il est défini, puis,
une fois empaquetée, celui de ses ressources (`strike-server/`), et sinon le
Python du `.venv`.

## Paquet .deb

```bash
./dev.sh package                                              # → desktop/dist/strike-kit-editor_0.3.0_amd64.deb
sudo apt install ./desktop/dist/strike-kit-editor_0.3.0_amd64.deb
sudo apt remove strike-kit-editor                             # désinstallation
```

`./dev.sh package` enchaîne le build de l'interface, le serveur figé et son test
de fumée, puis electron-builder (`npm run package` dans `desktop/`). Il vérifie
enfin que le paquet contient le serveur figé, l'interface et l'application.
Le numéro de version est celui de `desktop/package.json`.

Le paquet (environ 110 Mo) installe :

- l'application dans `/opt/Strike Kit Editor/`, avec le serveur figé dans
  `resources/strike-server/` ; la commande `strike-kit-editor` ;
- une entrée dans le menu des applications, avec son icône ;
- les types de fichier `.bkf` et `.fac` : un double-clic sur une sauvegarde dans
  le gestionnaire de fichiers l'ouvre dans l'application (dans la fenêtre déjà
  ouverte s'il y en a une) ;
- sur Ubuntu 24.04 et suivants, un profil AppArmor
  (`/etc/apparmor.d/strike-kit-editor`) qui permet la sandbox de Chromium : rien
  à faire à la main, contrairement au [développement](#ubuntu-2404-et-suivants--profil-apparmor).

L'icône est `desktop/build-resources/icon.svg` ; `icon.png` en est le rendu à
512 px, refait avec `desktop/build-resources/render-icon.cjs` (voir son en-tête).

## Fonctionnement

- **Serveur** : l'application lance le serveur (`python -m editor` ou le serveur
  figé) avec `--port 0 --watch-stdin`
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
- **Menu** : barre masquée, la touche `Alt` l'affiche ; les raccourcis restent
  actifs quand elle est masquée. *Fichier* (Ouvrir… `Ctrl+O`, Enregistrer `Ctrl+S`, Enregistrer
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
| `desktop/package.json` (`build`) | configuration d'electron-builder : paquet .deb, types de fichier, icône |
| `desktop/build-resources/` | icône (SVG source, PNG 512 px et script de rendu) |
| `desktop/apparmor.sh` | profil AppArmor de l'Electron de développement, et vérification avant `npm start` |
| `desktop/server.js` | choix et lancement du serveur, sans dépendance à Electron |
| `desktop/strike-server.spec`, `desktop/strike_server.py` | recette PyInstaller du serveur figé et son point d'entrée |
| `desktop/test/` | tests `node:test` (`npm test`) ; un faux serveur simule les cas d'erreur |

`npm test` vérifie la lecture de la ligne « prêt », les arguments, les échecs
(serveur arrêté, muet, introuvable) et l'arrêt ; un test de fumée lance le vrai
serveur sur la sauvegarde de référence quand `.venv` existe, et le serveur figé
quand `STRIKE_SERVER` le désigne (`./dev.sh freeze`).

## Dépannage

- `The SUID sandbox helper binary was found, but is not configured correctly` :
  voir [le profil AppArmor](#ubuntu-2404-et-suivants--profil-apparmor).
- Sous Wayland, Chromium écrit des erreurs Vulkan au démarrage
  (`'--ozone-platform=wayland' is not compatible with Vulkan`) : elles sont sans
  conséquence.
