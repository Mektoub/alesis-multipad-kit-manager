# Éditeur web

Interface graphique locale (FastAPI + Svelte) pour éditer les kits sans manipuler
de JSON.

## Lancement

Prérequis : Python 3 et Node.js (testé avec Python 3.14 et Node.js 25).

```bash
./dev.sh serve Backups/Backup001.bkf
```

`./dev.sh serve` est le **lancement rapide dans le navigateur**, sans Electron :
l'éditeur y fonctionne dans le même mode que l'application de bureau (jeton,
fichiers désignés par chemin absolu). La sauvegarde `.bkf` ou `.fac` à ouvrir
est obligatoire ; son chemin est relatif au dossier courant.

La commande prépare tout ce qui manque, puis lance le serveur :

1. crée l'environnement virtuel `.venv` s'il n'existe pas ;
2. installe les dépendances de `requirements-dev.txt` (éditeur, tests, outils),
   puis les réinstalle chaque fois que ce fichier ou `requirements.txt` change ;
3. installe les paquets de l'interface (`npm ci`) et la construit dans
   `editor/web/dist`, puis la reconstruit chaque fois qu'une source de
   `editor/web/` est modifiée ;
4. lance `python -m editor --open FICHIER` avec les options reçues.

`./dev.sh start` fait la même préparation pour l'application de bureau.

Variables utiles : `PYTHON=python3.12` choisit l'interpréteur qui crée le venv, et
`REBUILD=1` force la reconstruction de l'interface. Les `.bkf` et `.fac` du
dossier `Backups/` du projet sont ignorés par Git.

| Option | Rôle | Défaut |
|---|---|---|
| `--port N` | port HTTP (`0` : un port libre est choisi) | 8765 |
| `--host ADRESSE` | adresse d'écoute | 127.0.0.1 |
| `--no-browser` | ne pas ouvrir le navigateur | — |
| `--allow DOSSIER` | dossier autorisé en plus de la [zone par défaut](#dossiers-autorisés) (répétable) | — |
| `--watch-stdin` | s'arrêter quand l'entrée standard se ferme (utilisé par l'application de bureau) | — |
| `--version` | afficher la version (`alesis-kit-manager-server X.Y.Z`) et quitter | — |

Le navigateur s'ouvre sur l'adresse affichée, de la forme
`http://127.0.0.1:8765/#token=…`. Le serveur n'écoute que sur la machine locale et
`Ctrl+C` l'arrête.

### Dossiers autorisés

Le serveur n'ouvre et n'enregistre de sauvegarde que dans :

- le dossier personnel de l'utilisateur ;
- ses supports amovibles (clé USB, Strike branché en USB) : sous Linux
  `/media/<utilisateur>` et `/run/media/<utilisateur>`, sous macOS `/Volumes`,
  sous Windows tous les lecteurs sauf celui du système (`D:\`, `E:\`…, même
  branchés après le lancement) ;
- les dossiers ajoutés par `--allow DOSSIER` (`./dev.sh serve FICHIER --allow DOSSIER`).

Les chemins sont résolus avant la vérification : un lien symbolique placé dans le
dossier personnel ne permet pas d'atteindre un fichier extérieur. Un chemin hors
de ces dossiers est refusé (erreur 403, « hors des dossiers autorisés ») ; la
sauvegarde passée au lancement aussi, et le serveur s'arrête alors avec le code 2.
La copie `.bak` étant écrite à côté du fichier ouvert, elle reste dans la zone.
L'application de bureau utilise la zone par défaut.

### Jeton

Chaque requête `/api/*` doit porter l'en-tête `X-KitManager-Token` avec le jeton du
lancement, sinon elle reçoit une erreur 403 : un autre programme de la machine ne
peut donc pas piloter l'éditeur, qui lit et écrit des fichiers.

- **Lancement local** : un jeton est créé à chaque lancement et transmis au
  navigateur dans l'adresse (`#token=…`). L'interface le garde pour l'onglet, ce
  qui permet de recharger la page, et le retire de l'adresse affichée. Une page
  ouverte sans lui affiche « Accès refusé ».
- **Application Electron** : le jeton est donné par la variable d'environnement
  `KITMANAGER_TOKEN`. Une fois à l'écoute, le serveur écrit alors sur sa sortie
  standard une ligne `{"ready": true, "port": N}`, utile avec `--port 0`.

```bash
KITMANAGER_TOKEN=$(openssl rand -hex 16) .venv/bin/python -m editor --port 0 --open "$PWD/Backups/Backup001.bkf"
```

Sans `dev.sh`, l'installation manuelle est la suivante :

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd editor/web && npm ci && npm run build && cd ../..
.venv/bin/python -m editor --open Backups/Backup001.bkf
```

## Utilisation

1. **Ouvrir** : la sauvegarde passée au lancement est déjà ouverte. Pour en
   ouvrir une autre, saisir son chemin complet en haut, puis cliquer sur *Ouvrir*.
   Dans l'application de bureau, *Ouvrir…* et *Enregistrer sous…* utilisent les
   boîtes de dialogue du système, et seul le nom du fichier ouvert est affiché.
2. **Choisir un kit** dans la colonne de gauche (les kits vides sont masqués par défaut ; décocher *masquer les vides* pour les voir, par exemple pour y déposer un kit).
3. **Régler le kit** : nom, volume, tempo.
4. **Choisir un pad** dans la grille des 9 pads, disposée comme sur l'appareil (7-8-9 en haut,
   4-5-6 au milieu, 1-2-3 en bas). Elle montre le sample, la couleur de LED et,
   si le pad a un Mode (Control), un badge (« Click » pour Click On/Off). Sous la grille,
   les entrées de l'arrière identifiées (FootSwitch 1/2, FootSwitch 3/4, Trigger In 1,
   4/5, HH, dans cet ordre) ; les autres emplacements (10 à 24) s'affichent par le
   lien *afficher les emplacements non identifiés*.
5. **Régler le pad** :
   - sections du pad, comme sur l'appareil : *Feel* (Sensitivity, Curve, Threshold,
     Fixed Level), *Control* (Mode, Sound), *Output* (Audio Output, Kit FX Level,
     MIDI Note Output, Volume, Pan), *Light* (couleur, mode et beat Play / Stop),
     *Group* (Sync Group, Sync Mode) ; les paramètres non identifiés sont regroupés à part ;
   - *Wave A / Wave B* : sample, puis *Mode* (Playback Mode, Poly/Mono) et *Mix*
     (Volume, Pan, Fade In/Out, Velocity High/Low, Priority).

   Survoler le nom d'un réglage affiche sa description, d'après le manuel, et sa
   valeur par défaut pour le pad affiché. Celle-ci est relevée dans un kit vide
   écrit par l'appareil, et varie pour certains réglages : note MIDI propre à chaque
   emplacement, Sensitivity à 16 sur P1–P6 mais 24 sur les petits pads P7–P9. Pour
   un paramètre non identifié, l'infobulle donne aussi sa plage et, le cas échéant,
   une piste.
6. **Recopier un pad** : *Copier vers…* (en haut des réglages du pad) copie ses
   réglages vers un ou plusieurs autres emplacements. On choisit les sections (pad,
   éclairage, wave A, wave B) et si la note MIDI suit ; par défaut, chaque pad garde
   la sienne. Un champ absent de la cible n'est pas copié et est listé dans le
   message de confirmation.

   *Valeurs par défaut…* (à côté) remet des réglages aux valeurs d'un kit vide de
   l'appareil, propres à chaque emplacement (note MIDI, Sensitivity, éclairage…).
   On choisit les emplacements (le pad affiché est présélectionné) et les
   sections : Feel, Control, Output, Light et Group pour le pad, Mode et Mix pour
   chaque wave, *Sample (retirer)* pour retirer aussi le sample. Aucune section
   n'est cochée au départ ; *toutes les sections* les coche toutes, sauf le retrait
   des samples.
   Les paramètres non identifiés ne sont pas touchés.
7. **Modifier plusieurs pads** : *Modifier plusieurs pads…* (en haut des réglages
   du pad) donne une même valeur à un réglage sur une sélection de pads, par
   exemple Sensitivity = 20 sur P1, P3, P5 et P9. On choisit le réglage (pad,
   éclairage, vélocité ou mixage d'une wave), la valeur, bornée par sa plage, puis
   les pads. La valeur proposée est celle du pad courant. La section *Kits* permet
   d'appliquer la même valeur aux **mêmes pads de plusieurs kits** (kit courant
   coché par défaut, raccourci *kits non vides*). L'opération est tout ou rien :
   si un kit refuse la valeur, aucun n'est modifié.
8. **Déplacer ou dupliquer un kit** : *Déplacer / copier le kit…* (à côté du tempo)
   - *Déplacer / échanger* : le kit va au numéro choisi. Si ce kit est vide, c'est
     un déplacement (le numéro d'origine devient vide) ; sinon les deux kits sont
     échangés ;
   - *Copier (dupliquer)* : une copie du kit remplace le kit choisi, après
     confirmation si celui-ci n'est pas vide.

   Un kit ne contient pas son propre numéro : l'opération recopie ses octets tels
   quels, samples et réglages compris.

   Dans la liste des kits, la poignée ⠿ en bout de ligne (visible au survol d'un
   kit non vide) permet aussi de **réorganiser par glisser-déposer** : le kit
   prend la place du kit sur lequel on le dépose (un trait indique où), et les kits
   d'entre les deux se décalent d'un cran, comme dans une liste.

   *Supprimer le kit…* (à côté) remplace le kit, après confirmation, par le kit
   vide écrit par l'appareil : nom « Empty », volume 100, 120 BPM, réglages par
   défaut, aucun sample. Les samples utilisateur restent dans la sauvegarde. Le
   bouton est grisé sur un kit déjà vide.
9. **Choisir un sample** : le bouton du sample ouvre une fenêtre de recherche par nom
   ou par id, avec un filtre *Mes samples / Usine*. Le bouton ▶ écoute un sample
   perso (indisponible pour l'instant, voir la limitation ci-dessus). La zone du bas ajoute un WAV par glisser-déposer
   (voir [Ajouter un sample](ajouter-un-sample.md)).
10. **Enregistrer** écrit dans le fichier ouvert. Au premier enregistrement de
   chaque session sur un fichier d'origine, son état précédent est copié dans
   `<fichier>.N.bak` (`Backup001.bkf.1.bak`, puis `.2.bak` à la session suivante) :
   rien n'est perdu. **Enregistrer sous** écrit dans un autre fichier (le nom
   suivant est proposé, `Backup003.bkf` après `Backup002.bkf`), qui devient le
   fichier ouvert ; si ce fichier existe, une confirmation est demandée.
   **Recharger** relit le fichier ouvert et abandonne toutes les modifications non
   enregistrées, après confirmation s'il y en a ; le kit affiché reste le même.

Chaque modification est envoyée au serveur et validée aussitôt. Une valeur refusée
(hors plage, par exemple) affiche un message et le kit revient à son dernier état
valide. Les modifications restent en mémoire jusqu'à *Enregistrer*. Le
navigateur prévient si l'on quitte la page avec des modifications non enregistrées.

Charger ensuite le fichier produit sur l'appareil comme décrit dans
[Modifier un kit](modifier-un-kit.md#5-charger-sur-lappareil).

## API

Le serveur expose une API JSON, utilisable aussi depuis un script ; chaque requête
porte l'en-tête `X-KitManager-Token`, et les chemins de fichiers sont absolus :

| Méthode | Route | Rôle |
|---|---|---|
| POST | `/api/open` | ouvrir une sauvegarde (`{"path": "/chemin/absolu", "force": false}`) ; 403 hors des [dossiers autorisés](#dossiers-autorisés) ; 409 si des modifications ne sont pas enregistrées, sauf `force` |
| GET | `/api/state` | sauvegarde ouverte, liste des kits, modifications en attente |
| GET | `/api/meta` | description des paramètres (plages, libellés, couleurs) |
| GET / PUT | `/api/kits/{num}` | lire / modifier un kit (même JSON que l'export) |
| POST | `/api/kits/set` | même chose dans plusieurs kits, tout ou rien (`{"kits": ["031", "032"], "targets": [1, 9], "field": "params.sensitivity", "value": 20}`) ; renvoie l'état et les champs absents |
| POST | `/api/kits/{num}/set` | même valeur pour un champ de plusieurs emplacements (`{"targets": [1, 3, 5], "field": "params.sensitivity", "value": 20}` ; champs : `params.*`, `light.*`, `wave_a.*` / `wave_b.*` dont `sample` et les vélocités, `wave_a.params.*` / `wave_b.params.*`) |
| POST | `/api/kits/{num}/reset` | remettre des champs d'emplacements aux valeurs du kit vide de l'appareil (`{"targets": [1, 2], "fields": ["params.curve", "wave_a.sample"]}`) ; renvoie le kit et les champs non modifiés |
| POST | `/api/kits/{num}/move` | déplacer le kit au numéro `{"target": "033"}` ; les kits entre les deux numéros se décalent d'un cran ; renvoie l'état |
| POST | `/api/kits/{num}/clear` | supprimer le kit : le remplacer par le kit vide de l'appareil ; renvoie l'état |
| POST | `/api/kits/{num}/transfer` | copier le kit vers un autre numéro (`{"target": "040", "mode": "copy"}`) ou échanger les deux kits (`"mode": "swap"`) ; renvoie l'état |
| POST | `/api/kits/{num}/copy` | recopier un emplacement (`{"source": 9, "targets": [7, 8], "parts": ["params", "light", "wave_a", "wave_b"], "include_midi_note": false}`) |
| GET | `/api/samples` | catalogue des samples |
| GET | `/api/samples/{id}/wav` | WAV d'un sample utilisateur |
| POST | `/api/samples` | ajouter un WAV (formulaire multipart, champ `file`) |
| POST | `/api/save` | `{}` : enregistrer dans le fichier ouvert (copie `.N.bak` de l'original au premier enregistrement de la session) ; `{"path": …, "overwrite": false}` : enregistrer sous (403 hors des dossiers autorisés ; 409 si un autre fichier existe, sauf `overwrite`) |

La documentation interactive est disponible sur http://127.0.0.1:8765/docs ; ses
appels de test demandent d'ajouter l'en-tête du jeton.

## Développement de l'interface

Pour profiter du rechargement à chaud :

```bash
./dev.sh serve Backups/Backup001.bkf --no-browser   # serveur API ; noter le jeton affiché
cd editor/web && npm run dev                        # puis ouvrir http://localhost:5173/#token=…
```

Vite relaie `/api` vers le serveur ; le jeton affiché au lancement du serveur est
à ajouter à l'adresse de Vite. Voir aussi [Développement](developpement.md).

### Mode bureau

L'interface passe en mode bureau quand l'application Electron expose l'objet
`window.kitManagerDesktop` (preload) ; le même code sert aux deux modes.

| Membre | Rôle |
|---|---|
| `token` | jeton du serveur, envoyé dans l'en-tête `X-KitManager-Token` |
| `openFile()` | boîte native « Ouvrir » ; renvoie une promesse du chemin absolu choisi, ou `null` |
| `saveFile(defaultPath)` | boîte native « Enregistrer sous », ouverte sur le nom suivant ; renvoie le chemin ou `null`. La boîte confirme elle-même l'écrasement d'un fichier existant |
| `setDirty(dirty)` | appelé à chaque changement de l'état « modifications non enregistrées », pour que l'application confirme la fermeture de la fenêtre |
| `onCommand(handler)` | reçoit les commandes de l'application, `{ command, path? }` ; la valeur renvoyée par `handler` est la réponse : `open`, `save`, `save-as` (menu Fichier), `open-file` (fichier passé au lancement), `prepare-close` (→ `{ dirty }`, après envoi des modifications en attente), `save-before-close` (→ `{ saved }`) |

En mode bureau, l'interface ne bloque pas la fermeture de la page
(`beforeunload`) : c'est l'application qui la confirme.

Pour essayer ce mode dans le navigateur, sans Electron, un bouchon remplace les
boîtes natives par des `prompt()` : avec `npm run dev`, ajouter `&desktop=fake`
à l'adresse (`http://localhost:5173/#token=…&desktop=fake`). Il reste actif pour
l'onglet, journalise `setDirty` dans la console, marque le titre de la page
d'un « ● », et les commandes s'envoient depuis la console
(`await kitManagerFakeCommand("prepare-close")`). Il n'existe qu'en développement et n'est pas inclus dans le build.
