# Desktop app

**English** · [Français](../fr/desktop-app.md)

Alesis Strike Multipad Kit Manager (short name: Alesis Kit Manager): an
Electron app wrapping the editor, with the same interface in its own window
and the system's dialog boxes. It is installed from a
[.deb package](#deb-package), or run from the repository during development,
with the `.venv` Python or the [frozen server](#frozen-server).

## Running (development)

Requirements: Python 3 and Node.js, as for [the web editor](web-editor.md).

```bash
./dev.sh start Backups/Backup001.bkf     # from the repository root
./dev.sh start                           # home screen, then Fichier > Ouvrir…
```

The path given as an argument is relative to the folder the command is typed in.
`./dev.sh start` first prepares whatever is missing, like `./dev.sh serve` (venv,
dependencies, interface build if a source changed, `desktop/` packages),
then runs `npm start` in `desktop/`. On first run, Electron downloads
its executable.

`npm start` (`npm start -- FILE`) runs Electron directly, without preparing
anything: if the venv or the built interface is missing, the app says so and
suggests running `./dev.sh start`.

### Ubuntu 24.04 and later: AppArmor profile

These Ubuntu versions forbid unprivileged "user namespaces" by default
(`kernel.apparmor_restrict_unprivileged_userns = 1`). Yet Chromium, and
therefore Electron, uses them to isolate its processes. Without permission,
Electron stops at startup:

```
The SUID sandbox helper binary was found, but is not configured correctly.
```

Chrome and VS Code have an AppArmor profile in `/etc/apparmor.d` for this. One
is needed for the Electron in `desktop/node_modules`, installed once:

```bash
desktop/apparmor.sh | sudo tee /etc/apparmor.d/alesis-kit-manager-dev
sudo apparmor_parser -r /etc/apparmor.d/alesis-kit-manager-dev
```

`desktop/apparmor.sh` prints the profile, with the path of this repository's
executable. This path does not change with `npm ci`; the profile must however be
reinstalled if the repository is moved. The profile adds no restriction
(`unconfined`): it only allows user namespaces, and the Chromium sandbox
stays active. As long as the profile is missing, `npm start` prints a
warning before running Electron.

Alternative, to be redone after each Electron reinstall: give
`chrome-sandbox` to root with mode 4755
(`sudo chown root:root desktop/node_modules/electron/dist/chrome-sandbox && sudo chmod 4755 desktop/node_modules/electron/dist/chrome-sandbox`).

#### Why this profile, and what risk

AppArmor attaches profiles to executables, identified by their path, to
restrict what they can do (files, network, privileges). Most programs have
none and run unrestricted (`unconfined`).

User namespaces let an ordinary program create an isolated environment in
which it believes it is root. Sandboxes rely on them (Chromium, Flatpak,
rootless Podman), but they also expose parts of the kernel normally reserved
for root, through which many privilege escalations have gone. Ubuntu therefore
reserves them for programs whose profile allows it (`userns` rule).

Chromium confines the processes that render pages in them: a page exploiting
a vulnerability would remain isolated, with no file access. Without user
namespaces, it needs the root-owned `chrome-sandbox` helper; with neither,
Electron refuses to start rather than run unprotected.

The development profile adds no restriction (`unconfined`) and only allows
user namespaces (`userns`), for this executable alone: it restores the
pre-Ubuntu 24.04 behavior. Chrome, VS Code and the
[.deb package](#deb-package) have the same one.

- **For the app**, it is a gain: the Chromium sandbox works, whereas the
  common alternative, `--no-sandbox`, disables it.
- **For the system**, the weakening is real but limited, and comes from the
  path: the profile targets a file in the home folder, writable by the user.
  A program run under this account (a malicious npm package, for example)
  could replace the executable and inherit the `userns` right, then try to
  exploit a kernel vulnerability to become root. This requires an attacker
  already running code under this account: Ubuntu's restriction mainly
  protects against that next step, and the profile bypasses it for this path.
- **The .deb package profile does not have this flaw**: it targets
  `/opt/alesis-kit-manager/`, which belongs to root; nobody else can replace
  the executable there.
- **The other solutions**: `chrome-sandbox` owned by root with mode 4755 adds a
  privileged program among user-writable files (low risk); `--no-sandbox`
  changes nothing on the system, but offers no protection if a page exploited
  a vulnerability (low risk here, as the window only displays the local
  server).

For everyday use, the .deb package is therefore preferable, and the development
profile should only be kept while developing. To remove it:

```bash
sudo apparmor_parser -R /etc/apparmor.d/alesis-kit-manager-dev
sudo rm /etc/apparmor.d/alesis-kit-manager-dev
```

After that, `npm start` shows its warning again, and Electron no longer starts
in development.

## Frozen server

PyInstaller freezes the Python server into a self-contained folder, needing
neither Python nor the `.venv`: the executable, its libraries and the built
interface. This is what the [.deb package](#deb-package) ships.

```bash
./dev.sh freeze                  # → desktop/build/alesis-kit-manager-server/ (ignored by Git)
./dev.sh start --frozen Backups/Backup001.bkf
```

`./dev.sh start --frozen` first rebuilds the frozen server if it is missing or if
one of its sources changed (without rerunning the smoke test), then runs
the app with `KITMANAGER_SERVER=desktop/build/alesis-kit-manager-server/alesis-kit-manager-server`.

`./dev.sh freeze` builds the interface and the frozen server, then runs its smoke
test: from a temporary folder, with a minimal environment, the executable must
open the reference backup, serve a kit, a WAV and the interface, and refuse
access without a token. CI does the same (« Serveur figé » job).

- Recipe: `desktop/server.spec`, entry point `desktop/server_entry.py`
  (same options as `python -m editor`).
- Debug symbols are removed (`strip`): with a locally compiled Python
  (asdf, pyenv), the folder goes from 73 to 33 MB.
- It is built for the platform and Python version of the machine that
  builds it.

The app runs the server named by `KITMANAGER_SERVER` if it is set, then,
once packaged, the one in its resources (`alesis-kit-manager-server/`), and
otherwise the `.venv` Python.

## .deb package

```bash
./dev.sh package                                              # → desktop/dist/alesis-kit-manager_<version>_amd64.deb
sudo apt install ./desktop/dist/alesis-kit-manager_*_amd64.deb
sudo apt remove alesis-kit-manager                            # uninstall
```

`./dev.sh package` chains the interface build, the frozen server and its smoke
test, then electron-builder (`npm run package` in `desktop/`). It finally checks
that the package contains the frozen server, the interface and the app.
The version number is the one in `desktop/package.json`.

The package (about 110 MB) installs:

- the app in `/opt/alesis-kit-manager/`, with the frozen server in
  `resources/alesis-kit-manager-server/`; the `alesis-kit-manager` command;
- an "Alesis Kit Manager" entry in the applications menu, with its icon;
- the `.bkf` and `.fac` file types: double-clicking a backup in the file
  manager opens it in the app (in the already open window if there is one);
- on Ubuntu 24.04 and later, an AppArmor profile
  (`/etc/apparmor.d/alesis-kit-manager`) that enables the Chromium sandbox:
  nothing to do by hand, unlike in [development](#ubuntu-2404-and-later-apparmor-profile).

To electron-builder's default dependencies, the package adds
`libasound2t64 | libasound2`, without which Electron does not start on a
system with no sound installed.

### Application names

All names come from `app-names.json`, at the repository root:

| Key | Value | Use |
|---|---|---|
| `long` | Alesis Strike Multipad Kit Manager | display: window and page title, interface header, dialog boxes, package description |
| `short` | Alesis Kit Manager | short display: applications menu entry; on Windows and macOS, name of the installed app (`Alesis Kit Manager.app`, Start menu) |
| `id` | alesis-kit-manager | paths: `/opt/<id>`, executable, .deb package, menu entry `<id>.desktop`, AppArmor profiles, frozen server `<id>-server` |
| `config` | AlesisKitManager | configuration folder: `~/.config/<config>` (Windows: `%APPDATA%\<config>`, macOS: `~/Library/Application Support/<config>`) |
| `version` | 0.3.1 | app version as seen by the server (`/docs`); updated by `./dev.sh release` along with those of the `package.json` files (see [New version](development.md#new-version)) |

They are read by Vite (`editor/web/vite.config.js`: `<title>` and `__APP_NAMES__`),
PyInstaller (`desktop/server.spec`), electron-builder (`desktop/electron-builder.config.mjs`), `desktop/main.js` (which
finds them in the packaged app's `package.json`), the server
(title of its `/docs` documentation) and the scripts `dev.sh`, `desktop/apparmor.sh` and
`desktop/test-deb/verifier.sh`. The identifier must not contain spaces:
`chrome-sandbox` does not support an installation path containing any.

### Testing the installation in a container

```bash
./dev.sh test-deb
```

Installs the package from `desktop/dist/` in a clean Ubuntu 24.04 Docker
container (`desktop/test-deb/Dockerfile`, without Python or Node), then checks
(`desktop/test-deb/verifier.sh`):

- installation with `apt` (dependencies, install script);
- the installed files, the menu entry (`desktop-file-validate`), the absence
  of Python;
- the `.bkf` / `.fac` file types and the app associated with them;
- the bundled server: smoke test on the reference backup;
- the app: run under Xvfb by a non-root user, it must open its window on the
  local server and load the editor, then stop the server when quitting;
- uninstallation.

The package is first rebuilt if it is missing or if one of its sources changed.
The container is run with `--security-opt seccomp=unconfined`: Docker's default
seccomp filter forbids user namespaces, and the Chromium sandbox could not
start. The AppArmor profile and the actual desktop integration (menu,
double-click, dialog boxes) cannot be checked in a container.

The icon is `desktop/build-resources/icon.svg`; `icon.png` is its 512 px
rendering, regenerated with `desktop/build-resources/render-icon.cjs` (see its header).

## Windows and macOS packages

PyInstaller does not cross-compile: the frozen server is built on the target
system. The packages for all three systems are therefore built by GitHub
Actions (`.github/workflows/build.yml`, "Package"), on one runner per system:

| Runner | Packages (`desktop/dist/`) |
|---|---|
| `ubuntu-24.04` | `.deb` (not `ubuntu-latest`, which moved to Ubuntu 26: the frozen server depends on the build system's glibc, and the package must also work on 24.04) |
| `windows-2025` (x64) | NSIS `.exe` installer, `.zip` archive |
| `macos-26` (Apple Silicon, arm64) | `.dmg` image, `.zip` archive |

Runners are pinned rather than `*-latest`, so that a build does not change
without a change in the repository. When GitHub announces the retirement of an
image, change its label in `build.yml` (written twice, see the comment at the
top). On Windows and macOS, the runner version does not set the users' minimum
system (which depends on Python and Electron); on Linux, it does: see `ubuntu-24.04`.

The workflow is run by hand from the Actions tab ("Run workflow"), or by
the "Release" workflow on a `vX.Y.Z` tag, which then publishes the packages in
a draft GitHub release (see [New version](development.md#new-version)).
Each job checks version consistency, builds the interface, freezes the
server, tests it (smoke test, `--version`), runs `npm run package`, then
checks that the expected packages carry the version from `app-names.json`;
these are the run's artifacts (`paquet-Linux`, `paquet-Windows`,
`paquet-macOS`). The steps are written in the workflow, without `dev.sh` (Linux
only).

| System | Packages |
|---|---|
| Linux | `alesis-kit-manager_X.Y.Z_amd64.deb` (Debian name; package version checked) |
| Windows | `alesis-kit-manager-X.Y.Z-win-x64-setup.exe`, `alesis-kit-manager-X.Y.Z-win-x64.zip` |
| macOS | `alesis-kit-manager-X.Y.Z-mac-arm64.dmg`, `alesis-kit-manager-X.Y.Z-mac-arm64.zip` |

Locally, `npm run package` builds the packages for the current system (targets in
`desktop/electron-builder.config.mjs`); on Linux, use `./dev.sh package`.

- **Windows**: one-click installation, for the current user
  (`%LOCALAPPDATA%\Programs\Alesis Kit Manager`), without administrator rights,
  with an "Alesis Kit Manager" shortcut and opening of `.bkf` / `.fac` files by
  double-click. The `.zip` archive is used without installation.
- **macOS**: `Alesis Kit Manager.app`, for Apple Silicon Macs only.

The packages are not signed (no certificate). Windows SmartScreen shows
"Windows protected your PC": *More info*, then *Run anyway*. On macOS, the app
only has an ad hoc signature (required on Apple Silicon) and is not notarized:
Gatekeeper blocks it on first launch; right-click the app, *Open*, or
`xattr -dr com.apple.quarantine "/Applications/Alesis Kit Manager.app"`.

The default allowed folders depend on the system (see
[the web editor](web-editor.md#allowed-folders)).

## How it works

- **Server**: the app starts the server (`python -m editor` or the frozen
  server) with `--port 0 --watch-stdin`
  and a random token (`KITMANAGER_TOKEN`) and its configuration folder
  (`KITMANAGER_CONFIG`, where the server keeps the preferences), waits for the line
  `{"ready": true, "port": N}` (30 s at most), then opens the window on
  `http://127.0.0.1:N`. If the server does not start, an error box shows
  the end of its error output.
- **Shutdown**: when quitting, the app closes the server's standard input, and
  the server stops (then `SIGTERM`, `SIGKILL` if needed). If the app crashes,
  standard input is closed too: the server does not outlive it. If the server
  stops on its own, the app reports it and closes.
- **Window**: its size, position and maximized state are remembered from one
  launch to the next (`window-state.json` in the app's configuration folder, see
  [Preferences](web-editor.md#preferences)); a position outside the current
  screens is dropped. On first launch, it opens maximized; *Restore*
  brings it back to 1400×900.
- **Single instance**: running the app again with a file opens it in the
  existing window.
- **Menu**: the bar is hidden, the `Alt` key shows it; shortcuts remain
  active while it is hidden. *File* (*Open…* `Ctrl+O`, *Open Recent*, *Save* `Ctrl+S`,
  *Save As…* `Ctrl+Shift+S`, *Quit* `Ctrl+Q`), *Edit* (*Undo* `Ctrl+Z`, *Redo*
  `Ctrl+Y`, see [Undo / Redo](web-editor.md#undo--redo); cut,
  copy, paste; *Preferences…* `Ctrl+,`), *View* (zoom, developer
  tools), *Help* (*About*: name and version). On macOS, an
  application menu comes first, as for any Mac app: *About*, *Preferences…*
  (`Cmd+,`), *Hide*, *Hide Others*, *Show All*,
  *Quit* (`Cmd+Q`); *Quit* is then no longer in *File*, *Preferences…* no longer in *Edit*, and the *Help*
  menu disappears. Menu template: `desktop/menu.js`.
- **Language**: menus and dialogs follow the interface language
  ([Preferences](web-editor.md#preferences)); at launch, before the interface
  gives it, the one saved in `preferences.json`, otherwise the system's.
  Texts: `desktop/messages.js`.
- **Version**: shown next to the interface title and in *Help ›
  About*; `alesis-kit-manager --version` prints it in the terminal and quits
  without opening a window (`npx electron . --version` in development; nothing is
  shown on Windows, where the app has no console). The frozen server
  also has `--version`.
- **Closing**: with unsaved changes, a box offers
  *Save* (into the open file, with the usual `.bak` copy),
  *Quit without saving* or *Cancel*. A change still waiting
  to be sent to the server is counted.
- **Files**: the server only opens and saves in the user's home folder and
  removable media (see
  [Allowed folders](web-editor.md#allowed-folders)); the dialog boxes let you
  browse the whole disk, but a file chosen elsewhere is refused, with a
  message in the window.
- **Security**: the page has no access to Node (`contextIsolation`, `sandbox`);
  the preload script (`desktop/preload.cjs`) only exposes `window.kitManagerDesktop`
  (see [Desktop mode](web-editor.md#desktop-mode)), and only to the local
  server's page. Navigation is limited to that server; external links open
  in the browser.

## Files

| Path | Role |
|---|---|
| `desktop/main.js` | main process: server, window, menu, dialog boxes, closing |
| `desktop/menu.js` | menu template (application menu first on macOS) |
| `desktop/window-state.js` | window size, position and maximized state, kept from one launch to the next |
| `desktop/messages.js` | texts of the menus and dialogs, in English and French |
| `desktop/preload.cjs` | `window.kitManagerDesktop` bridge |
| `app-names.json` | application names (see [Application names](#application-names)) |
| `desktop/electron-builder.config.mjs` | electron-builder configuration: .deb package, file types, icon |
| `desktop/build-resources/` | icon (source SVG, 512 px PNG and rendering script) |
| `desktop/test-deb/` | package installation test in a container (`./dev.sh test-deb`) |
| `desktop/apparmor.sh` | AppArmor profile for the development Electron, and check before `npm start` |
| `desktop/server.js` | server selection and startup, with no dependency on Electron |
| `desktop/server.spec`, `desktop/server_entry.py` | PyInstaller recipe for the frozen server and its entry point |
| `desktop/test/` | `node:test` tests (`npm test`); a fake server simulates error cases |
| `desktop/e2e/` | end-to-end test (Playwright, `npm run e2e`) |

`npm test` checks reading of the "ready" line, the arguments, failures
(server stopped, silent, not found) and shutdown; a smoke test runs the real
server on the reference backup when `.venv` exists, and the frozen server
when `KITMANAGER_SERVER` points to it (`./dev.sh freeze`).

## End-to-end test

`./dev.sh e2e` prepares the venv and the interface, then runs `npm run e2e` in
`desktop/`: Playwright (`playwright-core`, no downloaded browser) drives
the repository's Electron, with a temporary home folder that receives a copy
of `tests/ressources/Backup001.bkf`.

- The backup is passed as an argument. The test renames kit 031, saves
  with *Fichier › Enregistrer*, checks the `.bak` copy of the original, then
  restarts the app on the file and reads back the new name.
- Closing with unsaved changes: *Annuler* keeps the
  window open, *Quitter sans enregistrer* closes the app without touching
  the file. The native dialog box is replaced in the main process (no system
  window to click).

The test opens real windows for a few seconds: on Linux without a display,
`xvfb-run -a ./dev.sh e2e`. Like `npm start`, it needs the
[AppArmor profile](#ubuntu-2404-and-later-apparmor-profile); with
`KITMANAGER_SERVER`, it uses the frozen server. CI runs it on Ubuntu
24.04 only; on Windows and macOS, the packages are checked by hand.

## Manual checks

What the end-to-end test does not cover: sound, drag and drop, native dialog
boxes and system integration. To be done on each system before publishing a
release (installed package: `.deb`, NSIS installer, `.dmg`), on a copy of a
backup.

| Check | Expected result |
|---|---|
| Installation, then launch from the applications menu ("Alesis Kit Manager" shortcut, Launchpad) | window opened maximized, home screen; app icon; *Restaurer* brings it back to 1400×900 |
| `--version` (Linux, macOS: `"/Applications/Alesis Kit Manager.app/Contents/MacOS/Alesis Kit Manager" --version`) | `alesis-kit-manager X.Y.Z`, no window |
| *Help › About*; version next to the title | package version |
| macOS: application menu (under its name) | *About*, *Hide*, *Hide Others*, *Show All*, *Quit* (`Cmd+Q`); *File* without *Quit*, no *Help* menu |
| Double-click a `.bkf` in the file manager (Explorer, Finder) | the app opens on that file |
| Double-click a second file, with the app open | opened in the same window |
| *File › Open…* (`Ctrl+O`, `Cmd+O` on Mac) | system dialog, `.bkf` / `.fac` filter |
| Open a file on a USB stick (`/media`, `/Volumes`, another drive on Windows) | opened; a file outside the [allowed folders](web-editor.md#allowed-folders) is refused with a message |
| Listen to a user sample (WAV playback) | audible sound, no error |
| Add a sample by dragging and dropping a `.wav` into the sample chooser | sample added, custom sample count incremented |
| Edit a kit, *Save* (`Ctrl+S`) | “Up to date”; `<file>.1.bak` copy of the original |
| *Enregistrer sous…* over an existing file | overwrite confirmation by the system dialog |
| Close the window with changes: *Annuler*, then *Enregistrer* | the window stays open, then the file is saved and the app closes |
| After closing, remaining processes (`ps`, Task Manager, Activity Monitor) | no `alesis-kit-manager-server` |
| Uninstallation (`sudo apt remove`, Settings › Apps, Trash) | app removed; backups are not touched |

On Windows and macOS, also check the first-launch warning
(SmartScreen, Gatekeeper: see [Windows and macOS packages](#windows-and-macos-packages)).

## Troubleshooting

- `The SUID sandbox helper binary was found, but is not configured correctly`:
  see [the AppArmor profile](#ubuntu-2404-and-later-apparmor-profile).
- On Wayland, Chromium prints Vulkan errors at startup
  (`'--ozone-platform=wayland' is not compatible with Vulkan`): they are
  harmless.
