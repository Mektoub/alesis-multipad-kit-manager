# Development

**English** · [Français](../fr/development.md)

## Code layout

| Path | Role |
|---|---|
| `strike_kits/` | reading and writing the formats (`__init__.py`), `export` / `import` commands (`python3 -m strike_kits`, `__main__.py`); standard library only |
| `editor/server.py` | the editor's FastAPI API |
| `editor/history.py` | edit history (undo / redo) |
| `editor/preferences.py` | user preferences (`preferences.json`) |
| `editor/i18n.py` | server texts in English and French (errors, history labels) |
| `editor/meta.py` | parameter descriptions for the UI (labels, colors) |
| `editor/__main__.py` | entry point (`python -m editor`) |
| `app-names.json` | application names: long, short, path identifier, configuration folder (see [Desktop app](desktop-app.md#application-names)) |
| `dev.sh` | launches the editor (browser or desktop app), preparing the venv and the UI automatically; linting, tests and builds locally, like the CI |
| `desktop/` | Electron desktop app (see [Desktop app](desktop-app.md)) |
| `editor/web/` | Svelte UI (Vite); texts in English and French in `src/lib/messages.js` |
| `editor/web/src/**/*.test.js` | UI tests (Vitest, jsdom) |
| `tests/test_strike_kits.py` | format and command-line tests |
| `tests/test_editor.py` | API tests |
| `tests/test_history.py` | history tests (undo / redo) |
| `tests/test_preferences.py` | preferences tests (file, API, effects on the editor) |
| `tests/test_i18n.py` | translation tests (catalogs, request language) |
| `tests/outils.py` | shared test helpers (reference backup, synthetic WAV and `.fac` files) |
| `tests/ressources/Backup001.bkf` | the tests' reference backup |
| `tests/construire_reference.py` | script that built this backup |
| `docs/en/*-format.md` (French: `docs/fr/`) | what is known about the binary formats |
| `docs/images/en/`, `docs/images/fr/` | screenshots, interface in the language of the documentation |
| `desktop/e2e/screenshots.js` | documentation screenshots (`./dev.sh screenshots`) |

In `strike_kits/__init__.py`:

- `decode_kit` / `encode_kit`: binary kit ↔ JSON;
- `Bkf`: `.bkf` container split into records, rebuildable byte for byte, with
  `add_sample` (and `remove_last_sample`, its inverse, reserved for building the
  reference backup);
- `Backup`: a `.bkf` or `.fac` backup opened in memory, used by the editor and by
  the commands.

## One command: `dev.sh`

`./dev.sh` runs the same checks as the CI. When needed, it creates `.venv`,
installs `requirements-dev.txt` and the UI packages (`npm ci`).

| Command | Role |
|---|---|
| `./dev.sh lint` | `ruff check`, `ruff format --check`, ESLint; writes nothing |
| `./dev.sh lint --fix` | fixes what can be fixed and reformats (ruff, ESLint) |
| `./dev.sh test` | all tests, Python and UI |
| `./dev.sh test tests.test_editor.Lancement` | only the given Python tests |
| `./dev.sh e2e` | end-to-end test of the desktop app (see [Desktop app](desktop-app.md#end-to-end-test)) |
| `./dev.sh screenshots` | screenshots for the documentation in `docs/images/en/` and `docs/images/fr/`, taken in the desktop app on the test reference backup (Playwright, light theme, 1400×900 window); rerun after an interface change; the window shows during the captures: do not type meanwhile |
| `./dev.sh build` | builds the UI into `editor/web/dist` |
| `./dev.sh serve FILE [--port N] [--host ADDRESS] [--no-browser]` | editor in the browser on this backup |
| `./dev.sh package` | .deb package of the app in `desktop/dist/` (see [Desktop app](desktop-app.md#deb-package)) |
| `./dev.sh test-deb` | installs and tests the .deb in an Ubuntu 24.04 Docker container (see [Desktop app](desktop-app.md#testing-the-installation-in-a-container)) |
| `./dev.sh start [--frozen] [FILE]` | launches the desktop app; `--frozen`: with the frozen server, rebuilt if a source has changed |
| `./dev.sh freeze` | frozen server (PyInstaller) in `desktop/build/alesis-kit-manager-server/`, then its smoke test (see [Desktop app](desktop-app.md#frozen-server)) |
| `./dev.sh all [--fix]` | everything; keeps going after a failure, prints a summary, non-zero exit code on failure |
| `./dev.sh release X.Y.Z` | new version: updates the versions, commits and creates the `vX.Y.Z` tag (see [New version](#new-version)) |

The following sections detail the commands it calls.

## Tests

```bash
python3 -m unittest -v tests.test_strike_kits                 # no dependencies
.venv/bin/python -m unittest -v tests.test_editor             # requires requirements.txt
.venv/bin/python -m unittest discover -s tests -t .           # everything
cd editor/web && npm test                                     # UI (Vitest)
cd desktop && npm test                                        # desktop app (node:test)
cd desktop && npm run e2e                                     # end-to-end (Playwright; venv and UI ready)
```

## Linting

```bash
.venv/bin/pip install -r requirements-dev.txt   # ruff, on top of the editor's dependencies
.venv/bin/ruff check .                          # errors, PEP 8 style, imports, common pitfalls
.venv/bin/ruff format .                         # formatting (120-character lines)
cd editor/web && npm run lint                   # ESLint: JavaScript and Svelte
```

Settings: `pyproject.toml` (`[tool.ruff]`) and `editor/web/eslint.config.js`.
Modernizing `"%s" % x` strings into f-strings (ruff's `UP` rules) is not enabled.

## Continuous integration

`.github/workflows/ci.yml` (GitHub Actions) runs on every push to `main` and on
every pull request. Five jobs, on Ubuntu:

| Job | Steps |
|---|---|
| Python (3.14) | `ruff check`, `ruff format --check`, all tests |
| UI (Node 24) | `npm ci`, `npm run lint` (ESLint), `npm test` (Vitest), `npm run build` |
| Desktop app (Node 24) | `npm ci`, `npm run lint` (ESLint), `npm test` (node:test; without `.venv`, the real-server test is skipped) |
| Desktop app, end-to-end (Ubuntu 24.04) | AppArmor profile for the development Electron, then `xvfb-run -a ./dev.sh e2e` |
| Frozen server (Python 3.14, Node 24) | `build.yml` workflow called on Ubuntu 24.04, without packaging: UI build, PyInstaller, smoke test |

Before pushing, the same commands can be run locally (see above).

The `.github/workflows/build.yml` workflow (“Package”) builds the desktop app
packages on Linux, Windows and macOS, either manually or when called by
`release.yml` on a `v*` tag (see [New version](#new-version) and
[the desktop app](desktop-app.md#windows-and-macos-packages)).
`ci.yml` reuses it for the “Serveur figé” (frozen server) job (`workflow_call`, inputs `os` and
`freeze-only`): the freeze steps exist in one place only. `./dev.sh freeze` does
the same thing locally, but the CI no longer runs it.

The setup shared by all jobs (Python 3.14 and `requirements-dev.txt`, Node 24,
pip and npm caches) is the composite action `.github/actions/setup`: the Python
and Node versions are written there only.

All tests rely on **a single backup**, `tests/ressources/Backup001.bkf` (5 MB),
independent of the working backups in the `Backups/` folder. It was built by
`tests/construire_reference.py` from a real backup of the device:

| Content | Used to check |
|---|---|
| kit 031 “WhereIs” (`KITC`): Control Click on P7–P9 | kits written by the device, hidden pads |
| kit 032 “CrazyInLove” (`KITC`, created on the device): P9 Click and Aux+Phone | `control`, `audio_output`, overlapped fields |
| kit 040 “Ham & Beans” (factory kit copied from the `.fac`) | velocity layers |
| empty kits (`KITH`) | edits, copying and swapping kits |
| samples 8071 “SnareUF” and 8072 “Sample Stuck” | WAV export, adding and removing a sample |

The two large original samples (61 MB) were replaced with these two short WAV
files, under the same ids, so that the kits still reference them.

The tests' `.fac` is built in memory from the reference kits (`tests/outils.py`,
`make_fac`). Given its 100 kits, this construction reproduces the device's real
`STRIKE_BACKUP_KIT.fac` byte for byte.

Adding a sample was verified once, byte for byte, against two backups made by
the device before and after an import. The tests keep its rules
(`test_regles_de_l_ajout`) and check that removing then adding gives back the
reference exactly.

Before fixing a bug, write a test that exposes it and check that it fails, then
fix it.

## New version

The application version is written in three places, kept up to date by
`./dev.sh release`:

| File | Used for |
|---|---|
| `app-names.json` (`version`) | server and UI: `--version`, About, header, API documentation (`/docs`); embedded in the frozen server |
| `desktop/package.json` (+ `package-lock.json`) | packages: file names and version declared to the system |
| `editor/web/package.json` (+ `package-lock.json`) | kept in line with the others, no other use |

`scripts/verifier-version.py` checks that they match (`./dev.sh lint`, `all` and
the CI); given a version, it checks that they all have it and that the CHANGELOG
has its section (`scripts/verifier-version.py X.Y.Z`).

Steps:

1. write the `## X.Y.Z — title` section at the top of `CHANGELOG.md`, commit it
   and merge it into `main`;
2. on an up-to-date `main` with a clean tree: `./dev.sh release X.Y.Z`. The
   script refuses if the CHANGELOG section is missing or if the tag already
   exists; it writes the version into the files above, commits “Version X.Y.Z”
   (nothing to commit if it is already there) and creates the annotated tag
   `vX.Y.Z`, whose message is the CHANGELOG section;
3. check, then push: `git push origin main vX.Y.Z`. The tag triggers the
   “Release” workflow (`.github/workflows/release.yml`): it rechecks the commit's
   versions, builds the packages for the three systems (`build.yml`) and creates
   a **draft release** with the packages and the CHANGELOG notes;
4. review the release on GitHub (*Releases* tab) and publish it.

The script does not run the checks: run `./dev.sh all` first.

### Git hooks

`.githooks/` contains two hooks, enabled by the first `./dev.sh` run
(`git config core.hooksPath .githooks`):

- `reference-transaction`: `git tag vX.Y.Z` fails if the target commit does not
  have version X.Y.Z in every file, or has no `## X.Y.Z` section in the CHANGELOG
  (Git has no “pre-tag” hook: this one sees every reference change);
- `pre-push`: the same check before pushing a tag created without the hook.

Only `v*` tags are checked; those from before the version was in
`app-names.json` (0.3.1 and earlier) are ignored. A hook can be bypassed
(`git -c core.hooksPath=/dev/null tag …`, `git push --no-verify`): the “Release”
workflow repeats the check before building anything.

## UI

```bash
cd editor/web
npm install
npm run dev     # development, with the server running alongside
npm run build   # production, into editor/web/dist
```

Package versions are pinned in `package.json`, `requirements.txt` and
`requirements-dev.txt`.
