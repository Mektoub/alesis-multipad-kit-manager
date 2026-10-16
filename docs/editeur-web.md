# Éditeur web

Interface graphique locale (FastAPI + Svelte) pour éditer les kits sans manipuler
de JSON.

## Installation (une fois)

Prérequis : Python 3 et Node.js (testé avec Python 3.14 et Node.js 25).

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd editor/web && npm install && npm run build && cd ../..
```

`npm run build` produit l'interface dans `editor/web/dist`, que le serveur
publie. Il faut le relancer après une modification de l'interface.

## Lancement

```bash
.venv/bin/python -m editor --root Strike
```

| Option | Rôle | Défaut |
|---|---|---|
| `--root DOSSIER` | dossier où chercher les sauvegardes et où enregistrer | dossier courant |
| `--port N` | port HTTP | 8765 |
| `--host ADRESSE` | adresse d'écoute | 127.0.0.1 |
| `--no-browser` | ne pas ouvrir le navigateur | — |

Le navigateur s'ouvre sur http://127.0.0.1:8765/. Le serveur n'écoute que sur la
machine locale, et ne lit ni n'écrit en dehors du dossier `--root`.

## Utilisation

1. **Ouvrir** : choisir une sauvegarde `.bkf` ou `.fac` trouvée dans le dossier
   racine, puis cliquer sur *Ouvrir*.
2. **Choisir un kit** dans la colonne de gauche (*masquer les vides* allège la liste).
3. **Régler le kit** : nom, volume, tempo.
4. **Choisir un pad** dans la grille des 9 pads, qui montre le sample, la note MIDI
   et la couleur de LED. Les emplacements 10 à 24 sont accessibles sous la grille.
5. **Régler le pad** :
   - *Pad* : volume, pan, note MIDI, Control, Audio Output… ; les paramètres non
     identifiés sont regroupés à part ;
   - *Éclairage* : couleurs et modes Play / Stop ;
   - *Wave A / Wave B* : sample, plage de vélocité, mixage.
6. **Choisir un sample** : le bouton du sample ouvre une fenêtre de recherche par nom
   ou par id, avec un filtre *Mes samples / Usine*. Le bouton ▶ écoute un sample
   perso. La zone du bas ajoute un WAV par glisser-déposer
   (voir [Ajouter un sample](ajouter-un-sample.md)).
7. **Enregistrer sous** : le nom suivant est proposé (`Backup003.bkf` après
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
