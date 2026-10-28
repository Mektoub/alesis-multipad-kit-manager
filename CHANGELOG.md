# Changelog

## Unreleased — License, synthetic test backup

- License: GNU GPL 3.0 or later (`LICENSE`, `license` field of the `package.json` files, *License* section of the READMEs with a notice that the project is not affiliated with Alesis).
- Tests: the reference backup (`tests/ressources/Backup001.bkf`, 5.2 → 3.4 MB) no longer contains any third-party sound: its 34 user samples are synthetic (renamed “Sine 01”, “Noise 02”…, except “SnareUF” and “Sample Stuck”), and the factory kit “Ham & Beans” is replaced with “Layer Demo”, built from an empty kit (velocity layers). `tests/construire_reference.py` rebuilds it from a device backup.

## 0.5.0 — English documentation, preferences, English interface

- Documentation in English (`README.md`, `docs/en/`) and in French (`README.fr.md`, `docs/fr/`), with the same English file names in both languages and a language switch at the top of each page. The changelog is now kept in English only.
- Web editor: on the small pads P7–P9, the sample names no longer overlap the pad label (the pad grows to fit its content).
- Documentation: screenshots of the web editor (overview, action windows, sample picker, history list and warning) in `docs/images/`, shared by both languages; `./dev.sh screenshots` regenerates them in the desktop app (`desktop/e2e/screenshots.js`, Playwright).
- Documentation: removed an outdated note saying that playing user samples (▶) was unavailable.
- User preferences, kept from one launch to the next in `preferences.json` (app configuration folder, or `KITMANAGER_CONFIG`) and shared by the browser and the desktop app: theme (system, light, dark), hide empty kits, reopen the last backup at launch, recent files (▾ chevron next to *Ouvrir* (Open), *Fichier › Ouvrir récent* (File › Open recent) menu), history size (10 to 1000, 100 by default), folder of the last opened file. *Préférences* (Preferences) window: ⚙ button in the header, `Ctrl+,` in the desktop app. API: `GET` / `PATCH /api/preferences` (`editor/preferences.py`).
- Desktop app: the window's size, position and maximized state are remembered (`window-state.json`); it opens maximized on first launch only.
- Interface in English or French: *Language* preference (system by default: French if the system is in French, English otherwise). Buttons, menus, dialogs, messages, tooltips and history labels are translated; pad parameter names and values stay in English, as on the device. The server answers in the language of the `X-KitManager-Language` header (English by default, `editor/i18n.py`); `strike_kits` errors stay in French.
- Documentation: screenshots per language (`docs/images/en/`, `docs/images/fr/`); the English documentation uses the English interface labels.

## 0.4.0 — UI improvements

- Web editor: history list (▾ chevron next to ↶ ↷), from the most recent action to the oldest, with the old and new value (“90 → 50”, “Normal → Exp2”), the current position and the *Enregistré* (Saved) marker; a click goes back to the chosen action. API: `GET /api/history`, `POST /api/history/goto`; `detail` in the `/api/undo` and `/api/redo` responses.

- Web editor: *Annuler / Rétablir* (Undo / Redo) (↶ ↷ buttons in the header, `Ctrl+Z`, `Ctrl+Y` or `Ctrl+Shift+Z`, the desktop app's *Édition* (Edit) menu) on parameter edits, one step per action, 100 at most. Moving, transferring or deleting a kit clears the history, after a warning (*Annuler* (Cancel), *Enregistrer et continuer* (Save and continue), *Continuer* (Continue)); adding a sample cannot be undone. API: `POST /api/undo`, `/api/redo`, `history` in the state (`editor/history.py`).

- Web editor: empty kits hidden by default in the list (*masquer les vides* (hide empty ones) checked on opening).
- Rear inputs located using device backups: 15 = Trigger In 4/5, 16 = Trigger In 1, 17 = Trigger In HH, 18 = FootSwitch 1/2, 20 = FootSwitch 3/4; these names replace “slot N” in the editor (`strike_kits.SLOT_NAMES`).
- Desktop app: the window opens maximized (*Restaurer* (Restore) brings it back to 1400×900).
- Web editor: messages shown as toasts (at the top, centered, above dialogs) instead of banners in the page; confirmations disappear on their own after 6 s, errors stay until dismissed.
- Web editor: *Recharger* (Reload) button (next to *Enregistrer* (Save)): rereads the open file and discards unsaved changes, after confirmation; the displayed kit stays the same.
- Web editor: kits reordered by drag and drop in the list, using the ⠿ handle at the end of the row (visible on hover): the kit takes the target kit's place, those in between shift by one. API: `POST /api/kits/{num}/move`; `strike_kits`: `Backup.move_kit`.
- Web editor: *Valeurs par défaut…* (Default values…) resets the settings of the chosen slots to the device's empty kit values (specific to each slot), by section (pad: Feel, Control, Output, Light, Group; waves: Mode, Mix, and sample on request; none checked initially, *toutes les sections* (all sections) link). API: `POST /api/kits/{num}/reset`; `strike_kits`: `Backup.reset_slots`.
- Web editor: Sound (Control section) shown as On / Off (0 = On by default, 1 = Off).
- Web editor: grid of the 9 pads centered in the space; the selected pad gets a background color (instead of a plain red border).
- Web editor: pad sections laid out in columns, each right below the previous one (no more empty space under short sections, Group no longer drops to the bottom of Light).
- Web editor: *Supprimer le kit…* (Delete kit…) replaces the chosen kit, after confirmation, with the device's empty kit (“Empty”, default settings); user samples stay in the backup. API: `POST /api/kits/{num}/clear`; the state flags empty kits (`empty`). `strike_kits`: `Backup.clear_kit`, `EMPTY_KIT`.
- Desktop app, macOS: application menu first (*À propos* (About), *Masquer* (Hide), *Masquer les autres* (Hide Others), *Tout afficher* (Show All), *Quitter* (Quit) `Cmd+Q`); *Quitter* removed from *Fichier* (File) and *Aide* (Help) menu removed, to avoid duplicates. Nothing changes on Linux and Windows (`desktop/menu.js`).

## 0.3.3 — Fixes

- Parameters identified by comparing two device backups: Curve, Kit FX Level, Sync Mode (`params.sync_mode`, fixed byte in the slot), Play Beat and Stop Beat (`light.play_beat` / `stop_beat`), Playback Mode (0–9, FS4 = 9 beyond the declared max) and the waves' Poly/Mono. JSON keys `p13`, `p16`, wave `p09` and `p19` become `curve`, `kit_fx_level`, `playback_mode` and `poly_mono`.
- Web editor: settings grouped by section, as on the device (pad: Feel, Control, Output, Light, Group; waves: Mode, Mix), also in *Modifier plusieurs pads* (Edit several pads); “Control” is now called “Mode”.
- End-to-end test of the desktop app (Playwright, `desktop/e2e/`, `./dev.sh e2e`, included in `./dev.sh all`): opening a copy of the reference backup, editing, saving through the menu and reading back, close confirmation with unsaved changes. Run by the CI on Ubuntu 24.04 (xvfb).
- Per-system manual checklist before a release (`docs/application-bureau.md`).

## 0.3.2 — Version and release management

- GitHub release on a `vX.Y.Z` tag (“Release” workflow, `release.yml`): commit versions checked, packages built for the three systems (`build.yml`, which no longer triggers itself on a tag), then a draft release with the packages and the CHANGELOG notes.
- Windows and macOS packages named `alesis-kit-manager-X.Y.Z-<win|mac>-<arch>[-setup].<ext>` (no spaces); the build checks that each expected package carries the version from `app-names.json` (and the .deb version), as well as the frozen server's `--version`.
- `scripts/verifier-version.py`: version consistency across `app-names.json`, the `package.json` files and the locks (`./dev.sh lint` / `all`, CI); with `X.Y.Z`, also checks the CHANGELOG section; `--notes` prints the release notes (used by `./dev.sh release` and the GitHub release).
- Git hooks (`.githooks/`, enabled by `./dev.sh`): `git tag vX.Y.Z` and pushing a tag are refused if the commit's versions are not X.Y.Z.
- `editor/web/package.json` aligned with the application version (0.3.1).
- Version shown in the UI (next to the title) and in the app's *Aide › À propos* (Help › About) menu; `alesis-kit-manager --version` and `python -m editor --version` (frozen server included) print it and exit. The .deb Docker test checks them.
- `./dev.sh release X.Y.Z`: on `main`, with a clean tree and a `## X.Y.Z` section in the CHANGELOG, writes the version into `app-names.json`, `desktop/package.json` and `editor/web/package.json` (+ locks), commits “Version X.Y.Z” and creates the annotated tag `vX.Y.Z` (message: the CHANGELOG section), without pushing it.
- The application version is also in `app-names.json`; the API shows it (`/docs`, instead of FastAPI's default 0.1.0). `editor/web/package.json` moves from 0.1.0 to the application version at the next `release`.

## 0.3.1 — GitHub Actions fixes

- CI: GitHub actions at v7 (no more Node 20 warnings); Linux package and “Serveur figé” (frozen server) job built on `ubuntu-24.04` (`ubuntu-latest` moves to Ubuntu 26, whose glibc would make the .deb unusable on 24.04). Windows and macOS runners pinned too: `windows-2025`, `macos-26`.
- Fix: the `desktop/server.js` tests failed on Windows (0.3.0 “Package” build); the paths of the server to launch now follow the given platform (`path.win32` / `path.posix`), and a test checks the Windows case on every system.
- Application version: 0.3.1 (`desktop/package.json`, `package-lock.json`).

## 0.3.0 — Move to an Electron desktop app

- `strike_kits.py` becomes the `strike_kits/` package (code in `__init__.py`, imports unchanged); command line: `python3 -m strike_kits export|import …` instead of `python3 strike_kits.py …`.
- CI factored out: setup shared by the jobs in the composite action `.github/actions/setup` (Python and Node versions in a single place); the `ci.yml` “Serveur figé” (frozen server) job reuses the “Paquets” (Packages) workflow (`workflow_call`, on Linux, without packaging) instead of `./dev.sh freeze`.
- Windows (one-click NSIS installer, zip) and macOS Apple Silicon (dmg, zip) packages, unsigned: “Paquets” workflow (`.github/workflows/build.yml`), one runner per system, on a `v*` tag or manually; packages as artifacts. Display name “Alesis Kit Manager” on Windows and macOS. `npm run package` builds the packages for the current system.
- Default allowed folders depending on the system: `/Volumes` on macOS, all drives except the system drive on Windows.
- Server launched without a console window on Windows; frozen server smoke test usable on Windows and with a relative path.
- A single operating mode, the Electron app's: token required on `/api/*`, files designated by absolute path. The “development” mode (`--root` folder, `GET /api/backups` list) is removed.
- `editeur.sh FICHIER`: quick local launch on a backup (usage shown without arguments); `python -m editor --open FICHIER`. Locally, a token is created and passed to the browser in the address (`#token=…`), then kept for the tab.
- UI: opening by full path, *Ouvrir* (Open) field updated after *Enregistrer sous* (Save as).
- UI in desktop mode (step 2 of the move to Electron): if the app exposes `window.strikeDesktop` (token, native `openFile` / `saveFile` dialogs, `setDirty`), *Ouvrir…* (Open…) and *Enregistrer sous…* (Save as…) go through the system dialogs, and the “unsaved” state is reported to it. Development stub (`#…&desktop=fake`, absent from the build) to test this mode in the browser.
- Electron desktop app (`desktop/`, step 3): `npm start [-- FICHIER]` launches the Python server with a random token and opens the editor in a window; *Fichier* (File) menu (*Ouvrir*, *Enregistrer*, *Enregistrer sous*, *Quitter* (Quit)) with shortcuts, native dialogs, single instance, close confirmation (*Enregistrer* / *Quitter sans enregistrer* (Quit without saving) / *Annuler* (Cancel)), server stopped on quit or on crash. `node:test` tests, ESLint; in `dev.sh` and the CI (“desktop” job).
- `./dev.sh start [--frozen] [FICHIER]`: launches the desktop app, with the frozen server if requested (rebuilt if a source has changed).
- Internal identifiers aligned with the application name: `KITMANAGER_TOKEN`, `KITMANAGER_SERVER`, `X-KitManager-Token` header, `window.kitManagerDesktop`, `kitmanager:…` messages between the window and Electron, file types `application/x-kitmanager-bkf` / `-fac` (previously `STRIKE_…`, `X-Strike-Token`, `strikeDesktop`, `strike:…`, `x-strike-…`).
- Application names centralized in `app-names.json`: “Alesis Strike Multipad Kit Manager” (display), “Alesis Kit Manager” (menu), `alesis-kit-manager` (package, executable, `/opt/alesis-kit-manager`, AppArmor profiles), `AlesisKitManager` (`~/.config/AlesisKitManager`), frozen server `alesis-kit-manager-server` (recipe `desktop/server.spec`, entry point `desktop/server_entry.py`); read by Vite, electron-builder (configuration moved to `desktop/electron-builder.config.mjs`), `main.js`, the server and the scripts.
- `./dev.sh test-deb`: installs the .deb in a clean Ubuntu 24.04 Docker container and checks files, file types, bundled server, Electron launch (Xvfb) and uninstallation.
- .deb package: dependency `libasound2t64 | libasound2` added (Electron would not start without it); installation path without spaces (`chrome-sandbox` failed with a path containing some).
- The server only opens and saves in the home folder, the user's removable media (`/media/<user>`, `/run/media/<user>`) and the folders added with `--allow DOSSIER` (also for `./dev.sh serve`), with resolved paths; elsewhere: error 403.
- Documentation: role of the development AppArmor profile, risks and removal (`docs/application-bureau.md`).
- .deb package of the desktop app (step 5): `./dev.sh package` (electron-builder); embedded frozen server, menu entry and icon, opening `.bkf` / `.fac` files by double-click (`file://` URLs accepted as arguments), AppArmor profile installed by the package.
- `./dev.sh serve FICHIER` replaces `editeur.sh` (removed): editor in the browser. A single setup, in `dev.sh` (venv with `requirements-dev.txt`, UI build if a source has changed); `scripts/preparer.sh` is removed. `npm start` no longer prepares anything and reports a missing venv or UI.
- Frozen server (step 4): `./dev.sh freeze` builds with PyInstaller a self-contained folder `desktop/build/strike-server/` (server and UI, 33 MB), then tests it outside the repository; “Serveur figé” CI job. The app launches the server designated by `STRIKE_SERVER`, the one in its resources once packaged, otherwise the `.venv` Python.
- Desktop app: menu bar hidden by default, shown with the Alt key.
- `desktop/apparmor.sh`: AppArmor profile for the development Electron (Ubuntu 24.04 and later block its sandbox); `npm start` warns as long as it is missing.
- `python -m editor --watch-stdin`: the server stops when its standard input closes.
- UI: desktop app commands (`strikeDesktop.onCommand`).
- `scripts/preparer.sh`: venv and UI setup, shared by `editeur.sh` and `npm start`.
- Sample preview (▶): the WAV is downloaded with the token then played from a blob (the audio tag could not send the token).
- UI tests with Vitest and jsdom (`npm test`), run by `dev.sh test` / `all` and by the CI.
- GitHub Actions continuous integration (`.github/workflows/ci.yml`): on every push to `main` and every pull request, `ruff check`, `ruff format --check` and tests on Python 3.14; ESLint and UI build on Node 24.
- Linting: ruff (`pyproject.toml`, `requirements-dev.txt`) with rules E, F, W, I, B and automatic formatting; ESLint with the recommended JavaScript and Svelte rules (`editor/web/eslint.config.js`, `npm run lint`).
- `dev.sh`: `lint [--fix]`, `test [TESTS…]`, `build`, `all` (final summary); installs the development dependencies when needed.
- Fix: the « Interface non construite » (UI not built) warning goes to standard error; it made the Ctrl+C shutdown test fail in the CI, where the UI is not built.
- Code brought into compliance: ruff formatting, `raise … from`, keys for `{#each}` lists, dialog selections as `SvelteSet`.

## 0.2.0 — 2026-10-16

- Local web editor (`python -m editor`): FastAPI + Svelte, kit editing, choosing and previewing samples, adding WAV files, saving to a new file.
- `Backup` class: `.bkf` / `.fac` backup editable in memory, used by the editor and by `import` / `export`.
- Web editor: pad grid laid out as on the device (7-8-9 at the top, half as tall, then 4-5-6 and 1-2-3).
- Web editor: copying one pad's settings to others (sections of your choice, MIDI note kept by default); Control badge (“Click”) on the pads instead of the MIDI note.
- `copy_slot_settings` function and `POST /api/kits/{num}/copy` route.
- Web editor: moving, swapping or duplicating a kit to another number (`Backup.copy_kit`, `Backup.swap_kits`, `POST /api/kits/{num}/transfer` route).
- Web editor: the tempo field's arrows step by 1 BPM (instead of 0.1); a decimal value can still be typed.
- Web editor: tooltips show the setting's default value for the displayed pad (taken from an empty kit of the device; `/api/meta` exposes `defaults`).
- Web editor: *Modifier plusieurs pads…* (Edit several pads…) gives a setting the same value on a selection of pads (`set_slots_value`, `Backup.set_slots`, `POST /api/kits/{num}/set` route).
- Editor server controllable by the desktop app (step 1 of the move to Electron): `STRIKE_TOKEN` token required on `/api/*` (`X-Strike-Token` header), `--port 0` and a `{"ready": true, "port": N}` line once listening; in desktop mode, files opened and saved by absolute path, anywhere.
- *Enregistrer* (Save) writes to the open file (previously only *Enregistrer sous* (Save as) existed and the original backup was protected); on the first save of each session on an original file, its previous state is copied to `<fichier>.N.bak`.
- Stopping the editor with Ctrl+C without an error trace (`KeyboardInterrupt`), with the message « Éditeur arrêté. » (Editor stopped.).
- Opening another backup with unsaved changes is refused by the server (409) unless confirmed (`force`); the UI asks for confirmation.
- `editeur.sh`: default backup folder `Backups/` (otherwise `Strike/`, then the current folder); `.bkf` / `.fac` files in `Backups/` are ignored by Git.
- Web editor: bulk editing can apply to the same pads of several kits, all or nothing (`Backup.set_slots_in_kits`, `POST /api/kits/set` route).
- Tests: a single reference backup, `tests/ressources/Backup001.bkf` (5 MB, built by `tests/construire_reference.py`), independent of the working backups in `Strike/`; tests moved to `tests/`, `.fac` built in memory. `Bkf.remove_last_sample` (inverse of `add_sample`, reserved for tests).
- Web editor: tooltip describing each setting (pad and wave parameters, kit, lighting, sample, velocity), based on the manual; `/api/meta` exposes `description` and `help`.
- `editeur.sh` script: launches the editor, creating or updating the venv, the dependencies and the UI when needed.
- Fix: in pads 1 to 8 of `KITC` kits, fields whose header is overlapped by other data were omitted; their value byte is now read and editable, and all pads show the same fields.
- Documentation reorganized: README reduced to the commands, one guide per use case in `docs/` (editing a kit, adding a sample, web editor, export contents, parameters, limitations, development).

## 0.1.0 — 2026-10-16

- Export of `.bkf` / `.fac` kits to JSON and import into a new backup (byte-for-byte round trip).
- Checksum recalculation (kit, `PACKBKF` / `FILEH` headers); value range validation.
- Sample catalog (`samples.json`); samples can be designated by id or by name.
- Documentation of the `.bkf`, `.fac` and `.kit` formats in `docs/`, including `.had` and sample lists.
- Adding WAV samples from the export's `wav/` folder (reproduces exactly the import done by the device).
- `KITC` kits: reading and editing the values of slots 1 to 8.
- Pad parameters identified: `control` (`p14`, 3 = Click On/Off) and `audio_output` (`p0f`, 4 = Aux+Phone).
- Wave velocities (`velocity_low`, `velocity_high`); fix: the sample of a wave whose velocity is not 0–127 was neither exported nor editable.
- Export of user samples' WAV files to `wav/` (`--no-wav` option); the import skips WAV files already present (by name or by content).
