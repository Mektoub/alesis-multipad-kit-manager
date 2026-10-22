# Application de bureau

Alesis Strike Multipad Kit Manager (nom court : Alesis Kit Manager) :
application Electron autour de l'éditeur, la même interface, dans sa propre
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
desktop/apparmor.sh | sudo tee /etc/apparmor.d/alesis-kit-manager-dev
sudo apparmor_parser -r /etc/apparmor.d/alesis-kit-manager-dev
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

#### Pourquoi ce profil, et quel risque

AppArmor associe des profils à des exécutables, désignés par leur chemin, pour
restreindre ce qu'ils peuvent faire (fichiers, réseau, privilèges). La plupart
des programmes n'en ont pas et tournent sans restriction (`unconfined`).

Les user namespaces permettent à un programme ordinaire de se créer un
environnement isolé où il se croit root. Les sandboxes s'en servent (Chromium,
Flatpak, Podman sans root), mais ils exposent aussi au programme des parties du
noyau normalement réservées à root, par lesquelles sont passées de nombreuses
élévations de privilèges. Ubuntu les réserve donc aux programmes dont le profil
le permet (règle `userns`).

Chromium y enferme les processus qui affichent les pages : une page qui
exploiterait une faille resterait isolée, sans accès aux fichiers. Faute de user
namespaces, il lui faut l'assistant `chrome-sandbox` appartenant à root ; sans
l'un ni l'autre, Electron refuse de démarrer plutôt que de tourner sans
protection.

Le profil de développement n'ajoute aucune restriction (`unconfined`) et
autorise seulement les user namespaces (`userns`), pour ce seul exécutable : il
lui rend le comportement d'avant Ubuntu 24.04. Chrome, VS Code et le
[paquet .deb](#paquet-deb) ont le même.

- **Pour l'application**, c'est un gain : la sandbox de Chromium fonctionne,
  alors que l'alternative courante, `--no-sandbox`, la désactive.
- **Pour le système**, l'affaiblissement est réel mais limité, et tient au
  chemin : le profil vise un fichier du dossier personnel, modifiable par
  l'utilisateur. Un programme lancé sous ce compte (un paquet npm malveillant,
  par exemple) pourrait remplacer l'exécutable et hériter du droit `userns`,
  puis tenter d'exploiter une faille du noyau pour devenir root. Il faut pour
  cela qu'un attaquant exécute déjà du code sous ce compte : la restriction
  d'Ubuntu protège surtout contre cette étape suivante, et le profil la
  contourne pour ce chemin.
- **Le profil du paquet .deb n'a pas ce défaut** : il vise
  `/opt/alesis-kit-manager/`, qui appartient à root ; personne d'autre ne peut y
  remplacer l'exécutable.
- **Les autres solutions** : `chrome-sandbox` à root en 4755 ajoute un programme
  privilégié au milieu de fichiers modifiables par l'utilisateur (risque faible) ;
  `--no-sandbox` ne change rien au système, mais n'offre aucune protection si une
  page exploitait une faille (risque faible ici, la fenêtre n'affichant que le
  serveur local).

Pour l'usage courant, mieux vaut donc le paquet .deb, et ne garder le profil de
développement que tant que l'on développe. Pour le retirer :

```bash
sudo apparmor_parser -R /etc/apparmor.d/alesis-kit-manager-dev
sudo rm /etc/apparmor.d/alesis-kit-manager-dev
```

Ensuite, `npm start` affiche de nouveau son avertissement, et Electron ne démarre
plus en développement.

## Serveur figé

PyInstaller fige le serveur Python dans un dossier autonome, sans besoin de
Python ni du `.venv` : l'exécutable, ses bibliothèques et l'interface construite.
C'est lui que le [paquet .deb](#paquet-deb) embarque.

```bash
./dev.sh freeze                  # → desktop/build/alesis-kit-manager-server/ (ignoré par Git)
./dev.sh start --frozen Backups/Backup001.bkf
```

`./dev.sh start --frozen` reconstruit d'abord le serveur figé s'il manque ou si
une de ses sources a changé (sans relancer le test de fumée), puis lance
l'application avec `KITMANAGER_SERVER=desktop/build/alesis-kit-manager-server/alesis-kit-manager-server`.

`./dev.sh freeze` construit l'interface et le serveur figé, puis lance son test
de fumée : depuis un dossier temporaire, avec un environnement minimal,
l'exécutable doit ouvrir la sauvegarde de référence, servir un kit, un WAV et
l'interface, et refuser l'accès sans jeton. La CI fait de même (job « Serveur
figé »).

- Recette : `desktop/server.spec`, point d'entrée `desktop/server_entry.py`
  (mêmes options que `python -m editor`).
- Les symboles de débogage sont retirés (`strip`) : avec un Python compilé
  localement (asdf, pyenv), le dossier passe de 73 à 33 Mo.
- Il est construit pour la plateforme et la version de Python de la machine qui
  le construit.

L'application lance le serveur désigné par `KITMANAGER_SERVER` s'il est défini, puis,
une fois empaquetée, celui de ses ressources (`alesis-kit-manager-server/`), et sinon le
Python du `.venv`.

## Paquet .deb

```bash
./dev.sh package                                              # → desktop/dist/alesis-kit-manager_<version>_amd64.deb
sudo apt install ./desktop/dist/alesis-kit-manager_*_amd64.deb
sudo apt remove alesis-kit-manager                            # désinstallation
```

`./dev.sh package` enchaîne le build de l'interface, le serveur figé et son test
de fumée, puis electron-builder (`npm run package` dans `desktop/`). Il vérifie
enfin que le paquet contient le serveur figé, l'interface et l'application.
Le numéro de version est celui de `desktop/package.json`.

Le paquet (environ 110 Mo) installe :

- l'application dans `/opt/alesis-kit-manager/`, avec le serveur figé dans
  `resources/alesis-kit-manager-server/` ; la commande `alesis-kit-manager` ;
- une entrée « Alesis Kit Manager » dans le menu des applications, avec son icône ;
- les types de fichier `.bkf` et `.fac` : un double-clic sur une sauvegarde dans
  le gestionnaire de fichiers l'ouvre dans l'application (dans la fenêtre déjà
  ouverte s'il y en a une) ;
- sur Ubuntu 24.04 et suivants, un profil AppArmor
  (`/etc/apparmor.d/alesis-kit-manager`) qui permet la sandbox de Chromium : rien
  à faire à la main, contrairement au [développement](#ubuntu-2404-et-suivants--profil-apparmor).

Aux dépendances par
défaut d'electron-builder, le paquet ajoute `libasound2t64 | libasound2`, sans
laquelle Electron ne démarre pas sur un système sans son installé.

### Noms de l'application

Tous les noms viennent de `app-names.json`, à la racine du dépôt :

| Clé | Valeur | Usage |
|---|---|---|
| `long` | Alesis Strike Multipad Kit Manager | affichage : titre de la fenêtre et de la page, en-tête de l'interface, boîtes de dialogue, description du paquet |
| `short` | Alesis Kit Manager | affichage court : entrée du menu des applications ; sous Windows et macOS, nom de l'application installée (`Alesis Kit Manager.app`, menu Démarrer) |
| `id` | alesis-kit-manager | chemins : `/opt/<id>`, exécutable, paquet .deb, entrée de menu `<id>.desktop`, profils AppArmor, serveur figé `<id>-server` |
| `config` | AlesisKitManager | dossier de configuration : `~/.config/<config>` (Windows : `%APPDATA%\<config>`, macOS : `~/Library/Application Support/<config>`) |
| `version` | 0.3.1 | version de l'application vue par le serveur (`/docs`) ; mise à jour par `./dev.sh release` avec celles des `package.json` (voir [Nouvelle version](developpement.md#nouvelle-version)) |

Ils sont lus par Vite (`editor/web/vite.config.js` : `<title>` et `__APP_NAMES__`),
PyInstaller (`desktop/server.spec`), electron-builder (`desktop/electron-builder.config.mjs`), `desktop/main.js` (qui
les retrouve dans le `package.json` de l'application empaquetée), le serveur
(titre de sa documentation `/docs`) et les scripts `dev.sh`, `desktop/apparmor.sh` et
`desktop/test-deb/verifier.sh`. L'identifiant ne doit pas contenir d'espaces :
`chrome-sandbox` ne supporte pas un chemin d'installation qui en contient.

### Tester l'installation dans un conteneur

```bash
./dev.sh test-deb
```

Installe le paquet de `desktop/dist/` dans un conteneur Docker Ubuntu 24.04
propre (`desktop/test-deb/Dockerfile`, sans Python ni Node), puis vérifie
(`desktop/test-deb/verifier.sh`) :

- l'installation par `apt` (dépendances, script d'installation) ;
- les fichiers installés, l'entrée de menu (`desktop-file-validate`), l'absence
  de Python ;
- les types de fichier `.bkf` / `.fac` et l'application qui leur est associée ;
- le serveur intégré : test de fumée sur la sauvegarde de référence ;
- l'application : lancée sous Xvfb par un utilisateur non root, elle doit ouvrir
  sa fenêtre sur le serveur local et charger l'éditeur, puis arrêter le serveur en
  quittant ;
- la désinstallation.

Le paquet est d'abord reconstruit s'il manque ou si une de ses sources a changé.
Le conteneur est lancé avec `--security-opt seccomp=unconfined` : le filtre
seccomp par défaut de Docker interdit les user namespaces, et la sandbox de
Chromium ne pourrait pas démarrer. Le profil AppArmor et l'intégration réelle au
bureau (menu, double-clic, boîtes de dialogue) ne se vérifient pas dans un
conteneur.

L'icône est `desktop/build-resources/icon.svg` ; `icon.png` en est le rendu à
512 px, refait avec `desktop/build-resources/render-icon.cjs` (voir son en-tête).

## Paquets Windows et macOS

PyInstaller ne fait pas de compilation croisée : le serveur figé se construit sur
le système visé. Les paquets des trois systèmes sont donc construits par GitHub
Actions (`.github/workflows/build.yml`, « Package »), sur un runner par système :

| Runner | Paquets (`desktop/dist/`) |
|---|---|
| `ubuntu-24.04` | `.deb` (pas `ubuntu-latest`, passé à Ubuntu 26 : le serveur figé dépend de la glibc du système de build, le paquet doit aussi marcher sur 24.04) |
| `windows-2025` (x64) | installateur NSIS `.exe`, archive `.zip` |
| `macos-26` (Apple Silicon, arm64) | image `.dmg`, archive `.zip` |

Les runners sont figés plutôt que `*-latest`, pour qu'un build ne change pas sans
modification du dépôt. Quand GitHub annonce le retrait d'une image, changer son
label dans `build.yml` (écrit deux fois, voir le commentaire en tête). Sous Windows
et macOS, la version du runner ne fixe pas le système minimal des utilisateurs
(qui dépend de Python et d'Electron) ; sous Linux, si : voir `ubuntu-24.04`.

Le workflow se lance à la main depuis l'onglet Actions (« Run workflow »), ou par
le workflow « Release » sur un tag `vX.Y.Z`, qui publie ensuite les paquets dans
une release GitHub en brouillon (voir [Nouvelle version](developpement.md#nouvelle-version)).
Chaque job vérifie la cohérence des versions, construit l'interface, fige le
serveur, le teste (test de fumée, `--version`), lance `npm run package`, puis
vérifie que les paquets attendus portent la version de `app-names.json` ; ce
sont les artefacts de l'exécution (`paquet-Linux`, `paquet-Windows`,
`paquet-macOS`). Les étapes sont écrites dans le workflow, sans `dev.sh` (Linux
seulement).

| Système | Paquets |
|---|---|
| Linux | `alesis-kit-manager_X.Y.Z_amd64.deb` (nom Debian ; version du paquet vérifiée) |
| Windows | `alesis-kit-manager-X.Y.Z-win-x64-setup.exe`, `alesis-kit-manager-X.Y.Z-win-x64.zip` |
| macOS | `alesis-kit-manager-X.Y.Z-mac-arm64.dmg`, `alesis-kit-manager-X.Y.Z-mac-arm64.zip` |

En local, `npm run package` construit les paquets du système courant (cibles de
`desktop/electron-builder.config.mjs`) ; sous Linux, passer par `./dev.sh package`.

- **Windows** : installation en un clic, pour l'utilisateur courant
  (`%LOCALAPPDATA%\Programs\Alesis Kit Manager`), sans droits administrateur,
  avec un raccourci « Alesis Kit Manager » et l'ouverture des `.bkf` / `.fac` par
  double-clic. L'archive `.zip` s'utilise sans installation.
- **macOS** : `Alesis Kit Manager.app`, pour les Mac Apple Silicon seulement.

Les paquets ne sont pas signés (pas de certificat). Windows SmartScreen affiche
« Windows a protégé votre ordinateur » : *Informations complémentaires*, puis
*Exécuter quand même*. Sous macOS, l'application n'a qu'une signature ad hoc
(indispensable sur Apple Silicon) et n'est pas notarisée : Gatekeeper la bloque
au premier lancement ; clic droit sur l'application, *Ouvrir*, ou bien
`xattr -dr com.apple.quarantine "/Applications/Alesis Kit Manager.app"`.

Les dossiers autorisés par défaut dépendent du système (voir
[l'éditeur web](editeur-web.md#dossiers-autorisés)).

## Fonctionnement

- **Serveur** : l'application lance le serveur (`python -m editor` ou le serveur
  figé) avec `--port 0 --watch-stdin`
  avec un jeton aléatoire (`KITMANAGER_TOKEN`), attend la ligne
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
  développement), *Aide* (À propos : nom et version).
- **Version** : affichée à côté du titre de l'interface et dans *Aide › À
  propos* ; `alesis-kit-manager --version` l'écrit dans le terminal et quitte
  sans ouvrir de fenêtre (`npx electron . --version` en développement ; rien ne
  s'affiche sous Windows, où l'application n'a pas de console). Le serveur figé
  a aussi `--version`.
- **Fermeture** : avec des modifications non enregistrées, une boîte propose
  *Enregistrer* (dans le fichier ouvert, avec la copie `.bak` habituelle),
  *Quitter sans enregistrer* ou *Annuler*. Une modification encore en attente
  d'envoi au serveur est comptée.
- **Fichiers** : le serveur n'ouvre et n'enregistre que dans le dossier
  personnel et les supports amovibles de l'utilisateur (voir
  [Dossiers autorisés](editeur-web.md#dossiers-autorisés)) ; les boîtes de
  dialogue permettent de parcourir tout le disque, mais un fichier choisi ailleurs
  est refusé, avec un message dans la fenêtre.
- **Sécurité** : la page n'a pas accès à Node (`contextIsolation`, `sandbox`) ;
  le préchargement (`desktop/preload.cjs`) n'expose que `window.kitManagerDesktop`
  (voir [Mode bureau](editeur-web.md#mode-bureau)), à la seule page du serveur
  local. La navigation est limitée à ce serveur ; les liens externes s'ouvrent
  dans le navigateur.

## Fichiers

| Chemin | Rôle |
|---|---|
| `desktop/main.js` | processus principal : serveur, fenêtre, menu, boîtes de dialogue, fermeture |
| `desktop/preload.cjs` | pont `window.kitManagerDesktop` |
| `app-names.json` | noms de l'application (voir [Noms de l'application](#noms-de-lapplication)) |
| `desktop/electron-builder.config.mjs` | configuration d'electron-builder : paquet .deb, types de fichier, icône |
| `desktop/build-resources/` | icône (SVG source, PNG 512 px et script de rendu) |
| `desktop/test-deb/` | test d'installation du paquet dans un conteneur (`./dev.sh test-deb`) |
| `desktop/apparmor.sh` | profil AppArmor de l'Electron de développement, et vérification avant `npm start` |
| `desktop/server.js` | choix et lancement du serveur, sans dépendance à Electron |
| `desktop/server.spec`, `desktop/server_entry.py` | recette PyInstaller du serveur figé et son point d'entrée |
| `desktop/test/` | tests `node:test` (`npm test`) ; un faux serveur simule les cas d'erreur |
| `desktop/e2e/` | test de bout en bout (Playwright, `npm run e2e`) |

`npm test` vérifie la lecture de la ligne « prêt », les arguments, les échecs
(serveur arrêté, muet, introuvable) et l'arrêt ; un test de fumée lance le vrai
serveur sur la sauvegarde de référence quand `.venv` existe, et le serveur figé
quand `KITMANAGER_SERVER` le désigne (`./dev.sh freeze`).

## Test de bout en bout

`./dev.sh e2e` prépare le venv et l'interface, puis lance `npm run e2e` dans
`desktop/` : Playwright (`playwright-core`, sans navigateur téléchargé) pilote
l'Electron du dépôt, avec un dossier personnel temporaire qui reçoit une copie
de `tests/ressources/Backup001.bkf`.

- La sauvegarde est passée en argument. Le test renomme le kit 031, enregistre
  par *Fichier › Enregistrer*, vérifie la copie `.bak` de l'original, puis
  relance l'application sur le fichier et relit le nouveau nom.
- Fermeture avec des modifications non enregistrées : *Annuler* garde la
  fenêtre ouverte, *Quitter sans enregistrer* ferme l'application sans toucher
  au fichier. La boîte de dialogue native est remplacée dans le processus
  principal (aucune fenêtre système à cliquer).

Le test ouvre de vraies fenêtres, quelques secondes : sous Linux sans affichage,
`xvfb-run -a ./dev.sh e2e`. Il a besoin, comme `npm start`, du
[profil AppArmor](#ubuntu-2404-et-suivants--profil-apparmor) ; avec
`KITMANAGER_SERVER`, il utilise le serveur figé. La CI le lance sous Ubuntu
24.04 seulement ; sous Windows et macOS, les paquets se vérifient à la main.

## Vérifications manuelles

Ce que le test de bout en bout ne couvre pas : son, glisser-déposer, boîtes de
dialogue natives et intégration au système. À faire sur chaque système avant de
publier une release (paquet installé : `.deb`, installateur NSIS, `.dmg`), sur une
copie d'une sauvegarde.

| Vérification | Résultat attendu |
|---|---|
| Installation, puis lancement depuis le menu des applications (raccourci « Alesis Kit Manager », Launchpad) | fenêtre ouverte, écran d'accueil ; icône de l'application |
| `--version` (Linux, macOS : `"/Applications/Alesis Kit Manager.app/Contents/MacOS/Alesis Kit Manager" --version`) | `alesis-kit-manager X.Y.Z`, sans fenêtre |
| *Aide › À propos* ; version à côté du titre | version du paquet |
| Double-clic sur un `.bkf` dans le gestionnaire de fichiers (Explorateur, Finder) | l'application s'ouvre sur ce fichier |
| Double-clic sur un deuxième fichier, l'application ouverte | ouvert dans la même fenêtre |
| *Fichier › Ouvrir…* (`Ctrl+O`, `Cmd+O` sur Mac) | boîte du système, filtre `.bkf` / `.fac` |
| Ouvrir un fichier sur une clé USB (`/media`, `/Volumes`, autre lecteur sous Windows) | ouvert ; un fichier hors des [dossiers autorisés](editeur-web.md#dossiers-autorisés) est refusé avec un message |
| Écouter un sample utilisateur (lecture du WAV) | son audible, sans erreur |
| Ajouter un sample par glisser-déposer d'un `.wav` dans le choix du sample | sample ajouté, nombre de samples perso incrémenté |
| Modifier un kit, *Enregistrer* (`Ctrl+S`) | « À jour » ; copie `<fichier>.1.bak` de l'original |
| *Enregistrer sous…* sur un fichier existant | confirmation d'écrasement par la boîte du système |
| Fermer la fenêtre avec des modifications : *Annuler*, puis *Enregistrer* | la fenêtre reste ouverte, puis le fichier est enregistré et l'application se ferme |
| Après fermeture, processus restants (`ps`, Gestionnaire des tâches, Moniteur d'activité) | aucun `alesis-kit-manager-server` |
| Désinstallation (`sudo apt remove`, Paramètres › Applications, corbeille) | application retirée ; les sauvegardes ne sont pas touchées |

Sous Windows et macOS, vérifier aussi l'avertissement au premier lancement
(SmartScreen, Gatekeeper : voir [Paquets Windows et macOS](#paquets-windows-et-macos)).

## Dépannage

- `The SUID sandbox helper binary was found, but is not configured correctly` :
  voir [le profil AppArmor](#ubuntu-2404-et-suivants--profil-apparmor).
- Sous Wayland, Chromium écrit des erreurs Vulkan au démarrage
  (`'--ozone-platform=wayland' is not compatible with Vulkan`) : elles sont sans
  conséquence.
