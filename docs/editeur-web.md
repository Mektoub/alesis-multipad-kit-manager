# Éditeur web

Interface graphique locale (FastAPI + Svelte) pour éditer les kits sans manipuler
de JSON.

## Lancement

Prérequis : Python 3 et Node.js (testé avec Python 3.14 et Node.js 25).

```bash
./editeur.sh
```

Le script prépare tout ce qui manque, puis lance le serveur :

1. crée l'environnement virtuel `.venv` s'il n'existe pas ;
2. installe les dépendances de `requirements.txt`, puis les réinstalle chaque fois
   que ce fichier change ;
3. installe les paquets de l'interface (`npm ci`) et la construit dans
   `editor/web/dist`, puis la reconstruit chaque fois qu'une source de
   `editor/web/` est modifiée ;
4. lance `python -m editor` avec les arguments reçus.

Sans `--root`, le dossier `Strike/` du projet est utilisé s'il existe. Variables
utiles : `PYTHON=python3.12` choisit l'interpréteur qui crée le venv, et
`REBUILD=1` force la reconstruction de l'interface.

| Option | Rôle | Défaut |
|---|---|---|
| `--root DOSSIER` | dossier où chercher les sauvegardes et où enregistrer | `Strike/` du projet, sinon le dossier courant |
| `--port N` | port HTTP | 8765 |
| `--host ADRESSE` | adresse d'écoute | 127.0.0.1 |
| `--no-browser` | ne pas ouvrir le navigateur | — |

Le navigateur s'ouvre sur http://127.0.0.1:8765/. Le serveur n'écoute que sur la
machine locale, et ne lit ni n'écrit en dehors du dossier `--root`. `Ctrl+C`
l'arrête.

Sans le script, l'installation manuelle est la suivante :

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd editor/web && npm ci && npm run build && cd ../..
.venv/bin/python -m editor --root Strike   # par défaut, la racine est le dossier courant
```

## Utilisation

1. **Ouvrir** : choisir une sauvegarde `.bkf` ou `.fac` trouvée dans le dossier
   racine, puis cliquer sur *Ouvrir*.
2. **Choisir un kit** dans la colonne de gauche (*masquer les vides* allège la liste).
3. **Régler le kit** : nom, volume, tempo.
4. **Choisir un pad** dans la grille des 9 pads, disposée comme sur l'appareil (7-8-9 en haut,
   4-5-6 au milieu, 1-2-3 en bas). Elle montre le sample, la couleur de LED et,
   si le pad a un Control, un badge (« Click » pour Click On/Off). Les emplacements 10 à 24 sont accessibles sous la grille.
5. **Régler le pad** :
   - *Pad* : volume, pan, note MIDI, Control, Audio Output… ; les paramètres non
     identifiés sont regroupés à part ;
   - *Éclairage* : couleurs et modes Play / Stop ;
   - *Wave A / Wave B* : sample, plage de vélocité, mixage.

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
7. **Modifier plusieurs pads** : *Modifier plusieurs pads…* (en haut des réglages
   du pad) donne une même valeur à un réglage sur une sélection de pads, par
   exemple Sensitivity = 20 sur P1, P3, P5 et P9. On choisit le réglage (pad,
   éclairage, vélocité ou mixage d'une wave), la valeur, bornée par sa plage, puis
   les pads. La valeur proposée est celle du pad courant.
8. **Déplacer ou dupliquer un kit** : *Déplacer / copier le kit…* (à côté du tempo)
   - *Déplacer / échanger* : le kit va au numéro choisi. Si ce kit est vide, c'est
     un déplacement (le numéro d'origine devient vide) ; sinon les deux kits sont
     échangés ;
   - *Copier (dupliquer)* : une copie du kit remplace le kit choisi, après
     confirmation si celui-ci n'est pas vide.

   Un kit ne contient pas son propre numéro : l'opération recopie ses octets tels
   quels, samples et réglages compris.
9. **Choisir un sample** : le bouton du sample ouvre une fenêtre de recherche par nom
   ou par id, avec un filtre *Mes samples / Usine*. Le bouton ▶ écoute un sample
   perso. La zone du bas ajoute un WAV par glisser-déposer
   (voir [Ajouter un sample](ajouter-un-sample.md)).
10. **Enregistrer sous** : le nom suivant est proposé (`Backup003.bkf` après
   `Backup002.bkf`). Si le fichier existe, une confirmation est demandée.
   L'enregistrement sur la sauvegarde d'origine est refusé.

Chaque modification est envoyée au serveur et validée aussitôt. Une valeur refusée
(hors plage, par exemple) affiche un message et le kit revient à son dernier état
valide. Les modifications restent en mémoire jusqu'à *Enregistrer sous*. Le
navigateur prévient si l'on quitte la page avec des modifications non enregistrées.

Charger ensuite le fichier produit sur l'appareil comme décrit dans
[Modifier un kit](modifier-un-kit.md#5-charger-sur-lappareil).

## API

Le serveur expose une API JSON, utilisable aussi depuis un script :

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/backups` | sauvegardes trouvées dans le dossier racine |
| POST | `/api/open` | ouvrir une sauvegarde (`{"path": …}`) |
| GET | `/api/state` | sauvegarde ouverte, liste des kits, modifications en attente |
| GET | `/api/meta` | description des paramètres (plages, libellés, couleurs) |
| GET / PUT | `/api/kits/{num}` | lire / modifier un kit (même JSON que l'export) |
| POST | `/api/kits/{num}/set` | même valeur pour un champ de plusieurs emplacements (`{"targets": [1, 3, 5], "field": "params.sensitivity", "value": 20}` ; champs : `params.*`, `light.*`, `wave_a.*` / `wave_b.*` dont `sample` et les vélocités, `wave_a.params.*` / `wave_b.params.*`) |
| POST | `/api/kits/{num}/transfer` | copier le kit vers un autre numéro (`{"target": "040", "mode": "copy"}`) ou échanger les deux kits (`"mode": "swap"`) ; renvoie l'état |
| POST | `/api/kits/{num}/copy` | recopier un emplacement (`{"source": 9, "targets": [7, 8], "parts": ["params", "light", "wave_a", "wave_b"], "include_midi_note": false}`) |
| GET | `/api/samples` | catalogue des samples |
| GET | `/api/samples/{id}/wav` | WAV d'un sample utilisateur |
| POST | `/api/samples` | ajouter un WAV (formulaire multipart, champ `file`) |
| POST | `/api/save` | enregistrer (`{"path": …, "overwrite": false}`) |

La documentation interactive est disponible sur http://127.0.0.1:8765/docs.

## Développement de l'interface

Pour profiter du rechargement à chaud :

```bash
.venv/bin/python -m editor --no-browser --root Strike   # serveur API
cd editor/web && npm run dev                            # http://localhost:5173
```

Vite relaie `/api` vers le serveur. Voir aussi [Développement](developpement.md).
