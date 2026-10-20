# Développement

## Organisation du code

| Chemin | Rôle |
|---|---|
| `strike_kits.py` | lecture et écriture des formats, commandes `export` / `import` (bibliothèque standard uniquement) |
| `editor/server.py` | API FastAPI de l'éditeur |
| `editor/meta.py` | description des paramètres pour l'interface (libellés, couleurs) |
| `editor/__main__.py` | lancement (`python -m editor`) |
| `editeur.sh` | lancement local rapide sur une sauvegarde, avec préparation automatique du venv et de l'interface |
| `dev.sh` | analyse, tests et build en local, comme la CI |
| `editor/web/` | interface Svelte (Vite) |
| `editor/web/src/**/*.test.js` | tests de l'interface (Vitest, jsdom) |
| `tests/test_strike_kits.py` | tests du format et de la ligne de commande |
| `tests/test_editor.py` | tests de l'API |
| `tests/outils.py` | outils communs aux tests (sauvegarde de référence, WAV et `.fac` synthétiques) |
| `tests/ressources/Backup001.bkf` | sauvegarde de référence des tests |
| `tests/construire_reference.py` | script qui a construit cette sauvegarde |
| `docs/format-*.md` | ce que l'on sait des formats binaires |

Dans `strike_kits.py` :

- `decode_kit` / `encode_kit` : kit binaire ↔ JSON ;
- `Bkf` : conteneur `.bkf` décomposé en enregistrements, reconstructible à
  l'identique, avec `add_sample` (et `remove_last_sample`, son inverse, réservé à
  la construction de la sauvegarde de référence) ;
- `Backup` : sauvegarde `.bkf` ou `.fac` ouverte en mémoire, utilisée par l'éditeur
  et par les commandes.

## En une commande : `dev.sh`

`./dev.sh` lance les mêmes vérifications que la CI. Au besoin, il crée `.venv`,
installe `requirements-dev.txt` et les paquets de l'interface (`npm ci`).

| Commande | Rôle |
|---|---|
| `./dev.sh lint` | `ruff check`, `ruff format --check`, ESLint ; n'écrit rien |
| `./dev.sh lint --fix` | corrige ce qui peut l'être et reformate (ruff, ESLint) |
| `./dev.sh test` | tous les tests, Python et interface |
| `./dev.sh test tests.test_editor.JetonEtChemins` | seulement les tests Python indiqués |
| `./dev.sh build` | build de l'interface dans `editor/web/dist` |
| `./dev.sh all [--fix]` | tout ; continue après un échec, affiche un bilan, code de sortie non nul en cas d'échec |

Les sections suivantes détaillent les commandes appelées.

## Tests

```bash
python3 -m unittest -v tests.test_strike_kits                 # sans dépendance
.venv/bin/python -m unittest -v tests.test_editor             # nécessite requirements.txt
.venv/bin/python -m unittest discover -s tests -t .           # tout
cd editor/web && npm test                                     # interface (Vitest)
```

## Analyse du code

```bash
.venv/bin/pip install -r requirements-dev.txt   # ruff, en plus des dépendances de l'éditeur
.venv/bin/ruff check .                          # erreurs, style PEP 8, imports, pièges courants
.venv/bin/ruff format .                         # formatage (lignes de 120 caractères)
cd editor/web && npm run lint                   # ESLint : JavaScript et Svelte
```

Réglages : `pyproject.toml` (`[tool.ruff]`) et `editor/web/eslint.config.js`. La
modernisation des chaînes `"%s" % x` en f-strings (règles `UP` de ruff) n'est pas
activée.

## Intégration continue

`.github/workflows/ci.yml` (GitHub Actions) se déclenche à chaque push sur `main`
et sur chaque pull request. Deux jobs, sous Ubuntu :

| Job | Étapes |
|---|---|
| Python (3.14) | `ruff check`, `ruff format --check`, tous les tests |
| Interface (Node 24) | `npm ci`, `npm run lint` (ESLint), `npm test` (Vitest), `npm run build` |

Avant de pousser, les mêmes commandes peuvent être lancées en local (voir
ci-dessus).

Tous les tests reposent sur **une seule sauvegarde**, `tests/ressources/Backup001.bkf`
(5 Mo), indépendante des sauvegardes de travail du dossier `Backups/`. Elle a été
construite par `tests/construire_reference.py` à partir d'une vraie sauvegarde de
l'appareil :

| Contenu | Sert à vérifier |
|---|---|
| kit 031 « WhereIs » (`KITC`) : Control Click sur P7–P9 | kits écrits par l'appareil, pads masqués |
| kit 032 « CrazyInLove » (`KITC`, créé sur l'appareil) : P9 Click et Aux+Phone | `control`, `audio_output`, champs recouverts |
| kit 040 « Ham & Beans » (kit d'usine copié du `.fac`) | couches de vélocité |
| kits vides (`KITH`) | modifications, copie et échange de kits |
| samples 8071 « SnareUF » et 8072 « Sample Stuck » | export des WAV, ajout et retrait de sample |

Les deux gros samples d'origine (61 Mo) y ont été remplacés par ces deux WAV
courts, sous les mêmes ids, pour que les kits continuent de les référencer.

Le `.fac` des tests est construit en mémoire à partir des kits de la référence
(`tests/outils.py`, `make_fac`). Cette construction reproduit octet pour octet le
vrai `STRIKE_BACKUP_KIT.fac` de l'appareil quand on lui donne ses 100 kits.

L'ajout de sample a été vérifié une fois octet pour octet contre deux sauvegardes
faites par l'appareil avant et après un import. Les tests en gardent les règles
(`test_regles_de_l_ajout`) et vérifient que retrait puis ajout redonnent la
référence à l'identique.

Avant de corriger un bug, écrire un test qui le met en évidence et vérifier qu'il
échoue, puis corriger.

## Interface

```bash
cd editor/web
npm install
npm run dev     # développement, avec le serveur lancé à côté
npm run build   # production, dans editor/web/dist
```

Les versions des paquets sont figées dans `package.json`, `requirements.txt` et
`requirements-dev.txt`.
