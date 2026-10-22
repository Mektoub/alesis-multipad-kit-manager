# Changelog

## 0.4.0 — en cours

- Éditeur web : grille des 9 pads centrée dans l'espace ; le pad sélectionné prend une couleur de fond (au lieu d'une simple bordure rouge).

## 0.3.3 — Corrections

- Paramètres identifiés en comparant deux sauvegardes de l'appareil : Curve, Kit FX Level, Sync Mode (`params.sync_mode`, octet fixe de l'emplacement), Play Beat et Stop Beat (`light.play_beat` / `stop_beat`), Playback Mode (0–9, FS4 = 9 au-delà du max déclaré) et Poly/Mono des waves. Les clés JSON `p13`, `p16`, wave `p09` et `p19` deviennent `curve`, `kit_fx_level`, `playback_mode` et `poly_mono`.
- Éditeur web : réglages rangés par sections, comme sur l'appareil (pad : Feel, Control, Output, Light, Group ; waves : Mode, Mix), aussi dans *Modifier plusieurs pads* ; « Control » s'appelle « Mode ».
- Test de bout en bout de l'application de bureau (Playwright, `desktop/e2e/`, `./dev.sh e2e`, inclus dans `./dev.sh all`) : ouverture d'une copie de la sauvegarde de référence, modification, enregistrement par le menu et relecture, confirmation de fermeture avec des modifications non enregistrées. Lancé par la CI sous Ubuntu 24.04 (xvfb).
- Liste de vérifications manuelles par système avant une release (`docs/application-bureau.md`).

## 0.3.2 — Gestion des versions / releases

- Release GitHub sur un tag `vX.Y.Z` (workflow « Release », `release.yml`) : versions du commit vérifiées, paquets des trois systèmes construits (`build.yml`, qui ne se lance plus lui-même sur un tag), puis release en brouillon avec les paquets et les notes du CHANGELOG.
- Paquets Windows et macOS nommés `alesis-kit-manager-X.Y.Z-<win|mac>-<arch>[-setup].<ext>` (sans espaces) ; le build vérifie que chaque paquet attendu porte la version de `app-names.json` (et la version du .deb), ainsi que `--version` du serveur figé.
- `scripts/verifier-version.py` : cohérence de la version dans `app-names.json`, les `package.json` et les locks (`./dev.sh lint` / `all`, CI) ; avec `X.Y.Z`, vérifie aussi la section du CHANGELOG ; `--notes` donne les notes de version (utilisé par `./dev.sh release` et la release GitHub).
- Hooks Git (`.githooks/`, activés par `./dev.sh`) : `git tag vX.Y.Z` et le push d'un tag sont refusés si les versions du commit ne sont pas X.Y.Z.
- `editor/web/package.json` aligné sur la version de l'application (0.3.1).
- Version affichée dans l'interface (à côté du titre) et dans le menu *Aide › À propos* de l'application ; `alesis-kit-manager --version` et `python -m editor --version` (serveur figé compris) l'affichent et quittent. Le test Docker du .deb les vérifie.
- `./dev.sh release X.Y.Z` : sur `main`, arbre propre et section `## X.Y.Z` présente dans le CHANGELOG, met la version dans `app-names.json`, `desktop/package.json` et `editor/web/package.json` (+ locks), commite « Version X.Y.Z » et crée le tag annoté `vX.Y.Z` (message : la section du CHANGELOG), sans le pousser.
- La version de l'application est aussi dans `app-names.json` ; l'API l'affiche (`/docs`, au lieu de la 0.1.0 par défaut de FastAPI). `editor/web/package.json` passe de 0.1.0 à la version de l'application au prochain `release`.

## 0.3.1 — Corrections GitHub Actions

- CI : actions GitHub en v7 (fin des avertissements Node 20) ; paquet Linux et job « Serveur figé » construits sur `ubuntu-24.04` (`ubuntu-latest` passe à Ubuntu 26, dont la glibc rendrait le .deb inutilisable sur 24.04). Runners Windows et macOS figés aussi : `windows-2025`, `macos-26`.
- Correction : les tests de `desktop/server.js` échouaient sous Windows (build « Package » de la 0.3.0) ; les chemins du serveur à lancer suivent maintenant la plateforme indiquée (`path.win32` / `path.posix`), et un test vérifie le cas Windows sur tous les systèmes.
- Version de l'application : 0.3.1 (`desktop/package.json`, `package-lock.json`).

## 0.3.0 — Passage à une application desktop avec electron

- `strike_kits.py` devient le paquet `strike_kits/` (code dans `__init__.py`, imports inchangés) ; ligne de commande : `python3 -m strike_kits export|import …` au lieu de `python3 strike_kits.py …`.
- CI factorisée : préparation commune des jobs dans l'action composite `.github/actions/setup` (versions de Python et de Node à un seul endroit) ; le job « Serveur figé » de `ci.yml` réutilise le workflow « Paquets » (`workflow_call`, sous Linux, sans paquet) au lieu de `./dev.sh freeze`.
- Paquets Windows (installateur NSIS en un clic, zip) et macOS Apple Silicon (dmg, zip), non signés : workflow « Paquets » (`.github/workflows/build.yml`), un runner par système, sur un tag `v*` ou à la main ; paquets en artefacts. Nom affiché « Alesis Kit Manager » sous Windows et macOS. `npm run package` construit les paquets du système courant.
- Dossiers autorisés par défaut selon le système : `/Volumes` sous macOS, tous les lecteurs sauf celui du système sous Windows.
- Serveur lancé sans fenêtre de console sous Windows ; test de fumée du serveur figé utilisable sous Windows et avec un chemin relatif.
- Un seul mode de fonctionnement, celui de l'application Electron : jeton exigé sur `/api/*`, fichiers désignés par chemin absolu. Le mode « développement » (dossier `--root`, liste `GET /api/backups`) est retiré.
- `editeur.sh FICHIER` : lancement local rapide sur une sauvegarde (usage affiché sans paramètre) ; `python -m editor --open FICHIER`. En local, un jeton est créé et transmis au navigateur dans l'adresse (`#token=…`), puis conservé pour l'onglet.
- Interface : ouverture par chemin complet, champ « Ouvrir » mis à jour après « Enregistrer sous ».
- Interface en mode bureau (étape 2 du passage à Electron) : si l'application expose `window.strikeDesktop` (jeton, boîtes natives `openFile` / `saveFile`, `setDirty`), *Ouvrir…* et *Enregistrer sous…* passent par les boîtes de dialogue du système, et l'état « non enregistré » lui est signalé. Bouchon de développement (`#…&desktop=fake`, absent du build) pour tester ce mode dans le navigateur.
- Application de bureau Electron (`desktop/`, étape 3) : `npm start [-- FICHIER]` lance le serveur Python avec un jeton aléatoire et ouvre l'éditeur dans une fenêtre ; menu Fichier (Ouvrir, Enregistrer, Enregistrer sous, Quitter) avec raccourcis, boîtes de dialogue natives, une seule instance, confirmation de fermeture (Enregistrer / Quitter sans enregistrer / Annuler), arrêt du serveur en quittant ou en cas de plantage. Tests `node:test`, ESLint ; dans `dev.sh` et la CI (job « desktop »).
- `./dev.sh start [--frozen] [FICHIER]` : lance l'application de bureau, avec le serveur figé si demandé (reconstruit si une source a changé).
- Identifiants internes alignés sur le nom de l'application : `KITMANAGER_TOKEN`, `KITMANAGER_SERVER`, en-tête `X-KitManager-Token`, `window.kitManagerDesktop`, messages `kitmanager:…` entre la fenêtre et Electron, types de fichier `application/x-kitmanager-bkf` / `-fac` (auparavant `STRIKE_…`, `X-Strike-Token`, `strikeDesktop`, `strike:…`, `x-strike-…`).
- Noms de l'application centralisés dans `app-names.json` : « Alesis Strike Multipad Kit Manager » (affichage), « Alesis Kit Manager » (menu), `alesis-kit-manager` (paquet, exécutable, `/opt/alesis-kit-manager`, profils AppArmor), `AlesisKitManager` (`~/.config/AlesisKitManager`), serveur figé `alesis-kit-manager-server` (recette `desktop/server.spec`, point d'entrée `desktop/server_entry.py`) ; lus par Vite, electron-builder (configuration déplacée dans `desktop/electron-builder.config.mjs`), `main.js`, le serveur et les scripts.
- `./dev.sh test-deb` : installe le .deb dans un conteneur Docker Ubuntu 24.04 propre et vérifie fichiers, types de fichier, serveur intégré, lancement d'Electron (Xvfb) et désinstallation.
- Paquet .deb : dépendance `libasound2t64 | libasound2` ajoutée (Electron ne démarrait pas sans elle) ; chemin d'installation sans espaces (`chrome-sandbox` échouait avec un chemin qui en contient).
- Le serveur n'ouvre et n'enregistre que dans le dossier personnel, les supports amovibles de l'utilisateur (`/media/<utilisateur>`, `/run/media/<utilisateur>`) et les dossiers ajoutés par `--allow DOSSIER` (aussi pour `./dev.sh serve`), chemins résolus ; ailleurs : erreur 403.
- Documentation : rôle du profil AppArmor de développement, risques et retrait (`docs/application-bureau.md`).
- Paquet .deb de l'application de bureau (étape 5) : `./dev.sh package` (electron-builder) ; serveur figé embarqué, entrée de menu et icône, ouverture des `.bkf` / `.fac` par double-clic (URL `file://` acceptées en argument), profil AppArmor installé par le paquet.
- `./dev.sh serve FICHIER` remplace `editeur.sh` (supprimé) : éditeur dans le navigateur. Une seule préparation, dans `dev.sh` (venv avec `requirements-dev.txt`, build de l'interface si une source a changé) ; `scripts/preparer.sh` est supprimé. `npm start` ne prépare plus rien et signale un venv ou une interface manquants.
- Serveur figé (étape 4) : `./dev.sh freeze` construit avec PyInstaller un dossier autonome `desktop/build/strike-server/` (serveur et interface, 33 Mo), puis le teste hors du dépôt ; job CI « Serveur figé ». L'application lance le serveur désigné par `STRIKE_SERVER`, celui de ses ressources une fois empaquetée, sinon le Python du `.venv`.
- Application de bureau : barre de menus masquée par défaut, affichée avec la touche Alt.
- `desktop/apparmor.sh` : profil AppArmor pour l'Electron de développement (Ubuntu 24.04 et suivants bloquent sa sandbox) ; `npm start` prévient tant qu'il manque.
- `python -m editor --watch-stdin` : le serveur s'arrête quand son entrée standard se ferme.
- Interface : commandes de l'application de bureau (`strikeDesktop.onCommand`).
- `scripts/preparer.sh` : préparation du venv et de l'interface, partagée par `editeur.sh` et `npm start`.
- Écoute des samples (▶) : le WAV est téléchargé avec le jeton puis lu depuis un blob (la balise audio ne pouvait pas envoyer le jeton).
- Tests de l'interface avec Vitest et jsdom (`npm test`), lancés par `dev.sh test` / `all` et par la CI.
- Intégration continue GitHub Actions (`.github/workflows/ci.yml`) : sur chaque push sur `main` et chaque pull request, `ruff check`, `ruff format --check` et tests sous Python 3.14 ; ESLint et build de l'interface sous Node 24.
- Analyse du code : ruff (`pyproject.toml`, `requirements-dev.txt`) avec les règles E, F, W, I, B et formatage automatique ; ESLint avec les règles recommandées JavaScript et Svelte (`editor/web/eslint.config.js`, `npm run lint`).
- `dev.sh` : `lint [--fix]`, `test [TESTS…]`, `build`, `all` (bilan final) ; installe au besoin les dépendances de développement.
- Correction : l'avertissement « Interface non construite » part sur la sortie d'erreur ; il faisait échouer le test d'arrêt par Ctrl+C dans la CI, où l'interface n'est pas construite.
- Code mis en conformité : formatage ruff, `raise … from`, clés des listes `{#each}`, sélections des fenêtres en `SvelteSet`.

## 0.2.0 — 2026-10-16

- Éditeur web local (`python -m editor`) : FastAPI + Svelte, édition des kits, choix et écoute des samples, ajout de WAV, enregistrement sous un nouveau fichier.
- Classe `Backup` : sauvegarde `.bkf` / `.fac` éditable en mémoire, utilisée par l'éditeur et par `import` / `export`.
- Éditeur web : grille des pads disposée comme sur l'appareil (7-8-9 en haut, deux fois moins hauts, puis 4-5-6 et 1-2-3).
- Éditeur web : recopie des réglages d'un pad vers d'autres (sections au choix, note MIDI conservée par défaut) ; badge du Control (« Click ») sur les pads à la place de la note MIDI.
- Fonction `copy_slot_settings` et route `POST /api/kits/{num}/copy`.
- Éditeur web : déplacer, échanger ou dupliquer un kit vers un autre numéro (`Backup.copy_kit`, `Backup.swap_kits`, route `POST /api/kits/{num}/transfer`).
- Éditeur web : les flèches du champ tempo avancent de 1 BPM (au lieu de 0,1) ; une valeur décimale reste saisissable.
- Éditeur web : les infobulles indiquent la valeur par défaut du réglage pour le pad affiché (relevée dans un kit vide de l'appareil ; `/api/meta` expose `defaults`).
- Éditeur web : « Modifier plusieurs pads… » donne une même valeur à un réglage sur une sélection de pads (`set_slots_value`, `Backup.set_slots`, route `POST /api/kits/{num}/set`).
- Serveur de l'éditeur pilotable par l'application de bureau (étape 1 du passage à Electron) : jeton `STRIKE_TOKEN` exigé sur `/api/*` (en-tête `X-Strike-Token`), `--port 0` et ligne `{"ready": true, "port": N}` une fois à l'écoute ; en mode bureau, fichiers ouverts et enregistrés par chemin absolu, n'importe où.
- « Enregistrer » écrit dans le fichier ouvert (auparavant, seul « Enregistrer sous » existait et la sauvegarde d'origine était protégée) ; au premier enregistrement de chaque session sur un fichier d'origine, son état précédent est copié dans `<fichier>.N.bak`.
- Arrêt de l'éditeur par Ctrl+C sans trace d'erreur (`KeyboardInterrupt`), avec le message « Éditeur arrêté. ».
- Ouvrir une autre sauvegarde avec des modifications non enregistrées est refusé par le serveur (409) sauf confirmation (`force`) ; l'interface demande confirmation.
- `editeur.sh` : dossier de sauvegardes par défaut `Backups/` (sinon `Strike/`, puis le dossier courant) ; les `.bkf` / `.fac` de `Backups/` sont ignorés par Git.
- Éditeur web : la modification groupée peut s'appliquer aux mêmes pads de plusieurs kits, tout ou rien (`Backup.set_slots_in_kits`, route `POST /api/kits/set`).
- Tests : une seule sauvegarde de référence, `tests/ressources/Backup001.bkf` (5 Mo, construite par `tests/construire_reference.py`), indépendante des sauvegardes de travail de `Strike/` ; tests déplacés dans `tests/`, `.fac` construit en mémoire. `Bkf.remove_last_sample` (inverse de `add_sample`, réservé aux tests).
- Éditeur web : infobulle décrivant chaque réglage (paramètres de pad et de wave, kit, éclairage, sample, vélocité), d'après le manuel ; `/api/meta` expose `description` et `help`.
- Script `editeur.sh` : lance l'éditeur en créant ou mettant à jour le venv, les dépendances et l'interface au besoin.
- Correction : dans les pads 1 à 8 des kits `KITC`, les champs dont l'en-tête est recouvert par d'autres données étaient omis ; leur octet valeur est désormais lu et modifiable, et tous les pads affichent les mêmes champs.
- Documentation réorganisée : README réduit aux commandes, un guide par cas d'usage dans `docs/` (modifier un kit, ajouter un sample, éditeur web, contenu de l'export, paramètres, limites, développement).

## 0.1.0 — 2026-10-16

- Export des kits `.bkf` / `.fac` en JSON et import vers une nouvelle sauvegarde (round-trip à l'identique).
- Recalcul des sommes de contrôle (kit, en-têtes `PACKBKF` / `FILEH`) ; validation des plages de valeurs.
- Catalogue des samples (`samples.json`) ; samples désignables par id ou par nom.
- Documentation des formats `.bkf`, `.fac` et `.kit` dans `docs/`, dont `.had` et les listes de samples.
- Ajout de samples WAV depuis le dossier `wav/` de l'export (reproduit à l'identique l'import fait par l'appareil).
- Kits `KITC` : lecture et modification des valeurs des emplacements 1 à 8.
- Paramètres de pad identifiés : `control` (`p14`, 3 = Click On/Off) et `audio_output` (`p0f`, 4 = Aux+Phone).
- Vélocités de wave (`velocity_low`, `velocity_high`) ; correction : le sample d'une wave dont la vélocité n'est pas 0–127 n'était ni exporté ni modifiable.
- Export des WAV des samples utilisateur dans `wav/` (option `--no-wav`) ; l'import ignore les WAV déjà présents (par nom ou par contenu).
