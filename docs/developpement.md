# Développement

## Organisation du code

| Chemin | Rôle |
|---|---|
| `strike_kits/` | lecture et écriture des formats (`__init__.py`), commandes `export` / `import` (`python3 -m strike_kits`, `__main__.py`) ; bibliothèque standard uniquement |
| `editor/server.py` | API FastAPI de l'éditeur |
| `editor/history.py` | historique des modifications (annuler / rétablir) |
| `editor/meta.py` | description des paramètres pour l'interface (libellés, couleurs) |
| `editor/__main__.py` | lancement (`python -m editor`) |
| `app-names.json` | noms de l'application : long, court, identifiant des chemins, dossier de configuration (voir [Application de bureau](application-bureau.md#noms-de-lapplication)) |
| `dev.sh` | lancement de l'éditeur (navigateur ou application de bureau), avec préparation automatique du venv et de l'interface ; analyse, tests et build en local, comme la CI |
| `desktop/` | application de bureau Electron (voir [Application de bureau](application-bureau.md)) |
| `editor/web/` | interface Svelte (Vite) |
| `editor/web/src/**/*.test.js` | tests de l'interface (Vitest, jsdom) |
| `tests/test_strike_kits.py` | tests du format et de la ligne de commande |
| `tests/test_editor.py` | tests de l'API |
| `tests/test_history.py` | tests de l'historique (annuler / rétablir) |
| `tests/outils.py` | outils communs aux tests (sauvegarde de référence, WAV et `.fac` synthétiques) |
| `tests/ressources/Backup001.bkf` | sauvegarde de référence des tests |
| `tests/construire_reference.py` | script qui a construit cette sauvegarde |
| `docs/format-*.md` | ce que l'on sait des formats binaires |

Dans `strike_kits/__init__.py` :

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
| `./dev.sh test tests.test_editor.Lancement` | seulement les tests Python indiqués |
| `./dev.sh e2e` | test de bout en bout de l'application de bureau (voir [Application de bureau](application-bureau.md#test-de-bout-en-bout)) |
| `./dev.sh build` | build de l'interface dans `editor/web/dist` |
| `./dev.sh serve FICHIER [--port N] [--host ADRESSE] [--no-browser]` | éditeur dans le navigateur sur cette sauvegarde |
| `./dev.sh package` | paquet .deb de l'application dans `desktop/dist/` (voir [Application de bureau](application-bureau.md#paquet-deb)) |
| `./dev.sh test-deb` | installe et teste le .deb dans un conteneur Docker Ubuntu 24.04 (voir [Application de bureau](application-bureau.md#tester-linstallation-dans-un-conteneur)) |
| `./dev.sh start [--frozen] [FICHIER]` | lance l'application de bureau ; `--frozen` : avec le serveur figé, reconstruit si une source a changé |
| `./dev.sh freeze` | serveur figé (PyInstaller) dans `desktop/build/alesis-kit-manager-server/`, puis son test de fumée (voir [Application de bureau](application-bureau.md#serveur-figé)) |
| `./dev.sh all [--fix]` | tout ; continue après un échec, affiche un bilan, code de sortie non nul en cas d'échec |
| `./dev.sh release X.Y.Z` | nouvelle version : met à jour les versions, commite et crée le tag `vX.Y.Z` (voir [Nouvelle version](#nouvelle-version)) |

Les sections suivantes détaillent les commandes appelées.

## Tests

```bash
python3 -m unittest -v tests.test_strike_kits                 # sans dépendance
.venv/bin/python -m unittest -v tests.test_editor             # nécessite requirements.txt
.venv/bin/python -m unittest discover -s tests -t .           # tout
cd editor/web && npm test                                     # interface (Vitest)
cd desktop && npm test                                        # application de bureau (node:test)
cd desktop && npm run e2e                                     # bout en bout (Playwright ; venv et interface prêts)
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
et sur chaque pull request. Cinq jobs, sous Ubuntu :

| Job | Étapes |
|---|---|
| Python (3.14) | `ruff check`, `ruff format --check`, tous les tests |
| Interface (Node 24) | `npm ci`, `npm run lint` (ESLint), `npm test` (Vitest), `npm run build` |
| Application de bureau (Node 24) | `npm ci`, `npm run lint` (ESLint), `npm test` (node:test ; sans `.venv`, le test du serveur réel est ignoré) |
| Application de bureau, bout en bout (Ubuntu 24.04) | profil AppArmor de l'Electron de développement, puis `xvfb-run -a ./dev.sh e2e` |
| Serveur figé (Python 3.14, Node 24) | workflow `build.yml` appelé sous Ubuntu 24.04, sans paquet : build de l'interface, PyInstaller, test de fumée |

Avant de pousser, les mêmes commandes peuvent être lancées en local (voir
ci-dessus).

Le workflow `.github/workflows/build.yml` (« Package ») construit les
paquets de l'application de bureau sous Linux, Windows et macOS, à la main ou
appelé par `release.yml` sur un tag `v*` (voir [Nouvelle version](#nouvelle-version)
et [l'application de bureau](application-bureau.md#paquets-windows-et-macos)).
`ci.yml` le réutilise pour le job « Serveur figé » (`workflow_call`, entrées `os`
et `freeze-only`) : les étapes du freeze n'existent qu'à un endroit. `./dev.sh
freeze` fait la même chose en local, mais la CI ne l'exécute plus.

La préparation commune à tous les jobs (Python 3.14 et `requirements-dev.txt`,
Node 24, caches pip et npm) est l'action composite `.github/actions/setup` :
les versions de Python et de Node ne sont écrites que là.

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

## Nouvelle version

La version de l'application est écrite à trois endroits, tenus à jour par
`./dev.sh release` :

| Fichier | Sert à |
|---|---|
| `app-names.json` (`version`) | serveur et interface : `--version`, À propos, en-tête, documentation de l'API (`/docs`) ; embarquée dans le serveur figé |
| `desktop/package.json` (+ `package-lock.json`) | paquets : nom des fichiers et version déclarée au système |
| `editor/web/package.json` (+ `package-lock.json`) | alignée sur les autres, sans autre usage |

`scripts/verifier-version.py` vérifie qu'ils concordent (`./dev.sh lint`, `all`
et la CI) ; avec une version, qu'ils ont tous celle-ci et que le CHANGELOG a sa
section (`scripts/verifier-version.py X.Y.Z`).

Étapes :

1. écrire la section `## X.Y.Z — titre` en tête de `CHANGELOG.md`, la commiter et
   la fusionner dans `main` ;
2. sur `main` à jour, l'arbre propre : `./dev.sh release X.Y.Z`. Le script refuse
   s'il manque la section du CHANGELOG ou si le tag existe déjà ; il met la
   version dans les fichiers ci-dessus, commite « Version X.Y.Z » (rien à commiter
   si elle y est déjà) et crée le tag annoté `vX.Y.Z`, dont le message reprend la
   section du CHANGELOG ;
3. vérifier, puis pousser : `git push origin main vX.Y.Z`. Le tag lance le
   workflow « Release » (`.github/workflows/release.yml`) : il revérifie les
   versions du commit, construit les paquets des trois systèmes (`build.yml`) et
   crée une **release en brouillon** avec les paquets et les notes du CHANGELOG ;
4. relire la release sur GitHub (onglet *Releases*) et la publier.

Le script ne lance pas les vérifications : passer `./dev.sh all` avant.

### Hooks Git

`.githooks/` contient deux hooks, activés par le premier `./dev.sh` lancé
(`git config core.hooksPath .githooks`) :

- `reference-transaction` : `git tag vX.Y.Z` échoue si le commit visé n'a pas la
  version X.Y.Z dans tous les fichiers, ou pas de section `## X.Y.Z` dans le
  CHANGELOG (Git n'a pas de hook « pre-tag » : celui-ci voit chaque modification
  de référence) ;
- `pre-push` : même vérification avant de pousser un tag créé sans le hook.

Seuls les tags `v*` sont vérifiés ; ceux d'avant la version dans
`app-names.json` (0.3.1 et avant) sont ignorés. Un hook se contourne
(`git -c core.hooksPath=/dev/null tag …`, `git push --no-verify`) : le workflow
« Release » refait la vérification avant de construire quoi que ce soit.

## Interface

```bash
cd editor/web
npm install
npm run dev     # développement, avec le serveur lancé à côté
npm run build   # production, dans editor/web/dist
```

Les versions des paquets sont figées dans `package.json`, `requirements.txt` et
`requirements-dev.txt`.
